from apify_client import ApifyClient
from config.config import APIFY_TOKEN



def resolve_instagram_creators(keyword, count=6):
    client = ApifyClient(APIFY_TOKEN)

    run_input = {
        "search": keyword,
        "searchType": "user",  
        "searchLimit": count,
    }

    try:
        run = client.actor("apify/instagram-search-scraper").call(run_input=run_input)

        usernames = []
        for item in client.dataset(run.default_dataset_id).iterate_items():
            username = (
                item.get("username")
                or item.get("ownerUsername")
                or (item.get("user") or {}).get("username")
            )
            if username and username not in usernames:
                usernames.append(username)

        print(f"Instagram: resolved {len(usernames)} creator handles for '{keyword}': {usernames}")
        return usernames[:count]

    except Exception as e:
        print("Instagram creator-resolution error:", e)
        return []


def _is_relevant(caption, keyword):
    """Cheap relevance filter so an off-topic viral reel from a niche
    creator doesn't pollute the brief. Checks whether any keyword token
    appears in the caption (case-insensitive)."""
    if not caption:
        return False
    caption_l = caption.lower()
    tokens = [t for t in keyword.lower().split() if len(t) > 2]
    if not tokens:
        return True
    return any(t in caption_l for t in tokens)


def search_instagram(keyword, creator_count=6, results_per_creator=3):
    usernames = resolve_instagram_creators(keyword, count=creator_count)
    if not usernames:
        print("Instagram: no creator handles resolved, skipping reel fetch.")
        return []

    client = ApifyClient(APIFY_TOKEN)

    run_input = {
        "username": usernames,
        "resultsLimit": results_per_creator,
        "skipPinnedPosts": False,
        "skipTrialReels": False,
        "includeSharesCount": False,
        "includeTranscript": False,
        "includeDownloadedVideo": False,
    }

    try:
        run = client.actor("xMc5Ga1oCONPmWJIa").call(run_input=run_input)

        print("Instagram Dataset:", run.default_dataset_id)

        results = []

        for item in client.dataset(run.default_dataset_id).iterate_items():
            caption = item.get("caption") or ""

            if not _is_relevant(caption, keyword):
                continue

            results.append({
                "platform": "instagram",
                "title": caption,
                "description": caption,
                "author": item.get("ownerUsername") or "",
                "url": item.get("url") or "",
                "views": item.get("videoPlayCount") or 0,
                "likes": item.get("likesCount") or 0,
                "comments": item.get("commentsCount") or 0,
                "published": item.get("timestamp") or ""
            })

        return results

    except Exception as e:
        print("Instagram Error:", e)
        return []