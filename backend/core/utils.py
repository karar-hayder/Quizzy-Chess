import logging
import math

import chess
from channels.db import database_sync_to_async
from django.conf import settings

logger = logging.getLogger(__name__)

import redis  # sync client
import redis.asyncio as aioredis

REDIS_URL = getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
_redis_pool = aioredis.ConnectionPool.from_url(
    REDIS_URL, encoding="utf-8", decode_responses=True
)
_redis = aioredis.Redis(connection_pool=_redis_pool)


def get_redis():
    return aioredis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)


def get_sync_redis():
    return redis.from_url(REDIS_URL, decode_responses=True)


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


def update_fen_sync(game, fen):
    """Synchronous version of update_fen for use in Celery tasks."""
    if not is_valid_fen(fen):
        logger.error(f"Attempted to save invalid FEN: {fen}")
        raise ValueError(f"Invalid FEN attempted to be saved: {fen}")

    game.fen = fen
    game.save()

    redis = get_sync_redis()
    redis.set(f"game:{game.code}:fen", fen)


def evaluate_board(board: chess.Board) -> float:
    try:
        import platform
        from django.conf import settings

        if platform.system() == "Linux":
            stockfish_path = (
                settings.BASE_DIR
                / "stockfish-linux"
                / "stockfish"
                / "stockfish-ubuntu-x86-64-avx2"
            )
        else:
            stockfish_path = (
                settings.BASE_DIR
                / "stockfish-win"
                / "stockfish-windows-x86-64-avx2.exe"
            )
        if not stockfish_path.exists():
            logger.warning(
                f"Stockfish not found at {stockfish_path}, using fallback evaluation"
            )
            return _fallback_evaluation(board)
        import chess.engine

        with chess.engine.SimpleEngine.popen_uci(str(stockfish_path)) as engine:
            engine.configure({"Threads": 1, "Hash": 16})
            info = engine.analyse(board, chess.engine.Limit(depth=10, time=0.1))

            if "score" in info and info["score"] is not None:
                score = info["score"].white().score(mate_score=10000)
                if score is not None:
                    return score / 100.0  # Convert to pawns
                else:
                    return 10.0 if info["score"].white().mate() > 0 else -10.0
            else:
                return _fallback_evaluation(board)

    except Exception as e:
        logger.warning(f"Stockfish evaluation failed: {e}, using fallback")
        return _fallback_evaluation(board)


def _fallback_evaluation(board: chess.Board) -> float:
    values = {
        chess.PAWN: 100,
        chess.KNIGHT: 320,
        chess.BISHOP: 330,
        chess.ROOK: 500,
        chess.QUEEN: 900,
        chess.KING: 0,
    }

    score = 0
    for piece_type in values:
        score += len(board.pieces(piece_type, chess.WHITE)) * values[piece_type]
        score -= len(board.pieces(piece_type, chess.BLACK)) * values[piece_type]
    center = [chess.E4, chess.D4, chess.E5, chess.D5]
    for sq in center:
        piece = board.piece_at(sq)
        if piece:
            if piece.color == chess.WHITE:
                score += 20
            else:
                score -= 20
    score += (
        5 * len(list(board.legal_moves))
        if board.turn == chess.WHITE
        else -5 * len(list(board.legal_moves))
    )
    return score / 100.0


def get_gradual_k(games_played, rating, k_max=40, k_min=10, decay_rate=0.03):
    k_experience = k_min + (k_max - k_min) * math.exp(-decay_rate * games_played)
    rating_factor = max(0.5, 1 - (rating - 1000) / 2000)  # Caps at 0.5 for high ratings

    k = k_experience * rating_factor
    return round(k, 2)


def calculate_elo(rating_a, rating_b, score_a, games_a, games_b):
    expected_a = 1 / (1 + 10 ** ((rating_b - rating_a) / 400))
    expected_b = 1 - expected_a
    score_b = 1 - score_a

    k_a = get_gradual_k(games_a, rating_a)
    k_b = get_gradual_k(games_b, rating_b)

    new_a = round(rating_a + k_a * (score_a - expected_a))
    new_b = round(rating_b + k_b * (score_b - expected_b))

    return new_a, new_b


from asgiref.sync import async_to_sync


def end_game_and_update_elo(game, winner=None, draw=False):
    if draw:
        game.status = "finished"
        game.result = "draw"
    elif winner:
        game.status = "finished"
        game.result = f"{winner}_win_by_timeout"
    else:
        game.status = "finished"
        game.result = "draw_by_timeout"
    game.save()
    try:
        from core.consumers import GameConsumer

        update_elo = getattr(GameConsumer, "update_elo", None)
        if update_elo:
            async_to_sync(update_elo)(None, game, winner=winner, draw=draw)
    except Exception as e:
        logger.error(f"Error updating Elo for game {game.id}: {e}")
    try:
        from core.tasks import analyze_game_task

        analyze_game_task.delay(game.id)
    except Exception as e:
        logger.error(f"Error triggering analysis for game {game.id}: {e}")
