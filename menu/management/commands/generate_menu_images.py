"""
Management command: generate_menu_images
Generates styled JPEG placeholder images for MenuItem objects
and uploads them to Cloudinary.

Usage:
    python manage.py generate_menu_images          # only items without images
    python manage.py generate_menu_images --all    # regenerate all
    python manage.py generate_menu_images --dry-run
"""
import io
import textwrap

import cloudinary
import cloudinary.uploader
from django.conf import settings
from django.core.management.base import BaseCommand

from menu.models import MenuItem

# ── Per-category theme ──────────────────────────────────────────────────────
# keyword → (bg_dark, bg_light, accent_hex, label)
CATEGORY_STYLES = {
    "starter":   ("#0d0603", "#2a0c08", "#c0392b", "STARTERS"),
    "duck":      ("#0a0805", "#251504", "#b5651d", "DUCK DISHES"),
    "rice":      ("#060a04", "#142010", "#d4a017", "RICE"),
    "noodle":    ("#0a0705", "#251a06", "#e67e22", "NOODLES"),
    "chicken":   ("#0d0603", "#2a0c08", "#e74c3c", "CHICKEN"),
    "beef":      ("#080605", "#201008", "#a0522d", "BEEF"),
    "pork":      ("#0a0603", "#221006", "#c0654a", "PORK"),
    "prawn":     ("#0a0603", "#250c06", "#d44000", "PRAWNS"),
    "fish":      ("#030a0d", "#062535", "#1a8caa", "FISH"),
    "seafood":   ("#030a0d", "#062535", "#1a8caa", "SEAFOOD"),
    "vegetable": ("#040c06", "#0d2212", "#27ae60", "VEGETABLES"),
    "veg":       ("#040c06", "#0d2212", "#27ae60", "VEGETABLES"),
    "soup":      ("#030d0a", "#082520", "#1aaa8a", "SOUPS"),
    "set menu":  ("#08060d", "#1a1028", "#8e44ad", "SET MENU"),
    "deal":      ("#08060d", "#1a1028", "#8e44ad", "DEALS"),
    "side":      ("#0a0902", "#201d05", "#b8860b", "SIDES"),
}
DEFAULT_STYLE = ("#0d0603", "#231208", "#d4a017", "MENU")

# Image dimensions  (16:9 friendly)
W, H = 800, 500


def _style_for_category(cat_name: str):
    key = cat_name.lower()
    for keyword, style in CATEGORY_STYLES.items():
        if keyword in key:
            return style
    return DEFAULT_STYLE


