import sys
import os
import chess
import chess.pgn
import chess.svg

from PySide6.QtCore import Qt, QByteArray
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QTreeView, QFileSystemModel, QPushButton, QLabel, QSplitter, QMessageBox
)
from PySide6.QtSvgWidgets import QSvgWidget


class PgnViewerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PySide6 PGN Viewer")
        self.resize(1000, 700)

        # Game state variables
        self.games = []
        self.current_game_index = 0
        self.current_node = None  # chess.pgn.GameNode pointer

        self.init_ui()
        self.init_shortcuts()

    def init_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # --- Left Panel: Directory Browser ---
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        
        left_label = QLabel("<b>Project Directory (.pgn files)</b>")
        left_layout.addWidget(left_label)

        self.file_model = QFileSystemModel()
        self.file_model.setRootPath(os.getcwd())
        self.file_model.setNameFilters(["*.pgn"])
        self.file_model.setNameFilterDisables(False)

        self.tree_view = QTreeView()
        self.tree_view.setModel(self.file_model)
        self.tree_view.setRootIndex(self.file_model.index(os.getcwd()))
        for i in range(1, self.file_model.columnCount()):
            self.tree_view.setColumnHidden(i, True)
            
        self.tree_view.doubleClicked.connect(self.on_file_double_clicked)
        left_layout.addWidget(self.tree_view)
        splitter.addWidget(left_container)

        # --- Right Panel: Board & Controls ---
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)

        self.info_label = QLabel("Select a PGN file from the left panel to begin.")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 5px;")
        right_layout.addWidget(self.info_label)

        self.board_widget = QSvgWidget()
        self.board_widget.setFixedSize(480, 480)
        
        board_layout = QHBoxLayout()
        board_layout.addStretch()
        board_layout.addWidget(self.board_widget)
        board_layout.addStretch()
        right_layout.addLayout(board_layout)

        self.move_label = QLabel("Move: -")
        self.move_label.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(self.move_label)

        right_layout.addStretch()

        button_layout = QHBoxLayout()
        
        self.btn_prev_game = QPushButton("Previous Game ('q')")
        self.btn_prev_move = QPushButton("Previous Move (←)")
        self.btn_next_move = QPushButton("Next Move (→)")
        self.btn_next_game = QPushButton("Next Game ('e')")

        self.btn_prev_game.clicked.connect(self.prev_game)
        self.btn_prev_move.clicked.connect(self.prev_move)
        self.btn_next_move.clicked.connect(self.next_move)
        self.btn_next_game.clicked.connect(self.next_game)

        button_layout.addWidget(self.btn_prev_game)
        button_layout.addWidget(self.btn_prev_move)
        button_layout.addWidget(self.btn_next_move)
        button_layout.addWidget(self.btn_next_game)
        right_layout.addLayout(button_layout)

        splitter.addWidget(right_container)
        splitter.setSizes([300, 700])

        self.update_board_display()

    def init_shortcuts(self):
        # Using QShortcut guarantees global window-wide shortcuts 
        # even when the file tree has keyboard focus.
        self.shortcut_next = QShortcut(QKeySequence(Qt.Key_Right), self)
        self.shortcut_next.activated.connect(self.next_move)

        self.shortcut_prev = QShortcut(QKeySequence(Qt.Key_Left), self)
        self.shortcut_prev.activated.connect(self.prev_move)

        # Handle both lowercase and uppercase Q / E cleanly
        self.shortcut_prev_game_lower = QShortcut(QKeySequence("q"), self)
        self.shortcut_prev_game_lower.activated.connect(self.prev_game)
        self.shortcut_prev_game_upper = QShortcut(QKeySequence("Q"), self)
        self.shortcut_prev_game_upper.activated.connect(self.prev_game)

        self.shortcut_next_game_lower = QShortcut(QKeySequence("e"), self)
        self.shortcut_next_game_lower.activated.connect(self.next_game)
        self.shortcut_next_game_upper = QShortcut(QKeySequence("E"), self)
        self.shortcut_next_game_upper.activated.connect(self.next_game)

    def on_file_double_clicked(self, index):
        file_path = self.file_model.filePath(index)
        if os.path.isfile(file_path) and file_path.endswith(".pgn"):
            self.load_pgn_file(file_path)

    def load_pgn_file(self, file_path):
        self.games = []
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                while True:
                    game = chess.pgn.read_game(f)
                    if game is None:
                        break
                    self.games.append(game)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load PGN file:\n{e}")
            return

        if not self.games:
            QMessageBox.warning(self, "Warning", "No valid chess games found in this PGN file.")
            return

        self.current_game_index = 0
        self.set_current_game(0)

    def set_current_game(self, index):
        if not self.games:
            return
        self.current_game_index = max(0, min(index, len(self.games) - 1))
        self.current_node = self.games[self.current_game_index]
        self.update_board_display()

    def next_move(self):
        if self.current_node and self.current_node.variations:
            self.current_node = self.current_node.variations[0]
            self.update_board_display()

    def prev_move(self):
        if self.current_node and self.current_node.parent:
            self.current_node = self.current_node.parent
            self.update_board_display()

    def next_game(self):
        if self.games and self.current_game_index < len(self.games) - 1:
            self.set_current_game(self.current_game_index + 1)

    def prev_game(self):
        if self.games and self.current_game_index > 0:
            self.set_current_game(self.current_game_index - 1)

    def update_board_display(self):
        if not self.games or not self.current_node:
            board = chess.Board()
            self.info_label.setText("No game loaded.")
            self.move_label.setText("Move: -")
        else:
            board = self.current_node.board()
            game = self.games[self.current_game_index]
            white = game.headers.get("White", "Unknown")
            black = game.headers.get("Black", "Unknown")
            result = game.headers.get("Result", "*")
            event = game.headers.get("Event", "Casual Game")
            
            self.info_label.setText(f"Game {self.current_game_index + 1} of {len(self.games)} | {event}\n{white} vs {black} ({result})")
            
            if self.current_node.move:
                move_san = self.current_node.san()
                ply = self.current_node.ply()
                self.move_label.setText(f"Current Move (Ply {ply}): {move_san}")
            else:
                self.move_label.setText("Start of Game")

        svg_data = chess.svg.board(board, lastmove=self.current_node.move if self.current_node else None).encode("utf-8")
        self.board_widget.load(QByteArray(svg_data))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = PgnViewerWindow()
    viewer.show()
    sys.exit(app.exec())