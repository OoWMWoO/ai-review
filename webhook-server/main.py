"""Main entry point for the AI Review webhook server."""

import logging
import sys
from pathlib import Path

from sanic import Sanic
from sanic.log import logger

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(Path(__file__).parent.parent / ".env")

from config import get_settings
from routes import github_bp
from services.mongo_service import MongoService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Create Sanic app
app = Sanic("ai-review")

# Register blueprints
app.blueprint(github_bp)


@app.listener("before_server_start")
async def setup_services(app, loop):
    """Initialize services before server starts."""
    settings = get_settings()

    # Initialize MongoDB connection
    app.ctx.mongo = MongoService(
        uri=settings.mongodb_uri,
        database=settings.mongodb_database
    )
    await app.ctx.mongo.connect()
    logger.info("MongoDB connected")

    # Store settings in app context
    app.ctx.settings = settings
    logger.info(f"Server configured for {settings.server_host}:{settings.server_port}")


@app.listener("after_server_stop")
async def cleanup_services(app, loop):
    """Cleanup services after server stops."""
    if hasattr(app.ctx, "mongo"):
        await app.ctx.mongo.disconnect()
        logger.info("MongoDB disconnected")


@app.route("/")
async def index(request):
    """Root endpoint."""
    return {"status": "ok", "service": "ai-review"}


if __name__ == "__main__":
    settings = get_settings()
    app.run(
        host=settings.server_host,
        port=settings.server_port,
        auto_reload=True,
        debug=True,
    )