"""Collect only manually approved official care pages with a real browser."""
import argparse, hashlib, json, re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APPROVED = ROOT / "data/seeds/approved_sources.jsonl"
MANIFEST = ROOT / "data/manifests/sources.jsonl"

def load_approved(path=APPROVED):
    records = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    ids = [r["source_id"] for r in records]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate source_id in approved sources")
    required = {"source_id", "brand", "source_type", "url", "filename"}
    if any(set(r) != required for r in records):
        raise ValueError("approved source has an invalid schema")
    return records

def sha256_bytes(content):
    return hashlib.sha256(content).hexdigest()

def build_manifest_record(source, *, title, final_url, accessed_at, local_path, content_hash):
    return {"source_id": source["source_id"], "brand": source["brand"], "source_type": source["source_type"],
            "source_title": title.strip() or source["source_id"], "source_url": final_url,
            "language": "en", "accessed_at": accessed_at, "local_path": local_path,
            "content_hash": content_hash, "enabled": True}

def update_manifest(record, path=MANIFEST):
    path = Path(path); existing = []
    if path.exists():
        existing = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    by_id = {item["source_id"]: item for item in existing}
    by_id[record["source_id"]] = record
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(by_id[k], ensure_ascii=False) + "\n" for k in by_id), encoding="utf-8")

def _expand_faq(page):
    for locator in (page.locator("button"), page.locator("[role='button']"), page.locator("summary")):
        for i in range(min(locator.count(), 100)):
            try:
                text = locator.nth(i).inner_text(timeout=300).strip()
                if re.search(r"faq|question|care|wash|clean|expand|more|how", text, re.I):
                    locator.nth(i).click(timeout=500)
            except Exception:
                pass

def collect_one(source, *, root=ROOT, browser_factory=None):
    from playwright.sync_api import sync_playwright
    factory = browser_factory or sync_playwright
    with factory() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.goto(source["url"], wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(1000)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(1000)
            _expand_faq(page)
            html = page.content().encode("utf-8")
            if len(html) < 500 or b"<html" not in html.lower():
                raise RuntimeError("page content is empty or not HTML")
            destination = Path(root) / "data/raw" / source["filename"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(html)
            record = build_manifest_record(source, title=page.title(), final_url=page.url,
                accessed_at=date.today().isoformat(), local_path="data/raw/" + source["filename"],
                content_hash=sha256_bytes(html))
            update_manifest(record, Path(root) / "data/manifests/sources.jsonl")
            return record
        finally:
            browser.close()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-id")
    parser.add_argument("--all", action="store_true", help="collect every approved URL")
    args = parser.parse_args()
    sources = load_approved()
    if not args.source_id and not args.all:
        parser.error("choose --source-id or --all; no implicit whole-list collection")
    selected = sources if args.all else [s for s in sources if s["source_id"] == args.source_id]
    if not selected: raise SystemExit(f"approved source not found: {args.source_id}")
    failures = 0
    for source in selected:
        try: print(json.dumps(collect_one(source), ensure_ascii=False))
        except Exception as exc: failures += 1; print(f"FAILED {source['source_id']}: {exc}")
    return 1 if failures else 0

if __name__ == "__main__": raise SystemExit(main())
