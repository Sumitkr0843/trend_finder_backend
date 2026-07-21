"""

Then the frontend calls: POST http://localhost:8000/api/search

"""

from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from scripts.reddit import search_reddit
from scripts.youtube import search_youtube
from scripts.tiktok import search_tiktok
from scripts.instagram import search_instagram
from scripts.x import search_x
from scripts.ranking import RankingEngine
from scripts.analyzer import TrendAnalyzer

app = FastAPI(title="Trend Finder API")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class SearchRequest(BaseModel):
    niche: str
    limit: int = 20


class SearchResponse(BaseModel):
    niche: str
    posts: list
    report: dict | None = None


class RevisionData(BaseModel):
    instruction: str
    previous_draft: dict | str
    failed_checks: list[dict] = []
    suggestions: list[str] = []


class GenerateRequest(BaseModel):
    brief: str
    platform: str
    content_type: str = "post"
    revision: RevisionData | None = None

class GenerateResponse(BaseModel):
    draft: dict | None = None
    error: str | None = None


class ReviewRequest(BaseModel):
    draft: dict | str  # the generated draft object (or raw text)
    brand_voice: str = ""
    checklist: str = ""  # newline-separated, one rule per line


class ReviewResponse(BaseModel):
    review: dict | None = None  # {"checks": [...], "suggestions": [...]}
    error: str | None = None


@app.post("/api/search", response_model=SearchResponse)
def search(req: SearchRequest):
    keyword = req.niche.strip()


    scrapers = (
        search_reddit,
        search_youtube,
        search_tiktok,
        search_instagram,
        search_x,
    )

    with ThreadPoolExecutor(max_workers=len(scrapers)) as pool:
        batches = list(pool.map(lambda fn: fn(keyword), scrapers))

    all_results = [post for batch in batches for post in batch]

    ranked_posts = RankingEngine.top_posts(all_results, limit=req.limit)

    report = TrendAnalyzer.mine(keyword, ranked_posts)

    return SearchResponse(niche=keyword, posts=ranked_posts, report=report)


@app.post("/api/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest):
    draft = TrendAnalyzer.generate_content(
        req.brief, req.platform, req.content_type,
        revision=req.revision.model_dump() if req.revision else None,
    )
    if draft is None:
        return GenerateResponse(
            draft=None,
            error="Generation failed - check the API server logs "
                  "(is Ollama running and the platform valid?).",
        )
    return GenerateResponse(draft=draft)


@app.post("/api/review", response_model=ReviewResponse)
def review(req: ReviewRequest):
    # Step 4: proofread the generated draft against the user's brand voice +
    # checklist with a separate reviewer call. review_content skips the AI and
    # returns an empty result when both are blank.
    try:
        result = TrendAnalyzer.review_content(
            req.draft, req.brand_voice, req.checklist
        )
    except RuntimeError as e:
        # LLM unreachable / invalid JSON / other failure -> 500 with a message.
        raise HTTPException(status_code=500, detail=str(e))

    return ReviewResponse(review=result)


@app.get("/api/health")
def health():
    return {"status": "ok"}