import logging

from config import settings
from schemas.analysis import AnalysisResponse
from schemas.coaching import CoachingResponse
from services.coach_provider import CoachProvider
from services.coaching import RuleBasedCoach

logger = logging.getLogger(__name__)


class _LLMCoachWithFallback:
    """Wraps LLMCoach with automatic fallback to RuleBasedCoach."""

    def __init__(self, llm_coach, fallback: RuleBasedCoach):
        self._llm = llm_coach
        self._fallback = fallback

    def generate(self, analysis: AnalysisResponse) -> CoachingResponse:
        try:
            result = self._llm.generate(analysis)
            result.flags.append("llm_used")
            return result
        except Exception as exc:
            logger.warning("LLM coach failed, falling back to rules: %s", exc)
            result = self._fallback.generate(analysis)
            result.flags.append("llm_fallback")
            return result


def get_coach_provider() -> CoachProvider:
    provider = settings.coach_provider

    if provider == "rules":
        return RuleBasedCoach()

    if provider == "llm":
        try:
            from services.llm_client import AnthropicClient
            from services.llm_coach import LLMCoach

            client = AnthropicClient.from_env()
            llm = LLMCoach(client)
            return _LLMCoachWithFallback(llm, RuleBasedCoach())
        except Exception as exc:
            logger.warning("Failed to init LLM coach, falling back to rules: %s", exc)
            return RuleBasedCoach()

    raise ValueError(f"Unknown COACH_PROVIDER: {provider!r}")
