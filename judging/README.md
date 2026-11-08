# Human judging

Each judge adds one row per team to `judge_scores.csv` (by PR or straight on `main`):

```
judge,team,voice_ux,creativity,technical_depth,demo,notes
joseph,example-team,7,8,6,9,"Great barge-in handling"
```

- `team` is the submission folder name (e.g. `example-team`).
- Each criterion is scored 1-10:
  - **voice_ux**: does it feel good to talk to? Latency, interruptions, voice choice, turn-taking.
  - **creativity**: is the idea novel and well suited to voice?
  - **technical_depth**: tools, integrations, real-time handling, engineering quality.
  - **demo**: how well the live demo / video lands.
- A team's judge score is the mean over all criteria and judges, scaled to 0-100.

Criteria names come from `judge_criteria` in `config.yaml`; change both together.
