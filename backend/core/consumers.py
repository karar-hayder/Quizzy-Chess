import asyncio
import functools
import json
import logging
import random
import time

import chess
import redis.asyncio as aioredis
import sentry_sdk  # Monitoring/analytics
from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from channels.exceptions import DenyConnection
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
from redis.asyncio import ConnectionPool

from core.tasks import analyze_game_task, run_ai_move_task
from core.utils import (
    calculate_elo,
    evaluate_board,
    get_redis,
    is_valid_fen,
    update_fen,
)
from users.models import CustomUser

from .models import STARTING_FEN, Game, Move
from .serializers import GameSerializer

logger = logging.getLogger(__name__)

AI_ELO = {
    "easy": 900,
    "normal": 1400,
    "hard": 1800,
}
NEUTRAL_OPPONENT_ELO = 1200


async def update_player_stats_and_rating(user, old_rating, new_rating, result, draw):
    """
    Update a user's stats and rating based on result.
    result: 'win', 'loss', or None
    draw: bool
    """
    user.games_played += 1
    if draw:
        user.games_drawn += 1
    elif result == "win":
        user.games_won += 1
    elif result == "loss":
        user.games_lost += 1
    user.rating = new_rating
    await database_sync_to_async(user.save)()
    await database_sync_to_async(user.refresh_from_db)()


async def get_quiz_question(game, subject):
    redis = get_redis()
    game_code = game.code
    try:
        key = f"game:{game_code}:quizzes:{subject.lower()}"
        logger.info(f"Fetching quiz question from Redis with key: {key}")
        questions_json = await redis.get(key)

        if questions_json:
            logger.info(
                f"Quiz questions found in Redis for game {game_code}, subject {subject}"
            )
            questions = json.loads(questions_json)
            if isinstance(questions, list) and questions:
                selected_question = random.choice(questions)
                logger.info(
                    f"Selected quiz question for game {game_code}, subject {subject}: {selected_question}"
                )
                return selected_question
            else:
                logger.info(
                    f"No valid questions list found in Redis for game {game_code}, subject {subject}"
                )
        else:
            logger.info(
                f"No quiz questions found in Redis for game {game_code}, subject {subject}"
            )
    except Exception as e:
        logger.error(
            f"Error fetching quiz question from Redis for game {game_code}, subject {subject}: {e}"
        )

    try:
        player_elos = []
        if hasattr(game, "player_white") and game.player_white:
            player_elos.append(getattr(game.player_white, "rating", 1200))
        if hasattr(game, "player_black") and game.player_black:
            player_elos.append(getattr(game.player_black, "rating", 1200))
        if not player_elos:
            player_elos = [1200]
        avg_elo = int(sum(player_elos) / len(player_elos))
        elo_range = 200
        min_elo = max(800, avg_elo - elo_range)
        max_elo = avg_elo + elo_range

        @sync_to_async()
        def get_quiz_from_db():
            from .models import QuizQuestion

            questions = QuizQuestion.objects.filter(
                subject=subject, avg_elo__gte=min_elo, avg_elo__lte=max_elo
            )[:5]
            if not questions.exists():
                questions = QuizQuestion.objects.filter(subject=subject)[:5]
            if questions.exists():
                question = random.choice(questions)
                return {
                    "subject": question.subject,
                    "question": question.question,
                    "choices": [
                        f"A: {question.option_a}",
                        f"B: {question.option_b}",
                        f"C: {question.option_c}",
                        f"D: {question.option_d}",
                    ],
                    "correct": question.correct_option,
                    "explanation": question.explanation
                    or f"Correct answer is {question.correct_option}",
                }
            return None

        db_question = await get_quiz_from_db()
        if db_question:
            logger.info(
                f"Found quiz question from database for game {game_code}, subject {subject}, avg Elo {avg_elo}"
            )
            return db_question
    except Exception as e:
        logger.error(
            f"Error fetching quiz question from database for game {game_code}, subject {subject}: {e}"
        )

    logger.warning(
        f"Using fallback dummy question for game {game_code}, subject {subject}"
    )
    return {
        "subject": subject,
        "question": f"Dummy question for {subject}?",
        "choices": ["A", "B", "C", "D"],
        "correct": "A",
        "explanation": "This is a dummy explanation.",
    }


REDIS_URL = getattr(settings, "REDIS_URL", "redis://localhost:6379/0")


def get_redis():
    return aioredis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)


@database_sync_to_async
def get_game_by_code(game_code):
    return Game.objects.get(code=game_code)


@database_sync_to_async
def get_game_and_players(game_code):
    try:
        game = Game.objects.get(code=game_code)
        return game, game.player_white_id, game.player_black_id
    except Game.DoesNotExist:
        return None, None, None


def sanitize_fen_for_frontend(fen: str):
    if not fen:
        return ""
    logger.warning(fen)
    return fen.strip()


