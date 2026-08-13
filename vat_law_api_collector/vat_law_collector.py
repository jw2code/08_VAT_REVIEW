#!/usr/bin/env python3
"""법제처 국가법령정보 공동활용 API에서 VAT 검토용 데이터를 수집한다.

목록 API로 후보 문서를 찾고, 일련번호로 본문 API를 호출한 뒤
원본 JSON/HTML과 분석용 CSV를 함께 저장한다.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


SEARCH_URL = "https://www.law.go.kr/DRF/lawSearch.do"
SERVICE_URL = "https://www.law.go.kr/DRF/lawService.do"
DEFAULT_LAWS = ("부가가치세법", "부가가치세법 시행령", "부가가치세법 시행규칙")
DEFAULT_KEYWORDS = ("부가가치세", "매입세액", "세금계산서")

STANDARD_COLUMNS = [
    "document_type", "source_target", "source_id", "title", "reference_no",
    "document_date", "court_or_agency", "tax_type", "issue_or_holding",
    "summary_or_answer", "claim", "facts_and_reasoning", "related_law",
    "full_text", "search_text", "source_url", "matched_queries",
    "body_format", "collected_at", "content_sha256", "raw_file",
]
CHUNK_COLUMNS = [
    "chunk_id", "source_target", "source_id", "document_type", "title",
    "reference_no", "document_date", "chunk_no", "chunk_text", "source_url",
    "content_sha256",
]


@dataclass(frozen=True)
class SourceSpec:
    name: str
    target: str
    id_keys: tuple[str, ...]
    title_keys: tuple[str, ...]
    ref_keys: tuple[str, ...]
    date_keys: tuple[str, ...]
    agency_keys: tuple[str, ...]
    period_param: str | None
    has_body_api: bool = True


SOURCES = {
    "precedents": SourceSpec(
        "판례", "prec", ("판례일련번호", "판례정보일련번호"),
        ("사건명",), ("사건번호",), ("선고일자",), ("법원명",), "prncYd",
    ),
    "tax_tribunal": SourceSpec(
        "조세심판례", "ttSpecialDecc", ("특별행정심판재결례일련번호",),
        ("사건명",), ("청구번호", "사건번호"), ("의결일자", "처분일자"),
        ("재결청", "처분청"), "rslYd",
    ),
    "interpretations": SourceSpec(
        "법령해석례", "expc", ("법령해석례일련번호",),
        ("안건명",), ("안건번호",), ("회신일자", "해석일자"),
        ("회신기관명", "해석기관명"), "explYd",
    ),
    "nts": SourceSpec(
        "국세청 법령해석(목록)", "ntsCgmExpc", ("법령해석일련번호",),
        ("안건명",), ("안건번호",), ("해석일자",), ("해석기관명",),
        "explYd", has_body_api=False,
    ),
}


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        value = clean_text(data)
        if value:
            self.parts.append(value)

    def text(self) -> str:
        return "\n".join(self.parts)


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return ""
    text = html.unescape(str(value)).replace("\u00a0", " ")
    return re.sub(r"[ \t\r\f\v]+", " ", text).strip()


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def make_session() -> requests.Session:
    retry = Retry(
        total=5, connect=5, read=5, backoff_factor=0.8,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(("GET",)), respect_retry_after_header=True,
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update({"User-Agent": "VAT-Review-Agent/1.0 (law data collector)"})
    return session


def api_get(session: requests.Session, url: str, params: dict[str, Any], timeout: int) -> requests.Response:
    response = session.get(url, params=params, timeout=timeout)
    response.raise_for_status()
    return response


def parse_json_response(response: requests.Response) -> Any:
    try:
        return response.json()
    except ValueError as exc:
        preview = response.text[:300].replace("\n", " ")
        raise ValueError(f"JSON 응답이 아닙니다: {preview}") from exc


def walk_dicts(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_dicts(child)


def first_value(value: Any, keys: Iterable[str]) -> str:
    wanted = set(keys)
    for item in walk_dicts(value):
        for key, child in item.items():
            if key in wanted:
                text = clean_text(child)
                if text:
                    return text
    return ""


def all_values(value: Any, keys: Iterable[str]) -> list[str]:
    wanted = set(keys)
    found: list[str] = []
    seen: set[str] = set()
    for item in walk_dicts(value):
        for key, child in item.items():
            if key in wanted:
                text = clean_text(child)
                if text and text not in seen:
                    seen.add(text)
                    found.append(text)
    return found


def find_records(payload: Any, id_keys: Iterable[str]) -> list[dict[str, Any]]:
    wanted = set(id_keys)
    records: list[dict[str, Any]] = []
    for item in walk_dicts(payload):
        if any(clean_text(item.get(key)) for key in wanted):
            records.append(item)
    return records


def total_count(payload: Any) -> int:
    value = first_value(payload, ("totalCnt", "totalcnt", "총건수"))
    try:
        return int(value.replace(",", ""))
    except (ValueError, AttributeError):
        return 0


def safe_name(value: str) -> str:
    cleaned = re.sub(r"[^0-9A-Za-z가-힣._-]+", "_", value).strip("_")
    return cleaned[:100] or "unknown"


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if columns is None:
        columns = sorted({key for row in rows for key in row}) if rows else ["message"]
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def split_text(text: str, max_chars: int = 3500, overlap: int = 300) -> list[str]:
    """긴 법률문서를 임베딩하기 좋은 크기로 나눈다."""
    text = clean_text(text)
    if not text:
        return []
    paragraphs = [part.strip() for part in re.split(r"\n{2,}|(?<=다\.)\s+", text) if part.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(paragraph) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            step = max(1, max_chars - overlap)
            for start in range(0, len(paragraph), step):
                piece = paragraph[start:start + max_chars]
                if piece:
                    chunks.append(piece)
            continue
        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) <= max_chars:
            current = candidate
        else:
            chunks.append(current)
            prefix = current[-overlap:] if overlap else ""
            current = f"{prefix}\n\n{paragraph}".strip()
    if current:
        chunks.append(current)
    return chunks


def make_rag_chunks(rows: list[dict[str, str]]) -> list[dict[str, str | int]]:
    chunks: list[dict[str, str | int]] = []
    for row in rows:
        for number, chunk_text in enumerate(split_text(row.get("search_text", "")), start=1):
            source_key = f"{row['source_target']}:{row['source_id']}:{number}"
            chunks.append({
                "chunk_id": source_key,
                "source_target": row["source_target"],
                "source_id": row["source_id"],
                "document_type": row["document_type"],
                "title": row["title"],
                "reference_no": row["reference_no"],
                "document_date": row["document_date"],
                "chunk_no": number,
                "chunk_text": chunk_text,
                "source_url": row["source_url"],
                "content_sha256": hashlib.sha256(chunk_text.encode("utf-8")).hexdigest(),
            })
    return chunks


def normalize_date_range(start: str | None, end: str | None) -> str | None:
    if not start and not end:
        return None
    start = start or "19000101"
    end = end or datetime.now().strftime("%Y%m%d")
    for value in (start, end):
        if not re.fullmatch(r"\d{8}", value):
            raise ValueError("날짜는 YYYYMMDD 형식이어야 합니다.")
    return f"{start}~{end}"


def collect_search_records(
    session: requests.Session,
    oc: str,
    spec: SourceSpec,
    keywords: list[str],
    output: Path,
    period: str | None,
    delay: float,
    timeout: int,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, str]]]:
    merged: dict[str, dict[str, Any]] = {}
    errors: list[dict[str, str]] = []
    raw_dir = output / "raw" / spec.target / "lists"

    for keyword in keywords:
        page = 1
        while True:
            params: dict[str, Any] = {
                "OC": oc, "target": spec.target, "type": "JSON",
                "search": 2, "query": keyword, "display": 100,
                "page": page, "sort": "ddes",
            }
            if period and spec.period_param:
                params[spec.period_param] = period
            try:
                response = api_get(session, SEARCH_URL, params, timeout)
                payload = parse_json_response(response)
                write_json(raw_dir / f"{safe_name(keyword)}_page_{page:04d}.json", payload)
                records = find_records(payload, spec.id_keys)
                count = total_count(payload)
                for record in records:
                    source_id = first_value(record, spec.id_keys)
                    if not source_id:
                        continue
                    if source_id not in merged:
                        merged[source_id] = {"record": record, "queries": set()}
                    merged[source_id]["queries"].add(keyword)
                print(f"[{spec.name}] '{keyword}' {page}페이지: {len(records)}건 / 전체 {count}건")
                if not records or page * 100 >= count:
                    break
                page += 1
                time.sleep(delay)
            except Exception as exc:  # 계속 가능한 수집 오류는 기록 후 다음 검색어로 진행
                errors.append({
                    "source": spec.name, "stage": "list", "query": keyword,
                    "page_or_id": str(page), "error": str(exc),
                })
                print(f"[경고] {spec.name} 목록 실패: {keyword} / {page} / {exc}", file=sys.stderr)
                break
        time.sleep(delay)
    return merged, errors


def extract_document_row(
    spec: SourceSpec,
    source_id: str,
    list_record: dict[str, Any],
    body: Any,
    matched_queries: Iterable[str],
    body_format: str,
    raw_file: Path,
) -> dict[str, str]:
    combined = {"list": list_record, "body": body}
    title = first_value(combined, spec.title_keys)
    reference_no = first_value(combined, spec.ref_keys)
    document_date = first_value(combined, spec.date_keys)
    agency = first_value(combined, spec.agency_keys)
    source_url = first_value(combined, (
        "판례상세링크", "행정심판재결례상세링크", "법령해석례상세링크",
        "법령해석상세링크", "법령상세링크",
    ))

    if spec.target == "prec":
        issue = first_value(body, ("판시사항",))
        summary = first_value(body, ("판결요지",))
        claim = ""
        reasoning = first_value(body, ("판례내용",))
        related = first_value(body, ("참조조문", "참조판례"))
        tax_type = ""
    elif spec.target == "ttSpecialDecc":
        issue = first_value(body, ("주문", "따른결정"))
        summary = first_value(body, ("재결요지",))
        claim = first_value(body, ("청구취지",))
        reasoning = first_value(body, ("이유",))
        related = first_value(body, ("관련법령", "참조결정"))
        tax_type = first_value(body, ("세목",))
    else:
        issue = first_value(body, ("질의요지", "질의내용"))
        summary = first_value(body, ("회답", "답변", "해석내용"))
        claim = ""
        reasoning = first_value(body, ("이유", "검토의견"))
        related = first_value(body, ("관련법령", "관계법령"))
        tax_type = first_value(body, ("세목",))

    if isinstance(body, str):
        full_text = clean_text(body)
    else:
        full_text_parts = all_values(body, (
            "판시사항", "판결요지", "판례내용", "재결요지", "주문", "청구취지",
            "이유", "관련법령", "질의요지", "질의내용", "회답", "답변", "해석내용",
        ))
        full_text = "\n\n".join(full_text_parts)
    search_text = "\n".join(x for x in (title, issue, summary, claim, reasoning, related) if x)
    collected_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    return {
        "document_type": spec.name,
        "source_target": spec.target,
        "source_id": source_id,
        "title": title,
        "reference_no": reference_no,
        "document_date": document_date,
        "court_or_agency": agency,
        "tax_type": tax_type,
        "issue_or_holding": issue,
        "summary_or_answer": summary,
        "claim": claim,
        "facts_and_reasoning": reasoning,
        "related_law": related,
        "full_text": full_text,
        "search_text": search_text,
        "source_url": source_url,
        "matched_queries": " | ".join(sorted(matched_queries)),
        "body_format": body_format,
        "collected_at": collected_at,
        "content_sha256": hashlib.sha256(full_text.encode("utf-8")).hexdigest(),
        "raw_file": raw_file.as_posix(),
    }


def collect_body_sources(
    session: requests.Session,
    oc: str,
    spec: SourceSpec,
    candidates: dict[str, dict[str, Any]],
    output: Path,
    delay: float,
    timeout: int,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    rows: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []
    raw_dir = output / "raw" / spec.target / "bodies"
    raw_dir.mkdir(parents=True, exist_ok=True)

    for index, (source_id, item) in enumerate(candidates.items(), start=1):
        record = item["record"]
        queries = item["queries"]
        if not spec.has_body_api:
            raw_file = raw_dir / f"{safe_name(source_id)}_list_only.json"
            write_json(raw_file, record)
            rows.append(extract_document_row(
                spec, source_id, record, {}, queries, "LIST_ONLY", raw_file,
            ))
            continue

        json_file = raw_dir / f"{safe_name(source_id)}.json"
        html_file = raw_dir / f"{safe_name(source_id)}.html"
        body: Any
        body_format = "JSON"
        raw_file = json_file
        try:
            if json_file.exists():
                body = json.loads(json_file.read_text(encoding="utf-8"))
            else:
                params = {"OC": oc, "target": spec.target, "type": "JSON", "ID": source_id}
                response = api_get(session, SERVICE_URL, params, timeout)
                body = parse_json_response(response)
                write_json(json_file, body)
        except Exception as json_exc:
            # 공식 안내상 국세법령정보시스템 출처 판례 본문은 HTML만 제공될 수 있다.
            if spec.target != "prec":
                errors.append({
                    "source": spec.name, "stage": "body", "query": "",
                    "page_or_id": source_id, "error": str(json_exc),
                })
                print(f"[경고] {spec.name} 본문 실패: {source_id} / {json_exc}", file=sys.stderr)
                continue
            try:
                params = {"OC": oc, "target": spec.target, "type": "HTML", "ID": source_id}
                response = api_get(session, SERVICE_URL, params, timeout)
                response.encoding = response.apparent_encoding or response.encoding
                raw_html = response.text
                html_file.write_text(raw_html, encoding="utf-8")
                parser = TextExtractor()
                parser.feed(raw_html)
                body = parser.text()
                body_format = "HTML_FALLBACK"
                raw_file = html_file
            except Exception as html_exc:
                errors.append({
                    "source": spec.name, "stage": "body_json_and_html", "query": "",
                    "page_or_id": source_id,
                    "error": f"JSON={json_exc}; HTML={html_exc}",
                })
                continue

        rows.append(extract_document_row(
            spec, source_id, record, body, queries, body_format, raw_file,
        ))
        print(f"[{spec.name}] 본문 {index}/{len(candidates)}: {source_id}")
        time.sleep(delay)
    return rows, errors


def collect_laws(
    session: requests.Session,
    oc: str,
    law_names: list[str],
    output: Path,
    delay: float,
    timeout: int,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    rows: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []
    raw_dir = output / "raw" / "eflaw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    for law_name in law_names:
        try:
            params = {
                "OC": oc, "target": "eflaw", "type": "JSON", "search": 1,
                "query": law_name, "display": 100, "page": 1,
            }
            list_payload = parse_json_response(api_get(session, SEARCH_URL, params, timeout))
            write_json(raw_dir / f"{safe_name(law_name)}_list.json", list_payload)
            candidates = find_records(list_payload, ("법령ID",))
            exact = [
                item for item in candidates
                if first_value(item, ("법령명한글", "법령명_한글")) == law_name
            ]
            if not exact:
                raise LookupError(f"정확히 일치하는 현행법령을 찾지 못했습니다: {law_name}")
            list_record = exact[0]
            law_id = first_value(list_record, ("법령ID",))
            body_file = raw_dir / f"{safe_name(law_name)}_{safe_name(law_id)}.json"
            if body_file.exists():
                body = json.loads(body_file.read_text(encoding="utf-8"))
            else:
                params = {"OC": oc, "target": "eflaw", "type": "JSON", "ID": law_id}
                body = parse_json_response(api_get(session, SERVICE_URL, params, timeout))
                write_json(body_file, body)

            title = first_value(body, ("법령명_한글", "법령명한글")) or law_name
            articles = all_values(body, (
                "조문내용", "항내용", "호내용", "목내용", "부칙내용", "별표내용",
                "개정문내용", "제개정이유내용",
            ))
            full_text = "\n".join(articles)
            collected_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
            rows.append({
                "document_type": "현행법령", "source_target": "eflaw",
                "source_id": law_id, "title": title,
                "reference_no": first_value(body, ("공포번호",)),
                "document_date": first_value(body, ("시행일자", "공포일자")),
                "court_or_agency": first_value(body, ("소관부처", "소관부처명")),
                "tax_type": "부가가치세", "issue_or_holding": "", "summary_or_answer": "",
                "claim": "", "facts_and_reasoning": "", "related_law": "",
                "full_text": full_text, "search_text": f"{title}\n{full_text}",
                "source_url": first_value(list_record, ("법령상세링크",)),
                "matched_queries": law_name, "body_format": "JSON",
                "collected_at": collected_at,
                "content_sha256": hashlib.sha256(full_text.encode("utf-8")).hexdigest(),
                "raw_file": body_file.as_posix(),
            })
            print(f"[현행법령] {title}: {len(articles)}개 텍스트 단위")
            time.sleep(delay)
        except Exception as exc:
            errors.append({
                "source": "현행법령", "stage": "law", "query": law_name,
                "page_or_id": "", "error": str(exc),
            })
            print(f"[경고] 현행법령 실패: {law_name} / {exc}", file=sys.stderr)
    return rows, errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="VAT Review Agent용 법률 데이터 수집기")
    parser.add_argument(
        "--sources", nargs="+", default=["all"],
        choices=["all", "laws", *SOURCES.keys()],
        help="수집할 출처. 기본값: all",
    )
    parser.add_argument("--keywords", nargs="+", default=list(DEFAULT_KEYWORDS))
    parser.add_argument("--laws", nargs="+", default=list(DEFAULT_LAWS))
    parser.add_argument("--start-date", help="검색 시작일 YYYYMMDD")
    parser.add_argument("--end-date", help="검색 종료일 YYYYMMDD")
    parser.add_argument("--output", default="output", help="저장 폴더")
    parser.add_argument("--delay", type=float, default=0.25, help="호출 간 대기 초")
    parser.add_argument("--timeout", type=int, default=40, help="요청 제한시간 초")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_dotenv(Path(".env"))
    oc = os.environ.get("LAW_API_OC", "").strip()
    if not oc:
        print("LAW_API_OC가 없습니다. .env.example을 .env로 복사한 뒤 인증값을 입력하세요.", file=sys.stderr)
        return 2

    try:
        period = normalize_date_range(args.start_date, args.end_date)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    selected = set(SOURCES) | {"laws"} if "all" in args.sources else set(args.sources)
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    session = make_session()
    all_rows: list[dict[str, str]] = []
    all_errors: list[dict[str, str]] = []

    if "laws" in selected:
        rows, errors = collect_laws(
            session, oc, args.laws, output, args.delay, args.timeout,
        )
        write_csv(output / "laws.csv", rows, STANDARD_COLUMNS)
        all_rows.extend(rows)
        all_errors.extend(errors)

    for key, spec in SOURCES.items():
        if key not in selected:
            continue
        candidates, errors = collect_search_records(
            session, oc, spec, args.keywords, output, period, args.delay, args.timeout,
        )
        rows, body_errors = collect_body_sources(
            session, oc, spec, candidates, output, args.delay, args.timeout,
        )
        write_csv(output / f"{key}.csv", rows, STANDARD_COLUMNS)
        all_rows.extend(rows)
        all_errors.extend(errors + body_errors)

    # RAG/임베딩 입력에는 검색문이 비어 있지 않은 문서만 포함한다.
    rag_rows = [row for row in all_rows if clean_text(row.get("search_text"))]
    write_csv(output / "rag_documents.csv", rag_rows, STANDARD_COLUMNS)
    write_csv(output / "rag_chunks.csv", make_rag_chunks(rag_rows), CHUNK_COLUMNS)
    write_csv(
        output / "collection_errors.csv", all_errors,
        ["source", "stage", "query", "page_or_id", "error"],
    )
    summary = []
    for doc_type in sorted({row["document_type"] for row in all_rows}):
        group = [row for row in all_rows if row["document_type"] == doc_type]
        summary.append({
            "document_type": doc_type, "count": len(group),
            "with_full_text": sum(bool(row["full_text"]) for row in group),
            "unique_content_hashes": len({row["content_sha256"] for row in group if row["content_sha256"]}),
        })
    write_csv(
        output / "collection_summary.csv", summary,
        ["document_type", "count", "with_full_text", "unique_content_hashes"],
    )
    print(f"\n완료: {len(all_rows)}건, 오류 {len(all_errors)}건")
    print(f"저장 위치: {output}")
    return 0 if all_rows else 1


if __name__ == "__main__":
    raise SystemExit(main())
