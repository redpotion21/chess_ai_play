import chess

class MMQSPST:
    """
    Advanced Chess AI featuring: Negamax with Alpha-Beta Pruning,
    Transposition Table (TT) with Zobrist FEN hashing,
    Piece-Square Tables (PST) with Tapered King Evaluation,
    Move Ordering (MVV-LVA / Transposition Move),
    Quiescence Search for tactile tactical evaluation,
    and Threefold Repetition Draw Consideration.
    """
    EXACT, LOWERBOUND, UPPERBOUND = 0, 1, 2

    def __init__(self, name="AdvancedEngine", depth=5):
        self.name = name
        self.max_depth = depth
        self.tt = {}

        self.piece_values = {
            chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330,
            chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 20000
        }

        self.pawn_pst = [
             0,  0,  0,  0,  0,  0,  0,  0,
             5, 10, 10,-20,-20, 10, 10,  5,
             5, -5,-10,  0,  0,-10, -5,  5,
            10, 10, 15, 25, 25, 15, 10, 10,
            20, 20, 30, 40, 40, 30, 20, 20,
            40, 40, 50, 60, 60, 50, 40, 40,
            80, 80, 90,100,100, 90, 80, 80,
             0,  0,  0,  0,  0,  0,  0,  0
        ]
        self.knight_pst = [
           -50,-40,-30,-30,-30,-30,-40,-50,
           -40,-20,  0,  5,  5,  0,-20,-40,
           -30,  5, 10, 15, 15, 10,  5,-30,
           -30,  0, 15, 20, 20, 15,  0,-30,
           -30,  5, 15, 20, 20, 15,  5,-30,
           -30,  0, 10, 15, 15, 10,  0,-30,
           -40,-20,  0,  0,  0,  0,-20,-40,
           -50,-40,-30,-30,-30,-30,-40,-50
        ]
        self.bishop_pst = [
           -20,-10,-10,-10,-10,-10,-10,-20,
           -10,  5,  0,  0,  0,  0,  5,-10,
           -10, 10, 10, 10, 10, 10, 10,-10,
           -10,  0, 10, 10, 10, 10,  0,-10,
           -10,  5,  5, 10, 10,  5,  5,-10,
           -10,  0,  5, 10, 10,  5,  0,-10,
           -10,  0,  0,  0,  0,  0,  0,-10,
           -20,-10,-10,-10,-10,-10,-10,-20
        ]
        self.rook_pst = [
             0,  0,  0,  5,  5,  0,  0,  0,
            -5,  0,  0,  0,  0,  0,  0, -5,
            -5,  0,  0,  0,  0,  0,  0, -5,
            -5,  0,  0,  0,  0,  0,  0, -5,
            -5,  0,  0,  0,  0,  0,  0, -5,
            -5,  0,  0,  0,  0,  0,  0, -5,
             5, 10, 10, 10, 10, 10, 10,  5,
             0,  0,  0,  0,  0,  0,  0,  0
        ]
        self.queen_pst = [
           -20,-10,-10, -5, -5,-10,-10,-20,
           -10,  0,  5,  0,  0,  0,  0,-10,
           -10,  5,  5,  5,  5,  5,  0,-10,
            -5,  0,  5,  5,  5,  5,  0, -5,
             0,  0,  5,  5,  5,  5,  0, -5,
           -10,  0,  5,  5,  5,  5,  0,-10,
           -10,  0,  0,  0,  0,  0,  0,-10,
           -20,-10,-10, -5, -5,-10,-10,-20
        ]
        self.king_mg_pst = [
            20, 30, 10,  0,  0, 10, 30, 20,
            20, 20,  0,  0,  0,  0, 20, 20,
           -10,-20,-20,-20,-20,-20,-20,-10,
           -20,-30,-30,-40,-40,-30,-30,-20,
           -30,-40,-40,-50,-50,-40,-40,-30,
           -30,-40,-40,-50,-50,-40,-40,-30,
           -30,-40,-40,-50,-50,-40,-40,-30,
           -30,-40,-40,-50,-50,-40,-40,-30
        ]
        self.king_eg_pst = [
           -50,-40,-30,-20,-20,-30,-40,-50,
           -30,-20,-10,  0,  0,-10,-20,-30,
           -30,-10, 20, 30, 30, 20,-10,-30,
           -30,-10, 30, 40, 40, 30,-10,-30,
           -30,-10, 30, 40, 40, 30,-10,-30,
           -30,-10, 20, 30, 30, 20,-10,-30,
           -30,-30,  0,  0,  0,  0,-30,-30,
           -50,-30,-30,-30,-30,-30,-30,-50
        ]

        self.pst_tables = {
            chess.PAWN: self.pawn_pst,
            chess.KNIGHT: self.knight_pst,
            chess.BISHOP: self.bishop_pst,
            chess.ROOK: self.rook_pst,
            chess.QUEEN: self.queen_pst,
        }

    def evaluate_board(self, board: chess.Board) -> int:
        # Added threefold repetition check to evaluation draws
        if board.is_stalemate() or board.is_insufficient_material() or board.is_repetition(3):
            return 0

        score = 0
        phase = 0

        for square, piece in board.piece_map().items():
            pt = piece.piece_type
            color = piece.color
            
            if pt in (chess.KNIGHT, chess.BISHOP):
                phase += 1
            elif pt == chess.ROOK:
                phase += 2
            elif pt == chess.QUEEN:
                phase += 4

            base_val = self.piece_values[pt]
            sq_idx = square if color == chess.WHITE else chess.square_mirror(square)

            if pt == chess.KING:
                pst_val = int(((self.king_mg_pst[sq_idx] * phase) + (self.king_eg_pst[sq_idx] * (24 - phase))) / 24)
            else:
                pst_val = self.pst_tables[pt][sq_idx]

            if color == chess.WHITE:
                score += base_val + pst_val
            else:
                score -= base_val + pst_val

        return score

    def order_moves(self, board: chess.Board, moves, hash_move=None):
        def score_move(move):
            if move == hash_move:
                return 10000000
                
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

    def quiescence_search(self, board: chess.Board, alpha: int, beta: int, color: int) -> int:
        stand_pat = self.evaluate_board(board) * color
        if stand_pat >= beta:
            return beta
        if alpha < stand_pat:
            alpha = stand_pat

        captures = list(board.generate_legal_captures())
        for move in self.order_moves(board, captures):
            board.push(move)
            score = -self.quiescence_search(board, -beta, -alpha, -color)
            board.pop()

            if score >= beta:
                return beta
            if score > alpha:
                alpha = score

        return alpha

    def negamax(self, board: chess.Board, depth: int, alpha: int, beta: int, color: int) -> int:
        # Check for threefold repetition at the start of search nodes
        if board.is_repetition(3):
            return 0

        original_alpha = alpha
        hash_key = board.fen()
        hash_move = None

        if hash_key in self.tt:
            tt_depth, tt_flag, tt_score, tt_move = self.tt[hash_key]
            if tt_depth >= depth:
                if tt_flag == self.EXACT:
                    return tt_score
                if tt_flag == self.LOWERBOUND and tt_score >= beta:
                    return tt_score
                if tt_flag == self.UPPERBOUND and tt_score <= alpha:
                    return tt_score
            hash_move = tt_move

        if depth == 0:
            return self.quiescence_search(board, alpha, beta, color)

        moves = list(board.legal_moves)
        if not moves:
            if board.is_check():
                return -99999 + depth
            return 0

        best_move = None
        best_score = -9999999
        ordered_moves = self.order_moves(board, moves, hash_move)

        for move in ordered_moves:
            board.push(move)
            score = -self.negamax(board, depth - 1, -beta, -alpha, -color)
            board.pop()

            if score > best_score:
                best_score = score
                best_move = move

            alpha = max(alpha, best_score)
            if alpha >= beta:
                break

        if best_score <= original_alpha:
            flag = self.UPPERBOUND
        elif best_score >= beta:
            flag = self.LOWERBOUND
        else:
            flag = self.EXACT
            
        self.tt[hash_key] = (depth, flag, best_score, best_move)

        return best_score

    def get_move(self, board: chess.Board) -> chess.Move:
        best_move = None
        color = 1 if board.turn == chess.WHITE else -1

        for d in range(1, self.max_depth + 1):
            score = self.negamax(board, d, -9999999, 9999999, color)
            tt_entry = self.tt.get(board.fen())
            if tt_entry:
                best_move = tt_entry[3]
            if abs(score) > 90000:
                break

        return best_move