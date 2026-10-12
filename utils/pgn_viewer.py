import chess
import chess.pgn
import chess.svg
import ipywidgets as widgets
from IPython.display import display, clear_output, SVG


class PGNViewer:
    """
    Reads a PGN file and provides an interactive UI with Back / Next buttons.
    """
    def __init__(self, pgn_filename):
        with open(pgn_filename) as f:
            self.game = chess.pgn.read_game(f)

        self.history = []
        self.moves = []
        
        temp_board = self.game.board()
        self.history.append(temp_board.copy())
        
        for move in self.game.mainline_moves():
            temp_board.push(move)
            self.history.append(temp_board.copy())
            self.moves.append(move)

        self.current_idx = 0

        # UI Elements
        self.output_area = widgets.Output()
        self.btn_first = widgets.Button(description="|< First", button_style='info')
        self.btn_prev = widgets.Button(description="< Prev", button_style='primary')
        self.btn_next = widgets.Button(description="Next >", button_style='primary')
        self.btn_last = widgets.Button(description="Last >|", button_style='info')

        self.btn_first.on_click(self.go_first)
        self.btn_prev.on_click(self.go_prev)
        self.btn_next.on_click(self.go_next)
        self.btn_last.on_click(self.go_last)

        self.controls = widgets.HBox([self.btn_first, self.btn_prev, self.btn_next, self.btn_last])
        
        display(self.controls)
        display(self.output_area)
        self.render()

    def render(self):
        with self.output_area:
            clear_output(wait=True)
            board = self.history[self.current_idx]
            last_m = self.moves[self.current_idx - 1] if self.current_idx > 0 else None
            
            svg = chess.svg.board(
                board, 
                size=400, 
                lastmove=last_m,
                check=board.king(board.turn) if board.is_check() else None
            )
            display(SVG(svg))
            
            if self.current_idx == 0:
                print("Start Position")
            else:
                last_played = self.moves[self.current_idx - 1]
                move_num = (self.current_idx + 1) // 2
                color = "White" if self.current_idx % 2 != 0 else "Black"
                print(f"Move {self.current_idx}/{len(self.moves)}: {move_num}. {color} played {last_played.uci()}")
            
            if self.current_idx == len(self.history) - 1:
                print(f"Game Finished! Result: {self.game.headers.get('Result', '*')}")

    def go_first(self, b):
        self.current_idx = 0
        self.render()

    def go_prev(self, b):
        if self.current_idx > 0:
            self.current_idx -= 1
            self.render()

    def go_next(self, b):
        if self.current_idx < len(self.history) - 1:
            self.current_idx += 1
            self.render()

    def go_last(self, b):
        self.current_idx = len(self.history) - 1
        self.render()


def load_and_view_pgn(filename="game.pgn"):
    return PGNViewer(filename)