import time
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QProgressBar, QFrame, QWidget
)
from PySide6.QtCore import Qt, QTimer
import engine

class ProgressWindow(QDialog):
    def __init__(self, job_id, parent=None):
        super().__init__(parent)
        self.job_id = job_id
        
        # We will keep a static snapshot of the completed sync details once it finishes
        self.final_snapshot = None
        self.sync_start_time = time.time()
        
        # Speed tracking variables
        self.last_bytes_transferred = 0
        self.last_poll_time = time.time()
        self.smooth_speed = 0.0
        
        # Load job basic details
        import database
        self.job = database.get_job(job_id)
        job_name = self.job['name'] if self.job else f"Job #{job_id}"
        
        self.setWindowTitle(f"Sync Details - {job_name}")
        self.resize(750, 500)
        self.init_ui()
        
        # Real-time poll timer (ticking every 200ms)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll_progress)
        self.timer.start(200)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header Info Card
        header_card = QFrame()
        header_card.setObjectName("cardFrame")
        header_layout = QVBoxLayout(header_card)
        header_layout.setContentsMargins(12, 12, 12, 12)
        header_layout.setSpacing(6)

        # Title and Status Badge
        title_row = QHBoxLayout()
        self.job_name_label = QLabel(self.job['name'] if self.job else "Sync Job")
        self.job_name_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #FF6B00;")
        title_row.addWidget(self.job_name_label)
        title_row.addStretch()
        
        self.status_badge = QLabel("RUNNING")
        self.status_badge.setStyleSheet("background-color: #00E5FF; color: #000000; font-weight: bold; padding: 2px 8px; border-radius: 4px;")
        title_row.addWidget(self.status_badge)
        header_layout.addLayout(title_row)

        # Path Label Details
        self.paths_label = QLabel(f"Source: {self.job['source']}\nDest: {self.job['destination']}")
        self.paths_label.setObjectName("subtitleLabel")
        self.paths_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        header_layout.addWidget(self.paths_label)

        layout.addWidget(header_card)

        # Progress Section
        progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        
        self.percentage_label = QLabel("0%")
        self.percentage_label.setStyleSheet("font-weight: bold;")
        progress_layout.addWidget(self.percentage_label)
        layout.addLayout(progress_layout)

        # Statistics Info Panel
        stats_frame = QFrame()
        stats_frame.setObjectName("innerCard")
        stats_layout = QHBoxLayout(stats_frame)
        stats_layout.setContentsMargins(10, 10, 10, 10)
        
        self.stat_files = QLabel("Processed: 0/0")
        self.stat_size = QLabel("Transferred: 0 MB")
        self.stat_speed = QLabel("Speed: 0.00 MB/s")
        self.stat_time = QLabel("Time Elapsed: 0s")
        
        for widget in (self.stat_files, self.stat_size, self.stat_speed, self.stat_time):
            widget.setObjectName("label-sm")
            stats_layout.addWidget(widget)
            
        layout.addWidget(stats_frame)

        # Search and Filter Row
        filter_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter files by name...")
        self.search_input.textChanged.connect(self.on_filter_changed)
        filter_row.addWidget(self.search_input, stretch=2)

        self.status_filter = QComboBox()
        self.status_filter.addItems(["All Files", "Pending", "Copying", "Success", "Failed", "Skipped"])
        self.status_filter.currentTextChanged.connect(self.on_filter_changed)
        filter_row.addWidget(self.status_filter, stretch=1)
        layout.addLayout(filter_row)

        # File List Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["File Path", "Size", "Status", "Speed", "Details"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch) # Path stretch
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        # Footer Row (Cancel/Close buttons)
        footer_layout = QHBoxLayout()
        footer_layout.addStretch()
        
        self.cancel_btn = QPushButton("Cancel Sync")
        self.cancel_btn.setObjectName("dangerBtn")
        self.cancel_btn.clicked.connect(self.cancel_sync)
        footer_layout.addWidget(self.cancel_btn)

        self.close_btn = QPushButton("Close View")
        self.close_btn.clicked.connect(self.accept)
        footer_layout.addWidget(self.close_btn)

        layout.addLayout(footer_layout)

    def on_filter_changed(self, text=None):
        self.last_table_refresh = time.time()
        self.refresh_table()

    def cancel_sync(self):
        reply = QMessageBox.question(
            self, "Cancel Synchronization",
            "Are you sure you want to stop this sync job in progress?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            engine.request_cancel_sync(self.job_id)
            self.cancel_btn.setEnabled(False)
            self.cancel_btn.setText("Cancelling...")

    def poll_progress(self):
        # Read from engine memory
        running_info = None
        with engine.active_syncs_lock:
            running_info = engine.active_syncs.get(self.job_id)

        if running_info:
            # Sync is active! Record latest snapshot
            self.final_snapshot = {
                'total_files': running_info['total_files'],
                'processed_files': running_info['processed_files'],
                'bytes_transferred': running_info['bytes_transferred'],
                'bytes_saved': running_info['bytes_saved'],
                'file_transfers': list(running_info['file_transfers'].values()),
                'cancel_requested': running_info['cancel_requested'],
                'elapsed': time.time() - running_info.get('start_time', self.sync_start_time)
            }
            
            # Speed Delta Calculation
            curr_time = time.time()
            dt = curr_time - self.last_poll_time
            self.last_poll_time = curr_time
            
            curr_bytes = running_info['bytes_transferred']
            db = curr_bytes - self.last_bytes_transferred
            self.last_bytes_transferred = curr_bytes
            
            if dt > 0.01:
                raw_speed = db / dt
                # Smooth speed using EMA
                self.smooth_speed = 0.7 * self.smooth_speed + 0.3 * raw_speed
                
            self.update_gui_from_snapshot(self.final_snapshot, is_running=True)
        else:
            # Sync is not in active list anymore!
            self.status_badge.setText("FINISHED")
            self.status_badge.setStyleSheet("background-color: #10B981; color: #ffffff; font-weight: bold; padding: 2px 8px; border-radius: 4px;")
            self.cancel_btn.setVisible(False)
            
            # If we don't even have a snapshot (e.g. opened after job finished), load empty state or mock
            if not self.final_snapshot:
                self.table.setRowCount(0)
                self.progress_bar.setValue(100)
                self.percentage_label.setText("100%")
                self.stat_files.setText("No active transfer data.")
                self.timer.stop()
                return

            self.update_gui_from_snapshot(self.final_snapshot, is_running=False)
            # Once sync has ended and we showed the final state, we can stop the poll timer.
            self.timer.stop()

    def update_gui_from_snapshot(self, snapshot, is_running):
        # Progress Bar
        total = snapshot['total_files']
        processed = snapshot['processed_files']
        if total > 0:
            pct = int((processed / total) * 100)
        else:
            pct = 100 if not is_running else 0
            
        self.progress_bar.setValue(pct)
        self.percentage_label.setText(f"{pct}%")

        # Stats Labels
        self.stat_files.setText(f"Processed: {processed}/{total}")
        
        tx_mb = snapshot['bytes_transferred'] / (1024**2)
        self.stat_size.setText(f"Transferred: {tx_mb:.2f} MB")
        
        elapsed = snapshot['elapsed']
        self.stat_time.setText(f"Time Elapsed: {int(elapsed)}s")

        # Calculate Average Speed & Current Speed
        avg_speed_mb = (tx_mb / elapsed) if elapsed > 0 else 0
        current_speed_mb = self.smooth_speed / (1024**2) if is_running else 0.0
        self.stat_speed.setText(f"Speed: {current_speed_mb:.2f} MB/s (Avg: {avg_speed_mb:.2f} MB/s)")

        if not is_running:
            if snapshot['cancel_requested']:
                self.status_badge.setText("CANCELLED")
                self.status_badge.setStyleSheet("background-color: #EF4444; color: #ffffff; font-weight: bold; padding: 2px 8px; border-radius: 4px;")
            else:
                self.status_badge.setText("COMPLETED")
                self.status_badge.setStyleSheet("background-color: #10B981; color: #ffffff; font-weight: bold; padding: 2px 8px; border-radius: 4px;")

        # Only refresh the table at most once every 1.5 seconds, or immediately if finished
        curr_time = time.time()
        if not hasattr(self, 'last_table_refresh'):
            self.last_table_refresh = 0
            
        if not is_running or (curr_time - self.last_table_refresh >= 1.5):
            self.last_table_refresh = curr_time
            self.refresh_table()

    def refresh_table(self):
        if not self.final_snapshot:
            return
            
        transfers = self.final_snapshot['file_transfers']
        search_text = self.search_input.text().strip().lower()
        selected_status = self.status_filter.currentText()

        # Filter items
        filtered = []
        for t in transfers:
            if search_text and search_text not in t['relative_path'].lower():
                continue
            if selected_status != "All Files" and t['status'] != selected_status:
                continue
            filtered.append(t)

        self.table.setRowCount(0)
        self.table.setRowCount(len(filtered))

        for row_idx, t in enumerate(filtered):
            # File Path
            path_item = QTableWidgetItem(t['relative_path'])
            path_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.table.setItem(row_idx, 0, path_item)

            # Size
            size_mb = t['size'] / (1024**2)
            size_item = QTableWidgetItem(f"{size_mb:.2f} MB")
            size_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.table.setItem(row_idx, 1, size_item)

            # Status
            status_item = QTableWidgetItem(t['status'].upper())
            status_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            if t['status'] == 'Success':
                status_item.setForeground(Qt.green)
            elif t['status'] == 'Failed':
                status_item.setForeground(Qt.red)
            elif t['status'] == 'Copying':
                status_item.setForeground(Qt.cyan)
            elif t['status'] == 'Skipped':
                status_item.setForeground(Qt.yellow)
            else:
                status_item.setForeground(Qt.gray)
            self.table.setItem(row_idx, 2, status_item)

            # Speed
            speed_bytes = t.get('speed', 0.0)
            if speed_bytes > 0:
                speed_str = f"{speed_bytes / (1024**2):.2f} MB/s"
            else:
                speed_str = "--"
            speed_item = QTableWidgetItem(speed_str)
            speed_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            if speed_bytes > 0:
                speed_item.setForeground(Qt.cyan)
            self.table.setItem(row_idx, 3, speed_item)

            # Details (Duration / Error)
            duration = t.get('duration', 0.0)
            err = t.get('error')
            if err:
                detail_str = f"Error: {err}"
            elif duration > 0:
                detail_str = f"Done in {duration:.2f}s"
            else:
                detail_str = "Queued"
            detail_item = QTableWidgetItem(detail_str)
            detail_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            if err:
                detail_item.setForeground(Qt.red)
            else:
                detail_item.setForeground(Qt.gray)
            self.table.setItem(row_idx, 4, detail_item)
