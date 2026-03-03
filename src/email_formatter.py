"""
Email formatter v3 — new structure:
  1. Recap: key learnings & insights
  2. Missed follow-ups
  3. The week ahead
  4. Open loops (if any)
  5. Closing thought
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


def _p(text: str) -> str:
    return f'<p style="font-family: Georgia, serif; font-size: 14px; color: #333; line-height: 1.6; margin: 0 0 8px 0;">{text}</p>'


def _li(text: str, indent: bool = False) -> str:
    pad = "28px" if indent else "18px"
    return f'<li style="font-family: Georgia, serif; font-size: 14px; color: #333; line-height: 1.6; margin-bottom: 5px; padding-left: 2px;">{text}</li>'


def _ul(items: list[str]) -> str:
    lis = "".join(_li(i) for i in items)
    return f'<ul style="margin: 0; padding-left: 18px;">{lis}</ul>'


def build_html_email(briefing: dict, week_of: str) -> str:
    sections_html = []

    # ── 1. Recap ──────────────────────────────────────────────────────────
    recap = briefing.get("recap", {})
    if recap:
        email_count = recap.get("email_count", 0)
        meeting_count = recap.get("meeting_count", 0)

        # Stats bar
        stats = f"""
        <div style="display: inline-flex; gap: 16px; margin-bottom: 16px;">
          <div style="background: #f0ebe3; padding: 8px 16px; border-radius: 4px; text-align: center; min-width: 60px;">
            <div style="font-family: Georgia, serif; font-size: 20px; font-weight: bold; color: #1a1a1a; line-height: 1;">{meeting_count}</div>
            <div style="font-family: sans-serif; font-size: 10px; color: #888; text-transform: uppercase; letter-spacing: 0.06em; margin-top: 2px;">Meetings</div>
          </div>
          <div style="background: #f0ebe3; padding: 8px 16px; border-radius: 4px; text-align: center; min-width: 60px;">
            <div style="font-family: Georgia, serif; font-size: 20px; font-weight: bold; color: #1a1a1a; line-height: 1;">{email_count}</div>
            <div style="font-family: sans-serif; font-size: 10px; color: #888; text-transform: uppercase; letter-spacing: 0.06em; margin-top: 2px;">Emails</div>
          </div>
        </div>"""

        content = stats

        # Frequent contacts
        freq = recap.get("frequent_contacts", [])
        if freq:
            rows = ""
            for fc in freq:
                rows += f"""<tr>
                  <td style="padding: 4px 12px 4px 0; font-family: Georgia, serif; font-size: 13px;
                             font-weight: bold; color: #1a1a1a; white-space: nowrap; vertical-align: top; width: 28%;">
                    {fc.get('name', '')}
                  </td>
                  <td style="padding: 4px 0; font-family: Georgia, serif; font-size: 13px; color: #555; line-height: 1.5;">
                    {fc.get('note', '')}
                  </td>
                </tr>"""
            content += f'<p style="font-family: sans-serif; font-size: 11px; color: #888; text-transform: uppercase; letter-spacing: 0.07em; margin: 14px 0 6px 0;">Frequently contacted</p>'
            content += f'<table style="width: 100%; border-collapse: collapse; margin-bottom: 14px;">{rows}</table>'

        # Notable emails
        notable = recap.get("notable_emails", [])
        if notable:
            items = []
            for e in notable:
                items.append(f"<strong>{e.get('from', '')}</strong> re: {e.get('subject', '')} — {e.get('why_notable', '')}")
            content += f'<p style="font-family: sans-serif; font-size: 11px; color: #888; text-transform: uppercase; letter-spacing: 0.07em; margin: 0 0 6px 0;">Notable emails</p>'
            content += _ul(items)

        # Key learnings
        learnings = recap.get("key_learnings", [])
        if learnings:
            content += f'<p style="font-family: sans-serif; font-size: 11px; color: #888; text-transform: uppercase; letter-spacing: 0.07em; margin: 14px 0 6px 0;">Key learnings</p>'
            content += _ul(learnings)

        sections_html.append(_section("Recap: key learnings &amp; insights", content, accent=True))

    # ── 2. Missed follow-ups ──────────────────────────────────────────────
    missed = briefing.get("missed_follow_ups", [])
    if missed:
        items = []
        for m in missed:
            direction = " <span style='color:#888; font-size:12px;'>(you → them)</span>" if m.get("direction") == "you_to_them" else ""
            items.append(f"<strong>{m.get('person', '')}</strong>{direction} — {m.get('what', '')}. <em style='color:#666;'>{m.get('suggested_action', '')}</em>")
        sections_html.append(_section("Missed follow-ups", _ul(items)))

    # ── 3. Week ahead ─────────────────────────────────────────────────────
    ahead = briefing.get("week_ahead", [])
    if ahead:
        rows = ""
        for event in ahead:
            is_highlight = event.get("highlight", False)
            title_style = "font-weight: bold; color: #1a1a1a;" if is_highlight else "color: #333;"
            highlight_dot = '<span style="color: #c0392b; margin-right: 4px;">●</span>' if is_highlight else '<span style="color: transparent; margin-right: 4px;">●</span>'
            prep = f'<br><span style="font-style: italic; color: #888; font-size: 12px;">{event["prep_note"]}</span>' if event.get("prep_note") else ""
            rows += f"""<tr>
              <td style="padding: 5px 10px 5px 0; font-family: sans-serif; font-size: 11px;
                         color: #888; white-space: nowrap; vertical-align: top; width: 18%;">
                {event.get('date', '')}
              </td>
              <td style="padding: 5px 0; font-family: Georgia, serif; font-size: 13px;
                         {title_style} vertical-align: top; line-height: 1.5;">
                {highlight_dot}{event.get('title', '')}{prep}
              </td>
            </tr>"""
        sections_html.append(_section("The week ahead", f'<table style="width: 100%; border-collapse: collapse;">{rows}</table>'))

    # ── 4. Open loops ─────────────────────────────────────────────────────
    open_loops = briefing.get("open_loops_from_last_week", [])
    if open_loops:
        sections_html.append(_section("Open loops from last week", _ul(open_loops)))

    # ── 5. Closing thought ────────────────────────────────────────────────
    closing = briefing.get("closing_thought", "")
    if closing:
        sections_html.append(_section("Closing thought", _p(f"<em>{closing}</em>")))

    body = "\n".join(sections_html)

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin: 0; padding: 0; background: #e8e2d9;">
  <div style="max-width: 640px; margin: 0 auto; background: #faf7f2;">

    <div style="background: #1a1a1a; padding: 24px 32px;">
      <h1 style="font-family: Georgia, serif; font-size: 18px; color: #f5f0e8; margin: 0 0 2px 0; letter-spacing: 0.02em;">
        Weekly Brief
      </h1>
      <p style="font-family: sans-serif; font-size: 11px; color: #666; margin: 0; letter-spacing: 0.04em;">
        {week_of.upper()}
      </p>
    </div>

    <div style="padding: 28px 32px 8px 32px;">
      {body}
    </div>

    <div style="padding: 0 32px 24px 32px; border-top: 1px solid #e8e2d9;">
      <p style="font-family: sans-serif; font-size: 11px; color: #bbb; margin: 14px 0 0 0;">
        Follow-up drafts are in Gmail Drafts. Red dot = highlighted event.
      </p>
    </div>

  </div>
</body>
</html>"""


def get_week_label() -> str:
    return datetime.now().strftime("%B %d, %Y")
