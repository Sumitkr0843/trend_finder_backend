import requests
from config.config import FIRECRAWL_API_KEY


# Reddit shut down self-service OAuth app creation in Nov 2025 (the
# "Responsible Builder Policy" you hit on prefs/apps). New OAuth tokens now
# require manual approval, and small/personal projects are routinely
# rejected or never answered - so scripted OAuth access isn't a realistic
# path here. The public reddit.com/*.json endpoints are also increasingly
# WAF-blocked (403) regardless of headers.
#
# Fallback: Firecrawl's /search endpoint runs a normal web search
# (site:reddit.com <keyword>) and returns page content directly - no Reddit
# API involved at all, so none of the above applies. Trade-off: you get
# titles, urls, and post content, but not exact upvote/comment counts
# (Reddit doesn't expose those in search-engine snippets). That's fine for
# the "mine hooks and pain points" step, which is the part that matters.

FIRECRAWL_SEARCH_URL = "https://api.firecrawl.dev/v2/search"


def search_reddit(keyword, limit=15):
    if not FIRECRAWL_API_KEY:
        print(
            "Reddit Error: Missing FIRECRAWL_API_KEY in .env. "
            "Sign up free at https://firecrawl.dev to get one."
        )
        return []

    try:
        resp = requests.post(
            FIRECRAWL_SEARCH_URL,
            headers={
                "Authorization": f"Bearer {FIRECRAWL_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "query": f"site:reddit.com {keyword}",
                "limit": limit,
                "scrapeOptions": {"formats": [{"type": "markdown"}]},
            },
            timeout=30,
        )
        resp.raise_for_status()
        payload = resp.json()

        items = (payload.get("data") or {}).get("web") or []

        results = []
        for item in items:
            results.append({
                "platform": "reddit",
                "title": item.get("title", ""),
                "description": (item.get("markdown") or item.get("description") or "")[:2000],
                "author": "",
                "url": item.get("url", ""),
                "views": 0,
                # Firecrawl's search results don't expose Reddit's own
                # score/comment counts - only what's on the page/snippet.
                "likes": 0,
                "comments": 0,
                "published": "",
            })

        print(f"Reddit (via Firecrawl): {len(results)} results")
        return results

    except Exception as e:
        print(f"Reddit Error: {e}")
        return []