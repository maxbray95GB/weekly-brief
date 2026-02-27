"""
Email formatter — turns the structured briefing dict into a clean,
formatted HTML email with sections and headers.
"""

from datetime import datetime


def _section(title: str, content: str) -> str:
    return f"""
    <div style="margin-bottom: 28px;">
      <h2 style="font-family: Georgia, serif; font-size: 15px; font-weight: bold;
                 color: #1a1a1a; text-transform: uppercase; letter-spacing: 0.08em;
                 border-bottom: 1px solid #ddd; padding-bottom: 6px; margin-bottom: 12px;">
        {title}
      </h2>
      {content}
    </div>
    """


def _p(text: str) -> str:
    return f'<p style="font-family: Georgia, serif; font-size: 14px; color: #333; line-height: 1.6; margin: 0 0 8px 0;">{text}</p>'


def _li(text: str) -> str:
    return f'<li style="font-family: Georgia, serif; font-size: 14px; color: #333; line-height: 1.6; margin-bottom: 4px;">{text}</li>'


def _ul(items: list[str]) -> str:
    lis = "".join(_li(i) for i in items)
    return f'<ul style="margin: 0; padding-left: 18px;">{lis}</ul>'


def build_html_email(briefing: dict, week_of: str) -> str:
    sections_html = []

    # ── At a glance ──────────────────────────────────────────────────────
    glance = briefing.get("at_a_glance", {})
    if glance:
        meetings = glance.get("meetings", 0)
        emails = glance.get("emails", 0)
        stats_html = f"""
        <div style="display: flex; gap: 24px; margin-bottom: 14px;">
          <div style="background: #f0ebe3; padding: 10px 18px; border-radius: 6px; text-align: center;">
            <div style="font-family: Georgia, serif; font-size: 22px; font-weight: bold; color: #1a1a1a;">{meetings}</div>
            <div style="font-family: sans-serif; font-size: 11px; color: #888; text-transform: uppercase; letter-spacing: 0.05em;">Meetings</div>
          </div>
          <div style="background: #f0ebe3; padding: 10px 18px; border-radius: 6px; text-align: center;">
            <div style="font-family: Georgia, serif; font-size: 22px; font-weight: bold; color: #1a1a1a;">{emails}</div>
            <div style="font-family: sans-serif; font-size: 11px; color: #888; text-transform: uppercase; letter-spacing: 0.05em;">Emails</div>
          </div>
        </div>"""

        bullets = []
        if glance.get("most_contacted"):
            bullets.append(f"<strong>Most contacted:</strong> {glance['most_contacted']}")
        if glance.get("momentum"):
            bullets.append(f"<strong>Momentum:</strong> {glance['momentum']}")
        if glance.get("watch_out"):
            bullets.append(f"<strong>Watch out:</strong> {glance['watch_out']}")

        sections_html.append(_section("This week at a glance", stats_html + _ul(bullets)))

    # ── Key learnings ────────────────────────────────────────────────────
    learnings = briefing.get("key_learnings", [])
    if learnings:
        sections_html.append(_section("Key learnings", _ul(learnings)))

    # ── Missed follow-ups ─────────────────────────────────────────────────
    missed = briefing.get("missed_follow_ups", [])
    if missed:
        items = []
        for m in missed:
            items.append(f"<strong>{m.get('person', '')}</strong> — {m.get('what', '')}. <em>{m.get('suggested_action', '')}</em>")
        sections_html.append(_section("Missed follow-ups", _ul(items)))

    # ── People ────────────────────────────────────────────────────────────
    people = briefing.get("people_spoke_to", [])
    if people:
        rows = ""
        for p in people:
            flag = " 🔔" if p.get("follow_up_needed") else ""
            rows += f"""<tr>
              <td style="padding: 5px 12px 5px 0; font-family: Georgia, serif; font-size: 13px;
                         font-weight: bold; color: #1a1a1a; white-space: nowrap; vertical-align: top; width: 30%;">
                {p.get('name', '')}{flag}
              </td>
              <td style="padding: 5px 0; font-family: Georgia, serif; font-size: 13px;
                         color: #555; line-height: 1.5;">
                {p.get('context', '')}
              </td>
            </tr>"""
        people_html = f'<table style="width: 100%; border-collapse: collapse;">{rows}</table>'
        sections_html.append(_section("Who you spoke to", people_html))

    # ── Docs ──────────────────────────────────────────────────────────────
    docs = briefing.get("docs_created_or_edited", [])
    if docs:
        items = []
        for d in docs:
            url = d.get("url", "")
            title = d.get("title", "Untitled")
            link = f'<a href="{url}" style="color: #5b7fa6;">{title}</a>' if url else title
            items.append(f"{link} — {d.get('significance', '')}")
        sections_html.append(_section("Documents", _ul(items)))

    # ── Open loops ────────────────────────────────────────────────────────
    open_loops = briefing.get("open_loops_from_last_week", [])
    if open_loops:
        sections_html.append(_section("Open loops from last week", _ul(open_loops)))

    # ── Week ahead ────────────────────────────────────────────────────────
    ahead = briefing.get("week_ahead_preview", [])
    if ahead:
        rows = ""
        for event in ahead:
            rows += f"""<tr>
              <td style="padding: 5px 12px 5px 0; font-family: sans-serif; font-size: 12px;
                         color: #888; white-space: nowrap; vertical-align: top; width: 20%;">
                {event.get('date', '')}
              </td>
              <td style="padding: 5px 12px 5px 0; font-family: Georgia, serif; font-size: 13px;
                         color: #1a1a1a; font-weight: bold; vertical-align: top; width: 30%;">
                {event.get('title', '')}
              </td>
              <td style="padding: 5px 0; font-family: Georgia, serif; font-size: 13px;
                         color: #666; font-style: italic; line-height: 1.5;">
                {event.get('prep_note', '')}
              </td>
            </tr>"""
        sections_html.append(_section("Week ahead", f'<table style="width: 100%; border-collapse: collapse;">{rows}</table>'))

    # ── Closing thought ───────────────────────────────────────────────────
    closing = briefing.get("closing_thought", "")
    if closing:
        sections_html.append(_section("Closing thought", _p(f"<em>{closing}</em>")))

    body = "\n".join(sections_html)

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin: 0; padding: 0; background: #f0ebe3;">
  <div style="max-width: 660px; margin: 0 auto; background: #faf7f2; padding: 0 0 40px 0;">

    <div style="background: #1a1a1a; padding: 28px 36px;">
      <h1 style="font-family: Georgia, serif; font-size: 20px; color: #f5f0e8; margin: 0 0 2px 0;">
        Weekly Brief
      </h1>
      <p style="font-family: sans-serif; font-size: 12px; color: #777; margin: 0;">
        {week_of}
      </p>
    </div>

    <div style="padding: 28px 36px;">
      {body}
    </div>

    <div style="padding: 0 36px; border-top: 1px solid #e0d8cc;">
      <p style="font-family: sans-serif; font-size: 11px; color: #bbb; margin: 14px 0 0 0;">
        Follow-up drafts are in your Gmail Drafts folder.
      </p>
    </div>

  </div>
</body>
</html>"""


def get_week_label() -> str:
    today = datetime.now()
    return f"Week of {today.strftime('%B %d, %Y')}"
