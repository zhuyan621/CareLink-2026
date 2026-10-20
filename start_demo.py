"""Check the local contest demo and launch its single-origin website."""

from __future__ import annotations

import argparse
import csv
import importlib.util
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parent
REQUIRED_MODULES = ("fastapi", "uvicorn", "numpy", "pandas", "sklearn", "scipy", "joblib", "requests", "yaml")


def check_environment() -> bool:
    missing = [name for name in REQUIRED_MODULES if importlib.util.find_spec(name) is None]
    dataset = ROOT / "medNo.22.csv"
    rows = 0
    if dataset.is_file():
        with dataset.open(encoding="utf-8-sig", newline="") as handle:
            rows = sum(1 for _ in csv.DictReader(handle))
    print(f"医学问答数据: {rows} / 605 行（问答，不是病例）")
    print(f"Python 依赖: {'齐全' if not missing else '缺少 ' + ', '.join(missing)}")
    medquad_ready = False
    if not missing:
        from medquad_qa import status
        medquad = status()
        medquad_ready = medquad["ready"] and medquad.get("indexed_pairs") == 16407
        print(f"MedQuAD 完整训练包: {'可用' if medquad_ready else '缺失或哈希核验失败'}"
              "（16,407 条有答案问答）")
    try:
        with urlopen("http://127.0.0.1:11434/api/tags", timeout=2) as response:
            ollama_online = response.status == 200
    except (OSError, URLError):
        ollama_online = False
    print(f"Ollama 服务: {'可访问' if ollama_online else '未连接；网站仍可启动，筛查会显示真实回退状态'}")
    if rows != 605:
        print("错误：medNo.22.csv 的行数与本版核验值不符。")
    return not missing and rows == 605 and medquad_ready


def main() -> int:
    parser = argparse.ArgumentParser(description="CareLink 2026 本机演示启动器")
    parser.add_argument("--check", action="store_true", help="只检查依赖、数据和 Ollama 状态")
    parser.add_argument("--port", type=int, default=8511)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("端口必须在 1–65535 之间")
    if not check_environment():
        return 2
    if args.check:
        return 0
    import uvicorn

    print(f"打开 http://127.0.0.1:{args.port}/ （Ctrl+C 停止）")
    uvicorn.run("careguard_site:app", host="127.0.0.1", port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