async def get_fen(game):
    redis = get_redis()
    try:
        fen = await redis.get(f"game:{game.code}:fen")
        if fen:
            return sanitize_fen_for_frontend(fen)
    except Exception:
        pass
    try:
        from django.apps import apps

        GameModel = apps.get_model("core", "Game")
        db_game = await database_sync_to_async(GameModel.objects.get)(pk=game.pk)
        if db_game.fen:
            return sanitize_fen_for_frontend(db_game.fen)
    except Exception:
        pass
    return sanitize_fen_for_frontend(game.fen)


def is_valid_fen(fen):
    try:
        chess.Board(fen)
        return True
    except Exception:
        return False


async def update_fen(game, fen):
    if not is_valid_fen(fen):
        logger.error(f"Attempted to save invalid FEN: {fen}")
        raise ValueError(f"Invalid FEN attempted to be saved: {fen}")
    game.fen = fen
    await database_sync_to_async(game.save)()
    redis = get_redis()
    await redis.set(f"game:{game.code}:fen", fen)


@database_sync_to_async
def create_move(game, player, move_data, quiz_required=False, quiz_correct=None):
    return Move.objects.create(
        game=game,
        player=player,
        from_square=move_data["from_square"],
        to_square=move_data["to_square"],
        piece=move_data["piece"],
        captured_piece=move_data.get("captured_piece"),
        move_number=move_data["move_number"],
        fen_after=move_data["fen_after"],
        quiz_required=quiz_required,
        quiz_correct=quiz_correct,
    )


@database_sync_to_async
def get_pending_quiz_move(game, move_number):
    return Move.objects.filter(
        game=game, move_number=move_number, quiz_required=True
    ).first()


@sync_to_async
def serialize_game(game):
    from django.core.serializers.json import DjangoJSONEncoder
    import json

    serializer = GameSerializer(game)
    data = serializer.data

    json_str = json.dumps(data, cls=DjangoJSONEncoder)
    return json.loads(json_str)


def ws_error_handler(func):
    @functools.wraps(func)
    async def wrapper(self, *args, **kwargs):
        try:
            return await func(self, *args, **kwargs)
        except DenyConnection:
            raise
        except Exception as e:
            logger.exception(f"Error in {func.__name__}: {e}")
            await self.send_json({"type": "error", "payload": {"reason": str(e)}})

    return wrapper


def require_authenticated_player(func):
    @functools.wraps(func)
    async def wrapper(self, *args, **kwargs):
        user = self.scope["user"]
        if not user.is_authenticated:
            await self.send_json(
                {
                    "type": "permission_denied",
                    "payload": {"reason": "Authentication required."},
                }
            )
            return
        return await func(self, *args, **kwargs)

    return wrapper


sentry_sdk.init(dsn=None, traces_sample_rate=1.0)


