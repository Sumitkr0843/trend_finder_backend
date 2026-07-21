from apify_client import ApifyClient
from config.config import APIFY_TOKEN


def search_tiktok(keyword):
    client = ApifyClient(APIFY_TOKEN)

    run_input = {
        "searchQueries": [
            keyword
        ],
        "searchSection": "/video",

    "resultsPerPage": 3,

    "profileScrapeSections": [
        "videos"
    ],

    "profileSorting": "latest",

    "excludePinnedPosts": False,

    "maxFollowersPerProfile": 0,
    "maxFollowingPerProfile": 0,
    "videoSearchSorting": "MOST_RELEVANT",
    "videoSearchDateFilter": "PAST_MONTH",
    "scrapeRelatedSearchWords": False,
    "scrapeRelatedVideos": False,
    "scrapeAdditionalAuthorMeta": False,
    "shouldDownloadVideos": False,
    "shouldDownloadCovers": False,
    "shouldDownloadSlideshowImages": False,
    "shouldDownloadAvatars": False,
    "shouldDownloadMusicCovers": False,
    "downloadSubtitlesOptions": "NEVER_DOWNLOAD_SUBTITLES",
    "commentsPerPost": 0,
    "topLevelCommentsPerPost": 0,
    "maxRepliesPerComment": 0,
    "proxyCountryCode": "None"
    }

    try:

        run = client.actor("GdWCkxBtKWOsKjdch").call(
            run_input=run_input
        )

        print("TikTok Dataset:", run.default_dataset_id)

        results = []

        for item in client.dataset(run.default_dataset_id).iterate_items():

            results.append({
                "platform": "tiktok",
                "title": item.get("text") or "",
                "description": item.get("text") or "",
                "author": item.get("authorMeta", {}).get("name", ""),
                "url": item.get("webVideoUrl") or "",
                "views": item.get("playCount") or 0,
                "likes": item.get("diggCount") or 0,
                "comments": item.get("commentCount") or 0,
                "published": item.get("createTimeISO") or ""
            })

        return results

    except Exception as e:
        print("TikTok Error:", e)
        return []