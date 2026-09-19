from app.main import app


def test_student_routes_registered():
    paths = {route.path for route in app.routes}
    assert "/api/students" in paths
    assert "/api/students/import-csv" in paths
    assert "/api/students/{student_id}" in paths
    assert "/api/students/{student_id}/enrolments" in paths
