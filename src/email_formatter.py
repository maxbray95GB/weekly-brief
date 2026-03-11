"""
Email formatter v4 — 6-section bi-weekly brief.

Sections:
  1. The week at a glance
  2. Key learnings and insights
  3. Week ahead
  4. Who you spoke to
  5. Documents
  6. Final thought
"""

from datetime import datetime


def _section(title: str, content: str, accent: bool = False) -> str:
    border_color = "#2c2c2c" if accent else "#ddd"
    return f"""
    <div style="margin-bottom: 28px;">
      <h2 style="font-family: Georgia, serif; font-size: 13px; font-weight: bold;
                 color: #1a1a1a; text-transform: uppercase; letter-spacing: 0.1em;
                 border-bottom: 2px solid {border_color}; padding-bottom: 6px; margin-bottom: 14px;">
        {title}
      </h2>
      {content}
    </div>
    """


def _p(text: str, size: str = "14px", color: str = "#333") -> str:
    return f'<p style="font-family: Georgia, serif; font-size: {size}; color: {color}; line-height: 1.6; margin: 0 0 8px 0;">{text}</p>'


def _label(text: str) -> str:
    return f'<p style="font-family: sans-serif; font-size: 11px; color: #888; text-transform: uppercase; letter-spacing: 0.07em; margin: 14px 0 6px 0;">{text}</p>'


def _li(text: str) -> str:
    return f'<li style="font-family: Georgia, serif; font-size: 14px; color: #333; line-height: 1.6; margin-bottom: 5px; padding-left: 2px;">{text}</li>'


def _ul(items: list[str]) -> str:
    lis = "".join(_li(i) for i in items)
    return f'<ul style="margin: 0; padding-left: 18px;">{lis}</ul>'


