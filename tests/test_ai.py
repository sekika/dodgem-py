import pytest
from unittest.mock import MagicMock

class TestDodgemAI:

    def test_evaluate_terminal_states(self, game):
        """Test evaluation scores for terminal game states."""
        # Scenario: First player has won (empty list)
        game.pieces = [[], [1]]
        # evaluate() returns the score from the perspective of the current player.
        # If it's First's turn (0) and they have already won:
        score = game.evaluate(game.pieces, 0, 1)
        assert score == game.eval_win

        # Scenario: First player has lost (Opponent has empty list)
        game.pieces = [[0], []]
        score = game.evaluate(game.pieces, 0, 1)
        assert score == -game.eval_win

    def test_evaluate_heuristic_depth_zero(self, game):
        """Test heuristic evaluation when recursion depth reaches zero."""
        # Setup board: First[0], Second[8] on 3x3 board
        # First(0): distance to right (col 2) = 3 - 0 = 3
        # Second(8): distance to top (row 0) = 1 + 2 = 3
        # The internal logic in evaluate() calculates a differential 'remain' value.
        # remain = (First's dist) - (Second's dist) = 3 - 3 = 0
        
        game.pieces = [[0], [8]]
    
        # Case: Turn 0 (First). Formula in code: 1 - 2 * remain
        # remain is 0, so score should be 1.
        score = game.evaluate(game.pieces, 0, 0) # depth=0
        assert score == 1
    
        # Let's try an unbalanced case to verify calculation with blocking
        # First at 5 (Row 1, Col 2). Dist = 3 - 2 = 1.
        # Second at 8 (Row 2, Col 2). Dist = 1 + 2 = 3.
        #
        # Internal 'remain' calculation:
        # 1. Second (8):
        #    - Base dist: -(1 + 2) = -3
        #    - Blocking check: 8 moves Up to 5. 5 is occupied by First.
        #      Condition (piece - n) in pieces[0] is True.
        #      Penalty: -1.
        #    - Second total: -4
        # 2. First (5):
        #    - Base dist: +(3 - 2) = +1
        #    - Blocking check: 5 is at right edge. Not blocked.
        #    - First total: +1
        #
        # Net 'remain' = -4 + 1 = -3
    
        game.pieces = [[5], [8]]
    
        # Turn 0 (First). Formula: 1 - 2 * remain
        # 1 - 2 * (-3) = 7
        score = game.evaluate(game.pieces, 0, 0)
        assert score == 7

    def test_play_comp_execution(self, game):
        """Test that play_comp executes a move and updates history."""
        # Setup CPU configuration
        game.level = [0, 1]      # Second player is CPU L1
        game.pieces = [[0], [4]] # Second player at center
        game.turn = 1            # CPU's turn
        game.depth = 1
        game.use_mongo = False   # Pure calculation
        
        # Initialize history
        game.move_history = [game.make_key(game.pieces, 0)]
        
        # Execute AI move
        game.play_comp()
        
        # Assertions
        assert game.turn == 0    # Turn passed
        assert 4 not in game.pieces[1] # Piece moved from 4
        assert len(game.move_history) == 2 # History updated

    def test_evaluate_uses_mongo(self, game):
        """Test that evaluate() consults MongoDB when use_mongo is True."""
        # Enable Mongo for this specific test
        game.use_mongo = True
        game.collection = MagicMock()
        
        # Mock DB response
        mock_val = 50
        game.collection.find_one.return_value = {"value": mock_val}
        
        pieces = [[0], [8]]
        turn = 0
        score = game.evaluate(pieces, turn, 1)
        
        assert score == mock_val
        key = game.make_key(pieces, turn)
        game.collection.find_one.assert_called_with({"_id": key})
