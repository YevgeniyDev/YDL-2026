"""Lead summary to the manager (admin) via MailerSend.

SAFETY (per the brief):
  - Only ever send to ADMIN_EMAIL (your own inbox). Never to arbitrary user addresses.
  - Sent on a conscious trigger only — when the user shares their contact — never in a loop.
  - The caller (app.py) additionally guards with a once-per-session flag, so at most one
    email is sent per conversation regardless of how many contacts the user types.

The email is a structured, branded HTML message: header, highlighted contact, an LLM
summary, and the full Q&A transcript, with a plain-text fallback for text-only clients.
"""
from __future__ import annotations

import datetime
import html as _html
import re
from dataclasses import dataclass

from . import config, providers
from .memory import Memory

PURPLE = "#7B2E83"
PURPLE_DARK = "#5E2266"
PURPLE_TINT = "#F5EFF7"


@dataclass
class SendResult:
    ok: bool
    message_id: str = ""
    error: str = ""


def summarize_conversation(memory: Memory) -> str:
    """Ask the LLM for a short admin-facing summary of the chat."""
    transcript = memory.full_transcript()
    if not transcript.strip():
        return "Пустой разговор."
    messages = [
        {
            "role": "system",
            "content": (
                "Сделай краткое саммари обращения пользователя для менеджера фонда: "
                "имя пользователя (если есть), что спрашивал, какая заявка/запрос, и контакты. "
                "3-6 предложений, по-русски."
            ),
        },
        {"role": "user", "content": transcript},
    ]
    try:
        return providers.chat(messages, temperature=0.2, max_tokens=300)
    except Exception:
        return transcript[:2000]  # never block the email on a summarization failure


def _md_to_html(text: str) -> str:
    """Tiny markdown -> HTML for email bodies: escape, **bold**, bullets, line breaks."""
    t = _html.escape(text or "")
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    lines = []
    for ln in t.split("\n"):
        s = ln.strip()
        if s.startswith("* ") or s.startswith("- "):
            lines.append("• " + s[2:])
        else:
            lines.append(ln)
    return "<br>".join(lines)


def _transcript_html(memory: Memory) -> str:
    """Render the conversation as readable Q/A blocks."""
    blocks = []
    if memory.summary:
        blocks.append(
            f'<div style="background:#fffaf0;border:1px solid #f0e6d2;border-radius:8px;'
            f'padding:10px 14px;margin-bottom:14px;font-size:13px;color:#7a6a3a;">'
            f'<b>Ранее в разговоре:</b> {_md_to_html(memory.summary)}</div>'
        )
    for user, bot in memory.turns:
        blocks.append(
            '<div style="margin-bottom:16px;">'
            '<div style="font-size:11px;color:#999;text-transform:uppercase;letter-spacing:.4px;margin-bottom:3px;">Пользователь</div>'
            f'<div style="background:{PURPLE_TINT};padding:9px 13px;border-radius:8px;font-size:13.5px;color:#1e1e1e;line-height:1.5;">{_md_to_html(user)}</div>'
            '<div style="font-size:11px;color:#999;text-transform:uppercase;letter-spacing:.4px;margin:8px 0 3px;">Ассистент</div>'
            f'<div style="background:#f6f6f8;padding:9px 13px;border-radius:8px;font-size:13.5px;color:#444;line-height:1.5;">{_md_to_html(bot)}</div>'
            "</div>"
        )
    return "".join(blocks) or '<div style="color:#999;font-size:13px;">(нет сообщений)</div>'


