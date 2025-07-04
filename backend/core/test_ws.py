import asyncio
import json
import logging

import pytest
from channels.db import database_sync_to_async
from channels.testing import ChannelsLiveServerTestCase, WebsocketCommunicator
from django.conf import settings
from django.db import transaction
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from backend.asgi import application
from core.consumers import update_fen
from users.models import CustomUser

from .models import Game, Move, QuizQuestion


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class GameWebSocketTests(ChannelsLiveServerTestCase):
    serve_static = True

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with transaction.atomic():
            cls.user1, _ = CustomUser.objects.get_or_create(
                username="player1", defaults={"password": "pass1"}
            )
            cls.user2, _ = CustomUser.objects.get_or_create(
                username="player2", defaults={"password": "pass2"}
            )
            cls.user3, _ = CustomUser.objects.get_or_create(
                username="spectator", defaults={"password": "spectatorpass"}
            )
            cls.quiz, _ = QuizQuestion.objects.get_or_create(
                subject="Math",
                question="2+2=?",
                option_a="3",
                option_b="4",
                option_c="5",
                option_d="6",
                correct_option="B",
                explanation="2+2=4",
            )
            cls.game, _ = Game.objects.get_or_create(
                player_white=cls.user1,
                player_black=cls.user2,
                subjects=["Math", "Science"],
            )
        transaction.get_connection().commit()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

    @database_sync_to_async
    def get_user_by_username(self, username):
        return CustomUser.objects.get(username=username)

    async def get_token(self, user):
        return str(AccessToken.for_user(user))

    async def ws_connect(self, user, code):
        token = await self.get_token(user)
        communicator = WebsocketCommunicator(
            application,
            f"/ws/game/{code}/?token={token}",
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        logging.info("WebSocket connected in test_move_and_quiz_flow")
        return communicator

    async def ws_receive_json(self, communicator, timeout=5):
        try:
            msg = await asyncio.wait_for(
                communicator.receive_json_from(), timeout=timeout
            )
            if not isinstance(msg, dict):
                print("Non-dict WebSocket message:", msg)
            return msg
        except asyncio.TimeoutError:
            self.fail("Timed out waiting for WebSocket message")
        except Exception as e:
            print("WebSocket receive error:", e)
            raise

    def get_msg_type(self, msg):
        return msg.get("type")

    async def ensure_test_game(self):
        from .models import CustomUser, Game

        code = self.__class__.game.code
        user1, _ = await database_sync_to_async(CustomUser.objects.get_or_create)(
            username="player1", defaults={"password": "pass1"}
        )
        user2, _ = await database_sync_to_async(CustomUser.objects.get_or_create)(
            username="player2", defaults={"password": "pass2"}
        )
        game, _ = await database_sync_to_async(Game.objects.get_or_create)(
            code=code,
            defaults={
                "player_white": user1,
                "player_black": user2,
                "subjects": ["Math", "Science"],
            },
        )
        return user1, user2, game

    async def test_move_and_quiz_flow(self):
        comm1 = comm2 = comm3 = None
        user1, user2, game = await self.ensure_test_game()
        code = game.code
        try:
            comm1 = await self.ws_connect(user1, code)
            comm2 = await self.ws_connect(user2, code)
            comm3 = await self.ws_connect(self.__class__.user3, code)
            await comm1.send_json_to(
                {
                    "type": "move",
                    "payload": {
                        "from_square": "e2",
                        "to_square": "e4",
                        "piece": "pawn",
                        "move_number": 1,
                        "fen_after": "somefen",
                        "captured_piece": "",
                    },
                }
            )
            msg = await self.wait_for_message_type(comm1, "move", timeout=5)
            print("move_and_quiz_flow: received", msg)
            msg_type = self.get_msg_type(msg)
            self.assertEqual(msg_type, "move")
            await comm2.send_json_to(
                {
                    "type": "move",
                    "payload": {
                        "from_square": "e2",
                        "to_square": "e5",
                        "piece": "pawn",
                        "move_number": 2,
                        "fen_after": "somefen",
                        "captured_piece": "",
                    },
                }
            )
            msg2 = await self.wait_for_message_type(comm2, "move_invalid", timeout=5)
            self.assertEqual(msg2["type"], "move_invalid")
            await comm3.send_json_to(
                {
                    "type": "move",
                    "payload": {
                        "from_square": "e2",
                        "to_square": "e4",
                        "piece": "pawn",
                        "move_number": 3,
                        "fen_after": "somefen",
                        "captured_piece": "",
                    },
                }
            )
            msg3 = await self.wait_for_message_type(comm3, None, timeout=5)
            if msg3.get("type") == "permission_denied":
                self.assertEqual(msg3["type"], "permission_denied")
            elif msg3.get("type") == "error":
                self.assertIn("reason", msg3.get("payload", {}))
                self.assertIn("Spectators cannot make moves", msg3["payload"]["reason"])
            else:
                self.fail(f"Unexpected message type: {msg3}")
            await comm1.send_json_to(
                {
                    "type": "move",
                    "payload": {
                        "from_square": "d1",
                        "to_square": "h5",
                        "piece": "queen",
                        "move_number": 4,
                        "fen_after": "somefen",
                        "captured_piece": "rook",
                        "subject": "Math",
                    },
                }
            )
            quiz_msg = await self.wait_for_message_type(
                comm1, "quiz_required", timeout=5
            )
            self.assertEqual(quiz_msg["type"], "quiz_required")
            await comm1.send_json_to(
                {"type": "quiz_answer", "payload": {"answer": "C", "move_number": 4}}
            )
            fail_msg = await self.wait_for_message_type(comm1, "quiz_failed", timeout=5)
            self.assertEqual(fail_msg["type"], "quiz_failed")
            await comm1.send_json_to(
                {"type": "quiz_answer", "payload": {"answer": "A", "move_number": 4}}
            )
            move_msg = await self.wait_for_message_type(comm1, "move", timeout=5)
            self.assertEqual(move_msg["type"], "move")
            await comm3.send_json_to(
                {"type": "quiz_answer", "payload": {"answer": "A", "move_number": 4}}
            )
            perm_msg = await self.wait_for_message_type(
                comm3, "permission_denied", timeout=5
            )
            self.assertEqual(perm_msg["type"], "permission_denied")
        except Exception as e:
            print(e)
        finally:
            await self.safe_disconnect(comm1)
            await self.safe_disconnect(comm2)
            await self.safe_disconnect(comm3)

    async def wait_for_message_type(self, communicator, expected_type, timeout=5):
        end_time = asyncio.get_event_loop().time() + timeout
        while True:
            remaining = end_time - asyncio.get_event_loop().time()
            if remaining <= 0:
                self.fail(f"Timed out waiting for message type: {expected_type}")
            msg = await asyncio.wait_for(
                communicator.receive_json_from(), timeout=remaining
            )
            print(f"[wait_for_message_type] Received: {msg}")
            msg_type = self.get_msg_type(msg)
            if msg_type is None:
                print(
                    f"[wait_for_message_type] WARNING: Message missing 'type' and 'message' keys: {msg}"
                )
            if msg_type == expected_type:
                return msg

    async def test_game_end_by_checkmate(self):
        user1, user2, game = await self.ensure_test_game()
        code = game.code
        comm1 = await self.ws_connect(user1, code)
        comm2 = await self.ws_connect(user2, code)
        try:
            pre_checkmate_fen = "7k/5Q2/6K1/8/8/8/8/8 w - - 0 1"
            game.fen = pre_checkmate_fen
            await update_fen(game, pre_checkmate_fen)
            await comm1.send_json_to(
                {"type": "move", "payload": {"from_square": "f7", "to_square": "g7"}}
            )
            msg = await self.wait_for_message_type(comm1, "game_over", timeout=5)
            self.assertEqual(msg["payload"]["reason"], "checkmate")
        finally:
            await self.safe_disconnect(comm1)
            await self.safe_disconnect(comm2)

    async def test_game_end_by_stalemate(self):
        import chess

        user1, user2, game = await self.ensure_test_game()
        code = game.code
        comm1 = await self.ws_connect(user1, code)
        comm2 = await self.ws_connect(user2, code)
        try:
            pre_stalemate_fen = "7k/5Q2/7K/8/8/8/8/8 w - - 0 1"
            game.fen = pre_stalemate_fen
            await update_fen(game, pre_stalemate_fen)
            await comm1.send_json_to(
                {"type": "move", "payload": {"from_square": "f7", "to_square": "g6"}}
            )
            msg = await self.wait_for_message_type(comm1, "game_over", timeout=5)
            self.assertEqual(msg["payload"]["reason"], "draw")
        finally:
            await self.safe_disconnect(comm1)
            await self.safe_disconnect(comm2)

    async def test_resign(self):
        user1, user2, game = await self.ensure_test_game()
        code = game.code
        comm1 = await self.ws_connect(user1, code)
        comm2 = await self.ws_connect(user2, code)
        try:
            await comm1.send_json_to({"type": "resign"})
            try:
                msg = await self.wait_for_message_type(comm2, "game_over", timeout=10)
                msg_type = self.get_msg_type(msg)
                self.assertEqual(msg_type, "game_over")
                self.assertEqual(msg["payload"]["reason"], "resignation")
                self.assertEqual(msg["payload"]["winner"], "black")
            except Exception as e:
                print(f"Error in test_resign: {e}")
                try:
                    debug_msg = await asyncio.wait_for(
                        comm2.receive_json_from(), timeout=2
                    )
                    print(f"Debug message received: {debug_msg}")
                except:
                    pass
                raise
        finally:
            await self.safe_disconnect(comm1)
            await self.safe_disconnect(comm2)

    async def test_draw_offer_and_accept(self):
        user1, user2, game = await self.ensure_test_game()
        code = game.code
        comm1 = await self.ws_connect(user1, code)
        comm2 = await self.ws_connect(user2, code)
        try:
            await comm1.send_json_to({"type": "draw_offer"})
            offer_msg = await self.wait_for_message_type(comm2, "draw_offer", timeout=5)
            self.assertEqual(offer_msg["type"], "draw_offer")
            await comm2.send_json_to({"type": "draw_accept"})
            over_msg = await self.wait_for_message_type(comm1, "game_over", timeout=10)
            self.assertEqual(over_msg["type"], "game_over")
            self.assertEqual(over_msg["payload"]["reason"], "draw_agreed")
        finally:
            await self.safe_disconnect(comm1)
            await self.safe_disconnect(comm2)

    async def safe_disconnect(self, communicator):
        """Safely disconnect a WebSocket communicator, handling any exceptions."""
        if communicator:
            try:
                await communicator.disconnect()
            except Exception as e:
                print(f"Warning: Error during disconnect: {e}")

    async def test_spectator_cannot_move_resign_or_draw(self):
        user1, user2, game = await self.ensure_test_game()
        code = game.code
        comm3 = await self.ws_connect(self.__class__.user3, code)
        try:
            await comm3.send_json_to(
                {"type": "move", "payload": {"from_square": "e2", "to_square": "e4"}}
            )
            msg = await self.wait_for_message_type(comm3, "permission_denied")
            self.assertEqual(msg["type"], "permission_denied")

            await comm3.send_json_to({"type": "resign"})
            msg2 = await self.wait_for_message_type(comm3, "permission_denied")
            print("Spectator resign response:", msg2)
            self.assertEqual(msg2["type"], "permission_denied")

            await comm3.send_json_to({"type": "draw_offer"})
            msg3 = await self.wait_for_message_type(comm3, "permission_denied")
            self.assertEqual(msg3["type"], "permission_denied")

            await comm3.send_json_to({"type": "draw_accept"})
            msg4 = await self.wait_for_message_type(comm3, "permission_denied")
            self.assertEqual(msg4["type"], "permission_denied")
        finally:
            await self.safe_disconnect(comm3)

    async def test_ai_game_ws_flow(self):
        from .models import CustomUser, Game

        user1, _ = await database_sync_to_async(CustomUser.objects.get_or_create)(
            username="player1", defaults={"password": "pass1"}
        )
        game = await database_sync_to_async(Game.objects.create)(
            player_white=user1,
            player_black=None,
            subjects=["Math"],
            is_vs_ai=True,
            ai_difficulty="easy",
            status="active",
        )
        comm1 = await self.ws_connect(user1, game.code)
        try:
            await comm1.send_json_to(
                {"type": "move", "payload": {"from_square": "e2", "to_square": "e4"}}
            )
            msg = await self.wait_for_message_type(comm1, "move", timeout=5)
            self.assertEqual(msg["type"], "move")
            ai_msg = await self.wait_for_message_type(comm1, "move", timeout=10)
            self.assertEqual(ai_msg["type"], "move")
            from chess import Board

            fen = ai_msg["payload"]["fen_after"]
            board = Board(fen)
            self.assertTrue(board.turn)  # True = white to move
        finally:
            await self.safe_disconnect(comm1)
