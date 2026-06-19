"""RAG orchestration: retrieve -> grounded prompt -> answer, or a safe fallback.

Anti-hallucination is enforced two ways:
  1. A hard relevance gate: if the nearest chunk is farther than RELEVANCE_MAX_DISTANCE,
     we never call the LLM with junk context — we return the fixed "contact a human" reply.
  2. A strict system prompt: answer ONLY from the provided context; if it's not there, say
     so plainly. Temperature is low.
The bot always answers in the user's language.
"""
from __future__ import annotations

import datetime
import re
from dataclasses import dataclass

from . import config, providers, retriever
from .memory import Memory
from .store import Hit

try:
    from langdetect import detect as _detect_lang
except Exception:
    _detect_lang = None

SUPPORTED = {"ru", "en", "kk"}

# Localized fallback shown when we have no good grounding for the question.
_FALLBACK = {
    "ru": (
        "К сожалению, у меня нет точной информации по этому вопросу. "
        "Рекомендую написать в фонд на {email}{phone} — вам ответит сотрудник."
    ),
    "en": (
        "Sorry, I don't have reliable information on that. "
        "I'd recommend contacting the foundation at {email}{phone} — a staff member will help you."
    ),
    "kk": (
        "Өкінішке орай, бұл сұрақ бойынша нақты ақпаратым жоқ. "
        "Қорға {email}{phone} арқылы хабарласуыңызды ұсынамын — маман сізге жауап береді."
    ),
}

_PERSONA = {
    "ru": "Ты — официальный, но дружелюбный консультант фонда «Yessenov Foundation».",
    "en": "You are the official yet friendly consultant of the Yessenov Foundation.",
    "kk": "Сен — «Yessenov Foundation» қорының ресми әрі сыпайы кеңесшісісің.",
}

_RULES = {
    "ru": (
        "Отвечай ТОЛЬКО на основе приведённого ниже КОНТЕКСТА. "
        "Если ответа в контексте нет — честно скажи, что не знаешь. "
        "Не выдумывай факты, даты, суммы или ссылки. Отвечай на русском языке. Будь кратким. "
        "Если пользователь хочет оставить заявку, получить консультацию специалиста или ты "
        "не можешь полностью помочь — вежливо предложи передать обращение менеджеру фонда и "
        "попроси указать имя и контакт (email или телефон)."
    ),
    "en": (
        "Answer ONLY using the CONTEXT below. "
        "If the answer is not in the context, honestly say you don't know. "
        "Never invent facts, dates, amounts or links. Answer in English. Be concise. "
        "If the user wants to leave a request, get a specialist consultation, or you cannot "
        "fully help — politely offer to forward their inquiry to a foundation manager and ask "
        "for their name and contact (email or phone)."
    ),
    "kk": (
        "Тек төмендегі МӘТІНМӘН (контекст) негізінде жауап бер. "
        "Егер жауап контексте болмаса — білмейтініңді шынайы айт. "
        "Дерек, күн, сома немесе сілтеме ойдан шығарма. Қазақ тілінде жауап бер. Қысқа бол. "
        "Егер пайдаланушы өтініш қалдырғысы келсе, маманның кеңесін алғысы келсе немесе сен "
        "толық көмектесе алмасаң — өтінішті қор менеджеріне жеткізуді сыпайы ұсынып, аты-жөні "
        "мен байланысын (email немесе телефон) сұра."
    ),
}

# Date-awareness so the bot can reason about which cycle is current / passed / upcoming.
_DATE_NOTE = {
    "ru": "Сегодня {date}. В контексте могут быть даты разных лет. Всегда указывай, к какому "
          "году относится дедлайн; если он уже прошёл относительно сегодняшней даты — прямо "
          "скажи об этом. Даты приёма на следующий год обычно публикуются на сайте фонда в "
          "январе–феврале — если их ещё нет, так и скажи и предложи следить за сайтом.",
    "en": "Today is {date}. The context may contain dates from different years. Always state which "
          "year a deadline belongs to; if it has already passed relative to today, say so plainly. "
          "Dates for next year's cycle are usually published on the foundation site in "
          "January–February — if they aren't available yet, say so and suggest watching the site.",
    "kk": "Бүгін {date}. Контексте әртүрлі жылдардың күндері болуы мүмкін. Дедлайн қай жылға "
          "қатысты екенін әрқашан көрсет; егер ол бүгінгі күнге қарай өтіп кеткен болса — оны "
          "ашық айт. Келесі жылғы қабылдау күндері әдетте қаңтар–ақпанда сайтта жарияланады — "
          "егер әлі жоқ болса, солай деп айт та, сайтты қадағалауды ұсын.",
}


def _date_note(lang: str) -> str:
    today = datetime.date.today().strftime("%d.%m.%Y")
    return _DATE_NOTE[lang].format(date=today)


