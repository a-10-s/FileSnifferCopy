def get_stylesheet():
    return """
        /* Main Window & Dialogs */
        QMainWindow, QDialog {
            background-color: #09090B;
        }


        /* Widgets */
        QWidget {
            color: #E4E4E7;
            font-family: "Segoe UI", "Inter", sans-serif;
            font-size: 13px;
        }

        /* Headers and Labels */
        QLabel#titleLabel {
            font-size: 22px;
            font-weight: bold;
            color: #FF6B00;
            margin-bottom: 5px;
        }
        QLabel#subtitleLabel {
            font-size: 12px;
            color: #A1A1AA;
        }
        QLabel#sectionHeader {
            font-size: 15px;
            font-weight: bold;
            color: #E4E4E7;
            border-bottom: 1px solid #27272A;
            padding-bottom: 5px;
            margin-top: 10px;
        }

        /* Group Boxes / Cards */
        QFrame#cardFrame {
            background-color: #18181B;
            border: 1px solid #27272A;
            border-radius: 8px;
            padding: 12px;
        }
        QFrame#innerCard {
            background-color: #0F0F11;
            border: 1px solid #27272A;
            border-radius: 6px;
            padding: 8px;
        }

        /* Buttons */
        QPushButton {
            background-color: #27272A;
            border: 1px solid #3F3F46;
            border-radius: 4px;
            color: #E4E4E7;
            padding: 6px 12px;
            font-weight: 500;
        }
        QPushButton:hover {
            background-color: #3F3F46;
            border-color: #52525B;
        }
        QPushButton:pressed {
            background-color: #18181B;
        }
        QPushButton:disabled {
            background-color: #09090B;
            border-color: #18181B;
            color: #52525B;
        }

        /* Primary Button */
        QPushButton#primaryBtn {
            background-color: #FF6B00;
            border: 1px solid #FF8533;
            color: #FFFFFF;
        }
        QPushButton#primaryBtn:hover {
            background-color: #E05E00;
        }
        QPushButton#primaryBtn:pressed {
            background-color: #C25200;
        }

        /* Danger Button */
        QPushButton#dangerBtn {
            background-color: #EF4444;
            border: 1px solid #F87171;
            color: #FFFFFF;
        }
        QPushButton#dangerBtn:hover {
            background-color: #DC2626;
        }
        QPushButton#dangerBtn:pressed {
            background-color: #B91C1C;
        }

        /* Inputs, SpinBoxes, ComboBoxes */
        QLineEdit, QSpinBox, QComboBox, QTimeEdit {
            background-color: #222226;
            border: 1px solid #3F3F46;
            border-radius: 4px;
            padding: 6px;
            color: #E4E4E7;
        }
        QLineEdit:hover, QSpinBox:hover, QComboBox:hover, QTimeEdit:hover {
            border-color: #FF6B00;
            background-color: #2A2A2F;
        }
        QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QTimeEdit:focus {
            border: 1px solid #FF6B00;
            background-color: #1E1E22;
        }
        QComboBox::drop-down {
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 25px;
            border-left: 1px solid #3F3F46;
            background-color: #2D2D30;
            border-top-right-radius: 4px;
            border-bottom-right-radius: 4px;
        }
        QComboBox::drop-down:hover {
            background-color: #FF6B00;
        }
        QComboBox::down-arrow {
            image: url("data:image/svg+xml;utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%23FF6B00' width='18px' height='18px'%3E%3Cpath d='M7 10l5 5 5-5z'/%3E%3C/svg%3E");
            width: 14px;
            height: 14px;
        }
        QComboBox QAbstractItemView {
            background-color: #18181B;
            border: 1px solid #FF6B00;
            selection-background-color: #FF6B00;
            selection-color: #FFFFFF;
            color: #E4E4E7;
        }

        /* QMenu Styling (Tray Context Menu) */
        QMenu {
            background-color: #18181B;
            border: 1px solid #3F3F46;
            border-radius: 4px;
            color: #E4E4E7;
            padding: 4px 0px;
        }
        QMenu::item {
            padding: 6px 24px;
            background-color: transparent;
        }
        QMenu::item:selected {
            background-color: #FF6B00;
            color: #FFFFFF;
        }
        QMenu::separator {
            height: 1px;
            background-color: #27272A;
            margin: 4px 0px;
        }

        /* Scroll Area and Viewports */
        QScrollArea {
            background-color: #09090B;
            border: none;
        }
        QScrollArea::viewport {
            background-color: #09090B;
        }
        QWidget#scrollContent {
            background-color: #09090B;
        }

        /* Tables */
        QTableWidget {
            background-color: #18181B;
            border: 1px solid #27272A;
            gridline-color: #27272A;
            border-radius: 6px;
            alternate-background-color: #131316;
        }
        QTableWidget::viewport {
            background-color: #18181B;
        }
        QHeaderView {
            background-color: #0F0F11;
            border: none;
        }
        QHeaderView::section {
            background-color: #0F0F11;
            color: #A1A1AA;
            padding: 6px;
            border: none;
            border-bottom: 1px solid #27272A;
            font-weight: bold;
        }
        QTableWidget QTableCornerButton::section {
            background-color: #0F0F11;
            border: none;
        }

        /* Checkboxes */
        QCheckBox {
            spacing: 8px;
        }
        QCheckBox::indicator {
            width: 18px;
            height: 18px;
            border: 1px solid #27272A;
            border-radius: 3px;
            background-color: #18181B;
        }
        QCheckBox::indicator:hover {
            border-color: #FF6B00;
        }
        QCheckBox::indicator:checked {
            background-color: #FF6B00;
            border-color: #FF8533;
            image: url("data:image/svg+xml;utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='white' width='18px' height='18px'%3E%3Cpath d='M0 0h24v24H0z' fill='none'/%3E%3Cpath d='M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z'/%3E%3C/svg%3E");
        }

        /* Progress Bar */
        QProgressBar {
            border: 1px solid #27272A;
            border-radius: 4px;
            text-align: center;
            background-color: #09090B;
            height: 16px;
            font-size: 10px;
            font-weight: bold;
        }
        QProgressBar::chunk {
            background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FF6B00, stop:1 #00E5FF);
            border-radius: 3px;
        }

        /* Scrollbars */
        QScrollBar:vertical {
            border: none;
            background: #09090B;
            width: 8px;
            margin: 0px;
        }
        QScrollBar::handle:vertical {
            background: #27272A;
            min-height: 20px;
            border-radius: 4px;
        }
        QScrollBar::handle:vertical:hover {
            background: #3F3F46;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }

        QScrollBar:horizontal {
            border: none;
            background: #09090B;
            height: 8px;
            margin: 0px;
        }
        QScrollBar::handle:horizontal {
            background: #27272A;
            min-width: 20px;
            border-radius: 4px;
        }
        QScrollBar::handle:horizontal:hover {
            background: #3F3F46;
        }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            width: 0px;
        }

        /* Tooltip */
        QToolTip {
            background-color: #18181B;
            color: #E4E4E7;
            border: 1px solid #FF6B00;
            border-radius: 4px;
            padding: 4px 8px;
            font-size: 12px;
        }

        /* Explore Folder Button */
        QPushButton#exploreBtn {
            background-color: #27272A;
            border: 1px solid #3F3F46;
            border-radius: 4px;
            color: #A1A1AA;
            padding: 0px;
            font-size: 14px;
        }
        QPushButton#exploreBtn:hover {
            background-color: #FF6B00;
            border-color: #FF8533;
            color: #FFFFFF;
        }
        QPushButton#exploreBtn:pressed {
            background-color: #C25200;
        }
    """
