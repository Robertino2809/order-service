import httpx
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def fake_response(text):
    r = MagicMock()
    r.text = text
    return r


def post_order(model_output, text="bilo što"):
    with patch("main.client.models.generate_content", return_value=fake_response(model_output)):
        return client.post("/order", json={"text": text})


def test_valid_order():
    resp = post_order('{"items": [{"id": "margarita", "quantity": 2}], "unavailable": []}')
    assert resp.status_code == 200
    assert resp.json()["items"] == [{"id": "margarita", "quantity": 2}]


def test_item_not_on_menu_goes_to_unavailable():
    resp = post_order('{"items": [{"id": "hamburger", "quantity": 2}], "unavailable": []}')
    assert resp.status_code == 200
    assert resp.json()["items"] == []
    assert resp.json()["unavailable"] == [{"text": "hamburger", "quantity": 2}]


def test_invalid_json_from_model_returns_502():
    resp = post_order("nije json")
    assert resp.status_code == 502


def test_invalid_quantity_returns_502():
    resp = post_order('{"items": [{"id": "margarita", "quantity": 0}], "unavailable": []}')
    assert resp.status_code == 502


def test_empty_text_returns_422():
    resp = client.post("/order", json={"text": ""})
    assert resp.status_code == 422


def test_meatless_suggestions_come_from_menu():
    resp = post_order('{"items": [], "unavailable": [], "wants_meatless_suggestions": true}')
    assert resp.status_code == 200
    assert resp.json()["items"] == []
    assert resp.json()["suggestions"] == ["margarita", "vegetariana", "quattro_formaggi", "mijesana_salata"]


def test_json_not_an_object_returns_502():
    resp = post_order('[1, 2, 3]')
    assert resp.status_code == 502


def test_item_missing_quantity_returns_502():
    resp = post_order('{"items": [{"id": "margarita"}], "unavailable": []}')
    assert resp.status_code == 502


def test_bool_quantity_returns_502():
    resp = post_order('{"items": [{"id": "margarita", "quantity": true}], "unavailable": []}')
    assert resp.status_code == 502


def test_gemini_timeout_returns_502():
    with patch("main.client.models.generate_content", side_effect=httpx.ConnectTimeout("timed out")):
        resp = client.post("/order", json={"text": "bilo što"})
    assert resp.status_code == 502


def test_unavailable_not_a_dict_returns_502():
    resp = post_order('{"items": [], "unavailable": ["hamburger"]}')
    assert resp.status_code == 502


def test_unavailable_missing_text_returns_502():
    resp = post_order('{"items": [], "unavailable": [{"quantity": 2}]}')
    assert resp.status_code == 502


def test_unavailable_bad_quantity_returns_502():
    resp = post_order('{"items": [], "unavailable": [{"text": "hamburger", "quantity": 0}]}')
    assert resp.status_code == 502


def test_too_long_text_returns_422():
    resp = client.post("/order", json={"text": "x" * 501})
    assert resp.status_code == 422