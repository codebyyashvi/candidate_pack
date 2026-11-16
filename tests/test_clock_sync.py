import os
import unittest
from plearun.loader import RecordLoader
from plearun.clock import ClockSynchronizer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECORDS_DIR = os.path.join(ROOT, "records")


class TestClockSync(unittest.TestCase):
    def test_clock_synchronization_bodycam_unaligned(self):
        loader = RecordLoader(RECORDS_DIR)
        sync = ClockSynchronizer(loader.records)

        # Bodycam clock has cues separated by 2.5s for events 5 minutes apart in wall clock
        # Rule 3 requires: If you cannot estimate an offset reliably, do not align that device.
        bodycam_status = sync.get_status("bodycam")
        self.assertFalse(bodycam_status.is_aligned)

        # CAD should be aligned (reference clock)
        cad_status = sync.get_status("CAD")
        self.assertTrue(cad_status.is_aligned)


if __name__ == "__main__":
    unittest.main()
