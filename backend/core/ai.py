import random

import chess

from core.utils import evaluate_board

OPENING_BOOK = {
    "start": ["e2e4", "d2d4", "c2c4", "g1f3", "f2f4", "b1c3", "b2b3", "g2g3"],
    "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1": [
        "e7e5",
        "c7c5",
        "e7e6",
        "g8f6",
        "d7d5",
        "d7d6",
        "g7g6",
        "b8c6",
    ],
    "rnbqkbnr/pppppppp/8/8/3P4/8/PPP1PPPP/RNBQKBNR b KQkq - 0 1": [
        "d7d5",
        "g8f6",
        "e7e6",
        "c7c5",
        "c7c6",
        "e7e5",
    ],
    "rnbqkbnr/pppppppp/8/8/2P5/8/PP1PPPPP/RNBQKBNR b KQkq - 0 1": [
        "e7e5",
        "g8f6",
        "e7e6",
        "c7c5",
        "d7d5",
    ],
    "rnbqkbnr/pppppppp/8/8/8/5N2/PPPPPPPP/RNBQKB1R b KQkq - 1 1": [
        "d7d5",
        "g8f6",
        "c7c5",
        "e7e6",
        "b8c6",
    ],
    "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2": [
        "g1f3",
        "b1c3",
        "f1c4",
        "d2d4",
        "f1b5",
    ],
    "rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq c6 0 2": [
        "g1f3",
        "d2d4",
        "b1c3",
        "f1c4",
    ],
    "rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2": [
        "b8c6",
        "g8f6",
        "d7d6",
        "f8c5",
    ],
    "rnbqkbnr/ppp1pppp/3p4/8/2PP4/8/PP2PPPP/RNBQKBNR b KQkq - 0 2": [
        "e7e6",
        "c7c6",
        "g8f6",
        "d5c4",
    ],
}


def evaluate_board_easy(board):
    """
    Fast, simple evaluation for easy AI: material only (no position, no mobility).
    Returns positive for white, negative for black.
    """
    values = {
        chess.PAWN: 1,
        chess.KNIGHT: 3,
        chess.BISHOP: 3,
        chess.ROOK: 5,
        chess.QUEEN: 9,
        chess.KING: 0,
    }
    score = 0
    for piece_type in values:
        score += len(board.pieces(piece_type, chess.WHITE)) * values[piece_type]
        score -= len(board.pieces(piece_type, chess.BLACK)) * values[piece_type]
    return score


def minimax(
    board, depth, maximizing, alpha=float("-inf"), beta=float("inf"), eval_fn=None
):
    if eval_fn is None:
        eval_fn = evaluate_board_easy
    if depth == 0 or board.is_game_over():
        return eval_fn(board), None
    best_moves = []
    if maximizing:
        max_eval = float("-inf")
        for move in board.legal_moves:
            board.push(move)
            eval, _ = minimax(board, depth - 1, False, alpha, beta, eval_fn)
            board.pop()
            if eval > max_eval:
                max_eval = eval
                best_moves = [move]
            elif eval == max_eval:
                best_moves.append(move)
            alpha = max(alpha, eval)
            if beta <= alpha:
                break
        return max_eval, random.choice(best_moves) if best_moves else (max_eval, None)
    else:
        min_eval = float("inf")
        for move in board.legal_moves:
            board.push(move)
            eval, _ = minimax(board, depth - 1, True, alpha, beta, eval_fn)
            board.pop()
            if eval < min_eval:
                min_eval = eval
                best_moves = [move]
            elif eval == min_eval:
                best_moves.append(move)
            beta = min(beta, eval)
            if beta <= alpha:
                break
        return min_eval, random.choice(best_moves) if best_moves else (min_eval, None)


def get_ai_move(fen, depth):
    board = chess.Board(fen)
    if board.fullmove_number <= 2:
        fen_key = board.fen()
        if board.turn == chess.WHITE and board.fullmove_number == 1:
            return random.choice(OPENING_BOOK["start"])
        elif fen_key in OPENING_BOOK:
            return random.choice(OPENING_BOOK[fen_key])
    _, move = minimax(board, depth, board.turn == chess.WHITE)
    return move.uci() if move else None
