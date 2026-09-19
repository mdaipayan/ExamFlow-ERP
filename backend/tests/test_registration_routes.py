from app.main import app


def test_registration_routes_registered():
    paths = {route.path for route in app.routes}
    assert "/api/examinations/{examination_id}/register-students" in paths
    assert "/api/examinations/{examination_id}/registrations" in paths
    assert "/api/examinations/{examination_id}/eligibility" in paths
    assert "/api/examinations/{examination_id}/eligibility/{student_id}/{course_id}" in paths
