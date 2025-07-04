import asyncio
import json
import logging
import os
import platform
from datetime import datetime, timedelta
from pathlib import Path
import re

import chess
import chess.engine
import redis
from asgiref.sync import async_to_sync
from celery import shared_task
from channels.layers import get_channel_layer
from django.conf import settings
from django.utils import timezone

from backend.utils import send_message
from core.ai import get_ai_move, minimax
from core.models import Game, GameAnalysis, Move
from core.serializers import GameSerializer
from core.utils import (
    end_game_and_update_elo,
    get_redis,
    get_sync_redis,
    update_fen,
    update_fen_sync,
)
from users.models import CustomUser

logger = logging.getLogger(__name__)
if platform.system() == "Linux":
    STOCKFISH_PATH = (
        settings.BASE_DIR
        / "stockfish-linux"
        / "stockfish"
        / "stockfish-ubuntu-x86-64-avx2"
    )
else:
    STOCKFISH_PATH = (
        settings.BASE_DIR / "stockfish-win" / "stockfish-windows-x86-64-avx2.exe"
    )
redis = get_redis()

QUIZ_PROMPT_MULTI = """
I need you to generate quiz questions for a chess-based educational game. For each subject in the following list: {Subjects}, generate {N} multiple-choice questions (A-D) suitable for a player of rank {Player_Rank}. Return a JSON object where each key is the subject and the value is a list of questions, each with 'question', 'choices', 'correct', and 'explanation'.
"""
QUIZ_PROMPT_SINGLE = """
I need you to generate {N} quiz questions for a chess-based educational game. The questions should be about {Subject} and suitable for a player of rank {Player_Rank}. Each question should be multiple-choice (A-D) with 'question', 'choices', 'correct', and 'explanation'. Return as a JSON list.
"""


def extract_json_from_text(text):
    match = re.search(r"({[\s\S]*})", text)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception as e:
            pass
    match = re.search(r"(\[[\s\S]*\])", text)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception as e:
            pass
    return None


@shared_task(queue="quiz")
def generate_quizs_in_advance(game_id, N=5, subject_list=None):
    import json

    from backend.utils import send_message
    from core.utils import get_redis

    try:
        game = Game.objects.get(id=game_id)
        if subject_list is None:
            subject_list = ["Math"]
        if isinstance(subject_list, str):
            subject_list = [subject_list]
        r = get_sync_redis()
        avg_elo = 1200
        if game.player_white and game.player_black:
            avg_elo = int(
                (
                    getattr(game.player_white, "elo", 1200)
                    + getattr(game.player_black, "elo", 1200)
                )
                / 2
            )
        elif game.player_white:
            avg_elo = getattr(game.player_white, "elo", 1200)
        elif game.player_black:
            avg_elo = getattr(game.player_black, "elo", 1200)
        if avg_elo < 1200:
            player_rank = "Beginner"
        elif avg_elo <= 1600:
            player_rank = "Intermediate"
        else:
            player_rank = "Advanced"
        results = {}
        if len(subject_list) == 1:
            subject = subject_list[0]
            prompt = QUIZ_PROMPT_SINGLE.format(
                N=N, Player_Rank=player_rank, Subject=subject
            )
            logger.info(f"Quiz prompt (single): {prompt}")
            quiz_content = send_message(message="", prompt=prompt)
            logger.info(
                f"Generated quiz questions for game {game_id}, subject {subject}: {quiz_content}"
            )
            redis_key = f"game:{game.code}:quizzes:{subject.lower()}"
            try:
                quiz_data = json.loads(quiz_content)
            except Exception as e:
                logger.error(
                    f"Failed to parse LLM response as JSON: {e}\nResponse: {quiz_content}"
                )
                quiz_data = extract_json_from_text(quiz_content)
                if quiz_data is None:
                    logger.error(
                        f"Could not extract valid JSON from LLM response for subject {subject}."
                    )
            if quiz_data:
                r.set(redis_key, json.dumps(quiz_data))
                logger.info(f"Saved quiz questions to Redis key {redis_key}")
                results[subject] = quiz_data
            else:
                logger.warning(
                    f"No valid quiz data for subject {subject} in LLM response."
                )
                results[subject] = None
        else:
            prompt = QUIZ_PROMPT_MULTI.format(
                N=N, Player_Rank=player_rank, Subjects=subject_list
            )
            logger.info(f"Quiz prompt (multi): {prompt}")
            quiz_content = send_message(message="", prompt=prompt)
            logger.info(
                f"Generated quiz questions for game {game_id}, subjects {subject_list}: {quiz_content}"
            )
            try:
                quiz_data = json.loads(quiz_content)
            except Exception as e:
                logger.error(
                    f"Failed to parse LLM response as JSON: {e}\nResponse: {quiz_content}"
                )
                quiz_data = extract_json_from_text(quiz_content)
                if quiz_data is None:
                    logger.error(
                        f"Could not extract valid JSON from LLM response for subjects {subject_list}."
                    )
                    quiz_data = {}
            for subject in subject_list:
                subject_questions = None
                if isinstance(quiz_data, dict):
                    subject_questions = quiz_data.get(subject)
                if not subject_questions:
                    logger.warning(
                        f"No questions found for subject {subject} in LLM response."
                    )
                else:
                    redis_key = f"game:{game.code}:quizzes:{subject.lower()}"
                    r.set(redis_key, json.dumps(subject_questions))
                    logger.info(f"Saved quiz questions to Redis key {redis_key}")
                results[subject] = subject_questions
        return results
    except Exception as e:
        logger.error(f"Error generating quiz questions for game {game_id}: {e}")
        return None


