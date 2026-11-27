import chess
import chess.engine


class StockfishAI:
    """Wrapper around a local UCI Stockfish executable with Elo strength control."""

    MIN_ELO = 1320
    MAX_ELO = 3190

    def __init__(self, path: str, name: str = "Stockfish", elo: int = 1800, movetime: float = 0.6):
        self.name = name
        self.movetime = movetime
        self.engine = chess.engine.SimpleEngine.popen_uci(path)
        self.game_token = object()

        elo_opt = self.engine.options.get("UCI_Elo")
        if elo_opt is not None and elo_opt.min is not None and elo_opt.max is not None:
            self.min_elo = int(elo_opt.min)
            self.max_elo = int(elo_opt.max)
        else:
            self.min_elo = self.MIN_ELO
            self.max_elo = self.MAX_ELO

        self.has_elo_limit = (
            "UCI_LimitStrength" in self.engine.options and "UCI_Elo" in self.engine.options
        )
        print(f"[{self.name}] Loaded '{path}' | UCI_Elo range: {self.min_elo}-{self.max_elo} | Elo supported: {self.has_elo_limit}")

        self.elo = max(self.min_elo, min(self.max_elo, int(elo)))
        self.set_elo(self.elo)

    def new_game(self):
        self.game_token = object()

    def set_elo(self, elo: int):
        self.elo = max(self.min_elo, min(self.max_elo, int(elo)))
        if self.engine is None:
            return
        if self.has_elo_limit:
            self.engine.configure({
                "UCI_LimitStrength": True,
                "UCI_Elo": self.elo,
            })
            print(f"[{self.name}] Applied UCI_LimitStrength=True, UCI_Elo={self.elo}")
        else:
            print(f"[{self.name}] Warning: Engine does not expose UCI_LimitStrength / UCI_Elo.")

    def get_move(self, board: chess.Board) -> chess.Move:
        result = self.engine.play(
            board,
            chess.engine.Limit(time=self.movetime),
            game=self.game_token,
        )
        return result.move

    def close(self):
        if self.engine is not None:
            self.engine.quit()
            self.engine = None