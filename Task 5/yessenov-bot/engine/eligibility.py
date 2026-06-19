"""Eligibility wizard — a guided, rule-based matcher for the foundation's programs.

This is deliberately DETERMINISTIC (no LLM): a curated rule set derived from the scraped
program pages, so it never hallucinates eligibility. Each program links back to its source
page, and results carry a disclaimer pointing to the official Program Provisions.

Public API:
  QUESTIONS                  -> ordered list of questions (localized)
  evaluate(answers)          -> list of (program_id, "eligible"|"maybe")
  program_text(pid, lang)    -> {name, docs, note, url}
  UI[lang]                   -> wizard chrome strings
"""
from __future__ import annotations

# ── Questions (ordered) ──────────────────────────────────────────────────────
QUESTIONS = [
    {
        "id": "citizen",
        "q": {
            "ru": "Вы гражданин(ка) Казахстана?",
            "en": "Are you a citizen of Kazakhstan?",
            "kk": "Сіз Қазақстан азаматысыз ба?",
        },
        "options": [
            {"id": "yes", "label": {"ru": "Да", "en": "Yes", "kk": "Иә"}},
            {"id": "no", "label": {"ru": "Нет", "en": "No", "kk": "Жоқ"}},
        ],
    },
    {
        "id": "status",
        "q": {
            "ru": "Кто вы сейчас?",
            "en": "What is your current status?",
            "kk": "Қазір сіз кімсіз?",
        },
        "options": [
            {"id": "school", "label": {"ru": "Школьник / выпускник школы", "en": "School student", "kk": "Мектеп оқушысы"}},
            {"id": "ba_early", "label": {"ru": "Бакалавриат, 1 курс", "en": "Bachelor, 1st year", "kk": "Бакалавр, 1-курс"}},
            {"id": "ba_mid", "label": {"ru": "Бакалавриат, 2 курс – предпоследний", "en": "Bachelor, 2nd to pre-final year", "kk": "Бакалавр, 2-курстан соңғыға дейін"}},
            {"id": "ba_final", "label": {"ru": "Бакалавриат, выпускной курс", "en": "Bachelor, final year", "kk": "Бакалавр, бітіруші курс"}},
            {"id": "master", "label": {"ru": "Магистрант / аспирант", "en": "Master's / PhD student", "kk": "Магистрант / аспирант"}},
            {"id": "prof", "label": {"ru": "Выпускник / молодой специалист", "en": "Graduate / young professional", "kk": "Түлек / жас маман"}},
        ],
    },
    {
        "id": "field",
        "q": {
            "ru": "Ваше направление (специальность)?",
            "en": "Your field of study?",
            "kk": "Сіздің бағытыңыз (мамандығыңыз)?",
        },
        "options": [
            {"id": "natural", "label": {"ru": "Естественные науки", "en": "Natural sciences", "kk": "Жаратылыстану ғылымдары"}},
            {"id": "ict", "label": {"ru": "ИКТ / IT", "en": "ICT / IT", "kk": "АКТ / IT"}},
            {"id": "engineering", "label": {"ru": "Инженерия", "en": "Engineering", "kk": "Инженерия"}},
            {"id": "industry", "label": {"ru": "Промышленность и строительство", "en": "Manufacturing & construction", "kk": "Өнеркәсіп және құрылыс"}},
            {"id": "health", "label": {"ru": "Здравоохранение", "en": "Healthcare", "kk": "Денсаулық сақтау"}},
            {"id": "other", "label": {"ru": "Другое / гуманитарные", "en": "Other / humanities", "kk": "Басқа / гуманитарлық"}},
        ],
    },
    {
        "id": "gpa",
        "q": {
            "ru": "Ваш средний балл (GPA)?",
            "en": "Your GPA?",
            "kk": "Сіздің орташа балыңыз (GPA)?",
        },
        "options": [
            {"id": "yes", "label": {"ru": "3.0 и выше", "en": "3.0 or higher", "kk": "3.0 және жоғары"}},
            {"id": "no", "label": {"ru": "Ниже 3.0", "en": "Below 3.0", "kk": "3.0-ден төмен"}},
            {"id": "unknown", "label": {"ru": "Не знаю", "en": "Not sure", "kk": "Білмеймін"}},
        ],
    },
]

_SCHOLARSHIP_FIELDS = {"natural", "ict", "engineering", "industry", "health"}


