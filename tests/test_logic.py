import pytest
from dodgem.dodgem import Dodgem

class TestDodgemRules:
    
    def test_initialization(self, game):
        """Test initial configuration for a 3x3 board."""
        # For n=3:
        # First player (0): pieces at 0, 3 (Left column)
        # Second player (1): pieces at 7, 8 (Bottom row)
        assert game.n == 3
        assert game.pieces == [[0, 3], [7, 8]]
        assert game.turn == 0

    def test_make_key(self, game):
        """Test the canonical JSON string generation for board states."""
        game.pieces = [[0], [8]]
        game.turn = 1
        key = game.make_key(game.pieces, game.turn)
        # Lists should be sorted and string should have no spaces
        assert key == '[[0],[8],1]'

    def test_move_available_first_player(self, game):
        """Test move availability for the First player (0)."""
        # First player moves generally towards the Right.
        # Board index mapping (3x3):
        # 0 1 2
        # 3 4 5
        # 6 7 8
        
        # Case 1: Center (4) -> Can move Right(5), Up(1), Down(7)
        game.pieces = [[4], []]
        moves = game.move_available(game.pieces, 4, 0)
        assert sorted(moves) == [1, 5, 7]

        # Case 2: Near goal (5) -> Can Exit(-1), Up(2), Down(8)
        game.pieces = [[5], []]
        moves = game.move_available(game.pieces, 5, 0)
        assert -1 in moves  # -1 represents exiting the board
        assert 2 in moves
        assert 8 in moves

        # Case 3: Blocked by opponent
        # Own piece at 4, Enemy at 5 -> Cannot move Right
        game.pieces = [[4], [5]]
        moves = game.move_available(game.pieces, 4, 0)
        assert 5 not in moves
        assert 1 in moves
        assert 7 in moves

    def test_move_available_second_player(self, game):
        """Test move availability for the Second player (1)."""
        # Second player moves generally Upwards.
        
        # Case 1: Center (4) -> Can move Up(1), Left(3), Right(5)
        game.pieces = [[], [4]]
        moves = game.move_available(game.pieces, 4, 1)
        assert sorted(moves) == [1, 3, 5]

        # Case 2: Near goal (1) -> Can Exit(-1), Left(0), Right(2)
        game.pieces = [[], [1]]
        moves = game.move_available(game.pieces, 1, 1)
        assert -1 in moves

    def test_is_finished_empty_pieces(self, game):
        """Test win condition when a player clears all pieces."""
        # First player has no pieces left -> First wins (win=0)
        game.pieces = [[], [8]]
        game.turn = 1
        assert game.is_finished() is True
        assert game.win == 0

        # Second player has no pieces left -> Second wins (win=1)
        game.pieces = [[0], []]
        game.turn = 0
        assert game.is_finished() is True
        assert game.win == 1

    def test_is_finished_blocked(self, game):
        """Test win condition when the opponent is trapped."""
        # The is_finished() method checks if the *opponent* of self.turn is blocked.
        # To test if Player 0 is blocked, we must simulate that it is Player 1's turn
        # (checking if Player 1's move blocked Player 0).
        
        # Setup: Player 0 is at [0], blocked by Player 1 at [1, 3].
        game.n = 3
        game.pieces = [[0], [1, 3]]
        
        # Set turn to 1. is_finished will check pieces[1-1] -> pieces[0].
        game.turn = 1 
        
        # Verify Player 0 really has no moves
        assert game.move_available(game.pieces, 0, 0) == []
        
        # Check termination logic
        assert game.is_finished() is True
        
        # Based on source code: "When opponent cannot move, you lose"
        # self.turn is 1. Opponent (0) cannot move. 1 loses.
        # self.win = 1 - self.turn = 0.
        assert game.win == 0

    def test_remain_heuristic(self, game):
        """Test calculation of the 'remain' heuristic (distance to goal)."""
        # First player wants to reach Column 2. Pos 0 is Col 0. Dist = 3 - 0 = 3.
        # Second player wants to reach Row 0. Pos 8 is Row 2. Dist = 1 + 2 = 3.
        game.pieces = [[0], [8]]
        
        # Total remain = 3 + 3 = 6
        assert game.remain(game.pieces) == 6
