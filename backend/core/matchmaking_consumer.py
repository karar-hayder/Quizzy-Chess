import json
import logging
import time
from typing import Dict, Optional

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.layers import get_channel_layer

from core.matchmaking import MatchmakingService
from core.serializers import GameSerializer
from users.models import CustomUser

logger = logging.getLogger(__name__)


class MatchmakingConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for handling matchmaking requests."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_id = None
        self.search_id = None
        self.matchmaking_service = None
        self.is_connected = False

    async def connect(self):
        """Handle WebSocket connection."""
        user = self.scope["user"]

        if not user.is_authenticated:
            await self.close(code=4001)  # Custom code for authentication required
            return

        self.user_id = user.id
        self.search_id = None
        self.is_connected = False
        self.matchmaking_service = MatchmakingService()

        await self.accept()

        group_name = f"user_{self.user_id}"
        await self.channel_layer.group_add(group_name, self.channel_name)
        logger.info(
            f"User {self.user_id} added to group {group_name} with channel {self.channel_name}"
        )

        self.is_connected = True
        logger.info(
            f"Matchmaking consumer connected for user {self.user_id} - connection state: {self.is_connected}"
        )

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        logger.info(
            f"Matchmaking consumer disconnecting for user {self.user_id} with close_code {close_code}"
        )

        if self.user_id:
            try:
                if self.search_id and self.matchmaking_service:
                    logger.info(
                        f"Removing user {self.user_id} from queue with search_id {self.search_id}"
                    )
                    await self.matchmaking_service.remove_player_from_queue(
                        self.user_id, self.search_id
                    )

                group_name = f"user_{self.user_id}"
                await self.channel_layer.group_discard(group_name, self.channel_name)
                logger.info(f"User {self.user_id} removed from group {group_name}")

            except Exception as e:
                logger.error(f"Error during disconnect for user {self.user_id}: {e}")

        self.is_connected = False
        logger.info(
            f"Matchmaking consumer disconnected for user {self.user_id} - connection state: {self.is_connected}"
        )

    async def receive(self, text_data):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(text_data)
            message_type = data.get("type")

            if message_type != "ping":
                logger.info(
                    f"User {self.user_id} received message type: {message_type}"
                )

            if message_type == "find_game":
                await self.handle_find_game(data.get("payload", {}))
            elif message_type == "cancel_search":
                await self.handle_cancel_search()
            elif message_type == "ping":
                await self.send_json({"type": "pong", "payload": {}})
            else:
                await self.send_json(
                    {
                        "type": "error",
                        "payload": {"reason": f"Unknown message type: {message_type}"},
                    }
                )

        except json.JSONDecodeError:
            await self.send_json(
                {"type": "error", "payload": {"reason": "Invalid JSON format"}}
            )
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await self.send_json(
                {"type": "error", "payload": {"reason": "Internal server error"}}
            )

    async def handle_find_game(self, payload: dict):
        """Handle find game request."""
        try:
            user_data = await self.get_user_data()
            if not user_data:
                await self.send_json(
                    {"type": "error", "payload": {"reason": "User data not found"}}
                )
                return

            logger.info(f"Player {self.user_id} attempting to join matchmaking queue")
            success = await self.matchmaking_service.add_player_to_queue(
                self.user_id, user_data
            )
            if not success:
                logger.error(f"Failed to add player {self.user_id} to queue")
                await self.send_json(
                    {
                        "type": "error",
                        "payload": {"reason": "Failed to join matchmaking queue"},
                    }
                )
                return
            logger.info(
                f"Player {self.user_id} successfully added to matchmaking queue"
            )

            self.search_id = f"{self.user_id}_{int(time.time())}"

            await self.send_json(
                {
                    "type": "search_started",
                    "payload": {
                        "message": "Searching for opponent...",
                        "search_id": self.search_id,
                    },
                }
            )

            await self.try_find_match(user_data)

        except Exception as e:
            logger.error(f"Error in handle_find_game: {e}")
            await self.send_json(
                {"type": "error", "payload": {"reason": "Failed to start search"}}
            )

    async def handle_cancel_search(self):
        """Handle cancel search request."""
        try:
            if self.search_id and self.matchmaking_service:
                success = await self.matchmaking_service.remove_player_from_queue(
                    self.user_id, self.search_id
                )
                if success:
                    self.search_id = None
                    await self.send_json(
                        {
                            "type": "search_cancelled",
                            "payload": {"message": "Search cancelled"},
                        }
                    )
                else:
                    await self.send_json(
                        {
                            "type": "error",
                            "payload": {"reason": "Failed to cancel search"},
                        }
                    )
            else:
                await self.send_json(
                    {
                        "type": "error",
                        "payload": {"reason": "No active search to cancel"},
                    }
                )

        except Exception as e:
            logger.error(f"Error in handle_cancel_search: {e}")
            await self.send_json(
                {"type": "error", "payload": {"reason": "Failed to cancel search"}}
            )

    async def try_find_match(self, user_data: dict):
        """Try to find a match for the current user."""
        try:
            if not self.search_id:
                logger.info(
                    f"Player {self.user_id} search cancelled, stopping match search"
                )
                return

            if not self.is_connected:
                logger.info(
                    f"Player {self.user_id} disconnected, stopping match search"
                )
                return

            logger.info(f"Player {self.user_id} starting match search")

            player_data = {
                "user_id": self.user_id,
                "elo": user_data.get("rating", 1200),
                "games_won": user_data.get("games_won", 0),
                "games_lost": user_data.get("games_lost", 0),
                "games_played": user_data.get("games_played", 0),
                "timestamp": time.time(),
                "search_id": self.search_id,
            }

            if player_data["games_played"] > 0:
                player_data["win_ratio"] = (
                    player_data["games_won"] / player_data["games_played"]
                )
            else:
                player_data["win_ratio"] = 0.5

            logger.info(
                f"Player {self.user_id} searching for match with Elo {player_data['elo']}"
            )

            opponent_data = await self.matchmaking_service.find_match(player_data)

            if not self.search_id:
                logger.info(
                    f"Player {self.user_id} search cancelled during find_match, stopping"
                )
                return

            if not self.is_connected:
                logger.info(
                    f"Player {self.user_id} disconnected during find_match, stopping"
                )
                return

            if opponent_data:
                logger.info(
                    f"Player {self.user_id} found opponent {opponent_data['user_id']}"
                )

                logger.info(
                    f"Player {self.user_id} attempting to create game with opponent {opponent_data['user_id']}"
                )
                try:
                    game = await self.matchmaking_service.create_match(
                        player_data, opponent_data
                    )
                    logger.info(
                        f"Game creation result for player {self.user_id}: {game}"
                    )
                except Exception as e:
                    logger.error(f"Error creating game for player {self.user_id}: {e}")
                    game = None

                if game:
                    logger.info(f"Game created by player {self.user_id}: {game.code}")

                    try:
                        game_data = await self.serialize_game(game)
                        logger.info(f"Game serialized successfully: {game.code}")
                    except Exception as e:
                        logger.error(f"Error serializing game {game.code}: {e}")
                        return

                    logger.info(f"Game created successfully: {game.code}")
                    logger.info(
                        f"Notifying players: {self.user_id} and {opponent_data['user_id']}"
                    )

                    self.search_id = None

                    for uid in [self.user_id, opponent_data["user_id"]]:
                        logger.info(f"Sending game_found notification to user {uid}")
                        try:
                            group_name = f"user_{uid}"
                            logger.info(f"Checking if group {group_name} exists")

                            try:
                                logger.info(
                                    f"Verifying group membership for {group_name}"
                                )
                            except Exception as e:
                                logger.warning(
                                    f"Could not verify group membership for {group_name}: {e}"
                                )

                            message = {
                                "type": "game_found",
                                "payload": {
                                    "game": game_data,
                                    "message": "Opponent found! Game starting...",
                                    "game_code": game.code,
                                },
                            }
                            logger.info(
                                f"Sending message to group {group_name} for game {game.code}: {message}"
                            )

                            await self.channel_layer.group_send(
                                group_name,
                                message,
                            )
                            logger.info(f"Successfully sent game_found to user {uid}")
                            logger.info(
                                f"Group send completed for {group_name} with message type: {message['type']}"
                            )

                        except Exception as e:
                            logger.error(f"Error in group_send to user {uid}: {e}")
                            logger.error(
                                f"Channel layer error details: {type(e).__name__}: {str(e)}"
                            )
                            continue

                else:
                    logger.error(
                        f"Failed to create game for {self.user_id} and {opponent_data['user_id']}"
                    )
            else:
                logger.info(f"Player {self.user_id} found no match, scheduling retry")
                await self.schedule_match_retry(user_data)

        except Exception as e:
            logger.error(f"Error in try_find_match for player {self.user_id}: {e}")

    async def schedule_match_retry(self, user_data: dict):
        """Schedule a retry to find a match using background task."""
        import asyncio

        async def retry_task():
            try:
                await asyncio.sleep(2)

                if not self.search_id:
                    logger.info(
                        f"Search cancelled for user {self.user_id}, skipping retry"
                    )
                    return

                if not self.is_connected:
                    logger.info(f"User {self.user_id} disconnected, skipping retry")
                    return

                logger.info(
                    f"Retrying match search for user {self.user_id} with search_id {self.search_id}"
                )
                await self.try_find_match(user_data)
            except Exception as e:
                logger.error(f"Error in retry task for user {self.user_id}: {e}")

        asyncio.create_task(retry_task())

    @database_sync_to_async
    def get_user_data(self) -> Optional[dict]:
        """Get user data for matchmaking."""
        try:
            user = CustomUser.objects.get(id=self.user_id)
            return {
                "rating": user.rating,
                "games_won": user.games_won,
                "games_lost": user.games_lost,
                "games_played": user.games_played,
                "username": user.username,
            }
        except CustomUser.DoesNotExist:
            return None

    @database_sync_to_async
    def serialize_game(self, game) -> dict:
        """Serialize game data with proper datetime handling."""
        from django.core.serializers.json import DjangoJSONEncoder
        import json

        simplified_game = {
            "code": game.code,
            "fen": game.fen,
            "player_white": (
                {
                    "id": game.player_white.id,
                    "username": game.player_white.username,
                    "rating": game.player_white.rating,
                }
                if game.player_white
                else None
            ),
            "player_black": (
                {
                    "id": game.player_black.id,
                    "username": game.player_black.username,
                    "rating": game.player_black.rating,
                }
                if game.player_black
                else None
            ),
        }

        return simplified_game

    async def game_found(self, event):
        """Handle game_found event."""
        logger.info(f"=== GAME_FOUND EVENT HANDLER ENTERED FOR USER {self.user_id} ===")
        game_code = event.get("payload", {}).get("game_code", "unknown")
        logger.info(
            f"game_found event received for user {self.user_id} for game {game_code}: {event}"
        )
        logger.info(
            f"game_found handler called for user {self.user_id} with channel {self.channel_name}"
        )
        logger.info(f"Connection state for user {self.user_id}: {self.is_connected}")

        self.search_id = None
        logger.info(f"Search ID cleared for user {self.user_id} for game {game_code}")

        try:
            if not self.is_connected:
                logger.warning(
                    f"User {self.user_id} not connected, cannot send game_found"
                )
                return

            logger.info(
                f"Attempting to send game_found to user {self.user_id} for game {game_code}"
            )
            await self.send_json({"type": "game_found", "payload": event["payload"]})
            logger.info(
                f"Successfully sent game_found to user {self.user_id} for game {game_code} and cleared search"
            )
        except Exception as e:
            logger.error(
                f"Error sending game_found to user {self.user_id} for game {game_code}: {e}"
            )
            logger.error(f"User {self.user_id} channel: {self.channel_name}")
            logger.error(f"User {self.user_id} group: user_{self.user_id}")
            logger.error(f"User {self.user_id} connection state: {self.is_connected}")
            logger.error(f"Event payload: {event.get('payload', {})}")

    async def send_json(self, data: dict):
        """Send JSON data to the client."""
        try:
            logger.info(
                f"Attempting to send JSON to client for user {self.user_id}: {data}"
            )
            await self.send(text_data=json.dumps(data))
            logger.info(f"Successfully sent JSON to client for user {self.user_id}")
        except Exception as e:
            logger.error(f"Error sending JSON to client for user {self.user_id}: {e}")
            raise
