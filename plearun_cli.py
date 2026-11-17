"""Verified Findings CLI tool.
Usage: python3 plearun_cli.py REPORT RECORDS_DIR
"""
import json
import os
import sys

from plearun.loader import RecordLoader, read_file_content_and_lines
from plearun.clock import ClockSynchronizer
from plearun.claim_extractor import extract_claims
from plearun.verifier import ClaimVerifier


def run_pipeline(report_path: str, records_dir: str) -> dict:
    if not os.path.exists(report_path):
        raise FileNotFoundError(f"Report not found: {report_path}")
    if not os.path.exists(records_dir):
        raise FileNotFoundError(f"Records directory not found: {records_dir}")

    # Read report
    report_content, _ = read_file_content_and_lines(report_path)

    # Extract claims from report
    claims = extract_claims(report_content)

    # Load all records
    loader = RecordLoader(records_dir)

    # Run clock synchronization
    clock_sync = ClockSynchronizer(loader.records)

    # Verify claims
    verifier = ClaimVerifier(loader, clock_sync)
    findings = verifier.verify_all(claims)

    return {
        "findings": [f.to_dict() for f in findings]
    }


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} REPORT [RECORDS_DIR]", file=sys.stderr)
        sys.exit(2)

    report_path = sys.argv[1]
    if len(sys.argv) >= 3:
        records_dir = sys.argv[2]
    else:
        # Default to 'records' if omitted
        records_dir = "records"

    try:
        output_dict = run_pipeline(report_path, records_dir)
        print(json.dumps(output_dict, indent=2))
        sys.exit(0)
    except Exception as e:
        print(f"Error running verified findings: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
