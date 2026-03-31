from backend.app.services.community_agent.orchestrator import _normalize_reader_selection


def test_normalize_reader_selection_includes_note() -> None:
    payload = {
        "reader_selection": {
            "text": "  Selected snippet  ",
            "anchor_id": "sec-1",
            "mode": "translated_html",
            "note": "  focus on assumptions and limits  ",
        }
    }

    normalized = _normalize_reader_selection(payload)

    assert normalized == {
        "text": "Selected snippet",
        "anchor_id": "sec-1",
        "mode": "translated_html",
        "note": "focus on assumptions and limits",
    }


def test_normalize_reader_selection_truncates_note() -> None:
    payload = {
        "reader_selection": {
            "text": "Selected snippet",
            "note": "a" * 3000,
        }
    }

    normalized = _normalize_reader_selection(payload)

    assert normalized is not None
    assert len(normalized["note"]) == 2000
