"""面向多车任务场景的正式 Python 客户端。"""

import json
from pathlib import Path
import socket
from threading import Lock
from typing import Any, Iterable, Mapping

from metacar import (
    GearMode,
    ObstacleInfo,
    ObstacleType,
    PoseGnss,
    RoadInfo,
    Vector3,
    VehicleControl,
)
from pydantic import TypeAdapter, ValidationError

from .models import (
    JsonObject,
    MultiVehicleSceneStaticData,
    ScenarioEvent,
    ScenarioInteractionResult,
    ScenarioObservation,
    ScenarioObservedTaskObject,
    ScenarioTaskDefinition,
    ScenarioTaskState,
    ScenarioVehicleInfo,
    ScenarioVehicleState,
    StaticObjectInfo,
)


class ScenarioAPIError(RuntimeError):
    """多车任务 API 错误基类。"""


class ScenarioConnectionError(ScenarioAPIError):
    """连接建立、连接断开或网络传输失败。"""


class ScenarioProtocolError(ScenarioAPIError):
    """Player 返回无效 JSON 或不符合公开模型的数据。"""


class ScenarioCommandError(ScenarioAPIError):
    """Player 拒绝执行公开命令。"""


class ScenarioTaskAPI:
    """通过换行分隔 JSON 协议连接多车任务 Player。"""

    ALLOWED_ACTIONS = (
        "submit_key",
        "report_observation",
        "scan",
        "request_entry",
        "release",
        "deliver",
    )

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 9100,
        timeout: float = 3.0,
    ) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self._connection: socket.socket | None = None
        self._response_stream: Any = None
        self._request_lock = Lock()

    def __enter__(self) -> "ScenarioTaskAPI":
        return self.connect()

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def connect(self) -> "ScenarioTaskAPI":
        if self._connection is not None:
            return self
        try:
            self._connection = socket.create_connection(
                (self.host, self.port), timeout=self.timeout
            )
            self._response_stream = self._connection.makefile(
                "r", encoding="utf-8"
            )
        except OSError as error:
            self.close()
            raise ScenarioConnectionError(
                f"无法连接 MetaCar 多车任务服务 {self.host}:{self.port}：{error}"
            ) from error
        return self

    def close(self) -> None:
        if self._response_stream is not None:
            try:
                self._response_stream.close()
            finally:
                self._response_stream = None
        if self._connection is not None:
            try:
                self._connection.close()
            finally:
                self._connection = None

    def get_scene_static_data(self) -> MultiVehicleSceneStaticData:
        response = self._request({"command": "get_scene_static_data"})
        static_payload = self._mapping(response, "scene_static_data")
        roads = self._load_roads(response, static_payload)
        return self._validate(
            MultiVehicleSceneStaticData,
            {
                "coordinate_system": self._required_non_empty_string(
                    static_payload,
                    "coordinate_system",
                    "静态数据坐标系",
                ),
                "roads": roads,
                "vehicles": self._required(
                    static_payload,
                    "vehicles",
                    "静态数据任务车辆列表",
                ),
                "static_objects": self._required(
                    static_payload,
                    "static_objects",
                    "静态数据固定布景列表",
                ),
            },
            "静态场景数据",
        )

    def get_task(self) -> ScenarioTaskDefinition:
        response = self._request({"command": "get_task"})
        payload = dict(self._mapping(response, "task"))
        payload["allowed_actions"] = list(self.ALLOWED_ACTIONS)
        return self._validate(ScenarioTaskDefinition, payload, "任务定义")

    def get_task_state(self) -> ScenarioTaskState:
        response = self._request({"command": "get_task_state"})
        return self._validate(
            ScenarioTaskState,
            self._mapping(response, "task_state"),
            "任务状态",
        )

    def get_vehicle_ids(self) -> list[str]:
        response = self._request({"command": "get_vehicles"})
        vehicle_ids = response.get("vehicle_ids", [])
        if not isinstance(vehicle_ids, list) or not all(
            isinstance(vehicle_id, str) for vehicle_id in vehicle_ids
        ):
            raise ScenarioProtocolError("车辆标识列表格式无效。")
        return vehicle_ids

    def get_vehicle_state(self, vehicle_id: str) -> ScenarioVehicleState:
        self._require_id(vehicle_id, "vehicle_id")
        response = self._request(
            {"command": "get_vehicle_state", "vehicle_id": vehicle_id}
        )
        return self._vehicle_state(self._mapping(response, "vehicle_state"))

    def get_vehicle_states(self) -> list[ScenarioVehicleState]:
        response = self._request({"command": "get_all_vehicle_states"})
        payload = self._required(response, "vehicle_states", "多车状态列表")
        if not isinstance(payload, list):
            raise ScenarioProtocolError("多车状态列表格式无效。")
        return [
            self._vehicle_state(self._as_mapping(item, "车辆状态"))
            for item in payload
        ]

    def set_vehicle_control(
        self,
        vehicle_id: str,
        control: VehicleControl,
    ) -> None:
        self._require_id(vehicle_id, "vehicle_id")
        self._request(
            {
                "command": "set_vehicle_control",
                "vehicle_id": vehicle_id,
                "vehicle_control": self._control_payload(control),
            }
        )

    def set_vehicle_controls(
        self,
        controls: Mapping[str, VehicleControl],
    ) -> list[str]:
        if not controls:
            raise ValueError("controls 不能为空。")
        payload = []
        for vehicle_id, control in controls.items():
            self._require_id(vehicle_id, "vehicle_id")
            payload.append(
                {
                    "vehicle_id": vehicle_id,
                    "vehicle_control": self._control_payload(control),
                }
            )
        response = self._request(
            {"command": "set_vehicle_controls", "vehicle_controls": payload}
        )
        vehicle_ids = response.get("vehicle_ids", list(controls))
        if not isinstance(vehicle_ids, list):
            raise ScenarioProtocolError("批量控制响应中的车辆标识格式无效。")
        return [str(vehicle_id) for vehicle_id in vehicle_ids]

    def stop_vehicles(self, vehicle_ids: Iterable[str]) -> list[str]:
        controls = {
            vehicle_id: VehicleControl(brake=1.0, gear=GearMode.PARKING)
            for vehicle_id in vehicle_ids
        }
        if not controls:
            raise ValueError("vehicle_ids 不能为空。")
        return self.set_vehicle_controls(controls)

    def get_observation(self, vehicle_id: str) -> ScenarioObservation:
        self._require_id(vehicle_id, "vehicle_id")
        response = self._request(
            {"command": "get_observation", "vehicle_id": vehicle_id}
        )
        payload = dict(self._mapping(response, "observation"))
        visible_payload = payload.get("visible_objects", [])
        if not isinstance(visible_payload, list):
            raise ScenarioProtocolError("可见对象列表格式无效。")
        visible_objects = [
            self._validate(
                ScenarioObservedTaskObject,
                self._as_mapping(item, "可见对象"),
                "可见对象",
            )
            for item in visible_payload
        ]
        payload["visible_objects"] = visible_objects
        payload["obstacles"] = [
            self._obstacle_info(item)
            for item in visible_objects
            if item.numeric_id > 0 and item.position is not None
        ]
        return self._validate(ScenarioObservation, payload, "车辆观测")

    def interact(
        self,
        vehicle_id: str,
        object_id: str,
        action: str,
        payload: str | Mapping[str, Any] | None = None,
    ) -> ScenarioInteractionResult:
        self._require_id(vehicle_id, "vehicle_id")
        self._require_id(object_id, "object_id")
        if action not in self.ALLOWED_ACTIONS:
            raise ValueError(f"不允许的任务动作：{action}")
        encoded_payload = self._interaction_payload(action, payload)
        response = self._request(
            {
                "command": "interact",
                "vehicle_id": vehicle_id,
                "object_id": object_id,
                "action": action,
                "payload": encoded_payload,
            }
        )
        return self._validate(
            ScenarioInteractionResult,
            {
                "message": response.get("message", ""),
                "vehicle_id": response.get("vehicle_id", vehicle_id),
                "object_id": response.get("object_id", object_id),
                "object_state": response.get("object_state", ""),
                "granted": response.get("granted", False),
            },
            "交互结果",
        )

    @staticmethod
    def _interaction_payload(
        action: str,
        payload: str | Mapping[str, Any] | None,
    ) -> str:
        if payload is None:
            return ""
        if isinstance(payload, str):
            return payload
        if not isinstance(payload, Mapping):
            raise TypeError("payload 必须是字符串、字典或 None。")
        field_name = {
            "report_observation": "observation_token",
            "submit_key": "key",
        }.get(action)
        if field_name is None:
            raise ValueError(f"动作 {action} 不接受字典 payload。")
        value = payload.get(field_name)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"{action} 的字典 payload 必须包含非空 {field_name}。"
            )
        return value

    def get_events(self, after_sequence: int = 0) -> list[ScenarioEvent]:
        response = self._request(
            {"command": "get_events", "after_sequence": max(0, after_sequence)}
        )
        return self._validate(
            list[ScenarioEvent], response.get("events", []), "任务事件"
        )

    def _request(self, command: Mapping[str, Any]) -> JsonObject:
        self.connect()
        encoded = (json.dumps(command, ensure_ascii=False) + "\n").encode("utf-8")
        with self._request_lock:
            try:
                assert self._connection is not None
                assert self._response_stream is not None
                self._connection.sendall(encoded)
                response_line = self._response_stream.readline()
            except (OSError, ValueError) as error:
                self.close()
                raise ScenarioConnectionError(
                    f"多车任务服务通信失败：{error}"
                ) from error
        if not response_line:
            self.close()
            raise ScenarioConnectionError("多车任务服务已断开，未返回响应。")
        try:
            response = json.loads(response_line)
        except json.JSONDecodeError as error:
            raise ScenarioProtocolError(
                "多车任务服务返回了无效 JSON。"
            ) from error
        if not isinstance(response, dict):
            raise ScenarioProtocolError("多车任务服务响应必须是 JSON 对象。")
        if not response.get("ok"):
            raise ScenarioCommandError(
                str(response.get("message", "命令执行失败。"))
            )
        return response

    @staticmethod
    def _load_roads(
        response: JsonObject,
        static_payload: Mapping[str, Any],
    ) -> list[RoadInfo]:
        if "roads" in static_payload:
            return ScenarioTaskAPI._validate(
                list[RoadInfo],
                static_payload["roads"],
                "静态道路数据",
            )
        map_path_value = response.get("map_path") or static_payload.get("map_path")
        if not isinstance(map_path_value, str) or not map_path_value:
            raise ScenarioProtocolError("静态数据响应缺少 roads 或 map_path。")
        map_path = Path(map_path_value)
        try:
            return TypeAdapter(list[RoadInfo]).validate_json(map_path.read_bytes())
        except (OSError, ValidationError) as error:
            raise ScenarioProtocolError(
                f"无法读取正式道路数据 {map_path}：{error}"
            ) from error

    @staticmethod
    def _vehicle_state(payload: Mapping[str, Any]) -> ScenarioVehicleState:
        position = ScenarioTaskAPI._vector(
            ScenarioTaskAPI._required(payload, "position", "车辆位置"),
            "车辆位置",
        )
        orientation = ScenarioTaskAPI._vector(
            ScenarioTaskAPI._required(payload, "orientation", "车辆姿态"),
            "车辆姿态",
        )
        velocity = ScenarioTaskAPI._vector(
            ScenarioTaskAPI._required(payload, "velocity", "车辆速度"),
            "车辆速度",
        )
        pose = PoseGnss.model_validate(
            {
                "posX": position.x,
                "posY": position.y,
                "posZ": position.z,
                "velX": velocity.x,
                "velY": velocity.y,
                "velZ": velocity.z,
                "oriX": orientation.x,
                "oriY": orientation.y,
                "oriZ": orientation.z,
            }
        )
        return ScenarioTaskAPI._validate(
            ScenarioVehicleState,
            {
                "vehicle_id": ScenarioTaskAPI._required_non_empty_string(
                    payload,
                    "vehicle_id",
                    "车辆标识",
                ),
                "state": ScenarioTaskAPI._required_non_empty_string(
                    payload,
                    "state",
                    "车辆运行状态",
                ),
                "pose": pose,
                "speed_mps": ScenarioTaskAPI._required_number(
                    payload,
                    "speed_mps",
                    "车辆纵向速度",
                ),
                "control": ScenarioTaskAPI._control_from_payload(
                    ScenarioTaskAPI._as_mapping(
                        ScenarioTaskAPI._required(
                            payload,
                            "vehicle_control",
                            "车辆控制状态",
                        ),
                        "车辆控制状态",
                    )
                ),
            },
            "车辆状态",
        )

    @staticmethod
    def _control_payload(control: VehicleControl) -> JsonObject:
        if not isinstance(control, VehicleControl):
            raise TypeError("control 必须是 metacar.VehicleControl。")
        return {
            "throttle": control.throttle,
            "brake": control.brake,
            "steering": control.steering,
            "gear": control.gear.value,
            "front_light": control.headlights_on,
            "left_blinker": control.left_blinker_on,
            "right_blinker": control.right_blinker_on,
            "double_flash": control.hazard_lights_on,
        }

    @staticmethod
    def _control_from_payload(payload: Mapping[str, Any]) -> VehicleControl:
        gear_value = ScenarioTaskAPI._required_integer(
            payload,
            "gear",
            "车辆挡位",
        )
        try:
            gear = GearMode(gear_value)
        except ValueError as error:
            raise ScenarioProtocolError("车辆挡位格式无效。") from error
        return VehicleControl(
            throttle=ScenarioTaskAPI._required_number(
                payload, "throttle", "车辆油门"
            ),
            brake=ScenarioTaskAPI._required_number(
                payload, "brake", "车辆制动"
            ),
            steering=ScenarioTaskAPI._required_number(
                payload, "steering", "车辆转向"
            ),
            gear=gear,
            left_blinker_on=ScenarioTaskAPI._required_boolean_alias(
                payload,
                "left_blinker",
                "Signal_Light_LeftBlinker",
                "车辆左转向灯",
            ),
            right_blinker_on=ScenarioTaskAPI._required_boolean_alias(
                payload,
                "right_blinker",
                "Signal_Light_RightBlinker",
                "车辆右转向灯",
            ),
            hazard_lights_on=ScenarioTaskAPI._required_boolean_alias(
                payload,
                "double_flash",
                "Signal_Light_DoubleFlash",
                "车辆双闪灯",
            ),
            headlights_on=ScenarioTaskAPI._required_boolean_alias(
                payload,
                "front_light",
                "Signal_Light_FrontLight",
                "车辆前灯",
            ),
        )

    @staticmethod
    def _obstacle_info(item: ScenarioObservedTaskObject) -> ObstacleInfo:
        assert item.position is not None
        orientation = item.orientation or Vector3(0.0, 0.0, 0.0)
        velocity = item.velocity or Vector3(0.0, 0.0, 0.0)
        return ObstacleInfo.model_validate(
            {
                "id": item.numeric_id,
                "type": ObstacleType.STATIC.value,
                "posX": item.position.x,
                "posY": item.position.y,
                "posZ": item.position.z,
                "velX": velocity.x,
                "velY": velocity.y,
                "velZ": velocity.z,
                "oriX": orientation.x,
                "oriY": orientation.y,
                "oriZ": orientation.z,
                "length": item.length_m,
                "width": item.width_m,
                "height": item.height_m,
                "RedundantValue": None,
            }
        )

    @staticmethod
    def _vector(value: Any, label: str) -> Vector3:
        try:
            return TypeAdapter(Vector3).validate_python(value)
        except ValidationError as error:
            raise ScenarioProtocolError(f"{label}格式无效：{error}") from error

    @staticmethod
    def _validate(type_: Any, value: Any, label: str):
        try:
            return TypeAdapter(type_).validate_python(value)
        except ValidationError as error:
            raise ScenarioProtocolError(f"{label}格式无效：{error}") from error

    @staticmethod
    def _mapping(container: Mapping[str, Any], key: str) -> Mapping[str, Any]:
        return ScenarioTaskAPI._as_mapping(container.get(key), key)

    @staticmethod
    def _as_mapping(value: Any, label: str) -> Mapping[str, Any]:
        if not isinstance(value, Mapping):
            raise ScenarioProtocolError(f"{label}必须是 JSON 对象。")
        return value

    @staticmethod
    def _required(
        container: Mapping[str, Any],
        key: str,
        label: str,
    ) -> Any:
        if key not in container:
            raise ScenarioProtocolError(f"响应缺少{label}。")
        return container[key]

    @staticmethod
    def _required_non_empty_string(
        container: Mapping[str, Any],
        key: str,
        label: str,
    ) -> str:
        value = ScenarioTaskAPI._required(container, key, label)
        if not isinstance(value, str) or not value.strip():
            raise ScenarioProtocolError(f"{label}必须是非空字符串。")
        return value

    @staticmethod
    def _required_number(
        container: Mapping[str, Any],
        key: str,
        label: str,
    ) -> float:
        value = ScenarioTaskAPI._required(container, key, label)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ScenarioProtocolError(f"{label}必须是数值。")
        return float(value)

    @staticmethod
    def _required_integer(
        container: Mapping[str, Any],
        key: str,
        label: str,
    ) -> int:
        value = ScenarioTaskAPI._required(container, key, label)
        if isinstance(value, bool) or not isinstance(value, int):
            raise ScenarioProtocolError(f"{label}必须是整数。")
        return value

    @staticmethod
    def _required_boolean_alias(
        container: Mapping[str, Any],
        key: str,
        legacy_key: str,
        label: str,
    ) -> bool:
        if key in container:
            value = container[key]
        elif legacy_key in container:
            value = container[legacy_key]
        else:
            raise ScenarioProtocolError(f"响应缺少{label}。")
        if not isinstance(value, bool):
            raise ScenarioProtocolError(f"{label}必须是布尔值。")
        return value

    @staticmethod
    def _require_id(value: str, label: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{label} 不能为空。")
