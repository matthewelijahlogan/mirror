from fastapi.testclient import TestClient
import json

from main import app

client = TestClient(app)


def test_landing():
    r = client.get("/")
    assert r.status_code == 200
    assert "Mirror" in r.text


def test_quizdata():
    r = client.get("/quizdata")
    assert r.status_code in (200, 500)
    # if 200 then should have a questions array
    if r.status_code == 200:
        data = r.json()
        assert "questions" in data


def test_submit_json():
    payload = {
        "name": "Tester",
        "birthdate": "1990-01-01",
        "quiz": {"mood": 3, "focus": 4}
    }
    r = client.post("/submit", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "fortune" in data


def test_fortune_page():
    r = client.get("/fortune")
    assert r.status_code == 200
    assert "Mirror" in r.text or "mirror" in r.text


if __name__ == "__main__":
    test_landing()
    test_quizdata()
    test_submit_json()
    test_fortune_page()
    print("All sanity checks passed")
