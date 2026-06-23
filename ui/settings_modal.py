import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QSpinBox, QMessageBox, QFrame
)
from PySide6.QtCore import Qt
import database

class SettingsModal(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Global Configuration Settings")
        self.resize(550, 400)
        self.setModal(True)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Card container
        card = QFrame()
        card.setObjectName("cardFrame")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)

        # Title/Description
        desc_label = QLabel("Configure engine preferences and FFmpeg pathways.")
        desc_label.setObjectName("subtitleLabel")
        card_layout.addWidget(desc_label)

        # FFmpeg Path
        ffmpeg_label = QLabel("Path to ffmpeg.exe:")
        ffmpeg_label.setObjectName("label-sm")
        card_layout.addWidget(ffmpeg_label)

        ffmpeg_row = QHBoxLayout()
        self.ffmpeg_input = QLineEdit()
        self.ffmpeg_input.setPlaceholderText("e.g. ffmpeg or C:/path/to/ffmpeg.exe")
        self.ffmpeg_input.setText(str(database.get_setting("ffmpeg_path", "ffmpeg")))
        ffmpeg_row.addWidget(self.ffmpeg_input)

        ffmpeg_browse_btn = QPushButton("Browse...")
        ffmpeg_browse_btn.clicked.connect(self.browse_ffmpeg)
        ffmpeg_row.addWidget(ffmpeg_browse_btn)

        ffmpeg_test_btn = QPushButton("Test Binary")
        ffmpeg_test_btn.clicked.connect(self.test_ffmpeg)
        ffmpeg_row.addWidget(ffmpeg_test_btn)
        card_layout.addLayout(ffmpeg_row)

        # Grid-like configuration values
        settings_grid = QHBoxLayout()
        
        # Settle Time
        vbox_settle = QVBoxLayout()
        settle_label = QLabel("File Settle Time (sec):")
        settle_label.setObjectName("label-sm")
        self.settle_spin = QSpinBox()
        self.settle_spin.setRange(5, 3600)
        self.settle_spin.setValue(int(database.get_setting("settle_time_seconds", 60)))
        vbox_settle.addWidget(settle_label)
        vbox_settle.addWidget(self.settle_spin)
        settings_grid.addLayout(vbox_settle)

        # Concurrency Threads
        vbox_threads = QVBoxLayout()
        threads_label = QLabel("Max Worker Threads:")
        threads_label.setObjectName("label-sm")
        self.threads_spin = QSpinBox()
        self.threads_spin.setRange(1, 32)
        self.threads_spin.setValue(int(database.get_setting("max_threads", 4)))
        vbox_threads.addWidget(threads_label)
        vbox_threads.addWidget(self.threads_spin)
        settings_grid.addLayout(vbox_threads)

        # Core Tick Rate (Polling Interval)
        vbox_poll = QVBoxLayout()
        poll_label = QLabel("Folder Scan Tick (sec):")
        poll_label.setObjectName("label-sm")
        self.poll_spin = QSpinBox()
        self.poll_spin.setRange(10, 86400)
        self.poll_spin.setValue(int(database.get_setting("poll_interval_seconds", 30)))
        vbox_poll.addWidget(poll_label)
        vbox_poll.addWidget(self.poll_spin)
        settings_grid.addLayout(vbox_poll)

        card_layout.addLayout(settings_grid)
        layout.addWidget(card)

        # Dialog buttons (Save/Cancel)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("Save Settings")
        save_btn.setObjectName("primaryBtn")
        save_btn.clicked.connect(self.save_settings)
        btn_row.addWidget(save_btn)

        layout.addLayout(btn_row)



    def browse_ffmpeg(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Locate FFmpeg Executable", "", "Executable Files (*.exe);;All Files (*)"
        )
        if file_path:
            self.ffmpeg_input.setText(os.path.normpath(file_path))

    def test_ffmpeg(self):
        path = self.ffmpeg_input.text().strip()
        # Import dynamically to avoid unused import at top
        import transcoder
        ok, msg = transcoder.verify_ffmpeg(path)
        if ok:
            QMessageBox.information(self, "Validation Success", f"Success!\n{msg}")
        else:
            QMessageBox.critical(self, "Validation Failed", f"Failed!\n{msg}")

    def save_settings(self):
        database.set_setting("ffmpeg_path", self.ffmpeg_input.text().strip())
        database.set_setting("settle_time_seconds", self.settle_spin.value())
        database.set_setting("max_threads", self.threads_spin.value())
        database.set_setting("poll_interval_seconds", self.poll_spin.value())
        self.accept()

