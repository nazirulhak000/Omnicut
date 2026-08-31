import unicodedata

text = "ลดพิเศษวันนี้ อย่าเพิ่งซื้อ"
print("Raw text:", text)
for i, c in enumerate(text):
    print(f"  [{i}] {c} (U+{ord(c):04X}) {unicodedata.name(c, 'UNKNOWN')}")

# Test decomposed vs composed
nfc = unicodedata.normalize('NFC', text)
nfd = unicodedata.normalize('NFD', text)
nfkc = unicodedata.normalize('NFKC', text)
print("NFC:", [hex(ord(c)) for c in nfc])
print("NFD:", [hex(ord(c)) for c in nfd])

# Test Thai tone reordering / normalization
# In Thai Unicode, consonant + vowel + tone is standard (e.g. น + ี + ้).
# But some shapers expect consonant + tone + vowel or PUA (Private Use Area) glyphs like in WinThai/D-B fonts!
