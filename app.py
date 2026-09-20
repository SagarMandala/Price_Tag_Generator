"""
Main Desktop GUI Application for Supermarket Shelf Price Tag Generator.
Built with PyQt6, converting Excel pricing into printable 8-tags-per-page A4 PDFs (90mm x 60mm).
Branded with 'BIGG Mart Price', pure white background, and per-row promotional offer dropdowns.
"""

import sys
import os
import subprocess

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QTableWidget, QTableWidgetItem,
    QProgressBar, QHeaderView, QLineEdit, QCheckBox, QComboBox,
    QMessageBox, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QPixmap, QImage, QDragEnterEvent, QDropEvent

from data_processor import parse_pricing_file, PROMOTIONAL_OFFERS
from tag_generator import generate_pdf, render_tag_preview_image, get_rupee_symbol, PAGE_LAYOUTS


# ==============================================================================
# BACKGROUND WORKER THREAD FOR PDF GENERATION
# ==============================================================================
class PdfGenerationWorker(QThread):
    progress_changed = pyqtSignal(int, int)
    finished = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, items, output_path, bg_color, store_title, show_cut_guides, design_style="option1", layout_mode="8_tags"):
        super().__init__()
        self.items = items
        self.output_path = output_path
        self.bg_color = bg_color
        self.store_title = store_title
        self.show_cut_guides = show_cut_guides
        self.design_style = design_style
        self.layout_mode = layout_mode

    def run(self):
        try:
            def on_progress(current, total):
                self.progress_changed.emit(current, total)

            result_path = generate_pdf(
                items=self.items,
                output_pdf_path=self.output_path,
                tag_bg_color=self.bg_color,
                store_title=self.store_title,
                validity_text="",
                show_cut_guides=self.show_cut_guides,
                design_style=self.design_style,
                layout_mode=self.layout_mode,
                progress_callback=on_progress
            )
            self.finished.emit(result_path)
        except Exception as e:
            self.failed.emit(str(e))


