from apify_client import ApifyClient
from config.config import APIFY_TOKEN

ACTOR_ID = "61RPP7dywgiy0JPD0"  # apidojo/tweet-scraper (paid plan required)


def normalize_tweet(item: dict) -> dict:
    author = item.get("author") or {}
    if not isinstance(author, dict):
        author = {}

    text = item.get("text") or ""

    return {
        "platform": "x",
        "title": text,
        "description": text,
        "author": author.get("userName") or author.get("name") or "",
        "url": item.get("url") or item.get("twitterUrl") or "",
        "views": item.get("viewCount") or 0,
        "likes": item.get("likeCount") or 0,
        "comments": item.get("replyCount") or 0,
        "published": item.get("createdAt") or "",
    }


def search_x(keyword, return_count=15):
    client = ApifyClient(APIFY_TOKEN)

    run_input = {
        "searchTerms": [keyword],
        "maxItems": 100,
        "sort": "Latest",
        "tweetLanguage": "en",
    }

    try:
        run = client.actor(ACTOR_ID).call(run_input=run_input)
        dataset_id = run.default_dataset_id

        results = []
        for item in client.dataset(dataset_id).iterate_items():
            if item.get("noResults"):
                continue
            results.append(normalize_tweet(item))

        return results[:return_count]

    except Exception as e:
        print("X Error:", e)
        return []