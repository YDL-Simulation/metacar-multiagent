"""Small packaging guard checks, independent of the simulator."""
import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('public_guard',Path(__file__).resolve().parents[1]/'scripts/check_public_release.py')
guard=importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

class ReleaseBoundaryTests(unittest.TestCase):
    def test_public_paths(self):
        for p in ['metacar_multiagent/api.py','examples/minimal_control.py','RELEASING.md','.github/workflows/python-tests.yml']:
            self.assertTrue(guard.allowed(p),p)
    def test_private_or_unsafe_paths(self):
        for p in ['Artifacts/run.json','examples/full_solution.py','metacar/api.py','docs/_build/index.html','../secret.py','/secret.py','.env','tests/__pycache__/x.py']:
            self.assertFalse(guard.allowed(p),p)
    def test_credential_detection(self):
        with self.assertRaises(ValueError): guard.check_content('dummy',b'pypi-'+b'x'*50)
    def test_normal_content(self):
        guard.check_content('example',b'from metacar_multiagent import ScenarioTaskAPI')