def evaluate(a: dict) -> list[tuple[str, str]]:
    """Return [(program_id, status)] where status is 'eligible' or 'maybe'."""
    out: list[tuple[str, str]] = []
    citizen, status, field, gpa = a.get("citizen"), a.get("status"), a.get("field"), a.get("gpa")
    if citizen != "yes":
        return out  # all programs are for Kazakhstani citizens

    # Yessenov Scholarship: bachelor, NOT 1st/final year, listed field, GPA >= 3.0
    if status == "ba_mid" and field in _SCHOLARSHIP_FIELDS:
        if gpa == "yes":
            out.append(("scholarship", "eligible"))
        elif gpa == "unknown":
            out.append(("scholarship", "maybe"))
        # gpa == "no" -> not eligible (3.0 is mandatory)

    # Research Internships: bachelor yr 2+, master, or researchers
    if status in {"ba_mid", "ba_final", "master", "prof"}:
        out.append(("research", "eligible"))

    # Yessenov Data Lab: open to students & young professionals who want data skills
    if status in {"ba_early", "ba_mid", "ba_final", "master", "prof"}:
        out.append(("ydl", "eligible"))

    # Yessenov Launch Pad: young specialists / additional soft & hard skills
    if status in {"ba_final", "master", "prof"}:
        out.append(("launchpad", "eligible"))

    return out


# ── Program content (grounded in the scraped pages) ──────────────────────────
_PROGRAMS = {
    "scholarship": {
        "url": "https://yessenovfoundation.org/about-us/programs/science/yessenov-scholarship",
        "name": {"ru": "Стипендия им. Ш. Есенова", "en": "Shakhmardan Yessenov Scholarship", "kk": "Ш. Есенов атындағы стипендия"},
        "note": {
            "ru": "20 стипендиатов, 70 000 тг/мес. Приём заявок обычно февраль–март (в 2026 — 2 февраля – 3 марта).",
            "en": "20 recipients, 70,000 KZT/month. Applications usually open Feb–Mar (in 2026: Feb 2 – Mar 3).",
            "kk": "20 стипендиат, айына 70 000 тг. Өтінімдер әдетте ақпан–наурызда (2026 ж.: 2 ақпан – 3 наурыз).",
        },
        "docs": {
            "ru": ["Заявка на сайте фонда", "Транскрипт (GPA ≥ 3.0)", "Мотивационное эссе", "Сертификаты/дипломы (по желанию)", "Рекомендации (по желанию)"],
            "en": ["Application on the foundation site", "Transcript (GPA ≥ 3.0)", "Motivation essay", "Certificates/diplomas (optional)", "Recommendations (optional)"],
            "kk": ["Қор сайтындағы өтінім", "Транскрипт (GPA ≥ 3.0)", "Мотивациялық эссе", "Сертификаттар/дипломдар (қалауыңызша)", "Ұсынымдар (қалауыңызша)"],
        },
    },
    "research": {
        "url": "https://yessenovfoundation.org/about-us/programs/science/research-internships",
        "name": {"ru": "Научные стажировки", "en": "Research Internships", "kk": "Ғылыми тағылымдамалар"},
        "note": {
            "ru": "Гранты на стажировки в ведущих лабораториях мира (до 90 дней), полное покрытие расходов.",
            "en": "Grants for internships at world-leading labs (up to 90 days), fully funded.",
            "kk": "Әлемнің жетекші зертханаларындағы тағылымдамаға гранттар (90 күнге дейін), толық қаржыландыру.",
        },
        "docs": {
            "ru": ["CV (резюме)", "Транскрипты за все семестры", "Диплом предыдущего уровня образования", "Мотивационное письмо", "Рекомендация руководителя"],
            "en": ["CV", "Transcripts for all semesters", "Diploma of previous education level", "Motivation letter", "Supervisor's recommendation"],
            "kk": ["CV (түйіндеме)", "Барлық семестр транскрипттері", "Алдыңғы білім деңгейінің дипломы", "Мотивациялық хат", "Жетекшінің ұсынымы"],
        },
    },
    "ydl": {
        "url": "https://yessenovfoundation.org/about-us/programs/resources/yessenov-data-lab",
        "name": {"ru": "Yessenov Data Lab", "en": "Yessenov Data Lab", "kk": "Yessenov Data Lab"},
        "note": {
            "ru": "Интенсив ~4 недели по анализу данных (обычно июнь–июль), совместно с AlmaU.",
            "en": "~4-week intensive in data analysis (usually Jun–Jul), together with AlmaU.",
            "kk": "Деректерді талдау бойынша ~4 апталық интенсив (әдетте маусым–шілде), AlmaU-мен бірге.",
        },
        "docs": {
            "ru": ["Онлайн-заявка на сайте", "Отборочный тест / собеседование"],
            "en": ["Online application", "Selection test / interview"],
            "kk": ["Сайттағы онлайн өтінім", "Іріктеу тесті / сұхбат"],
        },
    },
    "launchpad": {
        "url": "https://yessenovfoundation.org/about-us/programs/resources/yessenov-launch-pad",
        "name": {"ru": "Yessenov Launch Pad", "en": "Yessenov Launch Pad", "kk": "Yessenov Launch Pad"},
        "note": {
            "ru": "До 10 грантов (до 600 000 тг) на развитие soft и hard skills для молодых специалистов.",
            "en": "Up to 10 grants (up to 600,000 KZT) for soft & hard skills, for young professionals.",
            "kk": "Жас мамандарға soft және hard дағдыларына 10 грантқа дейін (600 000 тг дейін).",
        },
        "docs": {
            "ru": ["Заявка на сайте фонда", "Описание желаемого курса/обучения"],
            "en": ["Application on the foundation site", "Description of the desired course/training"],
            "kk": ["Қор сайтындағы өтінім", "Қалаған курс/оқу сипаттамасы"],
        },
    },
}


