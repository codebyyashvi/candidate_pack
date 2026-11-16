import os
import unittest
from plearun.loader import RecordLoader, parse_timestamp, read_file_content_and_lines

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECORDS_DIR = os.path.join(ROOT, "records")


class TestRecordLoader(unittest.TestCase):
    def setUp(self):
        self.loader = RecordLoader(RECORDS_DIR)

    def test_camera_log_parsed_with_bom_and_markers(self):
        cam_records = [r for r in self.loader.records if r.file == "camera_log.csv"]
        self.assertGreater(len(cam_records), 30)
        # Line 1 is marker, Line 2 is header, Line 3 is first record
        first_rec = cam_records[0]
        self.assertEqual(first_rec.row, 3)
        self.assertEqual(first_rec.device, "CAM-07")
        self.assertEqual(first_rec.speed_mph, 42)
        self.assertEqual(first_rec.zone_mph, 45)

    def test_notes_cp1252_encoding(self):
        notes_records = [r for r in self.loader.records if r.file == "notes_cp1252.csv"]
        self.assertEqual(len(notes_records), 3)
        self.assertEqual(notes_records[0].row, 2)
        self.assertEqual(notes_records[0].author, "Officer Lee")
        self.assertIn("Vehicle observed", notes_records[0].text_content)

    def test_dispatch_json_three_timestamp_formats(self):
        dispatch_records = [r for r in self.loader.records if r.file == "dispatch.json"]
        self.assertEqual(len(dispatch_records), 3)

        # Check timestamp parsing
        # D-1001: 2026-03-02 21:10:19
        d1 = next(r for r in dispatch_records if r.event_type == "911_call")
        self.assertIsNotNone(d1.timestamp)
        self.assertEqual(d1.timestamp.hour, 21)
        self.assertEqual(d1.timestamp.minute, 10)
        self.assertEqual(d1.timestamp.second, 19)

        # D-1002: 2026-03-02T21:17:19-05:00
        d2 = next(r for r in dispatch_records if r.event_type == "unit_on_scene")
        self.assertIsNotNone(d2.timestamp)
        self.assertEqual(d2.timestamp.hour, 21)
        self.assertEqual(d2.timestamp.minute, 17)
        self.assertEqual(d2.timestamp.second, 19)

        # D-1003: 1772504040000 (epoch ms -> 21:14:00)
        d3 = next(r for r in dispatch_records if r.event_type == "unit_dispatched")
        self.assertIsNotNone(d3.timestamp)
        self.assertEqual(d3.timestamp.hour, 21)
        self.assertEqual(d3.timestamp.minute, 14)
        self.assertEqual(d3.timestamp.second, 0)

    def test_webvtt_cues_and_overlapping(self):
        vtt_records = [r for r in self.loader.records if r.file == "bodycam_transcript.vtt"]
        self.assertEqual(len(vtt_records), 3)
        self.assertEqual(vtt_records[0].row, 1)
        self.assertEqual(vtt_records[1].row, 2)
        self.assertEqual(vtt_records[2].row, 3)

        # Cue 1 ends at 4.0, Cue 2 starts at 3.5 (overlap)
        self.assertEqual(vtt_records[0].metadata["end_sec"], 4.0)
        self.assertEqual(vtt_records[1].metadata["start_sec"], 3.5)
        self.assertIn("58 in a 45", vtt_records[0].text_content)

    def test_get_raw_row_text_exact_substring(self):
        # CSV raw row
        raw_note = self.loader.get_raw_row_text("notes_cp1252.csv", 4)
        self.assertIn("Stopped at lot ~21:16", raw_note)

        # VTT cue raw text
        raw_vtt = self.loader.get_raw_row_text("bodycam_transcript.vtt", 1)
        self.assertIn("58 in a 45", raw_vtt)

        # JSON line raw text
        raw_json = self.loader.get_raw_row_text("dispatch.json", 14)
        self.assertIn("2026-03-02T21:17:19-05:00", raw_json)


if __name__ == "__main__":
    unittest.main()
