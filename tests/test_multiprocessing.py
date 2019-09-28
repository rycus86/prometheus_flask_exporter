from unittest_helper import BaseTestCase
import tempfile
import shutil
import os
from prometheus_flask_exporter.multiprocess import _check_multiproc_env_var
from unittest.mock import patch


class TestEnvDir(BaseTestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir)

    def test_check_multiproc_env_var_works_with_lowercase(self):
        with patch.dict(os.environ, {'prometheus_multiproc_dir': 'not_a_dir'}):
            self.assertRaises(ValueError, _check_multiproc_env_var)
        with patch.dict(os.environ, {"prometheus_multiproc_dir": self.temp_dir}):
            self.assertIsNone(_check_multiproc_env_var())

    def test_check_multiproc_env_var_works_with_uppercase(self):
        with patch.dict(os.environ, {'PROMETHEUS_MULTIPROC_DIR': 'not_a_dir'}):
            self.assertRaises(ValueError, _check_multiproc_env_var)
        with patch.dict(os.environ, {"PROMETHEUS_MULTIPROC_DIR": self.temp_dir}):
            self.assertIsNone(_check_multiproc_env_var())
