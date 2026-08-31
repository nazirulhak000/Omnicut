from PIL import Image, ImageDraw, ImageFont

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
