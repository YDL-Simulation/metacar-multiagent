"""读取多车状态并发送安全停车命令的最小示例。"""

from metacar_multiagent import GearMode, ScenarioTaskAPI, VehicleControl


def main() -> None:
    with ScenarioTaskAPI() as api:
        scene = api.get_scene_static_data()
        task = api.get_task()
        vehicle_ids = api.get_vehicle_ids()
        print(
            f"{task.scenario_id}: roads={len(scene.roads)}, "
            f"vehicles={vehicle_ids}, fixed={len(scene.static_objects)}"
        )

        try:
            controls = {
                vehicle_id: VehicleControl(
                    brake=1.0,
                    gear=GearMode.PARKING,
                )
                for vehicle_id in vehicle_ids
            }
            api.set_vehicle_controls(controls)
        finally:
            api.stop_vehicles(vehicle_ids)


if __name__ == "__main__":
    main()
