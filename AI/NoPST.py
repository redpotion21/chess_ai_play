import chess


class NoPST:
    """
    Based on MMQSPST, with Piece-Square Tables (PST) removed and custom piece values applied.
    Tracks principal variation (PV) for both main search and quiescence search.
    """

    def __init__(self, name="NoPST", depth=4):
        self.name = name
        self.max_depth = depth

        self.piece_values = {
            chess.PAWN: 100,
            chess.KNIGHT: 300,
            chess.BISHOP: 300,
            chess.ROOK: 500,
            chess.QUEEN: 1000,
            chess.KING: 20000,
        }

    def evaluate_board(self, board: chess.Board) -> int:
        if board.is_stalemate() or board.is_insufficient_material() or board.is_repetition(3):
            return 0

        score = 0
        castling_bonus = 30
        if board.has_kingside_castling_rights(chess.WHITE):
            score += castling_bonus
        if board.has_queenside_castling_rights(chess.WHITE):
            score += castling_bonus // 2

        if board.has_kingside_castling_rights(chess.BLACK):
            score -= castling_bonus
        if board.has_queenside_castling_rights(chess.BLACK):
            score -= castling_bonus // 2

        for piece in board.piece_map().values():
            val = self.piece_values[piece.piece_type]
            if piece.color == chess.WHITE:
                score += val
            else:
                score -= val

        return score

    def order_moves(self, board: chess.Board, moves):
        def score_move(move):
            score = 0
            if board.is_capture(move):
                if board.is_en_passant(move):
                    return 100005

                victim = board.piece_at(move.to_square)
                attacker = board.piece_at(move.from_square)
                if victim and attacker:
                    score = 100000 + self.piece_values[victim.piece_type] - self.piece_values[attacker.piece_type]

            if move.promotion:
                score += 90000 + self.piece_values[move.promotion]

            return score

        return sorted(moves, key=score_move, reverse=True)

    def quiescence_search(self, board: chess.Board, alpha: int, beta: int, color: int) -> tuple[int, list[str]]:
        """Returns (score_from_color_perspective, q_capture_moves)."""
        stand_pat = self.evaluate_board(board) * color
        if stand_pat >= beta:
            return beta, []
        if alpha < stand_pat:
            alpha = stand_pat

        best_q_line: list[str] = []
        captures = list(board.generate_legal_captures())
        for move in self.order_moves(board, captures):
            board.push(move)
            child_score, child_q_line = self.quiescence_search(board, -beta, -alpha, -color)
            board.pop()

            score = -child_score
            if score >= beta:
                return beta, [move.uci()] + child_q_line
            if score > alpha:
                alpha = score
                best_q_line = [move.uci()] + child_q_line

        return alpha, best_q_line

    def negamax(self, board: chess.Board, depth: int, alpha: int, beta: int, color: int) -> tuple[int, list[str], list[str]]:
        """Returns (score_from_color_perspective, main_line, q_line)."""
        if board.is_repetition(3):
            return 0, [], []

        moves = list(board.legal_moves)
        if not moves:
            if board.is_check():
                return -99999 + (self.max_depth - depth), [], []
            return 0, [], []

        if depth == 0:
            q_score, q_line = self.quiescence_search(board, alpha, beta, color)
            return q_score, [], q_line

        best_score = -9999999
        best_line: list[str] = []
        best_q_line: list[str] = []

        for move in self.order_moves(board, moves):
            board.push(move)
            child_score, child_line, child_q_line = self.negamax(board, depth - 1, -beta, -alpha, -color)
            board.pop()

            score = -child_score
            if score > best_score:
                best_score = score
                best_line = [move.uci()] + child_line
                best_q_line = child_q_line

            alpha = max(alpha, best_score)
            if alpha >= beta:
                break

        return best_score, best_line, best_q_line

    def analyze_moves(self, board: chess.Board) -> list[tuple[chess.Move, int, bool, list[str], list[str]]]:
        """
        Evaluates all legal moves for board.turn at depth=self.max_depth.
        Returns [(move, delta, is_blunder, main_line, q_line), ...].
        """
        results: list[tuple[chess.Move, int, bool, list[str], list[str]]] = []
        mover_color = 1 if board.turn == chess.WHITE else -1
        baseline = self.evaluate_board(board) * mover_color

        for move in board.legal_moves:
            board.push(move)
            if board.is_checkmate():
                delta = 99999
                line = [move.uci()]
                q_line = []
            elif board.is_stalemate() or board.is_insufficient_material() or board.is_repetition(3):
                delta = -baseline if baseline > 0 else 0
                line = [move.uci()]
                q_line = []
            else:
                opp_score, opp_line, q_line = self.negamax(board, self.max_depth - 1, -9999999, 9999999, -mover_color)
                our_resulting_score = -opp_score
                delta = our_resulting_score - baseline
                line = [move.uci()] + opp_line
            board.pop()

            results.append((move, delta, delta < 0, line, q_line))

        return results

    def get_move(self, board: chess.Board) -> chess.Move:
        best_move = None
        color = 1 if board.turn == chess.WHITE else -1

        for d in range(1, self.max_depth + 1):
            _, line, _ = self.negamax(board, d, -9999999, 9999999, color)
            if line:
                best_move = chess.Move.from_uci(line[0])

        return best_move