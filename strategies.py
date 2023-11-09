"""
Some example strategies for people who want to create a custom, homemade bot.

With these classes, bot makers will not have to implement the UCI or XBoard interfaces themselves.
"""

from __future__ import annotations
import chess
from chess.engine import PlayResult
from chess.polyglot import zobrist_hash
import random
from engine_wrapper import MinimalEngine
from typing import Any, Union
from tqdm import tqdm
import logging
import copy
from functools import lru_cache
MOVE = Union[chess.engine.PlayResult, list[chess.Move]]


# Use this logger variable to print messages to the console or log files.
# logger.info("message") will always print "message" to the console or log file.
# logger.debug("message") will only print "message" if verbose logging is enabled.
logger = logging.getLogger(__name__)


class HashableChessBoard(chess.Board):
    def __hash__(self):
        return zobrist_hash(self)


class ExampleEngine(MinimalEngine):
    """An example engine that all homemade engines inherit."""

    pass



PIECE_VALUES = {
    chess.KING: 0,
    chess.QUEEN: 9,
    chess.BISHOP: 3.5,
    chess.KNIGHT: 3,
    chess.ROOK: 5,
    chess.PAWN: 1
}

def colorFactor(player: chess.WHITE | chess.BLACK) -> int:
    return 1 if player == chess.WHITE else -1

def negamax(board: chess.Board, depth: int, alpha: int = -999999, beta: int = 999999):
    if depth == 0:
        return eval_board(board)
    maxValue = -999999

    moves = board.legal_moves
    
    for move in moves:
        board.push(move)
        value = -negamax(board, depth-1, -beta, maxValue)
        board.pop(move)

        if (value > maxValue):
            maxValue = value
        # if (depth == Suchtiefe)
        #     besterZug = Zug;
        if (maxValue >= beta):
            break
    return maxValue

def alphaBetaNegaMax(board: chess.Board, depth: int, alpha: int = -999999, beta: int = 999999):
    if (depth == 0):
        return eval_board(board)
    
    for move in board.legal_moves:
        newBoard = copy.deepcopy(board)
        newBoard.push(move)
        score = -alphaBetaNegaMax(newBoard, depth-1, -beta, -alpha)
        
        if score >= beta:
            return beta
        
        if score > alpha:
            alpha = score
        
    return alpha

@lru_cache(maxsize=2**16)
def eval_board(board: chess.Board):
    white_score = 0
    black_score = 0

    for piece_type in chess.PIECE_TYPES:
        num_piece = len(board.pieces(piece_type, chess.WHITE))
        white_score += PIECE_VALUES[piece_type] * num_piece

    for piece_type in chess.PIECE_TYPES:
        num_piece = len(board.pieces(piece_type, chess.BLACK))
        black_score += PIECE_VALUES[piece_type] * num_piece
    
    score = (white_score - black_score) * colorFactor(board.turn)
        
    if board.is_checkmate():
        score = -999999
        
    if board.is_check():
        score -= 100
    

    return score

class BertEngine(MinimalEngine):
    def search(self, board: chess.Board, time_limit: chess.engine.Limit, ponder: bool, draw_offered: bool, root_moves: MOVE) -> PlayResult:
        # return super().search(board, time_limit, ponder, draw_offered, root_moves)
        print(eval_board.cache_info())
        board = HashableChessBoard(board.fen())

        best_moves = []
        best_score = -999999

        # check_moves = root_moves if root_moves is not None else board.legal_moves
        check_moves = board.legal_moves

        for move in tqdm(list(board.legal_moves), leave=False):
            new_board = copy.deepcopy(board)
            new_board.push(move)
            score = alphaBetaNegaMax(new_board, depth=3)
            
            user_score = score if board.turn == chess.WHITE else -score

            # try to minimize for opponent
            if user_score > best_score:
                best_score = user_score
                best_moves = [move]
            elif user_score == best_score:
                best_moves.append(move)
            else:
                pass

        best_move = random.choice(best_moves)
        
        # PAWN moves are unreversible
        if best_move.drop == chess.PAWN:
            eval_board.cache_clear()

        return PlayResult(best_move, None)

# Strategy names and ideas from tom7's excellent eloWorld video

class RandomMove(ExampleEngine):
    """Get a random move."""

    def search(self, board: chess.Board, *args: Any) -> PlayResult:
        """Choose a random move."""
        return PlayResult(random.choice(list(board.legal_moves)), None)


class Alphabetical(ExampleEngine):
    """Get the first move when sorted by san representation."""

    def search(self, board: chess.Board, *args: Any) -> PlayResult:
        """Choose the first move alphabetically."""
        moves = list(board.legal_moves)
        moves.sort(key=board.san)
        return PlayResult(moves[0], None)


class FirstMove(ExampleEngine):
    """Get the first move when sorted by uci representation."""

    def search(self, board: chess.Board, *args: Any) -> PlayResult:
        """Choose the first move alphabetically in uci representation."""
        moves = list(board.legal_moves)
        moves.sort(key=str)
        return PlayResult(moves[0], None)


class ComboEngine(ExampleEngine):
    """
    Get a move using multiple different methods.

    This engine demonstrates how one can use `time_limit`, `draw_offered`, and `root_moves`.
    """

    def search(self, board: chess.Board, time_limit: chess.engine.Limit, ponder: bool, draw_offered: bool,
               root_moves: MOVE) -> chess.engine.PlayResult:
        """
        Choose a move using multiple different methods.

        :param board: The current position.
        :param time_limit: Conditions for how long the engine can search (e.g. we have 10 seconds and search up to depth 10).
        :param ponder: Whether the engine can ponder after playing a move.
        :param draw_offered: Whether the bot was offered a draw.
        :param root_moves: If it is a list, the engine should only play a move that is in `root_moves`.
        :return: The move to play.
        """
        if isinstance(time_limit.time, int):
            my_time = time_limit.time
            my_inc = 0
        elif board.turn == chess.WHITE:
            my_time = time_limit.white_clock if isinstance(time_limit.white_clock, int) else 0
            my_inc = time_limit.white_inc if isinstance(time_limit.white_inc, int) else 0
        else:
            my_time = time_limit.black_clock if isinstance(time_limit.black_clock, int) else 0
            my_inc = time_limit.black_inc if isinstance(time_limit.black_inc, int) else 0

        possible_moves = root_moves if isinstance(root_moves, list) else list(board.legal_moves)

        if my_time / 60 + my_inc > 10:
            # Choose a random move.
            move = random.choice(possible_moves)
        else:
            # Choose the first move alphabetically in uci representation.
            possible_moves.sort(key=str)
            move = possible_moves[0]
        return PlayResult(move, None, draw_offered=draw_offered)
