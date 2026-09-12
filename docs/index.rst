metacar-multiagent Python API
==============================

``metacar-multiagent`` 是 ``metacar 0.4.0`` 的多车协同扩展包，不修改或覆盖
原 ``metacar``。旧场景继续使用 ``metacar.SceneAPI``，多车任务场景使用
``metacar_multiagent.ScenarioTaskAPI``。

安装
----

在正式学生资料包的两个 wheel 所在目录执行：

.. code-block:: console

   python -m pip install ./metacar-0.4.0-py3-none-any.whl ./metacar_multiagent-0.1.0-py3-none-any.whl

扩展包固定依赖 ``metacar==0.4.0``。安装时还需准备基础包所需的其他依赖，
不能仅凭这两个文件认定可以完全离线安装。
请使用发布清单指定的验收产物，不使用工程中遗留的旧构建。

.. toctree::
   :maxdepth: 2

   quickstart
   api