@shared_task
def update_user_quiz_stats(user_id, correct):
    """Update quiz stats for a user after a quiz attempt."""
    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        logger.error(f"User not found for quiz stats update: {user_id}")
        return
    user.quiz_attempted += 1
    if correct:
        user.quiz_correct += 1
    user.save()
    logger.info(
        f"Updated quiz stats for user {user_id}: attempted={user.quiz_attempted}, correct={user.quiz_correct}"
    )


@shared_task
def update_game_cache_and_broadcast_task(game_id, game_code):
    try:
        r = get_sync_redis()
        game = Game.objects.get(id=game_id)
        game_data = GameSerializer(game).data
        r.set(f"game:{game_code}:data", json.dumps(game_data))
        channel_layer = get_channel_layer()
        room_group_name = f"game_{game_code}"
        async_to_sync(channel_layer.group_send)(
            room_group_name,
            {
                "type": "game_update",
                "payload": game_data,
            },
        )
        logger.info(f"Updated cache and broadcasted for game {game_id}")
    except Exception as e:
        logger.error(f"Error updating cache/broadcast for game {game_id}: {e}")


@shared_task
def run_ai_move_task(game_id):
    """Run the AI move for a vs AI game, update state, and broadcast."""
    logger.info(f"AI move task triggered for game_id={game_id}")
    try:
        game = Game.objects.get(id=game_id)
    except Game.DoesNotExist:
        logger.error(f"Game not found for AI move: {game_id}")
        return
    if not game.is_vs_ai:
        logger.info(f"Game {game_id} is not vs AI. Skipping AI move.")
        return
    fen = game.fen
    board = chess.Board(fen)
    if game.ai_difficulty == "easy":
        _, move = minimax(board, 2, board.turn == chess.WHITE)
        if not move:
            logger.error(f"No AI move found (minimax) for game_id={game_id}, fen={fen}")
            return
    else:
        if game.ai_difficulty == "hard":
            ai_elo = 1800
        else:
            ai_elo = 1400
        try:
            with chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH) as engine:
                engine.configure({"UCI_LimitStrength": True, "UCI_Elo": ai_elo})
                result = engine.play(board, chess.engine.Limit(time=0.5))
                move = result.move
                if move not in board.legal_moves:
                    logger.warning(
                        f"AI move {move.uci()} not legal for game_id={game_id}, fen={fen}. Picking random legal move."
                    )
                    legal_moves = list(board.legal_moves)
                    if not legal_moves:
                        logger.error(
                            f"No legal moves available for game_id={game_id}, fen={fen}"
                        )
                        return
                    move = legal_moves[0]
        except Exception as e:
            logger.error(f"Error running Stockfish for AI move in game {game_id}: {e}")
            return
    piece = (
        board.piece_at(move.from_square).symbol().lower()
        if board.piece_at(move.from_square)
        else ""
    )
    captured_piece = (
        board.piece_at(move.to_square).symbol().lower()
        if board.piece_at(move.to_square)
        else ""
    )
    board.push(move)
    new_fen = board.fen()
    game_ended = False
    game_end_payload = None

    if board.is_checkmate():
        winner = "white" if not board.turn else "black"
        game.status = "finished"
        game.result = f"{winner}_win_by_checkmate"
        game.save()
        game_ended = True
        game_end_payload = {"reason": "checkmate", "winner": winner}
        logger.info(f"Game ended by checkmate after AI move. Winner: {winner}")
        analyze_game_task.delay(game.id)
    elif (
        board.is_stalemate()
        or board.is_insufficient_material()
        or board.can_claim_fifty_moves()
        or board.can_claim_threefold_repetition()
    ):
        game.status = "finished"
        game.result = "draw"
        game.save()
        game_ended = True
        game_end_payload = {"reason": "draw", "winner": None}
        logger.info(f"Game ended in draw after AI move.")
        analyze_game_task.delay(game.id)

    try:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            asyncio.set_event_loop(asyncio.new_event_loop())
        update_fen_sync(game, new_fen)
    except Exception as e:
        logger.error(f"Error updating FEN for AI move in game {game_id}: {e}")
        return
    move_obj = Move.objects.create(
        game=game,
        player=None,  # AI has no user
        from_square=chess.square_name(move.from_square),
        to_square=chess.square_name(move.to_square),
        piece=piece,
        captured_piece=captured_piece,
        move_number=game.moves.count() + 1,
        fen_after=new_fen,
        quiz_required=False,
        quiz_correct=None,
    )
    try:
        channel_layer = get_channel_layer()
        room_group_name = f"game_{game.code}"
        async_to_sync(channel_layer.group_send)(
            room_group_name,
            {
                "type": "move",
                "payload": {
                    "from_square": chess.square_name(move.from_square),
                    "to_square": chess.square_name(move.to_square),
                    "piece": piece,
                    "move_number": move_obj.move_number,
                    "fen_after": new_fen,
                    "captured_piece": captured_piece,
                    "uuid": str(move_obj.uuid),
                },
            },
        )
        if game_ended and game_end_payload:
            async_to_sync(channel_layer.group_send)(
                room_group_name,
                {
                    "type": "game_over",
                    "payload": game_end_payload,
                },
            )

        logger.info(f"AI move task completed for game_id={game_id}, move={move}")
        update_game_cache_and_broadcast_task.delay(game.id, game.code)
    except Exception as e:
        logger.error(f"Error broadcasting AI move for game {game_id}: {e}")