class GameConsumer(AsyncWebsocketConsumer):
    async def send_json(self, data):
        if "message" in data and "type" not in data:
            data["type"] = data.pop("message")
        await self.send(text_data=json.dumps(data))

    @ws_error_handler
    async def connect(self):
        logger.info("WebSocket connect called for %s", self.scope.get("user"))
        self.game_code = self.scope["url_route"]["kwargs"]["game_code"]
        self.room_group_name = f"game_{self.game_code}"
        self.quiz_answer_future = None  # For quiz answer handling
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        game, player_white_id, player_black_id = await get_game_and_players(
            self.game_code
        )
        if game is None:
            await self.send_json(
                {"type": "error", "payload": {"reason": "Game not found."}}
            )
            return

        user = self.scope["user"]
        user_id = user.id if user.is_authenticated else None

        is_white_player = user_id == player_white_id
        is_black_player = user_id == player_black_id
        is_player = is_white_player or is_black_player

        if getattr(game, "is_vs_ai", False) and game.status == "active":
            if user.is_authenticated and user.id != player_white_id:
                await self.send_json(
                    {
                        "type": "error",
                        "payload": {
                            "reason": "Cannot join as black in a vs AI game. You are a spectator."
                        },
                    }
                )
                return

        if (
            not is_player
            and user.is_authenticated
            and player_black_id is None
            and not getattr(game, "is_vs_ai", False)
        ):
            is_player = True
            logger.info(
                f"User {user.username} joining as black player (slot was empty)"
            )

        logger.info("About to call send_fen_and_game for game %s", game.code)
        await self.send_fen_and_game(game)
        logger.info("Called send_fen_and_game for game %s", game.code)

        if is_player:
            player_type = "white" if is_white_player else "black"
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "player_joined",
                    "payload": {"user": user.username, "player": player_type},
                },
            )
        else:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "spectator_joined",
                    "payload": {"user": user.username},
                },
            )

    @ws_error_handler
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        self.quiz_answer_future = None
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "spectator_left",
                "payload": {"user": self.scope["user"].username},
            },
        )

    @ws_error_handler
    async def receive(self, text_data):
        data = json.loads(text_data)
        logger.info(f"Received data: {data}")
        event_type = data.get("type")
        user = self.scope["user"]
        game, player_white_id, player_black_id = await get_game_and_players(
            self.game_code
        )
        if game is None:
            await self.send_json(
                {"type": "error", "payload": {"reason": "Game not found."}}
            )
            return
        user_id = user.id if user.is_authenticated else None

        is_white_player = user_id == player_white_id
        is_black_player = user_id == player_black_id
        is_player = is_white_player or is_black_player

        if (
            not is_player
            and user.is_authenticated
            and player_black_id is None
            and not getattr(game, "is_vs_ai", False)
        ):
            is_player = True
            logger.info(
                f"User {user.username} joining as black player (slot was empty)"
            )

        if not isinstance(data, dict) or "type" not in data:
            await self.send_json(
                {"type": "error", "payload": {"reason": "Invalid message format."}}
            )
            return
        if (
            event_type in ["move", "quiz_answer", "resign", "draw_offer", "draw_accept"]
            and not is_player
        ):
            await self.send_json(
                {
                    "type": "permission_denied",
                    "payload": {
                        "reason": "Spectators cannot make moves or answer quizzes."
                    },
                }
            )
            return
        if event_type == "move":
            redis = get_redis()
            lock = redis.lock(f"lock:game:{self.game_code}", timeout=5)
            async with lock:
                await self.handle_move(
                    data, game, user, player_white_id, player_black_id
                )
        elif event_type == "quiz_answer":
            await self.handle_quiz_answer(data, game)
        elif event_type == "resign":
            await self.handle_resign(user, game, player_white_id, player_black_id)
        elif event_type == "draw_offer":
            await self.handle_draw_offer(user, game, player_white_id, player_black_id)
        elif event_type == "draw_accept":
            await self.handle_draw_accept(user, game, player_white_id, player_black_id)
        elif event_type == "ping":
            await self.send_json({"type": "pong", "payload": {}})
        elif event_type == "join_as_black":
            await self.handle_join_as_black(
                user, game, player_white_id, player_black_id
            )
        else:
            await self.send_json(
                {"type": "error", "payload": {"reason": "Unknown event type."}}
            )

    async def update_elo(self, game, winner=None, draw=False):
        """Update Elo ratings for both players after game end. For AI games, use fixed AI Elo. Returns old/new Elo for all participants."""
        print("DEBUG: Entered update_elo", flush=True)
        if getattr(game, "is_vs_ai", False):
            ai_difficulty = getattr(game, "ai_difficulty", "easy")
            ai_elo = AI_ELO.get(ai_difficulty, AI_ELO["easy"])
            user_white = await database_sync_to_async(lambda: game.player_white)()
            if not user_white:
                return None
            old_human = user_white.rating
            old_ai = ai_elo
            games_human = user_white.games_played
            games_ai = 0
            if draw:
                score_human = 0.5
            else:
                score_human = 1 if winner == "white" else 0
            new_human, new_ai = calculate_elo(
                old_human, ai_elo, score_human, games_human, games_ai
            )

            if ai_difficulty != "easy":
                result = None
                if draw:
                    result = None
                elif winner == "white":
                    result = "win"
                else:
                    result = "loss"
                await update_player_stats_and_rating(
                    user_white, old_human, new_human, result, draw
                )

            return {
                "human": {"old": old_human, "new": new_human},
                "ai": {"old": old_ai, "new": new_ai},
            }
        user_white = await database_sync_to_async(lambda: game.player_white)()
        user_black = await database_sync_to_async(lambda: game.player_black)()
        if not (user_white and user_black):
            logger.warning(
                f"One or both players missing: white={user_white}, black={user_black}. Updating stats for available player."
            )
            if user_white:
                old_white = user_white.rating
                games_white = user_white.games_played
                user_white.games_played += 1
                if draw:
                    user_white.games_drawn += 1
                else:
                    if winner == "white":
                        user_white.games_won += 1
                    else:
                        user_white.games_lost += 1
                new_white, _ = calculate_elo(
                    old_white,
                    NEUTRAL_OPPONENT_ELO,
                    1 if winner == "white" else 0,
                    games_white,
                    0,
                )
                user_white.rating = new_white
                await database_sync_to_async(user_white.save)()
                await database_sync_to_async(user_white.refresh_from_db)()
                logger.info(
                    f"Stats saved for white({user_white.username}): played={user_white.games_played}, won={user_white.games_won}, lost={user_white.games_lost}, drawn={user_white.games_drawn}"
                )
            if user_black:
                old_black = user_black.rating
                games_black = user_black.games_played
                user_black.games_played += 1
                if draw:
                    user_black.games_drawn += 1
                else:
                    if winner == "black":
                        user_black.games_won += 1
                    else:
                        user_black.games_lost += 1
                new_black, _ = calculate_elo(
                    old_black,
                    NEUTRAL_OPPONENT_ELO,
                    1 if winner == "black" else 0,
                    games_black,
                    0,
                )
                user_black.rating = new_black
                await database_sync_to_async(user_black.save)()
                await database_sync_to_async(user_black.refresh_from_db)()
                logger.info(
                    f"Stats saved for black({user_black.username}): played={user_black.games_played}, won={user_black.games_won}, lost={user_black.games_lost}, drawn={user_black.games_drawn}"
                )
            return None

        old_white = user_white.rating
        old_black = user_black.rating
        games_white = user_white.games_played
        games_black = user_black.games_played
        logger.info(
            f"Calculating Elo: old_white={old_white}, old_black={old_black}, winner={winner}, draw={draw}"
        )
        if draw:
            score_white = 0.5
        else:
            score_white = 1 if winner == "white" else 0
        new_white, new_black = calculate_elo(
            old_white, old_black, score_white, games_white, games_black
        )
        logger.info(
            f"Elo calculated: new_white={new_white}, new_black={new_black} (score_white={score_white})"
        )
        result_white = None
        result_black = None
        if draw:
            result_white = None
            result_black = None
        elif winner == "white":
            result_white = "win"
            result_black = "loss"
        else:
            result_white = "loss"
            result_black = "win"
        await update_player_stats_and_rating(
            user_white, old_white, new_white, result_white, draw
        )
        await update_player_stats_and_rating(
            user_black, old_black, new_black, result_black, draw
        )
        logger.info(
            f"Elo and stats saved: white({user_white.username}) {old_white}->{new_white}, black({user_black.username}) {old_black}->{new_black}"
        )
        return {
            "white": {"old": old_white, "new": new_white},
            "black": {"old": old_black, "new": new_black},
        }

    async def handle_resign(self, user, game, player_white_id, player_black_id):
        winner = None
        if user.id == player_white_id:
            winner = "black"
        elif user.id == player_black_id or (
            player_black_id is None and not getattr(game, "is_vs_ai", False)
        ):
            winner = "white"
        else:
            await self.send_json(
                {
                    "type": "permission_denied",
                    "payload": {"reason": "Only players can resign."},
                }
            )
            return

        game.status = "finished"
        game.result = f"{winner}_win_by_resignation"
        await database_sync_to_async(game.save)()
        elo_change = await self.update_elo(game, winner=winner)
        logger.info(f"Player {user.username} resigned. Winner: {winner}")
        payload = {"reason": "resignation", "winner": winner}
        if elo_change:
            payload["elo_change"] = elo_change
        await sync_to_async(analyze_game_task.delay)(game.id)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "game_over",
                "payload": payload,
            },
        )

    async def handle_draw_offer(self, user, game, player_white_id, player_black_id):
        if user.id == player_white_id:
            offer_from = "white"
        elif user.id == player_black_id or (
            player_black_id is None and not getattr(game, "is_vs_ai", False)
        ):
            offer_from = "black"
        else:
            await self.send_json(
                {
                    "type": "permission_denied",
                    "payload": {"reason": "Only players can offer draws."},
                }
            )
            return

        logger.info(f"Draw offer from {offer_from}")
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "draw_offer",
                "payload": {"from": offer_from},
            },
        )

    async def handle_draw_accept(self, user, game, player_white_id, player_black_id):
        if not (
            user.id == player_white_id
            or user.id == player_black_id
            or (player_black_id is None and not getattr(game, "is_vs_ai", False))
        ):
            await self.send_json(
                {
                    "type": "permission_denied",
                    "payload": {"reason": "Only players can accept draws."},
                }
            )
            return

        game.status = "finished"
        game.result = "draw"
        await database_sync_to_async(game.save)()
        elo_change = await self.update_elo(game, draw=True)
        logger.info(f"Draw accepted. Game ended in draw.")
        payload = {"reason": "draw_agreed", "winner": None}
        if elo_change:
            payload["elo_change"] = elo_change
        await sync_to_async(analyze_game_task.delay)(game.id)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "game_over",
                "payload": payload,
            },
        )

    async def handle_move(self, data, game, user, player_white_id, player_black_id):
        if not user.is_authenticated:
            await self.send_json(
                {
                    "type": "permission_denied",
                    "payload": {"reason": "Authentication required to make moves."},
                }
            )
            return

        pending_quiz = None
        if user.is_authenticated:
            pending_quiz = await database_sync_to_async(
                lambda: Move.objects.filter(
                    game=game, player=user, quiz_required=True, quiz_correct=None
                ).first()
            )()
        if pending_quiz:
            await self.send_json(
                {
                    "type": "quiz_required",
                    "payload": {
                        "question": "You must answer the quiz for your last capture before moving again.",
                        "choices": [],
                        "move_number": pending_quiz.move_number,
                    },
                }
            )
            return
        move_data = data.get("payload", {})
        fen = await get_fen(game)
        board = chess.Board(fen if fen else STARTING_FEN)
        from_square = move_data.get("from_square")
        to_square = move_data.get("to_square")
        promotion = move_data.get("promotion", "")
        is_pawn = False
        if from_square and board.piece_at(chess.parse_square(from_square)):
            is_pawn = (
                board.piece_at(chess.parse_square(from_square)).piece_type == chess.PAWN
            )
        is_promotion_rank = False
        if is_pawn and to_square:
            rank = int(to_square[1])
            if (board.turn and rank == 8) or (not board.turn and rank == 1):
                is_promotion_rank = True
        move_uci = from_square + to_square
        if is_pawn and is_promotion_rank and promotion:
            move_uci += promotion
        move = chess.Move.from_uci(move_uci)
        piece = (
            board.piece_at(chess.parse_square(from_square)).symbol().lower()
            if board.piece_at(chess.parse_square(from_square))
            else ""
        )
        captured_piece = (
            board.piece_at(chess.parse_square(to_square)).symbol().lower()
            if board.piece_at(chess.parse_square(to_square))
            else ""
        )
        move_data["piece"] = piece
        move_data["captured_piece"] = captured_piece
        move_number = await database_sync_to_async(lambda: game.moves.count() + 1)()
        move_data["move_number"] = move_number
        turn = board.turn

        is_white_turn = turn
        is_black_turn = not turn

        user_should_move = False

        if is_white_turn and user.id == player_white_id:
            user_should_move = True
        elif is_black_turn:
            if user.id == player_black_id:
                user_should_move = True
            elif player_black_id is None and not getattr(game, "is_vs_ai", False):
                user_should_move = True
                logger.info(f"User {user.username} playing as black (slot was empty)")

        if not user_should_move:
            await self.send_json(
                {"type": "move_invalid", "payload": {"reason": "It's not your turn."}}
            )
            return
        logger.info(
            f"Move attempt: from={from_square}, to={to_square}, promotion={promotion}, move_uci={move_uci}, legal={move in board.legal_moves}, turn={board.turn}, user_id={user.id}, player_white_id={player_white_id}, player_black_id={player_black_id}"
        )
        if move not in board.legal_moves:
            logger.error(
                f"Illegal move attempted: {move_uci} on FEN {board.fen()} (promotion={promotion})"
            )
            await self.send_json(
                {"type": "move_invalid", "payload": {"reason": "Illegal move"}}
            )
            return
        board.push(move)
        logger.info(f"After move: FEN={board.fen()}")
        new_fen = board.fen()
        await update_fen(game, new_fen)
        game.fen = new_fen
        move_data["fen_after"] = new_fen
        quiz_required = False
        quiz_piece_types = [chess.QUEEN, chess.ROOK, chess.BISHOP]
        captured_piece_type = None
        if captured_piece:
            if captured_piece == "q":
                captured_piece_type = chess.QUEEN
            elif captured_piece == "r":
                captured_piece_type = chess.ROOK
            elif captured_piece == "b":
                captured_piece_type = chess.BISHOP
        if captured_piece_type in quiz_piece_types:
            quiz_required = True
        if quiz_required:
            subjects = getattr(game, "subjects", ["math"])
            subject = subjects[0] if isinstance(subjects, list) and subjects else "math"
            quiz_question = await get_quiz_question(game, subject)
            if not user.is_authenticated:
                await self.send_json(
                    {
                        "type": "permission_denied",
                        "payload": {"reason": "Authentication required to make moves."},
                    }
                )
                return
            move_obj = await create_move(game, user, move_data, quiz_required=True)
            move_obj.quiz_timestamp = time.time()
            move_obj.quiz_data = quiz_question
            move_obj.fen_before = board.fen()
            await database_sync_to_async(move_obj.save)()
            await self.send_json(
                {
                    "type": "quiz_required",
                    "payload": {
                        "question": quiz_question.get(
                            "question", "Dummy question: What is 2+2?"
                        ),
                        "choices": quiz_question.get(
                            "choices", ["A: 3", "B: 4", "C: 5", "D: 6"]
                        ),
                        "move_number": move_data["move_number"],
                        "subject": subject,
                    },
                }
            )
            return
        if not user.is_authenticated:
            await self.send_json(
                {
                    "type": "permission_denied",
                    "payload": {"reason": "Authentication required to make moves."},
                }
            )
            return
        move_obj = await create_move(game, user, move_data, quiz_required=False)
        try:
            board_score = evaluate_board(board)
        except Exception:
            board_score = None
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "move",
                "payload": {
                    "from_square": move_data["from_square"],
                    "to_square": move_data["to_square"],
                    "piece": piece,
                    "move_number": move_data.get("move_number", 0),
                    "fen_after": move_data.get("fen_after"),
                    "captured_piece": captured_piece,
                    "uuid": str(move_obj.uuid),
                    "score": board_score,
                },
            },
        )
        logger.warning(board.fen())
        if board.is_checkmate():
            winner = "white" if not board.turn else "black"
            game.status = "finished"
            game.result = f"{winner}_win_by_checkmate"
            await database_sync_to_async(game.save)()
            elo_change = await self.update_elo(game, winner=winner)
            logger.info(f"Game ended by checkmate. Winner: {winner}")
            payload = {"reason": "checkmate", "winner": winner}
            if elo_change:
                payload["elo_change"] = elo_change
            await sync_to_async(analyze_game_task.delay)(game.id)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "game_over",
                    "payload": payload,
                },
            )
        elif (
            board.is_stalemate()
            or board.is_insufficient_material()
            or board.can_claim_fifty_moves()
            or board.can_claim_threefold_repetition()
        ):
            game.status = "finished"
            game.result = "draw"
            await database_sync_to_async(game.save)()
            elo_change = await self.update_elo(game, draw=True)
            logger.info(f"Game ended in draw.")
            payload = {"reason": "draw", "winner": None}
            if elo_change:
                payload["elo_change"] = elo_change
            await sync_to_async(analyze_game_task.delay)(game.id)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "game_over",
                    "payload": payload,
                },
            )
        await self.send_fen_and_game(game)
        if (
            getattr(game, "is_vs_ai", False)
            and getattr(game, "status", None) == "active"
        ):
            logger.info(
                f"Triggering AI move for game {game.id} (vs AI, status={game.status})"
            )
            await sync_to_async(run_ai_move_task.delay)(game.id)
            logger.info(f"AI move task dispatched for game {game.id}")

        redis = get_redis()
        block_key = f"game:{game.code}:blocked_moves:{user.id}"
        move_str = f"{from_square}{to_square}"
        is_blocked = await redis.sismember(block_key, move_str)
        if is_blocked:
            await self.send_json(
                {
                    "type": "move_invalid",
                    "payload": {
                        "reason": "You cannot repeat this move this round after failing the quiz."
                    },
                }
            )
            return

    async def handle_quiz_answer(self, data, game):
        answer = data["payload"].get("answer")
        move_number = data["payload"].get("move_number")
        logger.info(f"Quiz answer received: {answer} for move_number: {move_number}")
        if self.quiz_answer_future and not self.quiz_answer_future.done():
            logger.debug("Setting quiz_answer_future result")
            self.quiz_answer_future.set_result((answer, move_number))

        fen = await get_fen(game)
        board = chess.Board(fen if fen else STARTING_FEN)
        move = await get_pending_quiz_move(game, move_number)
        if move and move.quiz_required and move.quiz_correct is None:
            if hasattr(move, "quiz_timestamp") and move.quiz_timestamp:
                if time.time() - move.quiz_timestamp > 30:
                    move.quiz_correct = False
                    await database_sync_to_async(move.save)()

                    previous_fen = None
                    if move.move_number > 1:
                        previous_move = await database_sync_to_async(
                            lambda: game.moves.filter(
                                move_number=move.move_number - 1
                            ).first()
                        )()
                        if previous_move:
                            previous_fen = previous_move.fen_after
                    else:
                        previous_fen = STARTING_FEN

                    if previous_fen:
                        await update_fen(game, previous_fen)
                        game.fen = previous_fen
                        await database_sync_to_async(game.save)()

                    await self.send_json(
                        {
                            "type": "quiz_failed",
                            "payload": {
                                "reason": "Quiz timed out. Try another move.",
                                "fen": previous_fen or game.fen,
                            },
                        }
                    )

                    await self.send_fen_and_game(game)
                    return

            correct_answer = None
            if move.quiz_data and isinstance(move.quiz_data, dict):
                correct_answer = move.quiz_data.get("correct", None)
            if not correct_answer:
                subjects = getattr(game, "subjects", ["math"])
                subject = (
                    subjects[0] if isinstance(subjects, list) and subjects else "math"
                )
                current_quiz = await get_quiz_question(game, subject)
                correct_answer = current_quiz.get("correct", "A")
            correct = answer == correct_answer

            if correct:
                try:
                    logger.info(
                        f"Quiz correct, applying move for move_number: {move_number}"
                    )
                    board = chess.Board(move.fen_before or game.fen)
                    new_fen = board.fen()
                    await update_fen(game, new_fen)
                    move.quiz_correct = True
                    await database_sync_to_async(move.save)()
                    # Patch for correct answer
                    player = await database_sync_to_async(lambda: move.player)()
                    if player:
                        player.quiz_attempted += 1
                        player.quiz_correct += 1
                        await database_sync_to_async(player.save)()
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            "type": "move",
                            "payload": {
                                "from_square": move.from_square,
                                "to_square": move.to_square,
                                "piece": move.piece,
                                "move_number": move.move_number,
                                "fen_after": new_fen,
                                "captured_piece": move.captured_piece,
                                "uuid": str(move.uuid),
                            },
                        },
                    )
                    # Trigger AI move if vs AI and game is still active
                    if (
                        getattr(game, "is_vs_ai", False)
                        and getattr(game, "status", None) == "active"
                    ):
                        logger.info(
                            f"Triggering AI move for game {game.id} (vs AI, status={game.status}) after quiz answer"
                        )
                        await sync_to_async(run_ai_move_task.delay)(game.id)
                        logger.info(
                            f"AI move task dispatched for game {game.id} after quiz answer"
                        )
                except Exception as exc:
                    logger.error(f"Error applying move after quiz: {exc}")
                    await self.send_json(
                        {
                            "type": "move_invalid",
                            "payload": {
                                "reason": "Move could not be applied after quiz"
                            },
                        }
                    )
            else:
                logger.info(f"Quiz incorrect for move_number: {move_number}")
                redis = get_redis()
                block_key = f"game:{game.code}:blocked_moves:{self.scope['user'].id}"
                move_str = f"{move.from_square}{move.to_square}"
                await redis.sadd(block_key, move_str)
                await redis.expire(
                    block_key, 600
                )  # Block for 10 minutes (or until round ends)

                move.quiz_correct = False
                await database_sync_to_async(move.save)()
                # Patch for incorrect answer
                player = await database_sync_to_async(lambda: move.player)()
                if player:
                    player.quiz_attempted += 1
                    await database_sync_to_async(player.save)()
                await database_sync_to_async(move.delete)()
                previous_fen = None
                if move.move_number > 1:
                    previous_move = await database_sync_to_async(
                        lambda: game.moves.filter(
                            move_number=move.move_number - 1
                        ).last()
                    )()
                    if previous_move:
                        previous_fen = previous_move.fen_after
                else:
                    previous_fen = STARTING_FEN
                if previous_fen:
                    await update_fen(game, previous_fen)
                    game.fen = previous_fen
                    await database_sync_to_async(game.save)()
                await self.send_json(
                    {
                        "type": "quiz_failed",
                        "payload": {
                            "reason": "Quiz answer incorrect. Try another move.",
                            "fen": previous_fen or game.fen,
                            "blocked_move": move_str,
                        },
                    }
                )
                await self.send_fen_and_game(game)

    async def game_message(self, event):
        payload = event.get("payload", {})
        msg_type = event.get("type")
        await self.send(text_data=json.dumps({"type": msg_type, "payload": payload}))

    async def handle_quiz(self, game, move, question, correct_option):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "quiz_question",
                    "question": question,
                }
            )
        )
        self.quiz_answer_future = asyncio.get_event_loop().create_future()
        try:
            answer, move_number = await asyncio.wait_for(
                self.quiz_answer_future, timeout=30
            )
            correct = answer == correct_option
            if correct:
                await self.send(
                    text_data=json.dumps(
                        {"type": "quiz_passed", "move_number": move_number}
                    )
                )
                try:
                    uci_move = chess.Move.from_uci(move.from_square + move.to_square)
                    board = chess.Board(await get_fen(game))
                    board.push(uci_move)
                    new_fen = board.fen()
                    await update_fen(game, new_fen)
                    move.quiz_correct = True
                    await database_sync_to_async(move.save)()
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            "type": "move",
                            "payload": {
                                "from_square": move.from_square,
                                "to_square": move.to_square,
                                "piece": move.piece,
                                "move_number": move.move_number,
                                "fen_after": new_fen,
                                "captured_piece": move.captured_piece,
                                "uuid": str(move.uuid),
                            },
                        },
                    )
                except Exception:
                    await self.send(
                        text_data=json.dumps(
                            {
                                "type": "move_invalid",
                                "payload": {
                                    "reason": "Move could not be applied after quiz"
                                },
                            }
                        )
                    )
            else:
                await self.send(
                    text_data=json.dumps(
                        {"type": "quiz_failed", "move_number": move_number}
                    )
                )
                move.quiz_correct = False
                await database_sync_to_async(move.save)()

                previous_fen = None
                if move.move_number > 1:
                    previous_move = await database_sync_to_async(
                        lambda: game.moves.filter(
                            move_number=move.move_number - 1
                        ).first()
                    )()
                    if previous_move:
                        previous_fen = previous_move.fen_after
                else:
                    previous_fen = STARTING_FEN

                if previous_fen:
                    await update_fen(game, previous_fen)
                    game.fen = previous_fen
                    await database_sync_to_async(game.save)()

                await self.send(
                    text_data=json.dumps(
                        {
                            "type": "quiz_failed",
                            "payload": {
                                "reason": "Quiz answer incorrect. Try another move.",
                                "fen": previous_fen or game.fen,
                            },
                        }
                    )
                )

                await self.send_fen_and_game(game)
        except asyncio.TimeoutError:
            await self.send(text_data=json.dumps({"type": "quiz_timeout"}))
            move.quiz_correct = False
            await database_sync_to_async(move.save)()

            previous_fen = None
            if move.move_number > 1:
                previous_move = await database_sync_to_async(
                    lambda: game.moves.filter(move_number=move.move_number - 1).first()
                )()
                if previous_move:
                    previous_fen = previous_move.fen_after
            else:
                previous_fen = STARTING_FEN

            if previous_fen:
                await update_fen(game, previous_fen)
                game.fen = previous_fen
                await database_sync_to_async(game.save)()

            await self.send(
                text_data=json.dumps(
                    {
                        "type": "quiz_failed",
                        "payload": {
                            "reason": "Quiz answer timeout. Try another move.",
                            "fen": previous_fen or game.fen,
                        },
                    }
                )
            )

            await self.send_fen_and_game(game)
        finally:
            self.quiz_answer_future = None

    async def send_fen_and_game(self, game):
        game_data = await serialize_game(game)
        fen = game_data.get("fen") or game.fen
        score = None
        try:
            board = chess.Board(fen)
            score = evaluate_board(board)
        except Exception:
            score = None
        game_data["score"] = score
        await self.send_json(
            {
                "type": "game_update",
                "payload": game_data,
            }
        )

    async def send_move(self, game, move_payload):
        fen = await get_fen(game)
        await self.send(
            text_data=json.dumps(
                {
                    "type": "move",
                    "payload": move_payload,
                    "fen": fen,
                }
            )
        )

    async def fen_update(self, event):
        await self.send_json(
            {"type": "fen_update", "payload": event.get("payload", {})}
        )

    async def move(self, event):
        await self.send_json({"type": "move", "payload": event.get("payload", {})})

    async def game_over(self, event):
        await self.send_json({"type": "game_over", "payload": event.get("payload", {})})

    async def draw_offer(self, event):
        await self.send_json(
            {"type": "draw_offer", "payload": event.get("payload", {})}
        )

    async def game_update(self, event):
        await self.send_json(
            {"type": "game_update", "payload": event.get("payload", {})}
        )

    async def handle_join_as_black(self, user, game, player_white_id, player_black_id):
        """Handle a user joining as the black player."""
        if not user.is_authenticated:
            await self.send_json(
                {"type": "error", "payload": {"reason": "Authentication required."}}
            )
            return

        if player_black_id is not None:
            await self.send_json(
                {
                    "type": "error",
                    "payload": {"reason": "Black player slot is already taken."},
                }
            )
            return

        if getattr(game, "is_vs_ai", False):
            await self.send_json(
                {
                    "type": "error",
                    "payload": {"reason": "Cannot join as black in an AI game."},
                }
            )
            return

        if user.id == player_white_id:
            await self.send_json(
                {
                    "type": "error",
                    "payload": {"reason": "You are already the white player."},
                }
            )
            return

        try:
            game.player_black = user
            await database_sync_to_async(game.save)()

            logger.info(
                f"User {user.username} assigned as black player for game {game.code}"
            )

            await self.send_json(
                {
                    "type": "joined_as_black",
                    "payload": {
                        "message": "Successfully joined as black player",
                        "game_code": game.code,
                    },
                }
            )

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "black_player_joined",
                    "payload": {"user": user.username, "game_code": game.code},
                },
            )

            game_data = await serialize_game(game)
            fen = game_data.get("fen") or game.fen
            score = None
            try:
                board = chess.Board(fen)
                score = evaluate_board(board)
            except Exception:
                score = None
            game_data["score"] = score

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "game_update",
                    "payload": game_data,
                },
            )

        except Exception as e:
            logger.error(f"Error assigning black player: {e}")
            await self.send_json(
                {
                    "type": "error",
                    "payload": {"reason": "Failed to join as black player."},
                }
            )

    async def player_joined(self, event):
        await self.send_json(
            {"type": "player_joined", "payload": event.get("payload", {})}
        )

    async def spectator_joined(self, event):
        await self.send_json(
            {"type": "spectator_joined", "payload": event.get("payload", {})}
        )

    async def spectator_left(self, event):
        await self.send_json(
            {"type": "spectator_left", "payload": event.get("payload", {})}
        )

    async def black_player_joined(self, event):
        await self.send_json(
            {"type": "black_player_joined", "payload": event.get("payload", {})}
        )


async def update_game_cache_and_broadcast(game, channel_layer, room_group_name):
    redis = get_redis()

    @database_sync_to_async
    def serialize_game(game):
        from django.core.serializers.json import DjangoJSONEncoder
        import json

        serializer = GameSerializer(game)
        data = serializer.data

        json_str = json.dumps(data, cls=DjangoJSONEncoder)
        return json.loads(json_str)

    game_data = await serialize_game(game)
    await redis.set(f"game:{game.code}:data", json.dumps(game_data))
    await channel_layer.group_send(
        room_group_name,
        {
            "type": "game_update",
            "payload": game_data,
        },
    )
