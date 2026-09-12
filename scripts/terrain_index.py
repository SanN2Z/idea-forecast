"""terrain_index.py -- build and query the local literature terrain of a project.

Scans every .md/.txt/.json under <project> for arXiv ids (YYMM.NNNNN) and http(s) links,
records where each appears and one line of context, and writes
    <project>/terrain/index.json   machine-readable
    <project>/terrain/INDEX.md     human-readable, sorted by number of mentions
Query mode greps ids and free text across the index and the cards directory.

    python terrain_index.py --project <idea-stage> --build
    python terrain_index.py --project <idea-stage> --query 2605.26731
    python terrain_index.py --project <idea-stage> --query "marginal contribution"

Gate 0 (F0) of the idea-forecast skill: nothing already cited in the project may later be presented
as a new finding, and nothing found here needs to be searched again.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ARXIV = re.compile(r"(?<![\d.])(\d{4}\.\d{4,5})(?:v\d+)?(?![\d.])")
URL = re.compile(r"https?://[^\s)\]>\"']+")
SKIP_DIRS = {"terrain", "node_modules", ".git", "__pycache__", "recovery"}
EXTS = {".md", ".txt", ".json"}


def _context(line: str, m_start: int, width: int = 90) -> str:
    lo = max(0, m_start - width // 2)
    return line[lo:lo + width].strip().replace("|", "\\|")


def build(project: Path) -> dict:
    ids: dict[str, dict] = defaultdict(lambda: {"files": {}, "n": 0})
    urls: dict[str, dict] = defaultdict(lambda: {"files": {}, "n": 0})
    n_files = 0
    for path in sorted(project.rglob("*")):
        if path.suffix.lower() not in EXTS or not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(project).parts):
            continue
        n_files += 1
        rel = str(path.relative_to(project)).replace("\\", "/")
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            raise RuntimeError(f"[fail] cannot read {path}: {exc}") from exc
        for lineno, line in enumerate(text.splitlines(), 1):
            for m in ARXIV.finditer(line):
                aid = m.group(1)
                yy, mm = int(aid[:2]), int(aid[2:4])
                if not (7 <= yy <= 30 and 1 <= mm <= 12):
                    continue
                rec = ids[aid]
                rec["n"] += 1
                rec["files"].setdefault(rel, {"line": lineno, "ctx": _context(line, m.start())})
            for m in URL.finditer(line):
                u = m.group(0).rstrip(".,;:")
                if "arxiv.org" in u:
                    continue
                rec = urls[u]
                rec["n"] += 1
                rec["files"].setdefault(rel, {"line": lineno, "ctx": _context(line, m.start())})
    out = {"project": str(project), "n_files": n_files, "arxiv": dict(ids), "urls": dict(urls)}
    tdir = project / "terrain"
    tdir.mkdir(exist_ok=True)
    (tdir / "index.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = [f"# Terrain index for `{project}`", "",
             f"{n_files} files scanned; {len(ids)} arXiv ids; {len(urls)} other links. "
             "Rebuild with `terrain_index.py --build`. Anything listed here is already known to this project.", "",
             "| arXiv | mentions | files | first context |", "|---|---|---|---|"]
    for aid, rec in sorted(ids.items(), key=lambda kv: (-kv[1]["n"], kv[0])):
        first = next(iter(rec["files"].values()))
        lines.append(f"| {aid} | {rec['n']} | {len(rec['files'])} | {first['ctx']} |")
    lines += ["", "| link | mentions | first file |", "|---|---|---|"]
    for u, rec in sorted(urls.items(), key=lambda kv: (-kv[1]["n"], kv[0]))[:300]:
        lines.append(f"| {u} | {rec['n']} | {next(iter(rec['files']))} |")
    (tdir / "INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[ok] {n_files} files, {len(ids)} arXiv ids, {len(urls)} links -> {tdir / 'INDEX.md'}")
    return out


def query(project: Path, q: str) -> None:
    idx_path = project / "terrain" / "index.json"
    if not idx_path.exists():
        raise SystemExit("[fail] no index; run --build first")
    idx = json.loads(idx_path.read_text(encoding="utf-8"))
    ql = q.lower()
    hits = 0
    if ARXIV.fullmatch(q):
        rec = idx["arxiv"].get(q)
        if rec:
            hits += 1
            print(f"{q}: {rec['n']} mention(s)")
            for f, meta in rec["files"].items():
                print(f"  {f}:{meta['line']}  {meta['ctx']}")
    # free-text over contexts and over cards
    for aid, rec in idx["arxiv"].items():
        for f, meta in rec["files"].items():
            if ql in meta["ctx"].lower():
                hits += 1
                print(f"{aid}  {f}:{meta['line']}  {meta['ctx']}")
    cards = project / "terrain" / "cards"
    if cards.exists():
        for card in sorted(cards.glob("*.md")):
            text = card.read_text(encoding="utf-8", errors="replace")
            if ql in text.lower():
                hits += 1
                print(f"card {card.name}")
    # also grep raw files for the phrase (contexts are only 90 chars wide)
    for path in sorted(project.rglob("*.md")):
        if any(part in SKIP_DIRS for part in path.relative_to(project).parts):
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if ql in line.lower():
                hits += 1
                print(f"{path.relative_to(project)}:{lineno}  {line.strip()[:160]}")
                if hits > 60:
                    print("... (truncated)")
                    return
    print(f"[{hits} hit(s)]" if hits else "[0 hits] -- not known locally; go to gate 2")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True, help="idea-stage directory")
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--query", default=None)
    a = ap.parse_args(argv)
    project = Path(a.project)
    if not project.is_dir():
        raise SystemExit(f"[fail] not a directory: {project}")
    if a.build:
        build(project)
    if a.query:
        query(project, a.query)
    if not a.build and not a.query:
        ap.error("give --build and/or --query")


if __name__ == "__main__":
    main()
