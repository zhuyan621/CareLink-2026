# MAPFM 原代码包与 CareGuard 网页工程合并核查

对照源：`C:\Users\Lenovo\Desktop\MAPFM_medical_AI_repaired_complete`；目标：本目录 `CareGuard_2026`。总交付包另在 `original_engine_package/` 独立保留原始工程的 225 文件源码快照，具体收录与排除见 `ORIGINAL_PACKAGE_SNAPSHOT.md`。2026-10-11 逐文件 SHA-256 比对发现，以下运行核心在原包与当前运行目录中**字节完全相同**：

| 文件 | SHA-256 |
| --- | --- |
| `mapfm_ecosystem_repaired.py` | `99a51b18bdb7e1b806e73af0ef7b3252734106e6accfd83b89cdb0043effa529` |
| `mapfm_utils/multimodal_utils.py` | `36e6ab0bef79593d8cfa4f281731a313b17c5a78d3af3a3d06251712afdbea02` |
| `config.yaml` | `3263a85f2417ebe3c69112fde7637eacf96a7806564c4b66182ff5114e883874` |
| `medNo.22.csv` | `00474d427edd5e93ed96424923ad4e8b66d91bc451ee25e653c1a050bd36384e` |

这不是“网页旁边放一份原始代码”的形式合并：工作台现在请求 `POST /screening/engineering`。服务端将用户填写的一组演示体征交给**原始** `MultimodalPreprocessor` 解析，再把解析出的数值编入当前 MAPFM 引擎的实际文本输入，执行 `HeterogeneousMultiAgentEcosystem.run_collaborative_task`，最后由 CareGuard 的谨慎展示层输出优先级线索、真实后端状态与人工复核门控。网页的工程桥面板显示本次解析条数、源码指纹和推理后端；`GET /engineering/status` 提供机器可核查的源文件摘要。旧的 `/screening` 仍保留作兼容接口。

一组体征是**单次观察**，不会伪称有纵向趋势；未经验证的时序模型不参与本次路径。输入格式与模型输出可运行不等于临床有效或适合真实患者。只使用合成或充分脱敏的记录进行演示。

原始包单独存在的 `*_backup.py`、`config_backup.yaml` 和 `_live_result.json` 是备份/旧结果，不是当前运行入口，因此没有覆盖运行目录；它们已保存在独立的 `original_engine_package/` 快照内。桌面原始包保持原状。当前可复现的工程连通性检查：

```powershell
python careguard_engineering_smoke.py --require-ollama
python careguard_engineering_smoke.py --require-ollama --base-url http://127.0.0.1:8511
python -m pytest tests/test_engineering_bridge.py -q
```

现场界面还需由团队用各自的合成输入检查：不同输入会触发新的请求 ID 与实际计算；若 Ollama 不在线，页面应明确显示降级而不是沿用历史成功快照。
