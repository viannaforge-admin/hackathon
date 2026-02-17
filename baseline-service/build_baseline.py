from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path

from app.baseline_builder import BaselineBuilder, BuildStatus
from app.graph_client import GraphClient
from app.keyword_miner import KeywordMinerClient, KeywordMinerConfig


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build baseline.json from Graph mock history")
    parser.add_argument("--days", type=int, default=35, help="Historical window in days")
    parser.add_argument(
        "--base-url",
        type=str,
        default=os.getenv("GRAPH_BASE_URL", "http://127.0.0.1:8000"),
        help="Graph mock base URL",
    )
    return parser.parse_args()


async def _main() -> None:
    args = parse_args()
    status = BuildStatus()
    output_path = Path(__file__).resolve().parent / "baseline.json"
    keyword_stats_path = Path(__file__).resolve().parent / "keyword_stats.json"
    keyword_miner = KeywordMinerClient(
        KeywordMinerConfig(
            enabled=os.getenv("USE_LLM_KEYWORD_MINER", "false").lower() == "true",
            service_url=os.getenv("KEYWORD_MINER_URL", "http://127.0.0.1:8030"),
            timeout_seconds=float(os.getenv("KEYWORD_MINER_TIMEOUT_SECONDS", "3.0")),
            max_retries=int(os.getenv("KEYWORD_MINER_MAX_RETRIES", "3")),
        )
    )
    builder = BaselineBuilder(
        GraphClient(base_url=args.base_url),
        output_path,
        status,
        keyword_miner=keyword_miner,
        keyword_stats_path=keyword_stats_path,
        keyword_batch_size=int(os.getenv("KEYWORD_MINER_BATCH_SIZE", "200")),
    )
    await builder.build(days=args.days)
    print(f"Wrote baseline to {output_path}")


if __name__ == "__main__":
    asyncio.run(_main())
