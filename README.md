# metacar-multiagent

`metacar-multiagent` 是基于 `metacar 0.4.0` 的多车协同场景扩展包。它不修改、
覆盖或替换原 `metacar`；旧场景继续使用 `metacar.SceneAPI`，多车任务场景使用
`metacar_multiagent.ScenarioTaskAPI`。

本项目独立维护、独立测试和独立发布。`metacar` 是基础依赖，不是本项目的源码
组成部分。

## 安装

使用正式学生资料包提供的两个 wheel，在它们所在目录执行：

```bash
python -m pip install ./metacar-0.4.0-py3-none-any.whl ./metacar_multiagent-0.1.0-py3-none-any.whl
```

扩展包固定依赖 `metacar==0.4.0`。基础包还需要 numpy、opencv-python、pydantic 等依赖，
安装时应能访问依赖源或已备齐相应文件；仅这两个 wheel 不代表完整的离线安装环境。

PyPI 版本发布后，也可执行 `python -m pip install metacar-multiagent==0.1.0`。
发行状态和安装文件以本仓库的 Release 页面为准。

## 最小示例

源码仓库和源码发行包提供 `examples/minimal_control.py`；wheel 不会将示例安装到当前目录。
通过客户端启动场景后，在下载的源码目录执行 `python examples/minimal_control.py`。
港口开发站试用使用开发版客户端。示例仅检查连接和停车，不完成运输任务。

```python
from metacar_multiagent import GearMode, ScenarioTaskAPI, VehicleControl

with ScenarioTaskAPI() as api:
    scene = api.get_scene_static_data()
    task = api.get_task()
    vehicle_ids = api.get_vehicle_ids()

    try:
        api.set_vehicle_controls({
            vehicle_id: VehicleControl(brake=1.0, gear=GearMode.PARKING)
            for vehicle_id in vehicle_ids
        })
    finally:
        api.stop_vehicles(vehicle_ids)
```

道路、车辆、固定布景和已感知障碍通过接口读取。固定任务规则和评分规则以正式文档
为准。

## 开发

先准备 Python 3.10 或更高版本，再安装本项目及开发依赖：

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
```

运行测试：

```powershell
.venv\Scripts\python -m unittest discover -s tests -p "test_*.py" -v
```

构建文档和发布包：

```powershell
.venv\Scripts\sphinx-build -W --keep-going -b html docs docs/_build/html
.venv\Scripts\python -m build
```

发布新版本前，应同步检查 `pyproject.toml`、`metacar_multiagent/__init__.py`、
`docs/conf.py` 和 `scripts/validate_release.py` 中的版本及构建标识，并在全新环境中
验证 wheel 和 sdist 均可与 `metacar 0.4.0` 共存。完整流程见 [发布手册](RELEASING.md)。
