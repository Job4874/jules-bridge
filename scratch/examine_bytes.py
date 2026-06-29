file_path = r"c:\Users\abdul\.jules\context\05_gotchas.md"
with open(file_path, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

print("Original text length (chars):", len(text))
print("First 20 chars of text:", [ord(c) for c in text[:20]])
print("First 20 chars of text as hex:", [hex(ord(c)) for c in text[:20]])

# Let's encode as UTF-16LE
bytes_le = text.encode("utf-16-le", errors="replace")
print("\nUTF-16LE bytes length:", len(bytes_le))
print("First 40 bytes UTF-16LE (hex):", bytes_le[:40].hex(' '))
print("First 40 bytes UTF-16LE (ascii):", repr(bytes_le[:40]))

# Let's encode as UTF-16BE
bytes_be = text.encode("utf-16-be", errors="replace")
print("\nUTF-16BE bytes length:", len(bytes_be))
print("First 40 bytes UTF-16BE (hex):", bytes_be[:40].hex(' '))
print("First 40 bytes UTF-16BE (ascii):", repr(bytes_be[:40]))
