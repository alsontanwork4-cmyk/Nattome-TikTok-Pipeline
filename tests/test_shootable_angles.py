import unittest

from batch_analysis.shootable_angles import (
    PRIORITY_SCORE_DIMENSIONS,
    generate_shootable_angles,
    nattome_priority_score,
)


def candidate(**overrides):
    payload = {
        "id": "angle-video",
        "rank": 1,
        "caption": "Acid reflux after meals routine",
        "play_count": 180000,
        "weighted_engagement_rate": 0.12,
        "nattome_relevance_score": 0.84,
    }
    payload.update(overrides)
    return payload


def gemini_evidence(**overrides):
    payload = {
        "status": "completed",
        "visual_observations": [
            {"timestamp_seconds": 0.5, "observation": "Creator points to stomach discomfort"}
        ],
        "visible_text": [{"timestamp_seconds": 0.6, "text": "Bloated after dinner?"}],
        "spoken_content": [
            {"start_seconds": 0, "text": "If reflux hits after meals", "confidence": 0.91}
        ],
        "audio_cues": [{"timestamp_seconds": 0, "cue": "calm voiceover"}],
        "hook_evidence": [{"timestamp_seconds": 0.5, "evidence": "problem question hook"}],
        "claim_evidence": [{"timestamp_seconds": 1.4, "text": "cures reflux overnight"}],
        "shootable_angles": [{"hook": "Gemini creative output must not be copied"}],
    }
    payload.update(overrides)
    return payload


class ShootableAnglesTest(unittest.TestCase):
    def test_no_angles_are_generated_without_evidence_anchors(self):
        angles = generate_shootable_angles(
            candidate(),
            {"prefix": "001_angle-video"},
            {
                "status": "missing_credentials",
                "reason": "Gemini API key is missing",
                "visual_observations": [],
                "visible_text": [],
                "spoken_content": [],
                "audio_cues": [],
                "hook_evidence": [],
                "claim_evidence": [],
            },
            claim_safety_review={"flagged_claims": []},
            evidence_quality={"evidence_quality_score": {"level": "low"}},
        )

        self.assertEqual(angles, [])

    def test_generates_one_evidence_backed_angle_without_filler(self):
        angles = generate_shootable_angles(
            candidate(),
            {"prefix": "001_angle-video"},
            gemini_evidence(
                visible_text=[],
                spoken_content=[],
                audio_cues=[],
                claim_evidence=[],
            ),
            claim_safety_review={"flagged_claims": []},
            evidence_quality={"evidence_quality_score": {"level": "medium"}},
        )

        self.assertEqual(len(angles), 1)
        self.assertEqual(angles[0]["source_evidence"], ["hook_evidence", "visual_observations"])
        self.assertIn("problem question hook", angles[0]["hook"])
        self.assertIn("reflux", angles[0]["product_fit"])

    def test_generates_multiple_angles_from_distinct_evidence_without_using_gemini_angles(self):
        angles = generate_shootable_angles(
            candidate(),
            {"prefix": "001_angle-video"},
            gemini_evidence(),
            claim_safety_review={
                "flagged_claims": [
                    {"category": "cure_claim"},
                    {"category": "one_night_fix"},
                ]
            },
            evidence_quality={"evidence_quality_score": {"level": "high"}},
        )

        self.assertEqual(len(angles), 3)
        self.assertTrue(all("Gemini creative output" not in angle["hook"] for angle in angles))
        self.assertTrue(
            all(
                {"hook", "avatar", "format", "product_fit", "recommendation", "claim_guardrails", "priority_score"}
                <= set(angle)
                for angle in angles
            )
        )
        self.assertTrue(all(angle["priority_score"]["max_points"] == 30 for angle in angles))
        self.assertIn("cure_claim", angles[0]["claim_guardrails"])

    def test_priority_score_keeps_six_dimensions_and_thirty_point_maximum(self):
        score = nattome_priority_score(
            candidate(play_count=300000, weighted_engagement_rate=0.2),
            gemini_evidence(),
            claim_safety_review={"flagged_claims": [{"category": "cure_claim"}]},
            evidence_quality={"evidence_quality_score": {"level": "high"}},
            audio_format="voiceover",
        )

        self.assertEqual(PRIORITY_SCORE_DIMENSIONS, list(score["dimensions"]))
        self.assertEqual(score["max_points"], 30)
        self.assertEqual(score["total"], sum(score["dimensions"].values()))
        self.assertLessEqual(score["total"], 30)
        self.assertEqual(score["dimensions"]["viral_strength"], 5)
        self.assertEqual(score["dimensions"]["brand_safety"], 3)


if __name__ == "__main__":
    unittest.main()
