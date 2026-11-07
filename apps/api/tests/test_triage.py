from app.api.triage import review_state


def test_open_case_takes_priority_over_all_other_triage_inputs():
    assert review_state("LOW", 1, 0) == "under_review"
    assert review_state("HIGH", 1, 2) == "under_review"


def test_high_alert_or_assessment_requires_review_without_changing_score():
    assert review_state("HIGH", 0, 0) == "needs_review"
    assert review_state("LOW", 0, 1) == "needs_review"
    assert review_state("MEDIUM", 0, 0) == "monitor"


def test_triage_route_requires_viewer():
    from app.api import auth as auth_api
    from app.main import app

    route = next(item for item in app.routes if getattr(item, "path", None) == "/api/v1/triage/assessments")
    assert route.dependant.dependencies[0].call is auth_api.require_viewer
