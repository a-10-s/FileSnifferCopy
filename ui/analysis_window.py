from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox, QFrame,
    QWidget
)
from PySide6.QtCore import Qt
from datetime import datetime

class AnalysisWindow(QDialog):
    def __init__(self, job, pending_files, parent=None):
        super().__init__(parent)
        self.job = job
        self.pending_files = pending_files
        self.selected_files = []
        
        self.setWindowTitle(f"Overwrite Analysis - {job['name']}")
        self.resize(800, 500)
        self.init_ui()
        self.populate_table()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header Info Card
        header = QFrame()
        header.setObjectName("cardFrame")
        h_layout = QVBoxLayout(header)
        h_layout.setContentsMargins(12, 12, 12, 12)
        h_layout.setSpacing(6)

        title = QLabel("Target Update - Comparison Report")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #FF6B00;")
        h_layout.addWidget(title)

        desc = QLabel(
            f"Source: {self.job['source']}\n"
            f"Destination: {self.job['destination']}\n"
            f"Scan completed. The following files are updated in source and need updating on target."
        )
        desc.setObjectName("subtitleLabel")
        h_layout.addWidget(desc)
        layout.addWidget(header)

        # Table Actions (Select all/none)
        action_row = QHBoxLayout()
        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(self.select_all)
        action_row.addWidget(self.select_all_btn)

        self.select_none_btn = QPushButton("Deselect All")
        self.select_none_btn.clicked.connect(self.select_none)
        action_row.addWidget(self.select_none_btn)
        
        action_row.addStretch()
        layout.addLayout(action_row)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Copy", "File Path", "Source Size", "Target Size", "Conflict Detail", "Last Modified (Src)"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch) # Path stretch
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        # Footer Actions
        footer = QHBoxLayout()
        footer.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        footer.addWidget(cancel_btn)

        self.proceed_btn = QPushButton("Execute Selected Updates")
        self.proceed_btn.setObjectName("primaryBtn")
        self.proceed_btn.clicked.connect(self.on_proceed)
        footer.addWidget(self.proceed_btn)
        
        layout.addLayout(footer)

    def populate_table(self):
        self.table.setRowCount(0)
        self.table.setRowCount(len(self.pending_files))

        # Sort files so overwrites are grouped first, then new files
        # (New files conflict_type is 'new', overwrites are 'overwrite_newer' / 'overwrite_size' / 'overwrite_forced')
        self.pending_files = sorted(
            self.pending_files, 
            key=lambda x: (x.get('conflict_type') == 'new', x['relative_path'])
        )

        for row_idx, f in enumerate(self.pending_files):
            # Checkbox
            checkbox_widget = QWidget()
            chk_lay = QHBoxLayout(checkbox_widget)
            chk_lay.setContentsMargins(0, 0, 0, 0)
            chk_lay.setAlignment(Qt.AlignCenter)
            chk = QCheckBox()
            chk.setChecked(True) # Checked by default
            chk_lay.addWidget(chk)
            self.table.setCellWidget(row_idx, 0, checkbox_widget)
            
            # Save checkbox reference on the dict to read later
            f['chk_reference'] = chk

            # File Path
            path_item = QTableWidgetItem(f['relative_path'])
            path_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.table.setItem(row_idx, 1, path_item)

            # Source Size
            src_mb = f['size'] / (1024**2)
            src_size_item = QTableWidgetItem(f"{src_mb:.2f} MB")
            src_size_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.table.setItem(row_idx, 2, src_size_item)

            # Target Size
            if f.get('target_exists'):
                tgt_mb = f['target_size'] / (1024**2)
                tgt_size_item = QTableWidgetItem(f"{tgt_mb:.2f} MB")
            else:
                tgt_size_item = QTableWidgetItem("--")
            tgt_size_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.table.setItem(row_idx, 3, tgt_size_item)

            # Conflict Details
            conflict = f.get('conflict_type', 'new')
            if conflict == 'new':
                txt = "NEW FILE"
                col = Qt.green
            elif conflict == 'overwrite_size':
                txt = "OVERWRITE (Size changed)"
                col = Qt.cyan
            elif conflict == 'overwrite_newer':
                txt = "OVERWRITE (Source is newer)"
                col = Qt.cyan
            else:
                txt = "OVERWRITE"
                col = Qt.cyan

            conflict_item = QTableWidgetItem(txt)
            conflict_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            conflict_item.setForeground(col)
            self.table.setItem(row_idx, 4, conflict_item)

            # Last Modified Date (Source)
            dt_str = datetime.fromtimestamp(f['mtime']).strftime("%Y-%m-%d %H:%M:%S")
            time_item = QTableWidgetItem(dt_str)
            time_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.table.setItem(row_idx, 5, time_item)

        # Resize columns to content
        self.table.resizeColumnToContents(0)
        self.table.resizeColumnToContents(2)
        self.table.resizeColumnToContents(3)
        self.table.resizeColumnToContents(4)
        self.table.resizeColumnToContents(5)

    def select_all(self):
        for f in self.pending_files:
            if 'chk_reference' in f:
                f['chk_reference'].setChecked(True)

    def select_none(self):
        for f in self.pending_files:
            if 'chk_reference' in f:
                f['chk_reference'].setChecked(False)

    def on_proceed(self):
        # Gather all selected files
        self.selected_files = []
        for f in self.pending_files:
            if 'chk_reference' in f and f['chk_reference'].isChecked():
                # We strip the checkbox reference before passing to avoid PySide6 layout reference leak
                clean_f = {
                    'relative_path': f['relative_path'],
                    'abs_src': f['abs_src'],
                    'abs_dst': f['abs_dst'],
                    'size': f['size'],
                    'mtime': f['mtime']
                }
                self.selected_files.append(clean_f)

        if not self.selected_files:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "No Files Selected", "You must select at least one file to execute updates.")
            return

        self.accept()