@shared_task(queue="analysis")
def analyze_game_task(game_id):
    """Analyze a finished game using Stockfish, storing overall and per-move analysis."""
    logger.info(f"Starting analysis for game {game_id}")
    try:
        game = Game.objects.get(id=game_id)
        game.analysis_status = "in_progress"
        game.save(update_fields=["analysis_status"])
    except Game.DoesNotExist:
        logger.error(f"Game not found for analysis: {game_id}")
        return

    moves = list(game.moves.order_by("move_number"))
    logger.info(f"Found {len(moves)} moves to analyze for game {game_id}")

    total_moves = len(moves)
    if total_moves == 0:
        logger.warning(f"No moves found for game {game_id}, skipping analysis")
        game.analysis_status = "failed"
        game.save(update_fields=["analysis_status"])
        return

    per_move = []
    blunders = 0
    inaccuracies = 0
    best_moves = 0

    try:
        with chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH) as engine:
            engine.configure({"Threads": 1, "Hash": 128})
            board = chess.Board()
            for i, move_obj in enumerate(moves):
                try:
                    if i > 0 and moves[i - 1].fen_after:
                        try:
                            board = chess.Board(moves[i - 1].fen_after)
                        except Exception as e:
                            logger.error(
                                f"Invalid FEN from previous move: {moves[i-1].fen_after}, using reconstructed position. Error: {e}"
                            )
                            board = chess.Board()
                            for j in range(i):
                                try:
                                    prev_move = chess.Move.from_uci(
                                        moves[j].from_square + moves[j].to_square
                                    )
                                    board.push(prev_move)
                                except Exception as e:
                                    logger.error(f"Error reconstructing move {j}: {e}")
                                    break
                    else:
                        board = chess.Board()

                    logger.debug(
                        f"Analyzing move {i+1}/{total_moves}: {move_obj.from_square}{move_obj.to_square} at FEN: {board.fen()}"
                    )
                    info = engine.analyse(board, chess.engine.Limit(depth=12))
                    pv = info.get("pv", [])
                    best_move = pv[0] if pv else None
                    evaluation = (
                        info["score"].white().score(mate_score=10000)
                        if "score" in info
                        else None
                    )
                    try:
                        played_move = chess.Move.from_uci(
                            move_obj.from_square + move_obj.to_square
                        )
                    except Exception as e:
                        logger.error(
                            f"Invalid move UCI {move_obj.from_square + move_obj.to_square}: {e}"
                        )
                        continue

                    comment = "OK"
                    if best_move:
                        try:
                            if played_move == best_move:
                                comment = "Best"
                                best_moves += 1
                            else:
                                try:
                                    board.push(best_move)
                                    best_eval = (
                                        engine.analyse(
                                            board, chess.engine.Limit(depth=12)
                                        )["score"]
                                        .white()
                                        .score(mate_score=10000)
                                    )
                                    board.pop()
                                except Exception as e:
                                    logger.error(
                                        f"Error pushing best_move {best_move} for FEN {board.fen()}: {e}"
                                    )
                                    best_eval = None
                                if best_eval is not None and evaluation is not None:
                                    diff = best_eval - evaluation
                                    if diff >= 100:
                                        comment = "Blunder"
                                        blunders += 1
                                    elif diff >= 30:
                                        comment = "Inaccuracy"
                                        inaccuracies += 1
                                    else:
                                        comment = "OK"
                        except chess.IllegalMoveError as e:
                            logger.error(
                                f"Illegal best_move {best_move} for FEN {board.fen()}: {e}"
                            )
                            comment = "Illegal best move"

                    per_move.append(
                        {
                            "move_number": move_obj.move_number,
                            "played": played_move.uci(),
                            "best": best_move.uci() if best_move else None,
                            "evaluation": evaluation,
                            "comment": comment,
                        }
                    )

                except Exception as move_exc:
                    logger.error(
                        f"Error analyzing move {move_obj.move_number} in game {game_id}: {move_exc}"
                    )
                    continue

    except Exception as e:
        logger.error(f"Game analysis failed for game {game_id}: {e}")
        game.analysis_status = "failed"
        game.save(update_fields=["analysis_status"])
        return
    accuracy_score = (
        (
            best_moves * 1.0
            + (total_moves - best_moves - blunders - inaccuracies) * 0.75
            + inaccuracies * 0.5
        )
        / total_moves
        if total_moves
        else 0
    )
    accuracy = accuracy_score

    overall = {
        "accuracy": accuracy,
        "blunders": blunders,
        "inaccuracies": inaccuracies,
        "total_moves": total_moves,
        "best_moves": best_moves,
    }

    logger.info(
        f"Analysis results for game {game_id}: accuracy={accuracy:.2f}, blunders={blunders}, inaccuracies={inaccuracies}"
    )

    try:
        GameAnalysis.objects.update_or_create(
            game=game,
            defaults={"overall": overall, "per_move": per_move},
        )
        game.analysis_status = "completed"
        game.save(update_fields=["analysis_status"])
        logger.info(f"Analysis complete for game {game_id}")
    except Exception as e:
        logger.error(f"Error saving analysis for game {game_id}: {e}")
        game.analysis_status = "failed"
        game.save(update_fields=["analysis_status"])


