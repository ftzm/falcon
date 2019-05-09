from flask import jsonify, url_for
import logging
from geo_rest import app
from webargs import fields, ValidationError
from webargs.flaskparser import use_kwargs
from rq import Queue
from redis import Redis
from geo_rest.tasks import lookup_address, lookup_coordinates


logger = logging.getLogger(__name__)
q = Queue(connection=Redis(app.config["REDIS_URI"]))


def validate_coordinates(coordinates):
    """Ensure that coordinates number two and are within the legal range."""
    if not len(coordinates) == 2:
        raise ValidationError("Coordinates list must contain exactly two floats.")
    lat = coordinates[0]
    if not (-90 <= lat <= 90):
        raise ValidationError("Latitude must be between -90 and 90")
    lng = coordinates[1]
    if not (-180 <= lng <= 180):
        raise ValidationError("Longitude must be between -180 and 180")


coordinates_args = {
    "coordinates": fields.List(
        fields.Float, required=True, validate=validate_coordinates
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
          type: object
          properties:
            coordinates:
              type: array
              items:
                type: number
          example: {'coordinates':[55.674146, 12.569553]}
    responses:
      202:
        description: Success. `Location` header contains created job url.
        headers:
          location:
            schema: string
            description: url of the successfully created job
        schema:
          type: object
          properties: {}
      422:
        description: Reports an error with the provided JSON argument.
        schema:
          type: object
          properties:
            error: {}
          example: {"error": {"coordinates": ["Coordinates list must contain exactly two floats."]}}
      500:
        description: Reports an error with the server.
        schema:
          type: object
          properties:
            error: {}
          example: {"error": "Some error message."}
    """
    try:
        job = q.enqueue(lookup_coordinates, coordinates)
    except Exception as e:
        logger.error("Error enqueueing job:\n" + str(e))
        return (
            jsonify(
                {
                    "error": "The server has encountered an error and cannot complete the request."
                }
            ),
            500,
        )
    return (
        jsonify({}),
        202,
        {"Location": url_for("coordinates_job", job_id=job.get_id())},
    )


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
          type: object
          properties:
            address:
              type: string
          example: {'address':'3605 Rue Saint Urbain, Montreal, CA'}
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
      422:
        description: Reports an error with the provided JSON argument.
        schema:
          type: object
          properties:
            error: {}
          example: {"error": {"address": "Missing required field."}}
      500:
        description: Reports an error with the server.
        schema:
          type: object
          properties:
            error: {}
          example: {"error": "Some error message."}
    """
    try:
        job = q.enqueue(lookup_address, address)
    except Exception as e:
        logger.error("Error enqueueing job:\n" + str(e))
        return (
            jsonify(
                {
                    "error": "The server has encountered an error and cannot complete the request."
                }
            ),
            500,
        )
    return (
        jsonify({}),
        202,
        {"Location": url_for("coordinates_job", job_id=job.get_id())},
    )


@app.route("/address/job/<job_id>")
def address_job(job_id):
    """Endpoint for looking up an address-producing job.
    TODO: proper explanation
    ---
    responses:
      200:
        description: Show job status. `result` is null unless status is finished.
        schema:
          type: object
          properties:
            result:
              type: string
              nullable: true
            status:
              type: string
              enum: [queued, finished, failed, started, deferred]
        examples:
          queued:
            {status: 'queued', 'result': null}
          finished:
            {status: 'finished', 'result':'3605 Rue Saint Urbain, Montreal, CA'}
      404:
        description: Error returned when the job cannot be found.
        schema:
          type: object
          properties:
            error:
              type: string
          example: {"error": "Job <id> does not exist."}
      500:
        description: Error returned when an error occurs during processing.
        schema:
          type: object
          properties:
            error:
              type: string
          example: {"error": "Error retrieving job."}
    """
    try:
        job = q.fetch_job(job_id)
        if job:
            return jsonify({"result": job.result, "status": job.get_status()})
        else:
            return jsonify({"error": f"job '{job_id}' does not exist."}), 404
    except Exception as e:
        logger.error("Error retrieving job:\n" + str(e))
        msg = (
            "Error retrieving job: The server has encountered an error and "
            "cannot complete the request."
        )
        return (jsonify({"error": msg}), 500)


@app.route("/coordinates/job/<job_id>")
def coordinates_job(job_id):
    """Endpoint for looking up a coordinates-producing job.
    TODO: proper explanation
    ---
    responses:
      200:
        description: Show job status. `result` is null unless status is finished.
        schema:
          type: object
          properties:
          example: {status: 'finished', 'result':'(45.5128137, -73.5737152)'}
      404:
        description: Error returned when the job cannot be found.
        schema:
          type: object
          properties:
            error:
              type: string
          example: {"error": "Job <id> does not exist."}
      500:
        description: Error returned when an error occurs during processing.
        schema:
          type: object
          properties:
            error:
              type: string
          example: {"error": "Error retrieving job."}
    """
    try:
        job = q.fetch_job(job_id)
        if job:
            return jsonify({"result": job.result, "status": job.get_status()})
        else:
            return jsonify({"error": f"job '{job_id}' does not exist."}), 404
    except Exception as e:
        logger.error("Error retrieving job:\n" + str(e))
        msg = (
            "Error retrieving job: The server has encountered an error and "
            "cannot complete the request."
        )
        return (jsonify({"error": msg}), 500)


@app.errorhandler(422)
def handle_error(err):
    """
    Return detailed error messages for invalid request parameters
    (from the webargs documentation)
    """
    headers = err.data.get("headers", None)
    messages = err.data.get("messages", ["Invalid request."])
    if headers:
        return jsonify({"error": messages}), err.code, headers
    else:
        return jsonify({"error": messages}), err.code
