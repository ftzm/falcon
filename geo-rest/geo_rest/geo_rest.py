from flask import Flask, request, jsonify, url_for
import geocoder
from typing import List

from redis import Redis
from rq import Queue

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


@app.route('/coordinates', methods=['POST', 'GET'])
def coordinates():
    data = request.get_json()
    address = data["coordinates"]
    job = q.enqueue(lookup_coordinates, address)
    return jsonify({}), 202, {'Location': url_for('job', job_id=job.get_id())}


@app.route('/address', methods=['POST', 'GET'])
def address():
    data = request.get_json()
    address = data["address"]
    job = q.enqueue(lookup_address, address)
    return jsonify({}), 202, {'Location': url_for('job', job_id=job.get_id())}


@app.route('/job/<job_id>')
def job(job_id):
    job = q.fetch_job(job_id)
    result = job.result
    return jsonify({"result": result, "status": job.get_status()})
