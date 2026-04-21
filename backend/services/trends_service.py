"""
Trends analysis: computes category counts, keyword frequency, daily snapshots.
"""
from datetime import datetime, date
from typing import Dict
from collections import Counter
from database import get_collection
from core.logger import get_logger

logger = get_logger()

import json
import asyncio
from typing import Dict, List
from collections import Counter, defaultdict
from database import get_collection
from core.logger import get_logger
from config import settings

logger = get_logger()

try:
    import google.generativeai as genai
    _gemini_ok = True
except ImportError:
    _gemini_ok = False

MOCK_MODE = not settings.gemini_api_key or not _gemini_ok

if not MOCK_MODE:
    genai.configure(api_key=settings.gemini_api_key)
    _model = genai.GenerativeModel(
        model_name=settings.gemini_model,
        generation_config=genai.types.GenerationConfig(temperature=0.3, max_output_tokens=3000),
    )

TRENDS_PROMPT = """\
You are an expert news analyst. Review these top headlines and summaries for today.
Target Language for trends logic representation: {language}.

Based on these articles, generate:
1. "overview": A 4-6 sentence summary covering major geopolitical, economic, and significant events today.
2. "top_themes": A list of 3-5 major overarching themes (not single words, use short phrases like "Tech layoffs continue").
3. "category_insights": A dictionary, pick top 1 or 2 categories and explain why they dominated (1 sentence each).

Return ONLY valid JSON (no markdown, no extra text):
{{
  "overview": "<4-6 sentence summary>",
  "top_themes": ["<theme 1>", "<theme 2>", "<theme 3>"],
  "category_insights": {{
    "finance": "Markets dominated news due to...",
    "politics": "Elections in various regions drove discussions..."
  }}
}}"""

STOP_WORDS = {
    "the", "a", "an", "is", "in", "on", "at", "to", "for", "of", "and", "or",
    "but", "with", "has", "have", "been", "were", "was", "will", "that", "this",
    "from", "by", "as", "are", "its", "it", "not", "be", "more", "new", "says",
    "said", "after", "over", "into", "about", "than", "up", "what", "how", "he",
    "she", "they", "his", "her", "their", "also", "year", "first", "two", "one",
}


async def _generate_ai_trends(articles: List[dict], language: str) -> dict:
    if MOCK_MODE or not articles:
        return {
            "overview": "AI Summary not available. Today saw a variety of standard news coverage across multiple sectors. Key events remain developing.",
            "top_themes": ["General Headlines", "Varied News Coverage", "Daily Updates"],
            "category_insights": {"general": "A mix of standard daily news."}
        }
    
    # Take top ~40 articles for the prompt
    sorted_arts = sorted(articles, key=lambda a: -(a.get("importance_score") or 5))[:40]
    art_text = "\\n".join([f"- [{a.get('category', 'general')}] {a.get('title', '')}: {a.get('summary', '')}" for a in sorted_arts])
    
    prompt = TRENDS_PROMPT.format(language=language) + "\\n\\nToday's Articles:\\n" + art_text
    
    try:
        response = await asyncio.to_thread(_model.generate_content, prompt)
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        data = json.loads(text.strip())
        return {
            "overview": data.get("overview", "Overview unavailable."),
            "top_themes": data.get("top_themes", []),
            "category_insights": data.get("category_insights", {})
        }
    except Exception as e:
        logger.error(f"Gemini trends generation error dict: {e}")
        return {
            "overview": "Failed to generate AI trends overview.",
            "top_themes": [],
            "category_insights": {}
        }


async def compute_trends() -> Dict:
    """Compute category + keyword trends, and AI insights per language."""
    news_col = get_collection("news")
    trends_col = get_collection("trends")
    today = date.today().isoformat()

    from_date = datetime.combine(date.today(), datetime.min.time())
    cursor = news_col.find({"scraped_at": {"$gte": from_date}})
    all_articles = await cursor.to_list(length=2000)

    if not all_articles:
        logger.warning(f"No articles found for {today} trends computation.")
        return {}

    articles_by_lang = defaultdict(list)
    for art in all_articles:
        lang = art.get("language", "en")
        articles_by_lang[lang].append(art)
    
    results = {}
    
    for lang, articles in articles_by_lang.items():
        category_counts: Counter = Counter()
        all_keywords: list = []

        for art in articles:
            category_counts[art.get("category", "general")] += 1

            for kw in art.get("keywords", []):
                word = kw.lower().strip()
                if word and word not in STOP_WORDS and word.isalpha():
                    all_keywords.append(word)

            for w in art.get("title", "").split():
                w = w.lower().strip(".,!?\\\"'()")
                if len(w) > 4 and w not in STOP_WORDS and w.isalpha():
                    all_keywords.append(w)

        kw_freq = Counter(all_keywords)
        trending_keywords = [{"word": w, "count": c} for w, c in kw_freq.most_common(25)]
        most_covered = category_counts.most_common(1)[0][0] if category_counts else "N/A"

        ai_data = await _generate_ai_trends(articles, lang)

        doc_id = f"{today}_{lang}"
        doc = {
            "date": today,
            "language": lang,
            "category_counts": dict(category_counts),
            "trending_keywords": trending_keywords,
            "most_covered": most_covered,
            "total_articles": len(articles),
            "computed_at": datetime.utcnow(),
            "overview": ai_data["overview"],
            "top_themes": ai_data["top_themes"],
            "category_insights": ai_data["category_insights"],
        }
        await trends_col.update_one({"date": today, "language": lang}, {"$set": doc}, upsert=True)
        results[lang] = doc
        logger.info(f"Trends computed | date={today} lang={lang} articles={len(articles)}")

    return results
