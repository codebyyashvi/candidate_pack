import os
import unittest
from plearun.claim_extractor import extract_claims, is_factual_claim

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT_PATH = os.path.join(ROOT, "reports/report_fictional_02.txt")


class TestClaimExtractor(unittest.TestCase):
    def test_extract_claims_from_sample(self):
        with open(REPORT_PATH, "r", encoding="utf-8") as f:
            content = f.read()

        claims = extract_claims(content)
        self.assertEqual(len(claims), 5)

        claim_texts = [c.claim_text for c in claims]

        # Verify each expected claim
        self.assertIn(
            "Officer Lee first observed the blue sedan at about 21:14 near mile marker 4, travelling 58 mph in a posted 45 zone.",
            claim_texts,
        )
        self.assertIn(
            "The driver pulled into the Harbor Gas lot and stopped around 21:16.",
            claim_texts,
        )
        self.assertIn(
            "A 911 call reporting the incident was logged at 21:11.",
            claim_texts,
        )
        self.assertIn(
            "Dispatch records show a unit on scene roughly 2 minutes after the stop.",
            claim_texts,
        )
        self.assertIn(
            "Officer Lee states the vehicle was the only car in the lane.",
            claim_texts,
        )

    def test_non_claims_filtered(self):
        # Disclaimers and non-predicate headers should not be claims
        self.assertFalse(is_factual_claim("SYNTHETIC - FICTIONAL CASE."))
        self.assertFalse(is_factual_claim("Case #2026-001"))
        self.assertTrue(is_factual_claim("The suspect vehicle was observed at 14:00."))


if __name__ == "__main__":
    unittest.main()
