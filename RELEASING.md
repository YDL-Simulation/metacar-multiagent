# 发布维护指南

发行包名为 `metacar-multiagent`，Python 导入名为 `metacar_multiagent`。基础依赖固定为 `metacar==0.4.0`。

## 自动检查

提交与 Pull Request 会触发 Python 3.10–3.13 兼容检查，以及发行物和文档验证。
本地可运行：

```console
python -m pip install -e ".[dev]"
python scripts/check_public_release.py
python scripts/prepare_release_candidate.py --output Artifacts/release-candidate
```

输出目录必须全新。验收脚本构建 wheel 和源码包，在独立环境中安装，检查依赖、公共类型、单元测试和文档。
公开内容检查只能识别预定义问题，不能替代代码审查。

## 发布步骤

1. 更新版本、变更记录和发布日期，确认代码及发行物检查通过。
2. 将发布分支推送到本仓库，等待自动检查完成。仅推送目标分支和版本标签，不批量推送其他本地分支或标签。
3. 创建与包版本一致的标签，例如 `v0.1.0`，并在该提交上创建 GitHub Release。
4. 发布 Release 将触发 `python-publish.yml`：验证标签、构建并检查发行物，再上传 PyPI。
5. 发布后从 PyPI 安装，核对版本、依赖和导入位置。已发布的版本不可覆盖，后续修复使用新版本号。

PyPI 使用 Trusted Publishing；owner、repository、工作流文件名和 `pypi` Environment 必须与平台配置一致。
在线文档通过 Read the Docs 连接本仓库，使用 `.readthedocs.yaml` 构建。

## 示例分发

`examples/minimal_control.py` 通过源码仓库及源码发行包提供；wheel 只安装 SDK。
仅更新示例时无需自动发布新的 PyPI 版本。
