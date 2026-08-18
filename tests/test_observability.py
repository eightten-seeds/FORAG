from backend.app.observability import active_stage, request_timing, time_stage


def test_request_timing_records_only_stage_metadata_and_resets_context() -> None:
    with request_timing() as timing:
        with time_stage("query_analysis"):
            assert active_stage() == "query_analysis"

    assert active_stage() is None
    assert len(timing.events) == 1
    event = timing.events[0]
    assert event.stage == "query_analysis"
    assert event.duration_ms >= 0
    assert event.success is True
    assert event.error_type is None
    assert timing.as_safe_dict()["events"] == [
        {
            "stage": "query_analysis",
            "start_ms": event.start_ms,
            "end_ms": event.end_ms,
            "duration_ms": event.duration_ms,
            "success": True,
            "error_type": None,
        }
    ]
