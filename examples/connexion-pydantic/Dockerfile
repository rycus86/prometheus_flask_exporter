FROM python:3.11-alpine

RUN apk add --no-cache curl && pip install flask==2.2.4 connexion pydantic prometheus_client

ADD . /tmp/latest
RUN pip install -e /tmp/latest --upgrade

ADD examples/connexion-pydantic /var/flask
WORKDIR /var/flask

CMD python /var/flask/main.py
