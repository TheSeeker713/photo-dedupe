#!/usr/bin/env python3
"""
Easter Egg Mini-Game: PacDupe
A tiny Pac-Man-like game hidden in the photo deduplication tool.
"""

import random
from typing import List, Tuple, Optional
from enum import Enum

try:
    from PySide6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, 
        QLabel, QMessageBox, QFrame
    )
    from PySide6.QtCore import (
        Qt, QTimer, QRect, Signal, QPropertyAnimation, 
        QEasingCurve, QPoint
    )
    from PySide6.QtGui import (
        QPainter, QColor, QPen, QBrush, QFont, QKeyEvent,
        QPaintEvent, QPixmap
    )
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    # Fallback classes
    class QDialog: pass
    class QWidget: pass
    class QTimer: pass
    class Signal: pass

class Direction(Enum):
    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

class GameState(Enum):
    PLAYING = "playing"
    WON = "won"
    PAUSED = "paused"

class PacDupeGame(QWidget):
    """The actual mini-game widget."""
    
    game_won = Signal()
    
    def __init__(self):
        super().__init__()
        self.setMinimumSize(300, 300)
        self.setMaximumSize(300, 300)
        self.setFixedSize(300, 300)
        self.setFocusPolicy(Qt.StrongFocus)
        
        # Game settings
        self.grid_size = 15
        self.cell_size = 20
        self.game_state = GameState.PLAYING
        
        # Player position (PacDupe character)
        self.player_x = 1
        self.player_y = 1
        self.player_direction = Direction.RIGHT
        
        # Walls (maze structure) - Initialize FIRST
        self.walls = []
        self.init_walls()
        
        # Dots to collect (representing duplicate files to "clean up")
        # Initialize AFTER walls so we can avoid placing dots in walls
        self.dots = []
        self.init_dots()
        
        # Game timer
        self.game_timer = QTimer()
        self.game_timer.timeout.connect(self.update_game)
        self.game_timer.start(200)  # 200ms updates
        
        # Animation for "eating" dots
        self.eating_animation = False
        self.eating_timer = QTimer()
        self.eating_timer.timeout.connect(self.stop_eating_animation)
        
        # Background color animation
        self.bg_color_phase = 0
        
    def init_dots(self):
        """Initialize dots to collect, avoiding walls and player start position."""
        # Create a pattern of dots avoiding walls and player start
        for x in range(1, self.grid_size - 1):
            for y in range(1, self.grid_size - 1):
                # Skip player start position
                if (x, y) == (1, 1):
                    continue
                    
                # Skip wall positions
                if (x, y) in self.walls:
                    continue
                    
                # Place dots in a checkerboard pattern for good distribution
                if (x + y) % 2 == 0:
                    self.dots.append((x, y))
                    
        # Add some additional random dots for variety, ensuring they don't conflict with walls
        attempts = 0
        random_dots_added = 0
        target_random_dots = 8
        
        while random_dots_added < target_random_dots and attempts < 50:
            x = random.randint(2, self.grid_size - 3)
            y = random.randint(2, self.grid_size - 3)
            
            # Check if position is valid (not wall, not player start, not already a dot)
            if ((x, y) not in self.walls and 
                (x, y) != (1, 1) and 
                (x, y) not in self.dots):
                self.dots.append((x, y))
                random_dots_added += 1
                
            attempts += 1
    
    def init_walls(self):
        """Initialize maze walls."""
        # Border walls
        for x in range(self.grid_size):
            self.walls.append((x, 0))
            self.walls.append((x, self.grid_size - 1))
        for y in range(self.grid_size):
            self.walls.append((0, y))
            self.walls.append((self.grid_size - 1, y))
            
        # Internal maze pattern
        for x in range(3, self.grid_size - 3, 3):
            for y in range(3, self.grid_size - 3, 2):
                self.walls.append((x, y))
                if y + 1 < self.grid_size - 1:
                    self.walls.append((x, y + 1))
    
    def keyPressEvent(self, event: QKeyEvent):
        """Handle keyboard input for movement."""
        if self.game_state != GameState.PLAYING:
            return
            
        key = event.key()
        if key == Qt.Key_Up:
            self.player_direction = Direction.UP
        elif key == Qt.Key_Down:
            self.player_direction = Direction.DOWN
        elif key == Qt.Key_Left:
            self.player_direction = Direction.LEFT
        elif key == Qt.Key_Right:
            self.player_direction = Direction.RIGHT
        elif key == Qt.Key_Space:
            # Pause/unpause
            if self.game_state == GameState.PLAYING:
                self.game_state = GameState.PAUSED
                self.game_timer.stop()
            else:
                self.game_state = GameState.PLAYING
                self.game_timer.start()
    
    def update_game(self):
        """Update game state."""
        if self.game_state != GameState.PLAYING:
            return
            
        # Move player
        dx, dy = self.player_direction.value
        new_x = self.player_x + dx
        new_y = self.player_y + dy
        
        # Check wall collision
        if (new_x, new_y) not in self.walls:
            self.player_x = new_x
            self.player_y = new_y
            
            # Check dot collection
            if (self.player_x, self.player_y) in self.dots:
                self.dots.remove((self.player_x, self.player_y))
                self.eating_animation = True
                self.eating_timer.start(100)
                
                # Check win condition
                if not self.dots:
                    self.game_state = GameState.WON
                    self.game_timer.stop()
                    self.game_won.emit()
        
        # Update background color for fun effect
        self.bg_color_phase = (self.bg_color_phase + 1) % 360
        self.update()
    
    def stop_eating_animation(self):
        """Stop the eating animation effect."""
        self.eating_animation = False
        self.eating_timer.stop()
    
    def paintEvent(self, event: QPaintEvent):
        """Paint the game."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Background with subtle color animation
        bg_intensity = 20 + int(5 * abs(1 - (self.bg_color_phase % 120) / 60))
        bg_color = QColor(bg_intensity, bg_intensity + 5, bg_intensity + 10)
        painter.fillRect(self.rect(), bg_color)
        
        # Draw grid
        painter.setPen(QPen(QColor(50, 50, 50), 1))
        for x in range(0, self.width(), self.cell_size):
            painter.drawLine(x, 0, x, self.height())
        for y in range(0, self.height(), self.cell_size):
            painter.drawLine(0, y, self.width(), y)
        
        # Draw walls
        painter.setBrush(QBrush(QColor(100, 100, 150)))
        painter.setPen(QPen(QColor(120, 120, 180), 2))
        for wall_x, wall_y in self.walls:
            x = wall_x * self.cell_size
            y = wall_y * self.cell_size
            painter.drawRect(x + 1, y + 1, self.cell_size - 2, self.cell_size - 2)
        
        # Draw dots (duplicate files to clean up)
        dot_color = QColor(255, 255, 100) if not self.eating_animation else QColor(255, 200, 100)
        painter.setBrush(QBrush(dot_color))
        painter.setPen(QPen(QColor(200, 200, 80), 1))
        for dot_x, dot_y in self.dots:
            x = dot_x * self.cell_size + self.cell_size // 2
            y = dot_y * self.cell_size + self.cell_size // 2
            size = 4 if not self.eating_animation else 6
            painter.drawEllipse(x - size // 2, y - size // 2, size, size)
        
        # Draw player (PacDupe character)
        player_x_px = self.player_x * self.cell_size
        player_y_px = self.player_y * self.cell_size
        
        # Player color changes based on eating animation
        if self.eating_animation:
            player_color = QColor(255, 150, 50)
        else:
            player_color = QColor(255, 200, 50)
            
        painter.setBrush(QBrush(player_color))
        painter.setPen(QPen(QColor(200, 150, 0), 2))
        
        # Draw PacDupe as a circle with a mouth
        center_x = player_x_px + self.cell_size // 2
        center_y = player_y_px + self.cell_size // 2
        radius = self.cell_size // 3
        
        # Body
        painter.drawEllipse(center_x - radius, center_y - radius, radius * 2, radius * 2)
        
        # Mouth (direction-based)
        mouth_color = QColor(0, 0, 0)
        painter.setBrush(QBrush(mouth_color))
        
        mouth_size = radius // 2
        if self.player_direction == Direction.RIGHT:
            mouth_x = center_x
            mouth_y = center_y - mouth_size // 2
        elif self.player_direction == Direction.LEFT:
            mouth_x = center_x - mouth_size
            mouth_y = center_y - mouth_size // 2
        elif self.player_direction == Direction.UP:
            mouth_x = center_x - mouth_size // 2
            mouth_y = center_y - mouth_size
        else:  # DOWN
            mouth_x = center_x - mouth_size // 2
            mouth_y = center_y
            
        painter.drawRect(mouth_x, mouth_y, mouth_size, mouth_size)
        
        # Game status text
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        painter.setFont(QFont("Arial", 8))
        
        if self.game_state == GameState.PAUSED:
            painter.drawText(10, 20, "PAUSED (Space to resume)")
        elif self.game_state == GameState.PLAYING:
            painter.drawText(10, 20, f"Duplicates left: {len(self.dots)}")
        elif self.game_state == GameState.WON:
            painter.drawText(10, 20, "YOU WON! All duplicates cleaned!")

class EasterEggDialog(QDialog):
    """The dialog that contains the easter egg game."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🎮 PacDupe - Clean Up Those Duplicates!")
        self.setFixedSize(360, 400)
        self.setModal(True)
        
        # Don't show in taskbar and keep on top
        self.setWindowFlags(Qt.Dialog | Qt.WindowStaysOnTopHint)
        
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("🎮 SECRET MINI-GAME DISCOVERED! 🎮")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Arial", 12, QFont.Bold))
        title.setStyleSheet("color: #FFD700; margin: 10px;")
        layout.addWidget(title)
        
        # Instructions
        instructions = QLabel(
            "Use arrow keys to move PacDupe!\n"
            "Eat all the yellow dots (duplicates) to win!\n"
            "Space = Pause/Resume"
        )
        instructions.setAlignment(Qt.AlignCenter)
        instructions.setStyleSheet("color: #CCCCCC; margin: 5px;")
        layout.addWidget(instructions)
        
        # Game widget
        self.game = PacDupeGame()
        self.game.game_won.connect(self.show_victory_message)
        layout.addWidget(self.game)
        
        # Close button
        self.close_button = QPushButton("Close Game")
        self.close_button.clicked.connect(self.close)
        self.close_button.setStyleSheet("""
            QPushButton {
                background-color: #444;
                color: white;
                border: 2px solid #666;
                border-radius: 5px;
                padding: 5px;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #555;
                border-color: #888;
            }
        """)
        layout.addWidget(self.close_button)
        
        self.setLayout(layout)
        
        # Dark theme
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
                border: 2px solid #444;
            }
        """)
        
    def show_victory_message(self):
        """Show the absurd victory message."""
        messages = [
            "🎉 CONGRATULATIONS! 🎉\n\nYou have successfully achieved the impossible:\nOrganizing digital chaos into perfect harmony!\n\nThe ancient art of duplicate deletion has been mastered.\nYour folders are now 37.2% more zen.\n\nThe Photo Deduplication Council hereby grants you\nthe prestigious title of 'Master File Wrangler'!\n\n(This title comes with absolutely no benefits\nbut sounds really impressive at parties)",
            
            "🌟 VICTORY ACHIEVED! 🌟\n\nIn a stunning display of pixel-level precision,\nyou have defeated the dreaded Duplicate Dragons!\n\nYour hard drive is now singing with joy,\nyour RAM is doing a happy dance,\nand somewhere in Silicon Valley,\na computer is shedding a single electronic tear\nof pure happiness.\n\nLegend says that cleaning up duplicates\nadds 3.7 years to your computer's lifespan\nand makes your coffee taste better.\n\n(Results may vary. Coffee improvement not guaranteed.)",
            
            "🎊 ASTOUNDING SUCCESS! 🎊\n\nBreaking News: Local human defeats\nthe notorious File Redundancy Menace!\n\nWitnesses report seeing actual disk space\nappearing out of nowhere, defying all known\nlaws of digital physics.\n\nExperts are baffled. Scientists are confused.\nYour computer is secretly plotting to nominate you\nfor the Nobel Prize in Applied File Management.\n\nSide effects may include: increased productivity,\nreduced storage anxiety, and spontaneous\nurges to organize everything.\n\n(Warning: May cause excessive satisfaction)",
            
            "🚀 MISSION ACCOMPLISHED! 🚀\n\nAlert: You have reached Peak File Organization!\n\nYour achievement has been recorded in the\nGalactic Registry of Impressive Digital Deeds.\nAlien civilizations across the universe\nare applauding your superior file management skills.\n\nAs a reward, the Universe has decided to grant you\nperfect WiFi signal strength for exactly 42 minutes\nand the ability to find matching socks\n87.3% more often.\n\n(Offer valid in this dimension only.\nVoid where prohibited by quantum mechanics.)"
        ]
        
        message = random.choice(messages)
        
        # Create a custom message box that auto-closes
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("🏆 Epic Victory! 🏆")
        msg_box.setText(message)
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setStandardButtons(QMessageBox.Ok)
        
        # Style the message box
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #2b2b2b;
                color: #FFD700;
            }
            QMessageBox QPushButton {
                background-color: #444;
                color: white;
                border: 2px solid #666;
                border-radius: 5px;
                padding: 8px 16px;
                min-width: 80px;
            }
            QMessageBox QPushButton:hover {
                background-color: #555;
                border-color: #888;
            }
        """)
        
        # Auto-close timer
        auto_close_timer = QTimer()
        auto_close_timer.timeout.connect(msg_box.close)
        auto_close_timer.start(30000)  # 30 seconds
        
        # Show the message
        msg_box.exec()
        auto_close_timer.stop()
        
        # Close the game dialog
        self.close()
    
    def keyPressEvent(self, event):
        """Forward key events to the game."""
        if hasattr(self, 'game'):
            self.game.keyPressEvent(event)

def show_easter_egg(parent=None):
    """Show the easter egg game dialog."""
    if not PYSIDE6_AVAILABLE:
        return
        
    dialog = EasterEggDialog(parent)
    dialog.exec()