import httpx
import json
import re
from config import settings


ANALYSIS_PROMPT = """
You are an expert short-form content strategist specializing in viral clip selection.

Analyze the following transcript and find the TOP 5 most clip-worthy moments.

## Campaign Rules
{campaign_rules}

## Transcript
{transcript_text}

## Selection Criteria
- Hook strength: Does the first sentence stop a scroller?
- Emotional impact: Does it create feeling (loss, inspiration, shock, humor)?
- Curiosity gap: Does it make someone want to know more?
- Novelty: Is this surprising or counter-intuitive?
- Completeness: Can it stand alone without context?

## Output Format
Return ONLY a valid JSON array. No explanation. No markdown. No extra text.

[
  {{
    "start": "HH:MM:SS",
    "end": "HH:MM:SS",
    "hook": "Rewritten opening line optimized for retention",
    "category": "emotional_story | controversy | educational | funny | curiosity_gap",
    "score": 0,
    "reason": "One sentence explaining why this moment works"
  }}
]

Rules:
- Each clip must be between {min_length}s and {max_length}s
- Avoid topics: {forbidden_topics}
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
        f"Forbidden topics: {', '.join(campaign.get('forbidden_topics', []))}\n"
        f"Style notes: {campaign.get('style_notes', 'none')}"
    )


def timestamp_to_seconds(ts: str) -> float:
    parts = ts.split(":")
    h, m, s = int(parts[0]), int(parts[1]), float(parts[2])
    return h * 3600 + m * 60 + s


def analyze(segments: list[dict], campaign: dict | None) -> list[dict]:
    """
    Sends transcript to Ollama LLM and returns list of viral moments.
    """
    transcript_text = "\n".join(
        f"[{s['start']:.1f}s - {s['end']:.1f}s] {s['text']}" for s in segments
    )

    min_length = campaign.get("min_clip_length", 30) if campaign else 30
    max_length = campaign.get("max_clip_length", 60) if campaign else 60
    forbidden = ", ".join(campaign.get("forbidden_topics", [])) if campaign else "none"

    prompt = ANALYSIS_PROMPT.format(
        campaign_rules=format_campaign_rules(campaign),
        transcript_text=transcript_text,
        min_length=min_length,
        max_length=max_length,
        forbidden_topics=forbidden
    )

    response = httpx.post(
        f"{settings.ollama_base_url}/api/generate",
        json={
            "model": settings.ollama_model,
            "prompt": prompt,
            "stream": False
        },
        timeout=120.0
    )
    response.raise_for_status()
    raw = response.json().get("response", "")

    # Defensive JSON extraction
    try:
        match = re.search(r'\[.*\]', raw, re.DOTALL)
        if not match:
            raise ValueError("No JSON array found in LLM response")
        moments = json.loads(match.group())
    except Exception as e:
        raise ValueError(f"Failed to parse LLM response: {e}\nRaw: {raw}")

    # Convert timestamps to seconds
    for m in moments:
        m["start_seconds"] = timestamp_to_seconds(m["start"])
        m["end_seconds"] = timestamp_to_seconds(m["end"])

    return moments