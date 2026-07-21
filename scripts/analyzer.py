import json
import os
import re

from openai import OpenAI
from config.config import OPENAI_API_KEY, OPENAI_MODEL


_client = OpenAI(api_key=OPENAI_API_KEY)


def _call_llm(prompt: str) -> str:
    """Shared OpenAI call used by mine(), generate_content(), and
    review_content(). Returns the raw text response (still needs JSON
    parsing/fence-stripping by the caller)."""
    response = _client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content.strip()


ANALYSIS_PROMPT = """You are an expert viral content strategist.

You will receive ranked social media posts collected from Reddit, YouTube, TikTok and Instagram for the niche: "{keyword}"

Your job is to create a Content Brief.

Extract:
- Most repeated hooks
- Customer frustrations (pain points, in their own words)
- Exact customer language (copy-paste-able phrases)
- Best performing content formats
- Three original content ideas

Rules:
- Never fabricate a hook, quote, or number - everything must trace back to something actually in the data below.
- If the same pain point or phrase shows up on two or more platforms, that's a validated signal worth calling out.
- Posts with likes/comments/views all at 0 (typically Reddit) have no real engagement data - still mine them for
  qualitative content (pain points, language), but weight posts with real engagement numbers more heavily for
  "top_hooks" and "winning_formats".
- content_ideas must be plain strings, not objects - one clear sentence per idea, not a title/format/angle breakdown.

Return ONLY valid JSON, nothing else - no markdown fences, no explanation. Exact schema:

{{
  "niche": "{keyword}",
  "top_hooks": [],
  "pain_points": [],
  "customer_language": [],
  "winning_formats": [],
  "content_ideas": []
}}

Here is the ranked post data:

{posts_json}
"""


PLATFORM_GUIDANCE = {
    "instagram": (
        "Instagram Reel / post. The 'title' is a strong first-line caption "
        "hook. 'body' is the full caption (short, punchy, line breaks and a "
        "few emojis are fine). Provide 8-15 relevant hashtags. Suggest a "
        "quick visual/shot idea in 'tips'."
    ),
    "youtube": (
        "YouTube video. The 'title' is a clickable, SEO-aware video title "
        "(<70 chars). 'body' is a short script outline: hook, 3-5 beats, and "
        "an outro CTA. Provide 5-10 tags as 'hashtags'. Put thumbnail/retention "
        "advice in 'tips'."
    ),
    "reddit": (
        "Reddit post. The 'title' is an authentic, non-clickbait post title "
        "that fits Reddit culture. 'body' is the post text - conversational, "
        "value-first, no marketing tone. 'hashtags' MUST be an empty list "
        "(Reddit has no hashtags). Suggest fitting subreddits in 'tips'."
    ),
    "x": (
        "X (Twitter). Content must be concise. If a thread is appropriate, "
        "put each tweet on its own line in 'body' (numbered 1/, 2/, ...) and "
        "keep every tweet under 280 characters. 'title' is the opening/first "
        "tweet. Provide 1-3 relevant hashtags only. Put timing/engagement "
        "advice in 'tips'."
    ),
}

PLATFORM_ALIASES = {
    "ig": "instagram",
    "insta": "instagram",
    "instagram": "instagram",
    "yt": "youtube",
    "youtube": "youtube",
    "reddit": "reddit",
    "x": "x",
    "twitter": "x",
}

CONTENT_TYPE_GUIDANCE = {
    "post": (
        "Format as a single standalone post/caption for the platform."
    ),
    "tweets": (
        "Format as X/Twitter-style tweets. If more than one, make it a "
        "numbered thread (1/, 2/, ...), each tweet under 280 characters, "
        "one tweet per line in 'body'."
    ),
    "scripts": (
        "Format as a short spoken video script with clear beats: a hook line, "
        "the main talking points, and an outro/CTA. Write it to be read aloud."
    ),
    "story": (
        "Format as a short vertical Story sequence: break 'body' into a few "
        "frames (Frame 1:, Frame 2:, ...), each with one punchy line of "
        "on-screen text plus a quick note on the visual."
    ),
}

CONTENT_TYPE_ALIASES = {
    "post": "post",
    "posts": "post",
    "tweet": "tweets",
    "tweets": "tweets",
    "script": "scripts",
    "scripts": "scripts",
    "story": "story",
    "stories": "story",
}

