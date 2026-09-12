"""审计 metacar-multiagent 发布物并生成机器可读证据。"""

from __future__ import annotations

import argparse
from email.parser import Parser
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile
import tempfile
from typing import Any
import zipfile


PACKAGE_NAME = "metacar-multiagent"
IMPORT_NAME = "metacar_multiagent"
VERSION = "0.1.0"
BUILD_ID = "simcar.portfog.multiagent.1"
CONTRACT = "R-A1B-API-01"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def run(command: list[str], cwd: Path) -> dict[str, Any]:
    environment = dict(os.environ)
    environment["PYTHONUTF8"] = "1"
    result = subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    output = result.stdout.strip()
    match = re.search(r"Ran (\d+) tests?", output)
    return {
        "passed": result.returncode == 0,
        "return_code": result.returncode,
        "test_count": int(match.group(1)) if match else None,
        "output_tail": "\n".join(output.splitlines()[-12:]),
    }


def installed_probe(python: Path, cwd: Path) -> dict[str, Any]:
    code = r'''
import importlib.metadata as metadata
import json
import metacar
import metacar_multiagent as extension

shared = [
    "VehicleControl", "GearMode", "PoseGnss", "RoadInfo", "LaneInfo",
    "BorderInfo", "LineType", "DrivingType", "TrafficSignType",
    "ObstacleInfo", "ObstacleType", "Vector2", "Vector3",
]
print(json.dumps({
    "metacar_distribution_version": metadata.version("metacar"),
    "extension_distribution_version": metadata.version("metacar-multiagent"),
    "metacar_module_path": metacar.__file__,
    "extension_module_path": extension.__file__,
    "extension_version": extension.__version__,
    "build_id": extension.SDK_BUILD_ID,
    "contract": extension.SDK_CONTRACT,
    "base_scene_api_present": hasattr(metacar, "SceneAPI"),
    "extension_scene_api_absent": not hasattr(extension, "SceneAPI"),
    "rules_model_absent": not hasattr(extension, "ScenarioTaskRules"),
    "task_rules_field_absent": "rules" not in extension.ScenarioTaskDefinition.model_fields,
    "old_static_model_name_absent": not hasattr(extension, "SceneStaticData"),
    "multi_vehicle_static_model_present": hasattr(extension, "MultiVehicleSceneStaticData"),
    "multi_vehicle_static_model_fields": sorted(
        extension.MultiVehicleSceneStaticData.model_fields
    ) if hasattr(extension, "MultiVehicleSceneStaticData") else [],
    "shared_type_identity": {
        name: getattr(extension, name) is getattr(metacar, name)
        for name in shared
    },
}, ensure_ascii=False))
'''
    result = subprocess.run(
        [str(python), "-c", code],
        cwd=cwd,
        env={**os.environ, "PYTHONUTF8": "1"},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        return {
            "passed": False,
            "return_code": result.returncode,
            "output": result.stdout.strip(),
        }
    try:
        payload = json.loads(result.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError) as error:
        return {
            "passed": False,
            "return_code": result.returncode,
            "output": result.stdout.strip(),
            "parse_error": str(error),
        }
    shared_identity = payload.get("shared_type_identity", {})
    payload["passed"] = bool(
        payload.get("metacar_distribution_version") == "0.4.0"
        and payload.get("extension_distribution_version") == VERSION
        and payload.get("extension_version") == VERSION
        and payload.get("build_id") == BUILD_ID
        and payload.get("contract") == CONTRACT
        and payload.get("base_scene_api_present")
        and payload.get("extension_scene_api_absent")
        and payload.get("rules_model_absent")
        and payload.get("task_rules_field_absent")
        and payload.get("old_static_model_name_absent")
        and payload.get("multi_vehicle_static_model_present")
        and payload.get("multi_vehicle_static_model_fields")
        == ["coordinate_system", "roads", "static_objects", "vehicles"]
        and shared_identity
        and all(shared_identity.values())
    )
    return payload


def has_exact_base_dependency(requires: list[str]) -> bool:
    """基础依赖必须唯一且无条件，不接受范围、额外约束或环境分支。"""
    base_requirements = []
    for requirement in requires:
        name = re.match(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)", requirement)
        if name and re.sub(r"[-_.]+", "-", name.group(1)).lower() == "metacar":
            base_requirements.append(requirement)
    return len(base_requirements) == 1 and re.fullmatch(
        r"\s*metacar\s*(?:==\s*0\.4\.0|\(\s*==\s*0\.4\.0\s*\))\s*",
        base_requirements[0], re.IGNORECASE,
    ) is not None


def inspect_wheel(path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(path) as archive:
        names = sorted(archive.namelist())
        metadata_name = next(
            name for name in names if name.endswith(".dist-info/METADATA")
        )
        metadata = Parser().parsestr(
            archive.read(metadata_name).decode("utf-8")
        )
    roots = sorted({name.split("/", 1)[0] for name in names})
    requires = metadata.get_all("Requires-Dist", [])
    package_files = [name for name in names if name.startswith(f"{IMPORT_NAME}/")]
    forbidden = [name for name in names if name.startswith("metacar/")]
    passed = bool(
        package_files
        and not forbidden
        and metadata.get("Name") == PACKAGE_NAME
        and metadata.get("Version") == VERSION
        and has_exact_base_dependency(requires)
        and any(requirement.startswith("pydantic>=2") for requirement in requires)
    )
    return {
        "path": str(path),
        "size_bytes": path.stat().st_size,
        "sha256": sha256(path),
        "archive_roots": roots,
        "entry_count": len(names),
        "requires_dist": requires,
        "exact_base_dependency": has_exact_base_dependency(requires),
        "forbidden_metacar_entries": forbidden,
        "passed": passed,
    }


def inspect_sdist(path: Path) -> dict[str, Any]:
    with tarfile.open(path, "r:gz") as archive:
        names = sorted(member.name for member in archive.getmembers())
    relative_names = [
        name.split("/", 1)[1] if "/" in name else "" for name in names
    ]
    roots = sorted({name.split("/", 1)[0] for name in names})
    forbidden = [
        name for name, relative in zip(names, relative_names)
        if relative == "metacar" or relative.startswith("metacar/")
    ]
    required = {
        "pyproject.toml",
        "README.md",
        "LICENSE",
        "metacar_multiagent/__init__.py",
        "scripts/validate_release.py",
    }
    missing = sorted(required.difference(relative_names))
    return {
        "path": str(path),
        "size_bytes": path.stat().st_size,
        "sha256": sha256(path),
        "archive_roots": roots,
        "entry_count": len(names),
        "forbidden_metacar_entries": forbidden,
        "missing_required_entries": missing,
        "passed": not forbidden and not missing,
    }


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=root)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--source-python", type=Path, default=root / ".build-venv/Scripts/python.exe"
    )
    parser.add_argument(
        "--wheel-python",
        type=Path,
        default=root / ".test-venv-wheel/Scripts/python.exe",
    )
    parser.add_argument(
        "--sdist-python",
        type=Path,
        default=root / ".test-venv-sdist/Scripts/python.exe",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    wheel = next((root / "dist").glob(f"{IMPORT_NAME}-{VERSION}-*.whl"))
    sdist = root / "dist" / f"{IMPORT_NAME}-{VERSION}.tar.gz"
    if not sdist.is_file():
        raise FileNotFoundError(sdist)
    for python in (args.source_python, args.wheel_python, args.sdist_python):
        if not python.is_file():
            raise FileNotFoundError(python)

    with tempfile.TemporaryDirectory(prefix="metacar-multiagent-audit-") as temp:
        clean_cwd = Path(temp)
        source_tests = run(
            [
                str(args.source_python),
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests",
                "-p",
                "test_*.py",
                "-v",
            ],
            root,
        )
        wheel_probe = installed_probe(args.wheel_python, clean_cwd)
        sdist_probe = installed_probe(args.sdist_python, clean_cwd)
        wheel_tests = run(
            [
                str(args.wheel_python),
                "-m",
                "unittest",
                "discover",
                "-s",
                str(root / "tests"),
                "-p",
                "test_*.py",
                "-v",
            ],
            clean_cwd,
        )
        wheel_pip_check = run(
            [str(args.wheel_python), "-m", "pip", "check"], clean_cwd
        )
        sdist_tests = run(
            [
                str(args.sdist_python),
                "-m",
                "unittest",
                "discover",
                "-s",
                str(root / "tests"),
                "-p",
                "test_*.py",
                "-v",
            ],
            clean_cwd,
        )
        sdist_pip_check = run(
            [str(args.sdist_python), "-m", "pip", "check"], clean_cwd
        )
        sphinx = run(
            [
                str(args.source_python),
                "-m",
                "sphinx",
                "-W",
                "--keep-going",
                "-b",
                "html",
                str(root / "docs"),
                str(clean_cwd / "sphinx-html"),
            ],
            clean_cwd,
        )

    evidence: dict[str, Any] = {
        "schema_version": 1,
        "package": {
            "distribution": PACKAGE_NAME,
            "import_name": IMPORT_NAME,
            "version": VERSION,
            "build_id": BUILD_ID,
            "contract": CONTRACT,
            "source_root": str(root),
        },
        "artifacts": {
            "wheel": inspect_wheel(wheel),
            "sdist": inspect_sdist(sdist),
        },
        "checks": {
            "source_tests": source_tests,
            "wheel_installed_probe": wheel_probe,
            "wheel_installed_tests": wheel_tests,
            "wheel_dependency_check": wheel_pip_check,
            "sdist_installed_probe": sdist_probe,
            "sdist_installed_tests": sdist_tests,
            "sdist_dependency_check": sdist_pip_check,
            "sphinx_strict": sphinx,
        },
    }
    all_checks = [
        evidence["artifacts"]["wheel"]["passed"],
        evidence["artifacts"]["sdist"]["passed"],
        *(check.get("passed", False) for check in evidence["checks"].values()),
    ]
    evidence["passed"] = all(all_checks)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"passed": evidence["passed"], "output": str(args.output)}))
    return 0 if evidence["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
