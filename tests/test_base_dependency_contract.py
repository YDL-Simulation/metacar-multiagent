"""基础依赖声明与发行包元数据的契约测试。"""
import ast
import importlib.util
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile

# 发布验证会从干净目录运行测试；只按文件加载维护者脚本，不把源码根目录
# 加入 sys.path，以免 wheel/sdist 的运行时测试误导入工作区扩展源码。
_spec = importlib.util.spec_from_file_location(
    "base_dependency_release_check",
    Path(__file__).resolve().parents[1] / "scripts/validate_release.py",
)
_release_check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_release_check)
has_exact_base_dependency = _release_check.has_exact_base_dependency
inspect_wheel = _release_check.inspect_wheel


class BaseDependencyContractTests(unittest.TestCase):
    def test_helper_loads_from_clean_directory_without_adding_source_path(self):
        code = (
            "import importlib.util, sys; before=list(sys.path); "
            "spec=importlib.util.spec_from_file_location('dependency_test', sys.argv[1]); "
            "module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); "
            "assert module.has_exact_base_dependency(['metacar==0.4.0']); "
            "assert sys.path == before"
        )
        with tempfile.TemporaryDirectory() as temporary:
            result = subprocess.run([sys.executable, "-I", "-c", code, str(Path(__file__).resolve())],
                                    cwd=temporary, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_source_dependency_is_exact(self):
        source = (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text("utf-8")
        dependencies = ast.literal_eval(re.search(r"(?m)^dependencies = (\[[\s\S]*?\])", source)[1])
        self.assertTrue(has_exact_base_dependency(dependencies))
        self.assertIn('version = "0.1.0"', source)
        self.assertIn('requires-python = ">=3.10"', source)
        self.assertEqual(dependencies, ["metacar==0.4.0", "pydantic>=2.0.0"])

    def test_exact_unconditional_spellings(self):
        for requirement in ["metacar==0.4.0", "MetaCar (==0.4.0)", " metacar == 0.4.0 "]:
            with self.subTest(requirement=requirement):
                self.assertTrue(has_exact_base_dependency([requirement, "pydantic>=2.0.0"]))

    def test_rejects_unsupported_dependency_forms(self):
        cases = [[], ["metacar<0.5,>=0.4"], ["metacar==0.4.1"],
                 ["metacar==0.4.*"], ["metacar===0.4.0"],
                 ['metacar==0.4.0; python_version >= "3.10"'],
                 ['metacar==0.4.0; extra == "dev"'],
                 ["metacar[extra]==0.4.0"], ["metacar @ file:///base.whl"],
                 ["metacar==0.4.0,!=0.4.1"], ["metacar_extra==0.4.0"],
                 ["metacar==0.4.0", "metacar>=0.4"],
                 ["metacar==0.4.0", "metacar==0.4.0"]]
        for requirements in cases:
            with self.subTest(requirements=requirements):
                self.assertFalse(has_exact_base_dependency(requirements))

    def inspect_fixture(self, requirements, forbidden=False):
        with tempfile.TemporaryDirectory() as temporary:
            wheel = Path(temporary) / "synthetic.whl"
            with zipfile.ZipFile(wheel, "w") as archive:
                archive.writestr("metacar_multiagent/__init__.py", "")
                archive.writestr("metacar_multiagent-0.1.0.dist-info/METADATA",
                                 "Metadata-Version: 2.1\nName: metacar-multiagent\nVersion: 0.1.0\n"
                                 + "".join(f"Requires-Dist: {r}\n" for r in requirements))
                if forbidden:
                    archive.writestr("metacar/__init__.py", "")
            return inspect_wheel(wheel)

    def test_synthetic_wheel_accepts_exact(self):
        self.assertTrue(self.inspect_fixture(["metacar==0.4.0", "pydantic>=2.0.0"])["passed"])

    def test_synthetic_wheel_rejects_wrong_missing_and_conditional(self):
        for requirement in [None, "metacar<0.5,>=0.4", "metacar==0.4.1",
                            'metacar==0.4.0; python_version >= "3.10"']:
            with self.subTest(requirement=requirement):
                requirements = ["pydantic>=2.0.0"] + ([requirement] if requirement else [])
                self.assertFalse(self.inspect_fixture(requirements)["passed"])

    def test_original_package_directory_still_forbidden(self):
        result = self.inspect_fixture(["metacar==0.4.0", "pydantic>=2.0.0"], forbidden=True)
        self.assertTrue(result["exact_base_dependency"])
        self.assertFalse(result["passed"])
        self.assertEqual(result["forbidden_metacar_entries"], ["metacar/__init__.py"])


if __name__ == "__main__":
    unittest.main()
