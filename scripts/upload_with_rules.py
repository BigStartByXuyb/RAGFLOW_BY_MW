#!/usr/bin/env python3
"""Upload files to a RAGFlow dataset and pick the parsing/chunking strategy by file name.

Why this exists: a RAGFlow pipeline routes by *file suffix* only — the documented
ingestion components (File / Parser / Chunker / Tokenizer / Extractor) are wired into a
fixed topology and there is no conditional node, so "if the file name matches *合同* use
the table strategy, otherwise keep the default" cannot be expressed inside the pipeline.
This script does that routing on the upload path instead:

    upload -> match the file name against the rule table -> PATCH the document's parse
    strategy -> trigger ingestion

Rules are evaluated in order and the first match wins. A file that matches nothing keeps
whatever the knowledge base is configured with.

Usage (Windows PowerShell):

    $env:RAGFLOW_API_KEY = "<key from the RAGFlow UI>"   # or pass --api-key
    python scripts/upload_with_rules.py `
        --base-url http://10.101.0.62:8082 `
        --dataset <dataset-id> `
        --rules scripts/filename-rules.example.json `
        C:\\inbox\\*.pdf

Options:
    --dry-run     only show which rule each file matches
    --no-parse    upload and patch, but do not start ingestion
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import requests

# Windows consoles default to a legacy code page, which turns the Chinese file names in
# the report into mojibake. Force UTF-8 so the output stays readable.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")


@dataclass
class Rule:
    pattern: str
    parser_id: str | None = None
    pipeline_id: str | None = None
    parse_type: int | None = None

    @classmethod
    def from_dict(cls, raw: dict) -> "Rule":
        pattern = str(raw.get("pattern", "")).strip()
        if not pattern:
            raise ValueError(f"rule without a pattern: {raw!r}")
        rule = cls(
            pattern=pattern,
            parser_id=(raw.get("parser_id") or None),
            pipeline_id=(raw.get("pipeline_id") or None),
            parse_type=raw.get("parse_type"),
        )
        if rule.parser_id and rule.pipeline_id:
            raise ValueError(f"rule {pattern!r}: set either parser_id or pipeline_id, not both")
        if rule.pipeline_id and rule.parse_type is None:
            rule.parse_type = 2
        if rule.parser_id and rule.parse_type is None:
            rule.parse_type = 1
        return rule

    def matches(self, filename: str) -> bool:
        name = filename.lower()
        pattern = self.pattern.lower()
        return fnmatch.fnmatch(name, pattern) or pattern.strip("*") in name

    def payload(self) -> dict:
        body: dict = {}
        if self.parse_type is not None:
            body["parse_type"] = self.parse_type
        if self.parser_id:
            body["parser_id"] = self.parser_id
        if self.pipeline_id:
            body["pipeline_id"] = self.pipeline_id
        return body

    def describe(self) -> str:
        if self.pipeline_id:
            return f"pipeline={self.pipeline_id}"
        if self.parser_id:
            return f"parser_id={self.parser_id}"
        return "no override"


def load_rules(path: Path) -> list[Rule]:
    data = json.loads(path.read_text(encoding="utf-8"))
    raw_rules = data.get("rules", data if isinstance(data, list) else [])
    return [Rule.from_dict(item) for item in raw_rules]


def pick_rule(filename: str, rules: list[Rule]) -> Rule | None:
    for rule in rules:
        if rule.matches(filename):
            return rule
    return None


class RagflowClient:
    def __init__(self, base_url: str, api_key: str, timeout: int = 300) -> None:
        self.base = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {api_key}"

    def upload(self, dataset_id: str, path: Path) -> str:
        url = f"{self.base}/api/v1/datasets/{dataset_id}/documents"
        with path.open("rb") as fh:
            resp = self.session.post(
                url,
                params={"type": "local"},
                files={"file": (path.name, fh)},
                timeout=self.timeout,
            )
        body = _json_or_raise(resp, f"upload {path.name}")
        items = body.get("data") or []
        if isinstance(items, dict):
            items = [items]
        if not items:
            raise RuntimeError(f"upload {path.name}: response has no document: {body}")
        doc = items[0]
        doc_id = doc.get("id") or doc.get("document_id")
        if not doc_id:
            raise RuntimeError(f"upload {path.name}: no document id in {doc!r}")
        return str(doc_id)

    def patch_document(self, dataset_id: str, document_id: str, payload: dict) -> None:
        url = f"{self.base}/api/v1/datasets/{dataset_id}/documents/{document_id}"
        resp = self.session.patch(url, json=payload, timeout=self.timeout)
        _json_or_raise(resp, f"patch {document_id}")

    def start_ingestion(self, dataset_id: str, document_ids: list[str]) -> None:
        url = f"{self.base}/api/v1/datasets/{dataset_id}/chunks"
        resp = self.session.post(
            url, json={"document_ids": document_ids}, timeout=self.timeout
        )
        _json_or_raise(resp, "start ingestion")


def _json_or_raise(resp: requests.Response, what: str) -> dict:
    try:
        body = resp.json()
    except ValueError:
        raise RuntimeError(f"{what}: HTTP {resp.status_code} {resp.text[:200]}")
    if resp.status_code >= 400 or body.get("code") not in (0, None):
        raise RuntimeError(
            f"{what}: HTTP {resp.status_code} code={body.get('code')} {body.get('message')}"
        )
    return body


def expand_inputs(patterns: list[str]) -> list[Path]:
    files: list[Path] = []
    for raw in patterns:
        path = Path(raw)
        if path.is_dir():
            files.extend(sorted(p for p in path.rglob("*") if p.is_file()))
        elif path.is_file():
            files.append(path)
        else:
            matches = sorted(Path().glob(raw))
            if not matches:
                raise SystemExit(f"no such file or directory: {raw}")
            files.extend(matches)
    return files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("inputs", nargs="+", help="files, directories, or glob patterns")
    parser.add_argument("--base-url", default=os.environ.get("RAGFLOW_BASE_URL", "http://127.0.0.1"))
    parser.add_argument("--api-key", default=os.environ.get("RAGFLOW_API_KEY"))
    parser.add_argument("--dataset", required=True, help="dataset (knowledge base) id")
    parser.add_argument("--rules", type=Path, default=Path(__file__).with_name("filename-rules.example.json"))
    parser.add_argument("--dry-run", action="store_true", help="only show the matched rule")
    parser.add_argument("--no-parse", action="store_true", help="do not trigger ingestion")
    args = parser.parse_args(argv)

    if not args.api_key and not args.dry_run:
        return _fail("missing API key: pass --api-key or set RAGFLOW_API_KEY")

    rules = load_rules(args.rules)
    files = expand_inputs(args.inputs)
    if not files:
        return _fail("nothing to upload")

    plans = [(path, pick_rule(path.name, rules)) for path in files]

    if args.dry_run:
        print(f"{'file':<40} {'rule':<20} action")
        for path, rule in plans:
            print(f"{path.name:<40} {(rule.pattern if rule else '-'):<20} {rule.describe() if rule else 'knowledge base default'}")
        return 0

    client = RagflowClient(args.base_url, args.api_key)
    uploaded: list[tuple[Path, str, Rule | None]] = []

    for path, rule in plans:
        try:
            doc_id = client.upload(args.dataset, path)
            if rule:
                client.patch_document(args.dataset, doc_id, rule.payload())
            uploaded.append((path, doc_id, rule))
            print(f"uploaded {path.name} -> {doc_id} ({rule.describe() if rule else 'dataset default'})")
        except Exception as exc:  # noqa: BLE001 - report and continue with other files
            print(f"FAILED {path.name}: {exc}", file=sys.stderr)

    if not uploaded:
        return _fail("no file was uploaded")

    if not args.no_parse:
        try:
            client.start_ingestion(args.dataset, [doc_id for _, doc_id, _ in uploaded])
            print(f"ingestion started for {len(uploaded)} document(s)")
        except Exception as exc:  # noqa: BLE001
            print(f"FAILED to start ingestion: {exc}", file=sys.stderr)
            return 1

    return 0


def _fail(message: str) -> int:
    print(message, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
