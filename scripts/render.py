import json
import os
import sys
import argparse
from datetime import datetime, timezone
from html import escape

PLATFORM_COLORS = {
    "youtube": "#ff0000",
    "tiktok": "#010101",
    "instagram": "#c13584",
    "reddit": "#ff4500",
}


def _badge(platform):
    color = PLATFORM_COLORS.get(platform.lower(), "#2563eb")
    return (
        f'<span style="background:{color};color:#fff;padding:3px 10px;'
        f'border-radius:999px;font-size:12px;font-weight:600;'
        f'text-transform:uppercase;letter-spacing:.03em;">{escape(platform)}</span>'
    )


def _list_cards(items):
    if not items:
        return '<p style="color:#94a3b8;">None found.</p>'
    return "".join(f'<li>{escape(str(x))}</li>' for x in items)


def render(out_dir="output", niche=""):
    report_path = os.path.join(out_dir, "report.json")
    posts_path = os.path.join(out_dir, "ranked_posts.json")

    if not os.path.exists(report_path):
        print(
            f"Error: {report_path} not found.\n"
            "Run the mining step first (Claude reading ranked_posts.json against "
            "the analysis prompt) to produce report.json before rendering."
        )
        sys.exit(1)

    if not os.path.exists(posts_path):
        print(f"Error: {posts_path} not found. Run scripts/main.py first.")
        sys.exit(1)

    with open(report_path, encoding="utf-8") as f:
        report = json.load(f)

    with open(posts_path, encoding="utf-8") as f:
        posts = json.load(f)

    report_niche = report.get("niche", "")
    if niche and report_niche and report_niche.lower() != niche.lower():
        print(
            f"Warning: report.json was generated for niche '{report_niche}', "
            f"but you're rendering with niche '{niche}'. This dashboard may "
            f"not match your current data."
        )

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    def _title_cell(p):
        title = escape(str(p.get("title", "")))[:140]
        url = p.get("url", "")
        if url:
            return (
                f'<a href="{escape(url)}" target="_blank" rel="noopener noreferrer" '
                f'style="color:#0f172a;text-decoration:none;border-bottom:1px dotted #94a3b8;">'
                f'{title}</a>'
            )
        return title

    rows = "".join(
        f'''<tr>
            <td>{_badge(p.get("platform",""))}</td>
            <td>{_title_cell(p)}</td>
            <td style="text-align:right;">{p.get("engagement_score", p.get("score", 0))}</td>
            <td style="text-align:right;">{p.get("likes",0)}</td>
            <td style="text-align:right;">{p.get("comments",0)}</td>
            <td style="text-align:right;">{p.get("views",0)}</td>
        </tr>'''
        for p in posts
    )

    phrase_bank = "".join(
        f'<span style="display:inline-block;background:#eef2ff;color:#3730a3;'
        f'padding:6px 12px;border-radius:8px;margin:4px;font-size:13px;">'
        f'{escape(str(x))}</span>'
        for x in report.get("customer_language", [])
    )

    pain_quotes = "".join(
        f'<blockquote style="border-left:4px solid #ef4444;margin:0 0 12px 0;'
        f'padding:8px 16px;color:#334155;background:#fef2f2;border-radius:0 8px 8px 0;">'
        f'{escape(str(x))}</blockquote>'
        for x in report.get("pain_points", [])
    )

    idea_cards = "".join(
        f'<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;'
        f'padding:16px;margin-bottom:12px;">'
        f'<div style="font-size:11px;font-weight:700;color:#16a34a;text-transform:uppercase;'
        f'letter-spacing:.05em;margin-bottom:6px;">Make this next</div>'
        f'{escape(str(idea))}</div>'
        for idea in report.get("content_ideas", [])
    )

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Trend Finder - {escape(niche) or "Content Brief"}</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{
    font-family: -apple-system, Segoe UI, Roboto, Arial, sans-serif;
    background: #f8fafc;
    color: #0f172a;
    margin: 0;
    padding: 40px 24px;
  }}
  .wrap {{ max-width: 960px; margin: 0 auto; }}
  h1 {{ font-size: 28px; margin-bottom: 4px; }}
  .meta {{ color: #64748b; font-size: 13px; margin-bottom: 32px; }}
  .card {{
    background: #fff;
    padding: 24px;
    margin-bottom: 24px;
    border-radius: 14px;
    box-shadow: 0 1px 3px rgba(0,0,0,.06), 0 1px 2px rgba(0,0,0,.04);
  }}
  h2 {{ font-size: 16px; text-transform: uppercase; letter-spacing: .04em;
        color: #2563eb; margin-top: 0; margin-bottom: 16px; }}
  li {{ margin-bottom: 10px; line-height: 1.5; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
  td, th {{ border-bottom: 1px solid #e2e8f0; padding: 10px 8px; text-align: left; }}
  th {{ color: #64748b; font-weight: 600; font-size: 12px; text-transform: uppercase; }}
  tr:hover {{ background: #f8fafc; }}
  td a:hover {{ border-bottom-style: solid; color: #2563eb; }}
</style>
</head>
<body>
<div class="wrap">

  <h1>Trend Finder{f" - {escape(niche)}" if niche else ""}</h1>
  <div class="meta">Generated {generated_at} - {len(posts)} posts analyzed across Reddit, YouTube, TikTok, Instagram</div>

  <div class="card">
    <h2>Top Hooks to Steal</h2>
    <ul>{_list_cards(report.get("top_hooks", []))}</ul>
  </div>

  <div class="card">
    <h2>Pain Points (in their own words)</h2>
    {pain_quotes or '<p style="color:#94a3b8;">None found.</p>'}
  </div>

  <div class="card">
    <h2>Customer Language / Phrase Bank</h2>
    <div>{phrase_bank or '<p style="color:#94a3b8;">None found.</p>'}</div>
  </div>

  <div class="card">
    <h2>Winning Formats</h2>
    <ul>{_list_cards(report.get("winning_formats", []))}</ul>
  </div>

  <div class="card">
    <h2>Content Ideas</h2>
    {idea_cards or '<p style="color:#94a3b8;">None found.</p>'}
  </div>

  <div class="card">
    <h2>Top Trending Posts</h2>
    <table>
      <tr><th>Platform</th><th>Title</th><th>Score</th><th>Likes</th><th>Comments</th><th>Views</th></tr>
      {rows}
    </table>
  </div>

</div>
</body>
</html>
"""

    out_path = os.path.join(out_dir, "report.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"report.html generated at {out_path}")
    return out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="output")
    parser.add_argument("--niche", default="")
    args = parser.parse_args()
    render(out_dir=args.out_dir, niche=args.niche)