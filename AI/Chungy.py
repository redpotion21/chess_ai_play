import chess

class Chungy:
    """
    Standard Minimax + Alpha-Beta Pruning Engine.
    Exposes a clean interface: `get_move(board) -> chess.Move`
    """
    def __init__(self, name="Minimax-Bot", depth=3):
        self.name = name
        self.depth = depth
        self.piece_values = {
            chess.PAWN: 10,
            chess.KNIGHT: 30,
            chess.BISHOP: 30,
            chess.ROOK: 50,
            chess.QUEEN: 90,
            chess.KING: 900
        }

    def evaluate_board(self, board: chess.Board) -> int:
        if board.is_checkmate():
            return -9999 if board.turn == chess.WHITE else 9999
        if board.is_game_over():
            return 0

        score = 0
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece:
                val = self.piece_values[piece.piece_type]
                score += val if piece.color == chess.WHITE else -val
        return score

    def _minimax(self, board: chess.Board, depth: int, alpha: float, beta: float, maximizing: bool):
        if depth == 0 or board.is_game_over():
            return self.evaluate_board(board), None

        best_move = None
        if maximizing:
            max_eval = -float('inf')
            for move in board.legal_moves:
                board.push(move)
                eval_score, _ = self._minimax(board, depth - 1, alpha, beta, False)
                board.pop()
                if eval_score > max_eval:
                    max_eval = eval_score
                    best_move = move
                alpha = max(alpha, eval_score)
                if beta <= alpha:
                    break
            return max_eval, best_move
        else:
            min_eval = float('inf')
            for move in board.legal_moves:
                board.push(move)
                eval_score, _ = self._minimax(board, depth - 1, alpha, beta, True)
                board.pop()
                if eval_score < min_eval:
                    min_eval = eval_score
                    best_move = move
                beta = min(beta, eval_score)
                if beta <= alpha:
                    break
            return min_eval, best_move

    def get_move(self, board: chess.Board) -> chess.Move:
        is_white = (board.turn == chess.WHITE)
        _, move = self._minimax(
            board, 
            depth=self.depth, 
            alpha=-float('inf'), 
            beta=float('inf'), 
            maximizing=is_white
        )
        return move