"""
PDF Generation module for Supermarket Shelf Price Tag Generator.
Generates multi-page A4 PDFs with an 8-tag grid (2 columns x 4 rows)
with exact 90mm x 60mm dimensions, pure white background, 'BIG Mart Price' branding,
and support for customizable promotions (e.g. 'BUY 1 GET 1 FREE', 'BUY 2 GET 1 FREE').
"""

import os
import re
from io import BytesIO
from PIL import Image

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# ==============================================================================
# FONT INITIALIZATION
# ==============================================================================
FONT_REGULAR = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
RUPEE_GLYPH_SUPPORTED = False

def init_fonts():
    global FONT_REGULAR, FONT_BOLD, RUPEE_GLYPH_SUPPORTED

    font_candidates = [
        ("TagSegoe", "C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/segoeuib.ttf"),
        ("TagArial", "C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
        ("TagCalibri", "C:/Windows/Fonts/calibri.ttf", "C:/Windows/Fonts/calibrib.ttf"),
    ]

    for name, reg_path, bold_path in font_candidates:
        if os.path.exists(reg_path) and os.path.exists(bold_path):
            try:
                pdfmetrics.registerFont(TTFont(name, reg_path))
                pdfmetrics.registerFont(TTFont(f"{name}-Bold", bold_path))
                FONT_REGULAR = name
                FONT_BOLD = f"{name}-Bold"
                RUPEE_GLYPH_SUPPORTED = True
                return
            except Exception:
                continue

    FONT_REGULAR = "Helvetica"
    FONT_BOLD = "Helvetica-Bold"
    RUPEE_GLYPH_SUPPORTED = False


init_fonts()


def get_rupee_symbol() -> str:
    return "₹" if RUPEE_GLYPH_SUPPORTED else "Rs."


# ==============================================================================
# DRAWING HELPERS
# ==============================================================================
def draw_arrow_banner(c: canvas.Canvas, bx: float, by: float, bw: float, bh: float, text: str, font_name: str, font_size: float):
    """
    Draws an arrow-shaped banner pointing to the right with white text inside.
    Shape: Rounded pill cap on left, straight top/bottom, pointed chevron on right.
    """
    r = bh / 2.0
    tip_dx = bh * 0.40

    p = c.beginPath()
    p.moveTo(bx + r, by)
    p.lineTo(bx + bw - tip_dx, by)
    p.lineTo(bx + bw, by + bh / 2.0)
    p.lineTo(bx + bw - tip_dx, by + bh)
    p.lineTo(bx + r, by + bh)
    p.arcTo(bx, by, bx + 2 * r, by + bh, 90, 180)
    p.close()

    c.saveState()
    c.setFillColor(colors.HexColor("#1A1A1A"))
    c.drawPath(p, fill=1, stroke=0)

    # Text inside banner
    c.setFillColor(colors.white)
    c.setFont(font_name, font_size)
    text_w = c.stringWidth(text, font_name, font_size)
    text_x = bx + r + ((bw - tip_dx - r) - text_w) / 2.0
    text_y = by + (bh - font_size) / 2.0 + 1.2
    c.drawString(text_x, text_y, text)
    c.restoreState()


def wrap_text_to_lines(text: str, max_w: float, font_name: str, font_size: float, c: canvas.Canvas, max_lines: int = 2) -> list[str]:
    words = text.split()
    if not words:
        return [""]

    lines = []
    current_line = []

    unit_pattern = re.compile(r"^\d+(?:\.\d+)?\s*(?:KG|G|GM|GMS|ML|L|LTR|LTRS|PCS|PC|SET|JAR|TUB|FW|RS|/-)$", re.IGNORECASE)
    has_unit_at_end = len(words) > 1 and bool(unit_pattern.match(words[-1]))

    if has_unit_at_end and len(words) >= 3:
        cand1 = " ".join(words[:-1])
        cand2 = words[-1]
        if c.stringWidth(cand1, font_name, font_size) <= max_w:
            return [cand1, cand2]

    for w in words:
        test_line = " ".join(current_line + [w])
        if c.stringWidth(test_line, font_name, font_size) <= max_w:
            current_line.append(w)
        else:
            if current_line:
                lines.append(" ".join(current_line))
                current_line = [w]
            else:
                lines.append(w)
            if len(lines) == max_lines - 1:
                break

    if current_line and len(lines) < max_lines:
        lines.append(" ".join(current_line))

    remaining_idx = len(" ".join(lines).split())
    if remaining_idx < len(words) and len(lines) == max_lines:
        remainder = " ".join(words[remaining_idx:])
        combined = f"{lines[-1]} {remainder}"
        while c.stringWidth(combined + "...", font_name, font_size) > max_w and len(combined) > 5:
            combined = combined[:-1]
        lines[-1] = combined.rstrip()

    return lines


# ==============================================================================
# PAGE & SHEET LAYOUT CONFIGURATIONS (8 Tags, 2 Tags, 1 Tag)
# ==============================================================================
PAGE_LAYOUTS = {
    "8_tags": {
        "id": "8_tags",
        "name": "8 Tags / A4 Sheet (90x60mm - Shelf Tags)",
        "short_name": "8 Tags / A4 (90x60mm)",
        "tags_per_page": 8,
        "cols": 2,
        "rows": 4,
        "tag_w": 90.0 * mm,
        "tag_h": 60.0 * mm,
        "col_gap": 6.0 * mm,
        "row_gap": 5.0 * mm,
        "page_size": A4,
    },
    "2_tags": {
        "id": "2_tags",
        "name": "2 Tags / A4 Sheet (Half Page A5 - Promo Posters)",
        "short_name": "2 Tags / A4 (Half Page A5)",
        "tags_per_page": 2,
        "cols": 1,
        "rows": 2,
        "tag_w": 190.0 * mm,
        "tag_h": 135.0 * mm,
        "col_gap": 0.0 * mm,
        "row_gap": 7.0 * mm,
        "page_size": A4,
    },
    "1_tag": {
        "id": "1_tag",
        "name": "1 Tag / A4 Sheet (Full Page A4 Landscape - Display Sign)",
        "short_name": "1 Tag / A4 Landscape",
        "tags_per_page": 1,
        "cols": 1,
        "rows": 1,
        "tag_w": 277.0 * mm,
        "tag_h": 190.0 * mm,
        "col_gap": 0.0 * mm,
        "row_gap": 0.0 * mm,
        "page_size": landscape(A4),
    }
}


# ==============================================================================
# OPTION 1 RENDERER: MODERN CARD (Price Focus + Yellow Offer Box)
# ==============================================================================
def draw_single_price_tag_option1(
    c: canvas.Canvas,
    x: float,
    y: float,
    tw: float,
    th: float,
    item: dict,
    tag_bg_color: str = "#FFFFFF",
    store_title: str = "BIG Mart Price",
    validity_text: str = "",
    show_cut_guides: bool = True
):
    """
    Renders Option 1: Modern shelf price tag.
    Adaptively scales across 90x60mm, 190x135mm (Half Page), and 190x277mm (Full Page A4).
    Pure white background, no QR code, no side margin text.
    Accommodates promotional offer yellow box and prominent 'YOUR SAVINGS' banner.
    """
    rupee = get_rupee_symbol()

    sx = tw / (90.0 * mm)
    sy = th / (60.0 * mm)

    is_full_page = tw > 240.0 * mm        # 1 tag (277x190mm Landscape)
    is_half_page = 120.0 * mm < tw <= 240.0 * mm # 2 tags (190x135mm)

    if is_full_page:
        header_h = 38.0 * mm
        footer_h = 42.0 * mm
        f_scale = 3.0
        price_f_scale = 3.0
    elif is_half_page:
        header_h = 28.0 * mm
        footer_h = 32.0 * mm
        f_scale = 2.1
        price_f_scale = 2.1
    else:
        header_h = 13.5 * mm
        footer_h = 14.5 * mm
        f_scale = 1.0
        price_f_scale = 1.0

    # 1. Background Fill
    c.setFillColor(colors.HexColor(tag_bg_color))
    c.rect(x, y, tw, th, fill=1, stroke=0)

    # Cut guide border
    if show_cut_guides:
        c.setStrokeColor(colors.HexColor("#D1D5DB"))
        c.setLineWidth(0.4 * f_scale)
        c.setDash(2 * f_scale, 2 * f_scale)
        c.rect(x, y, tw, th, fill=0, stroke=1)
        c.setDash()

    # Usable inner bounds
    ix = x + 4.5 * mm * sx
    iw = tw - 9.0 * mm * sx

    # 2. Header Section: Product Name
    top_y = y + th - 2.8 * mm * f_scale
    raw_name = item.get("item_name", "PRODUCT NAME").strip()

    header_font_size = 11.5 * f_scale
    if len(raw_name) > 36:
        header_font_size = 10.0 * f_scale
    elif len(raw_name) > 26:
        header_font_size = 10.8 * f_scale

    lines = wrap_text_to_lines(raw_name, iw, FONT_BOLD, header_font_size, c, max_lines=2)

    c.setFillColor(colors.HexColor("#111111"))
    c.setFont(FONT_BOLD, header_font_size)

    if len(lines) == 1:
        c.drawString(ix, top_y - header_font_size - 2.5 * f_scale, lines[0])
    else:
        c.drawString(ix, top_y - header_font_size, lines[0])
        c.drawString(ix, top_y - (header_font_size * 2 + 2.0 * f_scale), lines[1])

    # Top Divider Line below header
    div1_y = y + th - header_h
    c.setStrokeColor(colors.HexColor("#1A1A1A"))
    c.setLineWidth(0.75 * f_scale)
    c.line(x + 3.0 * mm * sx, div1_y, x + tw - 3.0 * mm * sx, div1_y)

    # 3. Middle Pricing Section
    div2_y = y + footer_h

    # Left Column: Store Title ("BIG Mart Price") & Strikethrough MRP
    title_raw = store_title.strip()
    if title_raw.upper().startswith("BIG MART"):
        title_line1 = "BIG MART"
        remainder = title_raw[8:].strip().upper()
        title_line2 = remainder if remainder else "PRICE"
    else:
        title_words = title_raw.upper().split(maxsplit=1)
        title_line1 = title_words[0] if title_words else "BIG MART"
        title_line2 = title_words[1] if len(title_words) > 1 else "PRICE"

    title_font_size = 12.0 * price_f_scale
    c.setFont(FONT_BOLD, title_font_size)
    c.drawString(ix, div1_y - 11.5 * price_f_scale, title_line1)
    c.drawString(ix, div1_y - 23.5 * price_f_scale, title_line2)

    # Giant Offer Price (Right Column)
    rate_formatted = item.get("rate_formatted", "0")
    if len(rate_formatted) <= 2:
        giant_size = 46.0 * price_f_scale
        rupee_size = 25.0 * price_f_scale
        giant_baseline_y = div1_y - 41.0 * price_f_scale
        rupee_raise = 11.0 * price_f_scale
    elif len(rate_formatted) <= 3:
        giant_size = 40.0 * price_f_scale
        rupee_size = 23.0 * price_f_scale
        giant_baseline_y = div1_y - 41.0 * price_f_scale
        rupee_raise = 10.0 * price_f_scale
    elif len(rate_formatted) <= 4:
        giant_size = 34.0 * price_f_scale
        rupee_size = 20.0 * price_f_scale
        giant_baseline_y = div1_y - 40.0 * price_f_scale
        rupee_raise = 8.5 * price_f_scale
    else:
        giant_size = 28.0 * price_f_scale
        rupee_size = 18.0 * price_f_scale
        giant_baseline_y = div1_y - 39.0 * price_f_scale
        rupee_raise = 7.0 * price_f_scale

    if is_full_page:
        giant_baseline_y = div1_y - 48.0 * mm

    # MRP with strikethrough (increased by 50% from base)
    mrp_formatted = item.get("mrp_formatted", "0")
    mrp_str = f"MRP: {rupee} {mrp_formatted}"

    mrp_font_size = 14.7 * price_f_scale
    c.setFont(FONT_BOLD, mrp_font_size)
    mrp_y = giant_baseline_y + 0.5 * price_f_scale
    c.drawString(ix, mrp_y, mrp_str)

    # Strikethrough line through MRP price portion
    mrp_prefix_w = c.stringWidth(f"MRP: {rupee} ", FONT_BOLD, mrp_font_size)
    price_val_w = c.stringWidth(mrp_formatted, FONT_BOLD, mrp_font_size)
    st_x = ix + mrp_prefix_w - 1
    st_y = mrp_y + 5.0 * price_f_scale
    c.setLineWidth(1.6 * price_f_scale)
    c.setStrokeColor(colors.HexColor("#111111"))
    c.line(st_x, st_y, st_x + price_val_w + 2 * price_f_scale, st_y)

    # Draw Giant Offer Price
    giant_w = c.stringWidth(rate_formatted, FONT_BOLD, giant_size)
    rupee_w = c.stringWidth(f"{rupee} ", FONT_BOLD, rupee_size)
    total_offer_w = rupee_w + giant_w

    offer_x = x + tw - 5.0 * mm * sx - total_offer_w
    c.setFont(FONT_BOLD, rupee_size)
    c.drawString(offer_x, giant_baseline_y + rupee_raise, rupee)
    c.setFont(FONT_BOLD, giant_size)
    c.drawString(offer_x + rupee_w - 1, giant_baseline_y, rate_formatted)

    # 4. Promotional Offer Box (Yellow Box between Price and Footer)
    offer = item.get("offer", "None")
    has_promo = bool(offer and str(offer).strip().upper() not in ["NONE", "", "FALSE", "0"])

    if has_promo:
        if is_full_page:
            pbox_h = 22.0 * mm
            pbox_y = div2_y + 7.0 * mm
            corner_r = 3.5 * mm
            base_p_font = 26.0
        elif is_half_page:
            pbox_h = 22.0 * mm
            pbox_y = div2_y + 4.5 * mm
            corner_r = 3.0 * mm
            base_p_font = 22.0
        else:
            pbox_h = 10.2 * mm
            pbox_y = div2_y + 2.0 * mm
            corner_r = 1.8 * mm
            base_p_font = 11.5

        pbox_x = ix
        pbox_w = iw

        # Draw bright supermarket yellow box with crisp dark border
        c.setFillColor(colors.HexColor("#FFE500"))
        c.setStrokeColor(colors.HexColor("#1A1A1A"))
        c.setLineWidth(0.85 * f_scale)
        c.roundRect(pbox_x, pbox_y, pbox_w, pbox_h, corner_r, fill=1, stroke=1)

        badge_text = str(offer).strip().upper()
        offer_font_size = base_p_font
        max_t_w = pbox_w - 8.0 * mm * f_scale
        while c.stringWidth(badge_text, FONT_BOLD, offer_font_size) > max_t_w and offer_font_size > (8.0 * f_scale):
            offer_font_size -= 0.5 * f_scale

        c.setFont(FONT_BOLD, offer_font_size)
        c.setFillColor(colors.HexColor("#111111"))
        t_w = c.stringWidth(badge_text, FONT_BOLD, offer_font_size)
        t_x = pbox_x + (pbox_w - t_w) / 2.0
        t_y = pbox_y + (pbox_h - offer_font_size) / 2.0 + 1.2 * f_scale
        c.drawString(t_x, t_y, badge_text)

    # Bottom Middle Divider Line
    c.setLineWidth(0.75 * f_scale)
    c.setStrokeColor(colors.HexColor("#1A1A1A"))
    c.line(x + 3.0 * mm * sx, div2_y, x + tw - 3.0 * mm * sx, div2_y)

    # 5. Footer Section: Always Shows Prominent Savings / Best Value Banner
    if is_full_page:
        bh = 26.0 * mm
        badge_font_size = 32.0
        savings_font_size = 44.0
        badge_w = 130.0 * mm
    elif is_half_page:
        bh = 17.5 * mm
        badge_font_size = 24.0
        savings_font_size = 32.0
        badge_w = 95.0 * mm
    else:
        bh = 8.5 * mm
        badge_font_size = 12.5
        savings_font_size = 17.0
        badge_w = 46.0 * mm

    by = y + (footer_h - bh) / 2.0

    savings_val = item.get("savings", 0.0)
    savings_formatted = item.get("savings_formatted", "0")

    if savings_val > 0:
        badge_text = "YOUR SAVINGS"
        savings_str = f"{rupee} {savings_formatted}"

        c.setFont(FONT_BOLD, savings_font_size)
        savings_w = c.stringWidth(savings_str, FONT_BOLD, savings_font_size)
        total_footer_w = badge_w + 3.0 * mm * f_scale + savings_w
        bx = x + (tw - total_footer_w) / 2.0

        draw_arrow_banner(c, bx, by, badge_w, bh, badge_text, FONT_BOLD, badge_font_size)
        c.setFillColor(colors.HexColor("#111111"))
        c.drawString(bx + badge_w + 2.5 * mm * f_scale, by + 1.4 * f_scale, savings_str)
    else:
        badge_text = "BEST VALUE"
        if not is_full_page and not is_half_page:
            badge_w = 42.0 * mm
        else:
            badge_w = badge_w * 0.9
        rate_str = f"{rupee} {rate_formatted}"

        c.setFont(FONT_BOLD, savings_font_size)
        rate_w = c.stringWidth(rate_str, FONT_BOLD, savings_font_size)
        total_footer_w = badge_w + 3.0 * mm * f_scale + rate_w
        bx = x + (tw - total_footer_w) / 2.0

        draw_arrow_banner(c, bx, by, badge_w, bh, badge_text, FONT_BOLD, badge_font_size)
        c.setFillColor(colors.HexColor("#111111"))
        c.drawString(bx + badge_w + 2.5 * mm * f_scale, by + 1.4 * f_scale, rate_str)


# ==============================================================================
# OPTION 2 RENDERER: BIG SAVINGS / DMART STYLE ("₹ Off" Highlight)
# ==============================================================================
def draw_single_price_tag_option2(
    c: canvas.Canvas,
    x: float,
    y: float,
    tw: float,
    th: float,
    item: dict,
    tag_bg_color: str = "#FFFFFF",
    store_title: str = "BIG Mart Price",
    validity_text: str = "",
    show_cut_guides: bool = True
):
    """
    Renders Option 2: Big Savings / DMart Style Price Tag.
    Adaptively scales across 90x60mm, 190x135mm (Half Page), and 190x277mm (Full Page A4).
    Dominant headline: '₹ <SAVINGS> Off' at top.
    Middle: Product Name (and optional promotional yellow banner if active).
    Bottom: 'MRP ₹ <mrp>' and '<Store Title> ₹ <rate>'.
    Enclosed in a solid rectangular black border.
    """
    rupee = get_rupee_symbol()

    sx = tw / (90.0 * mm)
    sy = th / (60.0 * mm)

    is_full_page = tw > 240.0 * mm        # 1 tag (277x190mm Landscape)
    is_half_page = 120.0 * mm < tw <= 240.0 * mm # 2 tags (190x135mm)

    if is_full_page:
        f_scale = 2.8
        border_margin = 5.0 * mm
        bottom_h = 24.0 * mm
    elif is_half_page:
        f_scale = 2.1
        border_margin = 4.0 * mm
        bottom_h = 18.0 * mm
    else:
        f_scale = 1.0
        border_margin = 2.2 * mm
        bottom_h = 8.8 * mm

    # 1. Background Fill
    c.setFillColor(colors.HexColor(tag_bg_color))
    c.rect(x, y, tw, th, fill=1, stroke=0)

    # Cut guide border
    if show_cut_guides:
        c.setStrokeColor(colors.HexColor("#D1D5DB"))
        c.setLineWidth(0.4 * f_scale)
        c.setDash(2 * f_scale, 2 * f_scale)
        c.rect(x, y, tw, th, fill=0, stroke=1)
        c.setDash()

    # Inner Solid Black Border
    border_x = x + border_margin
    border_y = y + border_margin
    border_w = tw - (border_margin * 2)
    border_h = th - (border_margin * 2)

    c.setStrokeColor(colors.HexColor("#111111"))
    c.setLineWidth(1.8 * f_scale)
    c.rect(border_x, border_y, border_w, border_h, fill=0, stroke=1)

    ix = border_x + 3.0 * mm * f_scale
    iw = border_w - 6.0 * mm * f_scale

    # Bottom pricing row divider line
    div_bottom_y = border_y + bottom_h
    c.setStrokeColor(colors.HexColor("#1A1A1A"))
    c.setLineWidth(0.75 * f_scale)
    c.line(border_x, div_bottom_y, border_x + border_w, div_bottom_y)

    # 2. Bottom Row: MRP and Store Price (Side by Side)
    mrp_formatted = item.get("mrp_formatted", "0")
    mrp_text = f"MRP {rupee} {mrp_formatted}"
    c.setFont(FONT_BOLD, 10.8 * f_scale)
    c.setFillColor(colors.HexColor("#111111"))
    c.drawString(ix, border_y + 2.8 * mm * f_scale, mrp_text)

    # Right: Store Title Price (e.g. "BIG Mart Price ₹ 515")
    rate_formatted = item.get("rate_formatted", "0")
    store_text = f"{store_title} {rupee} {rate_formatted}"
    c.setFont(FONT_BOLD, 11.2 * f_scale)
    c.drawRightString(border_x + border_w - 3.0 * mm * f_scale, border_y + 2.8 * mm * f_scale, store_text)

    # Check promotional scheme
    offer = item.get("offer", "None")
    has_promo = bool(offer and str(offer).strip().upper() not in ["NONE", "", "FALSE", "0"])

    savings_val = item.get("savings", 0.0)
    savings_formatted = item.get("savings_formatted", "0")

    # 3. Middle Section: Product Name (and Promo Yellow Strip if present)
    raw_name = item.get("item_name", "PRODUCT NAME").strip()

    if has_promo:
        if is_full_page:
            pbox_h = 18.0 * mm
            pbox_y = div_bottom_y + 4.0 * mm
            p_font_size = 22.0
        elif is_half_page:
            pbox_h = 14.5 * mm
            pbox_y = div_bottom_y + 2.5 * mm
            p_font_size = 18.0
        else:
            pbox_h = 6.8 * mm
            pbox_y = div_bottom_y + 1.5 * mm
            p_font_size = 9.5

        pbox_x = ix
        pbox_w = iw

        c.setFillColor(colors.HexColor("#FFE500"))
        c.setStrokeColor(colors.HexColor("#1A1A1A"))
        c.setLineWidth(0.75 * f_scale)
        c.roundRect(pbox_x, pbox_y, pbox_w, pbox_h, 1.5 * mm * f_scale, fill=1, stroke=1)

        badge_text = str(offer).strip().upper()
        while c.stringWidth(badge_text, FONT_BOLD, p_font_size) > (pbox_w - 6.0 * mm * f_scale) and p_font_size > (7.0 * f_scale):
            p_font_size -= 0.5 * f_scale
        c.setFont(FONT_BOLD, p_font_size)
        c.setFillColor(colors.HexColor("#111111"))
        bw = c.stringWidth(badge_text, FONT_BOLD, p_font_size)
        c.drawString(pbox_x + (pbox_w - bw) / 2.0, pbox_y + (pbox_h - p_font_size) / 2.0 + 1.0 * f_scale, badge_text)

        name_y = pbox_y + pbox_h + 2.5 * mm * f_scale
        name_font_size = 11.2 * f_scale if len(raw_name) <= 30 else 10.0 * f_scale
        lines = wrap_text_to_lines(raw_name, iw, FONT_BOLD, name_font_size, c, max_lines=2)
        c.setFont(FONT_BOLD, name_font_size)
        c.setFillColor(colors.HexColor("#111111"))
        if len(lines) == 1:
            c.drawString(ix, name_y + 1.0 * mm * f_scale, lines[0])
            top_name_y = name_y + 1.0 * mm * f_scale + name_font_size
        else:
            c.drawString(ix, name_y + 4.2 * mm * f_scale, lines[0])
            c.drawString(ix, name_y + 0.5 * mm * f_scale, lines[1])
            top_name_y = name_y + 4.2 * mm * f_scale + name_font_size
    else:
        name_font_size = (12.0 if len(raw_name) <= 26 else (11.0 if len(raw_name) <= 38 else 10.0)) * f_scale
        lines = wrap_text_to_lines(raw_name, iw, FONT_BOLD, name_font_size, c, max_lines=2)
        c.setFont(FONT_BOLD, name_font_size)
        c.setFillColor(colors.HexColor("#111111"))
        if len(lines) == 1:
            c.drawString(ix, div_bottom_y + 4.0 * mm * f_scale, lines[0])
            top_name_y = div_bottom_y + 4.0 * mm * f_scale + name_font_size
        else:
            c.drawString(ix, div_bottom_y + 8.0 * mm * f_scale, lines[0])
            c.drawString(ix, div_bottom_y + 3.0 * mm * f_scale, lines[1])
            top_name_y = div_bottom_y + 8.0 * mm * f_scale + name_font_size

    # 4. Top Headline: Giant '₹ <SAVINGS> Off' (As in Option2.jpeg)
    if savings_val > 0:
        main_val_str = savings_formatted
        suffix_str = "Off"
    else:
        main_val_str = rate_formatted
        suffix_str = "Price"

    if is_full_page:
        h_mult = 2.8
    elif is_half_page:
        h_mult = 2.05
    else:
        h_mult = 1.0

    if len(main_val_str) <= 2:
        val_size = 54.0 * h_mult
        r_size = 28.0 * h_mult
        r_raise = 14.0 * h_mult
        suf_size = 21.0 * h_mult
        suf_raise = 3.0 * h_mult
    elif len(main_val_str) <= 3:
        val_size = 50.0 * h_mult
        r_size = 26.0 * h_mult
        r_raise = 13.0 * h_mult
        suf_size = 20.0 * h_mult
        suf_raise = 3.0 * h_mult
    elif len(main_val_str) <= 4:
        val_size = 42.0 * h_mult
        r_size = 22.0 * h_mult
        r_raise = 11.0 * h_mult
        suf_size = 18.0 * h_mult
        suf_raise = 2.5 * h_mult
    else:
        val_size = 34.0 * h_mult
        r_size = 18.0 * h_mult
        r_raise = 9.0 * h_mult
        suf_size = 16.0 * h_mult
        suf_raise = 2.0 * h_mult

    # Center headline vertically in top available space
    top_limit = border_y + border_h - 4.0 * mm * f_scale
    bottom_limit = top_name_y + 3.0 * mm * f_scale
    avail_vert = max(10.0, top_limit - bottom_limit)
    headline_baseline_y = bottom_limit + (avail_vert - (val_size * 0.72)) / 2.0

    if headline_baseline_y + (val_size * 0.75) > top_limit:
        headline_baseline_y = top_limit - (val_size * 0.75)
    if headline_baseline_y < bottom_limit:
        headline_baseline_y = bottom_limit

    r_w = c.stringWidth(f"{rupee} ", FONT_BOLD, r_size)
    val_w = c.stringWidth(main_val_str, FONT_BOLD, val_size)
    suf_w = c.stringWidth(f" {suffix_str}", FONT_BOLD, suf_size)
    total_hl_w = r_w + val_w + suf_w

    hl_x = border_x + (border_w - total_hl_w) / 2.0

    c.setFont(FONT_BOLD, r_size)
    c.setFillColor(colors.HexColor("#111111"))
    c.drawString(hl_x, headline_baseline_y + r_raise, rupee)

    c.setFont(FONT_BOLD, val_size)
    c.drawString(hl_x + r_w, headline_baseline_y, main_val_str)

    c.setFont(FONT_BOLD, suf_size)
    c.drawString(hl_x + r_w + val_w + 3.0 * f_scale, headline_baseline_y + suf_raise, suffix_str)


# ==============================================================================
# ROUTER: DISPATCHES TO SELECTED DESIGN (OPTION 1 OR OPTION 2)
# ==============================================================================
def draw_single_price_tag(
    c: canvas.Canvas,
    x: float,
    y: float,
    tw: float,
    th: float,
    item: dict,
    tag_bg_color: str = "#FFFFFF",
    store_title: str = "BIG Mart Price",
    validity_text: str = "",
    show_cut_guides: bool = True,
    design_style: str = "option1"
):
    """
    Renders a single tag according to the chosen design style.
    design_style: 'option1' (Modern Price Focus) or 'option2' (Big Savings ₹ Off / DMart Style).
    """
    if str(design_style).lower() in ["option2", "2", "dmart", "savings_focus"]:
        draw_single_price_tag_option2(
            c=c,
            x=x,
            y=y,
            tw=tw,
            th=th,
            item=item,
            tag_bg_color=tag_bg_color,
            store_title=store_title,
            validity_text=validity_text,
            show_cut_guides=show_cut_guides
        )
    else:
        draw_single_price_tag_option1(
            c=c,
            x=x,
            y=y,
            tw=tw,
            th=th,
            item=item,
            tag_bg_color=tag_bg_color,
            store_title=store_title,
            validity_text=validity_text,
            show_cut_guides=show_cut_guides
        )


# ==============================================================================
# FULL MULTI-PAGE PDF GENERATOR (Supports 8, 2, or 1 Tag per A4 Sheet)
# ==============================================================================
def generate_pdf(
    items: list[dict],
    output_pdf_path: str,
    tag_bg_color: str = "#FFFFFF",
    store_title: str = "BIG Mart Price",
    validity_text: str = "",
    show_cut_guides: bool = True,
    design_style: str = "option1",
    layout_mode: str = "8_tags",
    progress_callback=None
) -> str:
    """
    Generates a printable A4 PDF with 8, 2, or 1 tag(s) per sheet using the selected layout and design.
    """
    if not items:
        raise ValueError("No items provided to generate price tags.")

    init_fonts()

    layout_cfg = PAGE_LAYOUTS.get(layout_mode, PAGE_LAYOUTS["8_tags"])
    tags_per_page = layout_cfg["tags_per_page"]
    cols = layout_cfg["cols"]
    rows = layout_cfg["rows"]
    tag_w = layout_cfg["tag_w"]
    tag_h = layout_cfg["tag_h"]
    col_gap = layout_cfg["col_gap"]
    row_gap = layout_cfg["row_gap"]

    page_size = layout_cfg.get("page_size", A4)
    page_w, page_h = page_size

    total_grid_w = cols * tag_w + (cols - 1) * col_gap
    total_grid_h = rows * tag_h + (rows - 1) * row_gap

    margin_x = (page_w - total_grid_w) / 2.0
    margin_y = (page_h - total_grid_h) / 2.0

    c = canvas.Canvas(output_pdf_path, pagesize=page_size)
    total_items = len(items)

    for idx, item in enumerate(items):
        slot_on_page = idx % tags_per_page

        if slot_on_page == 0 and idx > 0:
            c.showPage()
            c.setPageSize(page_size)

        col = slot_on_page % cols
        row = slot_on_page // cols

        tag_x = margin_x + col * (tag_w + col_gap)
        tag_y = margin_y + (rows - 1 - row) * (tag_h + row_gap)

        draw_single_price_tag(
            c=c,
            x=tag_x,
            y=tag_y,
            tw=tag_w,
            th=tag_h,
            item=item,
            tag_bg_color=tag_bg_color,
            store_title=store_title,
            validity_text="",
            show_cut_guides=show_cut_guides,
            design_style=design_style
        )

        if progress_callback:
            progress_callback(idx + 1, total_items)

    c.save()
    return output_pdf_path


def render_tag_preview_image(
    item: dict,
    tag_bg_color: str = "#FFFFFF",
    store_title: str = "BIG Mart Price",
    validity_text: str = "",
    design_style: str = "option1",
    layout_mode: str = "8_tags"
) -> Image.Image:
    """
    Renders a single tag to a high-resolution PIL Image for live GUI preview,
    using dimensions and aspect ratio corresponding to the chosen layout.
    """
    init_fonts()
    layout_cfg = PAGE_LAYOUTS.get(layout_mode, PAGE_LAYOUTS["8_tags"])
    tag_w = layout_cfg["tag_w"]
    tag_h = layout_cfg["tag_h"]

    bio = BytesIO()
    c = canvas.Canvas(bio, pagesize=(tag_w, tag_h))
    draw_single_price_tag(
        c=c,
        x=0,
        y=0,
        tw=tag_w,
        th=tag_h,
        item=item,
        tag_bg_color=tag_bg_color,
        store_title=store_title,
        validity_text="",
        show_cut_guides=False,
        design_style=design_style
    )
    c.save()
    bio.seek(0)

    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument(bio)
    page = pdf[0]
    # For large posters, scale 2.0 provides plenty of crisp resolution without huge memory
    scale_val = 3.0 if layout_mode == "8_tags" else (2.0 if layout_mode == "2_tags" else 1.5)
    pil_image = page.render(scale=scale_val).to_pil()
    return pil_image
