import csv
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QFileDialog, QMessageBox, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer
import database

class LogWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Transfers & Savings Log")
        self.resize(800, 600)
        self.init_ui()
        
        # Poll timer to refresh logs dynamically
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_logs)
        self.refresh_timer.start(2000)
        
        self.refresh_logs()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Filters Card — constrained to content height, never stretches vertically
        filter_card = QFrame()
        filter_card.setObjectName("cardFrame")
        filter_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        filter_layout = QHBoxLayout(filter_card)
        filter_layout.setContentsMargins(12, 12, 12, 12)
        filter_layout.setSpacing(12)

        # Job Filter
        job_vbox = QVBoxLayout()
        job_lbl = QLabel("Filter by Job:")
        job_lbl.setObjectName("label-sm")
        self.job_combo = QComboBox()
        self.job_combo.addItem("All Jobs")
        self.populate_job_filter()
        self.job_combo.currentTextChanged.connect(self.on_filter_changed)
        job_vbox.addWidget(job_lbl)
        job_vbox.addWidget(self.job_combo)
        filter_layout.addLayout(job_vbox)

        # Status Filter
        status_vbox = QVBoxLayout()
        status_lbl = QLabel("Filter by Status:")
        status_lbl.setObjectName("label-sm")
        self.status_combo = QComboBox()
        self.status_combo.addItems(["All Statuses", "Success", "Failed", "Warning"])
        self.status_combo.currentTextChanged.connect(self.on_filter_changed)
        status_vbox.addWidget(status_lbl)
        status_vbox.addWidget(self.status_combo)
        filter_layout.addLayout(status_vbox)

        # Search box
        search_vbox = QVBoxLayout()
        search_lbl = QLabel("Search Files:")
        search_lbl.setObjectName("label-sm")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Type file name...")
        self.search_input.textChanged.connect(self.on_filter_changed)
        search_vbox.addWidget(search_lbl)
        search_vbox.addWidget(self.search_input)
        filter_layout.addLayout(search_vbox, stretch=1)

        # Action Buttons
        btn_vbox = QVBoxLayout()
        btn_vbox.addStretch()
        
        self.export_btn = QPushButton("Export CSV")
        self.export_btn.clicked.connect(self.export_csv)
        btn_vbox.addWidget(self.export_btn)

        self.clear_btn = QPushButton("Clear Logs")
        self.clear_btn.setObjectName("dangerBtn")
        self.clear_btn.clicked.connect(self.clear_logs)
        btn_vbox.addWidget(self.clear_btn)

        filter_layout.addLayout(btn_vbox)

        layout.addWidget(filter_card)

        # History Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Timestamp", "Job", "File", "Status", "Savings / Detail"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch) # file name stretch
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

    def populate_job_filter(self):
        try:
            jobs = database.get_all_jobs()
            for j in jobs:
                self.job_combo.addItem(j['name'])
        except Exception:
            pass

    def on_filter_changed(self, text=None):
        self.refresh_logs()

    def refresh_logs(self):
        # Prevent refreshing if search or combos are active to avoid visual glitching,
        # but standard is to clear and reload. Since list size is <= 500, it's instant.
        try:
            history = database.get_history(limit=500)
        except Exception:
            return

        selected_job = self.job_combo.currentText()
        selected_status = self.status_combo.currentText()
        search_text = self.search_input.text().strip().lower()

        # Filter in-memory
        filtered_entries = []
        for entry in history:
            # Job Filter
            if selected_job != "All Jobs" and entry.get('job_name') != selected_job:
                continue

            # Status Filter
            entry_status = entry['status'].lower()
            if selected_status == "Success" and entry_status != "success":
                continue
            if selected_status == "Failed" and entry_status != "failed":
                continue
            if selected_status == "Warning" and entry_status != "warning":
                continue

            # Search Text Filter
            if search_text and search_text not in entry['file_name'].lower():
                continue

            filtered_entries.append(entry)

        # Display in Table
        self.table.setRowCount(0)
        self.table.setRowCount(len(filtered_entries))

        for row_idx, entry in enumerate(filtered_entries):
            # Timestamp
            ts_item = QTableWidgetItem(entry['timestamp'])
            ts_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.table.setItem(row_idx, 0, ts_item)

            # Job
            job_item = QTableWidgetItem(entry.get('job_name') or "System / Scheduler")
            job_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.table.setItem(row_idx, 1, job_item)

            # File
            file_item = QTableWidgetItem(entry['file_name'])
            file_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.table.setItem(row_idx, 2, file_item)

            # Status
            status_str = entry['status'].upper()
            status_item = QTableWidgetItem(status_str)
            status_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            if entry['status'] == 'success':
                status_item.setForeground(Qt.green)
            elif entry['status'] == 'warning':
                status_item.setForeground(Qt.yellow)
            else:
                status_item.setForeground(Qt.red)
            self.table.setItem(row_idx, 3, status_item)

            # Savings / Error Message
            saved = entry['bytes_saved']
            if entry['status'] == 'success':
                if saved > 0:
                    saved_str = f"Saved {saved / (1024**2):.2f} MB"
                    detail_item = QTableWidgetItem(saved_str)
                    detail_item.setForeground(Qt.cyan)
                else:
                    detail_item = QTableWidgetItem("Copied (Direct)")
                    detail_item.setForeground(Qt.gray)
            else:
                detail_item = QTableWidgetItem(entry['error_message'] or "Execution error")
                if entry['status'] == 'warning':
                    detail_item.setForeground(Qt.yellow)
                else:
                    detail_item.setForeground(Qt.red)

            detail_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.table.setItem(row_idx, 4, detail_item)

        # Resize header columns to fit contents
        self.table.resizeColumnToContents(0)
        self.table.resizeColumnToContents(1)
        self.table.resizeColumnToContents(3)
        self.table.resizeColumnToContents(4)

    def export_csv(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Log to CSV", "", "CSV Files (*.csv);;All Files (*)"
        )
        if not file_path:
            return

        try:
            # We fetch filtered logs
            history = database.get_history(limit=1000)
            selected_job = self.job_combo.currentText()
            selected_status = self.status_combo.currentText()
            search_text = self.search_input.text().strip().lower()

            with open(file_path, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Timestamp", "Job Name", "File Name", "Status", "Bytes Transferred", "Bytes Saved", "Error / Detail"])
                
                for entry in history:
                    if selected_job != "All Jobs" and entry.get('job_name') != selected_job:
                        continue
                    entry_status = entry['status'].lower()
                    if selected_status == "Success" and entry_status != "success":
                        continue
                    if selected_status == "Failed" and entry_status != "failed":
                        continue
                    if selected_status == "Warning" and entry_status != "warning":
                        continue
                    if search_text and search_text not in entry['file_name'].lower():
                        continue
                        
                    writer.writerow([
                        entry['timestamp'],
                        entry.get('job_name') or "System",
                        entry['file_name'],
                        entry['status'].upper(),
                        entry['bytes_transferred'],
                        entry['bytes_saved'],
                        entry['error_message'] or ""
                    ])
            QMessageBox.information(self, "Export Complete", f"History successfully exported to:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Failed to export log to CSV:\n{str(e)}")

    def clear_logs(self):
        reply = QMessageBox.question(
            self, "Confirm Clear",
            "Are you sure you want to clear all sync history logs?\nThis operation cannot be undone.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                database.clear_history()
                self.refresh_logs()
                # If parent exists and is dashboard, refresh statistics
                if self.parent() and hasattr(self.parent(), 'refresh_stats'):
                    self.parent().refresh_stats()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to clear logs:\n{str(e)}")
