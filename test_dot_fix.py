#!/usr/bin/env python3
"""
Test: Dot Placement Fix Verification
Verify that dots are no longer placed in wall positions.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_dot_placement():
    """Test that dots are not placed in wall positions."""
    print("🔍 Testing Dot Placement Fix...")
    print("=" * 40)
    
    try:
        from PySide6.QtWidgets import QApplication
        from gui.easter_egg import PacDupeGame
        
        # Create QApplication if it doesn't exist
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        # Create a game instance
        game = PacDupeGame()
        
        # Check for dots in wall positions
        dots_in_walls = []
        for dot in game.dots:
            if dot in game.walls:
                dots_in_walls.append(dot)
        
        print(f"📊 Test Results:")
        print(f"Total walls: {len(game.walls)}")
        print(f"Total dots: {len(game.dots)}")
        print(f"Dots in walls: {len(dots_in_walls)}")
        
        if dots_in_walls:
            print(f"❌ FAILED: Found {len(dots_in_walls)} dots in wall positions!")
            print(f"Problematic positions: {dots_in_walls[:5]}...")  # Show first 5
            return False
        else:
            print("✅ PASSED: No dots found in wall positions!")
            
        # Check for dots at player start position
        player_start = (game.player_x, game.player_y)
        if player_start in game.dots:
            print(f"❌ FAILED: Dot found at player start position {player_start}!")
            return False
        else:
            print("✅ PASSED: No dot at player start position!")
            
        # Check dot distribution
        grid_positions = (game.grid_size - 2) ** 2  # Exclude border
        wall_positions = len([w for w in game.walls if 0 < w[0] < game.grid_size-1 and 0 < w[1] < game.grid_size-1])
        available_positions = grid_positions - wall_positions - 1  # -1 for player start
        
        print(f"📈 Coverage Analysis:")
        print(f"Grid positions (excluding border): {grid_positions}")
        print(f"Wall positions (excluding border): {wall_positions}")
        print(f"Available positions: {available_positions}")
        print(f"Dot coverage: {len(game.dots)}/{available_positions} ({len(game.dots)/available_positions*100:.1f}%)")
        
        if len(game.dots) > available_positions:
            print("⚠️  WARNING: More dots than available positions!")
            return False
            
        print("\n🎮 Game is ready to play!")
        print("All dots are in valid positions and can be collected! 🎯")
        return True
        
    except ImportError as e:
        print(f"❌ Could not import game modules: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def main():
    """Run the dot placement test."""
    print("🎮 PacDupe - Dot Placement Fix Verification")
    print()
    
    success = test_dot_placement()
    
    print("\n" + "=" * 40)
    if success:
        print("🎉 ALL TESTS PASSED!")
        print("The dot placement fix is working correctly!")
        print("No more dots will be stuck in walls! 🎯")
    else:
        print("❌ TESTS FAILED!")
        print("There are still issues with dot placement.")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())