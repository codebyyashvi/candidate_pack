import json
import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT_PATH = os.path.join(ROOT, "reports/report_fictional_02.txt")
RECORDS_DIR = os.path.join(ROOT, "records")
CLI_PATH = os.path.join(ROOT, "plearun_cli.py")


class TestCLI(unittest.TestCase):
    def test_cli_execution_and_schema(self):
        cmd = [sys.executable, CLI_PATH, REPORT_PATH, RECORDS_DIR]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(res.returncode, 0, f"CLI failed with error: {res.stderr}")

        # Parse JSON output
        data = json.loads(res.stdout)
        self.assertIn("findings", data)
        self.assertIsInstance(data["findings"], list)
        self.assertEqual(len(data["findings"]), 5)

        for item in data["findings"]:
            self.assertIn("claim", item)
            self.assertIn("finding", item)
            self.assertIn(item["finding"], ["match", "conflict", "not_settled", "not_checkable"])
            if item["finding"] in ["match", "conflict"]:
                self.assertIn("cite", item)
                self.assertIn("file", item["cite"])
                self.assertIn("row", item["cite"])
                self.assertIsInstance(item["cite"]["row"], int)
                self.assertIn("quote", item)
                self.assertIsInstance(item["quote"], str)
            else:
                self.assertNotIn("cite", item)
                self.assertNotIn("quote", item)


if __name__ == "__main__":
    unittest.main()
