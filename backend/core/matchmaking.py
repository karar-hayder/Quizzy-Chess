import asyncio
import json
import logging
import math
import time
from typing import Dict, List, Optional, Tuple

import redis.asyncio as aioredis
from channels.db import database_sync_to_async
from django.conf import settings

from core.models import Game
from core.utils import get_redis
from users.models import CustomUser

logger = logging.getLogger(__name__)


class MatchmakingService:
    """Elo-based matchmaking service with win/loss ratio consideration.

    Thread-safe: Uses Redis for state management and creates fresh connections per instance.
    Each consumer should create its own instance to avoid connection sharing issues.
    """

    def __init__(self):
        self._redis = None
        self.queue_key = "matchmaking_queue"
        self.active_searches_key = "active_searches"
        self.max_wait_time = 60  # seconds
        self.elo_tolerance = 200  # base Elo difference tolerance
        self.ratio_tolerance = 0.3  # win/loss ratio tolerance

    @property
    def redis(self):
        """Lazy Redis connection."""
        if self._redis is None:
            self._redis = get_redis()
        return self._redis

    async def add_player_to_queue(self, user_id: int, user_data: dict) -> bool:
        """Add a player to the matchmaking queue."""
        try:
            player_data = {
                "user_id": user_id,
                "elo": user_data.get("rating", 1200),
                "games_won": user_data.get("games_won", 0),
                "games_lost": user_data.get("games_lost", 0),
                "games_played": user_data.get("games_played", 0),
                "timestamp": time.time(),
                "search_id": f"{user_id}_{int(time.time())}",
            }

            if player_data["games_played"] > 0:
                player_data["win_ratio"] = (
                    player_data["games_won"] / player_data["games_played"]
                )
            else:
                player_data["win_ratio"] = 0.5

            await self.redis.lpush(self.queue_key, json.dumps(player_data))
            await self.redis.sadd(self.active_searches_key, player_data["search_id"])

            queue_length = await self.redis.llen(self.queue_key)
            logger.info(
                f"Player {user_id} added to matchmaking queue with Elo {player_data['elo']}. Queue now has {queue_length} players."
            )
            return True

        except Exception as e:
            logger.error(f"Error adding player {user_id} to queue: {e}")
            return False

    async def remove_player_from_queue(
        self, user_id: int, search_id: str = None
    ) -> bool:
        """Remove a player from the matchmaking queue."""
        try:
            if search_id:
                await self.redis.srem(self.active_searches_key, search_id)

            queue_items = await self.redis.lrange(self.queue_key, 0, -1)
            for item in queue_items:
                try:
                    player_data = json.loads(item)
                    if player_data["user_id"] == user_id:
                        await self.redis.lrem(self.queue_key, 1, item)
                        logger.info(f"Player {user_id} removed from matchmaking queue")
                        return True
                except json.JSONDecodeError:
                    continue

            return False

        except Exception as e:
            logger.error(f"Error removing player {user_id} from queue: {e}")
            return False

    async def find_match(self, player_data: dict) -> Optional[dict]:
        """Find a suitable match for a player based on Elo and win/loss ratio."""
        try:
            queue_items = await self.redis.lrange(self.queue_key, 0, -1)
            current_time = time.time()

            logger.info(
                f"Searching for match for player {player_data['user_id']} (Elo: {player_data['elo']})"
            )
            logger.info(f"Queue contains {len(queue_items)} items")

            valid_players = []
            for item in queue_items:
                try:
                    candidate = json.loads(item)
                    logger.info(
                        f"Checking candidate: user_id={candidate.get('user_id')}, elo={candidate.get('elo')}, timestamp={candidate.get('timestamp')}"
                    )

                    if (
                        candidate["user_id"] != player_data["user_id"]
                        and current_time - candidate["timestamp"] < self.max_wait_time
                    ):
                        valid_players.append(candidate)
                        logger.info(
                            f"Valid candidate found: user_id={candidate['user_id']}, elo={candidate['elo']}"
                        )
                    else:
                        if candidate["user_id"] == player_data["user_id"]:
                            logger.info(
                                f"Skipping self: user_id={candidate['user_id']}"
                            )
                        else:
                            logger.info(
                                f"Expired candidate: user_id={candidate['user_id']}, age={current_time - candidate['timestamp']}s"
                            )
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON in queue item: {item}")
                    continue

            logger.info(f"Found {len(valid_players)} valid candidates")

            if not valid_players:
                logger.info("No valid players found for matching")
                return None

            best_match = None
            best_score = float("inf")

            for candidate in valid_players:
                score = self._calculate_match_score(player_data, candidate)
                logger.info(f"Match score for {candidate['user_id']}: {score}")
                if score < best_score:
                    best_score = score
                    best_match = candidate

            if best_match and self._is_acceptable_match(player_data, best_match):
                logger.info(
                    f"Found acceptable match: {best_match['user_id']} (score: {best_score})"
                )
                return best_match
            else:
                logger.info(
                    f"Best match {best_match['user_id'] if best_match else 'None'} not acceptable"
                )

            return None

        except Exception as e:
            logger.error(f"Error finding match: {e}")
            return None

    def _calculate_match_score(self, player1: dict, player2: dict) -> float:
        """Calculate match quality score (lower is better)."""
        elo_diff = abs(player1["elo"] - player2["elo"])
        elo_score = (elo_diff / self.elo_tolerance) ** 2

        ratio_diff = abs(player1["win_ratio"] - player2["win_ratio"])
        ratio_score = (ratio_diff / self.ratio_tolerance) ** 2

        wait_time1 = time.time() - player1["timestamp"]
        wait_time2 = time.time() - player2["timestamp"]
        wait_bonus = -min(wait_time1, wait_time2) / 10

        return elo_score + ratio_score + wait_bonus

    def _is_acceptable_match(self, player1: dict, player2: dict) -> bool:
        """Check if two players are acceptable matches."""
        wait_time = time.time() - min(player1["timestamp"], player2["timestamp"])
        dynamic_elo_tolerance = self.elo_tolerance + (wait_time / 10) * 50

        elo_diff = abs(player1["elo"] - player2["elo"])
        if elo_diff > dynamic_elo_tolerance:
            logger.info(
                f"Elo difference too high: {elo_diff} > {dynamic_elo_tolerance}"
            )
            return False

        ratio_diff = abs(player1["win_ratio"] - player2["win_ratio"])
        if ratio_diff > self.ratio_tolerance:
            logger.info(
                f"Ratio difference too high: {ratio_diff} > {self.ratio_tolerance}"
            )
            return False

        logger.info(
            f"Match is acceptable: elo_diff={elo_diff}, ratio_diff={ratio_diff}"
        )
        return True

    async def create_match(
        self, player1_data: dict, player2_data: dict
    ) -> Optional[Game]:
        """Create a game between two matched players."""
        try:
            logger.info(
                f"Creating match between player {player1_data['user_id']} and {player2_data['user_id']}"
            )

            logger.info(f"Removing player {player1_data['user_id']} from queue")
            await self.remove_player_from_queue(
                player1_data["user_id"], player1_data["search_id"]
            )

            logger.info(f"Removing player {player2_data['user_id']} from queue")
            await self.remove_player_from_queue(
                player2_data["user_id"], player2_data["search_id"]
            )

            logger.info(
                f"Creating game object for players {player1_data['user_id']} and {player2_data['user_id']}"
            )
            game = await self._create_game_async(
                player1_data["user_id"], player2_data["user_id"]
            )

            if game:
                logger.info(
                    f"Created match between {player1_data['user_id']} and {player2_data['user_id']}: {game.code}"
                )
                return game
            else:
                logger.error(
                    f"Game creation returned None for players {player1_data['user_id']} and {player2_data['user_id']}"
                )

            return None

        except Exception as e:
            logger.error(
                f"Error creating match between {player1_data['user_id']} and {player2_data['user_id']}: {e}"
            )
            return None

    @database_sync_to_async
    def _create_game_async(self, player1_id: int, player2_id: int) -> Game:
        """Create a game synchronously."""
        try:
            logger.info(f"Looking up users {player1_id} and {player2_id}")
            player1 = CustomUser.objects.get(id=player1_id)
            player2 = CustomUser.objects.get(id=player2_id)
            logger.info(f"Found users: {player1.username} and {player2.username}")

            logger.info(f"Creating Game object in database")
            game = Game.objects.create(
                player_white=player1,
                player_black=player2,
                status="active",
                subjects=["math"],
            )
            logger.info(f"Game created successfully with code: {game.code}")

            return game

        except CustomUser.DoesNotExist as e:
            logger.error(f"User not found: {player1_id} or {player2_id} - {e}")
            return None
        except Exception as e:
            logger.error(f"Error creating game: {e}")
            return None

    async def cleanup_expired_searches(self):
        """Remove expired searches from the queue."""
        try:
            queue_items = await self.redis.lrange(self.queue_key, 0, -1)
            current_time = time.time()

            for item in queue_items:
                try:
                    player_data = json.loads(item)
                    if current_time - player_data["timestamp"] > self.max_wait_time:
                        await self.redis.lrem(self.queue_key, 1, item)
                        await self.redis.srem(
                            self.active_searches_key, player_data["search_id"]
                        )
                        logger.info(
                            f"Removed expired search for player {player_data['user_id']}"
                        )
                except json.JSONDecodeError:
                    await self.redis.lrem(self.queue_key, 1, item)

        except Exception as e:
            logger.error(f"Error cleaning up expired searches: {e}")

    async def get_queue_status(self) -> dict:
        """Get current queue status."""
        try:
            queue_length = await self.redis.llen(self.queue_key)
            active_searches = await self.redis.scard(self.active_searches_key)

            status = {"queue_length": queue_length, "active_searches": active_searches}
            logger.info(f"Queue status requested: {status}")
            return status
        except Exception as e:
            logger.error(f"Error getting queue status: {e}")
            return {"queue_length": 0, "active_searches": 0}
