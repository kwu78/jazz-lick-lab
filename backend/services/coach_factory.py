from config import settings
from services.coach_provider import CoachProvider
from services.coaching import RuleBasedCoach


def get_coach_provider() -> CoachProvider:
    provider = settings.coach_provider

    if provider == "rules":
        return RuleBasedCoach()

    if provider == "llm":
        raise NotImplementedError(
            "LLM coach provider is not yet implemented. "
            "Set COACH_PROVIDER=rules or leave unset."
        )

    raise ValueError(f"Unknown COACH_PROVIDER: {provider!r}")
