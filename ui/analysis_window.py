from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTreeWidget, QTreeWidgetItem, QHeaderView, QFrame,
    QAbstractItemView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from datetime import datetime

class AnalysisWindow(QDialog):
    def __init__(self, job, pending_files, parent=None):
        super().__init__(parent)
        self.job = job
        self.pending_files = pending_files
        self.selected_files = []
        self._updating_checks = False
        
        self.setWindowTitle(f"Overwrite Analysis - {job['name']}")
        self.resize(900, 600)  # slightly wider to accommodate folder tree structure nicely
        self.init_ui()
        self.populate_tree()

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

        # Tree Widget
        self.tree = QTreeWidget()
        self.tree.setColumnCount(5)
        self.tree.setHeaderLabels([
            "File Path", "Source Size", "Target Size", "Conflict Detail", "Last Modified (Src)"
        ])
        self.tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tree.setAlternatingRowColors(True)
        
        # Style tree widget to match dark theme beautifully
        self.tree.setStyleSheet("""
            QTreeWidget {
                background-color: #18181B;
                border: 1px solid #27272A;
                alternate-background-color: #131316;
                border-radius: 6px;
            }
            QHeaderView::section {
                background-color: #0F0F11;
                color: #A1A1AA;
                padding: 6px;
                border: none;
                border-bottom: 1px solid #27272A;
                font-weight: bold;
            }
            QTreeWidget::item {
                padding: 4px;
            }
            QTreeWidget::item:selected {
                background-color: #FF6B00;
                color: #FFFFFF;
            }
            QTreeWidget::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #3F3F46;
                border-radius: 3px;
                background-color: #222226;
            }
            QTreeWidget::indicator:hover {
                border-color: #FF6B00;
            }
            QTreeWidget::indicator:checked {
                background-color: #FF6B00;
                border-color: #FF8533;
                image: url("data:image/svg+xml;utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='white' width='16px' height='16px'%3E%3Cpath d='M0 0h24v24H0z' fill='none'/%3E%3Cpath d='M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z'/%3E%3C/svg%3E");
            }
            QTreeWidget::indicator:indeterminate {
                background-color: #FF6B00;
                border-color: #FF8533;
                image: url("data:image/svg+xml;utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='white' width='16px' height='16px'%3E%3Crect x='4' y='11' width='16' height='2'/%3E%3C/svg%3E");
            }
        """)

        self.tree.header().setSectionResizeMode(QHeaderView.Interactive)
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        
        # Connect check state change signal
        self.tree.itemChanged.connect(self.on_item_changed)
        
        layout.addWidget(self.tree)

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

    def populate_tree(self):
        self.tree.clear()
        
        # Sort files so they are processed in order
        sorted_files = sorted(self.pending_files, key=lambda x: x['relative_path'])
        
        # Keep track of folder nodes
        folder_cache = {}
        
        for f in sorted_files:
            # Normalize path separators
            path = f['relative_path'].replace('\\', '/')
            parts = path.split('/')
            
            current_parent = self.tree.invisibleRootItem()
            current_path = ""
            
            for i, part in enumerate(parts):
                if i < len(parts) - 1:
                    # Directory part
                    current_path = f"{current_path}/{part}" if current_path else part
                    if current_path in folder_cache:
                        current_parent = folder_cache[current_path]
                    else:
                        item = QTreeWidgetItem(current_parent)
                        item.setText(0, f"📁 {part}")
                        item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsAutoTristate)
                        item.setCheckState(0, Qt.Checked)
                        
                        folder_cache[current_path] = item
                        current_parent = item
                else:
                    # File part
                    item = QTreeWidgetItem(current_parent)
                    item.setText(0, f"📄 {part}")
                    item.setData(0, Qt.UserRole, f)
                    item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                    item.setCheckState(0, Qt.Checked)
                    
                    # Source Size
                    src_mb = f['size'] / (1024**2)
                    item.setText(1, f"{src_mb:.2f} MB")
                    
                    # Target Size
                    if f.get('target_exists'):
                        tgt_mb = f['target_size'] / (1024**2)
                        item.setText(2, f"{tgt_mb:.2f} MB")
                    else:
                        item.setText(2, "--")
                        
                    # Conflict Detail
                    conflict = f.get('conflict_type', 'new')
                    if conflict == 'new':
                        txt = "NEW FILE"
                        col = QColor("#00FF00")
                    elif conflict == 'overwrite_size':
                        txt = "OVERWRITE (Size changed)"
                        col = QColor("#00E5FF")
                    elif conflict == 'overwrite_newer':
                        txt = "OVERWRITE (Source is newer)"
                        col = QColor("#00E5FF")
                    else:
                        txt = "OVERWRITE"
                        col = QColor("#00E5FF")
                    
                    item.setText(3, txt)
                    item.setForeground(3, col)
                    
                    # Last Modified Date (Source)
                    dt_str = datetime.fromtimestamp(f['mtime']).strftime("%Y-%m-%d %H:%M:%S")
                    item.setText(4, dt_str)

        # Expand all folders by default
        self.tree.expandAll()
        
        # Resize other columns to fit contents
        for col in range(1, 5):
            self.tree.resizeColumnToContents(col)

    def _propagate_down(self, item, state):
        for i in range(item.childCount()):
            child = item.child(i)
            child.setCheckState(0, state)
            self._propagate_down(child, state)

    def on_item_changed(self, item, column):
        if column != 0 or self._updating_checks:
            return
            
        self._updating_checks = True
        try:
            state = item.checkState(0)
            if state != Qt.PartiallyChecked:
                self._propagate_down(item, state)
        finally:
            self._updating_checks = False

    def select_all(self):
        self._updating_checks = True
        try:
            root = self.tree.invisibleRootItem()
            for i in range(root.childCount()):
                item = root.child(i)
                item.setCheckState(0, Qt.Checked)
                self._propagate_down(item, Qt.Checked)
        finally:
            self._updating_checks = False

    def select_none(self):
        self._updating_checks = True
        try:
            root = self.tree.invisibleRootItem()
            for i in range(root.childCount()):
                item = root.child(i)
                item.setCheckState(0, Qt.Unchecked)
                self._propagate_down(item, Qt.Unchecked)
        finally:
            self._updating_checks = False

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space:
            selected_items = self.tree.selectedItems()
            if selected_items:
                # Find the target state based on the first selected item's checkState
                first_state = selected_items[0].checkState(0)
                target_state = Qt.Unchecked if first_state == Qt.Checked else Qt.Checked
                
                self._updating_checks = True
                try:
                    for item in selected_items:
                        item.setCheckState(0, target_state)
                        self._propagate_down(item, target_state)
                finally:
                    self._updating_checks = False
                
                event.accept()
                return
        super().keyPressEvent(event)

    def on_proceed(self):
        self.selected_files = []
        
        def collect_checked(item):
            file_data = item.data(0, Qt.UserRole)
            if file_data is not None:
                if item.checkState(0) == Qt.Checked:
                    clean_f = {
                        'relative_path': file_data['relative_path'],
                        'abs_src': file_data['abs_src'],
                        'abs_dst': file_data['abs_dst'],
                        'size': file_data['size'],
                        'mtime': file_data['mtime']
                    }
                    self.selected_files.append(clean_f)
            else:
                for i in range(item.childCount()):
                    collect_checked(item.child(i))

        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            collect_checked(root.child(i))

        if not self.selected_files:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "No Files Selected", "You must select at least one file to execute updates.")
            return

        self.accept()