# ==============================================================================
# CUSTOM PREVIEW WIDGET (Clean Scaling without Clipping)
# ==============================================================================
class TagPreviewWidget(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._master_pixmap = None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(280, 200)

    def setTagPixmap(self, pixmap: QPixmap):
        self._master_pixmap = pixmap
        self.refresh()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.refresh()

    def refresh(self):
        if self._master_pixmap and not self._master_pixmap.isNull():
            avail_w = max(40, self.width() - 16)
            avail_h = max(40, self.height() - 16)
            scaled = self._master_pixmap.scaled(
                avail_w,
                avail_h,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            super().setPixmap(scaled)


# ==============================================================================
# MAIN WINDOW CLASS
# ==============================================================================
class PriceTagGeneratorApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("BIG Mart - Supermarket Shelf Price Tag Generator")
        self.setMinimumSize(1150, 800)
        self.resize(1220, 850)

        # State
        self.loaded_items = []
        self.current_excel_path = ""
        self.generated_pdf_path = ""
        self.tag_bg_color = "#FFFFFF"  # White background
        self.selected_preview_index = 0

        self.init_ui()
        self.apply_styles()

        # Enable Drag and Drop
        self.setAcceptDrops(True)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(14)

        # ----------------------------------------------------------------------
        # Header Banner
        # ----------------------------------------------------------------------
        header_frame = QFrame()
        header_frame.setObjectName("headerFrame")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(18, 14, 18, 14)

        title_vbox = QVBoxLayout()
        title_lbl = QLabel("BIG Mart - Shelf Price Tag Generator")
        title_lbl.setObjectName("appTitle")
        self.subtitle_lbl = QLabel("Convert Excel pricing sheets into printable multi-page A4 PDFs (8, 2, or 1 tag(s) per sheet)")
        self.subtitle_lbl.setObjectName("appSubtitle")
        title_vbox.addWidget(title_lbl)
        title_vbox.addWidget(self.subtitle_lbl)
        header_layout.addLayout(title_vbox)

        header_layout.addStretch()

        badge_box = QHBoxLayout()
        self.grid_badge = QLabel("📐 8 Tags / A4 Sheet (90x60mm)")
        self.grid_badge.setObjectName("infoBadge")
        rupee_badge = QLabel(f"💱 {get_rupee_symbol()} Unicode Native")
        rupee_badge.setObjectName("infoBadge")
        badge_box.addWidget(self.grid_badge)
        badge_box.addWidget(rupee_badge)
        header_layout.addLayout(badge_box)

        main_layout.addWidget(header_frame)

        # ----------------------------------------------------------------------
        # Main Two-Column Split
        # ----------------------------------------------------------------------
        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)

        # LEFT COLUMN (Controls, Table, Options)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        # 1. File Upload Drop Zone & Browse Card
        self.drop_card = QFrame()
        self.drop_card.setObjectName("cardFrame")
        drop_layout = QVBoxLayout(self.drop_card)
        drop_layout.setContentsMargins(16, 14, 16, 14)

        file_action_row = QHBoxLayout()
        self.browse_btn = QPushButton("📁 Browse Excel File (.xls, .xlsx)")
        self.browse_btn.setObjectName("browseBtn")
        self.browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.browse_btn.clicked.connect(self.browse_file)
        file_action_row.addWidget(self.browse_btn)

        self.file_status_lbl = QLabel("No Excel file selected yet (Drag & Drop .xls or .xlsx here)")
        self.file_status_lbl.setObjectName("fileStatus")
        self.file_status_lbl.setWordWrap(True)
        file_action_row.addWidget(self.file_status_lbl, 1)

        drop_layout.addLayout(file_action_row)
        left_layout.addWidget(self.drop_card)

        # 2. Data & Offer Table Card
        table_card = QFrame()
        table_card.setObjectName("cardFrame")
        table_card_layout = QVBoxLayout(table_card)
        table_card_layout.setContentsMargins(16, 12, 16, 12)
        table_card_layout.setSpacing(8)

        table_header_row = QHBoxLayout()
        table_title = QLabel("📊 Products & Promotions (Set Offers Per Row)")
        table_title.setObjectName("sectionTitle")
        table_header_row.addWidget(table_title)

        table_header_row.addStretch()
        self.rows_count_lbl = QLabel("0 items loaded")
        self.rows_count_lbl.setObjectName("metaLabel")
        table_header_row.addWidget(self.rows_count_lbl)
        table_card_layout.addLayout(table_header_row)

        # Quick Bulk Apply Bar
        bulk_bar = QHBoxLayout()
        bulk_lbl = QLabel("Bulk Set Offer for All:")
        bulk_lbl.setObjectName("fieldLabel")
        bulk_bar.addWidget(bulk_lbl)

        self.bulk_offer_combo = QComboBox()
        self.bulk_offer_combo.setObjectName("dropdown")
        self.bulk_offer_combo.addItems(PROMOTIONAL_OFFERS)
        bulk_bar.addWidget(self.bulk_offer_combo)

        self.apply_bulk_btn = QPushButton("Apply to All Rows")
        self.apply_bulk_btn.setObjectName("smallBtn")
        self.apply_bulk_btn.clicked.connect(self.apply_bulk_offer)
        bulk_bar.addWidget(self.apply_bulk_btn)

        self.clear_bulk_btn = QPushButton("Clear / Disable All")
        self.clear_bulk_btn.setObjectName("smallBtn")
        self.clear_bulk_btn.clicked.connect(self.clear_all_offers)
        bulk_bar.addWidget(self.clear_bulk_btn)

        bulk_bar.addStretch()
        table_card_layout.addLayout(bulk_bar)

        # Products Table
        self.preview_table = QTableWidget(0, 5)
        self.preview_table.setHorizontalHeaderLabels(["ITEM NAME", "MRP (₹)", "RATE-A (₹)", "SAVINGS (₹)", "PROMOTION / OFFER"])
        self.preview_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.preview_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.preview_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.preview_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.preview_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.preview_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.preview_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.preview_table.cellClicked.connect(self.on_table_row_clicked)
        self.preview_table.setFixedHeight(230)
        table_card_layout.addWidget(self.preview_table)

        left_layout.addWidget(table_card)

        # 3. Tag Settings Card
        settings_card = QFrame()
        settings_card.setObjectName("cardFrame")
        settings_layout = QVBoxLayout(settings_card)
        settings_layout.setContentsMargins(16, 12, 16, 12)
        settings_layout.setSpacing(10)

        settings_title = QLabel("⚙️ Tag Settings & Design")
        settings_title.setObjectName("sectionTitle")
        settings_layout.addWidget(settings_title)

        form_row1 = QHBoxLayout()

        lbl_layout = QLabel("Page Layout:")
        lbl_layout.setObjectName("fieldLabel")
        self.layout_combo = QComboBox()
        self.layout_combo.setObjectName("dropdown")
        self.layout_combo.addItem("8 Tags / A4 Sheet (90x60mm - Shelf Tags)", "8_tags")
        self.layout_combo.addItem("2 Tags / A4 Sheet (Half Page A5 - Promo Posters)", "2_tags")
        self.layout_combo.addItem("1 Tag / A4 Sheet (Full Page A4 Landscape - Display Sign)", "1_tag")
        self.layout_combo.currentIndexChanged.connect(self.on_layout_changed)
        form_row1.addWidget(lbl_layout)
        form_row1.addWidget(self.layout_combo, 3)

        lbl_design = QLabel("Tag Design:")
        lbl_design.setObjectName("fieldLabel")
        self.design_combo = QComboBox()
        self.design_combo.setObjectName("dropdown")
        self.design_combo.addItems([
            "Option 1: Modern Tag (Price Focus + Yellow Offer Box)",
            "Option 2: Big Savings Tag (₹ Off / DMart Style)"
        ])
        self.design_combo.currentIndexChanged.connect(self.update_live_preview)
        form_row1.addWidget(lbl_design)
        form_row1.addWidget(self.design_combo, 3)

        settings_layout.addLayout(form_row1)

        form_row2 = QHBoxLayout()

        lbl_title = QLabel("Store Title:")
        lbl_title.setObjectName("fieldLabel")
        self.store_title_input = QLineEdit("BIG Mart Price")
        self.store_title_input.setObjectName("textInput")
        self.store_title_input.setPlaceholderText("e.g. BIG Mart Price")
        self.store_title_input.textChanged.connect(self.update_live_preview)
        form_row2.addWidget(lbl_title)
        form_row2.addWidget(self.store_title_input, 3)

        self.cut_guides_cb = QCheckBox("Cut Guides")
        self.cut_guides_cb.setChecked(True)
        self.cut_guides_cb.setObjectName("checkbox")
        self.cut_guides_cb.toggled.connect(self.update_live_preview)
        form_row2.addWidget(self.cut_guides_cb)

        settings_layout.addLayout(form_row2)
        left_layout.addWidget(settings_card)

        # 4. Action & Progress Card
        action_card = QFrame()
        action_card.setObjectName("cardFrame")
        action_layout = QVBoxLayout(action_card)
        action_layout.setContentsMargins(16, 12, 16, 12)
        action_layout.setSpacing(10)

        btn_row = QHBoxLayout()
        self.generate_btn = QPushButton("⚡ Generate Price Tags PDF (8 per A4)")
        self.generate_btn.setObjectName("generateBtn")
        self.generate_btn.setEnabled(False)
        self.generate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.generate_btn.clicked.connect(self.start_pdf_generation)
        btn_row.addWidget(self.generate_btn, 2)

        self.open_pdf_btn = QPushButton("📄 Done! Open PDF")
        self.open_pdf_btn.setObjectName("openPdfBtn")
        self.open_pdf_btn.setEnabled(False)
        self.open_pdf_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_pdf_btn.clicked.connect(self.open_generated_pdf)
        btn_row.addWidget(self.open_pdf_btn, 1)

        self.open_folder_btn = QPushButton("📂 Open Folder")
        self.open_folder_btn.setObjectName("openFolderBtn")
        self.open_folder_btn.setEnabled(False)
        self.open_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_folder_btn.clicked.connect(self.open_output_folder)
        btn_row.addWidget(self.open_folder_btn, 1)

        action_layout.addLayout(btn_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("progressBar")
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        action_layout.addWidget(self.progress_bar)

        self.status_message_lbl = QLabel("Ready. Select an Excel file to begin.")
        self.status_message_lbl.setObjectName("statusLabel")
        action_layout.addWidget(self.status_message_lbl)

        left_layout.addWidget(action_card)
        content_layout.addWidget(left_widget, 6)

        # RIGHT COLUMN: LIVE TAG PREVIEW
        right_card = QFrame()
        right_card.setObjectName("cardFrame")
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(16, 12, 16, 12)
        right_layout.setSpacing(8)

        preview_header_row = QHBoxLayout()
        self.preview_title = QLabel("👁️ Live Tag Preview (90x60mm)")
        self.preview_title.setObjectName("sectionTitle")
        preview_header_row.addWidget(self.preview_title)

        preview_header_row.addStretch()
        self.tag_index_lbl = QLabel("Tag #1")
        self.tag_index_lbl.setObjectName("badgeBlue")
        preview_header_row.addWidget(self.tag_index_lbl)
        right_layout.addLayout(preview_header_row)

        self.preview_desc = QLabel("Real-time rendering of the 90mm x 60mm shelf price tag:")
        self.preview_desc.setObjectName("metaLabel")
        right_layout.addWidget(self.preview_desc)

        # Preview Image Container
        self.tag_image_lbl = TagPreviewWidget()
        self.tag_image_lbl.setObjectName("previewImageContainer")
        right_layout.addWidget(self.tag_image_lbl, 1)

        # Quick summary stats underneath preview
        self.stats_box = QFrame()
        self.stats_box.setObjectName("statsBox")
        stats_layout = QHBoxLayout(self.stats_box)
        stats_layout.setContentsMargins(10, 8, 10, 8)

        self.stat_pages_lbl = QLabel("Pages: 0 (A4)")
        self.stat_pages_lbl.setObjectName("statText")
        self.stat_items_lbl = QLabel("Items: 0")
        self.stat_items_lbl.setObjectName("statText")
        self.stat_savings_lbl = QLabel("Max Savings: ₹0")
        self.stat_savings_lbl.setObjectName("statText")

        stats_layout.addWidget(self.stat_pages_lbl)
        stats_layout.addWidget(self.stat_items_lbl)
        stats_layout.addWidget(self.stat_savings_lbl)
        right_layout.addWidget(self.stats_box)

        content_layout.addWidget(right_card, 4)
        main_layout.addLayout(content_layout)

    # --------------------------------------------------------------------------
    # STYLESHEET
    # --------------------------------------------------------------------------
    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #F8FAFC;
                font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
            }
            #headerFrame {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
            }
            #appTitle {
                font-size: 20px;
                font-weight: 700;
                color: #0F172A;
            }
            #appSubtitle {
                font-size: 13px;
                color: #64748B;
            }
            #infoBadge {
                background-color: #EEF2F6;
                color: #334155;
                font-size: 12px;
                font-weight: 600;
                padding: 6px 12px;
                border-radius: 6px;
                border: 1px solid #E2E8F0;
            }
            #cardFrame {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
            }
            #sectionTitle {
                font-size: 14px;
                font-weight: 700;
                color: #1E293B;
            }
            #fieldLabel {
                font-size: 12px;
                font-weight: 600;
                color: #475569;
            }
            #metaLabel {
                font-size: 12px;
                color: #64748B;
            }
            #textInput {
                background-color: #F8FAFC;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
                color: #1E293B;
            }
            #textInput:focus {
                border: 1px solid #2563EB;
                background-color: #FFFFFF;
            }
            #dropdown {
                background-color: #F8FAFC;
                border: 1px solid #CBD5E1;
                border-radius: 5px;
                padding: 4px 8px;
                font-size: 11px;
                color: #1E293B;
            }
            #smallBtn {
                background-color: #E2E8F0;
                color: #1E293B;
                font-size: 11px;
                font-weight: 600;
                padding: 5px 10px;
                border-radius: 5px;
                border: 1px solid #CBD5E1;
            }
            #smallBtn:hover {
                background-color: #CBD5E1;
            }
            #checkbox {
                font-size: 12px;
                font-weight: 600;
                color: #475569;
            }
            #browseBtn {
                background-color: #2563EB;
                color: #FFFFFF;
                font-size: 13px;
                font-weight: 600;
                padding: 8px 16px;
                border-radius: 6px;
                border: none;
            }
            #browseBtn:hover {
                background-color: #1D4ED8;
            }
            #generateBtn {
                background-color: #059669;
                color: #FFFFFF;
                font-size: 14px;
                font-weight: 700;
                padding: 10px 18px;
                border-radius: 6px;
                border: none;
            }
            #generateBtn:hover {
                background-color: #047857;
            }
            #generateBtn:disabled {
                background-color: #94A3B8;
            }
            #openPdfBtn {
                background-color: #2563EB;
                color: #FFFFFF;
                font-size: 13px;
                font-weight: 600;
                padding: 10px 14px;
                border-radius: 6px;
                border: none;
            }
            #openPdfBtn:hover {
                background-color: #1D4ED8;
            }
            #openPdfBtn:disabled {
                background-color: #E2E8F0;
                color: #94A3B8;
            }
            #openFolderBtn {
                background-color: #F1F5F9;
                color: #334155;
                font-size: 13px;
                font-weight: 600;
                padding: 10px 14px;
                border-radius: 6px;
                border: 1px solid #CBD5E1;
            }
            #openFolderBtn:hover {
                background-color: #E2E8F0;
            }
            #openFolderBtn:disabled {
                background-color: #F8FAFC;
                color: #CBD5E1;
                border-color: #E2E8F0;
            }
            #progressBar {
                border: none;
                border-radius: 4px;
                background-color: #E2E8F0;
            }
            #progressBar::chunk {
                background-color: #059669;
                border-radius: 4px;
            }
            #statusLabel {
                font-size: 12px;
                color: #64748B;
            }
            #badgeBlue {
                background-color: #DBEAFE;
                color: #1E40AF;
                font-size: 11px;
                font-weight: 700;
                padding: 3px 8px;
                border-radius: 4px;
            }
            #previewImageContainer {
                background-color: #F1F5F9;
                border: 1px dashed #CBD5E1;
                border-radius: 8px;
                padding: 8px;
            }
            #statsBox {
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 6px;
            }
            #statText {
                font-size: 11px;
                font-weight: 600;
                color: #475569;
            }
            QTableWidget {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 6px;
                gridline-color: #F1F5F9;
                font-size: 12px;
            }
            QTableWidget::item {
                padding: 3px 5px;
            }
            QTableWidget::item:selected {
                background-color: #EFF6FF;
                color: #1E40AF;
            }
            QHeaderView::section {
                background-color: #F8FAFC;
                color: #475569;
                font-weight: 600;
                font-size: 11px;
                border: none;
                border-bottom: 1px solid #E2E8F0;
                padding: 6px;
            }
        """)

    # --------------------------------------------------------------------------
    # DRAG & DROP SUPPORT
    # --------------------------------------------------------------------------
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                path = urls[0].toLocalFile()
                if path.lower().endswith((".xls", ".xlsx", ".csv")):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if os.path.exists(path):
                self.load_file(path)

    # --------------------------------------------------------------------------
    # FILE SELECTION & LOADING
    # --------------------------------------------------------------------------
    def browse_file(self):
        start_dir = os.path.dirname(self.current_excel_path) if self.current_excel_path else os.getcwd()
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Supermarket Pricing File",
            start_dir,
            "Excel Files (*.xls *.xlsx);;All Files (*.*)"
        )
        if file_path:
            self.load_file(file_path)

    def load_file(self, file_path: str):
        try:
            self.loaded_items = parse_pricing_file(file_path)
            self.current_excel_path = file_path
            filename = os.path.basename(file_path)
            file_size_kb = os.path.getsize(file_path) / 1024.0

            self.file_status_lbl.setText(f"✓ <b>{filename}</b> ({file_size_kb:.1f} KB) - {len(self.loaded_items)} products found")
            self.rows_count_lbl.setText(f"{len(self.loaded_items)} items loaded")
            self.status_message_lbl.setText(f"File loaded successfully: {len(self.loaded_items)} products ready.")

            # Populate table with all loaded rows and offer dropdowns
            self.populate_products_table()

            # Update stats dynamically based on selected layout
            self.update_stats_display()

            # Enable Generate button
            self.generate_btn.setEnabled(True)
            self.selected_preview_index = 0
            self.update_live_preview()

        except Exception as e:
            QMessageBox.critical(self, "Error Loading File", f"Failed to parse Excel file:\n\n{str(e)}")
            self.file_status_lbl.setText("Error loading file. Please select a valid Excel file.")

    def populate_products_table(self):
        total = len(self.loaded_items)
        self.preview_table.setRowCount(total)

        for r in range(total):
            item = self.loaded_items[r]
            self.preview_table.setItem(r, 0, QTableWidgetItem(item["item_name"]))
            self.preview_table.setItem(r, 1, QTableWidgetItem(f"₹ {item['mrp_formatted']}"))
            self.preview_table.setItem(r, 2, QTableWidgetItem(f"₹ {item['rate_formatted']}"))
            self.preview_table.setItem(r, 3, QTableWidgetItem(f"₹ {item['savings_formatted']}"))

            # Promotional Offer Cell: Checkbox to enable + Dropdown to select offer
            cell_widget = QWidget()
            cell_layout = QHBoxLayout(cell_widget)
            cell_layout.setContentsMargins(4, 2, 4, 2)
            cell_layout.setSpacing(6)

            chk = QCheckBox()
            chk.setToolTip("Enable promotional offer for this product")

            combo = QComboBox()
            combo.setStyleSheet("font-size: 11px; padding: 2px 4px;")
            offer_list = [o for o in PROMOTIONAL_OFFERS if o != "None"]
            combo.addItems(offer_list)

            current_offer = item.get("offer", "None")
            is_enabled = bool(current_offer and str(current_offer).strip().upper() not in ["NONE", "", "FALSE", "0"])

            chk.setChecked(is_enabled)
            combo.setEnabled(is_enabled)
            if is_enabled and current_offer in offer_list:
                combo.setCurrentText(current_offer)
            else:
                combo.setCurrentIndex(0)

            # Closures to connect signals
            def make_chk_handler(row_idx, c_box):
                def handler(checked):
                    c_box.setEnabled(checked)
                    val = c_box.currentText() if checked else "None"
                    self.on_row_offer_changed(row_idx, val)
                return handler

            def make_combo_handler(row_idx, c_chk):
                def handler(text):
                    if c_chk.isChecked():
                        self.on_row_offer_changed(row_idx, text)
                return handler

            chk.toggled.connect(make_chk_handler(r, combo))
            combo.currentTextChanged.connect(make_combo_handler(r, chk))

            cell_layout.addWidget(chk)
            cell_layout.addWidget(combo, 1)
            self.preview_table.setCellWidget(r, 4, cell_widget)

        if total > 0:
            self.preview_table.selectRow(0)

    def on_row_offer_changed(self, row_idx: int, new_offer: str):
        if row_idx < len(self.loaded_items):
            self.loaded_items[row_idx]["offer"] = new_offer
            if row_idx == self.selected_preview_index:
                self.update_live_preview()

    def apply_bulk_offer(self):
        offer_to_apply = self.bulk_offer_combo.currentText()
        for r in range(self.preview_table.rowCount()):
            cell_widget = self.preview_table.cellWidget(r, 4)
            if cell_widget:
                chk = cell_widget.findChild(QCheckBox)
                combo = cell_widget.findChild(QComboBox)
                if offer_to_apply == "None":
                    if chk:
                        chk.blockSignals(True)
                        chk.setChecked(False)
                        chk.blockSignals(False)
                    if combo:
                        combo.setEnabled(False)
                    if r < len(self.loaded_items):
                        self.loaded_items[r]["offer"] = "None"
                else:
                    if chk:
                        chk.blockSignals(True)
                        chk.setChecked(True)
                        chk.blockSignals(False)
                    if combo:
                        combo.setEnabled(True)
                        combo.blockSignals(True)
                        combo.setCurrentText(offer_to_apply)
                        combo.blockSignals(False)
                    if r < len(self.loaded_items):
                        self.loaded_items[r]["offer"] = offer_to_apply

        self.update_live_preview()
        self.status_message_lbl.setText(f"Applied '{offer_to_apply}' to all {len(self.loaded_items)} products.")

    def clear_all_offers(self):
        for r in range(self.preview_table.rowCount()):
            cell_widget = self.preview_table.cellWidget(r, 4)
            if cell_widget:
                chk = cell_widget.findChild(QCheckBox)
                combo = cell_widget.findChild(QComboBox)
                if chk:
                    chk.blockSignals(True)
                    chk.setChecked(False)
                    chk.blockSignals(False)
                if combo:
                    combo.setEnabled(False)
                if r < len(self.loaded_items):
                    self.loaded_items[r]["offer"] = "None"
        self.update_live_preview()
        self.status_message_lbl.setText("Disabled promotional offers for all products.")

    def on_table_row_clicked(self, row, col):
        if row < len(self.loaded_items):
            self.selected_preview_index = row
            self.tag_index_lbl.setText(f"Tag #{row + 1}")
            self.update_live_preview()

    # --------------------------------------------------------------------------
    # LAYOUT & STATS HELPERS
    # --------------------------------------------------------------------------
    def get_current_layout_mode(self) -> str:
        if hasattr(self, "layout_combo") and self.layout_combo.currentData():
            return self.layout_combo.currentData()
        return "8_tags"

    def update_stats_display(self):
        total_items = len(self.loaded_items)
        layout_mode = self.get_current_layout_mode()
        tags_per_page = PAGE_LAYOUTS.get(layout_mode, PAGE_LAYOUTS["8_tags"])["tags_per_page"]
        total_pages = (total_items + tags_per_page - 1) // tags_per_page if total_items > 0 else 0
        max_savings = max((item["savings"] for item in self.loaded_items), default=0.0)

        self.stat_pages_lbl.setText(f"Pages: {total_pages} (A4)")
        self.stat_items_lbl.setText(f"Items: {total_items}")
        self.stat_savings_lbl.setText(f"Max Savings: ₹{max_savings:.0f}")

    def on_layout_changed(self):
        layout_mode = self.get_current_layout_mode()
        layout_cfg = PAGE_LAYOUTS.get(layout_mode, PAGE_LAYOUTS["8_tags"])
        tags_per_page = layout_cfg["tags_per_page"]

        self.grid_badge.setText(f"📐 {layout_cfg['name']}")
        self.generate_btn.setText(f"⚡ Generate Price Tags PDF ({tags_per_page} per A4)")
        self.preview_title.setText(f"👁️ Live Tag Preview ({layout_cfg['short_name']})")
        self.preview_desc.setText(f"Real-time rendering of the {layout_cfg['name']}:")

        self.update_stats_display()
        self.update_live_preview()

    # --------------------------------------------------------------------------
    # LIVE TAG PREVIEW
    # --------------------------------------------------------------------------
    def update_live_preview(self):
        if not self.loaded_items:
            sample_item = {
                "item_name": "Bingo Mad Angles Achaari Masti 117g",
                "mrp": 50.0,
                "mrp_formatted": "50",
                "rate_a": 34.0,
                "rate_formatted": "34",
                "savings": 16.0,
                "savings_formatted": "16",
                "offer": "BUY 1 GET 1 FREE"
            }
        else:
            idx = min(self.selected_preview_index, len(self.loaded_items) - 1)
            sample_item = self.loaded_items[idx]

        store_title = self.store_title_input.text().strip() or "BIGG Mart Price"
        design_style = "option2" if self.design_combo.currentIndex() == 1 else "option1"
        layout_mode = self.get_current_layout_mode()

        try:
            pil_img = render_tag_preview_image(
                item=sample_item,
                tag_bg_color=self.tag_bg_color,
                store_title=store_title,
                validity_text="",
                design_style=design_style,
                layout_mode=layout_mode
            )
            data = pil_img.convert("RGBA").tobytes("raw", "RGBA")
            qimg = QImage(data, pil_img.width, pil_img.height, QImage.Format.Format_RGBA8888)
            pixmap = QPixmap.fromImage(qimg)

            self.tag_image_lbl.setTagPixmap(pixmap)
        except Exception as e:
            self.tag_image_lbl.setText(f"Preview unavailable:\n{str(e)}")

    # --------------------------------------------------------------------------
    # PDF GENERATION (Supports 8, 2, or 1 Tag per A4 Sheet)
    # --------------------------------------------------------------------------
    def start_pdf_generation(self):
        if not self.loaded_items:
            return

        layout_mode = self.get_current_layout_mode()
        layout_cfg = PAGE_LAYOUTS.get(layout_mode, PAGE_LAYOUTS["8_tags"])
        tags_per_page = layout_cfg["tags_per_page"]

        default_dir = os.path.dirname(self.current_excel_path) if self.current_excel_path else os.getcwd()
        base_name = os.path.splitext(os.path.basename(self.current_excel_path))[0] if self.current_excel_path else "Price_Tags"
        suggested_name = f"{base_name}_{layout_mode}_A4.pdf"
        default_output = os.path.join(default_dir, suggested_name)

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            f"Save Price Tags PDF ({tags_per_page} per A4)",
            default_output,
            "PDF Files (*.pdf)"
        )
        if not save_path:
            return

        # Lock UI
        self.generate_btn.setEnabled(False)
        self.browse_btn.setEnabled(False)
        self.open_pdf_btn.setEnabled(False)
        self.open_folder_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_message_lbl.setText(f"Generating {layout_cfg['name']} ({tags_per_page} per A4 sheet)...")

        store_title = self.store_title_input.text().strip() or "BIGG Mart Price"
        show_cut_guides = self.cut_guides_cb.isChecked()
        design_style = "option2" if self.design_combo.currentIndex() == 1 else "option1"

        self.worker = PdfGenerationWorker(
            items=self.loaded_items,
            output_path=save_path,
            bg_color=self.tag_bg_color,
            store_title=store_title,
            show_cut_guides=show_cut_guides,
            design_style=design_style,
            layout_mode=layout_mode
        )
        self.worker.progress_changed.connect(self.on_pdf_progress)
        self.worker.finished.connect(self.on_pdf_finished)
        self.worker.failed.connect(self.on_pdf_failed)
        self.worker.start()

    def on_pdf_progress(self, current, total):
        pct = int((current / total) * 100)
        self.progress_bar.setValue(pct)
        self.status_message_lbl.setText(f"Processing tag {current} of {total} ({pct}%)...")

    def on_pdf_finished(self, output_path):
        self.generated_pdf_path = output_path
        self.progress_bar.setValue(100)
        self.status_message_lbl.setText(f"✓ PDF generated successfully: {os.path.basename(output_path)}")

        self.generate_btn.setEnabled(True)
        self.browse_btn.setEnabled(True)
        self.open_pdf_btn.setEnabled(True)
        self.open_folder_btn.setEnabled(True)

        total_items = len(self.loaded_items)
        layout_mode = self.get_current_layout_mode()
        layout_cfg = PAGE_LAYOUTS.get(layout_mode, PAGE_LAYOUTS["8_tags"])
        tags_per_page = layout_cfg["tags_per_page"]
        total_pages = (total_items + tags_per_page - 1) // tags_per_page

        reply = QMessageBox.information(
            self,
            "Price Tags PDF Ready!",
            f"Successfully generated <b>{total_items} price tags</b> across <b>{total_pages} A4 pages</b> ({layout_cfg['name']})!<br><br>"
            f"Saved to:<br><code>{output_path}</code><br><br>"
            "Would you like to open the PDF now?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.open_generated_pdf()

    def on_pdf_failed(self, error_msg):
        self.generate_btn.setEnabled(True)
        self.browse_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.status_message_lbl.setText("Generation failed.")
        QMessageBox.critical(self, "PDF Generation Failed", f"An error occurred while generating PDF:\n\n{error_msg}")

    # --------------------------------------------------------------------------
    # ACTION HANDLERS: OPEN PDF & FOLDER
    # --------------------------------------------------------------------------
    def open_generated_pdf(self):
        if self.generated_pdf_path and os.path.exists(self.generated_pdf_path):
            try:
                os.startfile(self.generated_pdf_path)
            except Exception as e:
                QMessageBox.warning(self, "Error Opening PDF", f"Could not launch default PDF viewer:\n{e}")

    def open_output_folder(self):
        if self.generated_pdf_path and os.path.exists(self.generated_pdf_path):
            try:
                subprocess.Popen(f'explorer /select,"{os.path.abspath(self.generated_pdf_path)}"')
            except Exception as e:
                folder = os.path.dirname(self.generated_pdf_path)
                os.startfile(folder)


# ==============================================================================
# MAIN ENTRY POINT
# ==============================================================================
def main():
    app = QApplication(sys.argv)
    app.setApplicationName("BIGG Mart Price Tag Generator")

    window = PriceTagGeneratorApp()

    if os.path.exists("REPORT.xls"):
        window.load_file(os.path.abspath("REPORT.xls"))
    else:
        window.update_live_preview()

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