# Warm confirmation shown once the user shares their contact — the email goes to the manager.
_LEAD_THANKS = {
    "ru": "Спасибо! Я передал ваше обращение менеджеру фонда — с вами свяжутся по указанным "
          "контактам в ближайшее время. Если есть ещё вопросы, я с радостью помогу.",
    "en": "Thank you! I've forwarded your request to a foundation manager — they'll get in touch "
          "using the contact details you shared. If you have any more questions, I'm happy to help.",
    "kk": "Рахмет! Өтінішіңізді қор менеджеріне жеткіздім — көрсетілген байланыс арқылы сізбен "
          "жақын арада хабарласады. Қосымша сұрақтарыңыз болса, көмектесуге дайынмын.",
}

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"\+?\d[\d\s\-()]{7,}\d")


def extract_contact(text: str) -> str | None:
    """Return an email or phone number found in the text, else None.

    This is the (deterministic) trigger for the lead email: the moment the user shares a
    contact, we treat it as a conscious request to be reached by a manager.
    """
    m = _EMAIL_RE.search(text)
    if m:
        return m.group(0)
    for m in _PHONE_RE.finditer(text):
        digits = re.sub(r"\D", "", m.group(0))
        if 9 <= len(digits) <= 15:  # plausible phone number length
            return m.group(0).strip()
    return None


@dataclass
class Answer:
    text: str
    hits: list[Hit]
    grounded: bool  # False when the fallback was returned
    lang: str
    lead: str | None = None  # contact the user supplied → triggers the manager email


# Characters unique to the Kazakh Cyrillic alphabet — langdetect has no Kazakh model and
# misreads it as Russian, so we check these first.
_KK_CHARS = set("әғқңөұүһі")


def detect_lang(text: str) -> str:
    low = text.lower()
    if any(ch in _KK_CHARS for ch in low):
        return "kk"
    if _detect_lang:
        try:
            code = _detect_lang(text)
            code = "kk" if code == "kz" else code
            if code in SUPPORTED:
                return code
        except Exception:
            pass
    return "ru"  # default to Russian (primary audience) when unsure


_PHONE_LABEL = {"ru": "тел.", "kk": "тел.", "en": "tel."}


def _contact_suffix(lang: str) -> tuple[str, str]:
    email = config.CONTACT_EMAIL
    phone = f", {_PHONE_LABEL.get(lang, 'tel.')} {config.CONTACT_PHONE}" if config.CONTACT_PHONE else ""
    return email, phone


def _build_context(hits: list[Hit]) -> str:
    blocks = []
    for i, h in enumerate(hits, 1):
        blocks.append(f"[Источник {i}] ({h.source_url})\n{h.chunk_text}")
    return "\n\n".join(blocks)


def contextualize(question: str, memory: Memory | None) -> str:
    """Rewrite an elliptical follow-up ("А стипендии?") into a standalone search query.

    Short questions embed poorly and let noise outrank the right pages. When there's prior
    conversation, we fold the topic back in before retrieval. The original question is still
    what the user sees answered — this only improves what we *search* for.
    """
    if not memory or not memory.turns:
        return question
    history = memory.as_context()
    prompt = [
        {
            "role": "system",
            "content": (
                "Rewrite the user's last message into a single self-contained search query "
                "in the same language, resolving pronouns/ellipsis from the conversation. "
                "Output ONLY the query text, no quotes, no explanation."
            ),
        },
        {"role": "user", "content": f"Conversation:\n{history}\n\nLast message: {question}\n\nStandalone query:"},
    ]
    try:
        rewritten = providers.chat(prompt, temperature=0.0, max_tokens=60).strip()
        # Guard against the model returning something empty or absurdly long.
        if rewritten and len(rewritten) <= 200:
            return rewritten
    except Exception:
        pass
    return question


def answer(question: str, memory: Memory | None = None) -> Answer:
    lang = detect_lang(question)

    # Lead capture: if the user shares a contact, acknowledge and signal the manager email.
    # This runs BEFORE the relevance gate so a "my email is …" message isn't sent to fallback.
    contact = extract_contact(question)
    if contact:
        return Answer(text=_LEAD_THANKS[lang], hits=[], grounded=False, lang=lang, lead=contact)

    search_query = contextualize(question, memory)
    hits = retriever.retrieve(search_query)
    email, phone = _contact_suffix(lang)

    # Relevance gate — don't even prompt the LLM if nothing is close enough.
    if not hits or retriever.best_distance(hits) > config.RELEVANCE_MAX_DISTANCE:
        return Answer(
            text=_FALLBACK[lang].format(email=email, phone=phone),
            hits=hits,
            grounded=False,
            lang=lang,
        )

    system = f"{_PERSONA[lang]} {_RULES[lang]} {_date_note(lang)}"
    context = _build_context(hits)
    mem_block = memory.as_context() if memory else ""

    user_content = ""
    if mem_block:
        user_content += f"[История разговора]\n{mem_block}\n\n"
    user_content += f"[КОНТЕКСТ]\n{context}\n\n[ВОПРОС]\n{question}"

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_content},
    ]
    text = providers.chat(messages, temperature=0.2, max_tokens=700)
    return Answer(text=text, hits=hits, grounded=True, lang=lang)
