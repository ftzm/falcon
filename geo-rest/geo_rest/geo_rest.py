from flask import Flask, jsonify, url_for
import geocoder
from typing import List

from redis import Redis
from rq import Queue

from webargs import fields, ValidationError
from webargs.flaskparser import use_kwargs

from flasgger import Swagger

q = Queue(connection=Redis())

app = Flask(__name__)

app.config["SWAGGER"] = {"title": "Geolocation"}
Swagger(app)


def lookup_address(address: str) -> List[float]:
    g = geocoder.osm(address)
    coordinates = str(tuple(g.latlng))
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


@app.route("/address/request", methods=["POST"])
@use_kwargs(coordinates_args)
def address(coordinates):
    """Endpoint for looking up coordinates to produce an address.
    TODO: proper explanation
    ---
    parameters:
      - name: coordinates
        required: true
        in: body
        description: Latitutde and longitude coordinates as a two item list.
        schema:
           $ref: '#/definitions/coordinates'
    responses:
      202:
        description: Empty JSON accompanied by Location header with job url.
        headers:
          location:
            schema: string
            description: url of the successfully created job
        schema:
          type: object
          properties: {}
    definitions:
      coordinates:
        type: object
        properties:
          coordinates:
            type: array
            items:
              type: number
        example: {'coordinates':[55.674146, 12.569553]}
    """
    job = q.enqueue(lookup_coordinates, coordinates)
    return jsonify({}), 202, {"Location": url_for("address_job", job_id=job.get_id())}


address_args = {"address": fields.String(required=True)}


@app.route("/coordinates/request", methods=["POST"])
@use_kwargs(address_args)
def coordinates(address):
    """Endpoint for looking up an address to produce coordinates.
    TODO: proper explanation
    ---
    parameters:
      - name: address
        required: true
        in: body
        description: An address as a single string.
        schema:
           $ref: '#/definitions/address'
    responses:
      202:
        description: Empty JSON accompanied by Location header with job url.
        headers:
          location:
            schema: string
            description: url of the successfully created job
        schema:
          type: object
          properties: {}
    definitions:
      address:
        type: object
        properties:
          address:
            type: string
        example: {'address':'3605 Rue Saint Urbain, Montreal, CA'}
    """
    job = q.enqueue(lookup_address, address)
    return jsonify({}), 202, {"Location": url_for("coordinates_job", job_id=job.get_id())}


@app.route("/address/job/<job_id>")
def address_job(job_id):
    """Endpoint for looking up an address-producing job.
    TODO: proper explanation
    ---
    responses:
      200:
        description: OK
        schema:
          type: object
          properties:
          example: {status: 'finished', 'result':'3605 Rue Saint Urbain, Montreal, CA'}
    """
    job = q.fetch_job(job_id)
    result = job.result
    return jsonify({"result": result, "status": job.get_status()})

@app.route("/coordinates/job/<job_id>")
def coordinates_job(job_id):
    """Endpoint for looking up a coordinates-producing job.
    TODO: proper explanation
    ---
    responses:
      200:
        description: OK
        schema:
          type: object
          properties:
          example: {status: 'finished', 'result':'(45.5128137, -73.5737152)'}
    """
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
