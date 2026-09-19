from app.main import app


def test_regulation_approval_route_registered():
    paths = {route.path for route in app.routes}
    assert "/api/academic/regulations/{regulation_id}/versions/{version_id}/approve" in paths


def test_examination_setup_routes_registered():
    paths = {route.path for route in app.routes}
    assert "/api/examinations" in paths
    assert "/api/examinations/{examination_id}/courses" in paths
    assert "/api/examinations/{examination_id}/activate" in paths
