import time
import random
import threading
import requests

endpoints = ("one", "two", "three", "four", "error")
HOST = "http://app:5000/"


def run():
    while True:
        try:
            target = random.choice(endpoints)
            requests.get(HOST + target, timeout=1)
        except:
            print("cannot connect", HOST)
            time.sleep(1)


if __name__ == "__main__":
    for _ in range(4):
        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()

    while True:
        time.sleep(1)
