"""search_b.py -- run one search brief through an external CLI model (Searcher-B) and save the result as a
markdown file the judge can read. Model-agnostic: the command is configurable.

    python search_b.py --brief terrain/briefs/A1.md --name A1 --project <idea-stage>
    python search_b.py --prompt "..." --name quick --project <idea-stage> --cmd "gemini -p - -o {out}"

Command resolution (first hit wins):
    --cmd            explicit template; {out} is replaced by the output path; the prompt is sent on stdin
    $SEARCH_B_CMD    same template from the environment
    default          codex exec --skip-git-repo-check --ephemeral -s read-only -o {out} -   (OpenAI Codex CLI)
Each run of a 40-row brief takes 20-45 min and roughly 50-100k tokens on Codex; fail loud on non-zero exit
or empty output; on timeout kill the whole process tree (Windows: taskkill /T; POSIX: process group).

Output: <project>/terrain/searches/<name>_B_<UTC stamp>.md, plus one line appended to terrain/CLAIMS.md.
The brief is wrapped in a fixed instruction block that forces web search, one row per hit with id/link and one
verbatim English evidence sentence, read-depth flags, and explicit "NOT FOUND" rows.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import shlex
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

DEFAULT_CMD = "codex exec --skip-git-repo-check --ephemeral -s read-only -o {out} -"
HEADER = """You are Searcher-B in a retrieval-first research workflow. Use web search for every query below; do not answer from memory.
Rules:
1. For each atom and each query, report hits as a markdown table row:
   | atom | query | id or URL | title | year | venue/source | one verbatim English sentence from the abstract or body that shows the overlap | read depth (abstract / full text) |
2. Prefer arXiv ids (YYMM.NNNNN). For blogs/docs/repos give the URL and date.
3. If a query returns nothing relevant, write a row with "NOT FOUND" in the id column. Never invent papers.
4. Cover all vocabulary axes the brief asks for (own field, adjacent fields, engineering/product, classic pre-2018).
5. After the table, add a section "## Closest prior work per atom" listing at most 3 items per atom with the precise delta to the atom in one sentence each. No opinions on novelty; the judgment is made elsewhere.
6. Finish with "## Queries run" listing every query string you actually issued.
"""


def build_cmd(template: str, out: Path) -> list[str]:
    parts = shlex.split(template.replace("{out}", str(out)), posix=(os.name != "nt"))
    if os.name == "nt" and parts and parts[0].lower().endswith(".cmd"):
        parts = ["cmd", "/c"] + parts
    return parts


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--brief", help="markdown file with atoms and the query matrix")
    ap.add_argument("--prompt", help="inline brief instead of --brief")
    ap.add_argument("--name", required=True, help="short slug for the output file")
    ap.add_argument("--project", required=True, help="idea-stage directory")
    ap.add_argument("--cmd", default=os.environ.get("SEARCH_B_CMD", DEFAULT_CMD),
                    help="command template; {out} = output path; prompt on stdin")
    ap.add_argument("--timeout", type=int, default=2700, help="seconds")
    a = ap.parse_args(argv)
    if bool(a.brief) == bool(a.prompt):
        ap.error("give exactly one of --brief / --prompt")
    body = Path(a.brief).read_text(encoding="utf-8") if a.brief else a.prompt
    prompt = HEADER + "\n## Brief\n" + body + "\n"
    out_dir = Path(a.project) / "terrain" / "searches"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = out_dir / f"{a.name}_B_{stamp}.md"
    cmd = build_cmd(a.cmd, out)
    print(f"[search_b] {a.name} -> {out}\n  cmd: {' '.join(cmd)}")
    popen_kw = {}
    if os.name != "nt":
        popen_kw["start_new_session"] = True
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, encoding="utf-8", errors="replace", **popen_kw)
    try:
        out_txt, err_txt = proc.communicate(prompt, timeout=a.timeout)
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)
        else:
            import signal
            os.killpg(proc.pid, signal.SIGKILL)
        raise SystemExit(f"[fail] searcher-B timed out after {a.timeout}s; process tree killed. Partial output (if any): {out}")
    if proc.returncode != 0:
        sys.stderr.write((out_txt or "")[-3000:] + (err_txt or "")[-3000:])
        raise SystemExit(f"[fail] searcher-B exit {proc.returncode}")
    if not out.exists() or out.stat().st_size < 50:
        # some CLIs only print to stdout; keep that as the result
        if out_txt and len(out_txt.strip()) > 50:
            out.write_text(out_txt, encoding="utf-8")
        else:
            sys.stderr.write((out_txt or "")[-3000:])
            raise SystemExit("[fail] empty output from searcher-B")
    text = out.read_text(encoding="utf-8", errors="replace")
    out.write_text(f"<!-- searcher-B cmd: {a.cmd}; brief: {a.brief or 'inline'}; {stamp} -->\n" + text, encoding="utf-8")
    log = Path(a.project) / "terrain" / "CLAIMS.md"
    with open(log, "a", encoding="utf-8") as fh:
        fh.write(f"\n- [{stamp}] Searcher-B brief `{a.name}` -> `terrain/searches/{out.name}` ({len(text)} chars)\n")
    print(f"[ok] {len(text)} chars written")


if __name__ == "__main__":
    main()
