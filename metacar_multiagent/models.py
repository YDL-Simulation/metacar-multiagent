"""多车任务场景的公开数据模型。"""

from typing import Any

from metacar import (
    ObstacleInfo,
    PoseGnss,
    RoadInfo,
    Vector3,
    VehicleControl,
)
from pydantic import BaseModel, ConfigDict, Field


class ScenarioModel(BaseModel):
    """忽略 Player 的向后兼容附加字段，只暴露正式模型字段。"""

    model_config = ConfigDict(extra="ignore")


class ScenarioVehicleInfo(ScenarioModel):
    """多车任务中一辆车辆的静态公开信息。"""

    vehicle_id: str
    display_name: str
    role: str
    length_m: float
    width_m: float
    height_m: float
    maximum_speed_mps: float


class StaticObjectInfo(ScenarioModel):
    """场景初始化时一次性公开的固定可碰撞物。"""

    id: str
    category: str
    display_name: str
    position: Vector3
    orientation_degrees: Vector3
    length_m: float
    width_m: float
    height_m: float


class MultiVehicleSceneStaticData(ScenarioModel):
    """多车任务场景的静态信息。"""

    coordinate_system: str
    roads: list[RoadInfo]
    vehicles: list[ScenarioVehicleInfo]
    static_objects: list[StaticObjectInfo]


class ScenarioTaskObjective(ScenarioModel):
    objective_id: str
    objective_type: str
    required_role: str = ""
    state: str = ""
    description: str = ""


class ScenarioUncertaintyRegion(ScenarioModel):
    shape: str = ""
    minimum: Vector3 | None = None
    maximum: Vector3 | None = None
    center: Vector3 | None = None
    radius_m: float = 0.0
    diameter_m: float = 0.0


class ScenarioSharedTaskObject(ScenarioModel):
    object_id: str
    object_type: str
    display_name: str = ""
    state: str = ""
    information_level: str = "lv0"
    information_level_index: int = 0
    uncertainty_region: ScenarioUncertaintyRegion | None = None
    valid_observation_count: int = 0
    required_observation_count: int = 0
    position: Vector3 | None = None
    orientation: Vector3 | None = None
    orientation_unit: str = "degrees"
    length_m: float = 0.0
    width_m: float = 0.0
    height_m: float = 0.0
    road_ids: list[str] = Field(default_factory=list)
    lane_ids: list[str] = Field(default_factory=list)


class ScenarioObservedTaskObject(ScenarioModel):
    object_id: str
    object_type: str
    display_name: str = ""
    state: str = ""
    distance_m: float = 0.0
    position: Vector3 | None = None
    relative_position: Vector3 | None = None
    hint: str = ""
    numeric_id: int = 0
    orientation: Vector3 | None = None
    orientation_unit: str = "degrees"
    velocity: Vector3 | None = None
    length_m: float = 0.0
    width_m: float = 0.0
    height_m: float = 0.0
    observation_token: str = ""
    observed_at_seconds: float = 0.0
    uncertainty_region: ScenarioUncertaintyRegion | None = None


class ScenarioTaskDefinition(ScenarioModel):
    """本局公开任务定义；固定规则不属于该模型。"""

    scenario_id: str
    scenario_name: str
    api_version: str
    problem_type: str
    instance_seed: int
    coordinate_system: str
    control_mode: str
    observation_model: str
    vehicles: list[ScenarioVehicleInfo] = Field(default_factory=list)
    objectives: list[ScenarioTaskObjective] = Field(default_factory=list)
    shared_task_objects: list[ScenarioSharedTaskObject] = Field(default_factory=list)
    allowed_actions: list[str] = Field(default_factory=list)


class ScenarioTaskState(ScenarioModel):
    phase: str = ""
    instance_seed: int = 0
    shared_task_objects: list[ScenarioSharedTaskObject] = Field(default_factory=list)
    verified_signal_count: int = 0
    total_signal_count: int = 0
    unlocked_destination_count: int = 0
    total_destination_count: int = 0
    roadblock_active: bool = False
    intersection_owner: str = ""


class ScenarioVehicleState(ScenarioModel):
    vehicle_id: str
    state: str
    pose: PoseGnss
    speed_mps: float
    control: VehicleControl


class ScenarioObservation(ScenarioModel):
    vehicle_id: str
    role: str = ""
    phase: str = ""
    position: Vector3
    visible_objects: list[ScenarioObservedTaskObject] = Field(default_factory=list)
    obstacles: list[ObstacleInfo] = Field(default_factory=list)
    shared_task_objects: list[ScenarioSharedTaskObject] = Field(default_factory=list)
    verified_signal_count: int = 0
    total_signal_count: int = 0
    unlocked_destination_count: int = 0
    total_destination_count: int = 0
    roadblock_active: bool = False
    intersection_owner: str = ""


class ScenarioInteractionResult(ScenarioModel):
    message: str
    vehicle_id: str
    object_id: str
    object_state: str = ""
    granted: bool = False


class ScenarioEvent(ScenarioModel):
    sequence: int
    elapsed_seconds: float
    event_type: str
    message: str
    vehicle_id: str = ""
    object_id: str = ""


JsonObject = dict[str, Any]
