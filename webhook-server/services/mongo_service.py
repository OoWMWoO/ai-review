"""MongoDB service for storing and retrieving review data."""

import logging
from datetime import datetime
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure

logger = logging.getLogger(__name__)


class MongoService:
    """Service for MongoDB operations."""

    def __init__(self, uri: str, database: str):
        self.uri = uri
        self.database_name = database
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None

    async def connect(self) -> None:
        """Connect to MongoDB."""
        try:
            self.client = AsyncIOMotorClient(self.uri)
            # Verify connection
            await self.client.admin.command("ping")
            self.db = self.client[self.database_name]
            logger.info(f"Connected to MongoDB: {self.database_name}")
        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from MongoDB."""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")

    async def save_review(self, review_data: dict) -> str:
        """
        Save a review result to MongoDB.
        Returns the inserted document ID.
        """
        collection = self.db["reviews"]
        review_data["created_at"] = datetime.utcnow()
        result = await collection.insert_one(review_data)
        logger.info(f"Saved review with ID: {result.inserted_id}")
        return str(result.inserted_id)

    async def get_review(self, review_id: str) -> Optional[dict]:
        """Get a review by ID."""
        from bson import ObjectId

        collection = self.db["reviews"]
        review = await collection.find_one({"_id": ObjectId(review_id)})
        if review:
            review["_id"] = str(review["_id"])
        return review

    async def get_reviews_by_pr(
        self, repo_owner: str, repo_name: str, pr_number: int
    ) -> list[dict]:
        """Get all reviews for a specific PR."""
        collection = self.db["reviews"]
        cursor = collection.find({
            "pr_info.repo_owner": repo_owner,
            "pr_info.repo_name": repo_name,
            "pr_info.pr_number": pr_number,
        }).sort("created_at", -1)

        reviews = []
        async for review in cursor:
            review["_id"] = str(review["_id"])
            reviews.append(review)
        return reviews

    async def update_review_status(
        self, review_id: str, status: str, error: Optional[str] = None
    ) -> None:
        """Update the status of a review."""
        from bson import ObjectId

        collection = self.db["reviews"]
        update_data = {
            "status": status,
            "updated_at": datetime.utcnow(),
        }
        if error:
            update_data["error"] = error

        await collection.update_one(
            {"_id": ObjectId(review_id)},
            {"$set": update_data}
        )
        logger.info(f"Updated review {review_id} status to: {status}")