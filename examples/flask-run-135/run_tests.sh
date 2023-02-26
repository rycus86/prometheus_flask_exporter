#!/bin/bash

cd "$(dirname "$0")"

_fail() {
    docker logs flask-run-135
    docker rm -f flask-run-135 > /dev/null 2>&1
    exit 1
}

docker build -f Dockerfile -t flask-run-135 ../../. > /dev/null || _fail
docker run -d --name flask-run-135 -p 4000:4000 flask-run-135 > /dev/null || _fail

echo 'Waiting for the server to start...'

for _ in $(seq 1 10); do
    if curl -fs http://localhost:4000/metrics > /dev/null; then
        break
    else
        sleep 0.2
    fi
done

echo 'Starting the tests...'

for _ in $(seq 1 10); do
    curl -s http://localhost:4000/info > /dev/null
    if [ "$?" != "0" ]; then
        echo 'Failed to request the test endpoint'
        _fail
    fi
done

curl -s http://localhost:4000/metrics \
  | grep 'flask_http_request_duration_seconds_count{method="GET",path="/info",status="200"} 10.0' \
  > /dev/null

curl -s http://localhost:4000/metrics \
  | grep 'flask_http_request_total{method="GET",status="200"} 10.0' \
  > /dev/null

if [ "$?" != "0" ]; then
    echo 'The expected metrics are not found'
    _fail
fi

docker rm -f flask-run-135 > /dev/null
echo 'OK, all done'