def _hex(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _blend(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def _draw_diamond(draw, cx, cy, half, color, width=2):
    """Draw a rotated-square (diamond) outline."""
    pts = [(cx, cy - half), (cx + half, cy), (cx, cy + half), (cx - half, cy)]
    for i in range(4):
        draw.line([pts[i], pts[(i + 1) % 4]], fill=color, width=width)


def _corner_bracket(draw, x, y, size, color, flip_x=False, flip_y=False):
    """Draw an L-shaped corner bracket."""
    dx = -size if flip_x else size
    dy = -size if flip_y else size
    draw.line([(x, y), (x + dx, y)], fill=color, width=2)
    draw.line([(x, y), (x, y + dy)], fill=color, width=2)


def _load_fonts():
    font_paths = [
        # macOS
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        # Linux / Heroku
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    from PIL import ImageFont
    for path in font_paths:
        try:
            return {
                "hero":  ImageFont.truetype(path, 42),
                "sub":   ImageFont.truetype(path, 20),
                "brand": ImageFont.truetype(path, 14),
                "large": ImageFont.truetype(path, 72),
            }
        except OSError:
            continue
    # Absolute fallback
    f = ImageFont.load_default()
    return {"hero": f, "sub": f, "brand": f, "large": f}


def _make_image(item_name: str, category_name: str) -> bytes:
    from PIL import Image, ImageDraw

    bg_dark_hex, bg_light_hex, accent_hex, cat_label = _style_for_category(category_name)
    bg_dark  = _hex(bg_dark_hex)
    bg_light = _hex(bg_light_hex)
    accent   = _hex(accent_hex)
    gold     = (212, 160, 23)
    gold_lt  = (240, 192, 48)   # #f0c030  — bright readable gold
    white    = (245, 240, 232)

    img  = Image.new("RGB", (W, H), bg_dark)
    draw = ImageDraw.Draw(img)

    # ── 1. Diagonal gradient background ──────────────────────────────────────
    for y in range(H):
        t = y / H
        c = _blend(bg_dark, bg_light, t * 0.9)
        draw.line([(0, y), (W, y)], fill=c)

    # ── 2. Subtle diagonal grid (texture) ────────────────────────────────────
    grid_color = _blend(bg_light, accent, 0.06)
    step = 48
    for x in range(-H, W + H, step):
        draw.line([(x, 0), (x + H, H)], fill=grid_color, width=1)

    # ── 3. Background watermark — big faded category initial ─────────────────
    fonts = _load_fonts()
    wm_color = _blend(bg_light, accent, 0.10)
    draw.text((W // 2, H // 2 - 20), category_name[0].upper(),
              font=fonts["large"], fill=wm_color, anchor="mm")

    # ── 4. Centre decorative diamonds ────────────────────────────────────────
    cx, cy = W // 2, H // 2 - 10
    # Outer large diamond — accent, faint
    _draw_diamond(draw, cx, cy, 170, _blend(bg_light, accent, 0.22), width=1)
    # Middle diamond — accent
    _draw_diamond(draw, cx, cy, 120, _blend(accent, bg_light, 0.4), width=1)
    # Inner diamond — gold
    _draw_diamond(draw, cx, cy, 76, gold, width=2)
    # Innermost filled disc (accent)
    r = 44
    draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], fill=accent)
    # Letter inside disc
    draw.text((cx, cy), category_name[0].upper(),
              font=fonts["sub"], fill=white, anchor="mm")

    # ── 5. Full-width text panel at bottom ───────────────────────────────────
    panel_y = H - 165
    panel_color = _blend(bg_dark, (0, 0, 0), 0.55)
    # Fade panel in from transparent to solid
    for i, y in enumerate(range(panel_y - 20, panel_y)):
        t = i / 20
        c = _blend(bg_dark, panel_color, t * 0.7)
        draw.line([(0, y), (W, y)], fill=c)
    draw.rectangle([(0, panel_y), (W, H)], fill=panel_color)

    # ── 6. Accent top bar + gold bottom bar ──────────────────────────────────
    draw.rectangle([(0, 0), (W, 6)], fill=accent)
    draw.rectangle([(0, H - 5), (W, H)], fill=gold)

    # ── 7. Gold outer border (2px) ───────────────────────────────────────────
    border_color = _blend(bg_dark, gold, 0.35)
    draw.rectangle([(0, 0), (W - 1, H - 1)], outline=border_color, width=2)

    # ── 8. Corner brackets ───────────────────────────────────────────────────
    b_sz = 22
    b_pad = 12
    bracket_color = _blend(gold, bg_dark, 0.3)
    _corner_bracket(draw, b_pad,      b_pad,      b_sz, bracket_color)
    _corner_bracket(draw, W - b_pad,  b_pad,      b_sz, bracket_color, flip_x=True)
    _corner_bracket(draw, b_pad,      H - b_pad,  b_sz, bracket_color, flip_y=True)
    _corner_bracket(draw, W - b_pad,  H - b_pad,  b_sz, bracket_color, flip_x=True, flip_y=True)

    # ── 9. Category label (accent colour, letter-spaced feel) ────────────────
    draw.text((W // 2, panel_y + 18), cat_label,
              font=fonts["brand"], fill=accent, anchor="mm")

    # ── 10. Gold divider ─────────────────────────────────────────────────────
    div_y = panel_y + 34
    div_w = 200
    draw.rectangle([(W // 2 - div_w, div_y), (W // 2 + div_w, div_y + 1)],
                   fill=_blend(gold, bg_dark, 0.55))
    # Diamond pip at centre of divider
    pip = 4
    draw.polygon([(W // 2, div_y - pip),
                  (W // 2 + pip, div_y),
                  (W // 2, div_y + pip),
                  (W // 2 - pip, div_y)], fill=gold)

    # ── 11. Item name — BRIGHT GOLD, word-wrapped ──────────────────────────
    max_chars = 24
    lines = textwrap.wrap(item_name, width=max_chars)[:3]
    n = len(lines)
    line_h = 50
    panel_inner_h = H - panel_y - 40   # space below divider to brand line
    total_text_h = n * line_h
    y_start = panel_y + 52 + (panel_inner_h - total_text_h) // 2
    for line in lines:
        draw.text((W // 2, y_start), line,
                  font=fonts["hero"], fill=gold_lt, anchor="mm")
        y_start += line_h

    # ── 12. Branding at very bottom ──────────────────────────────────────────
    draw.text((W // 2, H - 16), "DESPAIR CHINESE · HACKNEY",
              font=fonts["brand"], fill=_blend(bg_dark, gold, 0.4), anchor="mm")

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92, optimize=True)
    buf.seek(0)
    return buf.read()

class Command(BaseCommand):
    help = "Generate styled placeholder images for menu items and upload to Cloudinary."

    def add_arguments(self, parser):
        parser.add_argument(
            "--all", action="store_true",
            help="Regenerate images for ALL items, even those that already have one.",
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Generate images locally but do not upload to Cloudinary.",
        )

    def handle(self, *args, **options):
        s = settings.CLOUDINARY_STORAGE
        cloudinary.config(
            cloud_name=s["CLOUD_NAME"],
            api_key=s["API_KEY"],
            api_secret=s["API_SECRET"],
        )

        if options["all"]:
            items = MenuItem.objects.select_related("category").all()
        else:
            items = MenuItem.objects.select_related("category").filter(image="")
            if not items.exists():
                items = MenuItem.objects.select_related("category").filter(image__isnull=True)

        count = items.count()
        if count == 0:
            self.stdout.write(self.style.WARNING(
                "No items need images. Use --all to regenerate existing ones."))
            return

        self.stdout.write(f"Generating images for {count} menu items…")

        ok = fail = 0
        for item in items:
            cat_name = item.category.name if item.category else "Menu"
            try:
                jpeg_bytes = _make_image(item.name, cat_name)
            except Exception as e:
                self.stderr.write(f"  ✗ Image gen failed for {item.name}: {e}")
                fail += 1
                continue

            if options["dry_run"]:
                self.stdout.write(f"  [dry-run] {item.name} — {len(jpeg_bytes)} bytes")
                ok += 1
                continue

            public_id = f"media/menu/placeholder_{item.pk}"
            try:
                result = cloudinary.uploader.upload(
                    jpeg_bytes,
                    public_id=public_id,
                    overwrite=True,
                    resource_type="image",
                    format="jpg",
                )
                # Store as media/menu/placeholder_PK.jpg in the image field
                new_path = f"menu/placeholder_{item.pk}.jpg"
                MenuItem.objects.filter(pk=item.pk).update(image=new_path)
                self.stdout.write(
                    self.style.SUCCESS(f"  ✓ {item.name} → {result['secure_url']}")
                )
                ok += 1
            except Exception as e:
                self.stderr.write(f"  ✗ Upload failed for {item.name}: {e}")
                fail += 1

        self.stdout.write(
            self.style.SUCCESS(f"\nDone: {ok} uploaded, {fail} failed.")
        )
