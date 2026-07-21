from typing import List


class RankingEngine:
    """
    Ranks content collected from multiple social media platforms
    using a normalized engagement score.
    """

    # Platform weight
    PLATFORM_WEIGHT = {
        "youtube": 1.0,
        "tiktok": 1.0,
        "instagram": 1.0,
        "reddit": 1.0,
        
    }

    @staticmethod
    def calculate_score(post: dict) -> float:

        views = float(post.get("views", 0) or 0)
        likes = float(post.get("likes", 0) or 0)
        comments = float(post.get("comments", 0) or 0)

        # Base engagement score
        base_score = (
            (views * 0.01) +
            (likes * 2) +
            (comments * 5)
        )

        platform = post.get("platform", "").lower()

        multiplier = RankingEngine.PLATFORM_WEIGHT.get(
            platform,
            1.0
        )

        final_score = base_score * multiplier

        return round(final_score, 2)

    @staticmethod
    def rank_posts(posts: List[dict]):

        ranked_posts = []

        for post in posts:

            post["engagement_score"] = RankingEngine.calculate_score(post)

            ranked_posts.append(post)

        ranked_posts.sort(
            key=lambda x: x["engagement_score"],
            reverse=True
        )

        return ranked_posts

    # Minimum number of slots reserved for a platform in the final list, so a
    # low-engagement source is not crowded out by a high-engagement one. A
    # platform that returns fewer posts than its floor simply gives the unused
    # slots back to the general pool - the total never shrinks because of it.
    PLATFORM_FLOOR = {
        "x": 5,
    }

    @staticmethod
    def top_posts(posts: List[dict], limit=20):

        ranked = RankingEngine.rank_posts(posts)

        if not RankingEngine.PLATFORM_FLOOR:
            return ranked[:limit]

        selected = []
        selected_ids = set()

        # Pass 1: reserve each platform's floor, best-scoring posts first.
        for platform, floor in RankingEngine.PLATFORM_FLOOR.items():

            quota = min(floor, limit - len(selected))

            if quota <= 0:
                break

            for post in ranked:

                if quota == 0:
                    break

                if id(post) in selected_ids:
                    continue

                if post.get("platform", "").lower() != platform:
                    continue

                selected.append(post)
                selected_ids.add(id(post))
                quota -= 1

        # Pass 2: backfill the remainder from the whole pool by score. This is
        # what keeps the total at `limit` when a floored platform under-delivers
        # (e.g. X returning nothing because of its rate limits).
        for post in ranked:

            if len(selected) >= limit:
                break

            if id(post) in selected_ids:
                continue

            selected.append(post)
            selected_ids.add(id(post))

        # Floor-reserved posts were appended out of order; restore score order.
        selected.sort(
            key=lambda x: x["engagement_score"],
            reverse=True
        )

        return selected

    @staticmethod
    def print_top_posts(posts):

        print("\n")
        print("=" * 80)
        print("🔥 TOP TRENDING CONTENT")
        print("=" * 80)

        for index, post in enumerate(posts, start=1):

            print(f"\n#{index}")

            print(f"Platform : {post['platform']}")
            print(f"Score    : {post['engagement_score']}")
            print(f"Likes    : {post['likes']}")
            print(f"Comments : {post['comments']}")
            print(f"Views    : {post['views']}")
            print(f"Title    : {post['title']}")