GENERATE_PROMPT = """You are an expert social media content creator.

Write an original piece of content for the platform: "{platform}".
Content type/format requested: "{content_type}".

Content brief from the user:
\"\"\"{brief}\"\"\"

Platform guidance:
{guidance}

Format guidance:
{type_guidance}

Rules:
- Tailor tone, length, and structure to the platform AND content type above.
- Be concrete and ready-to-post - no placeholders like [insert here].
- Return ONLY valid JSON, nothing else - no markdown fences, no explanation.

Exact schema:
{{
  "platform": "{platform}",
  "content_type": "{content_type}",
  "title": "",
  "hook": "",
  "body": "",
  "hashtags": [],
  "call_to_action": "",
  "tips": []
}}
"""

REVISION_PROMPT = """You are an expert social media content creator, revising an existing draft.

Platform: "{platform}"
Content type/format: "{content_type}"

Original content brief from the user:
\"\"\"{brief}\"\"\"

Platform guidance:
{guidance}

Format guidance:
{type_guidance}

Current draft (JSON):
{previous_draft_json}

This draft failed the following checks:
{failed_checks_block}

Suggestions to address:
{suggestions_block}

Rules:
- Revise the draft to fix the failed checks and apply the suggestions above.
- Keep everything that already works unchanged - do not rewrite parts that
  weren't flagged.
- Tailor tone, length, and structure to the platform AND content type above.
- Be concrete and ready-to-post - no placeholders like [insert here].
- Return ONLY valid JSON, nothing else - no markdown fences, no explanation.

Exact schema:
{{
  "platform": "{platform}",
  "content_type": "{content_type}",
  "title": "",
  "hook": "",
  "body": "",
  "hashtags": [],
  "call_to_action": "",
  "tips": []
}}
"""

REVIEW_PROMPT = """You are a meticulous content reviewer / proofreader.

You will be given a generated content draft, a brand voice description, and a
checklist of rules. Evaluate the draft against the brand voice AND against each
checklist rule.

Brand voice:
\"\"\"{brand_voice}\"\"\"

Checklist rules (evaluate each one separately, in this order):
{checklist_block}

The draft to review (JSON):
{draft_json}

Rules for your evaluation:
- Produce exactly one entry in "checks" for each checklist rule above, in the
  same order. Set "passed" to true only if the draft clearly satisfies that
  rule; otherwise false. Keep "reason" to one short sentence.
- For any check that fails, "reason" MUST include the exact offending text
  quoted from the draft. If you cannot quote specific text that violates the
  rule, mark it as passed instead.
- If there are no checklist rules, "checks" must be an empty array.
- Use the brand voice to inform your reasoning and to drive "suggestions":
  concrete, actionable edits that would better match the brand voice or fix any
  failed checks. If everything is perfect, "suggestions" may be an empty array.
- Judge only what is actually in the draft - do not invent problems.

Return ONLY valid JSON, nothing else - no markdown fences, no explanation.
Exact schema:
{{
  "checks": [{{ "item": "the checklist rule text", "passed": true, "reason": "" }}],
  "suggestions": []
}}
"""


