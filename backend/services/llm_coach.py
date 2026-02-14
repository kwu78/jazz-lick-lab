import json
import logging

from schemas.analysis import AnalysisResponse
from schemas.coaching import CoachingResponse
from services.llm_client import AnthropicClient

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a jazz music coach. Given a JSON analysis of a jazz lick, produce \
coaching feedback as a single JSON object. Output ONLY valid JSON with no \
markdown, no code fences, no extra commentary.

The JSON must have exactly these fields:
- "summary": string — 1-2 sentence overview of the lick
- "why_it_works": string — explain why the lick sounds good harmonically
- "practice_steps": list of 3-5 short strings — actionable practice steps
- "variation_idea": string — one creative way to vary the lick
- "listening_tip": string — what to listen for when playing it back

Keep advice concise, actionable, and jazz-practice oriented.\
"""


class LLMCoach:
    """Coaching provider backed by the Anthropic Messages API."""

    def __init__(self, client: AnthropicClient):
        self._client = client

    def generate(self, analysis: AnalysisResponse) -> CoachingResponse:
        user_prompt = json.dumps(analysis.model_dump(), default=str)
        raw = self._client.complete(_SYSTEM_PROMPT, user_prompt)

        # Strip markdown fences if the model wraps its output
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            logger.error("LLM returned non-JSON: %s", text[:200])
            raise ValueError("LLM returned invalid CoachingResponse") from exc

        try:
            return CoachingResponse(**data)
        except Exception as exc:
            logger.error("LLM JSON did not match CoachingResponse: %s", data)
            raise ValueError("LLM returned invalid CoachingResponse") from exc
