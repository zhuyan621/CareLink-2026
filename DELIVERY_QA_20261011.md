# 安护智链 CareGuard｜2026-10-11 交付验收记录

## 自动化与本机执行

- `python -m pytest -q --junitxml=artifacts/competition/careguard_pytest_latest.xml`：**128 passed，0 failed，0 error**；另有 3 条第三方 SWIG 类型弃用警告。
- `python start_demo.py --check`：核心依赖齐全，`medNo.22.csv` 为 **605/605 行**，Ollama 本机服务可访问。
- `python careguard_smoke.py --require-ollama`：合成胸痛场景为 P1，`ollama_local_http` 已验证且未回退；动态证据 0、离线参考 1，要求人工复核，不允许临床使用；审计摘要不含原始交接文本。自检快照见 `artifacts/competition/careguard_live_smoke_latest.json`。
- `node --check careguard_web/site.js` 与 `node --check careguard_web/handoff.js`：语法检查通过。
- 工程合并自检 `python careguard_engineering_smoke.py --require-ollama --base-url http://127.0.0.1:8511`：原始 MAPFM 核心、预处理器、配置和问答 CSV 的 SHA-256 与初始包一致；合成体征经原工程解析 1 条，运行中的 HTTP 服务实际调用本机 Ollama，`transport=live_loopback_http`、`ollama_generation_verified=true`、后端 `ollama_local_http`、P1、待人工复核。快照见 `artifacts/competition/careguard_engineering_smoke_latest.json`；单次输入不代表时序预测或临床有效。
- 已核对旧 8511 监听者确为当日启动的 CareGuard Python 服务，随后仅停止其已验证的 PID，并以合并后的版本重新在 `http://127.0.0.1:8511/` 启动。新版首页返回 200、`/engineering/status` 返回 `core_source_match=true`，再对 8511 发起合成案例 HTTP 实际计算成功。用于回退的 8512 临时服务随后关闭。
- 针对原工程包未被物理收录的问题，已在 `original_engine_package/` 添加独立原工程源码快照：225 个文件、63,537,964 字节；与桌面最初工程逐文件 SHA-256 比对 **225/225 一致**。`.venv`、Git/IDE/Python 缓存与日志目录未复制，排除范围见 `ORIGINAL_PACKAGE_SNAPSHOT.md`。首次完整测试暴露旧包同名测试被重复收集，已用根目录 `pytest.ini` 隔离。
- 新同事启动说明分为可双击阅读的 `打开网页_新同事先看这个.txt` 和详细的 `START_HERE_新同事打开网页.md`；命令、模型名、默认端口与运行文件逐项核对，`python start_demo.py --check` 通过。首次在全新 Windows 电脑安装依赖仍需该电脑实际操作验证。

## 浏览器实测

本机 `http://127.0.0.1:8511/` 的首页、工作台、证据与边界、三维研究图谱、加入我们页面均已检查，控制台未见错误；对应截图见 `artifacts/site-qa/`。在实际工作台使用合成案例完成了筛查、P1 人工复核、交接摘要生成和 TXT 下载。修改输入后旧结果与摘要自动失效。390px 移动视口检查未发现横向溢出；结束后已恢复默认视口。

复看截图时发现证据页桌面视口曾有约 8px 横向滚动；现已将证据内容装饰层裁切在版心内。修复后再次实测：1280px 桌面视口及 390px 手机视口均为 `scrollWidth == clientWidth`，并已更新证据页截图。

本次工程桥面板的新增视觉验收尚未完成：浏览器工具对预览的访问被已保存的用户权限设置拒绝，故没有生成或伪造这部分截图。服务器、接口、自动化测试和实际模型计算分别完成核验；视觉与真实点击流程仍需在权限允许后补测。

## 尚未完成或不应宣称的事项

- 合作表单的邮件通道未配置，页面明确禁用发送；没有做真实邮件投递测试。
- 历史获奖作品的原始参赛包和个人贡献证据尚须团队核对；本记录不作资格认定。
- 没有外部临床验证、真实机构部署或临床性能结论。合成案例软件测试不可等同临床验证。
- 本次网页截图只证明指定时间、本机、当前视口下的可见状态；不证明持续在线。
