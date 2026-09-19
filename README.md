# 🏷️ Supermarket Shelf Price Tag Generator

A complete, standalone Python desktop GUI application for Windows built with **PyQt6** and **ReportLab**. It converts supermarket pricing spreadsheets (`.xls`, `.xlsx`, `.csv`) into printable multi-page A4 PDFs containing supermarket shelf price tags (6 tags per sheet, 2x3 grid) matching the authentic retail shelf tag reference design.

---

## 🌟 Key Features

1. **Exact Supermarket Shelf Tag Layout (8 Tags per A4 Sheet):**
   - **Page Size:** Standard A4 Portrait (210mm x 297mm) with balanced printable margins.
   - **Grid:** Exactly 8 tags per page (2 columns x 4 rows).
   - **Tag Dimensions:** Exactly **90mm wide x 60mm high**.
   - **Background & Border:** Pure white background with subtle dashed cut-guide lines.

2. **Accurate Tag Content Breakdown:**
   - **Header:** Bold product name (auto-wrapping up to 2 lines) with pack size emphasis.
   - **Branding:** `"BIG Mart Price"` stacked above the MRP.
   - **Middle Pricing Section:**
     - Left: Stacked `"BIG MART PRICE"` header + strikethrough original price `"MRP: ₹ <MRP>"`.
     - Right: Giant bold offer price (Indian Rupee symbol `₹` alongside massive numerals).
     - Crisp divider rules separating header, pricing, and footer.
   - **Promotional Offers & Savings Footer (No QR Code):**
     - Supports per-row promotional schemes: `BUY 1 GET 1 FREE`, `BUY 2 GET 1 FREE`, `BUY 3 GET 1 FREE`, `FLAT 20% OFF`, `FLAT 50% OFF`, etc.
     - Automatically renders dark chevron promotional badges alongside `SAVE ₹ <AMOUNT>`.
     - When no special offer is selected: centered `YOUR SAVINGS ₹ <SAVINGS>` badge.
     - Handles zero savings cleanly with a `BEST VALUE` badge.

3. **Modern PyQt6 Desktop GUI:**
   - Drag-and-drop or file browser for `.xls` and `.xlsx`.
   - Interactive Products Table showing all items with **per-row Promotional Offer dropdowns**.
   - "Bulk Set Offer for All" button to apply schemes across all products in one click.
   - Live interactive tag preview widget updating in real time as you change offers or select items.
   - Multi-threaded PDF generation with animated progress bar.
   - One-click "Done! Open PDF" and "Open Folder" action buttons.

4. **Robust Data Parsing:**
   - Supports both legacy `.xls` (via `xlrd`) and modern `.xlsx` (via `openpyxl`).
   - Flexible column matching: `ITEM NAME`, `MRP`, `RATE-A` (and optional `BARCODE`, `RACK`).
   - Cleans raw price strings like `"MRP.470.00"` or `"Rs. 230"` via regex.

---

## 🚀 Quick Start & Run

### Prerequisites
- Python 3.10+ (Python 3.11 recommended) on Windows.

### Installation
```bash
# 1. Clone or navigate to the project directory
cd Price_Slip

# 2. Install required dependencies
python -m pip install -r requirements.txt
```

### Launch the Application
```bash
python app.py
```

---

## 📦 Building Standalone Windows Executable (.exe)

You can compile the entire application into a standalone `.exe` that runs on any Windows machine without needing Python installed:

### Option A: Run the One-Click Build Script
Double-click `build_exe.bat` in Windows Explorer, or run:
```bat
build_exe.bat
```

### Option B: Run PyInstaller Directly
```bash
pyinstaller price_tag_generator.spec --clean --noconfirm
```

Once compilation completes, the standalone executable is generated at:
```
dist/PriceTagGenerator.exe
```

---

## 📂 Project Architecture

```
Price_Slip/
├── app.py                     # PyQt6 GUI application & Live Tag Preview
├── tag_generator.py           # Core ReportLab 6-tag A4 PDF generation engine
├── data_processor.py          # Excel parser, regex price cleaner & savings calculator
├── requirements.txt           # Python dependency specifications
├── build_exe.bat              # One-click Windows .exe compilation script
├── price_tag_generator.spec   # PyInstaller build configuration
├── REPORT.xls                 # Sample supermarket pricing dataset (36 products)
└── README.md                  # Project documentation & usage instructions
```

---

## 🛠️ Data Format Specification

The application automatically parses Excel sheets containing:
| Column Name | Description | Example Input |
|---|---|---|
| `ITEM NAME` | Product name with pack weight/size | `Bingo Mad Angles Achaari Masti 117g` |
| `MRP` | Maximum retail price (numeric or string) | `MRP.470.00` or `50` |
| `RATE-A` | Selling / offer price | `460` or `34` |
| `BARCODE` *(optional)* | Product EAN / UPC code | `8901725107574` (auto-generated if omitted) |
| `RACK` *(optional)* | Store aisle / rack location | `W16004-5-6-7-11` (auto-generated if omitted) |
