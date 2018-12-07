FROM python:3.7-alpine

RUN apk add --no-cache gcc musl-dev linux-headers

ADD requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

ADD server.py config.py /var/flask/
WORKDIR /var/flask

ENV prometheus_multiproc_dir /tmp
ENV METRICS_PORT 9200

CMD uwsgi --http 0.0.0.0:4000 --module server:app --master --processes 4 --threads 2
