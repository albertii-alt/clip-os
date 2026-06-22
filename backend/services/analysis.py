import json
import re
from google import genai
from config import settings


ANALYSIS_PROMPT = """
You are an expert short-form content strategist specializing in viral clip selection.

Analyze the following transcript and find the TOP 5 most clip-worthy moments.

## Campaign Rules
{campaign_rules}

## CREATOR STYLE DIRECTIVE (HIGH PRIORITY — follow this strictly)
{style_notes}
This directive overrides general selection criteria. Only select moments that match this style.

## Transcript
{transcript_text}

## Selection Criteria
- Hook strength: Does the first sentence stop a scroller?
- Emotional impact: Does it create feeling (loss, inspiration, shock, humor)?
- Curiosity gap: Does it make someone want to know more?
- Novelty: Is this surprising or counter-intuitive?
- Completeness: Can it stand alone without context?
- Hook caption quality: Write a comment-style hook caption (15-25 words) that teases the moment the way an engaging social media comment or caption would. It should build curiosity or emotional investment without giving away the full outcome. Think the style of: "She thought she'd never see her family again, but what happened next changed everything." or "He had one shot to fix this mistake, and what he did next surprised everyone." Write in normal sentence case, not all caps (the renderer handles uppercase styling separately). End the caption with exactly one relevant emoji that matches the tone of the moment (e.g. 😱 for shocking, 😢 for emotional, 🤯 for mind-blowing, 😂 for funny).

## Output Format
Return ONLY a valid JSON array. No explanation. No markdown. No extra text.

[
  {{
    "start": "MM:SS",
    "end": "MM:SS",
    "hook": "Rewritten opening line optimized for retention",
    "short_title": "Comment-style hook caption, 15-25 words, building curiosity, ending with one emoji",
    "category": "emotional_story | controversy | educational | funny | curiosity_gap",
    "score": 85,
    "reason": "One sentence explaining why this moment works"
  }}
]

Rules:
- Each clip must be between {min_length}s and {max_length}s
- Avoid topics: {forbidden_topics}
- score must be an integer between 0 and 100
- Return exactly 5 moments, sorted by score descending
"""


def format_campaign_rules(campaign: dict | None) -> str:
    if not campaign:
        return "No specific campaign rules. Select general high-retention moments."
    return (
        f"Platform: {campaign.get('platform', 'any')}\n"
        f"Required hashtags: {', '.join(campaign.get('required_hashtags', []))}\n"
        f"Required tags: {', '.join(campaign.get('required_tags', []))}\n"
        f"Clip length: {campaign.get('min_clip_length', 30)}s to {campaign.get('max_clip_length', 60)}s\n"
        f"Forbidden topics: {', '.join(campaign.get('forbidden_topics', []))}"
    )


def timestamp_to_seconds(ts: str) -> float:
    parts = ts.split(":")
    if len(parts) == 2:
        m, s = int(parts[0]), float(parts[1])
        return m * 60 + s
    elif len(parts) == 3:
        h, m, s = int(parts[0]), int(parts[1]), float(parts[2])
        return h * 3600 + m * 60 + s
    else:
        return float(ts)


def analyze(segments: list[dict], campaign: dict | None) -> list[dict]:
    """
    Sends full transcript to Gemini Flash and returns top 5 viral moments.
    Handles any video length thanks to Gemini's large context window.
    """
    # Build full transcript — no truncation needed with Gemini
    transcript_text = "\n".join(
        f"[{s['start']:.1f}s - {s['end']:.1f}s] {s['text']}" for s in segments
    )

    min_length = campaign.get("min_clip_length", 30) if campaign else 30
    max_length = campaign.get("max_clip_length", 60) if campaign else 60
    forbidden = ", ".join(campaign.get("forbidden_topics", [])) if campaign else "none"
    style_notes = campaign.get("style_notes", "No specific style directive.") if campaign else "No specific style directive."

    prompt = ANALYSIS_PROMPT.format(
        campaign_rules=format_campaign_rules(campaign),
        style_notes=style_notes,
        transcript_text=transcript_text,
        min_length=min_length,
        max_length=max_length,
        forbidden_topics=forbidden
    )

    # Call Gemini Flash
    client = genai.Client(api_key=settings.gemini_api_key)
    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=prompt
    )

    raw = response.text or ""
    print(f"[DEBUG] Gemini response: {raw[:300]}")

    # Defensive JSON extraction
    try:
        # Strip markdown code blocks if present
        clean = re.sub(r'```json|```', '', raw).strip()
        match = re.search(r'\[.*\]', clean, re.DOTALL)
        if not match:
            raise ValueError("No JSON array found in Gemini response")
        # Strip trailing commas before } or ] — Gemini sometimes outputs JS-style JSON
        json_str = re.sub(r',\s*([}\]])', r'\1', match.group())
        moments = json.loads(json_str)
    except Exception as e:
        raise ValueError(f"Failed to parse Gemini response: {e}\nRaw: {raw}")

    # Convert timestamps to seconds
    for m in moments:
        m["start_seconds"] = timestamp_to_seconds(m["start"])
        m["end_seconds"] = timestamp_to_seconds(m["end"])

    return moments