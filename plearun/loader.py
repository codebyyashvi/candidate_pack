"""Robust multi-format record loader and raw row citation extractor."""
import csv
import datetime
import io
import json
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ParsedRecord:
    file: str
    row: int  # 1-based line number in file or cue number in WebVTT
    raw_text: str  # literal line or cue text for substring verification
    source_type: str  # 'camera', 'notes', 'dispatch', 'bodycam', 'generic'
    device: Optional[str] = None
    author: Optional[str] = None
    event_type: Optional[str] = None
    timestamp: Optional[datetime.datetime] = None
    timestamp_epoch: Optional[float] = None
    time_str: Optional[str] = None
    speed_mph: Optional[int] = None
    zone_mph: Optional[int] = None
    text_content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


def read_file_content_and_lines(filepath: str) -> Tuple[str, List[str]]:
    """Reads a file trying UTF-8 with BOM, standard UTF-8, CP1252, and Latin-1."""
    encodings = ["utf-8-sig", "utf-8", "cp1252", "latin-1"]
    for enc in encodings:
        try:
            with open(filepath, "r", encoding=enc) as f:
                content = f.read()
                lines = [line.rstrip("\r\n") for line in content.splitlines()]
                return content, lines
        except (UnicodeDecodeError, UnicodeError):
            continue
    # Fallback to binary with errors replace
    with open(filepath, "rb") as f:
        content = f.read().decode("latin-1", errors="replace")
        lines = [line.rstrip("\r\n") for line in content.splitlines()]
        return content, lines


