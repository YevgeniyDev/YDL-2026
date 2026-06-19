"""Compact conversation memory — the small-context strategy on the chat side.

We never send the full transcript to the (small-context) LLM. Instead we keep the last
N turns verbatim and fold everything older into a single rolling summary string.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import providers

KEEP_LAST_TURNS = 4  # a "turn" = one user+assistant exchange kept verbatim
SUMMARY_TRIGGER = 6  # summarize once history grows beyond this many turns


@dataclass
class Memory:
    summary: str = ""
    turns: list[tuple[str, str]] = field(default_factory=list)  # (user, assistant)

    def add_turn(self, user: str, assistant: str) -> None:
        self.turns.append((user, assistant))
        if len(self.turns) > SUMMARY_TRIGGER:
            self._compress()

    def _compress(self) -> None:
        """Fold the oldest turns (beyond KEEP_LAST_TURNS) into the rolling summary."""
        old = self.turns[:-KEEP_LAST_TURNS]
        self.turns = self.turns[-KEEP_LAST_TURNS:]
        convo = "\n".join(f"User: {u}\nAssistant: {a}" for u, a in old)
        prompt = [
            {
                "role": "system",
                "content": (
                    "Update the running summary of a support chat. Keep it under 120 words, "
                    "factual, capturing what the user wants and key info given. Same language "
                    "as the conversation."
                ),
            },
            {
                "role": "user",
                "content": f"Existing summary:\n{self.summary or '(none)'}\n\nNew exchanges:\n{convo}",
            },
        ]
        try:
            self.summary = providers.chat(prompt, temperature=0.1, max_tokens=200)
        except Exception:
            # If summarization fails, fall back to truncating older context silently.
            pass

    def as_context(self) -> str:
        """Render memory as a compact context block for the RAG prompt."""
        parts = []
        if self.summary:
            parts.append(f"Conversation summary so far: {self.summary}")
        for u, a in self.turns:
            parts.append(f"User: {u}\nAssistant: {a}")
        return "\n\n".join(parts)

    def full_transcript(self) -> str:
        """Whole conversation as plain text — used only for the email summary, not the LLM prompt."""
        parts = []
        if self.summary:
            parts.append(f"[earlier] {self.summary}")
        parts.extend(f"User: {u}\nAssistant: {a}" for u, a in self.turns)
        return "\n\n".join(parts)
