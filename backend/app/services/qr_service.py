import os
import qrcode
from qrcode.image.styledpil import StyledPilImage
from PIL import Image, ImageDraw, ImageFont


UPLOAD_DIR = "uploads/qrcodes"


def generate_qr_code(retailer_code: str, referral_link: str) -> str:
    """
    Generate a QR code PNG for the given referral link.
    Saves to uploads/qrcodes/<retailer_code>.png
    Returns the relative file path.
    """
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(referral_link)
    qr.make(fit=True)

    # Dark fill on white — clean, scannable
    img = qr.make_image(fill_color="#111008", back_color="white")

    # Add a small label below the QR
    img = _add_label(img, retailer_code)

    file_path = os.path.join(UPLOAD_DIR, f"{retailer_code}.png")
    img.save(file_path)

    return file_path


def _add_label(qr_img: Image.Image, retailer_code: str) -> Image.Image:
    """Add a text label beneath the QR code image."""
    qr_w, qr_h = qr_img.size
    label_height = 40
    canvas = Image.new("RGB", (qr_w, qr_h + label_height), "white")
    canvas.paste(qr_img, (0, 0))

    draw = ImageDraw.Draw(canvas)
    # Use default font — no external font file needed
    text = f"11:11:11  |  {retailer_code}"
    # Estimate text position (centered)
    try:
        font = ImageFont.truetype("arial.ttf", 14)
    except IOError:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    x = (qr_w - text_w) // 2
    y = qr_h + 10
    draw.text((x, y), text, fill="#111008", font=font)

    return canvas