def parse_timestamp(
    val: Any,
    default_date: str = "2026-03-02",
    default_tz_offset_hours: float = -5.0,
) -> Tuple[Optional[datetime.datetime], Optional[float]]:
    """Normalizes arbitrary timestamp formats into (datetime, unix_epoch_seconds).

    Supports:
    - ISO 8601 strings (e.g. 2026-03-02T21:17:19-05:00)
    - SQL datetime strings (e.g. 2026-03-02 21:10:19)
    - Millisecond epoch integers (e.g. 1772504040000)
    - Second epoch integers (e.g. 1772504040)
    - Time-only strings (e.g. 21:15, 21:16:00)
    """
    if val is None or val == "":
        return None, None

    tz = datetime.timezone(datetime.timedelta(hours=default_tz_offset_hours))

    # Numeric timestamp
    if isinstance(val, (int, float)):
        num = float(val)
        if num > 1e11:  # Milliseconds
            sec = num / 1000.0
        else:
            sec = num
        dt = datetime.datetime.fromtimestamp(sec, tz=tz)
        return dt, dt.timestamp()

    s = str(val).strip()

    # Numeric string
    if s.isdigit():
        num = float(s)
        if num > 1e11:
            sec = num / 1000.0
        else:
            sec = num
        dt = datetime.datetime.fromtimestamp(sec, tz=tz)
        return dt, dt.timestamp()

    # ISO 8601 or standard datetime
    try:
        dt = datetime.datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz)
        return dt, dt.timestamp()
    except (ValueError, TypeError):
        pass

    # Datetime with space 'YYYY-MM-DD HH:MM:SS'
    m_full = re.match(r"^(\d{4}-\d{2}-\d{2})\s+(\d{1,2}:\d{2}(?::\d{2})?)$", s)
    if m_full:
        try:
            iso_str = f"{m_full.group(1)}T{m_full.group(2)}"
            dt = datetime.datetime.fromisoformat(iso_str).replace(tzinfo=tz)
            return dt, dt.timestamp()
        except Exception:
            pass

    # Time only 'HH:MM' or 'HH:MM:SS'
    m_time = re.match(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?$", s)
    if m_time:
        hh = int(m_time.group(1))
        mm = int(m_time.group(2))
        ss = int(m_time.group(3)) if m_time.group(3) else 0
        try:
            base_d = datetime.date.fromisoformat(default_date)
            dt = datetime.datetime(base_d.year, base_d.month, base_d.day, hh, mm, ss, tzinfo=tz)
            return dt, dt.timestamp()
        except Exception:
            pass

    return None, None


class RecordLoader:
    """Manages loading and indexing of all records in RECORDS_DIR."""

    def __init__(self, records_dir: str):
        self.records_dir = records_dir
        self.raw_files: Dict[str, Tuple[str, List[str]]] = {}
        self.records: List[ParsedRecord] = []
        self.load_all()

    def get_raw_row_text(self, filename: str, row: int) -> str:
        """Retrieves the raw line or cue text for exact citation checking (Rule 1)."""
        base_name = os.path.basename(filename)
        path = os.path.join(self.records_dir, base_name)
        if not os.path.exists(path):
            return ""

        if base_name not in self.raw_files:
            self.raw_files[base_name] = read_file_content_and_lines(path)

        content, lines = self.raw_files[base_name]

        if base_name.endswith(".vtt"):
            # WebVTT: row is 1-based cue index
            cues = self._parse_vtt_cues_raw(content)
            if 1 <= row <= len(cues):
                return cues[row - 1]
            return ""
        else:
            # Line-based (CSV, JSON, text): row is 1-based line number
            if 1 <= row <= len(lines):
                return lines[row - 1]
            return ""

    def _parse_vtt_cues_raw(self, content: str) -> List[str]:
        """Returns the full raw text block for each cue in a WebVTT file."""
        blocks = re.split(r"\n\s*\n", content.strip())
        cue_blocks = []
        for b in blocks:
            if "-->" in b:
                cue_blocks.append(b.strip())
        return cue_blocks

    def load_all(self):
        if not os.path.exists(self.records_dir):
            return

        for fname in sorted(os.listdir(self.records_dir)):
            filepath = os.path.join(self.records_dir, fname)
            if not os.path.isfile(filepath):
                continue
            content, lines = read_file_content_and_lines(filepath)
            self.raw_files[fname] = (content, lines)

            if fname.endswith(".vtt"):
                self._load_vtt(fname, content)
            elif fname.endswith(".json"):
                self._load_json(fname, content, lines)
            elif fname.endswith(".csv"):
                self._load_csv(fname, lines)
            else:
                self._load_generic_text(fname, lines)

    def _load_vtt(self, fname: str, content: str):
        blocks = re.split(r"\n\s*\n", content.strip())
        cue_idx = 0
        for block in blocks:
            if "-->" not in block:
                continue
            cue_idx += 1
            lines = [l.strip() for l in block.splitlines() if l.strip()]
            timing_line = None
            payload_lines = []
            for l in lines:
                if "-->" in l:
                    timing_line = l
                elif timing_line is not None:
                    payload_lines.append(l)

            payload_text = " ".join(payload_lines)
            speaker = None
            text = payload_text
            # Extract speaker if format is "[SYNTHETIC] Officer Lee: ..." or "Officer Lee: ..."
            m_speaker = re.search(r"(?:\[SYNTHETIC\]\s*)?([A-Za-z0-9\s]+?):\s*(.*)", payload_text)
            if m_speaker:
                speaker = m_speaker.group(1).strip()
                text = m_speaker.group(2).strip()

            # Parse start and end times
            m_times = re.search(r"(\d{2}:\d{2}:\d{2}\.\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}\.\d{3})", timing_line)
            start_sec = 0.0
            end_sec = 0.0
            if m_times:
                start_sec = self._parse_vtt_time(m_times.group(1))
                end_sec = self._parse_vtt_time(m_times.group(2))

            # Look for mentioned times in transcript e.g. "about 21:16"
            time_str = None
            m_t = re.search(r"\b(\d{1,2}:\d{2})\b", payload_text)
            if m_t:
                time_str = m_t.group(1)

            # Look for speed in transcript e.g. "58 in a 45"
            speed_val = None
            zone_val = None
            m_sp = re.search(r"\b(\d{2})\s+in\s+a\s+(\d{2})\b", payload_text)
            if m_sp:
                speed_val = int(m_sp.group(1))
                zone_val = int(m_sp.group(2))

            self.records.append(
                ParsedRecord(
                    file=fname,
                    row=cue_idx,
                    raw_text=block.strip(),
                    source_type="bodycam",
                    device="bodycam",
                    author=speaker,
                    event_type="transcript",
                    timestamp=None,
                    timestamp_epoch=start_sec,
                    time_str=time_str,
                    speed_mph=speed_val,
                    zone_mph=zone_val,
                    text_content=payload_text,
                    metadata={"start_sec": start_sec, "end_sec": end_sec, "timing": timing_line},
                )
            )

    def _parse_vtt_time(self, s: str) -> float:
        parts = s.split(":")
        if len(parts) == 3:
            h = float(parts[0])
            m = float(parts[1])
            sec = float(parts[2])
            return h * 3600.0 + m * 60.0 + sec
        return 0.0

    def _load_csv(self, fname: str, lines: List[str]):
        # Filter out comments/markers while keeping line indices
        data_rows = []
        header_idx = -1
        headers = []

        for idx, line in enumerate(lines):
            line_str = line.strip()
            if not line_str:
                continue
            if line_str.startswith("#"):
                continue
            if header_idx == -1:
                header_idx = idx
                reader = csv.reader([line])
                headers = [h.strip() for h in next(reader)]
                continue
            data_rows.append((idx + 1, line))

        headers_lower = [h.lower() for h in headers]

        for row_num, line in data_rows:
            reader = csv.reader([line])
            try:
                fields = next(reader)
            except Exception:
                continue
            row_dict = {
                headers_lower[i]: fields[i].strip()
                for i in range(min(len(headers_lower), len(fields)))
            }

            # Check if camera log
            if "speed_mph" in row_dict or "speed" in row_dict:
                raw_ts = row_dict.get("timestamp") or row_dict.get("time")
                dt, epoch = parse_timestamp(raw_ts)
                speed = None
                zone = None
                try:
                    speed = int(row_dict.get("speed_mph") or row_dict.get("speed", 0))
                except Exception:
                    pass
                try:
                    zone = int(row_dict.get("zone_mph") or row_dict.get("zone", 0))
                except Exception:
                    pass
                device = row_dict.get("device", "camera")

                self.records.append(
                    ParsedRecord(
                        file=fname,
                        row=row_num,
                        raw_text=line,
                        source_type="camera",
                        device=device,
                        author=device,
                        event_type="speed_record",
                        timestamp=dt,
                        timestamp_epoch=epoch,
                        time_str=dt.strftime("%H:%M") if dt else None,
                        speed_mph=speed,
                        zone_mph=zone,
                        text_content=line,
                        metadata=row_dict,
                    )
                )

            # Check if officer/dispatch notes
            elif "note" in row_dict or "time" in row_dict or "author" in row_dict:
                raw_time = row_dict.get("time") or row_dict.get("timestamp")
                dt, epoch = parse_timestamp(raw_time)
                author = row_dict.get("author")
                note_text = row_dict.get("note", "")
                note_id = row_dict.get("id")

                self.records.append(
                    ParsedRecord(
                        file=fname,
                        row=row_num,
                        raw_text=line,
                        source_type="notes",
                        device=author,
                        author=author,
                        event_type="note",
                        timestamp=dt,
                        timestamp_epoch=epoch,
                        time_str=raw_time,
                        speed_mph=None,
                        zone_mph=None,
                        text_content=note_text,
                        metadata=row_dict,
                    )
                )

            else:
                self.records.append(
                    ParsedRecord(
                        file=fname,
                        row=row_num,
                        raw_text=line,
                        source_type="generic_csv",
                        text_content=line,
                        metadata=row_dict,
                    )
                )

    def _load_json(self, fname: str, content: str, lines: List[str]):
        try:
            data = json.loads(content)
        except Exception:
            return

        events = []
        if isinstance(data, dict):
            if "export" in data and isinstance(data["export"], dict) and "events" in data["export"]:
                events = data["export"]["events"]
            elif "events" in data:
                events = data["events"]
            else:
                # Top level list of events or dict
                events = [data]
        elif isinstance(data, list):
            events = data

        for ev in events:
            if not isinstance(ev, dict):
                continue
            ev_id = ev.get("id")
            ev_type = ev.get("type", "")
            raw_logged = ev.get("logged") or ev.get("timestamp") or ev.get("time")
            unit = ev.get("unit")
            dt, epoch = parse_timestamp(raw_logged)

            # Find exact line numbers in raw JSON lines where ev_id or ev_type or logged appears
            best_line = 1
            if ev_id:
                for idx, l in enumerate(lines):
                    if f'"{ev_id}"' in l:
                        best_line = idx + 1
                        break
            if best_line == 1 and ev_type:
                for idx, l in enumerate(lines):
                    if f'"{ev_type}"' in l:
                        best_line = idx + 1
                        break

            # Find exact line where logged timestamp appears
            logged_line = best_line
            if raw_logged is not None:
                str_ts = str(raw_logged)
                for idx, l in enumerate(lines):
                    if str_ts in l:
                        logged_line = idx + 1
                        break

            self.records.append(
                ParsedRecord(
                    file=fname,
                    row=logged_line if logged_line != 1 else best_line,
                    raw_text=lines[logged_line - 1] if logged_line <= len(lines) else "",
                    source_type="dispatch",
                    device="CAD",
                    author="Dispatch",
                    event_type=ev_type,
                    timestamp=dt,
                    timestamp_epoch=epoch,
                    time_str=dt.strftime("%H:%M") if dt else None,
                    text_content=f"{ev_type} logged at {raw_logged} unit {unit}",
                    metadata={**ev, "type_line": best_line, "logged_line": logged_line},
                )
            )

    def _load_generic_text(self, fname: str, lines: List[str]):
        for idx, line in enumerate(lines):
            line_str = line.strip()
            if not line_str:
                continue
            self.records.append(
                ParsedRecord(
                    file=fname,
                    row=idx + 1,
                    raw_text=line,
                    source_type="generic_text",
                    text_content=line_str,
                )
            )
