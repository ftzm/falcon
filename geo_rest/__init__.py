import os
from flask import Flask
from flasgger import Swagger


class ProdConfig:
    DEBUG = False
    REDIS_URI = "redis"


class DevConfig:
    DEBUG = True
    REDIS_URI = "localhost"


app = Flask(__name__)

flask_env = os.getenv("FLASK_ENV")
if flask_env == "development":
    app.config.from_object(DevConfig)
else:
    app.config.from_object(ProdConfig)

app.config["SWAGGER"] = {"title": "Geolocation"}
Swagger(app)

import geo_rest.views
