import time
import random

from flask import Flask
from prometheus_flask_exporter import PrometheusMetrics


app = Flask(__name__)
PrometheusMetrics(app)


endpoints = ("one", "two", "three", "four", "five", "error")


@app.route("/one")
def first_route():
    time.sleep(random.random() * 0.2)
    return "ok"


@app.route("/two")
def the_second():
    time.sleep(random.random() * 0.4)
    return "ok"


@app.route("/three")
def test_3rd():
    time.sleep(random.random() * 0.6)
    return "ok"


@app.route("/four")
def fourth_one():
    time.sleep(random.random() * 0.8)
    return "ok"


@app.route("/error")
def oops():
    return ":(", 500


if __name__ == "__main__":
    app.run("0.0.0.0", 5000, threaded=True)
