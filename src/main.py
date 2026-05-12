"""
AI Devotional Video Generator
Entry point for CLI and server modes.
"""

import argparse
import sys
from pathlib import Path
from loguru import logger


def setup_logging(level: str = "INFO") -> None:
    """Configure logging."""
    logger.remove()
    logger.add(sys.stderr, level=level)
    log_file = Path("logs/pipeline.log")
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logger.add(str(log_file), rotation="10 MB", level=level)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="AI Devotional Video Generator - 1-minute Hindi Bhakti Videos"
    )
    parser.add_argument("--deity", type=str, default="krishna",
                        choices=["krishna", "shiva", "ram"],
                        help="Deity for the devotional video")
    parser.add_argument("--topic", type=str, default=None,
                        help="Specific topic/subject for the script")
    parser.add_argument("--output", type=str, default=None,
                        help="Output video file path")
    parser.add_argument("--multi-image", action="store_true",
                        help="Use multiple transitioning images")
    parser.add_argument("--images", type=int, default=4,
                        help="Number of images (for --multi-image)")
    parser.add_argument("--server", action="store_true",
                        help="Run as FastAPI server")
    parser.add_argument("--port", type=int, default=8000,
                        help="Server port (default: 8000)")
    parser.add_argument("--config", type=str, default="config.yaml",
                        help="Path to config file")

    args = parser.parse_args()

    setup_logging()
    logger.info(f"Devotional Video Generator v1.0.0")
    logger.info(f"Deity: {args.deity}, Topic: {args.topic}")

    if args.server:
        run_server(args)
    else:
        run_pipeline(args)


def run_pipeline(args) -> None:
    """Run the video generation pipeline once."""
    from src.pipeline import DevotionalPipeline

    pipeline = DevotionalPipeline(args.config)

    if args.multi_image:
        logger.info("Running multi-image pipeline...")
        output = pipeline.generate(
            deity=args.deity,
            topic=args.topic,
            output_path=args.output,
        )
    else:
        logger.info("Running standard pipeline...")
        output = pipeline.generate(
            deity=args.deity,
            topic=args.topic,
            output_path=args.output,
        )

    print(f"\n✅ Video generated: {output}")


def run_server(args) -> None:
    """Run the FastAPI server for on-demand video generation."""
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    import uvicorn

    app = FastAPI(title="Devotional Video Generator API")

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "version": "1.0.0"}

    @app.post("/generate")
    async def generate_endpoint(deity: str = "krishna", topic: str = None) -> dict:
        """Generate a devotional video on demand."""
        from src.pipeline import DevotionalPipeline
        pipeline = DevotionalPipeline(args.config)
        output_path = pipeline.generate(deity=deity, topic=topic)
        return {"status": "success", "video_path": output_path}

    logger.info(f"Starting server on port {args.port}")
    uvicorn.run(app, host="0.0.0.0", port=args.port)


if __name__ == "__main__":
    main()