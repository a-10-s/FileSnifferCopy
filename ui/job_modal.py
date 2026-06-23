import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QComboBox, QSpinBox, QTimeEdit,
    QCheckBox, QMessageBox, QFrame, QStackedWidget, QWidget
)
from PySide6.QtCore import Qt, QTime
import database

class JobModal(QDialog):
    def __init__(self, job_id=None, parent=None):
        super().__init__(parent)
        self.job_id = job_id
        self.setWindowTitle("Create Cron Job" if not job_id else "Edit Cron Job")
        self.resize(550, 720)
        self.setModal(True)
        self.init_ui()
        if self.job_id:
            self.load_job_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # Card container
        card = QFrame()
        card.setObjectName("cardFrame")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)

        # Job Name
        name_label = QLabel("Job Identifier Name:")
        name_label.setObjectName("label-sm")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. Render Farm Daily Backup")
        card_layout.addWidget(name_label)
        card_layout.addWidget(self.name_input)

        # Source Directory
        src_label = QLabel("Source Watch Folder (LAN/Local):")
        src_label.setObjectName("label-sm")
        src_row = QHBoxLayout()
        self.src_input = QLineEdit()
        self.src_input.setPlaceholderText("Select folder...")
        src_row.addWidget(self.src_input)
        src_browse = QPushButton("Browse...")
        src_browse.clicked.connect(lambda: self.browse_directory(self.src_input))
        src_row.addWidget(src_browse)
        card_layout.addWidget(src_label)
        card_layout.addLayout(src_row)

        # Destination Directory
        dst_label = QLabel("Destination Output Folder (LAN/Local):")
        dst_label.setObjectName("label-sm")
        dst_row = QHBoxLayout()
        self.dst_input = QLineEdit()
        self.dst_input.setPlaceholderText("Select folder...")
        dst_row.addWidget(self.dst_input)
        dst_browse = QPushButton("Browse...")
        dst_browse.clicked.connect(lambda: self.browse_directory(self.dst_input))
        dst_row.addWidget(dst_browse)
        card_layout.addWidget(dst_label)
        card_layout.addLayout(dst_row)

        # Schedule Row
        sched_row = QHBoxLayout()
        
        sched_type_vbox = QVBoxLayout()
        sched_type_label = QLabel("Sync Schedule:")
        sched_type_label.setObjectName("label-sm")
        self.sched_type_combo = QComboBox()
        self.sched_type_combo.addItems(["Manual", "Interval (Min)", "Daily"])
        self.sched_type_combo.currentTextChanged.connect(self.toggle_schedule_view)
        sched_type_vbox.addWidget(sched_type_label)
        sched_type_vbox.addWidget(self.sched_type_combo)
        sched_row.addLayout(sched_type_vbox)

        # Stacked widget for scheduler inputs
        self.sched_stack = QStackedWidget()
        
        # Manual Widget
        self.manual_widget = QWidget()
        self.sched_stack.addWidget(self.manual_widget)
        
        # Interval Widget
        self.hourly_widget = QWidget()
        hourly_lay = QVBoxLayout(self.hourly_widget)
        hourly_lay.setContentsMargins(0,0,0,0)
        h_label = QLabel("Repeat Interval (Minutes):")
        h_label.setObjectName("label-sm")
        self.hourly_spin = QSpinBox()
        self.hourly_spin.setRange(1, 10080) # 1 minute to 1 week
        self.hourly_spin.setValue(10)       # default 10 minutes
        hourly_lay.addWidget(h_label)
        hourly_lay.addWidget(self.hourly_spin)
        self.sched_stack.addWidget(self.hourly_widget)
        
        # Daily Widget
        self.daily_widget = QWidget()
        daily_lay = QVBoxLayout(self.daily_widget)
        daily_lay.setContentsMargins(0,0,0,0)
        d_label = QLabel("Run Daily At:")
        d_label.setObjectName("label-sm")
        self.daily_time = QTimeEdit()
        self.daily_time.setTime(QTime(18, 0)) # Default 6 PM
        daily_lay.addWidget(d_label)
        daily_lay.addWidget(self.daily_time)
        self.sched_stack.addWidget(self.daily_widget)
        
        sched_row.addWidget(self.sched_stack)
        card_layout.addLayout(sched_row)

        # Copy/Sync Mode Selection
        mode_row = QHBoxLayout()
        mode_lbl = QLabel("Sync Copy Mode:")
        mode_lbl.setObjectName("label-sm")
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Mirror Folder (Brute Force, No Prompts)", "mirror")
        self.mode_combo.addItem("Target Update (Analyze & Confirm Overwrites)", "update")
        mode_row.addWidget(mode_lbl)
        mode_row.addWidget(self.mode_combo, stretch=1)
        card_layout.addLayout(mode_row)

        # Cache Auto-Pruning card
        card_layout.addWidget(QLabel("Cache Auto-Pruning options:"))
        prune_card = QFrame()
        prune_card.setObjectName("innerCard")
        prune_layout = QVBoxLayout(prune_card)
        prune_layout.setSpacing(8)

        self.prune_checkbox = QCheckBox("Enable Auto-Pruning (Clear destination space when low)")
        self.prune_checkbox.stateChanged.connect(self.toggle_prune_fields)
        prune_layout.addWidget(self.prune_checkbox)

        self.prune_settings_widget = QWidget()
        prune_sublayout = QHBoxLayout(self.prune_settings_widget)
        prune_sublayout.setContentsMargins(0, 0, 0, 0)
        prune_sublayout.setSpacing(8)
        
        prune_lbl = QLabel("Min Destination Free Space (GB):")
        prune_lbl.setObjectName("label-sm")
        self.prune_spin = QSpinBox()
        self.prune_spin.setRange(1, 10000)
        self.prune_spin.setValue(20)
        prune_sublayout.addWidget(prune_lbl)
        prune_sublayout.addWidget(self.prune_spin)
        prune_layout.addWidget(self.prune_settings_widget)
        card_layout.addWidget(prune_card)

        # Automated Proxy Generation card
        card_layout.addWidget(QLabel("Automated Proxy options:"))
        proxy_card = QFrame()
        proxy_card.setObjectName("innerCard")
        proxy_layout = QVBoxLayout(proxy_card)
        proxy_layout.setSpacing(8)

        self.proxy_checkbox = QCheckBox("Enable MP4 Review Proxy Generation (Post-Sync)")
        self.proxy_checkbox.stateChanged.connect(self.toggle_proxy_fields)
        proxy_layout.addWidget(self.proxy_checkbox)

        self.proxy_settings_widget = QWidget()
        proxy_sublayout = QHBoxLayout(self.proxy_settings_widget)
        proxy_sublayout.setContentsMargins(0, 0, 0, 0)
        proxy_sublayout.setSpacing(8)
        
        fps_lbl = QLabel("Proxy Framerate (FPS):")
        fps_lbl.setObjectName("label-sm")
        self.proxy_fps_spin = QSpinBox()
        self.proxy_fps_spin.setRange(1, 120)
        self.proxy_fps_spin.setValue(24)
        proxy_sublayout.addWidget(fps_lbl)
        proxy_sublayout.addWidget(self.proxy_fps_spin)
        proxy_layout.addWidget(self.proxy_settings_widget)
        card_layout.addWidget(proxy_card)
        
        layout.addWidget(card)

        # Dialog Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("Save Cron Job")
        save_btn.setObjectName("primaryBtn")
        save_btn.clicked.connect(self.save_job)
        btn_row.addWidget(save_btn)

        layout.addLayout(btn_row)
        
        # Default state
        self.toggle_prune_fields(Qt.Unchecked)
        self.toggle_proxy_fields(Qt.Unchecked)

    def browse_directory(self, line_edit):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Folder", line_edit.text())
        if dir_path:
            line_edit.setText(os.path.normpath(dir_path))

    def toggle_schedule_view(self, text):
        if text == "Manual":
            self.sched_stack.setCurrentWidget(self.manual_widget)
        elif text in ("Interval (Min)", "Hourly", "Interval"):
            self.sched_stack.setCurrentWidget(self.hourly_widget)
        elif text == "Daily":
            self.sched_stack.setCurrentWidget(self.daily_widget)



    def toggle_prune_fields(self, state):
        enabled = self.prune_checkbox.isChecked()
        self.prune_settings_widget.setEnabled(enabled)

    def toggle_proxy_fields(self, state):
        enabled = self.proxy_checkbox.isChecked()
        self.proxy_settings_widget.setEnabled(enabled)

    def load_job_data(self):
        job = database.get_job(self.job_id)
        if job:
            self.name_input.setText(job['name'])
            self.src_input.setText(job['source'])
            self.dst_input.setText(job['destination'])
            
            sched_type = job['schedule_type']
            if sched_type in ('Interval', 'Interval (Min)', 'Hourly'):
                self.sched_type_combo.setCurrentText("Interval (Min)")
                self.hourly_spin.setValue(int(job['schedule_value'] or 10))
            else:
                self.sched_type_combo.setCurrentText(sched_type)
            
            if sched_type == 'Daily':
                t_str = job['schedule_value'] or "18:00"
                try:
                    h, m = map(int, t_str.split(':'))
                    self.daily_time.setTime(QTime(h, m))
                except Exception:
                    self.daily_time.setTime(QTime(18, 0))
                    

            self.prune_checkbox.setChecked(job['prune_enabled'] == 1)
            self.prune_spin.setValue(int(job['prune_threshold_gb'] or 20))
            self.proxy_checkbox.setChecked(job['proxy_enabled'] == 1)
            self.proxy_fps_spin.setValue(int(job['proxy_fps'] or 24))
            
            sync_mode = job.get('sync_mode', 'mirror')
            idx = self.mode_combo.findData(sync_mode)
            if idx != -1:
                self.mode_combo.setCurrentIndex(idx)

    def save_job(self):
        name = self.name_input.text().strip()
        source = self.src_input.text().strip()
        destination = self.dst_input.text().strip()
        sched_type = self.sched_type_combo.currentText()
        
        if not name or not source or not destination:
            QMessageBox.critical(self, "Invalid Inputs", "Name, Source, and Destination are required.")
            return

        if not os.path.exists(source):
            QMessageBox.warning(self, "Invalid Path", f"Source path '{source}' does not exist.")
            return
            
        if source == destination:
            QMessageBox.critical(self, "Invalid Paths", "Source and Destination paths cannot be identical.")
            return

        # Compute schedule value and type
        if sched_type in ("Interval (Min)", "Hourly", "Interval"):
            sched_val = str(self.hourly_spin.value())
            save_type = "Interval"
        elif sched_type == "Daily":
            sched_val = self.daily_time.time().toString("HH:mm")
            save_type = "Daily"
        else:
            sched_val = ""
            save_type = "Manual"

        convert_enabled = 0
        convert_extensions = ""
        target_compression = ""
        prune_enabled = 1 if self.prune_checkbox.isChecked() else 0
        prune_threshold = self.prune_spin.value()
        proxy_enabled = 1 if self.proxy_checkbox.isChecked() else 0
        proxy_fps = self.proxy_fps_spin.value()
        sync_mode = self.mode_combo.currentData() or 'mirror'

        if self.job_id:
            # Edit Mode (keep active status as is)
            job = database.get_job(self.job_id)
            active = job['active'] if job else 1
            database.update_job(
                self.job_id, name, source, destination, save_type, sched_val,
                convert_enabled, convert_extensions, target_compression, active,
                prune_enabled, prune_threshold, proxy_enabled, proxy_fps, sync_mode
            )
        else:
            # Add Mode
            database.add_job(
                name, source, destination, save_type, sched_val,
                convert_enabled, convert_extensions, target_compression,
                prune_enabled, prune_threshold, proxy_enabled, proxy_fps, sync_mode
            )

        self.accept()
