import sys
from datetime import datetime
import chess
import chess.svg
import chess.pgn
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QSlider,
    QSpinBox,
)
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtCore import Qt, QByteArray, Signal

from AI.NoPST import NoPST
from AI.StockfishAI import StockfishAI

# Update this path to your actual Stockfish executable
STOCKFISH_PATH = "stockfish/stockfish-windows-x86-64-universal.exe" 


class ClickableSvgWidget(QSvgWidget):
    """Custom SVG widget that captures mouse clicks to translate to board squares."""
    clicked = Signal(int, int)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(int(event.position().x()), int(event.position().y()))
        super().mousePressEvent(event)


class ChessWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Python Chess vs AI (Desktop App)")
        self.setFixedSize(500, 645)

        self.board = chess.Board()
        self.nopst_ai = NoPST(name="NoPST", depth=4)
        self.stockfish_ai = None
        try:
            self.stockfish_ai = StockfishAI(path=STOCKFISH_PATH, name="Stockfish", elo=1800, movetime=0.6)
        except Exception as exc:
            print(f"Warning: Could not start Stockfish ({exc}). Falling back to NoPST.")

        self.ai = self.stockfish_ai if self.stockfish_ai is not None else self.nopst_ai
        self.assist_ai = NoPST(name="NoPST-Assist", depth=4)
        self.human_color = chess.WHITE

        self.selected_square = None
        self.last_move = None
        self.blunder_moves: list[tuple[chess.Move, int]] = []

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.status_label = QLabel("Your turn (White). Click piece, then click destination.")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #333;")
        layout.addWidget(self.status_label)

        self.board_size = 440
        self.svg_widget = ClickableSvgWidget(self)
        self.svg_widget.setFixedSize(self.board_size, self.board_size)
        self.svg_widget.clicked.connect(self.handle_board_click)

        board_layout = QHBoxLayout()
        board_layout.addStretch()
        board_layout.addWidget(self.svg_widget)
        board_layout.addStretch()
        layout.addLayout(board_layout)

        # Stockfish Elo controls
        elo_layout = QHBoxLayout()
        min_elo = self.stockfish_ai.min_elo if self.stockfish_ai else 1320
        max_elo = self.stockfish_ai.max_elo if self.stockfish_ai else 3190
        init_elo = self.stockfish_ai.elo if self.stockfish_ai else 1800

        elo_layout.addWidget(QLabel("Stockfish Elo:"))

        self.elo_slider = QSlider(Qt.Horizontal)
        self.elo_slider.setRange(min_elo, max_elo)
        self.elo_slider.setValue(init_elo)
        self.elo_slider.setEnabled(self.stockfish_ai is not None)
        elo_layout.addWidget(self.elo_slider)

        self.elo_spinbox = QSpinBox()
        self.elo_spinbox.setRange(min_elo, max_elo)
        self.elo_spinbox.setValue(init_elo)
        self.elo_spinbox.setEnabled(self.stockfish_ai is not None)
        elo_layout.addWidget(self.elo_spinbox)

        self.elo_slider.valueChanged.connect(self.on_slider_changed)
        self.elo_spinbox.valueChanged.connect(self.on_spinbox_changed)
        layout.addLayout(elo_layout)

        btn_layout = QHBoxLayout()
        self.white_btn = QPushButton("Play as White")
        self.white_btn.clicked.connect(lambda: self.restart_game(chess.WHITE))
        btn_layout.addWidget(self.white_btn)

        self.black_btn = QPushButton("Play as Black")
        self.black_btn.clicked.connect(lambda: self.restart_game(chess.BLACK))
        btn_layout.addWidget(self.black_btn)

        self.opponent_btn = QPushButton(f"Opponent: {self.ai.name}")
        self.opponent_btn.clicked.connect(self.toggle_opponent)
        btn_layout.addWidget(self.opponent_btn)

        layout.addLayout(btn_layout)

        self.refresh_blunder_analysis()
        self.update_board_display()

    def on_slider_changed(self, value: int):
        if self.elo_spinbox.value() != value:
            self.elo_spinbox.blockSignals(True)
            self.elo_spinbox.setValue(value)
            self.elo_spinbox.blockSignals(False)
        if self.stockfish_ai is not None:
            self.stockfish_ai.set_elo(value)

    def on_spinbox_changed(self, value: int):
        if self.elo_slider.value() != value:
            self.elo_slider.blockSignals(True)
            self.elo_slider.setValue(value)
            self.elo_slider.blockSignals(False)
        if self.stockfish_ai is not None:
            self.stockfish_ai.set_elo(value)

    def toggle_opponent(self):
        if self.ai is self.stockfish_ai:
            self.ai = self.nopst_ai
        elif self.stockfish_ai is not None:
            self.ai = self.stockfish_ai
        self.opponent_btn.setText(f"Opponent: {self.ai.name}")
        self.restart_game(self.human_color)

    def refresh_blunder_analysis(self):
        """Runs NoPST right after the opponent moves and prints move scores and lines to terminal."""
        self.blunder_moves = []
        if not self.board.is_game_over() and self.board.turn == self.human_color:
            turn_label = "White" if self.board.turn == chess.WHITE else "Black"
            print(f"\n--- NoPST Scores ({turn_label} to move, depth={self.assist_ai.max_depth}) ---")
            all_moves = self.assist_ai.analyze_moves(self.board.copy())
            for move, score, is_blunder, line, q_line in all_moves:
                tag = " [BLUNDER]" if is_blunder else ""
                line_str = f" | line: {' '.join(line)}" if line else ""
                q_str = f" | q_line: {' '.join(q_line)}" if q_line else ""
                print(f"  {move.uci():6s} -> score: {score:+d}{tag}{line_str}{q_str}")
            self.blunder_moves = [(move, score) for move, score, is_blunder, _, _ in all_moves if is_blunder]

    def get_blunder_destinations_for_selected(self) -> set[chess.Square]:
        if self.selected_square is None:
            return set()
        return {
            move.to_square
            for move, _ in self.blunder_moves
            if move.from_square == self.selected_square
        }

    def update_board_display(self):
        squares_to_highlight = {self.selected_square} if self.selected_square is not None else set()
        fill_squares = {sq: "#e74c3c" for sq in self.get_blunder_destinations_for_selected()}

        svg_data = chess.svg.board(
            board=self.board,
            size=self.board_size,
            lastmove=self.last_move,
            squares=chess.SquareSet(squares_to_highlight),
            fill=fill_squares,
            coordinates=False,
            flipped=(self.human_color == chess.BLACK),
            check=self.board.king(self.board.turn) if self.board.is_check() else None,
        )
        self.svg_widget.load(QByteArray(svg_data.encode("utf-8")))

    def handle_board_click(self, x, y):
        if self.board.is_game_over() or self.board.turn != self.human_color:
            return

        sq_size = self.board_size / 8.0

        if self.human_color == chess.BLACK:
            file = 7 - int(x / sq_size)
            rank = int(y / sq_size)
        else:
            file = int(x / sq_size)
            rank = 7 - int(y / sq_size)

        clicked_square = chess.square(file, rank)

        if self.selected_square is None:
            piece = self.board.piece_at(clicked_square)
            if piece and piece.color == self.human_color:
                self.selected_square = clicked_square
                self.update_board_display()
        else:
            move = chess.Move(self.selected_square, clicked_square)

            piece = self.board.piece_at(self.selected_square)
            if piece and piece.piece_type == chess.PAWN:
                if (piece.color == chess.WHITE and chess.square_rank(clicked_square) == 7) or (
                    piece.color == chess.BLACK and chess.square_rank(clicked_square) == 0
                ):
                    move = chess.Move(self.selected_square, clicked_square, promotion=chess.QUEEN)

            if move in self.board.legal_moves:
                self.board.push(move)
                self.last_move = move
                self.selected_square = None
                self.blunder_moves = []
                self.update_board_display()

                if self.board.is_game_over():
                    self.handle_game_over()
                else:
                    self.status_label.setText(f"{self.ai.name} is thinking...")
                    QApplication.processEvents()

                    ai_move = self.ai.get_move(self.board.copy())
                    if ai_move in self.board.legal_moves:
                        self.board.push(ai_move)
                        self.last_move = ai_move

                    if self.board.is_game_over():
                        self.update_board_display()
                        self.handle_game_over()
                    else:
                        self.status_label.setText("Analyzing blunders...")
                        QApplication.processEvents()
                        self.refresh_blunder_analysis()
                        self.update_board_display()

                        color_name = "White" if self.human_color == chess.WHITE else "Black"
                        self.status_label.setText(f"Your turn ({color_name}).")
            else:
                piece = self.board.piece_at(clicked_square)
                if piece and piece.color == self.human_color:
                    self.selected_square = clicked_square
                else:
                    self.selected_square = None
                self.update_board_display()

    def handle_game_over(self):
        result = self.board.result()
        reason = "Game Over"
        if self.board.is_checkmate():
            reason = "Checkmate"
        elif self.board.is_stalemate():
            reason = "Stalemate"
        elif self.board.is_insufficient_material():
            reason = "Insufficient Material"

        self.status_label.setText(f"Game Over! Result: {result} ({reason})")
        self.save_game_to_pgn()

    def save_game_to_pgn(self):
        game = chess.pgn.Game.from_board(self.board)

        game.headers["Event"] = "Python Chess vs AI"
        game.headers["White"] = "Human" if self.human_color == chess.WHITE else self.ai.name
        game.headers["Black"] = self.ai.name if self.human_color == chess.WHITE else "Human"
        game.headers["Date"] = datetime.now().strftime("%Y.%m.%d")
        game.headers["Result"] = self.board.result()

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        filename = f"{timestamp}_{self.ai.name}.pgn"

        with open(filename, "w", encoding="utf-8") as pgn_file:
            print(game, file=pgn_file)

        print(f"Game successfully saved to {filename}")

    def restart_game(self, color):
        self.human_color = color
        self.board = chess.Board()
        self.selected_square = None
        self.last_move = None
        self.blunder_moves = []

        if self.stockfish_ai is not None:
            self.stockfish_ai.new_game()

        color_name = "White" if self.human_color == chess.WHITE else "Black"

        if self.human_color == chess.BLACK:
            self.status_label.setText(f"{self.ai.name} (White) is thinking...")
            QApplication.processEvents()

            ai_move = self.ai.get_move(self.board.copy())
            if ai_move in self.board.legal_moves:
                self.board.push(ai_move)
                self.last_move = ai_move

        if not self.board.is_game_over():
            self.status_label.setText("Analyzing blunders...")
            QApplication.processEvents()
            self.refresh_blunder_analysis()
            self.status_label.setText(f"Your turn ({color_name}).")
        else:
            self.handle_game_over()

        self.update_board_display()

    def closeEvent(self, event):
        if self.stockfish_ai is not None:
            self.stockfish_ai.close()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ChessWindow()
    window.show()
    sys.exit(app.exec())