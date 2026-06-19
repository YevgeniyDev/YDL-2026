"""Streamlit chat UI for the Yessenov Foundation assistant.

Branding matches yessenovfoundation.org: purple accent (#7B2E83), white wordmark on a
dark-purple header band, clean white content, system sans-serif.

Two independent notions of language:
  * INTERFACE language — chosen with the language switch; localizes the UI chrome only.
  * ANSWER language — auto-detected by the engine from each user message (unchanged), so a
    Russian-interface user can still ask in English and get an English answer.

The UI is a thin shell over engine/ — it owns conversation state and the email button's
double-send guard.

Run:  streamlit run app.py
"""
from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st

from engine.memory import Memory
from engine import rag, emailer, eligibility

# --- brand constants ---
PURPLE = "#7B2E83"
PURPLE_DARK = "#5E2266"
PURPLE_TINT = "#F5EFF7"
ASSETS = Path(__file__).parent / "assets"

# Interface-language switch: label shown in the widget -> language code.
LANG_LABELS = {"Қазақша": "kk", "Русский": "ru", "English": "en"}
CODE_TO_LABEL = {code: label for label, code in LANG_LABELS.items()}
DEFAULT_LANG = "ru"

# --- UI string table (interface chrome only; not the bot's answers) ---
UI = {
    "ru": {
        "title": "Ассистент фонда Yessenov",
        "tagline": "Гранты · Стипендии · Программы · Yessenov Data Lab",
        "lang_label": "Язык интерфейса",
        "about_h": "О боте",
        "about_1": "Официальный ассистент фонда Yessenov. Отвечает по грантам, стипендиям и "
                   "программам **только на основе** материалов сайта yessenovfoundation.org, "
                   "на языке вашего сообщения.",
        "admin_h": "📧 Администратору",
        "send_btn": "Отправить саммари разговора",
        "sent_already": "Саммари уже отправлено.",
        "need_question": "Сначала задайте хотя бы один вопрос.",
        "sending": "Отправляю…",
        "sent_ok": "Отправлено! ID: {id}",
        "send_err": "Не удалось отправить: {err}",
        "clear_btn": "🗑 Очистить чат",
        "welcome": "👋 **Здравствуйте!** Я помогу с вопросами о грантах, стипендиях и программах "
                   "фонда. Спросите что-нибудь или выберите тему:",
        "placeholder": "Спросите про гранты, стипендии или программы…",
        "sources": "📎 Источники",
        "spinner": "Ищу в базе знаний…",
        "error": "Ошибка обращения к модели: {err}",
        "suggestions": [
            "Что такое Yessenov Data Lab?",
            "Какие стипендии есть у фонда?",
            "Какие требования к стипендии Есенова?",
            "Как связаться с фондом?",
        ],
    },
    "en": {
        "title": "Yessenov Foundation Assistant",
        "tagline": "Grants · Scholarships · Programs · Yessenov Data Lab",
        "lang_label": "Interface language",
        "about_h": "About",
        "about_1": "The official Yessenov Foundation assistant. It answers questions about grants, "
                   "scholarships and programs **only from** yessenovfoundation.org content, in the "
                   "language of your message.",
        "admin_h": "📧 To admin",
        "send_btn": "Send conversation summary",
        "sent_already": "Summary already sent.",
        "need_question": "Ask at least one question first.",
        "sending": "Sending…",
        "sent_ok": "Sent! ID: {id}",
        "send_err": "Could not send: {err}",
        "clear_btn": "🗑 Clear chat",
        "welcome": "👋 **Hello!** I can help with questions about the foundation's grants, "
                   "scholarships and programs. Ask something or pick a topic:",
        "placeholder": "Ask about grants, scholarships or programs…",
        "sources": "📎 Sources",
        "spinner": "Searching the knowledge base…",
        "error": "Model request error: {err}",
        "suggestions": [
            "What is Yessenov Data Lab?",
            "What scholarships does the foundation offer?",
            "What are the requirements for the Yessenov Scholarship?",
            "How can I contact the foundation?",
        ],
    },
    "kk": {
        "title": "Yessenov қорының ассистенті",
        "tagline": "Гранттар · Стипендиялар · Бағдарламалар · Yessenov Data Lab",
        "lang_label": "Интерфейс тілі",
        "about_h": "Бот туралы",
        "about_1": "Yessenov қорының ресми ассистенті. Гранттар, стипендиялар және бағдарламалар "
                   "туралы сұрақтарға **тек** yessenovfoundation.org материалдары негізінде, "
                   "хабарламаңыздың тілінде жауап береді.",
        "admin_h": "📧 Әкімшіге",
        "send_btn": "Әңгіме түйінін жіберу",
        "sent_already": "Түйін жіберілді.",
        "need_question": "Алдымен кемінде бір сұрақ қойыңыз.",
        "sending": "Жіберілуде…",
        "sent_ok": "Жіберілді! ID: {id}",
        "send_err": "Жіберу мүмкін болмады: {err}",
        "clear_btn": "🗑 Чатты тазалау",
        "welcome": "👋 **Сәлеметсіз бе!** Қордың гранттары, стипендиялары мен бағдарламалары "
                   "туралы сұрақтарға көмектесемін. Сұрақ қойыңыз немесе тақырыпты таңдаңыз:",
        "placeholder": "Гранттар, стипендиялар немесе бағдарламалар туралы сұраңыз…",
        "sources": "📎 Дереккөздер",
        "spinner": "Білім қорынан іздеу…",
        "error": "Модельге сұрау қатесі: {err}",
        "suggestions": [
            "Yessenov Data Lab дегеніміз не?",
            "Қордың қандай стипендиялары бар?",
            "Есенов стипендиясына қандай талаптар бар?",
            "Қормен қалай байланысуға болады?",
        ],
    },
}

