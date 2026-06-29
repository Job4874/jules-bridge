import sys

file_path = r"c:\Users\abdul\.jules\context\05_gotchas.md"
with open(file_path, "rb") as f:
    data = f.read()

print(f"File size in bytes: {len(data)}")
print(f"First 20 bytes (hex): {data[:20].hex(' ')}")

encodings = ["utf-8", "utf-16", "utf-16-le", "utf-16-be", "gbk", "gb18030", "utf-8-sig", "latin-1"]
for enc in encodings:
    try:
        decoded = data.decode(enc)
        print(f"\n--- Decoded as {enc} (first 200 chars repr) ---")
        escaped = decoded[:200].encode('ascii', 'backslashreplace').decode('ascii')
        print(escaped)
    except Exception as e:
        print(f"\nFailed to decode as {enc}: {e}")
