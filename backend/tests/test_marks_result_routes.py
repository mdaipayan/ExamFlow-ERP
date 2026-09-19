from app.main import app


def test_marks_and_result_routes_registered():
    paths = {route.path for route in app.routes}
    assert "/api/examinations/{examination_id}/marks" in paths
    assert "/api/examinations/{examination_id}/marks/import-csv" in paths
    assert "/api/examinations/{examination_id}/marks/validate" in paths
    assert "/api/examinations/{examination_id}/results/calculate" in paths
    assert "/api/examinations/{examination_id}/results/latest" in paths
