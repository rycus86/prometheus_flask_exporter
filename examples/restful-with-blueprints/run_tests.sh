#!/bin/bash

cd "$(dirname "$0")"

_fail() {
    docker rm -f restful-with-blueprints > /dev/null 2>&1
    exit 1
}

docker build -f Dockerfile -t restful-with-blueprints ../../. > /dev/null || _fail
docker run -d --name restful-with-blueprints -p 4000:4000 restful-with-blueprints > /dev/null || _fail

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
    curl -s http://localhost:4000/api/v1/test > /dev/null
    if [ "$?" != "0" ]; then
        echo 'Failed to request the test endpoint'
        _fail
    fi
done

for _ in $(seq 1 7); do
    curl -s 'http://localhost:4000/api/v1/test?fail=1' > /dev/null
done

curl -s http://localhost:4000/metrics \
  | grep 'test_by_status_count{code="200"} 10.0' \
  > /dev/null

if [ "$?" != "0" ]; then
    echo 'The expected metrics are not found'
    _fail
fi

curl -s http://localhost:4000/metrics \
  | grep 'test_by_status_count{code="400"} 7.0' \
  > /dev/null

if [ "$?" != "0" ]; then
    echo 'The expected metrics are not found'
    _fail
fi

docker rm -f restful-with-blueprints > /dev/null
echo 'OK, all done'
