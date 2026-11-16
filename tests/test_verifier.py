import os
import unittest
from plearun.loader import RecordLoader
from plearun.clock import ClockSynchronizer
from plearun.claim_extractor import extract_claims, ExtractedClaim
from plearun.verifier import ClaimVerifier
from plearun.models import FINDING_MATCH, FINDING_NOT_SETTLED, FINDING_NOT_CHECKABLE

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT_PATH = os.path.join(ROOT, "reports/report_fictional_02.txt")
RECORDS_DIR = os.path.join(ROOT, "records")


class TestVerifier(unittest.TestCase):
    def setUp(self):
        self.loader = RecordLoader(RECORDS_DIR)
        self.clock_sync = ClockSynchronizer(self.loader.records)
        self.verifier = ClaimVerifier(self.loader, self.clock_sync)

    def test_sample_findings(self):
        with open(REPORT_PATH, "r", encoding="utf-8") as f:
            content = f.read()

        claims = extract_claims(content)
        findings = self.verifier.verify_all(claims)
        self.assertEqual(len(findings), 5)

        finding_map = {f.claim: f for f in findings}

        # Claim 1: Speed observation
        c1 = "Officer Lee first observed the blue sedan at about 21:14 near mile marker 4, travelling 58 mph in a posted 45 zone."
        self.assertEqual(finding_map[c1].finding, FINDING_MATCH)
        self.assertIsNotNone(finding_map[c1].cite)
        self.assertIsNotNone(finding_map[c1].quote)
        # Verify Rule 1 on Claim 1
        raw_row = self.loader.get_raw_row_text(finding_map[c1].cite.file, finding_map[c1].cite.row)
        self.assertIn(finding_map[c1].quote, raw_row)

        # Claim 2: Stop around 21:16
        c2 = "The driver pulled into the Harbor Gas lot and stopped around 21:16."
        self.assertEqual(finding_map[c2].finding, FINDING_MATCH)
        self.assertIsNotNone(finding_map[c2].cite)
        self.assertIsNotNone(finding_map[c2].quote)
        raw_row = self.loader.get_raw_row_text(finding_map[c2].cite.file, finding_map[c2].cite.row)
        self.assertIn(finding_map[c2].quote, raw_row)

        # Claim 3: 911 call logged at 21:11 (evidence ambiguous/conflict between CAD 21:10:19 and note 21:11)
        c3 = "A 911 call reporting the incident was logged at 21:11."
        self.assertEqual(finding_map[c3].finding, FINDING_NOT_SETTLED)
        self.assertIsNone(finding_map[c3].cite)
        self.assertIsNone(finding_map[c3].quote)

        # Claim 4: Unit on scene roughly 2 minutes after stop
        c4 = "Dispatch records show a unit on scene roughly 2 minutes after the stop."
        self.assertEqual(finding_map[c4].finding, FINDING_MATCH)
        self.assertIsNotNone(finding_map[c4].cite)
        self.assertIsNotNone(finding_map[c4].quote)
        raw_row = self.loader.get_raw_row_text(finding_map[c4].cite.file, finding_map[c4].cite.row)
        self.assertIn(finding_map[c4].quote, raw_row)

        # Claim 5: Lane assertion (no records)
        c5 = "Officer Lee states the vehicle was the only car in the lane."
        self.assertEqual(finding_map[c5].finding, FINDING_NOT_CHECKABLE)
        self.assertIsNone(finding_map[c5].cite)
        self.assertIsNone(finding_map[c5].quote)

    def test_rule_1_downgrade_on_invalid_quote(self):
        # Artificially inject an invalid quote that is not a substring
        claim = ExtractedClaim(
            claim_text="The driver pulled into the Harbor Gas lot and stopped around 21:16.",
            original_line_num=1,
        )
        finding = self.verifier.verify_claim(claim)
        finding.quote = "NONEXISTENT_QUOTE_THAT_CANNOT_BE_FOUND"

        # Verify through verify_all which enforces Rule 1
        class DummyVerifier(ClaimVerifier):
            def verify_claim(self, c):
                return finding

        dv = DummyVerifier(self.loader, self.clock_sync)
        results = dv.verify_all([claim])
        self.assertEqual(results[0].finding, FINDING_NOT_SETTLED)
        self.assertIsNone(results[0].cite)
        self.assertIsNone(results[0].quote)


if __name__ == "__main__":
    unittest.main()
