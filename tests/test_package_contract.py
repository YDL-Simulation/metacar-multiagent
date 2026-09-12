import unittest
from unittest.mock import Mock

import metacar
import metacar_multiagent as multiagent


class PackageContractTests(unittest.TestCase):
    def test_shared_types_are_reexported_without_redefinition(self):
        names = (
            "VehicleControl",
            "GearMode",
            "PoseGnss",
            "RoadInfo",
            "LaneInfo",
            "BorderInfo",
            "LineType",
            "DrivingType",
            "TrafficSignType",
            "ObstacleInfo",
            "ObstacleType",
            "Vector2",
            "Vector3",
        )
        for name in names:
            with self.subTest(name=name):
                self.assertIn(name, multiagent.__all__)
                self.assertIs(getattr(multiagent, name), getattr(metacar, name))

    def test_reexported_enums_keep_metacar_values(self):
        expected_members = {
            "GearMode": {
                "NEUTRAL": 0,
                "DRIVE": 1,
                "REVERSE": 2,
                "PARKING": 3,
            },
            "LineType": {
                "MIDDLE_LINE": 1,
                "SIDE_LINE": 2,
                "SOLID_LINE": 3,
                "STOP_LINE": 4,
                "ZEBRA_CROSSING": 5,
                "DASH_LINE": 6,
            },
            "DrivingType": {
                "MOTOR_VEHICLE_ALLOWED": 1,
                "NON_MOTOR_VEHICLE_ALLOWED": 2,
                "PEDESTRIAN_ALLOWED": 3,
            },
            "TrafficSignType": {
                "NO_SIGN": 0,
                "SPEED_LIMIT_SIGN": 1,
                "STOP_SIGN": 2,
                "V2X_SIGN": 3,
            },
            "ObstacleType": {
                name: member.value
                for name, member in metacar.ObstacleType.__members__.items()
            },
        }
        for type_name, members in expected_members.items():
            with self.subTest(type_name=type_name):
                enum_type = getattr(multiagent, type_name)
                self.assertEqual(
                    members,
                    {
                        name: member.value
                        for name, member in enum_type.__members__.items()
                    },
                )

    def test_reexported_model_construction_and_access_follow_metacar(self):
        expected_model_fields = {
            "VehicleControl": {
                "throttle",
                "brake",
                "steering",
                "gear",
                "left_blinker_on",
                "right_blinker_on",
                "hazard_lights_on",
                "headlights_on",
            },
            "PoseGnss": {
                "pos_x",
                "pos_y",
                "pos_z",
                "vel_x",
                "vel_y",
                "vel_z",
                "ori_x",
                "ori_y",
                "ori_z",
            },
            "RoadInfo": {
                "id",
                "begin_pos",
                "end_pos",
                "driving_type",
                "traffic_sign_type",
                "stop_line",
                "predecessor_ids",
                "successor_ids",
                "lanes",
            },
            "LaneInfo": {
                "id",
                "left_border",
                "right_border",
                "left_lane_id",
                "right_lane_id",
                "width",
                "path_points",
            },
            "BorderInfo": {"type", "path_points"},
            "ObstacleInfo": {
                "id",
                "type",
                "pos_x",
                "pos_y",
                "pos_z",
                "vel_x",
                "vel_y",
                "vel_z",
                "ori_x",
                "ori_y",
                "ori_z",
                "length",
                "width",
                "height",
                "extra_info",
            },
        }
        for type_name, fields in expected_model_fields.items():
            with self.subTest(type_name=type_name):
                self.assertEqual(
                    fields,
                    set(getattr(multiagent, type_name).model_fields),
                )

        default_control = multiagent.VehicleControl()
        self.assertEqual(0.0, default_control.throttle)
        self.assertEqual(0.0, default_control.brake)
        self.assertEqual(0.0, default_control.steering)
        self.assertEqual(metacar.GearMode.DRIVE, default_control.gear)
        self.assertFalse(default_control.left_blinker_on)
        self.assertFalse(default_control.right_blinker_on)
        self.assertFalse(default_control.hazard_lights_on)
        self.assertFalse(default_control.headlights_on)

        pose = multiagent.PoseGnss(
            posX=1.0,
            posY=2.0,
            posZ=3.0,
            velX=-4.0,
            velY=5.0,
            velZ=6.0,
            oriX=7.0,
            oriY=8.0,
            oriZ=9.0,
        )
        self.assertEqual((1.0, 2.0, 3.0), (pose.pos_x, pose.pos_y, pose.pos_z))
        self.assertEqual((-4.0, 5.0, 6.0), (pose.vel_x, pose.vel_y, pose.vel_z))
        self.assertEqual((7.0, 8.0, 9.0), (pose.ori_x, pose.ori_y, pose.ori_z))
        self.assertEqual(
            {
                "posX",
                "posY",
                "posZ",
                "velX",
                "velY",
                "velZ",
                "oriX",
                "oriY",
                "oriZ",
            },
            set(pose.model_dump(by_alias=True)),
        )

        left_border = multiagent.BorderInfo(
            borderType=multiagent.LineType.SOLID_LINE,
            pathPoint=[multiagent.Vector2(0.0, 0.0)],
        )
        right_border = multiagent.BorderInfo(
            borderType=multiagent.LineType.DASH_LINE,
            pathPoint=[multiagent.Vector2(0.0, 3.5)],
        )
        lane = multiagent.LaneInfo(
            id="Lane_1",
            LeftBorder=left_border,
            RightBorder=right_border,
            leftLane="",
            rightLane="",
            width=3.5,
            pathPoint=[multiagent.Vector2(0.0, 1.75)],
        )
        road = multiagent.RoadInfo(
            id="Road_1",
            beginPos=multiagent.Vector3(0.0, 0.0, 0.0),
            endPos=multiagent.Vector3(10.0, 0.0, 0.0),
            drivingType=multiagent.DrivingType.MOTOR_VEHICLE_ALLOWED,
            trafficSign=multiagent.TrafficSignType.NO_SIGN,
            stopLine=[],
            predecessor=[],
            successor=[],
            laneData=[lane],
        )
        self.assertEqual(metacar.LineType.SOLID_LINE, lane.left_border.type)
        self.assertEqual("Lane_1", road.lanes[0].id)
        self.assertEqual(
            metacar.DrivingType.MOTOR_VEHICLE_ALLOWED,
            road.driving_type,
        )
        self.assertEqual(metacar.TrafficSignType.NO_SIGN, road.traffic_sign_type)
        serialized_road = road.model_dump(by_alias=True)
        self.assertEqual(
            {
                "id",
                "beginPos",
                "endPos",
                "drivingType",
                "trafficSign",
                "stopLine",
                "predecessor",
                "successor",
                "laneData",
            },
            set(serialized_road),
        )
        self.assertEqual(
            {
                "id",
                "LeftBorder",
                "RightBorder",
                "leftLane",
                "rightLane",
                "width",
                "pathPoint",
            },
            set(serialized_road["laneData"][0]),
        )
        self.assertEqual(
            {"borderType", "pathPoint"},
            set(serialized_road["laneData"][0]["LeftBorder"]),
        )

        obstacle = multiagent.ObstacleInfo(
            id=1001,
            type=multiagent.ObstacleType.STATIC,
            posX=1.0,
            posY=2.0,
            posZ=3.0,
            velX=0.0,
            velY=0.0,
            velZ=0.0,
            oriX=0.0,
            oriY=0.0,
            oriZ=90.0,
            length=6.0,
            width=2.5,
            height=2.6,
            RedundantValue=None,
        )
        self.assertEqual(1.0, obstacle.pos_x)
        self.assertEqual(90.0, obstacle.ori_z)
        self.assertIsNone(obstacle.extra_info)
        self.assertIn("RedundantValue", obstacle.model_dump(by_alias=True))

    def test_reexported_vectors_keep_constructor_and_attributes(self):
        vector2 = multiagent.Vector2(1.0, -2.0)
        vector3 = multiagent.Vector3(3.0, -4.0, 5.0)
        self.assertEqual((1.0, -2.0), (vector2.x, vector2.y))
        self.assertEqual((3.0, -4.0, 5.0), (vector3.x, vector3.y, vector3.z))

    def test_extension_does_not_replace_old_scene_api(self):
        self.assertTrue(hasattr(metacar, "SceneAPI"))
        self.assertFalse(hasattr(multiagent, "SceneAPI"))

    def test_extension_static_model_has_distinct_multi_vehicle_name(self):
        self.assertTrue(hasattr(metacar, "SceneStaticData"))
        self.assertFalse(hasattr(multiagent, "SceneStaticData"))
        self.assertTrue(hasattr(multiagent, "MultiVehicleSceneStaticData"))
        self.assertIsNot(
            multiagent.MultiVehicleSceneStaticData,
            metacar.SceneStaticData,
        )
        self.assertEqual(
            {"coordinate_system", "roads", "vehicles", "static_objects"},
            set(multiagent.MultiVehicleSceneStaticData.model_fields),
        )
        self.assertEqual(
            list[metacar.RoadInfo],
            multiagent.MultiVehicleSceneStaticData.model_fields[
                "roads"
            ].annotation,
        )

    def test_original_scene_static_data_keeps_metacar_contract(self):
        original = metacar.SceneStaticData(
            route=[metacar.Vector3(1.0, 2.0, 3.0)],
            roads=[],
            sub_scenes=[],
            vla_extension=None,
        )
        self.assertEqual(
            {"route", "roads", "sub_scenes", "vla_extension"},
            set(metacar.SceneStaticData.model_fields),
        )
        self.assertEqual(
            (1.0, 2.0, 3.0),
            (original.route[0].x, original.route[0].y, original.route[0].z),
        )

    def test_vehicle_control_finite_value_behavior_matches_old_scene_api(self):
        cases = (
            ("default", metacar.VehicleControl()),
            (
                "normal",
                metacar.VehicleControl(
                    throttle=0.25,
                    brake=0.1,
                    steering=0.4,
                ),
            ),
            (
                "boundary",
                metacar.VehicleControl(
                    throttle=1.0,
                    brake=1.0,
                    steering=-1.0,
                ),
            ),
            (
                "ordinary_outside_range",
                metacar.VehicleControl(
                    throttle=1.1,
                    brake=-0.2,
                    steering=1.4,
                ),
            ),
        )

        for label, control in cases:
            with self.subTest(label=label):
                old_api = metacar.SceneAPI.__new__(metacar.SceneAPI)
                old_api._move_to_start = 0
                old_api._move_to_end = 0
                old_api._model_socket = Mock()
                old_api.set_vehicle_control(control)
                old_api._model_socket.send.assert_called_once()

                new_api = multiagent.ScenarioTaskAPI()
                new_api._request = Mock(return_value={"ok": True})
                try:
                    new_api.set_vehicle_control("Car_A", control)
                    command = new_api._request.call_args.args[0]
                finally:
                    new_api.close()

                wire_control = command["vehicle_control"]
                self.assertEqual(control.throttle, wire_control["throttle"])
                self.assertEqual(control.brake, wire_control["brake"])
                self.assertEqual(control.steering, wire_control["steering"])
                self.assertEqual(control.gear.value, wire_control["gear"])

    def test_rules_model_and_non_student_methods_are_absent(self):
        self.assertFalse(hasattr(multiagent, "ScenarioTaskRules"))
        for name in (
            "get_score",
            "get_run_report",
            "get_planning_problem",
            "reset_demo",
            "set_demo_phase",
            "capture_demo_frame",
        ):
            with self.subTest(name=name):
                self.assertFalse(hasattr(multiagent.ScenarioTaskAPI, name))

    def test_public_version_and_contract(self):
        self.assertEqual("0.1.0", multiagent.__version__)
        self.assertEqual("R-A1B-API-01", multiagent.SDK_CONTRACT)


if __name__ == "__main__":
    unittest.main()
