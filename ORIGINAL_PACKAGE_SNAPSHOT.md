# 最初 MAPFM 工程源码快照说明

为避免把“已合并运行核心”误认为“原工程包已随总包交付”，本版在 `original_engine_package/` 中单独保留最初 `MAPFM_medical_AI_repaired_complete` 的源码快照。它与 CareGuard 运行目录并排存在，而不是用旧文件覆盖新的网页/API。

2026-10-11 从桌面原工程目录复制了 **225 个文件、63,537,964 字节**，包括原始 `api.py`、MAPFM 主程序、预处理器、配置、`medNo.22.csv`、原始 `README.md`、`docs/`、`dashboard/`、`tests/`、`med-ts-llm_source/`、历史备份及已有 `artifacts/`。逐文件重新计算 SHA-256，与桌面源目录对应文件对比：**225/225 一致，0 个差异**。总 ZIP 内的 `PACKAGE_MANIFEST.json` 还列出每个快照文件的大小和 SHA-256。

未复制 `.venv/`（约 1.55 GB、47,616 个本机依赖文件）、`.git/`、`.idea/`、`__pycache__/`、`.pytest_cache/` 和 `logs/`。这些是机器环境、版本库元数据或运行痕迹，不是原创工程源码；请在目标机器按照 `requirements.txt` 重建环境。原始文件未删除或修改。

网站实际运行的是总包根目录的 `api.py`、`mapfm_ecosystem_repaired.py`、`mapfm_utils/` 与数据文件。原工程快照仅用于并排核查，避免 Python 导入旧备份文件。工程连接方式与本机 Ollama 计算证据见 `ENGINE_SOURCE_MERGE.md` 和 `artifacts/competition/careguard_engineering_smoke_latest.json`。这些软件检查不构成临床验证。

总包根目录的 `pytest.ini` 只收集当前 `tests/`，避免快照内同名旧测试与新版测试发生 Python 模块名冲突；原工程的测试文件保持原样，可以在其目录内按旧工程要求单独运行。
