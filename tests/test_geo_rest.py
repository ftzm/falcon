import pytest
import json
from rq import Queue
from fakeredis import FakeStrictRedis

import geo_rest
from geo_rest.tasks import lookup_coordinates, lookup_address


@pytest.fixture
def client(monkeypatch, mocker):
    client = geo_rest.app.test_client()
    yield client


@pytest.fixture
def mq():
    q = Queue(is_async=False, connection=FakeStrictRedis())
    yield q


@pytest.fixture
def mock_side_effects(mq, mocker, monkeypatch):
    """
    Fixture that handles mocking geocoder and rq for happy path purposes.
    """
    mock_g = mocker.Mock()
    mock_osm = mocker.Mock(return_value=mock_g)
    mock_osm = monkeypatch.setattr(geo_rest.tasks.geocoder, "osm", mock_osm)
    monkeypatch.setattr(geo_rest.views, "q", mq)

    class Resources:
        def __init__(self, mock_g, mq):
            self.g = mock_g
            self.q = mq

    yield Resources(mock_g, mq)


# Tests for /address


def test_address_success(client, mock_side_effects):
    resp = client.post("/address/request", json={"coordinates": [50, 50]})
    assert resp.status_code == 202
    assert json.loads(resp.data.decode()) == {}


def test_address_missing_argument(client, mock_side_effects):
    resp = client.post("/address/request", json={"nonsense": 42})
    assert resp.status_code == 422
    error = {"error": {"coordinates": ["Missing data for required field."]}}
    assert json.loads(resp.data.decode()) == error


@pytest.mark.parametrize("test_input", [[-91, 0], [91, 0], [0, -181], [0, 181]])
def test_address_invalid_coordinates(client, mock_side_effects, test_input):
    resp = client.post("/address/request", json={"coordinates": test_input})
    assert resp.status_code == 422
    assert "error" in json.loads(resp.data.decode()).keys()


def test_address_queue_failure(client):
    resp = client.post("/address/request", json={"coordinates": [50, 50]})
    assert resp.status_code == 500
    assert "error" in json.loads(resp.data.decode()).keys()


def test_address_job_success(client, mock_side_effects):
    mock_side_effects.g.address = "Test Address"
    job = mock_side_effects.q.enqueue(lookup_coordinates, [50, 50])
    resp = client.get(f"/address/job/{job.get_id()}")
    output = json.loads(resp.data.decode("utf-8"))

    assert resp.status_code == 200
    assert output == {"result": "Test Address", "status": "finished"}


def test_address_job_match_not_found(client, mock_side_effects):
    mock_side_effects.g.ok = False
    job = mock_side_effects.q.enqueue(lookup_coordinates, [50, 50])
    resp = client.get("/address/job/" + job.get_id())
    output = json.loads(resp.data.decode("utf-8"))
    assert resp.status_code == 200
    assert output["result"] is None


def test_address_job_missing(client, mock_side_effects):
    resp = client.get("/address/job/1")
    assert resp.status_code == 404
    assert "error" in json.loads(resp.data.decode()).keys()


def test_address_job_backend_failure(client):
    resp = client.get("/address/job/1")
    assert resp.status_code == 500
    assert "error" in json.loads(resp.data.decode()).keys()


def test_address_happypath(client, mock_side_effects):
    mock_side_effects.g.address = "Address"

    # Request address
    req_resp = client.post("/address/request", json={"coordinates": [50, 50]})
    location = req_resp.headers.get("Location")
    job_url = location.replace("http://localhost", "")  # TODO: get relative url

    # Get job result
    job_resp = client.get(job_url)
    output = json.loads(job_resp.data.decode("utf-8"))

    assert job_resp.status_code == 200
    assert output == {"result": "Address", "status": "finished"}


# Tests for /coordinates


def test_coordinates_success(client, mock_side_effects):
    mock_side_effects.g.latlng = [50, 50]
    resp = client.post("/coordinates/request", json={"address": "Test Address"})
    assert resp.status_code == 202
    assert json.loads(resp.data.decode()) == {}


def test_coordinates_missing_argument(client, mock_side_effects):
    resp = client.post("/coordinates/request", json={})
    assert resp.status_code == 422
    error = {"error": {"address": ["Missing data for required field."]}}
    assert json.loads(resp.data.decode()) == error


def test_coordinates_queue_failure(client):
    resp = client.post("/coordinates/request", json={"address": "Test Address"})
    assert resp.status_code == 500
    assert "error" in json.loads(resp.data.decode()).keys()


def test_coordinates_job_success(client, mock_side_effects):
    mock_side_effects.g.latlng = [50, 50]
    job = mock_side_effects.q.enqueue(lookup_address, "Test Address")
    resp = client.get(f"/coordinates/job/{job.get_id()}")
    output = json.loads(resp.data.decode("utf-8"))

    assert resp.status_code == 200
    assert output == {"result": "(50, 50)", "status": "finished"}


def test_coordinates_job_match_not_found(client, mock_side_effects):
    mock_side_effects.g.ok = False
    job = mock_side_effects.q.enqueue(lookup_coordinates, [50, 50])
    resp = client.get("/coordinates/job/" + job.get_id())
    output = json.loads(resp.data.decode("utf-8"))
    assert output["result"] is None


def test_coordinates_job_missing(client, mock_side_effects):
    resp = client.get("/coordinates/job/1")
    assert resp.status_code == 404
    assert "error" in json.loads(resp.data.decode()).keys()


def test_coordinates_job_backend_failure(client):
    resp = client.get("/coordinates/job/1")
    assert resp.status_code == 500
    assert "error" in json.loads(resp.data.decode()).keys()


def test_coordinates_happypath(client, mock_side_effects):
    mock_side_effects.g.latlng = [50, 50]

    # Request coordinates
    req_resp = client.post("/coordinates/request", json={"address": "Test Address"})
    location = req_resp.headers.get("Location")
    job_url = location.replace("http://localhost", "")  # TODO: get relative url

    # Get job result
    job_resp = client.get(job_url)
    output = json.loads(job_resp.data.decode("utf-8"))

    assert job_resp.status_code == 200
    assert output == {"result": "(50, 50)", "status": "finished"}
