import time
import chess
import chess.pgn
import chess.svg
import ipywidgets as widgets
from IPython.display import display, clear_output, SVG


class GraphicalGameManager:
    """
    Jupyter Notebook / Google Colab Graphical Game Manager.
    Supports AI vs AI, Player vs AI, and Player vs Player with live SVG board updates.
    """
    def __init__(self,
                 white_player,
                 black_player,
                 turn_delay=0.5,
                 board_size=400,
                 pgn_filename="match"):
        self.board = chess.Board()
        self.white_player = white_player
        self.black_player = black_player
        self.turn_delay = turn_delay
        self.board_size = board_size
        self.is_paused = False
        self.pgn_filename = pgn_filename
        self.waiting_for_human = False

        # --- Setup IPyWidgets UI Layout ---
        self.board_output = widgets.Output()
        self.status_label = widgets.Label(value="Status: Ready to start")
        self.move_log = widgets.Textarea(
            value="",
            description="Moves:",
            disabled=True,
            layout=widgets.Layout(width="250px", height="340px")
        )
        
        # Human Move Input Controls
        self.move_input = widgets.Text(
            placeholder="e.g. e4, Nf3, e2e4",
            description="Your Move:",
            disabled=True,
            layout=widgets.Layout(width="300px")
        )
        self.submit_button = widgets.Button(
            description="Submit Move",
            disabled=True,
            button_style="primary",
            icon="check"
        )
        
        # Interactive Control Buttons
        self.play_button = widgets.Button(description="Start Game", icon="play", button_style="success")
        self.pause_button = widgets.Button(description="Pause", icon="pause", button_style="warning")
        
        self.play_button.on_click(self._on_play_clicked)
        self.pause_button.on_click(self._on_pause_clicked)
        self.submit_button.on_click(self._on_submit_clicked)
        self.move_input.on_submit(self._on_submit_clicked)

        controls = widgets.HBox([self.play_button, self.pause_button])
        human_controls = widgets.HBox([self.move_input, self.submit_button])
        left_panel = widgets.VBox([self.board_output, controls, human_controls, self.status_label])
        self.ui = widgets.HBox([left_panel, self.move_log])

    def render_board(self, last_move=None):
        """Renders the current chess board using chess.svg inside the Output widget."""
        with self.board_output:
            clear_output(wait=True)
            svg_data = chess.svg.board(
                board=self.board,
                size=self.board_size,
                lastmove=last_move,
                check=self.board.king(self.board.turn) if self.board.is_check() else None
            )
            display(SVG(svg_data))

    def _update_move_log(self):
        """Updates move list in the side log box."""
        moves_san = []
        temp_board = chess.Board()
        for i, move in enumerate(self.board.move_stack):
            if i % 2 == 0:
                moves_san.append(f"{(i//2) + 1}. {temp_board.san(move)}")
            else:
                moves_san[-1] += f"  {temp_board.san(move)}"
            temp_board.push(move)
        
        self.move_log.value = "\n".join(moves_san)

    def display(self):
        """Initializes and displays the UI inside the notebook output cell."""
        display(self.ui)
        self.render_board()

    def _on_play_clicked(self, b):
        if self.board.is_game_over():
            return
        self.is_paused = False
        self.play_button.description = "Resume"
        self._step_game()

    def _on_pause_clicked(self, b):
        self.is_paused = True
        self.status_label.value = "Status: Paused"

    def _step_game(self):
        """Drives the game turn-by-turn supporting both AI and Human players."""
        if self.is_paused or self.board.is_game_over():
            return

        if self.board.can_claim_threefold_repetition() or self.board.is_fivefold_repetition():
            self.status_label.value = "Game Over! Draw by Threefold Repetition."
            self._handle_game_over("Threefold Repetition")
            return

        current_player = self.white_player if self.board.turn == chess.WHITE else self.black_player
        color_str = "White" if self.board.turn == chess.WHITE else "Black"
        player_name = current_player.name if current_player else "Human"

        is_human = (current_player is None or isinstance(current_player, HumanPlayer))

        if is_human:
            self.status_label.value = f"Status: Your turn ({color_str})! Enter move."
            self.move_input.disabled = False
            self.submit_button.disabled = False
            self.waiting_for_human = True
        else:
            self.move_input.disabled = True
            self.submit_button.disabled = True
            self.status_label.value = f"Status: {color_str} ({player_name}) thinking..."
            
            move = current_player.get_move(self.board.copy())

            if move in self.board.legal_moves:
                self.board.push(move)
                self._update_move_log()
                self.render_board(last_move=move)

                if self.board.is_game_over() or self.board.can_claim_threefold_repetition():
                    self._handle_game_over()
                    return

                time.sleep(self.turn_delay)
                self._step_game()
            else:
                self.status_label.value = f"Error: Illegal move by {player_name}"
                self._handle_game_over("Illegal Move")

    def _on_submit_clicked(self, b):
        if not self.waiting_for_human:
            return

        move_text = self.move_input.value.strip()
        if not move_text:
            return

        move = None
        try:
            move = self.board.parse_san(move_text)
        except ValueError:
            try:
                move = chess.Move.from_uci(move_text)
            except ValueError:
                move = None

        if move and move in self.board.legal_moves:
            self.move_input.value = ""
            self.move_input.disabled = True
            self.submit_button.disabled = True
            self.waiting_for_human = False

            self.board.push(move)
            self._update_move_log()
            self.render_board(last_move=move)

            if self.board.is_game_over() or self.board.can_claim_threefold_repetition():
                self._handle_game_over()
                return

            time.sleep(self.turn_delay)
            self._step_game()
        else:
            self.status_label.value = f"Invalid move '{move_text}'. Try SAN (e.g. e4, Nf3) or UCI (e.g. e2e4)."

    def _handle_game_over(self, custom_reason=None):
        self.move_input.disabled = True
        self.submit_button.disabled = True
        
        if custom_reason:
            reason = custom_reason
        else:
            reason = ""
            if self.board.is_checkmate():
                reason = "Checkmate"
            elif self.board.is_stalemate():
                reason = "Stalemate"
            elif self.board.is_insufficient_material():
                reason = "Insufficient Material"
            elif self.board.is_fifty_moves():
                reason = "50-Move Rule"
            else:
                reason = "Game Over"

        result = self.board.result()
        self.status_label.value = f"Game Over! Result: {result} ({reason})"
        self.export_pgn(self.pgn_filename)

    def export_pgn(self, filename: str):
        game = chess.pgn.Game.from_board(self.board)
        game.headers["Event"] = "Jupyter Graphical Human vs AI Match"
        game.headers["White"] = self.white_player.name if self.white_player else "Human"
        game.headers["Black"] = self.black_player.name if self.black_player else "Human"
        game.headers["Result"] = self.board.result()

        with open(filename + ".pgn", "w") as f:
            exporter = chess.pgn.FileExporter(f)
            game.accept(exporter)


class HumanPlayer:
    """Human player interface for Jupyter Notebook."""
    def __init__(self, name="Human"):
        self.name = name


def ai_selector(class_name, *args, **kwargs):
    import sys
    # Dynamically look up the class from loaded AI modules or globals
    # Alternatively, import specific modules directly depending on preference.
    from AI.MMQSPST import MMQSPST
    from AI.Chungy import Chungy
    
    registry = {
        "MMQSPST": MMQSPST,
        "Chungy": Chungy
    }
    
    cls = registry.get(class_name)
    if cls is None:
        raise ValueError(f"AI Class '{class_name}' not found.")
    return cls(*args, **kwargs)