def program_text(pid: str, lang: str) -> dict:
    p = _PROGRAMS[pid]
    return {"name": p["name"][lang], "note": p["note"][lang], "docs": p["docs"][lang], "url": p["url"]}


# ── Wizard chrome strings ────────────────────────────────────────────────────
UI = {
    "ru": {
        "start": "🎯 Подобрать программу за 30 секунд",
        "intro": "Ответьте на 4 коротких вопроса — я подскажу, какие программы вам подходят и какие документы нужны.",
        "restart": "↺ Пройти заново",
        "close": "Закрыть",
        "eligible_h": "✅ Вам, скорее всего, подходят:",
        "maybe_h": "❔ Возможно подходят (нужно уточнить):",
        "none": "По указанным данным точного совпадения нет. Но не расстраивайтесь — напишите нам, и мы подскажем варианты. Можно также рассмотреть Yessenov Data Lab.",
        "docs_label": "Нужные документы:",
        "more": "Подробнее",
        "cta": "Хотите, чтобы менеджер связался и помог с заявкой? Напишите имя и контакт (email или телефон) в чате ниже.",
        "disclaimer": "Это предварительная оценка. Точные условия — в Положении программы на сайте фонда.",
    },
    "en": {
        "start": "🎯 Find your program in 30 seconds",
        "intro": "Answer 4 short questions and I'll tell you which programs fit you and what documents you need.",
        "restart": "↺ Start over",
        "close": "Close",
        "eligible_h": "✅ You're likely eligible for:",
        "maybe_h": "❔ Possibly eligible (needs checking):",
        "none": "No exact match for the details given. Don't worry — message us and we'll suggest options. You could also consider Yessenov Data Lab.",
        "docs_label": "Documents needed:",
        "more": "Details",
        "cta": "Want a manager to reach out and help with your application? Type your name and contact (email or phone) in the chat below.",
        "disclaimer": "This is a preliminary estimate. Exact terms are in the Program Provisions on the foundation site.",
    },
    "kk": {
        "start": "🎯 30 секундта бағдарлама таңдау",
        "intro": "4 қысқа сұраққа жауап беріңіз — сізге қандай бағдарламалар сай келетінін және қандай құжаттар қажет екенін айтамын.",
        "restart": "↺ Қайта бастау",
        "close": "Жабу",
        "eligible_h": "✅ Сізге сай келуі мүмкін:",
        "maybe_h": "❔ Мүмкін сай келеді (нақтылау қажет):",
        "none": "Көрсетілген деректер бойынша нақты сәйкестік жоқ. Бізге жазыңыз — нұсқалар ұсынамыз. Yessenov Data Lab-ты да қарастыруға болады.",
        "docs_label": "Қажетті құжаттар:",
        "more": "Толығырақ",
        "cta": "Менеджер хабарласып, өтінімге көмектессін бе? Төмендегі чатқа атыңыз бен байланысыңызды (email немесе телефон) жазыңыз.",
        "disclaimer": "Бұл алдын ала бағалау. Нақты шарттар — қор сайтындағы бағдарлама ережесінде.",
    },
}