st.set_page_config(page_title="Yessenov Foundation — Assistant", page_icon="🟣", layout="centered")


def _logo_data_uri() -> str | None:
    p = ASSETS / "logo.png"
    if p.exists():
        return "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode()
    return None


def _inject_css() -> None:
    st.markdown(
        f"""
        <style>
        #MainMenu, footer, header {{ visibility: hidden; }}
        /* position: relative makes this the anchor for the floating language menu */
        .block-container {{ padding-top: 1.2rem; max-width: 820px; position: relative; }}

        /* Language switch floats in the top-right corner, overlaying content (not pushing it).
           right:16px matches the content boxes' right edge; top:12px adds space above it. */
        .st-key-langbox {{ position: absolute; top: 12px; right: 16px; width: 190px; z-index: 1000; }}
        .st-key-langmenu {{
            background: #fff; border: 1px solid #E3D3EA; border-radius: 10px;
            box-shadow: 0 8px 24px rgba(94,34,102,0.20); padding: 6px; margin-top: 4px;
        }}
        .yf-header {{
            background: linear-gradient(135deg, {PURPLE_DARK} 0%, {PURPLE} 100%);
            border-radius: 14px; padding: 22px 26px; margin-top: 26px; margin-bottom: 18px;
            display: flex; align-items: center; gap: 18px;
            box-shadow: 0 4px 18px rgba(94,34,102,0.25);
        }}
        .yf-header img {{ height: 38px; }}
        .yf-header .yf-title {{ color: #fff; }}
        .yf-header .yf-title h1 {{ font-size: 1.25rem; margin: 0; font-weight: 600; }}
        .yf-header .yf-title p  {{ margin: 2px 0 0; font-size: 0.85rem; opacity: 0.85; }}
        .stChatMessage {{ border-radius: 12px; }}
        div[data-testid="stChatMessageContent"] {{ font-size: 0.97rem; }}
        .stButton > button {{
            background: {PURPLE}; color: #fff; border: none; border-radius: 8px; font-weight: 500;
        }}
        .stButton > button:hover {{ background: {PURPLE_DARK}; color: #fff; }}
        div[data-testid="column"] .stButton > button {{
            background: {PURPLE_TINT}; color: {PURPLE_DARK};
            border: 1px solid #E3D3EA; font-weight: 400; font-size: 0.85rem;
        }}
        div[data-testid="column"] .stButton > button:hover {{ background: #EADcF0; color: {PURPLE_DARK}; }}
        .streamlit-expanderHeader {{ font-size: 0.85rem; color: {PURPLE_DARK}; }}
        a {{ color: {PURPLE}; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_header(t: dict) -> None:
    logo = _logo_data_uri()
    img_html = f'<img src="{logo}" alt="Yessenov Foundation"/>' if logo else ""
    st.markdown(
        f"""
        <div class="yf-header">
            {img_html}
            <div class="yf-title">
                <h1>{t['title']}</h1>
                <p>{t['tagline']}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _dedup_sources(hits) -> list:
    seen, out = set(), []
    for h in hits:
        if h.source_url not in seen:
            seen.add(h.source_url)
            out.append(h)
    return out


def _start_wizard() -> None:
    st.session_state.wizard_active = True
    st.session_state.wizard_step = 0
    st.session_state.wizard_answers = {}


def _render_program(pid: str, lang: str, w: dict) -> None:
    p = eligibility.program_text(pid, lang)
    with st.container(border=True):
        st.markdown(f"**{p['name']}**  \n{p['note']}")
        st.markdown(f"_{w['docs_label']}_")
        for d in p["docs"]:
            st.markdown(f"- {d}")
        st.markdown(f"[{w['more']}]({p['url']})")


def _render_wizard(lang: str) -> None:
    """Guided eligibility flow. One question per step; results + CTA at the end."""
    w = eligibility.UI[lang]
    questions = eligibility.QUESTIONS
    step = st.session_state.wizard_step

    if step < len(questions):
        q = questions[step]
        if step == 0:
            st.caption(w["intro"])
        st.markdown(f"**{step + 1}/{len(questions)} — {q['q'][lang]}**")
        cols = st.columns(2)
        for i, opt in enumerate(q["options"]):
            if cols[i % 2].button(opt["label"][lang], key=f"wiz_{q['id']}_{opt['id']}", use_container_width=True):
                st.session_state.wizard_answers[q["id"]] = opt["id"]
                st.session_state.wizard_step += 1
                st.rerun()
        return

    # Results
    results = eligibility.evaluate(st.session_state.wizard_answers)
    eligible = [pid for pid, stt in results if stt == "eligible"]
    maybe = [pid for pid, stt in results if stt == "maybe"]
    if eligible:
        st.markdown(f"#### {w['eligible_h']}")
        for pid in eligible:
            _render_program(pid, lang, w)
    if maybe:
        st.markdown(f"#### {w['maybe_h']}")
        for pid in maybe:
            _render_program(pid, lang, w)
    if not eligible and not maybe:
        st.info(w["none"])
    st.caption(w["disclaimer"])
    st.success(w["cta"])
    c1, c2 = st.columns(2)
    if c1.button(w["restart"], key="wiz_restart", use_container_width=True):
        _start_wizard()
        st.rerun()
    if c2.button(w["close"], key="wiz_close", use_container_width=True):
        st.session_state.wizard_active = False
        st.rerun()


def _init_state() -> None:
    st.session_state.setdefault("memory", Memory())
    st.session_state.setdefault("messages", [])      # {role, content, hits?, grounded?}
    st.session_state.setdefault("lead_sent", False)  # one manager email per conversation
    st.session_state.setdefault("pending", None)     # question queued from a suggestion chip
    st.session_state.setdefault("ui_lang", DEFAULT_LANG)  # interface language code
    st.session_state.setdefault("lang_open", False)  # is the language list expanded?
    st.session_state.setdefault("wizard_active", False)  # eligibility wizard open?
    st.session_state.setdefault("wizard_step", 0)
    st.session_state.setdefault("wizard_answers", {})


def _process(prompt: str, t: dict) -> None:
    """Run one user turn. The bot auto-detects the answer language from `prompt` itself."""
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner(t["spinner"]):
            try:
                result = rag.answer(prompt, st.session_state.memory)
            except Exception as e:  # surface API/config errors instead of crashing
                st.error(t["error"].format(err=e))
                st.session_state.messages.pop()
                return
        st.markdown(result.text)
        sources = _dedup_sources(result.hits) if result.grounded else []
        if sources:
            with st.expander(t["sources"]):
                for h in sources:
                    st.markdown(f"- [{h.source_url}]({h.source_url}) — _{h.topic}_")
    st.session_state.memory.add_turn(prompt, result.text)
    st.session_state.messages.append(
        {"role": "assistant", "content": result.text, "hits": sources, "grounded": result.grounded}
    )
    # Lead capture: the moment the user shares a contact, forward ONE summary to the manager.
    # Guarded to once per conversation so a bug can never send in a loop.
    if result.lead and not st.session_state.lead_sent:
        res = emailer.send_summary(st.session_state.memory, contact=result.lead)
        if res.ok:
            st.session_state.lead_sent = True


# ── app ──
_init_state()
_inject_css()

# Interface-language switch — a globe button pinned to the top-right that shows ONLY the
# current language. Clicking it toggles a floating menu (CSS-positioned to overlay content,
# not push it down); picking a language closes the menu. Chrome only — the bot still answers
# in the language of each message.
ui_lang = st.session_state.ui_lang
with st.container(key="langbox"):
    caret = "▴" if st.session_state.lang_open else "▾"
    if st.button(f"🌐 {CODE_TO_LABEL[ui_lang]} {caret}", use_container_width=True, key="lang_toggle"):
        st.session_state.lang_open = not st.session_state.lang_open
        st.rerun()
    if st.session_state.lang_open:
        with st.container(key="langmenu"):
            for code, label in CODE_TO_LABEL.items():
                if st.button(label, key=f"lang_opt_{code}", use_container_width=True):
                    st.session_state.ui_lang = code
                    st.session_state.lang_open = False  # collapse after choosing
                    st.rerun()

t = UI[ui_lang]

_render_header(t)

# Eligibility wizard — entry button + active panel (a unique, on-mission feature).
if st.session_state.wizard_active:
    with st.container(border=True):
        _render_wizard(ui_lang)
else:
    if st.button(eligibility.UI[ui_lang]["start"], key="wiz_start", use_container_width=True):
        _start_wizard()
        st.rerun()

# Replay history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("hits"):
            with st.expander(t["sources"]):
                for h in msg["hits"]:
                    st.markdown(f"- [{h.source_url}]({h.source_url}) — _{h.topic}_")

# Welcome + suggestion chips (before the first message, and not while the wizard is open)
if not st.session_state.messages and not st.session_state.wizard_active:
    st.markdown(t["welcome"])
    cols = st.columns(2)
    for i, s in enumerate(t["suggestions"]):
        if cols[i % 2].button(s, key=f"sug_{i}", use_container_width=True):
            st.session_state.pending = s
            st.rerun()

# Handle a queued suggestion or typed input
typed = st.chat_input(t["placeholder"])
prompt = st.session_state.pending or typed
if prompt:
    st.session_state.pending = None
    _process(prompt, t)
    st.rerun()
