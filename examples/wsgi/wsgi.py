import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

os.environ["PROMETHEUS_MULTIPROC_DIR"] = "/tmp"
os.environ["prometheus_multiproc_dir"] = "/tmp"

from app import app as application
