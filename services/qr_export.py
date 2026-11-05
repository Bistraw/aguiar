"""Printable QR image for a card: the QR with the card name below it."""

import qrcode
from PIL import Image, ImageDraw, ImageFont

FONT_SIZE = 36
TEXT_AREA = 70


def _font():
    for name in ("arial.ttf", "segoeui.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, FONT_SIZE)
        except OSError:
            continue
    return ImageFont.load_default(size=FONT_SIZE)


def build_card_image(card):
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=12, border=4)
    qr.add_data(card.qr_payload())
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_img = (qr_img.get_image() if hasattr(qr_img, "get_image") else qr_img).convert("RGB")

    canvas = Image.new("RGB", (qr_img.width, qr_img.height + TEXT_AREA), "white")
    canvas.paste(qr_img, (0, 0))
    draw = ImageDraw.Draw(canvas)
    font = _font()
    left, top, right, bottom = draw.textbbox((0, 0), card.name, font=font)
    x = (canvas.width - (right - left)) // 2 - left
    y = qr_img.height + (TEXT_AREA - (bottom - top)) // 2 - top - 10
    draw.text((x, y), card.name, fill="black", font=font)
    return canvas


def export_card_qr_png(card, path):
    build_card_image(card).save(path, "PNG")
