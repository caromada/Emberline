"""Fire identity across ingest runs.

DBSCAN labels are meaningless run to run. We match today's perimeters to known
fires by polygon IoU with greedy 1:1 assignment, then resolve merges: an
unmatched-but-overlapping older fire folds into the surviving ID (the older
first_seen wins, per incident-tracking convention). Fires unseen longer than
max_gap_days retire and never match again.
"""
from dataclasses import dataclass, field
from datetime import date


@dataclass
class FireRecord:
    fire_id: str
    first_seen: str
    last_seen: str
    merged_into: str | None = None


@dataclass
class MatchResult:
    assignments: list[str]                 # fire_id per today-polygon, same order
    records: list[FireRecord]              # updated registry (prev + newborns)
    events: list[tuple] = field(default_factory=list)
    next_serial: int = 0


def _iou(a, b) -> float:
    inter = a.intersection(b).area
    return inter / a.union(b).area if inter > 0 else 0.0


def _days_between(a: str, b: str) -> int:
    return (date.fromisoformat(b) - date.fromisoformat(a)).days


def match_day(prev, today_polys, today: str, iou_threshold: float,
              max_gap_days: int, next_serial: int) -> MatchResult:
    records = [rec for rec, _ in prev]
    active = [
        (i, rec, geom) for i, (rec, geom) in enumerate(prev)
        if rec.merged_into is None and 0 <= _days_between(rec.last_seen, today) <= max_gap_days
    ]

    pairs = sorted(
        ((_iou(geom, poly), i, j)
         for i, _, geom in active for j, poly in enumerate(today_polys)),
        reverse=True,
    )
    prev_taken: dict[int, int] = {}   # prev index -> today index
    today_taken: dict[int, int] = {}  # today index -> prev index
    for iou, i, j in pairs:
        if iou < iou_threshold:
            break
        if i in prev_taken or j in today_taken:
            continue
        prev_taken[i] = j
        today_taken[j] = i

    assignments: list[str | None] = [None] * len(today_polys)
    events: list[tuple] = []
    for i, j in prev_taken.items():
        rec = records[i]
        rec.last_seen = today
        assignments[j] = rec.fire_id

    # merges: an active fire that lost the 1:1 assignment but still overlaps an
    # assigned polygon folds into it; the older ID survives.
    for i, rec, geom in active:
        if i in prev_taken:
            continue
        best = max(
            ((_iou(geom, poly), j) for j, poly in enumerate(today_polys) if j in today_taken),
            default=(0.0, -1),
        )
        if best[0] >= iou_threshold:
            j = best[1]
            winner = records[today_taken[j]]
            if rec.first_seen < winner.first_seen:
                # the older record takes over the polygon; the newer one folds in
                rec, winner = winner, rec
                assignments[j] = winner.fire_id
                winner.last_seen = today
            rec.merged_into = winner.fire_id
            events.append(("merge", rec.fire_id, winner.fire_id, today))

    for j, fid in enumerate(assignments):
        if fid is None:
            new = FireRecord(f"F{next_serial:04d}", first_seen=today, last_seen=today)
            next_serial += 1
            records.append(new)
            assignments[j] = new.fire_id

    return MatchResult(assignments=assignments, records=records,
                       events=events, next_serial=next_serial)
