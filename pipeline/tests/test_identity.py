from shapely.geometry import box

from emberline.identity import FireRecord, match_day


def _rec(fid, first, last):
    return FireRecord(fire_id=fid, first_seen=first, last_seen=last)


def test_growing_fire_keeps_id():
    prev = [(_rec("F0001", "2026-08-19", "2026-08-20"), box(0, 0, 1000, 1000))]
    result = match_day(prev, [box(0, 0, 1500, 1500)], today="2026-08-21",
                       iou_threshold=0.1, max_gap_days=3, next_serial=2)
    assert result.assignments == ["F0001"]
    assert result.records[0].last_seen == "2026-08-21"


def test_new_fire_gets_new_id():
    prev = [(_rec("F0001", "2026-08-19", "2026-08-20"), box(0, 0, 1000, 1000))]
    result = match_day(prev, [box(0, 0, 1100, 1100), box(90_000, 0, 91_000, 1000)],
                       today="2026-08-21", iou_threshold=0.1, max_gap_days=3, next_serial=2)
    assert result.assignments == ["F0001", "F0002"]


def test_merge_keeps_older_id_and_records_event():
    prev = [
        (_rec("F0001", "2026-08-15", "2026-08-20"), box(0, 0, 2000, 2000)),
        (_rec("F0002", "2026-08-18", "2026-08-20"), box(2500, 0, 4500, 2000)),
    ]
    merged = box(0, 0, 4500, 2000)
    result = match_day(prev, [merged], today="2026-08-21",
                       iou_threshold=0.1, max_gap_days=3, next_serial=3)
    assert result.assignments == ["F0001"]
    loser = next(r for r in result.records if r.fire_id == "F0002")
    assert loser.merged_into == "F0001"
    assert result.events == [("merge", "F0002", "F0001", "2026-08-21")]


def test_cloud_gap_fire_still_matches():
    prev = [(_rec("F0001", "2026-08-15", "2026-08-19"), box(0, 0, 1000, 1000))]  # gap: 19 -> 21
    result = match_day(prev, [box(100, 100, 1200, 1200)], today="2026-08-21",
                       iou_threshold=0.1, max_gap_days=3, next_serial=2)
    assert result.assignments == ["F0001"]


def test_stale_fire_not_matched():
    prev = [(_rec("F0001", "2026-08-01", "2026-08-10"), box(0, 0, 1000, 1000))]  # 11-day gap
    result = match_day(prev, [box(0, 0, 1000, 1000)], today="2026-08-21",
                       iou_threshold=0.1, max_gap_days=3, next_serial=2)
    assert result.assignments == ["F0002"]


def test_same_day_rerun_rematches():
    prev = [(_rec("F0001", "2026-08-19", "2026-08-21"), box(0, 0, 1000, 1000))]
    result = match_day(prev, [box(0, 0, 1100, 1100)], today="2026-08-21",
                       iou_threshold=0.1, max_gap_days=3, next_serial=2)
    assert result.assignments == ["F0001"]
