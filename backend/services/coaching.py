from schemas.analysis import AnalysisResponse
from schemas.coaching import CoachingResponse


class RuleBasedCoach:
    """Deterministic coaching based on analysis metrics."""

    def generate(self, analysis: AnalysisResponse) -> CoachingResponse:
        metrics = analysis.metrics
        ii_v_i = analysis.ii_v_i

        # Build summary
        summary_parts = [
            f"This lick contains {metrics.total_notes} notes",
            f"with {metrics.chord_tone_pct:.0%} chord-tone coverage",
            f"and {metrics.tension_pct:.0%} tension usage.",
        ]
        if ii_v_i:
            keys = [e.key_guess for e in ii_v_i if e.key_guess]
            summary_parts.append(
                f"Detected {len(ii_v_i)} ii-V-I progression(s)"
                + (f" in key(s): {', '.join(keys)}." if keys else ".")
            )
        summary = " ".join(summary_parts)

        # Why it works
        if metrics.chord_tone_pct >= 0.6:
            why = (
                "The lick is strongly grounded in chord tones, giving it a clear "
                "harmonic foundation that outlines the changes."
            )
        elif metrics.tension_pct >= 0.3:
            why = (
                "The lick makes deliberate use of tensions to create color and "
                "movement against the harmony."
            )
        else:
            why = (
                "The lick uses a mix of chord tones and passing tones, creating "
                "melodic interest through voice leading."
            )

        # Practice steps
        steps = [
            "Learn the lick slowly in the original key, paying attention to "
            "which notes are chord tones vs tensions.",
            "Practice with a metronome at half tempo, then gradually increase.",
            "Transpose to at least 3 other keys using the /transpose endpoint.",
        ]
        if ii_v_i:
            steps.append(
                "Isolate the ii-V-I section and practice resolving to the "
                "target chord tone on beat 1."
            )

        # Variation idea
        if metrics.chord_tone_pct >= 0.7:
            variation = (
                "Try adding approach tones (chromatic or diatonic) before "
                "each chord tone to add movement."
            )
        else:
            variation = (
                "Try simplifying the line to just chord tones on strong beats, "
                "then re-add tensions one at a time."
            )

        # Listening tip
        if ii_v_i:
            listening = (
                "Listen to how the line resolves across the ii-V-I. Notice "
                "which note lands on the I chord and what role it plays "
                "(root, 3rd, 7th)."
            )
        else:
            listening = (
                "Listen to how the melody moves against the chord changes. "
                "Notice where tension builds and where it resolves."
            )

        return CoachingResponse(
            summary=summary,
            why_it_works=why,
            practice_steps=steps,
            variation_idea=variation,
            listening_tip=listening,
        )
