import json
import os
from concurrent.futures import ThreadPoolExecutor

from scripts.reddit import search_reddit
from scripts.render import render
from scripts.youtube import search_youtube
from scripts.tiktok import search_tiktok
from scripts.instagram import search_instagram
from scripts.ranking import RankingEngine
from scripts.analyzer import TrendAnalyzer


def save_results(results):
    os.makedirs("output", exist_ok=True)

    with open("output/ranked_posts.json", "w", encoding="utf-8") as file:
        json.dump(results, file, indent=4, ensure_ascii=False)

    print("\n Results saved to output/ranked_posts.json")


def main():
    print("=" * 60)
    print(" Trend Finder")
    print("=" * 60)

    keyword = input("Enter your niche: ").strip()

    sources = (
        ("Reddit", search_reddit),
        ("YouTube", search_youtube),
        ("TikTok", search_tiktok),
        ("Instagram", search_instagram),
    )

    print("\n Searching Reddit, YouTube, TikTok, Instagram , X")

    # Run the scrapers concurrently; each one blocks on a remote actor run.
    with ThreadPoolExecutor(max_workers=len(sources)) as pool:
        batches = list(pool.map(lambda s: s[1](keyword), sources))

    all_results = []

    for (name, _), batch in zip(sources, batches):
        print(f"✓ {name}: {len(batch)} results")
        all_results.extend(batch)

    print(f"\n Total Results Collected: {len(all_results)}")


    ranked_posts = RankingEngine.top_posts(
        all_results,
        limit=20
    )

    RankingEngine.print_top_posts(ranked_posts)


    TrendAnalyzer.prepare(ranked_posts)


    save_results(ranked_posts)

    # ---------------- Mine (Gemini API) ----------------
    print("\n Mining results into a content brief...")
    report = TrendAnalyzer.mine(keyword, ranked_posts)

    # ---------------- Render dashboard ----------------
    if report:
        print("\n Rendering dashboard...")
        render(out_dir="output", niche=keyword)


    print(" Python Phase Completed")




if __name__ == "__main__":
    main()