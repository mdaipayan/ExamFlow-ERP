from app.main import app


def test_examination_routes_registered():
    paths = {route.path for route in app.routes}
    assert "/api/examinations" in paths
    assert "/api/examinations/{examination_id}/courses" in paths
    assert "/api/examinations/{examination_id}/activate" in paths
