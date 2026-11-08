"""Run every scenario against every (or selected) agent and save scored results.

    python -m evals.run                     # all teams
    python -m evals.run --team my-team      # one team
    python -m evals.run --mock              # offline: scripted caller + dummy judge, no API key needed
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import uuid
from datetime import datetime, timezone

from .agent_client import AgentClient
from .common import RESULTS, load_config, load_scenarios, load_submissions, validate_submission
from .llm import Judge, MockJudge, MockSimulator, Simulator


def run_call(agent: AgentClient, sim, scenario: dict, slug: str, max_turns: int) -> dict:
    session = f"{slug}__{scenario['id']}__{uuid.uuid4().hex[:6]}"
    turns, latencies, errors = [], [], []

    def agent_says(text: str) -> bool:
        t = agent.send(session, text)
        latencies.append(t.latency_s)
        if t.error:
            errors.append(t.error)
        turns.append({"role": "agent", "text": t.reply, "latency_s": round(t.latency_s, 3)})
        return t.end_call

    ended = agent_says("")  # greeting
    for _ in range(max_turns):
        if ended:
            break
        caller = sim.next_turn(scenario, turns)
        turns.append({"role": "caller", "text": caller.message})
        ended = agent_says(caller.message)
        if caller.hang_up:
            break
    return {"session": session, "turns": turns, "latencies": latencies, "errors": errors}


def latency_score(median_s: float, cfg: dict) -> float:
    great, poor = cfg["latency_seconds"]["great"], cfg["latency_seconds"]["poor"]
    if median_s <= great:
        return 10.0
    if median_s >= poor:
        return 0.0
    return round(10 * (poor - median_s) / (poor - great), 2)


def scenario_score(verdict: dict, lat: float, cfg: dict) -> float:
    """Weighted 0-100 score for one scenario."""
    w = cfg["automated_criteria"]
    parts = {**{k: verdict[k] for k in w if k != "latency"}, "latency": lat}
    return round(sum(parts[k] * w[k] for k in w) * 10, 2)


def evaluate_team(slug: str, sub: dict, scenarios: list[dict], cfg: dict, mock: bool) -> dict:
    agent = AgentClient(sub["endpoint"], sub.get("auth_env", ""), cfg["request_timeout"])
    sim = (MockSimulator if mock else Simulator)(cfg["models"]["simulator"])
    judge = (MockJudge if mock else Judge)(cfg["models"]["judge"])

    results = []
    for sc in scenarios:
        if sc.get("applies_to") and slug not in sc["applies_to"]:
            continue
        print(f"  - {sc['id']}", flush=True)
        call = run_call(agent, sim, sc, slug, cfg["max_turns"])
        verdict = judge.score(sc, call["turns"]).model_dump()
        med = statistics.median(call["latencies"]) if call["latencies"] else 99.0
        lat = latency_score(med, cfg)
        results.append({
            "scenario": sc["id"],
            "verdict": verdict,
            "median_latency_s": round(med, 3),
            "latency_score": lat,
            "score": scenario_score(verdict, lat, cfg),
            "errors": call["errors"],
            "transcript": call["turns"],
        })

    overall = round(statistics.mean(r["score"] for r in results), 2) if results else 0.0
    return {
        "team": sub["team"],
        "slug": slug,
        "evaluated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mock": mock,
        "automated_score": overall,
        "scenarios": results,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--team", action="append", help="team slug (repeatable); default all")
    ap.add_argument("--mock", action="store_true", help="offline run without calling Claude")
    args = ap.parse_args()

    cfg, scenarios, subs = load_config(), load_scenarios(), load_submissions()
    targets = args.team or list(subs)
    RESULTS.mkdir(parents=True, exist_ok=True)

    failed = 0
    for slug in targets:
        sub = subs.get(slug)
        if sub is None:
            print(f"unknown team: {slug}", file=sys.stderr)
            failed += 1
            continue
        if errs := validate_submission(slug, sub):
            print(f"skipping {slug}: {'; '.join(errs)}", file=sys.stderr)
            failed += 1
            continue
        print(f"Evaluating {slug} ...", flush=True)
        res = evaluate_team(slug, sub, scenarios, cfg, args.mock)
        (RESULTS / f"{slug}.json").write_text(json.dumps(res, indent=2) + "\n")
        print(f"  => automated score {res['automated_score']}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
