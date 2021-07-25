#!/bin/bash

cd "$(dirname "$0")"

_fail() {
    docker rm -f gunicorn-app-factory-sample > /dev/null 2>&1
    exit 1
}

docker build -f Dockerfile -t gunicorn-app-factory-sample ../../. > /dev/null || _fail
docker run -d --name gunicorn-app-factory-sample -p 4000:4000 gunicorn-app-factory-sample > /dev/null || _fail

echo 'Waiting for Gunicorn to start...'

for _ in $(seq 1 10); do
    PROCESS_COUNT=$(docker exec gunicorn-app-factory-sample sh -c 'pgrep -a gunicorn | wc -l')
    if [ $PROCESS_COUNT -ge 5 ]; then
        break
    fi
done

echo 'Starting the tests...'

for _ in $(seq 1 10); do
    curl -s http://localhost:4000/test > /dev/null
    if [ "$?" != "0" ]; then
        echo 'Failed to request the test endpoint'
        _fail
    fi
done

curl -s http://localhost:4000/metrics \
  | grep 'flask_http_request_duration_seconds_count{method="GET",path="/test",status="200"} 10.0' \
  > /dev/null

if [ "$?" != "0" ]; then
    echo 'The expected metrics are not found'
    _fail
fi

curl -s http://localhost:4000/metrics \
  | grep 'cnt_index_total 10.0' \
  > /dev/null

if [ "$?" != "0" ]; then
    echo 'The expected metrics are not found'
    _fail
fi

docker rm -f gunicorn-app-factory-sample > /dev/null
echo 'OK, all done'