class TrendAnalyzer:

    @staticmethod
    def review_content(draft, brand_voice="", checklist=""):
        """Step 4 of the pipeline: a SEPARATE reviewer call (distinct from
        generate_content) that proofreads a draft against a user-defined brand
        voice and checklist using Gemini. Returns a dict shaped
        {"checks": [...], "suggestions": [...]}.

        Returns an empty result ({"checks": [], "suggestions": []}) without
        calling the model when both brand_voice and checklist are empty.
        Raises RuntimeError with a descriptive message if the model call fails
        or returns invalid JSON (the route turns this into a 500)."""

        brand_voice = (brand_voice or "").strip()
        checklist = (checklist or "").strip()

        if not brand_voice and not checklist:
            return {"checks": [], "suggestions": []}

        rules = [line.strip() for line in checklist.splitlines() if line.strip()]
        if rules:
            checklist_block = "\n".join(
                f"{i + 1}. {rule}" for i, rule in enumerate(rules)
            )
        else:
            checklist_block = "(no checklist rules provided)"

        prompt = REVIEW_PROMPT.format(
            brand_voice=brand_voice or "(no brand voice provided)",
            checklist_block=checklist_block,
            draft_json=json.dumps(draft, indent=2, ensure_ascii=False),
        )

        try:
            text = _call_llm(prompt)
            text = re.sub(r"^```json\s*|\s*```$", "", text)
            result = json.loads(text)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Reviewer response wasn't valid JSON: {e}")
        except Exception as e:
            raise RuntimeError(f"Review failed: {e}")

        checks = []
        for c in result.get("checks", []) if isinstance(result, dict) else []:
            if not isinstance(c, dict):
                continue
            raw_passed = c.get("passed", False)
            if isinstance(raw_passed, str):
                passed = raw_passed.strip().lower() == "true"
            else:
                passed = bool(raw_passed)
            checks.append({
                "item": str(c.get("item", "")),
                "passed": passed,
                "reason": str(c.get("reason", "")),
            })

        raw_suggestions = result.get("suggestions", []) if isinstance(result, dict) else []
        suggestions = []
        for s in raw_suggestions:
            if isinstance(s, dict):
                parts = [str(v).strip() for v in s.values() if str(v).strip()]
                text_val = " — ".join(parts)
            else:
                text_val = str(s).strip()
            if text_val:
                suggestions.append(text_val)

        print(f"[OK] draft reviewed ({len(checks)} checks, "
              f"{len(suggestions)} suggestions) via Gemini/{OPENAI_MODEL}")
        return {"checks": checks, "suggestions": suggestions}

    @staticmethod
    def generate_content(brief, platform, content_type="post", revision=None):
        """Generate a platform-tailored content draft from a free-text brief
        using Gemini (same engine as mine()). Returns a dict matching the
        GENERATE_PROMPT schema, or None on failure.

        If `revision` is provided (dict with previous_draft, failed_checks,
        suggestions), builds a revision prompt against the existing draft
        instead of generating from scratch."""

        key = (platform or "").strip().lower()
        canonical = PLATFORM_ALIASES.get(key)
        if canonical is None:
            print(f"Generator Error: unknown platform '{platform}'. "
                  f"Expected one of: ig, yt, reddit, x.")
            return None

        type_key = (content_type or "post").strip().lower()
        canonical_type = CONTENT_TYPE_ALIASES.get(type_key)
        if canonical_type is None:
            print(f"Generator Error: unknown content type '{content_type}'. "
                  f"Expected one of: post, tweets, scripts, story.")
            return None

        if not (brief or "").strip():
            print("Generator Error: brief is empty.")
            return None

        if revision:
            failed_checks = revision.get("failed_checks", []) or []
            suggestions = revision.get("suggestions", []) or []
            previous_draft = revision.get("previous_draft", "") or ""

            failed_checks_block = "\n".join(
                f"- {c.get('item', '')}: {c.get('reason', '')}" for c in failed_checks
            ) or "(none listed)"
            suggestions_block = "\n".join(f"- {s}" for s in suggestions) or "(none listed)"

            prompt = REVISION_PROMPT.format(
                platform=canonical,
                content_type=canonical_type,
                brief=brief.strip(),
                guidance=PLATFORM_GUIDANCE[canonical],
                type_guidance=CONTENT_TYPE_GUIDANCE[canonical_type],
                previous_draft_json=json.dumps(previous_draft, indent=2, ensure_ascii=False),
                failed_checks_block=failed_checks_block,
                suggestions_block=suggestions_block,
            )
        else:
            prompt = GENERATE_PROMPT.format(
                platform=canonical,
                content_type=canonical_type,
                brief=brief.strip(),
                guidance=PLATFORM_GUIDANCE[canonical],
                type_guidance=CONTENT_TYPE_GUIDANCE[canonical_type],
            )

        try:
            text = _call_llm(prompt)
            text = re.sub(r"^```json\s*|\s*```$", "", text)

            draft = json.loads(text)
            draft["platform"] = canonical
            draft["content_type"] = canonical_type
            action = "revised" if revision else "generated"
            print(f"[OK] {canonical_type} draft {action} for {canonical} "
                  f"(Gemini/{OPENAI_MODEL})")
            return draft

        except json.JSONDecodeError as e:
            print(f"Generator Error: Gemini's response wasn't valid JSON: {e}")
            return None
        except Exception as e:
            print(f"Generator Error: {e}")
            return None

    @staticmethod
    def prepare(posts):
        os.makedirs("output", exist_ok=True)
        with open("output/ranked_posts.json", "w", encoding="utf-8") as file:
            json.dump(posts, file, indent=4, ensure_ascii=False)
        print("[OK] ranked_posts.json created")

    @staticmethod
    def mine(keyword, posts):
        """Calls Gemini to mine ranked posts into a content brief. Writes
        output/report.json."""

        prompt = ANALYSIS_PROMPT.format(
            keyword=keyword,
            posts_json=json.dumps(posts, indent=2, ensure_ascii=False),
        )

        try:
            text = _call_llm(prompt)
            text = re.sub(r"^```json\s*|\s*```$", "", text)

            report = json.loads(text)

            os.makedirs("output", exist_ok=True)
            with open("output/report.json", "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

            print(f"[OK] report.json generated (mined via Gemini/{OPENAI_MODEL})")
            return report

        except json.JSONDecodeError as e:
            print(f"Analyzer Error: Gemini's response wasn't valid JSON: {e}")
            return None
        except Exception as e:
            print(f"Analyzer Error: {e}")
            return None