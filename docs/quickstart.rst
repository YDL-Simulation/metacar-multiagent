安装与最小示例
==============

公开发行完成后，在 Python 3.10 或更高版本的虚拟环境中执行：

.. code-block:: console

   python -m pip install metacar-multiagent==0.1.0
   python -m pip check

公开发行前使用资料包中的两个 wheel，安装方式见首页。本扩展固定依赖
``metacar==0.4.0``，不修改原包；安装可能需要联网下载其他依赖。

从源码仓库、源码发行包或学生资料包获取 ``examples/minimal_control.py``。
示例不随 wheel 安装到当前目录。通过客户端启动场景，等待加载完成后执行：

.. code-block:: console

   python examples/minimal_control.py

港口开发站试用使用开发版客户端。示例读取公开信息并停车，仅检查连接，不执行完整运输。
任务与评分以配套正式文档为准。连接失败时先检查场景是否启动；反馈时提供 Python、SDK、
场景版本及原始报错，不提供令牌或密码。
