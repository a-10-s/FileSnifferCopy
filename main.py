import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QPainter, QColor, QPen, QBrush
from PySide6.QtCore import Qt

import database
from ui.dashboard import DashboardWindow
from ui.styles import get_stylesheet

class FileSnifferApp(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        # Prevent exit when last window is closed (important for tray minimize)
        self.setQuitOnLastWindowClosed(False)

        # Set stylesheet globally
        self.setStyleSheet(get_stylesheet())

        # Set global window icon using our SVG logo
        logo_path = Path(__file__).resolve().parent / "ui" / "resources" / "logo.svg"
        if logo_path.exists():
            self.setWindowIcon(QIcon(str(logo_path)))

        # Initialize main window
        self.window = DashboardWindow()


        # Initialize system tray
        self.setup_tray()

        # Show window initially
        self.window.show()

    def create_tray_icon(self):
        """Create a custom-painted tray icon (orange circle with crosshair) so we don't depend on external assets."""
        from PySide6.QtGui import QPixmap
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw background circle (Slate surfaces color)
        painter.setBrush(QBrush(QColor("#18181B")))
        painter.setPen(QPen(QColor("#27272A"), 1.5))
        painter.drawEllipse(2, 2, 28, 28)
        
        # Draw inner indicator circle (Cyber Orange)
        painter.setBrush(QBrush(QColor("#FF6B00")))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(9, 9, 14, 14)
        
        # Draw simple crosshair notches
        painter.setPen(QPen(QColor("#00E5FF"), 2))
        painter.drawLine(16, 4, 16, 8)
        painter.drawLine(16, 24, 16, 28)
        painter.drawLine(4, 16, 8, 16)
        painter.drawLine(24, 16, 28, 16)
        
        painter.end()
        return QIcon(pixmap)

    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        logo_path = Path(__file__).resolve().parent / "ui" / "resources" / "logo.svg"
        if logo_path.exists():
            self.tray_icon.setIcon(QIcon(str(logo_path)))
        else:
            self.tray_icon.setIcon(self.create_tray_icon())
        self.tray_icon.setToolTip("FileSniffer Service")

        # Context Menu
        menu = QMenu()
        
        open_action = menu.addAction("Restore Dashboard")
        open_action.triggered.connect(self.show_dashboard)

        sync_all_action = menu.addAction("Sync All Jobs Now")
        sync_all_action.triggered.connect(self.sync_all_jobs)

        menu.addSeparator()
        
        exit_action = menu.addAction("Exit FileSniffer")
        exit_action.triggered.connect(self.exit_app)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

        # Override close behavior in the main window to call our custom hide
        self.window.closeEvent = self.on_window_close_clicked

    def show_dashboard(self):
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()

    def sync_all_jobs(self):
        jobs = database.get_all_jobs()
        for job in jobs:
            if job['active'] and job['id'] in self.window.job_cards:
                self.window.job_cards[job['id']].trigger_sync()

    def on_tray_activated(self, reason):
        # Double-click or click on tray icon restores the UI dashboard
        if reason in (QSystemTrayIcon.DoubleClick, QSystemTrayIcon.Trigger):
            self.show_dashboard()

    def on_window_close_clicked(self, event):
        # Prevent window closing and hide it instead
        event.ignore()
        self.window.hide()
        
        # Show tray notification balloon if first time or as reminder
        self.tray_icon.showMessage(
            "FileSniffer",
            "FileSniffer is running in the background system tray.",
            QSystemTrayIcon.Information,
            3000
        )

    def exit_app(self):
        self.tray_icon.hide()
        self.quit()

if __name__ == "__main__":
    app = FileSnifferApp(sys.argv)
    sys.exit(app.exec())
