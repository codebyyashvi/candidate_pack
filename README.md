# Verified Findings: Take-Home Assignment Implementation

## Overview & Architecture
This command-line tool verifies factual claims in incident reports against heterogeneous, unsynchronized machine records. It runs completely offline without network access or LLM dependencies (`make test`).

### How It Works
1. **Multi-Format Ingestion (`plearun/loader.py`)**: Reads varied file formats preserving exact raw line bytes for citation auditing:
   - CSV with UTF-8 BOM (`\ufeff`) and `#PLEARUN` marker/comment lines (`camera_log.csv`).
   - Windows-1252 / CP1252 encoded CSV with quoted fields (`notes_cp1252.csv`).
   - Nested CAD JSON with 3 timestamp formats: ISO-8601 with timezone, epoch ms, and SQL datetime strings (`dispatch.json`).
   - WebVTT transcripts with overlapping cues and speaker tags (`bodycam_transcript.vtt`).
2. **Clock Synchronization Engine (`plearun/clock.py`, Rule 3)**: Discovers shared anchor events across sources to evaluate clock offsets. If candidate offsets contradict each other (e.g. bodycam cues spanning 2.5 seconds for events 5 minutes apart in wall-clock time), the device is flagged as **unaligned** and its clock is not used for temporal conflict/match deductions.
3. **Claim Extraction (`plearun/claim_extractor.py`)**: Uses grammatical sentence boundary detection to segment the report into factual claims containing verbal predicates, numerical speeds, times, and counts, filtering synthetic disclaimer headers (`SYNTHETIC - FICTIONAL CASE.`) and non-assertive titles.
4. **Verification Engine (`plearun/verifier.py`)**:
   - Matches claims against candidate records based on entities, action types, speeds, and aligned timestamps.
   - **Rule 1 Verification**: Before outputting any `match` or `conflict`, the engine looks up the raw row/cue text and strictly verifies `quote in raw_row_text`. If the quote is not an exact substring, the finding is automatically downgraded to `not_settled` (with `cite` and `quote` omitted).
   - **Rule 2 Conservative Policy**: When records disagree (e.g. CAD log 21:10:19 vs note 21:11), the finding is reported as `not_settled` to avoid false conflicts.
   - **Rule 4 Data Isolation**: Record text is parsed strictly as data, making the system 100% immune to adversarial prompt injection.

---

## Three Hardest Decisions
1. **Refusing to align the bodycam clock**: Bodycam Cue 2 ("weaving", 911 call ~21:10:19) and Cue 3 ("pulling in at the lot", ~21:16) occur 2.5 seconds apart in cue time. Anchoring to Cue 2 yields offset $\approx 21:10$, while Cue 3 yields $\approx 21:15$. Per Rule 3, because the offset cannot be estimated reliably, bodycam is kept unaligned. It verifies spoken statements ("58 in a 45"), but cannot confirm wall-clock time.
2. **Marking 911 call logging as `not_settled` instead of `conflict`**: CAD export shows call receipt at 21:10:19, while human notes record dispatch note at 21:11. Because human notes round to whole minutes while CAD logs seconds, a 41-second discrepancy is not decisive evidence of falsity. Under Rule 2 ("A confident wrong conflict is much worse than 'not_settled'"), marking `not_settled` is the only defensible choice.
3. **Defining citation `row` as 1-based file line number for CSV/JSON and cue index for WebVTT**: In `camera_log.csv`, Line 1 is a marker comment (`#PLEARUN...`). Using data-row index vs file-line index would cause `quote in lines[row-1]` to fail under Rule 1. Standardizing on raw file line numbers guarantees exact substring verification.

---

## What It Gets Wrong
- **Geographic & Spatial Reasoning**: Does not model road networks; cannot verify whether CAM-07 is at mile marker 4 or if travel times between cameras match speed limits.
- **Complex Semantic Paraphrasing**: Heavy linguistic paraphrasing without explicit numeric/temporal anchors defaults safely to `not_settled` or `not_checkable`.

---

## What Would Break First on Real Records
1. **High-Density Unlabeled Traffic**: Without license-plate readers (ALPR) or vehicle tracking, attributing camera speed pulses to a specific vehicle among dozens on a multi-lane highway is intractable.
2. **Non-Linear Audio & Rebroadcast Latency**: Real bodycam audio frequently contains buffered radio transmissions, repeater delays, and discontinuous sleep/wake segments that warp timeline linearity.
3. **Dirty Timezones & Clock Drift**: Uncalibrated quartz clocks in field cameras and CAD servers drifting by minutes across daylight saving time transitions without explicit UTC offset tags.

---

## Tools Used
- Python 3 standard library (`csv`, `json`, `re`, `datetime`, `unittest`, `dataclasses`, `os`, `sys`).
- AI assistant (Antigravity with Gemini 3.8 Flash) for initial architecture scaffolding, test suite design, and documentation. All code is explained, verified, and audited.
