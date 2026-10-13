import sys
from datetime import datetime
import chess
import chess.svg
import chess.pgn
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtCore import Qt, QByteArray, Signal

from AI.MMQSPST import MMQSPST

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
        self.setFixedSize(500, 580)

        self.board = chess.Board()
        self.ai = MMQSPST(name="MMQSPST", depth=4)
        self.human_color = chess.WHITE
        
        self.selected_square = None
        self.last_move = None

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

        btn_layout = QHBoxLayout()
        self.white_btn = QPushButton("Play as White")
        self.white_btn.clicked.connect(lambda: self.restart_game(chess.WHITE))
        btn_layout.addWidget(self.white_btn)

        self.black_btn = QPushButton("Play as Black")
        self.black_btn.clicked.connect(lambda: self.restart_game(chess.BLACK))
        btn_layout.addWidget(self.black_btn)
        
        layout.addLayout(btn_layout)

        self.update_board_display()

    def update_board_display(self):
        squares_to_highlight = {self.selected_square} if self.selected_square is not None else set()

        svg_data = chess.svg.board(
            board=self.board,
            size=self.board_size,
            lastmove=self.last_move,
            squares=chess.SquareSet(squares_to_highlight),
            coordinates=False,  # Disables border margins so squares fill 0 to board_size precisely
            flipped=(self.human_color == chess.BLACK),
            check=self.board.king(self.board.turn) if self.board.is_check() else None
        )
        self.svg_widget.load(QByteArray(svg_data.encode('utf-8')))

    def handle_board_click(self, x, y):
        if self.board.is_game_over() or self.board.turn != self.human_color:
            return

        sq_size = self.board_size / 8.0
        
        # Adjust coordinate translation based on whether the board is flipped
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
                if (piece.color == chess.WHITE and chess.square_rank(clicked_square) == 7) or \
                   (piece.color == chess.BLACK and chess.square_rank(clicked_square) == 0):
                    move = chess.Move(self.selected_square, clicked_square, promotion=chess.QUEEN)

            if move in self.board.legal_moves:
                self.board.push(move)
                self.last_move = move
                self.selected_square = None
                self.update_board_display()

                if self.board.is_game_over():
                    self.handle_game_over()
                else:
                    self.status_label.setText("AI is thinking...")
                    QApplication.processEvents()
                    
                    ai_move = self.ai.get_move(self.board.copy())
                    if ai_move in self.board.legal_moves:
                        self.board.push(ai_move)
                        self.last_move = ai_move
                        self.update_board_display()

                    if self.board.is_game_over():
                        self.handle_game_over()
                    else:
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
        
        color_name = "White" if self.human_color == chess.WHITE else "Black"
        
        if self.human_color == chess.BLACK:
            self.status_label.setText("AI (White) is thinking...")
            QApplication.processEvents()
            
            ai_move = self.ai.get_move(self.board.copy())
            if ai_move in self.board.legal_moves:
                self.board.push(ai_move)
                self.last_move = ai_move
                
            self.status_label.setText(f"Your turn ({color_name}).")
        else:
            self.status_label.setText(f"New game started. Your turn ({color_name}).")
            
        self.update_board_display()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ChessWindow()
    window.show()
    sys.exit(app.exec())