def _build_html(summary: str, contact: str | None, memory: Memory) -> str:
    when = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
    n = len(memory.turns)
    contact_block = ""
    if contact:
        contact_block = (
            f'<div style="background:{PURPLE_TINT};border-left:4px solid {PURPLE};'
            f'padding:12px 16px;border-radius:6px;margin-bottom:22px;">'
            f'<div style="font-size:11px;color:{PURPLE};text-transform:uppercase;letter-spacing:.6px;">Контакт пользователя</div>'
            f'<div style="font-size:17px;font-weight:bold;color:#1e1e1e;margin-top:3px;">{_html.escape(contact)}</div>'
            f"</div>"
        )

    def section_title(t: str) -> str:
        return (
            f'<div style="font-size:12px;color:{PURPLE};font-weight:bold;'
            f'text-transform:uppercase;letter-spacing:.6px;margin:0 0 8px;">{t}</div>'
        )

    return f"""\
<div style="background:#f4f4f7;padding:24px 0;font-family:Arial,Helvetica,sans-serif;">
  <div style="max-width:600px;margin:0 auto;background:#ffffff;border-radius:12px;
              overflow:hidden;border:1px solid #ececf0;">
    <div style="background:{PURPLE_DARK};padding:20px 28px;">
      <div style="color:#ffffff;font-size:18px;font-weight:bold;">📨 Новая заявка из чат-бота</div>
      <div style="color:#e6d4ee;font-size:13px;margin-top:4px;">Yessenov Foundation — ассистент</div>
    </div>
    <div style="padding:24px 28px;">
      {contact_block}
      {section_title("Саммари обращения")}
      <div style="font-size:14px;line-height:1.6;color:#333;margin-bottom:24px;">{_md_to_html(summary)}</div>
      {section_title("История разговора")}
      {_transcript_html(memory)}
    </div>
    <div style="background:#fafafa;padding:14px 28px;border-top:1px solid #ececf0;
                color:#999;font-size:12px;">
      Отправлено автоматически ассистентом фонда · {when} · сообщений: {n}
    </div>
  </div>
</div>"""


def _build_text(summary: str, contact: str | None, memory: Memory) -> str:
    when = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
    parts = ["НОВАЯ ЗАЯВКА ИЗ ЧАТ-БОТА YESSENOV", "=" * 40]
    if contact:
        parts.append(f"Контакт пользователя: {contact}")
    parts += ["", "САММАРИ:", summary, "", "ИСТОРИЯ РАЗГОВОРА:"]
    if memory.summary:
        parts.append(f"[ранее] {memory.summary}")
    for user, bot in memory.turns:
        parts += [f"Пользователь: {user}", f"Ассистент: {bot}", ""]
    parts.append(f"--- Отправлено {when}, сообщений: {len(memory.turns)} ---")
    return "\n".join(parts)


def send_summary(memory: Memory, contact: str | None = None) -> SendResult:
    """Send one structured lead email to ADMIN_EMAIL (the manager)."""
    if not config.MAILERSEND_API_KEY:
        return SendResult(False, error="MAILERSEND_API_KEY is not set.")
    if not config.ADMIN_EMAIL:
        return SendResult(False, error="ADMIN_EMAIL is not set.")

    summary = summarize_conversation(memory)
    html_body = _build_html(summary, contact, memory)
    text_body = _build_text(summary, contact, memory)
    subject = f"Новая заявка из чата{f' — {contact}' if contact else ''}"

    try:
        from mailersend import MailerSendClient, EmailBuilder

        ms = MailerSendClient(api_key=config.MAILERSEND_API_KEY)
        email = (
            EmailBuilder()
            .from_email(config.MAIL_FROM_EMAIL, config.MAIL_FROM_NAME)
            .to_many([{"email": config.ADMIN_EMAIL, "name": "Admin"}])
            .subject(subject)
            .html(html_body)
            .text(text_body)
            .build()
        )
        response = ms.emails.send(email)

        # MailerSend v2: success on HTTP 202; id in response.data['id'] / x-message-id header.
        status = getattr(response, "status_code", None)
        ok = bool(getattr(response, "success", False)) or (status is not None and 200 <= status < 300)
        if not ok:
            return SendResult(False, error=f"MailerSend rejected the email (HTTP {status}).")
        data = getattr(response, "data", None)
        message_id = (data.get("id", "") if isinstance(data, dict) else "") or \
            (getattr(response, "headers", {}) or {}).get("x-message-id", "")
        return SendResult(True, message_id=message_id or "sent")
    except Exception as e:  # noqa: BLE001 — surface any SDK/network error to the caller
        return SendResult(False, error=str(e))
