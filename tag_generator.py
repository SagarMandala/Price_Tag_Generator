"""
PDF Generation module for Supermarket Shelf Price Tag Generator.
Generates multi-page A4 PDFs with an 8-tag grid (2 columns x 4 rows)
with exact 90mm x 60mm dimensions, pure white background, 'BIGG Mart Price' branding,
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
    text = text.strip()
    if not text:
        return [""]

    # If the text fits in a single line, always return as single line
    if c.stringWidth(text, font_name, font_size) <= max_w:
        return [text]

    words = text.split()
    if len(words) <= 1:
        return [text]

    lines = []
    current_line = []

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
        header_h = 30.0 * mm
        footer_h = 40.0 * mm
        f_scale = 3.0
        price_f_scale = 3.0
    elif is_half_page:
        header_h = 23.0 * mm
        footer_h = 31.0 * mm
        f_scale = 2.1
        price_f_scale = 2.1
    else:
        header_h = 11.2 * mm
        footer_h = 13.8 * mm
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
    ix = x + 3.8 * mm * sx
    iw = tw - 7.6 * mm * sx

    # Top & bottom dividers for middle section
    div1_y = y + th - header_h
    div2_y = y + footer_h

    # 2. Header Section: Product Name (Single line always, split only if text exceeds bounds)
    raw_name = item.get("item_name", "PRODUCT NAME").strip()
    header_font_size = 11.2 * f_scale
    if c.stringWidth(raw_name, FONT_BOLD, header_font_size) <= iw:
        lines = [raw_name]
    else:
        single_line = False
        for candidate_sz in [10.8, 10.2, 9.8, 9.2]:
            test_sz = candidate_sz * f_scale
            if c.stringWidth(raw_name, FONT_BOLD, test_sz) <= iw:
                header_font_size = test_sz
                lines = [raw_name]
                single_line = True
                break
        if not single_line:
            header_font_size = 10.0 * f_scale
            lines = wrap_text_to_lines(raw_name, iw, FONT_BOLD, header_font_size, c, max_lines=2)

    c.setFillColor(colors.HexColor("#111111"))
    c.setFont(FONT_BOLD, header_font_size)

    if len(lines) == 1:
        line_y = div1_y + (header_h - header_font_size * 0.75) / 2.0
        c.drawString(ix, line_y, lines[0])
    else:
        total_text_h = 2 * header_font_size + 2.0 * f_scale
        base_y = div1_y + (header_h - total_text_h) / 2.0
        c.drawString(ix, base_y + header_font_size + 2.0 * f_scale, lines[0])
        c.drawString(ix, base_y, lines[1])

    # Top Divider Line below header
    c.setStrokeColor(colors.HexColor("#1A1A1A"))
    c.setLineWidth(0.75 * f_scale)
    c.line(x + 2.5 * mm * sx, div1_y, x + tw - 2.5 * mm * sx, div1_y)

    # 3. Middle Pricing Section
    # Left Column: Store Title ("BIG MART PRICE") & MRP
    # Right Column: Promotional Offer Box (if present) placed above Rate-A Price
    mid_h = div1_y - div2_y
    giant_baseline_y = div2_y + 0.6 * mm * f_scale
    rate_formatted = item.get("rate_formatted", "0")

    offer = item.get("offer", "None")
    has_promo = bool(offer and str(offer).strip().upper() not in ["NONE", "", "FALSE", "0"])

    if has_promo:
        # Promotional Offer Box placed directly ABOVE the Rate-A price in the right column
        if is_full_page:
            pbox_h = 18.0 * mm
            pbox_w = 148.0 * mm
            base_p_font = 24.0
        elif is_half_page:
            pbox_h = 12.5 * mm
            pbox_w = 102.0 * mm
            base_p_font = 17.0
        else:
            pbox_h = 5.8 * mm * f_scale
            pbox_w = 48.0 * mm * sx
            base_p_font = 9.2 * f_scale

        pbox_top = div1_y - 0.7 * mm * f_scale
        pbox_y = pbox_top - pbox_h
        pbox_x = x + tw - 3.0 * mm * sx - pbox_w

        # Draw Yellow Promo Box
        c.setFillColor(colors.HexColor("#FFE500"))
        c.setStrokeColor(colors.HexColor("#1A1A1A"))
        c.setLineWidth(0.85 * f_scale)
        c.roundRect(pbox_x, pbox_y, pbox_w, pbox_h, 1.4 * mm * f_scale, fill=1, stroke=1)

        badge_text = str(offer).strip().upper()
        offer_font_size = base_p_font
        while c.stringWidth(badge_text, FONT_BOLD, offer_font_size) > (pbox_w - 4.0 * mm * f_scale) and offer_font_size > (6.5 * f_scale):
            offer_font_size -= 0.5 * f_scale

        c.setFont(FONT_BOLD, offer_font_size)
        c.setFillColor(colors.HexColor("#111111"))
        ot_w = c.stringWidth(badge_text, FONT_BOLD, offer_font_size)
        c.drawString(pbox_x + (pbox_w - ot_w) / 2.0, pbox_y + (pbox_h - offer_font_size) / 2.0 + 0.8 * f_scale, badge_text)

        # Available vertical for Rate-A below promo box
        avail_vert = (pbox_y - 0.4 * mm * f_scale) - giant_baseline_y
        target_giant_size = avail_vert / 0.70
        max_rate_w = 58.5 * mm * sx

        giant_size = min(92.0 * price_f_scale, target_giant_size)
        rupee_size = giant_size * 0.36
        rupee_gap = 1.0 * mm * sx
        r_w = c.stringWidth(rupee, FONT_BOLD, rupee_size) + rupee_gap
        val_w = c.stringWidth(rate_formatted, FONT_BOLD, giant_size)
        total_rate_w = r_w + val_w

        if total_rate_w > max_rate_w:
            scale = max_rate_w / total_rate_w
            giant_size *= scale
            rupee_size *= scale
            r_w *= scale
            val_w *= scale
            total_rate_w = max_rate_w

        # Position Rate-A under promo box:
        # If rate fits within pbox_w, center under promo box; otherwise expand leftward
        if total_rate_w <= pbox_w:
            offer_x = pbox_x + (pbox_w - total_rate_w) / 2.0
        else:
            offer_x = x + tw - 3.0 * mm * sx - total_rate_w

        rupee_raise = giant_size * 0.34
        c.setFont(FONT_BOLD, rupee_size)
        c.drawString(offer_x, giant_baseline_y + rupee_raise, rupee)
        c.setFont(FONT_BOLD, giant_size)
        c.drawString(offer_x + r_w, giant_baseline_y, rate_formatted)

        title_col_w = pbox_x - ix - 2.0 * mm * sx
        mrp_col_w = offer_x - ix - 2.0 * mm * sx

    else:
        # No promotional offer: Giant Rate-A takes almost the entire height between upper and lower lines
        avail_vert = (div1_y - 0.8 * mm * f_scale) - giant_baseline_y
        target_giant_size = avail_vert / 0.70

        max_rate_w = 58.5 * mm * sx
        giant_size = min(112.0 * price_f_scale, target_giant_size)
        rupee_size = giant_size * 0.36
        rupee_gap = 1.0 * mm * sx
        r_w = c.stringWidth(rupee, FONT_BOLD, rupee_size) + rupee_gap
        val_w = c.stringWidth(rate_formatted, FONT_BOLD, giant_size)
        total_rate_w = r_w + val_w

        if total_rate_w > max_rate_w:
            scale = max_rate_w / total_rate_w
            giant_size *= scale
            rupee_size *= scale
            r_w *= scale
            val_w *= scale
            total_rate_w = max_rate_w

        offer_x = x + tw - 3.0 * mm * sx - total_rate_w
        rupee_raise = giant_size * 0.34

        c.setFont(FONT_BOLD, rupee_size)
        c.setFillColor(colors.HexColor("#111111"))
        c.drawString(offer_x, giant_baseline_y + rupee_raise, rupee)
        c.setFont(FONT_BOLD, giant_size)
        c.drawString(offer_x + r_w, giant_baseline_y, rate_formatted)

        title_col_w = offer_x - ix - 2.0 * mm * sx
        mrp_col_w = offer_x - ix - 2.0 * mm * sx

    # Left Column: Store Title ("BIG MART PRICE") in single line, big
    title_str = store_title.strip().upper()
    title_font_size = 14.5 * price_f_scale
    while c.stringWidth(title_str, FONT_BOLD, title_font_size) > title_col_w and title_font_size > 7.5 * price_f_scale:
        title_font_size -= 0.5 * price_f_scale

    title_w = c.stringWidth(title_str, FONT_BOLD, title_font_size)
    title_x = ix + (title_col_w - title_w) / 2.0
    title_y = div1_y - 2.0 * mm * f_scale - title_font_size * 0.75
    c.setFont(FONT_BOLD, title_font_size)
    c.setFillColor(colors.HexColor("#111111"))
    c.drawString(title_x, title_y, title_str)

    # MRP: Only displayed with strikethrough if MRP is greater than Rate-A (discounted item)
    # If price and rate-a are the same, completely hide the striked MRP
    mrp_val = item.get("mrp", 0.0)
    rate_val = item.get("rate_a", item.get("rate", 0.0))
    mrp_formatted = item.get("mrp_formatted", "0")
    has_discount = (mrp_val > rate_val + 0.001) and (mrp_formatted != rate_formatted)

    if has_discount:
        mrp_str = f"MRP: {rupee} {mrp_formatted}"
        mrp_font_size = 12.0 * price_f_scale
        while c.stringWidth(mrp_str, FONT_BOLD, mrp_font_size) > mrp_col_w and mrp_font_size > 7.5 * price_f_scale:
            mrp_font_size -= 0.5 * price_f_scale

        mrp_w = c.stringWidth(mrp_str, FONT_BOLD, mrp_font_size)
        mrp_x = ix + (mrp_col_w - mrp_w) / 2.0
        mrp_y = div2_y + 1.8 * mm * f_scale

        c.setFont(FONT_BOLD, mrp_font_size)
        c.drawString(mrp_x, mrp_y, mrp_str)

        # Strikethrough line through MRP price value portion
        prefix_w = c.stringWidth(f"MRP: {rupee} ", FONT_BOLD, mrp_font_size)
        price_val_w = c.stringWidth(mrp_formatted, FONT_BOLD, mrp_font_size)
        st_x = mrp_x + prefix_w
        st_y = mrp_y + mrp_font_size * 0.36
        c.setLineWidth(1.4 * price_f_scale)
        c.setStrokeColor(colors.HexColor("#111111"))
        c.line(st_x, st_y, st_x + price_val_w, st_y)

    # Bottom Middle Divider Line
    c.setLineWidth(0.75 * f_scale)
    c.setStrokeColor(colors.HexColor("#1A1A1A"))
    c.line(x + 2.5 * mm * sx, div2_y, x + tw - 2.5 * mm * sx, div2_y)

    # 5. Footer Section: Bigger YOUR SAVINGS (both text and amount cover entire space after bottom line)
    bh = footer_h - 1.8 * mm * f_scale
    by = y + (footer_h - bh) / 2.0

    savings_val = item.get("savings", 0.0)
    savings_formatted = item.get("savings_formatted", "0")

    footer_ix = x + 3.0 * mm * sx
    footer_avail_w = tw - 6.0 * mm * sx

    if savings_val > 0:
        badge_text = "YOUR SAVINGS"
        val_str = f"{rupee} {savings_formatted}"
    else:
        badge_text = "BEST VALUE"
        val_str = f"{rupee} {rate_formatted}"

    savings_font_size = 24.0 * f_scale
    badge_font_size = 14.5 * f_scale

    val_w = c.stringWidth(val_str, FONT_BOLD, savings_font_size)
    val_x = footer_ix + footer_avail_w - val_w
    bw = max(20.0 * mm * f_scale, val_x - footer_ix - 2.2 * mm * f_scale)

    while c.stringWidth(badge_text, FONT_BOLD, badge_font_size) > (bw - bh * 0.6) and badge_font_size > 8.0 * f_scale:
        badge_font_size -= 0.5 * f_scale

    draw_arrow_banner(c, footer_ix, by, bw, bh, badge_text, FONT_BOLD, badge_font_size)
    c.setFont(FONT_BOLD, savings_font_size)
    c.setFillColor(colors.HexColor("#111111"))
    c.drawString(val_x, by + (bh - savings_font_size * 0.72) / 2.0, val_str)


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
    Dominant headline: '₹ <SAVINGS> Off' scaling to cover the entire upper space.
    Middle: Product Name (strictly single line whenever possible) and promo yellow banner.
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

    # 3. Middle Section: Product Name (strictly single line if possible)
    raw_name = item.get("item_name", "PRODUCT NAME").strip()
    name_font_size = 11.5 * f_scale
    if c.stringWidth(raw_name, FONT_BOLD, name_font_size) <= iw:
        lines = [raw_name]
    else:
        single_line = False
        for candidate_sz in [11.0, 10.5, 10.0, 9.5]:
            test_sz = candidate_sz * f_scale
            if c.stringWidth(raw_name, FONT_BOLD, test_sz) <= iw:
                name_font_size = test_sz
                lines = [raw_name]
                single_line = True
                break
        if not single_line:
            name_font_size = 10.2 * f_scale
            lines = wrap_text_to_lines(raw_name, iw, FONT_BOLD, name_font_size, c, max_lines=2)

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

        name_y = pbox_y + pbox_h + 2.0 * mm * f_scale
    else:
        name_y = div_bottom_y + 2.5 * mm * f_scale

    c.setFont(FONT_BOLD, name_font_size)
    c.setFillColor(colors.HexColor("#111111"))
    if len(lines) == 1:
        c.drawString(ix, name_y, lines[0])
        top_name_y = name_y + name_font_size * 0.75
    else:
        c.drawString(ix, name_y + name_font_size + 1.5 * f_scale, lines[0])
        c.drawString(ix, name_y, lines[1])
        top_name_y = name_y + name_font_size * 1.8 + 1.5 * f_scale

    # 4. Top Headline: Giant '₹ <SAVINGS> Off' covering the entire available space
    if savings_val > 0:
        main_val_str = savings_formatted
        suffix_str = "Off"
    else:
        main_val_str = rate_formatted
        suffix_str = "Price"

    top_limit = border_y + border_h - 2.0 * mm * f_scale
    bottom_limit = top_name_y + 1.5 * mm * f_scale
    avail_vert = max(10.0, top_limit - bottom_limit)
    avail_w = border_w - 3.5 * mm * f_scale

    # Scale font size so off amount covers the entire upper space
    val_size = (avail_vert * 0.94) / 0.72
    r_size = val_size * 0.52
    suf_size = val_size * 0.38

    r_w = c.stringWidth(f"{rupee} ", FONT_BOLD, r_size)
    val_w = c.stringWidth(main_val_str, FONT_BOLD, val_size)
    suf_w = c.stringWidth(f" {suffix_str}", FONT_BOLD, suf_size)
    total_hl_w = r_w + val_w + suf_w

    if total_hl_w > avail_w:
        scale = avail_w / total_hl_w
        val_size *= scale
        r_size *= scale
        suf_size *= scale
        r_w *= scale
        val_w *= scale
        suf_w *= scale
        total_hl_w = avail_w

    headline_baseline_y = bottom_limit + (avail_vert - (val_size * 0.72)) / 2.0
    r_raise = val_size * 0.20
    suf_raise = val_size * 0.06
    hl_x = border_x + (border_w - total_hl_w) / 2.0

    c.setFont(FONT_BOLD, r_size)
    c.setFillColor(colors.HexColor("#111111"))
    c.drawString(hl_x, headline_baseline_y + r_raise, rupee)

    c.setFont(FONT_BOLD, val_size)
    c.drawString(hl_x + r_w, headline_baseline_y, main_val_str)

    c.setFont(FONT_BOLD, suf_size)
    c.drawString(hl_x + r_w + val_w + 2.0 * f_scale, headline_baseline_y + suf_raise, suffix_str)



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
