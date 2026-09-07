# NOTE: this file has no `def test_*` functions -- it is a manual diagnostic
# script (see .agents/rules/testing_standard.md rule 4: side effects at
# import time are not allowed in tests/test_*.py). Output files are only
# written when main() actually runs under `if __name__ == "__main__":`,
# never on plain pytest collection/import.

from PIL import Image, ImageDraw, ImageFont


def main():
    img = Image.new("RGBA", (1000, 600), (20, 25, 40, 255))
    draw = ImageDraw.Draw(img)

    fonts = [
        ("Mitr-Bold.ttf", "Mitr: ลดพิเศษวันนี้ อย่าเพิ่งซื้อ"),
        ("Prompt-Black.ttf", "Prompt: ลดพิเศษวันนี้ อย่าเพิ่งซื้อ"),
        ("IBMPlexSansThai-Bold.ttf", "IBM: ลดพิเศษวันนี้ อย่าเพิ่งซื้อ"),
        ("Kanit-Black.ttf", "Kanit: ลดพิเศษวันนี้ อย่าเพิ่งซื้อ")
    ]

    for idx, (f_name, text) in enumerate(fonts):
        font = ImageFont.truetype(f"02_Assets/Fonts/{f_name}", 44)
        draw.text((50, 50 + idx * 120), text, font=font, fill=(255, 230, 0))

    img.save("test_pillow_thai.png")
    print("Saved test_pillow_thai.png")


if __name__ == "__main__":
    main()
