"""Claude-powered caller simulator and transcript judge.

Both have a `mock` variant so the whole pipeline can run offline (`--mock`) for testing.
"""
from __future__ import annotations

import anthropic
from pydantic import BaseModel, Field

FALLBACK = {"fallbacks": "default", "betas": ["server-side-fallback-2026-07-01"]}


def format_transcript(turns: list[dict]) -> str:
    return "\n".join(f"{t['role'].upper()}: {t['text']}" for t in turns)


# ---------------------------------------------------------------- caller simulator

class CallerTurn(BaseModel):
    message: str = Field(description="What the caller says next, as spoken words.")
    hang_up: bool = Field(description="True once the goal is done or clearly cannot be reached.")


SIM_SYSTEM = """You are role-playing a phone caller to test a voice AI agent.
Stay in character. Speak like a real person on the phone: short, natural sentences, no stage directions.
Pursue your goal; when it is achieved or clearly impossible, say goodbye and set hang_up to true.

Persona: {persona}
Goal: {goal}"""


class Simulator:
    def __init__(self, model: str):
        self.client = anthropic.Anthropic()
        self.model = model

    def next_turn(self, scenario: dict, turns: list[dict]) -> CallerTurn:
        prompt = (
            "Conversation so far (AGENT is the AI you are testing, CALLER is you):\n\n"
            f"{format_transcript(turns) or '(the agent has not spoken yet)'}\n\nWhat do you say next?"
        )
        resp = self.client.beta.messages.parse(
            model=self.model,
            max_tokens=2000,
            system=SIM_SYSTEM.format(**scenario),
            messages=[{"role": "user", "content": prompt}],
            output_config={"effort": "low"},
            output_format=CallerTurn,
            **FALLBACK,
        )
        if resp.parsed_output is None:
            return CallerTurn(message="Sorry, I have to go. Bye.", hang_up=True)
        return resp.parsed_output


class MockSimulator:
    def __init__(self, *_):
        pass

    def next_turn(self, scenario: dict, turns: list[dict]) -> CallerTurn:
        n = sum(t["role"] == "caller" for t in turns)
        lines = [f"Hi! {scenario['goal'].strip()}", "Okay, that works.", "Great, thanks. Bye!"]
        return CallerTurn(message=lines[min(n, 2)], hang_up=n >= 2)


# ---------------------------------------------------------------- judge

class Verdict(BaseModel):
    task_success: int = Field(ge=1, le=10, description="Did the caller's goal get achieved per the success criteria?")
    accuracy: int = Field(ge=1, le=10, description="Were the agent's statements correct and free of hallucination?")
    conversation_quality: int = Field(ge=1, le=10, description="Natural, concise, voice-appropriate phrasing and turn-taking.")
    robustness: int = Field(ge=1, le=10, description="Handling of corrections, ambiguity, off-topic or adversarial input.")
    rationale: str = Field(description="Two or three sentences justifying the scores.")


JUDGE_SYSTEM = """You are a strict, fair judge in a voice AI agent hackathon.
You score one call transcript between a simulated CALLER and the team's AGENT.
Judge only the AGENT. Score each criterion 1-10 where 5 is mediocre and 10 is flawless.
Replies are spoken aloud, so penalize long, list-heavy or markdown-formatted answers.
If the agent errored or went silent, score accordingly."""


class Judge:
    def __init__(self, model: str):
        self.client = anthropic.Anthropic()
        self.model = model

    def score(self, scenario: dict, turns: list[dict]) -> Verdict:
        criteria = "\n".join(f"- {c}" for c in scenario.get("success_criteria", []))
        prompt = (
            f"Scenario: {scenario['title']}\nCaller goal: {scenario['goal']}\n"
            f"Success criteria:\n{criteria}\n\nTranscript:\n{format_transcript(turns)}"
        )
        resp = self.client.beta.messages.parse(
            model=self.model,
            max_tokens=8000,
            system=JUDGE_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
            output_config={"effort": "high"},
            output_format=Verdict,
            **FALLBACK,
        )
        if resp.parsed_output is None:
            raise RuntimeError(f"judge returned no verdict (stop_reason={resp.stop_reason})")
        return resp.parsed_output


class MockJudge:
    def __init__(self, *_):
        pass

    def score(self, scenario: dict, turns: list[dict]) -> Verdict:
        agent_turns = [t for t in turns if t["role"] == "agent" and t["text"]]
        s = 7 if agent_turns else 1
        return Verdict(task_success=s, accuracy=s, conversation_quality=s, robustness=s,
                       rationale="Mock verdict (offline run).")