def build_html_email(briefing: dict, date_label: str, is_monday: bool = False) -> str:
    sections_html = []

    # ── 1. The week at a glance ──────────────────────────────────────────
    glance = briefing.get("glance", {})
    if glance:
        email_count = glance.get("email_count", 0)
        meeting_count = glance.get("meeting_count", 0)

        # Stats badges
        content = f"""
        <table cellpadding="0" cellspacing="0" border="0" style="margin-bottom: 16px;">
          <tr>
            <td style="background: #f0ebe3; padding: 8px 16px; border-radius: 4px; text-align: center; min-width: 60px;">
              <div style="font-family: Georgia, serif; font-size: 20px; font-weight: bold; color: #1a1a1a; line-height: 1;">{meeting_count}</div>
              <div style="font-family: sans-serif; font-size: 10px; color: #888; text-transform: uppercase; letter-spacing: 0.06em; margin-top: 2px;">Meetings</div>
            </td>
            <td style="width: 12px;"></td>
            <td style="background: #f0ebe3; padding: 8px 16px; border-radius: 4px; text-align: center; min-width: 60px;">
              <div style="font-family: Georgia, serif; font-size: 20px; font-weight: bold; color: #1a1a1a; line-height: 1;">{email_count}</div>
              <div style="font-family: sans-serif; font-size: 10px; color: #888; text-transform: uppercase; letter-spacing: 0.06em; margin-top: 2px;">Emails</div>
            </td>
          </tr>
        </table>"""

        # Standout contacts
        standouts = glance.get("standout_contacts", [])
        if standouts:
            rows = ""
            for sc in standouts:
                rows += f"""<tr>
                  <td style="padding: 3px 10px 3px 0; font-family: Georgia, serif; font-size: 13px;
                             font-weight: bold; color: #1a1a1a; white-space: nowrap; vertical-align: top; width: 30%;">
                    {sc.get('name', '')}
                  </td>
                  <td style="padding: 3px 0; font-family: Georgia, serif; font-size: 13px; color: #555; line-height: 1.4;">
                    {sc.get('note', '')}
                  </td>
                </tr>"""
            content += _label("Standout contacts")
            content += f'<table style="width: 100%; border-collapse: collapse; margin-bottom: 10px;">{rows}</table>'

        # Momentum
        momentum = glance.get("momentum")
        if momentum:
            content += _label("Where momentum is building")
            content += _p(momentum)

        # Gap
        gap = glance.get("gap")
        if gap:
            content += _label("Possible gap")
            content += _p(f"<em>{gap}</em>", color="#996633")

        sections_html.append(_section("The week at a glance", content, accent=True))

    # ── 2. Key learnings and insights ────────────────────────────────────
    learnings = briefing.get("key_learnings", [])
    if learnings:
        sections_html.append(_section("Key learnings &amp; insights", _ul(learnings)))

    # ── 3. Week ahead ────────────────────────────────────────────────────
    ahead = briefing.get("week_ahead", [])
    if ahead:
        next_update = "Friday" if is_monday else "Monday"
        rows = ""
        for event in ahead:
            is_hl = event.get("highlight", False)
            title_style = "font-weight: bold; color: #1a1a1a;" if is_hl else "color: #333;"
            dot = '<span style="color: #c0392b; margin-right: 4px;">&#9679;</span>' if is_hl else ''
            prep = ""
            if event.get("prep_note"):
                prep = f'<br><span style="font-style: italic; color: #888; font-size: 12px;">{event["prep_note"]}</span>'
            rows += f"""<tr>
              <td style="padding: 4px 10px 4px 0; font-family: sans-serif; font-size: 11px;
                         color: #888; white-space: nowrap; vertical-align: top; width: 18%;">
                {event.get('date', '')}
              </td>
              <td style="padding: 4px 0; font-family: Georgia, serif; font-size: 13px;
                         {title_style} vertical-align: top; line-height: 1.4;">
                {dot}{event.get('title', '')}{prep}
              </td>
            </tr>"""
        subtitle = f'<p style="font-family: sans-serif; font-size: 11px; color: #aaa; margin: 0 0 8px 0;">Until your {next_update} update</p>'
        sections_html.append(_section(
            "Week ahead",
            subtitle + f'<table style="width: 100%; border-collapse: collapse;">{rows}</table>'
        ))

    # ── 4. Who you spoke to ──────────────────────────────────────────────
    people = briefing.get("people", [])
    if people:
        rows = ""
        for person in people:
            count = person.get("interaction_count", 1)
            count_badge = f'<span style="font-family: sans-serif; font-size: 10px; color: #888; margin-left: 4px;">({count}x)</span>' if count > 1 else ''
            follow_up = ""
            if person.get("missed_follow_up"):
                follow_up = f'<br><span style="font-size: 12px; color: #996633;">&#9888; {person["missed_follow_up"]}</span>'
            rows += f"""<tr>
              <td style="padding: 4px 10px 4px 0; font-family: Georgia, serif; font-size: 13px;
                         font-weight: bold; color: #1a1a1a; white-space: nowrap; vertical-align: top; width: 30%;">
                {person.get('name', '')}{count_badge}
              </td>
              <td style="padding: 4px 0; font-family: Georgia, serif; font-size: 13px; color: #555; line-height: 1.4;">
                {person.get('summary', '')}{follow_up}
              </td>
            </tr>"""
        sections_html.append(_section(
            "Who you spoke to",
            f'<table style="width: 100%; border-collapse: collapse;">{rows}</table>'
        ))

    # ── 5. Documents ─────────────────────────────────────────────────────
    documents = briefing.get("documents", [])
    if documents:
        items = []
        for doc in documents:
            link = f' <a href="{doc["url"]}" style="color: #4a6fa5; font-size: 12px;">Open</a>' if doc.get("url") else ""
            items.append(f"<strong>{doc.get('title', '')}</strong> — {doc.get('note', '')}{link}")
        sections_html.append(_section("Documents", _ul(items)))

    # ── 6. Final thought ─────────────────────────────────────────────────
    final = briefing.get("final_thought", "")
    if final:
        sections_html.append(_section("Final thought", _p(f"<em>{final}</em>")))

    body = "\n".join(sections_html)

    day_type = "Monday" if is_monday else "Friday"

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin: 0; padding: 0; background: #e8e2d9;">
  <div style="max-width: 640px; margin: 0 auto; background: #faf7f2;">

    <div style="background: #1a1a1a; padding: 24px 32px;">
      <h1 style="font-family: Georgia, serif; font-size: 18px; color: #f5f0e8; margin: 0 0 2px 0; letter-spacing: 0.02em;">
        {day_type} Brief
      </h1>
      <p style="font-family: sans-serif; font-size: 11px; color: #666; margin: 0; letter-spacing: 0.04em;">
        {date_label.upper()}
      </p>
    </div>

    <div style="padding: 28px 32px 8px 32px;">
      {body}
    </div>

    <div style="padding: 0 32px 24px 32px; border-top: 1px solid #e8e2d9;">
      <p style="font-family: sans-serif; font-size: 11px; color: #bbb; margin: 14px 0 0 0;">
        Follow-up drafts are in Gmail Drafts. Red dot = highlighted event. &#9888; = needs follow-up.
      </p>
    </div>

  </div>
</body>
</html>"""


def get_brief_label() -> str:
    return datetime.now().strftime("%B %d, %Y")
