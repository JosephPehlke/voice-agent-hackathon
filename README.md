# Voice Agent Hackathon

Submit your voice agent here. Every agent is put through the same simulated calls, scored by an LLM judge and by
human judges, and ranked on the **[leaderboard](LEADERBOARD.md)** (also published as a web page from `docs/`).

## How ranking works

| Part | Weight | How it's measured |
|---|---|---|
| Automated evals | 60% | Claude plays a caller through each scenario in `scenarios/`, then a Claude judge scores the transcript on task success, accuracy, conversation quality and robustness. Reply latency is measured on every turn. |
| Human judges | 40% | Judges score voice UX, creativity, technical depth and demo in `judging/judge_scores.csv`. |

Weights, criteria and models are all in [`config.yaml`](config.yaml). Teams with only one score source so far are
ranked on what they have and marked as partial.

## For teams

See [`submissions/README.md`](submissions/README.md): copy `submissions/example-team/`, point `endpoint` at your agent's
text-mode HTTP endpoint, and open a PR.

## For organizers

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...

python -m evals.validate                 # check every agent.yaml
python -m evals.run                      # evaluate all teams (or --team <slug>)
python -m evals.run --mock               # offline dry run, no API key needed
python -m evals.leaderboard              # rebuild LEADERBOARD.md and docs/index.html
```

Try it end to end with the bundled reference agent: `python examples/echo_agent.py &` then
`python -m evals.run --team example-team --mock && python -m evals.leaderboard`.

### Automation

- `.github/workflows/validate.yml` checks submissions on every PR.
- `.github/workflows/evaluate.yml` runs on merges to `main`: it evaluates only the teams whose `agent.yaml` changed
  (or everyone if scenarios/config/eval code changed), rebuilds the leaderboard and commits the results. It can also be
  run by hand from the Actions tab.

One-time setup:
1. Add an `ANTHROPIC_API_KEY` repository secret (Settings → Secrets and variables → Actions).
2. Turn on GitHub Pages from the `main` branch, `/docs` folder, to publish the leaderboard page.
3. If a team's endpoint needs a token, add it as a secret and expose it to the "Run evals" step under the name given in their `auth_env`.

## Layout

```
config.yaml              weights, criteria, models
submissions/<team>/      one agent.yaml per team
scenarios/*.yaml         simulated calls every agent goes through
judging/                 human judge rubric and scores
evals/                   runner, simulator + judge, leaderboard builder
results/auto/<team>.json transcripts, scores and judge rationales
LEADERBOARD.md, docs/    generated leaderboard
```
