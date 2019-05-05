from flask import Flask, request, jsonify, url_for
import geocoder
from typing import List

from redis import Redis
from rq import Queue

from webargs import fields, ValidationError
from webargs.flaskparser import use_kwargs
q = Queue(connection=Redis())

app = Flask(__name__)

def lookup_address(address: str) -> List[float]:
    g = geocoder.osm(address)
    coordinates = g.latlng
    return coordinates


def lookup_coordinates(coordinates: List[float]) -> str:
    g = geocoder.osm(coordinates, method="reverse")
    address = g.address
    return address


def assert_coordinates_length(coordinates):
    if not len(coordinates) == 2:
        raise ValidationError("coordinates list must contain exactly two floats.")


coordinates_args = {
    "coordinates": fields.List(
        fields.Float, required=True, validate=assert_coordinates_length
    )
}


@app.route("/coordinates", methods=["POST"])
@use_kwargs(coordinates_args)
def coordinates(coordinates):
    job = q.enqueue(lookup_coordinates, coordinates)
    return jsonify({}), 202, {"Location": url_for("job", job_id=job.get_id())}


address_args = {"address": fields.String(required=True)}


@app.route("/address", methods=["POST"])
@use_kwargs(address_args)
def address(address):
    job = q.enqueue(lookup_address, address)
    return jsonify({}), 202, {"Location": url_for("job", job_id=job.get_id())}


@app.route("/job/<job_id>")
def job(job_id):
    job = q.fetch_job(job_id)
    result = job.result
    return jsonify({"result": result, "status": job.get_status()})


# Return validation errors as JSON (from webargs documentation)
@app.errorhandler(422)
def handle_error(err):
    headers = err.data.get("headers", None)
    messages = err.data.get("messages", ["Invalid request."])
    if headers:
        return jsonify({"errors": messages}), err.code, headers
    else:
        return jsonify({"errors": messages}), err.code
