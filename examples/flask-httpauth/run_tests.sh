#!/bin/bash

cd "$(dirname "$0")"

_fail() {
    docker rm -f flask-httpauth > /dev/null 2>&1
    exit 1
}

docker build -f Dockerfile -t flask-httpauth ../../. > /dev/null || _fail
docker run -d --name flask-httpauth -p 4000:4000 flask-httpauth > /dev/null || _fail

echo 'Waiting for the server to start...'

for _ in $(seq 1 10); do
    if curl -fs -u 'metrics:test' http://localhost:4000/metrics > /dev/null; then
        break
    else
        sleep 0.2
    fi
done

echo 'Starting the tests...'

for _ in $(seq 1 10); do
    curl -s -u 'user:pass' http://localhost:4000/test > /dev/null
    if [ "$?" != "0" ]; then
        echo 'Failed to request the test endpoint'
        _fail
    fi
done

curl -s -u 'metrics:test' http://localhost:4000/metrics \
  | grep 'flask_http_request_duration_seconds_count{method="GET",path="/test",status="200"} 10.0' \
  > /dev/null

if [ "$?" != "0" ]; then
    echo 'The expected metrics are not found'
    _fail
fi

# ensure we can't access the endpoints without authentication
if ! curl -sv http://localhost:4000/metrics 2>&1 | grep -qiE 'HTTP/[0-9.]+ 401 Unauthorized'; then
    echo 'Unexpected unauthenticated response on the metrics endpoint'
    _fail
fi
if ! curl -sv http://localhost:4000/test 2>&1 | grep -qiE 'HTTP/[0-9.]+ 401 Unauthorized'; then
    echo 'Unexpected unauthenticated response on the test endpoint'
    _fail
fi

docker rm -f flask-httpauth > /dev/null
echo 'OK, all done'
