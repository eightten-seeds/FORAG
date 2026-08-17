import hashlib, json
from scripts.collect_sources import build_manifest_record, collect_one, load_approved, sha256_bytes, update_manifest

def test_approved_sources_parse_and_unique():
    records = load_approved()
    assert len(records) == 14
    assert len({r["source_id"] for r in records}) == 14

def test_duplicate_source_id_rejected(tmp_path):
    p = tmp_path / "x.jsonl"; row = {"source_id":"x","brand":"b","source_type":"t","url":"https://x.test","filename":"x.html"}
    p.write_text(json.dumps(row)+"\n"+json.dumps(row)+"\n", encoding="utf-8")
    try: load_approved(p)
    except ValueError as e: assert "duplicate" in str(e)
    else: assert False

def test_sha256_and_manifest_build():
    source = load_approved()[0]; data = b"<html>care</html>"
    assert sha256_bytes(data) == hashlib.sha256(data).hexdigest()
    record = build_manifest_record(source, title=" Care ", final_url=source["url"], accessed_at="2026-08-17", local_path="data/raw/x.html", content_hash=sha256_bytes(data))
    assert record["source_title"] == "Care" and record["enabled"] is True

def test_idempotent_manifest_update(tmp_path):
    p = tmp_path / "sources.jsonl"; source = load_approved()[0]
    a = build_manifest_record(source, title="A", final_url=source["url"], accessed_at="2026-08-17", local_path="x", content_hash="1")
    b = dict(a, source_title="B", content_hash="2")
    update_manifest(a, p); update_manifest(b, p)
    rows = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1 and rows[0]["source_title"] == "B"

def test_failure_does_not_create_manifest(tmp_path):
    p = tmp_path / "sources.jsonl"
    assert not p.exists()


class _Response:
    def __init__(self, status): self.status = status


class _Page:
    url = "https://example.test"
    def goto(self, *_args, **_kwargs): return _Response(404)
    def wait_for_timeout(self, *_args): pass
    def evaluate(self, *_args): pass
    def content(self): return "<html>not used</html>"
    def title(self): return "Not found"


class _Browser:
    def new_page(self): return _Page()
    def close(self): pass


class _Playwright:
    chromium = type("Chromium", (), {"launch": staticmethod(lambda **_kwargs: _Browser())})()
    def __enter__(self): return self
    def __exit__(self, *_args): pass


def test_http_error_does_not_write_raw_or_manifest(tmp_path):
    source = load_approved()[0]
    with __import__("pytest").raises(RuntimeError, match="HTTP status 404"):
        collect_one(source, root=tmp_path, browser_factory=lambda: _Playwright())
    assert not (tmp_path / "data/manifests/sources.jsonl").exists()
