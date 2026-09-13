接口参考
========

多车任务接口
------------

.. autoclass:: metacar_multiagent.ScenarioTaskAPI
   :members:
   :undoc-members:

路口交互说明
^^^^^^^^^^^^

任务进行中，同一车辆重复申请或释放不会重复完成通行；重复释放仅确认本车已有结果，路口当前是否空闲应以最新任务状态中的占用车辆为准。

泊位交付说明
^^^^^^^^^^^^

同一车辆重复提交已完成的泊位（包括任务结束后），仅确认已有交付结果；其他车辆不能再次交付该泊位。

数据模型
--------

.. autopydantic_model:: metacar_multiagent.MultiVehicleSceneStaticData

.. autopydantic_model:: metacar_multiagent.ScenarioVehicleInfo

.. autopydantic_model:: metacar_multiagent.StaticObjectInfo

.. autopydantic_model:: metacar_multiagent.ScenarioVehicleState

车辆状态说明
^^^^^^^^^^^^

``get_vehicle_states()`` 一次读取全部任务车辆状态，可作为一轮多车决策输入；需要新状态时再次调用。

``ScenarioVehicleState.state`` 常见值包括：``Assigned`` 已分配、``Moving`` 移动中、``Waiting`` 等待中、``Parked`` 已驻车、``SafetyStopped`` 超时安全停车、``Completed`` 已完成、``Failed`` 已失败。

``ScenarioVehicleState.speed_mps`` 是车辆当前纵向速度，前进为正、倒车为负，单位为米每秒。``ScenarioVehicleState.control`` 是车辆当前实际生效的控制值。

.. autopydantic_model:: metacar_multiagent.ScenarioTaskDefinition

任务目标

.. autopydantic_model:: metacar_multiagent.ScenarioTaskObjective

共享任务对象

.. autopydantic_model:: metacar_multiagent.ScenarioSharedTaskObject

位置不确定区域

.. autopydantic_model:: metacar_multiagent.ScenarioUncertaintyRegion

.. autopydantic_model:: metacar_multiagent.ScenarioTaskState

.. autopydantic_model:: metacar_multiagent.ScenarioObservation

当前车辆观测对象

.. autopydantic_model:: metacar_multiagent.ScenarioObservedTaskObject

.. autopydantic_model:: metacar_multiagent.ScenarioInteractionResult

.. autopydantic_model:: metacar_multiagent.ScenarioEvent

异常
----

.. autoclass:: metacar_multiagent.ScenarioAPIError

.. autoclass:: metacar_multiagent.ScenarioConnectionError

.. autoclass:: metacar_multiagent.ScenarioProtocolError

.. autoclass:: metacar_multiagent.ScenarioCommandError
