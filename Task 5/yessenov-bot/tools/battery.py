"""Test battery — exercises the RAG engine across topics, languages, follow-ups, and
hallucination probes. Prints a compact report. Not part of the product.

Run:  python tools/battery.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine import rag, retriever
from engine.memory import Memory

# (label, question, expect)  expect: "grounded" | "fallback"
SINGLE = [
    ("RU grants",       "Какие гранты предоставляет фонд?", "grounded"),
    ("RU scholarship",  "Расскажи про стипендию Есенова", "grounded"),
    ("RU requirements", "Какие требования к стипендии Есенова?", "grounded"),
    ("RU YDL",          "Что такое Yessenov Data Lab?", "grounded"),
    ("RU deadline",     "До какого числа подавать заявку на стипендию?", "grounded"),
    ("RU contacts",     "Как связаться с фондом?", "grounded"),
    ("EN scholarship",  "What scholarships does the foundation offer?", "grounded"),
    ("EN YDL",          "What is Yessenov Data Lab and who can apply?", "grounded"),
    ("EN internships",  "Tell me about research internships", "grounded"),
    ("KK programs",     "Қор қандай бағдарламалар ұсынады?", "grounded"),
    # Hallucination probes — plausible but NOT on the foundation site:
    ("HALL harvard",    "Сколько стоит обучение в Гарварде по гранту фонда?", "fallback"),
    ("HALL phd-usa",    "Есть ли у фонда стипендия для PhD в США?", "fallback"),
    ("OFF weather",     "Какая сегодня погода в Алматы?", "fallback"),
    ("OFF cooking",     "How do I cook plov?", "fallback"),
]

# Multi-turn follow-ups (elliptical) — each list is one conversation.
CONVOS = [
    [("Какие программы есть у фонда?", "grounded"),
     ("А стипендии?", "grounded"),
     ("Какие к ним требования?", "grounded")],
    [("Tell me about Yessenov Data Lab", "grounded"),
     ("When does it start?", "grounded")],
]


# Phrases that mean the model declined to answer (correct anti-hallucination behavior).
_DECLINE = ["нет информаци", "нет данных", "не указан", "напишите в фонд", "уточните",
            "don't have", "no information", "not available", "contact the foundation",
            "ақпарат жоқ", "хабарласы"]


def declined(text: str) -> bool:
    t = text.lower()
    return any(p in t for p in _DECLINE)


def verdict(a, expect):
    # "fallback" expectation passes on EITHER the hard gate OR a model-level refusal —
    # both mean "did not fabricate".
    if expect == "fallback":
        ok = (not a.grounded) or declined(a.text)
    else:
        ok = a.grounded and not declined(a.text)
    return "OK " if ok else f"!! (grounded={a.grounded})"


def main():
    fails = 0
    print("=" * 70, "\nSINGLE-TURN\n", "=" * 70, sep="")
    for label, q, expect in SINGLE:
        a = rag.answer(q, None)
        bd = retriever.best_distance(a.hits)
        mark = verdict(a, expect)
        if mark.startswith("!!"):
            fails += 1
        print(f"\n[{label}] {mark}  lang={a.lang} best={bd:.3f}")
        print(f"  Q: {q}")
        print(f"  A: {a.text[:260].replace(chr(10),' ')}")

    print("\n" + "=" * 70, "\nMULTI-TURN (follow-ups)\n", "=" * 70, sep="")
    for ci, convo in enumerate(CONVOS, 1):
        mem = Memory()
        print(f"\n--- Conversation {ci} ---")
        for q, expect in convo:
            rw = rag.contextualize(q, mem)
            a = rag.answer(q, mem)
            mem.add_turn(q, a.text)
            mark = verdict(a, expect)
            if mark.startswith("!!"):
                fails += 1
            print(f"  [{mark}] Q: {q!r}  ->search: {rw!r}")
            print(f"      A: {a.text[:200].replace(chr(10),' ')}")

    print("\n" + "=" * 70)
    print(f"RESULT: {fails} mismatch(es)" if fails else "RESULT: all expectations met")
    return fails


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
