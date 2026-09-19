"""
Data processing module for Supermarket Shelf Price Tag Generator.
Handles parsing Excel files (.xls, .xlsx), cleaning prices, and calculating savings.
"""

import os
import re
import hashlib
import pandas as pd


PROMOTIONAL_OFFERS = [
    "None",
    "BUY 1 GET 1 FREE",
    "BUY 2 GET 1 FREE",
    "BUY 3 GET 1 FREE",
    "BUY 2 GET 2 FREE",
    "BUY 1 GET 1 @ 50% OFF",
    "BUY 2 GET 10% OFF",
    "BUY 2 GET 15% OFF",
    "BUY 2 GET 20% OFF",
    "FLAT 10% OFF",
    "FLAT 20% OFF",
    "FLAT 30% OFF",
    "FLAT 50% OFF",
    "COMBO OFFER",
    "MEGA SAVER",
    "SPECIAL OFFER"
]


def clean_price(val) -> float:
    """
    Extracts a numeric float from price strings like 'MRP.470.00', 'Rs. 230', '40.00', etc.
    Returns 0.0 if parsing fails.
    """
    if pd.isna(val) or val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)

    s = str(val).strip()
    # Find all matches for numbers with optional decimal point
    matches = re.findall(r"[-+]?\d+(?:\.\d+)?", s)
    if matches:
        try:
            return float(matches[0])
        except ValueError:
            pass

    # Fallback: remove everything except digits and dot
    cleaned = re.sub(r"[^\d.]", "", s)
    try:
        return float(cleaned) if cleaned else 0.0
    except ValueError:
        return 0.0


def format_currency(val: float) -> str:
    """
    Formats a numeric price cleanly:
    - 460.0 -> '460'
    - 49.5  -> '49.50'
    - 49.25 -> '49.25'
    """
    if val is None:
        return "0"
    val = round(float(val), 2)
    if val.is_integer():
        return f"{int(val)}"
    return f"{val:.2f}"


def generate_ean13(text: str) -> str:
    """
    Generates a realistic 13-digit Indian EAN barcode number (starting with 890)
    deterministically from the product name if no barcode is provided in the Excel sheet.
    """
    h = hashlib.md5(text.encode("utf-8")).hexdigest()
    # Extract 9 digits from hash
    digits = "".join(filter(str.isdigit, h))[:9].ljust(9, "0")
    # Base 12 digits: 890 (India country code) + 9 digits
    base12 = "890" + digits
    # Calculate EAN-13 checksum digit
    evens = sum(int(base12[i]) for i in range(1, 12, 2)) * 3
    odds = sum(int(base12[i]) for i in range(0, 12, 2))
    check = (10 - ((odds + evens) % 10)) % 10
    return f"{base12}{check}"


def find_column(df_columns, candidates):
    """
    Finds a column name in df_columns matching any candidate (case-insensitive, ignoring whitespace).
    """
    norm_cols = {re.sub(r"[\s_-]+", "", str(c).strip().upper()): c for c in df_columns}
    for cand in candidates:
        norm_cand = re.sub(r"[\s_-]+", "", cand.upper())
        if norm_cand in norm_cols:
            return norm_cols[norm_cand]
    return None


def parse_pricing_file(file_path: str):
    """
    Loads an Excel file (.xls, .xlsx) and returns a list of cleaned tag item dictionaries.
    Each item contains:
    - index: int
    - item_name: str
    - mrp: float
    - mrp_formatted: str
    - rate_a: float
    - rate_formatted: str
    - savings: float
    - savings_formatted: str
    - barcode: str
    - rack_code: str
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    # Determine engine based on extension
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".xls":
        # xlrd or default
        df = pd.read_excel(file_path, engine="xlrd")
    elif ext == ".xlsx":
        df = pd.read_excel(file_path, engine="openpyxl")
    elif ext == ".csv":
        df = pd.read_csv(file_path)
    else:
        # Let pandas auto-detect
        df = pd.read_excel(file_path)

    # Detect key columns
    cols = df.columns.tolist()
    item_col = find_column(cols, ["ITEM NAME", "ITEMNAME", "ITEM", "PRODUCT NAME", "PRODUCT", "DESCRIPTION", "NAME"])
    mrp_col = find_column(cols, ["MRP", "MAX RETAIL PRICE", "ORIGINAL PRICE", "M.R.P."])
    rate_col = find_column(cols, ["RATE-A", "RATE A", "RATE", "OFFER PRICE", "SELLING PRICE", "SPECIAL PRICE", "OUR PRICE"])
    barcode_col = find_column(cols, ["BARCODE", "EAN", "UPC", "ITEM CODE", "CODE"])
    rack_col = find_column(cols, ["RACK", "LOCATION", "BIN", "RACK CODE", "SHELF"])
    offer_col = find_column(cols, ["OFFER", "PROMOTION", "SCHEME", "DEAL", "PROMO"])

    if not item_col:
        raise ValueError("Could not find product name column (e.g. 'ITEM NAME') in the Excel file.")
    if not mrp_col:
        raise ValueError("Could not find MRP column (e.g. 'MRP') in the Excel file.")
    if not rate_col:
        raise ValueError("Could not find offer rate column (e.g. 'RATE-A') in the Excel file.")

    items = []
    for idx, row in df.iterrows():
        raw_name = row.get(item_col)
        if pd.isna(raw_name) or not str(raw_name).strip():
            continue  # Skip blank rows

        item_name = str(raw_name).strip()
        mrp_val = clean_price(row.get(mrp_col))
        rate_val = clean_price(row.get(rate_col))

        savings_val = max(0.0, round(mrp_val - rate_val, 2))

        # Barcode & Rack Code
        if barcode_col and not pd.isna(row.get(barcode_col)):
            barcode_str = str(row.get(barcode_col)).strip()
            if barcode_str.endswith(".0"):
                barcode_str = barcode_str[:-2]
        else:
            barcode_str = generate_ean13(item_name)

        if rack_col and not pd.isna(row.get(rack_col)):
            rack_str = str(row.get(rack_col)).strip()
        else:
            h_sub = hashlib.md5(item_name.encode("utf-8")).hexdigest()[:4].upper()
            rack_str = f"W{h_sub}-1-2-3"

        # Offer / Promotion scheme
        offer_val = "None"
        if offer_col and not pd.isna(row.get(offer_col)):
            cand_offer = str(row.get(offer_col)).strip()
            if cand_offer and cand_offer.lower() != "nan":
                offer_val = cand_offer

        items.append({
            "index": idx + 1,
            "item_name": item_name,
            "mrp": mrp_val,
            "mrp_formatted": format_currency(mrp_val),
            "rate_a": rate_val,
            "rate_formatted": format_currency(rate_val),
            "savings": savings_val,
            "savings_formatted": format_currency(savings_val),
            "barcode": barcode_str,
            "rack_code": rack_str,
            "offer": offer_val
        })

    return items
