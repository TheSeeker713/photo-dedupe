"""
Clean end section for theme_settings_dialog.py
"""

        def reject(self):
            """Close dialog without applying changes."""
            reply = QMessageBox.question(
                self, "Discard Changes",
                "Are you sure you want to discard your changes?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                super().reject()


    def show_theme_settings_dialog(parent=None):
        """Show the theme settings dialog."""
        dialog = ThemeSettingsDialog(parent)
        return dialog


else:
    # Dummy implementations for when Qt is not available
    class ThemeSettingsDialog:
        """Dummy theme settings dialog."""
        def __init__(self, parent=None):
            pass
    
    def show_theme_settings_dialog(parent=None):
        """Dummy show theme settings dialog."""
        print("Theme settings dialog not available (Qt not available)")
        return None