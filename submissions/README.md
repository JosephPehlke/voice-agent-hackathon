# Submitting your agent

1. Copy `example-team/` to `submissions/<your-team-slug>/` (lowercase, dashes).
2. Fill in `agent.yaml`.
3. Open a pull request. CI validates the file; once merged, your agent is evaluated and lands on the leaderboard.

## The agent protocol

The evaluator talks to your agent in **text mode** over HTTP, one turn at a time, standing in for the
speech-to-text / text-to-speech layer. Expose the same brain your voice pipeline uses.

```
POST <endpoint>
Content-Type: application/json
Authorization: Bearer <token>        # only if auth_env is set

{"session_id": "example-team__book-dentist__a1b2", "message": "Hi, I'd like to book a cleaning."}
```

Respond with:

```json
{"reply": "Sure! What day works for you?", "end_call": false}
```

- `session_id` is stable for the whole conversation; keep your own state keyed on it.
- The first request of a call has `"message": ""` — reply with your greeting.
- Set `end_call: true` when your agent hangs up.
- Reply latency is measured on every turn and counts toward your score, so keep responses snappy.

`examples/echo_agent.py` is a minimal working reference.
