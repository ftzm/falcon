# Running the application

To run the service, simply run `docker-compose up` in the root directory. The
service is accessible on port 8000. To see API documentation and test the
endpoints, visit `http://localhost:8000/apidocs`

# Development

To install required dependencies, run `pipenv update` in the project root. Run
`pipenv shell` to enter the project virtualenv. From there, the application can
be run with `FLASK_APP=geo_rest FLASK_ENV=development flask run`, and tests can
be run with `pytest tests`. For the application to function outside of
docker-compose a redis instance will also need to be running.

# API flow

To request the coordinates associated with an address, the address is first
posted to `/address/request`. The response carries a `Location` header which
contains the url assocated with the created job. Getting the job endpoint
returns a json object containing the job status and output. The same pattern
applies to the `/coordinates` endpoint.

It is possible to see this flow in action by using the "try it out" button on
one of the request endpoints, copying the content of the location header, and
pasting it into the browser.

# Technological Motivation

Given the limited scope of the assignment I opted for the Python web framework
Flask, as I've used it before to implement similar simple services and it
seemed like a good fit.

RQ is not something I've used before, but I since it was recommended by the
assignment spec I gave it a look and found it to be a nice, simpler alternative
to something like Celery.

For API documentation I've used the Flasgger library, as it automatically
provides discoverable API documentation.

To create a production-esque Docker image the application is packaged with the
WSGI server Gunicorn, mainly since it comes recommended both by the Flask
documentation and my colleagues.
