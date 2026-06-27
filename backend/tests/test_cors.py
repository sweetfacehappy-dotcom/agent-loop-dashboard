from fastapi.testclient import TestClient

from app.main import app


def test_frontend_origin_can_call_api():
    client = TestClient(app)

    response = client.options(
        "/loops",
        headers={
            "Origin": "http://127.0.0.1:5180",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5180"
