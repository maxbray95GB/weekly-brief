"""
Email formatter — turns the structured briefing dict into a clean,
formatted HTML email with sections and headers.
"""

from datetime import datetime


def _section(title: str, content: str) -> str:
    return f"""
    <div style="margin-bottom: 32px;">
      <h2 style="font-family: Georgia, serif; font-size: 18px; color: #1a1a1a; 
                 border-bottom: 2px solid #e8e0d5; padding-bottom: 8px; margin-bottom: 16px;">
        {title}
      </h2>
      {content}
    </div>
    """


def _p(text: str) -> str:
    return f'<p style="font-family: Georgia, serif; font-size: 15px; color: #333; line-height: 1.7; margin: 0 0 10px 0;">{text}</p>'


def _li(text: str) -> str:
    return f'<li style="font-family: Georgia, serif; font-size: 15px; color: #333; line-height: 1.7; margin-bottom: 6px;">{text}</li>'


def _ul(items: list[str]) -> str:
    lis = "".join(_li(i) for i in items)
    return f'<ul style="margin: 0; padding-left: 20px;">{lis}</ul>'


def _pill(text: str) -> str:
    return (
        f'<span style="display: inline-block; background: #f0ebe3; color: #555; '
        f'font-family: sans-serif; font-size: 12px; padding: 3px 10px; '
        f'border-radius: 12px; margin: 2px 4px 2px 0;">{text}</span>'
    )


def build_html_email(briefing: dict, week_of: str) -> str:
    """
    Converts the structured briefing dict into a full HTML email string.
    """
    sections_html = []

    # ── Week headline & themes ──────────────────────────────────────────
    headline_html = _p(f"<em>{briefing.get('week_headline', '')}</em>")
    themes = briefing.get("key_themes", [])
    if themes:
        headline_html += "<div style='margin-top: 10px;'>" + "".join(_pill(t) for t in themes) + "</div>"
    sections_html.append(_section("This week at a glance", headline_html))

    # ── People ──────────────────────────────────────────────────────────
    people = briefing.get("people_spoke_to", [])
    if people:
        rows = ""
        for p in people:
            flag = " 🔔" if p.get("follow_up_needed") else ""
            rows += f"""
            <tr>
              <td style="padding: 8px 12px 8px 0; font-family: Georgia, serif; font-size: 14px; 
                          font-weight: bold; color: #1a1a1a; white-space: nowrap; vertical-align: top;">
                {p.get('name', '')}{flag}
              </td>
              <td style="padding: 8px 0; font-family: Georgia, serif; font-size: 14px; 
                          color: #444; line-height: 1.6;">
                {p.get('context', '')}
              </td>
            </tr>"""
        people_html = f'<table style="width: 100%; border-collapse: collapse;">{rows}</table>'
        sections_html.append(_section("Who you spoke to", people_html))

    # ── Key learnings ───────────────────────────────────────────────────
    learnings = briefing.get("key_learnings", [])
    if learnings:
        sections_html.append(_section("Key learnings & insights", _ul(learnings)))

    # ── Missed follow-ups ────────────────────────────────────────────────
    missed = briefing.get("missed_follow_ups", [])
    if missed:
        items = []
        for m in missed:
            items.append(f"<strong>{m.get('person', '')}</strong> — {m.get('what', '')}. <em>{m.get('suggested_action', '')}</em>")
        sections_html.append(_section("⚠️ Missed follow-ups", _ul(items)))

    # ── Docs ─────────────────────────────────────────────────────────────
    docs = briefing.get("docs_created_or_edited", [])
    if docs:
        items = []
        for d in docs:
            url = d.get("url", "")
            title = d.get("title", "Untitled")
            link = f'<a href="{url}" style="color: #5b7fa6;">{title}</a>' if url else title
            items.append(f"{link} — {d.get('significance', '')}")
        sections_html.append(_section("Documents", _ul(items)))

    # ── Open loops from last week ────────────────────────────────────────
    open_loops = briefing.get("open_loops_from_last_week", [])
    if open_loops:
        sections_html.append(_section("Open loops from last week", _ul(open_loops)))

    # ── Week ahead ───────────────────────────────────────────────────────
    ahead = briefing.get("week_ahead_preview", [])
    if ahead:
        rows = ""
        for event in ahead:
            rows += f"""
            <tr>
              <td style="padding: 8px 12px 8px 0; font-family: Georgia, serif; font-size: 13px; 
                          color: #666; white-space: nowrap; vertical-align: top;">
                {event.get('date', '')}
              </td>
              <td style="padding: 8px 0; font-family: Georgia, serif; font-size: 14px; 
                          color: #1a1a1a; font-weight: bold; vertical-align: top;">
                {event.get('title', '')}
              </td>
              <td style="padding: 8px 0 8px 12px; font-family: Georgia, serif; font-size: 14px; 
                          color: #555; font-style: italic; line-height: 1.5;">
                {event.get('prep_note', '')}
              </td>
            </tr>"""
        ahead_html = f'<table style="width: 100%; border-collapse: collapse;">{rows}</table>'
        sections_html.append(_section("Week ahead", ahead_html))

    # ── Closing thought ──────────────────────────────────────────────────
    closing = briefing.get("closing_thought", "")
    if closing:
        sections_html.append(_section("Closing thought", _p(f"<em>{closing}</em>")))

    # ── Assemble full email ──────────────────────────────────────────────
    body = "\n".join(sections_html)

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin: 0; padding: 0; background: #f5f0e8;">
  <div style="max-width: 680px; margin: 0 auto; background: #faf7f2; padding: 0 0 40px 0;">
    
    <!-- Header -->
    <div style="background: #2c2c2c; padding: 32px 40px;">
      <h1 style="font-family: Georgia, serif; font-size: 24px; color: #f5f0e8; margin: 0 0 4px 0;">
        Weekly Brief
      </h1>
      <p style="font-family: sans-serif; font-size: 13px; color: #999; margin: 0;">
        {week_of}
      </p>
    </div>
    
    <!-- Content -->
    <div style="padding: 32px 40px;">
      {body}
    </div>
    
    <!-- Footer -->
    <div style="padding: 0 40px; border-top: 1px solid #e0d8cc;">
      <p style="font-family: sans-serif; font-size: 12px; color: #aaa; margin: 16px 0 0 0;">
        Generated by your Weekly Brief bot. Any follow-up email drafts are waiting in your Gmail Drafts folder.
      </p>
    </div>
    
  </div>
</body>
</html>"""


def get_week_label() -> str:
    """Returns a human-readable label for the current week."""
    today = datetime.now()
    # Go back 7 days for the start of the period
    start = today.replace(day=today.day - 7) if today.day > 7 else today
    return f"Week of {today.strftime('%B %d, %Y')}"
