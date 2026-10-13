import chess
import chess.pgn
from AI.MMQSPST import MMQSPST

def run_simulation(white_depth=4, black_depth=4, pgn_filename="ai_match.pgn"):
    # Initialize the board
    board = chess.Board()

    # Initialize two AI players
    white_ai = MMQSPST(name="MMQSPST_White", depth=white_depth)
    black_ai = MMQSPST(name="MMQSPST_Black", depth=black_depth)

    # Set up PGN game structure
    game = chess.pgn.Game()
    game.headers["White"] = white_ai.name
    game.headers["Black"] = black_ai.name
    game.headers["Event"] = "AI vs AI Simulation"
    
    node = game

    print(f"--- Starting Simulation ---")
    print(f"White: {white_ai.name} (Depth {white_depth})")
    print(f"Black: {black_ai.name} (Depth {black_depth})\n")

    move_count = 0
    while not board.is_game_over():
        # Choose move based on whose turn it is
        if board.turn == chess.WHITE:
            move = white_ai.get_move(board)
            current_player = white_ai.name
        else:
            move = black_ai.get_move(board)
            current_player = black_ai.name

        # Safety check if engine fails to find a move
        if move is None or move not in board.legal_moves:
            print(f"{current_player} returned an invalid or null move. Ending game.")
            break

        # 1. Get SAN notation BEFORE pushing the move
        san_move = board.san(move)

        # 2. Push move to board and add to PGN tree
        board.push(move)
        node = node.add_variation(move)
        move_count += 1
        
        print(f"Move {move_count} ({current_player}): {san_move} (FEN: {board.fen()[:30]}...)")

    # Record the game result
    result = board.result()
    game.headers["Result"] = result
    print(f"\n--- Game Over ---")
    print(f"Result: {result} ({board.outcome().termination.name if board.outcome() else 'Unknown'})")

    # Save to PGN file
    with open(pgn_filename, "w", encoding="utf-8") as f:
        print(game, file=f, end="\n\n")
    
    print(f"PGN successfully saved to '{pgn_filename}'")

if __name__ == "__main__":
    run_simulation(white_depth=4, black_depth=4, pgn_filename="ai_match.pgn")