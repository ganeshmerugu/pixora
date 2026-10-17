"""Run Pixora against ParseBench benchmark.

Usage:
  python run_parsebench.py                    # Full benchmark (requires HuggingFace datasets)
  python run_parsebench.py --test             # Quick test with 5 docs per category
  python run_parsebench.py --category table   # Single category
  python run_parsebench.py --local ./data     # Use local JSONL files
"""
import argparse
import asyncio
import json
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


async def main():
    parser = argparse.ArgumentParser(description="Run Pixora against ParseBench")
    parser.add_argument("--test", action="store_true", help="Quick test mode (5 docs per category)")
    parser.add_argument("--category", type=str, default="", help="Single category to evaluate")
    parser.add_argument("--local", type=str, default="", help="Path to local JSONL files")
    parser.add_argument("--max-docs", type=int, default=0, help="Max documents per category")
    parser.add_argument("--output", type=str, default="parsebench_results.json", help="Output JSON file")
    parser.add_argument("--pipeline", type=str, default="pixora_tesseract", help="Pipeline name")
    args = parser.parse_args()

    from pixora.evals.parsebench.loader import ParseBenchDataset
    from pixora.evals.parsebench.runner import PixoraParseBenchRunner, format_report

    dataset = ParseBenchDataset()
    categories = [args.category] if args.category else None
    max_per_cat = args.max_docs or (5 if args.test else 0)

    if args.local:
        logger.info("Loading from local directory: %s", args.local)
        dataset.load_from_jsonl(args.local, categories=categories)
    else:
        logger.info("Loading from HuggingFace (llamaindex/ParseBench)...")
        try:
            dataset.load(categories=categories, max_per_category=max_per_cat * 50 if max_per_cat else 0)
        except ImportError:
            logger.error(
                "Install the datasets package: pip install datasets\n"
                "Or download manually and use --local flag"
            )
            sys.exit(1)

    stats = dataset.get_stats()
    logger.info("Dataset loaded: %s", json.dumps(stats, indent=2, default=str))

    runner = PixoraParseBenchRunner(pipeline_name=args.pipeline)
    report = await runner.run(
        dataset,
        categories=categories,
        max_docs_per_category=max_per_cat,
    )

    print("\n" + format_report(report))

    with open(args.output, "w") as f:
        json.dump(dict(report), f, indent=2, default=str)
    logger.info("Results saved to %s", args.output)


if __name__ == "__main__":
    asyncio.run(main())
