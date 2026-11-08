"""Combine automated results and human judge scores into the ranked leaderboard.

Writes LEADERBOARD.md, docs/leaderboard.json and docs/index.html.
"""
from __future__ import annotations

import csv
import html
import json
import statistics
from datetime import datetime, timezone

from .common import JUDGE_CSV, RESULTS, ROOT, load_config, load_submissions


def judge_scores(criteria: list[str]) -> dict[str, dict]:
    by_team: dict[str, list[float]] = {}
    judges: dict[str, set] = {}
    if JUDGE_CSV.exists():
        for row in csv.DictReader(JUDGE_CSV.open()):
            team = (row.get("team") or "").strip()
            vals = [float(row[c]) for c in criteria if (row.get(c) or "").strip()]
            if team and vals:
                by_team.setdefault(team, []).extend(vals)
                judges.setdefault(team, set()).add(row.get("judge", "").strip())
    return {t: {"score": round(statistics.mean(v) * 10, 2), "judges": len(judges[t])} for t, v in by_team.items()}


def build_rows() -> list[dict]:
    cfg = load_config()
    w_auto, w_judge = cfg["weights"]["automated"], cfg["weights"]["judges"]
    subs = load_submissions()
    judged = judge_scores(cfg["judge_criteria"])
    autos = {f.stem: json.loads(f.read_text()) for f in RESULTS.glob("*.json")}

    rows = []
    for slug, sub in subs.items():
        a = autos.get(slug)
        j = judged.get(slug)
        auto_score = a["automated_score"] if a else None
        judge_score = j["score"] if j else None
        if auto_score is not None and judge_score is not None:
            final = w_auto * auto_score + w_judge * judge_score
        else:  # only one source so far: rank on what we have, flagged as partial
            final = auto_score if auto_score is not None else judge_score
        rows.append({
            "slug": slug,
            "team": sub.get("team", slug),
            "project": sub.get("project", ""),
            "repo": sub.get("repo", ""),
            "automated": auto_score,
            "judges": judge_score,
            "judge_count": j["judges"] if j else 0,
            "final": round(final, 2) if final is not None else None,
            "partial": auto_score is None or judge_score is None,
            "mock": bool(a and a.get("mock")),
            "median_latency_s": (round(statistics.median(s["median_latency_s"] for s in a["scenarios"]), 2)
                                 if a and a["scenarios"] else None),
            "scenarios": {s["scenario"]: s["score"] for s in a["scenarios"]} if a else {},
        })
    rows.sort(key=lambda r: (r["final"] is None, -(r["final"] or 0)))
    for i, r in enumerate(rows, 1):
        r["rank"] = i if r["final"] is not None else None
    return rows


def fmt(v, suffix=""):
    return "–" if v is None else f"{v:g}{suffix}"


def write_markdown(rows: list[dict], cfg: dict, now: str) -> None:
    w = cfg["weights"]
    lines = [
        "# Leaderboard", "",
        f"_Updated {now}. Final = {w['automated']:g} × automated + {w['judges']:g} × judges. "
        "`*` = partial (only one score source so far)._", "",
        "| Rank | Team | Project | Final | Automated | Judges | Median latency |",
        "|---:|---|---|---:|---:|---:|---:|",
    ]
    for r in rows:
        team = f"[{r['team']}]({r['repo']})" if r["repo"] else r["team"]
        final = fmt(r["final"]) + ("*" if r["partial"] and r["final"] is not None else "")
        judges = fmt(r["judges"]) + (f" ({r['judge_count']})" if r["judge_count"] else "")
        lines.append(f"| {fmt(r['rank'])} | {team} | {r['project']} | **{final}** | {fmt(r['automated'])} "
                     f"| {judges} | {fmt(r['median_latency_s'], 's')} |")
    lines += ["", "Per-scenario transcripts and judge rationales live in `results/auto/<team>.json`.", ""]
    (ROOT / "LEADERBOARD.md").write_text("\n".join(lines))


HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Voice Agent Leaderboard</title>
<style>
:root{{--bg:#fafaf9;--fg:#1c1917;--muted:#78716c;--card:#fff;--line:#e7e5e4;--accent:#4f46e5;--gold:#ca8a04}}
@media (prefers-color-scheme:dark){{:root{{--bg:#0c0a09;--fg:#f5f5f4;--muted:#a8a29e;--card:#1c1917;--line:#292524;--accent:#818cf8;--gold:#facc15}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,sans-serif}}
main{{max-width:960px;margin:0 auto;padding:32px 16px}}h1{{margin:0 0 4px;font-size:28px}}p.sub{{color:var(--muted);margin:0 0 24px}}
.wrap{{overflow-x:auto;background:var(--card);border:1px solid var(--line);border-radius:12px}}
table{{width:100%;border-collapse:collapse;min-width:620px}}th,td{{padding:12px 14px;text-align:left;border-bottom:1px solid var(--line)}}
th{{font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted)}}tr:last-child td{{border-bottom:0}}
td.n{{text-align:right;font-variant-numeric:tabular-nums}}td.rank{{font-weight:700;width:56px}}tr.top td.rank{{color:var(--gold)}}
.final{{font-weight:700;color:var(--accent)}}.proj{{color:var(--muted);font-size:13px}}a{{color:inherit}}
.tag{{font-size:11px;color:var(--muted);border:1px solid var(--line);border-radius:6px;padding:1px 6px;margin-left:6px}}
</style></head><body><main>
<h1>Voice Agent Leaderboard</h1>
<p class="sub">Updated {now} · Final = {wa:g} × automated evals + {wj:g} × judges</p>
<div class="wrap"><table><thead><tr><th>Rank</th><th>Team</th><th style="text-align:right">Final</th>
<th style="text-align:right">Automated</th><th style="text-align:right">Judges</th><th style="text-align:right">Latency</th></tr></thead>
<tbody>{rows}</tbody></table></div>
</main></body></html>
"""


def write_html(rows: list[dict], cfg: dict, now: str) -> None:
    out = []
    for r in rows:
        name = html.escape(r["team"])
        if r["repo"]:
            name = f'<a href="{html.escape(r["repo"])}">{name}</a>'
        tags = ('<span class="tag">partial</span>' if r["partial"] and r["final"] is not None else "") + \
               ('<span class="tag">mock</span>' if r["mock"] else "")
        out.append(
            f'<tr class="{"top" if r["rank"] == 1 else ""}"><td class="rank">{fmt(r["rank"])}</td>'
            f'<td>{name}{tags}<div class="proj">{html.escape(r["project"])}</div></td>'
            f'<td class="n final">{fmt(r["final"])}</td><td class="n">{fmt(r["automated"])}</td>'
            f'<td class="n">{fmt(r["judges"])}</td><td class="n">{fmt(r["median_latency_s"], "s")}</td></tr>')
    w = cfg["weights"]
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "docs" / "index.html").write_text(
        HTML.format(now=now, wa=w["automated"], wj=w["judges"], rows="\n".join(out)))
    (ROOT / "docs" / "leaderboard.json").write_text(json.dumps({"updated": now, "rows": rows}, indent=2) + "\n")


def main() -> None:
    cfg = load_config()
    rows = build_rows()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    write_markdown(rows, cfg, now)
    write_html(rows, cfg, now)
    print(f"Leaderboard written ({len(rows)} teams).")


if __name__ == "__main__":
    main()