@shared_task(queue="maintenance")
def cleanup_expired_matchmaking_searches():
    """Clean up expired searches from the matchmaking queue."""
    try:
        from core.matchmaking import MatchmakingService
        import asyncio

        matchmaking_service = MatchmakingService()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(matchmaking_service.cleanup_expired_searches())
        finally:
            loop.close()
        logger.info("Cleaned up expired matchmaking searches")
    except Exception as e:
        logger.error(f"Error cleaning up expired matchmaking searches: {e}")


@shared_task(queue="maintenance")
def cleanup_stale_games():
    """
    Periodic task to:
    1. Delete games in 'waiting' status older than 30 minutes.
    2. End games in 'active' status where no move has been played in 2 hours, awarding win to last player to move.
    """
    logger.info("Running cleanup_stale_games task...")
    now = timezone.now()
    waiting_cutoff = now - timedelta(minutes=30)
    waiting_games = Game.objects.filter(status="waiting", created_at__lt=waiting_cutoff)
    count_waiting = waiting_games.count()
    waiting_games.delete()
    logger.info(f"Deleted {count_waiting} waiting games older than 30 minutes.")
    active_cutoff = now - timedelta(hours=2)
    active_games = Game.objects.filter(status="active")
    ended = 0
    for game in active_games:
        last_move = game.moves.order_by("-created_at").first()
        if last_move:
            last_move_time = last_move.created_at
        else:
            last_move_time = game.created_at
        if last_move_time < active_cutoff:
            if last_move and last_move.player:
                if last_move.player == game.player_white:
                    winner = "white"
                elif last_move.player == game.player_black:
                    winner = "black"
                else:
                    winner = None
            else:
                winner = None
            if winner:
                end_game_and_update_elo(game, winner=winner, draw=False)
            else:
                end_game_and_update_elo(game, winner=None, draw=True)
            ended += 1
    logger.info(f"Ended {ended} active games with no move in 2 hours.")


@shared_task(queue="analysis")
def queue_unanalyzed_games():
    """Find all finished games with analysis_status 'pending' or 'failed' and queue them for analysis."""
    logger.info("Checking for unanalyzed finished games...")
    games = Game.objects.filter(
        status="finished", analysis_status__in=["pending", "failed"]
    )
    game_count = games.count()
    logger.info(
        f"Found {game_count} finished games with pending/failed analysis status"
    )

    queued_count = 0
    for game in games:
        logger.info(
            f"Queuing analysis for game {game.id} (status={game.status}, analysis_status={game.analysis_status})"
        )
        game.analysis_status = "in_progress"
        game.save(update_fields=["analysis_status"])
        analyze_game_task.delay(game.id)
        queued_count += 1

    logger.info(f"Queued {queued_count} games for analysis.")
