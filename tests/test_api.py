import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import metacar

from metacar_multiagent import (
    GearMode,
    MultiVehicleSceneStaticData,
    ObstacleType,
    ScenarioCommandError,
    ScenarioProtocolError,
    ScenarioTaskAPI,
    VehicleControl,
)


class ScenarioTaskAPITests(unittest.TestCase):
    def setUp(self):
        self.api = ScenarioTaskAPI()

    def tearDown(self):
        self.api.close()

    def test_static_data_uses_extension_model_and_base_road_types(self):
        with tempfile.TemporaryDirectory() as directory:
            map_path = Path(directory) / "mapd"
            map_path.write_text("[]", encoding="utf-8")
            response = {
                "ok": True,
                "map_path": str(map_path),
                "scene_static_data": {
                    "coordinate_system": "metacar_world",
                    "vehicles": [
                        {
                            "vehicle_id": "Car_A",
                            "display_name": "运输车 A",
                            "role": "transport",
                            "length_m": 5.0,
                            "width_m": 2.0,
                            "height_m": 2.2,
                            "maximum_speed_mps": 8.0,
                        }
                    ],
                    "static_objects": [
                        {
                            "id": "warehouse-01",
                            "category": "warehouse",
                            "display_name": "仓库 01",
                            "position": {"x": 1.0, "y": 2.0, "z": 0.0},
                            "orientation_degrees": {
                                "x": 0.0,
                                "y": 0.0,
                                "z": 90.0,
                            },
                            "length_m": 20.0,
                            "width_m": 10.0,
                            "height_m": 8.0,
                        }
                    ],
                },
            }
            with patch.object(self.api, "_request", return_value=response):
                static_data = self.api.get_scene_static_data()

        self.assertEqual("metacar_world", static_data.coordinate_system)
        self.assertIsInstance(static_data, MultiVehicleSceneStaticData)
        self.assertEqual([], static_data.roads)
        self.assertEqual("Car_A", static_data.vehicles[0].vehicle_id)
        self.assertEqual("warehouse", static_data.static_objects[0].category)
        self.assertFalse(hasattr(static_data, "route"))

    def test_static_data_rejects_missing_required_fields(self):
        complete = {
            "coordinate_system": "metacar_world",
            "roads": [],
            "vehicles": [],
            "static_objects": [],
        }
        for missing in ("coordinate_system", "vehicles", "static_objects"):
            with self.subTest(missing=missing):
                payload = dict(complete)
                payload.pop(missing)
                response = {"ok": True, "scene_static_data": payload}
                with patch.object(self.api, "_request", return_value=response):
                    with self.assertRaises(ScenarioProtocolError):
                        self.api.get_scene_static_data()

    def test_static_data_rejects_invalid_required_field_types(self):
        response = {
            "ok": True,
            "scene_static_data": {
                "coordinate_system": 123,
                "roads": [],
                "vehicles": {},
                "static_objects": [],
            },
        }
        with patch.object(self.api, "_request", return_value=response):
            with self.assertRaises(ScenarioProtocolError):
                self.api.get_scene_static_data()

    def test_task_does_not_define_or_return_rules(self):
        response = {
            "ok": True,
            "task": {
                "scenario_id": "PORT-FOG-01",
                "scenario_name": "港口迷雾协同运输",
                "api_version": "1.0",
                "problem_type": "multi_vehicle_task",
                "instance_seed": 7,
                "coordinate_system": "metacar_world",
                "control_mode": "vehicle_control_heartbeat",
                "observation_model": "limited_fov",
                "rules": {
                    "observation_radius_m": 30.0,
                    "road_boundary_contact_seconds": 0.2,
                },
            },
        }
        with patch.object(self.api, "_request", return_value=response):
            task = self.api.get_task()

        self.assertFalse(hasattr(task, "rules"))
        self.assertFalse(hasattr(task, "road_boundaries"))
        self.assertIn("deliver", task.allowed_actions)

    def test_task_and_state_preserve_current_public_signal(self):
        signal = {
            "object_id": "Signal_A",
            "object_type": "signal",
            "display_name": "海关闸口",
            "information_level": "lv3",
            "information_level_index": 3,
            "position": {"x": 20.0, "y": 13.5, "z": 0.0},
        }
        task_response = {
            "ok": True,
            "task": {
                "scenario_id": "PORT-FOG-01",
                "scenario_name": "港口迷雾协同运输",
                "api_version": "student-planning-0.2",
                "problem_type": "multi_vehicle_task_and_route_planning",
                "instance_seed": 0,
                "coordinate_system": "metacar_world",
                "control_mode": "low_level_vehicle_control",
                "observation_model": "limited_fov",
                "shared_task_objects": [signal],
            },
        }
        state_response = {
            "ok": True,
            "task_state": {
                "phase": "SignalChain",
                "instance_seed": 0,
                "shared_task_objects": [signal],
                "verified_signal_count": 0,
                "total_signal_count": 3,
            },
        }

        with patch.object(self.api, "_request", return_value=task_response):
            task = self.api.get_task()
        with patch.object(self.api, "_request", return_value=state_response):
            state = self.api.get_task_state()

        self.assertEqual("Signal_A", task.shared_task_objects[0].object_id)
        self.assertEqual("signal", task.shared_task_objects[0].object_type)
        self.assertEqual("", task.shared_task_objects[0].state)
        self.assertEqual(20.0, task.shared_task_objects[0].position.x)
        self.assertEqual(13.5, task.shared_task_objects[0].position.y)
        self.assertEqual(
            task.shared_task_objects[0],
            state.shared_task_objects[0],
        )
        self.assertFalse(hasattr(task, "road_nodes"))

    def test_task_state_preserves_resolved_roadblock_public_state(self):
        response = {
            "ok": True,
            "task_state": {
                "phase": "Roadblock",
                "instance_seed": 1,
                "shared_task_objects": [
                    {
                        "object_id": "Roadblock_West",
                        "object_type": "roadblock",
                        "display_name": "动态路障",
                        "state": "blocked",
                        "information_level": "lv3",
                        "information_level_index": 3,
                        "position": {"x": 56.0, "y": 32.0, "z": 0.0},
                        "road_ids": ["PORT_V_MAIN_P56_32_P130_S"],
                        "lane_ids": ["PORT_V_MAIN_P56_32_P130_S_0"],
                    }
                ],
                "verified_signal_count": 3,
                "total_signal_count": 3,
                "roadblock_active": True,
            },
        }

        with patch.object(self.api, "_request", return_value=response):
            state = self.api.get_task_state()

        self.assertEqual(1, len(state.shared_task_objects))
        roadblock = state.shared_task_objects[0]
        self.assertEqual("Roadblock_West", roadblock.object_id)
        self.assertEqual("roadblock", roadblock.object_type)
        self.assertEqual("blocked", roadblock.state)
        self.assertEqual(
            ["PORT_V_MAIN_P56_32_P130_S"],
            roadblock.road_ids,
        )
        self.assertEqual(
            ["PORT_V_MAIN_P56_32_P130_S_0"],
            roadblock.lane_ids,
        )
        self.assertFalse(hasattr(state, "dynamic_road_states"))

    def test_vehicle_state_preserves_reverse_speed_pose_and_effective_control(self):
        response = {
            "ok": True,
            "vehicle_state": {
                "vehicle_id": "Car_C",
                "state": "Moving",
                "position": {"x": 10.0, "y": -2.0, "z": 0.5},
                "orientation": {"x": 0.0, "y": 0.0, "z": 90.0},
                "velocity": {"x": -3.0, "y": 0.0, "z": 0.0},
                "speed_mps": -3.0,
                "vehicle_control": {
                    "throttle": 0.4,
                    "brake": 0.0,
                    "steering": -0.1,
                    "gear": 1,
                    "front_light": True,
                    "left_blinker": True,
                    "right_blinker": False,
                    "double_flash": False,
                },
            },
        }
        with patch.object(self.api, "_request", return_value=response):
            state = self.api.get_vehicle_state("Car_C")

        self.assertEqual(10.0, state.pose.pos_x)
        self.assertEqual(90.0, state.pose.ori_z)
        self.assertEqual(-3.0, state.pose.vel_x)
        self.assertEqual(-3.0, state.speed_mps)
        self.assertEqual(0.4, state.control.throttle)
        self.assertEqual(0.0, state.control.brake)
        self.assertEqual(-0.1, state.control.steering)
        self.assertEqual(GearMode.DRIVE, state.control.gear)
        self.assertTrue(state.control.headlights_on)
        self.assertTrue(state.control.left_blinker_on)
        self.assertFalse(state.control.right_blinker_on)
        self.assertFalse(state.control.hazard_lights_on)

    def test_vehicle_state_rejects_missing_required_fields(self):
        complete = self._complete_vehicle_state_payload()
        for missing in (
            "vehicle_id",
            "state",
            "position",
            "orientation",
            "velocity",
            "speed_mps",
            "vehicle_control",
        ):
            with self.subTest(missing=missing):
                payload = dict(complete)
                payload.pop(missing)
                response = {"ok": True, "vehicle_state": payload}
                with patch.object(self.api, "_request", return_value=response):
                    with self.assertRaises(ScenarioProtocolError):
                        self.api.get_vehicle_state("Car_C")

    def test_vehicle_state_rejects_empty_identity_and_partial_control(self):
        for mutate in (
            lambda payload: payload.update(vehicle_id=""),
            lambda payload: payload.update(state=""),
            lambda payload: payload["vehicle_control"].pop("throttle"),
        ):
            payload = self._complete_vehicle_state_payload()
            mutate(payload)
            response = {"ok": True, "vehicle_state": payload}
            with patch.object(self.api, "_request", return_value=response):
                with self.assertRaises(ScenarioProtocolError):
                    self.api.get_vehicle_state("Car_C")

    def test_vehicle_state_rejects_missing_nested_vector_or_control_fields(self):
        for group, fields in (
            ("position", ("x", "y", "z")),
            ("orientation", ("x", "y", "z")),
            ("velocity", ("x", "y", "z")),
            (
                "vehicle_control",
                (
                    "throttle",
                    "brake",
                    "steering",
                    "gear",
                    "front_light",
                    "left_blinker",
                    "right_blinker",
                    "double_flash",
                ),
            ),
        ):
            for missing in fields:
                with self.subTest(group=group, missing=missing):
                    payload = copy.deepcopy(
                        self._complete_vehicle_state_payload()
                    )
                    payload[group].pop(missing)
                    response = {"ok": True, "vehicle_state": payload}
                    with patch.object(self.api, "_request", return_value=response):
                        with self.assertRaises(ScenarioProtocolError):
                            self.api.get_vehicle_state("Car_C")

    def test_missing_all_vehicle_states_is_not_an_empty_snapshot(self):
        with patch.object(
            self.api,
            "_request",
            return_value={"ok": True},
        ):
            with self.assertRaises(ScenarioProtocolError):
                self.api.get_vehicle_states()

    def test_all_vehicle_states_returns_one_complete_four_vehicle_snapshot(self):
        vehicle_ids = ("Car_A", "Car_B", "Car_C", "Car_D")
        payloads = []
        for index, vehicle_id in enumerate(vehicle_ids):
            payload = copy.deepcopy(self._complete_vehicle_state_payload())
            payload["vehicle_id"] = vehicle_id
            payload["state"] = (
                "Moving" if vehicle_id in ("Car_A", "Car_B") else "Waiting"
            )
            payload["position"]["x"] = float(index * 10)
            payload["speed_mps"] = -1.0 if vehicle_id == "Car_D" else 1.0
            payloads.append(payload)

        response = {"ok": True, "vehicle_states": payloads}
        with patch.object(self.api, "_request", return_value=response) as request:
            states = self.api.get_vehicle_states()

        request.assert_called_once_with({"command": "get_all_vehicle_states"})
        self.assertEqual(list(vehicle_ids), [state.vehicle_id for state in states])
        self.assertEqual(4, len({state.vehicle_id for state in states}))
        self.assertTrue(all(state.pose is not None for state in states))
        self.assertTrue(all(state.control is not None for state in states))
        self.assertEqual(-1.0, states[-1].speed_mps)

    def test_control_uses_base_type_and_wire_mapping(self):
        captured = {}

        def request(command):
            captured.update(command)
            return {"ok": True}

        with patch.object(self.api, "_request", side_effect=request):
            self.api.set_vehicle_control(
                "Car_A",
                VehicleControl(
                    throttle=0.3,
                    steering=0.2,
                    gear=GearMode.DRIVE,
                    headlights_on=True,
                    hazard_lights_on=True,
                ),
            )

        wire_control = captured["vehicle_control"]
        self.assertTrue(wire_control["front_light"])
        self.assertTrue(wire_control["double_flash"])
        self.assertNotIn("headlights_on", wire_control)

    def test_finite_control_values_are_sent_without_extra_range_rejection(self):
        with patch.object(
            self.api,
            "_request",
            return_value={"ok": True},
        ) as request:
            self.api.set_vehicle_control(
                "Car_A",
                VehicleControl(throttle=1.1, brake=-0.2, steering=1.4),
            )

        command = request.call_args.args[0]
        self.assertEqual(1.1, command["vehicle_control"]["throttle"])
        self.assertEqual(-0.2, command["vehicle_control"]["brake"])
        self.assertEqual(1.4, command["vehicle_control"]["steering"])

    def test_batch_control_is_one_atomic_command(self):
        with patch.object(
            self.api,
            "_request",
            return_value={"ok": True, "vehicle_ids": ["Car_A", "Car_B"]},
        ) as request:
            vehicle_ids = self.api.set_vehicle_controls(
                {
                    "Car_A": VehicleControl(throttle=0.2),
                    "Car_B": VehicleControl(
                        brake=1.0, gear=GearMode.PARKING
                    ),
                }
            )

        self.assertEqual(["Car_A", "Car_B"], vehicle_ids)
        command = request.call_args.args[0]
        self.assertEqual("set_vehicle_controls", command["command"])
        self.assertEqual(2, len(command["vehicle_controls"]))

    def test_visible_task_obstacle_reuses_base_obstacle_info(self):
        response = {
            "ok": True,
            "observation": {
                "vehicle_id": "Car_C",
                "position": {"x": 0.0, "y": 0.0, "z": 0.0},
                "visible_objects": [
                    {
                        "object_id": "Obstacle_1",
                        "object_type": "static_task_obstacle",
                        "numeric_id": 1001,
                        "position": {"x": 12.0, "y": 4.0, "z": 0.0},
                        "orientation": {"x": 0.0, "y": 0.0, "z": 90.0},
                        "velocity": {"x": 0.0, "y": 0.0, "z": 0.0},
                        "length_m": 6.0,
                        "width_m": 2.5,
                        "height_m": 2.6,
                    }
                ],
            },
        }
        with patch.object(self.api, "_request", return_value=response):
            observation = self.api.get_observation("Car_C")

        self.assertEqual(1, len(observation.obstacles))
        self.assertIsInstance(observation.obstacles[0], metacar.ObstacleInfo)
        self.assertEqual(1001, observation.obstacles[0].id)
        self.assertEqual(ObstacleType.STATIC, observation.obstacles[0].type)
        self.assertEqual(90.0, observation.obstacles[0].ori_z)

    def test_hidden_action_is_rejected_before_network(self):
        with patch.object(self.api, "_request") as request:
            with self.assertRaisesRegex(ValueError, "不允许"):
                self.api.interact("Car_A", "Berth_A", "reset_demo")
        request.assert_not_called()

    def test_interaction_mapping_sends_raw_observation_token(self):
        with patch.object(
            self.api,
            "_request",
            return_value={"ok": True, "granted": True},
        ) as request:
            result = self.api.interact(
                "Car_C",
                "Obstacle_1",
                "report_observation",
                {"observation_token": "observation-token-123"},
            )

        self.assertTrue(result.granted)
        self.assertEqual(
            "observation-token-123",
            request.call_args.args[0]["payload"],
        )

    def test_server_failure_becomes_command_error(self):
        self.api.connect = lambda: self.api
        self.api._connection = _FakeConnection()
        self.api._response_stream = _FakeStream(
            '{"ok":false,"message":"denied"}\n'
        )
        with self.assertRaisesRegex(ScenarioCommandError, "denied"):
            self.api.get_vehicle_ids()

    def test_delivery_retry_results_use_existing_interaction_model(self):
        for vehicle_id, state, granted in (
            ("Car_A", "completed", True),
            ("Car_B", "completed_by_other", False),
        ):
            with self.subTest(vehicle_id=vehicle_id):
                self.api.connect = lambda: self.api
                self.api._connection = _FakeConnection()
                self.api._response_stream = _FakeStream(
                    '{"ok":true,"vehicle_id":"' + vehicle_id +
                    '","object_id":"Berth_A","object_state":"' + state +
                    '","granted":' + str(granted).lower() + ',"message":"recorded result"}\n'
                )
                result = self.api.interact(vehicle_id, "Berth_A", "deliver")
                self.assertEqual(vehicle_id, result.vehicle_id)
                self.assertEqual("Berth_A", result.object_id)
                self.assertEqual(state, result.object_state)
                self.assertEqual(granted, result.granted)
                self.assertEqual("recorded result", result.message)

    @staticmethod
    def _complete_vehicle_state_payload():
        return {
            "vehicle_id": "Car_C",
            "state": "Moving",
            "position": {"x": 10.0, "y": -2.0, "z": 0.5},
            "orientation": {"x": 0.0, "y": 0.0, "z": 90.0},
            "velocity": {"x": 3.0, "y": 0.0, "z": 0.0},
            "speed_mps": 3.0,
            "vehicle_control": {
                "throttle": 0.4,
                "brake": 0.0,
                "steering": -0.1,
                "gear": 1,
                "front_light": True,
                "left_blinker": True,
                "right_blinker": False,
                "double_flash": False,
            },
        }


class _FakeConnection:
    def sendall(self, payload):
        self.payload = payload

    def close(self):
        pass


class _FakeStream:
    def __init__(self, response):
        self.response = response

    def readline(self):
        return self.response

    def close(self):
        pass


if __name__ == "__main__":
    unittest.main()
