import inspect
import unittest

import metacar_multiagent as api


class DocumentContractTests(unittest.TestCase):
    def test_scenario_task_api_has_exact_documented_methods(self):
        expected = {
            "connect",
            "close",
            "get_scene_static_data",
            "get_task",
            "get_task_state",
            "get_vehicle_ids",
            "get_vehicle_state",
            "get_vehicle_states",
            "set_vehicle_control",
            "set_vehicle_controls",
            "stop_vehicles",
            "get_observation",
            "interact",
            "get_events",
        }
        public = {
            name
            for name, value in inspect.getmembers(
                api.ScenarioTaskAPI, inspect.isfunction
            )
            if not name.startswith("_")
        }
        self.assertEqual(expected, public)

    def test_multi_vehicle_scene_static_data_fields(self):
        self.assertEqual(
            {"coordinate_system", "roads", "vehicles", "static_objects"},
            set(api.MultiVehicleSceneStaticData.model_fields),
        )
        self.assertFalse(hasattr(api, "SceneStaticData"))

    def test_task_definition_fields(self):
        self.assertEqual(
            {
                "scenario_id",
                "scenario_name",
                "api_version",
                "problem_type",
                "instance_seed",
                "coordinate_system",
                "control_mode",
                "observation_model",
                "vehicles",
                "objectives",
                "shared_task_objects",
                "allowed_actions",
            },
            set(api.ScenarioTaskDefinition.model_fields),
        )

    def test_vehicle_and_static_object_fields(self):
        self.assertEqual(
            {
                "vehicle_id",
                "display_name",
                "role",
                "length_m",
                "width_m",
                "height_m",
                "maximum_speed_mps",
            },
            set(api.ScenarioVehicleInfo.model_fields),
        )
        self.assertEqual(
            {
                "id",
                "category",
                "display_name",
                "position",
                "orientation_degrees",
                "length_m",
                "width_m",
                "height_m",
            },
            set(api.StaticObjectInfo.model_fields),
        )

    def test_shared_task_object_fields(self):
        self.assertEqual(
            {
                "object_id",
                "object_type",
                "display_name",
                "state",
                "information_level",
                "information_level_index",
                "uncertainty_region",
                "valid_observation_count",
                "required_observation_count",
                "position",
                "orientation",
                "orientation_unit",
                "length_m",
                "width_m",
                "height_m",
                "road_ids",
                "lane_ids",
            },
            set(api.ScenarioSharedTaskObject.model_fields),
        )
        self.assertFalse(hasattr(api, "ScenarioDynamicRoadState"))

    def test_task_state_fields(self):
        self.assertEqual(
            {
                "phase",
                "instance_seed",
                "shared_task_objects",
                "verified_signal_count",
                "total_signal_count",
                "unlocked_destination_count",
                "total_destination_count",
                "roadblock_active",
                "intersection_owner",
            },
            set(api.ScenarioTaskState.model_fields),
        )


if __name__ == "__main__":
    unittest.main()
