import os
import sys
import time
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QFrame, QTableWidget, QTableWidgetItem,
    QProgressBar, QHeaderView, QMessageBox, QDialog
)
from PySide6.QtCore import Qt, QTimer, Signal, QObject
from PySide6.QtGui import QIcon

import database
import engine
from ui.job_modal import JobModal
from ui.settings_modal import SettingsModal
from ui.styles import get_stylesheet

class SyncSignals(QObject):
    """Thread-safe signals to update GUI from background threads."""
    progress_signal = Signal(int, str, str, int, int) # job_id, rel_path, status, bytes_tx, bytes_saved
    finished_signal = Signal(int, bool, str) # job_id, success, message
    scan_finished_signal = Signal(int, list, str) # job_id, pending_files, error_message

# Instantiate global sync signals
sync_signals = SyncSignals()

class JobCard(QFrame):
    """Custom card widget for displaying a single sync job."""
    def __init__(self, job, parent_dashboard):
        super().__init__()
        self.job = job
        self.dashboard = parent_dashboard
        self.setObjectName("cardFrame")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(12, 12, 12, 12)

        # Header Row (Title and Status)
        header = QHBoxLayout()
        self.title_label = QLabel(self.job['name'])
        self.title_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #FF6B00;")
        header.addWidget(self.title_label)
        
        header.addStretch()

        self.status_label = QLabel()
        header.addWidget(self.status_label)
        layout.addLayout(header)

        # Paths Info — explore button LEFT of label, scaled up
        paths_layout = QVBoxLayout()
        paths_layout.setSpacing(6)
        
        src_row = QHBoxLayout()
        src_row.setSpacing(6)
        src_explore = QPushButton("📂")
        src_explore.setObjectName("exploreBtn")
        src_explore.setToolTip("Open Source Folder in File Explorer")
        src_explore.setFixedSize(28, 24)
        src_explore.clicked.connect(lambda: self.explore_path(self.job['source']))
        src_lbl = QLabel(f"Source: {self.job['source']}")
        src_lbl.setObjectName("label-sm")
        src_lbl.setStyleSheet("color: #A1A1AA;")
        src_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        src_row.addWidget(src_explore)
        src_row.addWidget(src_lbl, 1)
        paths_layout.addLayout(src_row)

        dst_row = QHBoxLayout()
        dst_row.setSpacing(6)
        dst_explore = QPushButton("📂")
        dst_explore.setObjectName("exploreBtn")
        dst_explore.setToolTip("Open Destination Folder in File Explorer")
        dst_explore.setFixedSize(28, 24)
        dst_explore.clicked.connect(lambda: self.explore_path(self.job['destination']))
        dst_lbl = QLabel(f"Dest: {self.job['destination']}")
        dst_lbl.setObjectName("label-sm")
        dst_lbl.setStyleSheet("color: #A1A1AA;")
        dst_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        dst_row.addWidget(dst_explore)
        dst_row.addWidget(dst_lbl, 1)
        paths_layout.addLayout(dst_row)

        layout.addLayout(paths_layout)

        # Settings and Schedule Summary
        summary = []
        sched_t = self.job['schedule_type']
        if sched_t == 'Interval':
            summary.append(f"Sched: Interval ({self.job['schedule_value']} Min)")
        else:
            summary.append(f"Sched: {sched_t}")
            if self.job['schedule_value']:
                summary.append(f"({self.job['schedule_value']})")
            
        summary_lbl = QLabel(" | ".join(summary))
        summary_lbl.setObjectName("label-sm")
        summary_lbl.setStyleSheet("color: #71717A; font-style: italic;")
        layout.addWidget(summary_lbl)

        # Progress bar (starts hidden)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Live sync info: current file + speed (starts hidden)
        self.sync_info_row = QHBoxLayout()
        self.current_file_label = QLabel()
        self.current_file_label.setObjectName("label-sm")
        self.current_file_label.setStyleSheet("color: #00E5FF;")
        self.current_file_label.setVisible(False)
        self.speed_label = QLabel()
        self.speed_label.setObjectName("label-sm")
        self.speed_label.setStyleSheet("color: #A1A1AA; font-weight: bold;")
        self.speed_label.setVisible(False)
        self.sync_info_row.addWidget(self.current_file_label, 1)
        self.sync_info_row.addWidget(self.speed_label)
        layout.addLayout(self.sync_info_row)

        # Buttons/Actions Row
        actions = QHBoxLayout()
        
        self.sync_btn = QPushButton("Run Now")
        self.sync_btn.setObjectName("primaryBtn")
        self.sync_btn.clicked.connect(self.trigger_sync)
        actions.addWidget(self.sync_btn)

        self.toggle_active_btn = QPushButton()
        self.update_active_button_label()
        self.toggle_active_btn.clicked.connect(self.toggle_active)
        actions.addWidget(self.toggle_active_btn)

        self.edit_btn = QPushButton("Edit")
        self.edit_btn.clicked.connect(self.edit_job)
        actions.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setObjectName("dangerBtn")
        self.delete_btn.clicked.connect(self.delete_job)
        actions.addWidget(self.delete_btn)

        self.details_btn = QPushButton("Details 📊")
        self.details_btn.clicked.connect(self.open_progress_monitor)
        actions.addWidget(self.details_btn)

        layout.addLayout(actions)
        self.update_status_display()


    def update_status_display(self):
        job_id = self.job['id']
        
        # Check if job is currently running in the engine
        running_info = None
        with engine.active_syncs_lock:
            running_info = engine.active_syncs.get(job_id)

        if running_info:
            self.status_label.setText("Running...")
            self.status_label.setStyleSheet("color: #00E5FF; font-weight: bold;")
            
            # Switch button to Stop Copying
            if running_info.get('cancel_requested', False):
                self.sync_btn.setText("Cancelling...")
                self.sync_btn.setEnabled(False)
            else:
                self.sync_btn.setText("Stop Copying")
                self.sync_btn.setEnabled(True)
                self.sync_btn.setObjectName("dangerBtn")
                self.sync_btn.style().unpolish(self.sync_btn)
                self.sync_btn.style().polish(self.sync_btn)
        else:
            if not self.job['active']:
                self.status_label.setText("Paused")
                self.status_label.setStyleSheet("color: #71717A; font-weight: bold;")
            else:
                self.status_label.setText("Idle")
                self.status_label.setStyleSheet("color: #10B981; font-weight: bold;")
                
            # Restore button to Run Now
            self.sync_btn.setText("Run Now")
            self.sync_btn.setEnabled(True)
            self.sync_btn.setObjectName("primaryBtn")
            self.sync_btn.style().unpolish(self.sync_btn)
            self.sync_btn.style().polish(self.sync_btn)

    def update_active_button_label(self):
        if self.job['active']:
            self.toggle_active_btn.setText("Pause Cron")
        else:
            self.toggle_active_btn.setText("Resume Cron")

    def toggle_active(self):
        new_state = 0 if self.job['active'] else 1
        database.update_job(
            self.job['id'], self.job['name'], self.job['source'], self.job['destination'],
            self.job['schedule_type'], self.job['schedule_value'], self.job['convert_enabled'],
            self.job['convert_extensions'], self.job['target_compression'], new_state,
            self.job.get('prune_enabled', 0), self.job.get('prune_threshold_gb', 20.0),
            self.job.get('proxy_enabled', 0), self.job.get('proxy_fps', 24),
            self.job.get('sync_mode', 'mirror')
        )
        self.job['active'] = new_state
        self.update_status_display()
        self.update_active_button_label()
        self.dashboard.refresh_stats()

    def edit_job(self):
        # Open edit modal
        modal = JobModal(self.job['id'], self)
        if modal.exec() == JobModal.Accepted:
            self.dashboard.refresh_jobs()

    def delete_job(self):
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete job '{self.job['name']}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            database.delete_job(self.job['id'])
            self.dashboard.refresh_jobs()

    def start_sync_execution(self, selected_files=None):
        job_id = self.job['id']
        sync_mode = self.job.get('sync_mode', 'mirror')
        
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.current_file_label.setText("Starting selective updates..." if selected_files is not None else "Scanning directory...")
        self.current_file_label.setVisible(True)
        self.status_label.setText("Running...")
        self.status_label.setStyleSheet("color: #00E5FF; font-weight: bold;")
        
        # Helper callbacks that push updates to main thread via Signals
        def prog_cb(rel_path, status, bytes_tx, bytes_saved, err_msg=None):
            sync_signals.progress_signal.emit(job_id, rel_path, status, bytes_tx, bytes_saved)
            
        def fin_cb(job_id, success, message):
            sync_signals.finished_signal.emit(job_id, success, message)
            
        engine.sync_job(job_id, prog_cb, fin_cb, files_to_sync=selected_files)
        self.update_status_display()
        
        if sync_mode == 'update':
            self.open_progress_monitor()

    def trigger_sync(self):
        job_id = self.job['id']
        
        # Check if running
        with engine.active_syncs_lock:
            is_running = job_id in engine.active_syncs
            cancel_requested = engine.active_syncs.get(job_id, {}).get('cancel_requested', False) if is_running else False
            
        if is_running:
            if not cancel_requested:
                # Request cancel
                engine.request_cancel_sync(job_id)
                self.update_status_display()
        else:
            # Check copy mode
            sync_mode = self.job.get('sync_mode', 'mirror')
            
            if sync_mode == 'update':
                self.sync_btn.setText("Scanning...")
                self.sync_btn.setEnabled(False)
                self.status_label.setText("Scanning...")
                self.status_label.setStyleSheet("color: #00E5FF; font-weight: bold;")
                
                import threading
                def run_scan():
                    try:
                        pending_files = engine.scan_job_files(self.job)
                        sync_signals.scan_finished_signal.emit(job_id, pending_files, "")
                    except Exception as e:
                        sync_signals.scan_finished_signal.emit(job_id, [], str(e))
                        
                t = threading.Thread(target=run_scan, daemon=True)
                t.start()
            else:
                self.start_sync_execution(None)

    def handle_scan_finished(self, pending_files, error_msg):
        self.sync_btn.setText("Run Now")
        self.sync_btn.setEnabled(True)
        self.update_status_display()
        
        if error_msg:
            QMessageBox.critical(self, "Scan Error", f"Failed to scan source directory:\n{error_msg}")
            return
            
        if not pending_files:
            QMessageBox.information(self, "Sync Up to Date", "All files in the destination directory are fully up to date.")
            return
            
        from ui.analysis_window import AnalysisWindow
        analysis = AnalysisWindow(self.job, pending_files, self.dashboard)
        if analysis.exec() == QDialog.Accepted:
            selected_files = analysis.selected_files
            self.start_sync_execution(selected_files)

    def update_progress(self, processed, total, current_file):
        # Pull live speed from engine
        live_speed_mb = 0.0
        with engine.active_syncs_lock:
            info = engine.active_syncs.get(self.job['id'])
            if info:
                elapsed = max(0.001, time.time() - info.get('start_time', time.time()))
                bytes_tx = info.get('bytes_transferred', 0)
                live_speed_mb = (bytes_tx / elapsed) / (1024 ** 2)

        if total > 0:
            percentage = int((processed / total) * 100)
            self.progress_bar.setValue(percentage)
            file_text = f"[{processed}/{total}] {current_file}" if current_file else f"[{processed}/{total}] Processing..."
            self.current_file_label.setText(file_text)
            self.current_file_label.setVisible(True)
            self.speed_label.setText(f"⚡ {live_speed_mb:.2f} MB/s")
            self.speed_label.setVisible(True)
        else:
            self.progress_bar.setValue(100)
            self.current_file_label.setText("Scanning...")
            self.current_file_label.setVisible(True)
            self.speed_label.setVisible(False)
            
        self.update_status_display()

    def reset_progress(self):
        self.progress_bar.setVisible(False)
        self.current_file_label.setVisible(False)
        self.speed_label.setVisible(False)
        self.sync_btn.setText("Run Now")
        self.sync_btn.setEnabled(True)
        self.update_status_display()

    def explore_path(self, path):
        import os
        normalized = os.path.normpath(path)
        if os.path.exists(normalized):
            try:
                os.startfile(normalized)
            except Exception as e:
                QMessageBox.critical(self, "Explorer Error", f"Could not open directory: {str(e)}")
        else:
            QMessageBox.warning(self, "Path Not Found", f"The directory '{normalized}' does not exist.")

    def mouseDoubleClickEvent(self, event):
        self.open_progress_monitor()

    def open_progress_monitor(self):
        from ui.progress_window import ProgressWindow
        job_id = self.job['id']
        # Check if a window for this job is already open
        existing = self.dashboard.progress_windows.get(job_id)
        if existing is not None and existing.isVisible():
            # Bring it to front
            existing.raise_()
            existing.activateWindow()
            return
        # Create new modeless window
        win = ProgressWindow(job_id, self.dashboard)
        win.setAttribute(Qt.WA_DeleteOnClose, True)
        win.destroyed.connect(lambda: self.dashboard.progress_windows.pop(job_id, None))
        self.dashboard.progress_windows[job_id] = win
        win.show()



class DashboardWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FileSniffer Control Panel")
        self.resize(950, 720)

        
        self.job_cards = {}
        self.last_scheduler_check = 0
        # Track open modeless progress windows keyed by job_id
        self.progress_windows = {}

        self.load_cached_settings()

        self.init_ui()
        self.setup_signals()

    def load_cached_settings(self):
        self.poll_interval = database.get_setting("poll_interval_seconds", 30)

    def update_global_progress(self):
        with engine.active_syncs_lock:
            active_jobs = list(engine.active_syncs.values())
            
        if not active_jobs:
            self.global_progress_container.setVisible(False)
            return
            
        total_processed = 0
        total_files = 0
        
        for info in active_jobs:
            total_processed += info.get('processed_files', 0)
            total_files += info.get('total_files', 0)
            
        if total_files > 0:
            percentage = int((total_processed / total_files) * 100)
            self.global_progress_bar.setValue(percentage)
            self.global_progress_label.setText(f"Overall Sync Progress: {percentage}% ({total_processed}/{total_files} files)")
        else:
            self.global_progress_bar.setValue(0)
            self.global_progress_label.setText("Overall Sync Progress: Scanning...")
            
        self.global_progress_container.setVisible(True)
        
        # Background ticks timer (1 second interval)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.on_tick)
        self.timer.start(1000)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        # Header Row
        header = QHBoxLayout()
        header.setSpacing(10)
        
        # Branded logo next to the title
        logo_label = QLabel()
        logo_path = Path(__file__).resolve().parent / "resources" / "logo.svg"
        if logo_path.exists():
            logo_pix = QIcon(str(logo_path)).pixmap(28, 28)
            logo_label.setPixmap(logo_pix)
        header.addWidget(logo_label)

        title_box = QVBoxLayout()
        title = QLabel("FileSniffer")
        title.setObjectName("titleLabel")
        subtitle = QLabel("Background File Sync & Transcoding Utility for Content Studios")
        subtitle.setObjectName("subtitleLabel")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box)
        header.addStretch()

        add_job_btn = QPushButton("New Cron Job")
        add_job_btn.setObjectName("primaryBtn")
        add_job_btn.clicked.connect(self.open_new_job_modal)
        header.addWidget(add_job_btn)

        log_btn = QPushButton("View History Log 📋")
        log_btn.clicked.connect(self.open_log_window)
        header.addWidget(log_btn)

        settings_btn = QPushButton("Settings")
        settings_btn.clicked.connect(self.open_settings_modal)
        header.addWidget(settings_btn)
        main_layout.addLayout(header)


        # Stats Panel
        stats_layout = QHBoxLayout()
        
        self.stat_jobs = QFrame()
        self.stat_jobs.setObjectName("cardFrame")
        self.stat_jobs_layout = QVBoxLayout(self.stat_jobs)
        self.lbl_jobs_val = QLabel("0")
        self.lbl_jobs_val.setStyleSheet("font-size: 24px; font-weight: bold; color: #FF6B00;")
        self.stat_jobs_layout.addWidget(QLabel("Active Cron Jobs"))
        self.stat_jobs_layout.addWidget(self.lbl_jobs_val)
        stats_layout.addWidget(self.stat_jobs)

        self.stat_saved = QFrame()
        self.stat_saved.setObjectName("cardFrame")
        self.stat_saved_layout = QVBoxLayout(self.stat_saved)
        self.lbl_saved_val = QLabel("0 GB")
        self.lbl_saved_val.setStyleSheet("font-size: 24px; font-weight: bold; color: #00E5FF;")
        self.stat_saved_layout.addWidget(QLabel("Total Disk Space Reclaimed"))
        self.stat_saved_layout.addWidget(self.lbl_saved_val)
        stats_layout.addWidget(self.stat_saved)

        self.stat_status = QFrame()
        self.stat_status.setObjectName("cardFrame")
        self.stat_status_layout = QVBoxLayout(self.stat_status)
        self.lbl_status_val = QLabel("All schedules running")
        self.lbl_status_val.setStyleSheet("font-size: 16px; font-weight: bold; color: #10B981; margin-top: 8px;")
        self.stat_status_layout.addWidget(QLabel("System Status"))
        self.stat_status_layout.addWidget(self.lbl_status_val)
        stats_layout.addWidget(self.stat_status)

        main_layout.addLayout(stats_layout)

        # Global Progress Bar (visible only when syncing)
        self.global_progress_container = QFrame()
        self.global_progress_container.setObjectName("cardFrame")
        self.global_progress_container.setStyleSheet("background-color: #111115; border-color: #FF6B00;")
        global_progress_layout = QVBoxLayout(self.global_progress_container)
        global_progress_layout.setContentsMargins(12, 12, 12, 12)
        global_progress_layout.setSpacing(6)
        
        self.global_progress_label = QLabel("Overall Sync Progress: 0%")
        self.global_progress_label.setStyleSheet("color: #E4E4E7; font-weight: bold;")
        global_progress_layout.addWidget(self.global_progress_label)
        
        self.global_progress_bar = QProgressBar()
        self.global_progress_bar.setFixedHeight(18)
        self.global_progress_bar.setValue(0)
        global_progress_layout.addWidget(self.global_progress_bar)
        
        self.global_progress_container.setVisible(False)
        main_layout.addWidget(self.global_progress_container)

        # Scrollable Job Cards Panel
        jobs_vbox = QVBoxLayout()
        jobs_header = QLabel("Cron Jobs")
        jobs_header.setObjectName("sectionHeader")
        jobs_vbox.addWidget(jobs_header)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        
        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("scrollContent")
        self.scroll_content_layout = QVBoxLayout(self.scroll_content)
        self.scroll_content_layout.setSpacing(12)
        self.scroll_content_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_content_layout.addStretch()
        self.scroll_area.setWidget(self.scroll_content)
        
        jobs_vbox.addWidget(self.scroll_area)
        main_layout.addLayout(jobs_vbox, stretch=1)
        
        # Load Initial Data
        self.refresh_jobs()
        self.refresh_stats()


    def setup_signals(self):
        # Bind thread-safe Signals to UI updates
        sync_signals.progress_signal.connect(self.on_sync_progress)
        sync_signals.finished_signal.connect(self.on_sync_finished)
        sync_signals.scan_finished_signal.connect(self.on_scan_finished)

    def refresh_jobs(self):
        # Clear existing layout (excluding the stretch at the bottom)
        # Delete old widgets
        for card in list(self.job_cards.values()):
            card.setParent(None)
            card.deleteLater()
        self.job_cards.clear()

        jobs = database.get_all_jobs()
        
        # Insert them into scroll container layout
        for job in jobs:
            card = JobCard(job, self)
            self.job_cards[job['id']] = card
            # Insert at the top (before the stretch element)
            self.scroll_content_layout.insertWidget(self.scroll_content_layout.count() - 1, card)

        self.refresh_stats()

    def refresh_stats(self):
        jobs = database.get_all_jobs()
        active_jobs = sum(1 for j in jobs if j['active'])
        self.lbl_jobs_val.setText(str(active_jobs))
        
        # Reclaimed bytes
        total_saved_bytes = database.get_total_savings()
        # Convert bytes to human readable (GB / MB)
        if total_saved_bytes >= 1024**3:
            saved_str = f"{total_saved_bytes / (1024**3):.2f} GB"
        elif total_saved_bytes >= 1024**2:
            saved_str = f"{total_saved_bytes / (1024**2):.2f} MB"
        else:
            saved_str = f"{total_saved_bytes / 1024:.2f} KB"
        self.lbl_saved_val.setText(saved_str)

        # System Running Status
        with engine.active_syncs_lock:
            running_count = len(engine.active_syncs)
        if running_count > 0:
            self.lbl_status_val.setText(f"Running {running_count} cron job(s)")
            self.lbl_status_val.setStyleSheet("color: #00E5FF; font-weight: bold;")
        elif active_jobs > 0:
            self.lbl_status_val.setText("All schedules active")
            self.lbl_status_val.setStyleSheet("color: #10B981; font-weight: bold;")
        else:
            self.lbl_status_val.setText("All schedules paused")
            self.lbl_status_val.setStyleSheet("color: #71717A; font-weight: bold;")

    def open_log_window(self):
        from ui.log_window import LogWindow
        if not hasattr(self, 'log_window') or self.log_window is None:
            self.log_window = LogWindow(self)
        self.log_window.show()
        self.log_window.raise_()
        self.log_window.activateWindow()


    def open_new_job_modal(self):
        modal = JobModal(parent=self)
        if modal.exec() == JobModal.Accepted:
            self.refresh_jobs()

    def open_settings_modal(self):
        modal = SettingsModal(parent=self)
        if modal.exec() == QDialog.Accepted:
            self.load_cached_settings()

    # --- Live thread signals slots ---

    def on_sync_progress(self, job_id, rel_path, status, bytes_tx, bytes_saved):
        # Pull live thread progress details from engine
        running_info = None
        with engine.active_syncs_lock:
            running_info = engine.active_syncs.get(job_id)
            
        if running_info and job_id in self.job_cards:
            processed = running_info['processed_files']
            total = running_info['total_files']
            current = running_info['current_file']
            self.job_cards[job_id].update_progress(processed, total, current)
            
        self.update_global_progress()

    def on_sync_finished(self, job_id, success, message):
        if job_id in self.job_cards:
            self.job_cards[job_id].reset_progress()
            
        self.refresh_stats()
        if hasattr(self, 'log_window') and self.log_window is not None and self.log_window.isVisible():
            self.log_window.refresh_logs()
        self.update_global_progress()

    def on_scan_finished(self, job_id, pending_files, error_msg):
        if job_id in self.job_cards:
            self.job_cards[job_id].handle_scan_finished(pending_files, error_msg)

    # --- Core Scheduler Trigger Tick ---

    def on_tick(self):
        # 1. Update running timers or progress bars if files are being processed
        with engine.active_syncs_lock:
            for job_id, info in list(engine.active_syncs.items()):
                if job_id in self.job_cards:
                    self.job_cards[job_id].update_progress(
                        info['processed_files'], info['total_files'], info['current_file']
                    )

        # 2. Check schedules at configured intervals
        curr_time = time.time()
        
        if curr_time - self.last_scheduler_check >= self.poll_interval:
            self.last_scheduler_check = curr_time
            
            # Call engine check with progress and completion callbacks
            def prog_cb(rel_path, status, bytes_tx, bytes_saved):
                # Signals allow crossing thread boundaries
                sync_signals.progress_signal.emit(0, rel_path, status, bytes_tx, bytes_saved)
                
            def fin_cb(job_id, success, message):
                sync_signals.finished_signal.emit(job_id, success, message)
                
            engine.check_and_run_schedules(prog_cb, fin_cb)
            self.refresh_stats()

    # System Tray Interceptor Override
    def closeEvent(self, event):
        # Intercept close click to minimize to tray instead of quitting
        event.ignore()
        self.hide()
        # Trigger tray alert via parent application tray controller
        tray_app = QWidget.find(self.winId())
        # We will handle showing balloon message in main.py tray logic
