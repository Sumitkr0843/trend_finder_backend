from apify_client import ApifyClient
from config.config import APIFY_TOKEN


def search_youtube(keyword):
    client = ApifyClient(APIFY_TOKEN)

    run_input = {
        "searchQueries": [keyword],
        "maxResults": 5,
        "maxResultsShorts": 0,
        "maxResultStreams": 0,
        "downloadSubtitles": False,
        "sortingOrder": "relevance",
        "dateFilter": "month",
        "videoType": "video",
        "aiVideoDescription": False,
        "aiVideoSummary": False,
    }

    try:
        run = client.actor("h7sDV53CddomktSi5").call(
            run_input=run_input
        )

        print("YouTube Dataset:", run.default_dataset_id)

        results = []

        for item in client.dataset(run.default_dataset_id).iterate_items():

            results.append({
                "platform": "youtube",
                "title": item.get("title") or "",
                "description": item.get("description") or "",
                "author": item.get("channelName") or "",
                "url": item.get("url") or "",
                "views": item.get("viewCount") or 0,
                "likes": item.get("likes") or 0,
                "comments": item.get("commentsCount") or 0,
                "published": item.get("publishedTimeText") or ""
            })

        return results

    except Exception as e:
        print("YouTube Error:", e)
        return []