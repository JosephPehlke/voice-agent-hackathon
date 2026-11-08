"""Shared loading helpers."""
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SUBMISSIONS = ROOT / "submissions"
SCENARIOS = ROOT / "scenarios"
RESULTS = ROOT / "results" / "auto"
JUDGE_CSV = ROOT / "judging" / "judge_scores.csv"

REQUIRED_FIELDS = ("team", "project", "endpoint")


def load_config() -> dict:
    return yaml.safe_load((ROOT / "config.yaml").read_text())


def load_submissions() -> dict[str, dict]:
    """Return {team_slug: agent.yaml contents}."""
    subs = {}
    for f in sorted(SUBMISSIONS.glob("*/agent.yaml")):
        subs[f.parent.name] = yaml.safe_load(f.read_text()) or {}
    return subs


def load_scenarios() -> list[dict]:
    return [yaml.safe_load(f.read_text()) for f in sorted(SCENARIOS.glob("*.yaml"))]


def validate_submission(slug: str, data: dict) -> list[str]:
    errors = [f"missing `{k}`" for k in REQUIRED_FIELDS if not data.get(k)]
    ep = str(data.get("endpoint", ""))
    if ep and not ep.startswith(("http://", "https://")):
        errors.append("`endpoint` must be an http(s) URL")
    if slug != slug.lower() or " " in slug:
        errors.append("folder name must be lowercase with no spaces")
    return errors
