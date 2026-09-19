from app.main import app


def test_foundation_routes_registered():
    paths = {route.path for route in app.routes}
    assert "/api/health" in paths
    assert "/api/setup/status" in paths
    assert "/api/setup/initialize" in paths
    assert "/api/auth/login" in paths
    assert "/api/auth/me" in paths
    assert "/api/academic/programmes" in paths
    assert "/api/academic/courses" in paths
    assert "/api/academic/regulations" in paths
