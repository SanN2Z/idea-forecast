"""cited_backbone.py -- collect the citation backbone and/or the last-N-days shoots of a research direction.

Backends: OpenAlex (title+abstract match, cited_by_count) for the backbone; arXiv API (submittedDate) for the recent shoots.
Both free, no key; set OPENALEX_MAILTO for the polite pool.
Semantic Scholar was tried first and rate-limits unauthenticated clients (HTTP 429) too often to be usable.

    python cited_backbone.py --project <idea-stage> --query "self-evolving agents harness" --top 40 --since 2019
    python cited_backbone.py --project <idea-stage> --query "self-evolving agents harness" --recent-days 90
    python cited_backbone.py --project <idea-stage> --query "..." --top 40 --recent-days 90   # both, two files

Output (markdown tables, one row per paper: id | title | year | citations | venue | date | url | first sentence):
    <project>/terrain/backbone_<slug>_<stamp>.md      top-cited (sorted by cited_by_count)
    <project>/terrain/recent_<slug>_<stamp>.md        published within --recent-days (sorted by date)
Both are inputs for Searcher-A, who must still read the full text of anything that enters a card.
Fails loud on HTTP errors or empty results. Several --query values may be given; results are merged by work id.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

API = "https://api.openalex.org/works"
SELECT = "id,doi,title,publication_year,publication_date,cited_by_count,primary_location,abstract_inverted_index,ids"


def get(params: dict) -> dict:
    mailto = os.environ.get("OPENALEX_MAILTO")
    if mailto:
        params["mailto"] = mailto
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "idea-forecast/1.0"})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001 - retry with backoff, then fail loud
            if attempt == 5:
                raise SystemExit(f"[fail] OpenAlex request failed: {exc}\n{url}")
            time.sleep(2 * (attempt + 1))
    return {}


def fetch(query: str, limit: int, filt: str, sort: str) -> list[dict]:
    rows, page = [], 1
    while len(rows) < limit:
        f = f"title_and_abstract.search:{query}" + ("," + filt if filt else "")
        data = get({"filter": f, "sort": sort, "per-page": min(200, limit - len(rows)), "page": page, "select": SELECT})
        batch = data.get("results", [])
        rows.extend(batch)
        if not batch or len(batch) < min(200, limit - len(rows) + len(batch)):
            break
        page += 1
        time.sleep(0.3)
    return rows[:limit]


def work_id(w: dict) -> str:
    if w.get("abstract_text"):
        return w["id"]
    ids = w.get("ids") or {}
    loc = (w.get("primary_location") or {}).get("landing_page_url") or ""
    m = re.search(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})", loc)
    if m:
        return m.group(1)
    if w.get("doi"):
        return w["doi"].replace("https://doi.org/", "")
    return (ids.get("openalex") or w.get("id") or "?").replace("https://openalex.org/", "")


def abstract_first_sentence(w: dict) -> str:
    if w.get("abstract_text"):
        s = re.split(r"(?<=[.!?])\s+", w["abstract_text"].strip(), maxsplit=1)[0]
        return s[:220].replace("|", "/")
    inv = w.get("abstract_inverted_index")
    if not inv:
        return ""
    pos = {}
    for tok, idxs in inv.items():
        for i in idxs:
            pos[i] = tok
    text = " ".join(pos[i] for i in sorted(pos))
    s = re.split(r"(?<=[.!?])\s+", text.strip(), maxsplit=1)[0]
    return s[:220].replace("|", "/")


def venue(w: dict) -> str:
    src = (w.get("primary_location") or {}).get("source") or {}
    return (src.get("display_name") or "").replace("|", "/")


ARXIV_API = "http://export.arxiv.org/api/query"


def fetch_arxiv_recent(query: str, start: str, limit: int) -> list[dict]:
    """arXiv API, newest first, stop when submitted date < start. Query words are ANDed over all fields;
    quoted phrases are kept as phrases."""
    import xml.etree.ElementTree as ET
    terms = re.findall(r'"[^"]+"|\S+', query)
    q = " AND ".join(f"all:{t}" for t in terms)
    ns = {"a": "http://www.w3.org/2005/Atom"}
    rows, got = [], 0
    while got < limit:
        params = {"search_query": q, "sortBy": "submittedDate", "sortOrder": "descending",
                  "start": got, "max_results": min(100, limit - got)}
        url = ARXIV_API + "?" + urllib.parse.urlencode(params)
        for attempt in range(5):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "idea-forecast/1.0"}), timeout=60) as r:
                    xml = r.read().decode("utf-8")
                break
            except Exception as exc:  # noqa: BLE001
                if attempt == 4:
                    raise SystemExit(f"[fail] arXiv API failed: {exc}")
                time.sleep(3 * (attempt + 1))
        entries = ET.fromstring(xml).findall("a:entry", ns)
        if not entries:
            break
        stop = False
        for e in entries:
            date = (e.findtext("a:published", default="", namespaces=ns) or "")[:10]
            if date < start:
                stop = True
                break
            aid = re.sub(r"v\d+$", "", (e.findtext("a:id", default="", namespaces=ns) or "").rsplit("/", 1)[-1])
            rows.append({"id": aid, "title": " ".join((e.findtext("a:title", default="", namespaces=ns) or "").split()),
                         "publication_year": date[:4], "publication_date": date, "cited_by_count": "",
                         "primary_location": {"landing_page_url": f"https://arxiv.org/abs/{aid}", "source": {"display_name": "arXiv"}},
                         "abstract_text": " ".join((e.findtext("a:summary", default="", namespaces=ns) or "").split())})
        got += len(entries)
        if stop or len(entries) < 100:
            break
        time.sleep(3)  # arXiv asks for >= 3 s between requests
    return rows


def write_table(path: Path, title: str, rows: list[dict]):
    lines = [f"# {title}", "", f"生成 {dt.datetime.now():%Y-%m-%d %H:%M}；{len(rows)} 篇；来源 OpenAlex（骨干）/ arXiv API（近期）。"
             "每行只是摘要级线索，进卡片前必须读正文。", "",
             "| # | id | title | year | citations | venue | date | url | abstract (first sentence) | 读了正文? |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for i, w in enumerate(rows, 1):
        url = (w.get("primary_location") or {}).get("landing_page_url") or w.get("doi") or w.get("id") or ""
        lines.append(f"| {i} | {work_id(w)} | {(w.get('title') or '').replace('|', '/')} | {w.get('publication_year') or ''} | "
                     f"{w.get('cited_by_count') or 0} | {venue(w)} | {w.get('publication_date') or ''} | {url} | "
                     f"{abstract_first_sentence(w)} | |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[ok] {len(rows)} rows -> {path}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True, help="idea-stage directory")
    ap.add_argument("--query", action="append", required=True, help="search query; repeat for several")
    ap.add_argument("--top", type=int, default=0, help="collect the N most-cited papers (0 = skip)")
    ap.add_argument("--since", type=int, default=2018, help="earliest publication year for the cited backbone")
    ap.add_argument("--recent-days", type=int, default=0, help="collect papers published in the last N days (0 = skip)")
    ap.add_argument("--pool", type=int, default=200, help="candidates fetched per query before merging")
    ap.add_argument("--slug", default=None, help="file name slug; default derived from the first query")
    ap.add_argument("--keep-surveys", action="store_true", help="keep titles containing survey/review/overview (dropped by default)")
    a = ap.parse_args(argv)
    if not a.top and not a.recent_days:
        ap.error("give --top and/or --recent-days")
    out_dir = Path(a.project) / "terrain"
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = a.slug or re.sub(r"[^a-z0-9]+", "-", a.query[0].lower()).strip("-")[:40]
    stamp = dt.datetime.now().strftime("%Y%m%d")

    if a.top:
        merged: dict[str, dict] = {}
        for q in a.query:
            for w in fetch(q, a.pool, f"publication_year:>{a.since - 1},cited_by_count:>0", "cited_by_count:desc"):
                merged.setdefault(w["id"], w)
        if not merged:
            raise SystemExit("[fail] no works returned for the backbone query")
        rows = sorted(merged.values(), key=lambda w: w.get("cited_by_count") or 0, reverse=True)
        if not a.keep_surveys:
            rows = [w for w in rows if not re.search(r"(survey|review|overview|roadmap|perspective)", w.get("title") or "", re.I)]
        rows = rows[: a.top]
        write_table(out_dir / f"backbone_{slug}_{stamp}.md",
                    f"引用骨干：{' / '.join(a.query)}（{a.since} 起，前 {a.top}）", rows)

    if a.recent_days:
        start = (dt.date.today() - dt.timedelta(days=a.recent_days)).isoformat()
        merged = {}
        for q in a.query:
            for w in fetch_arxiv_recent(q, start, a.pool):
                merged.setdefault(w["id"], w)
        if not merged:
            raise SystemExit("[fail] no arXiv papers returned for the recent query")
        rows = sorted(merged.values(), key=lambda w: w.get("publication_date") or "", reverse=True)
        write_table(out_dir / f"recent_{slug}_{stamp}.md",
                    f"最近 {a.recent_days} 天：{' / '.join(a.query)}（{start} 起）", rows)


if __name__ == "__main__":
    main()
