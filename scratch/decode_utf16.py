file_path = r"c:\Users\abdul\.jules\context\05_gotchas.md"
with open(file_path, "rb") as f:
    data = f.read()

try:
    decoded = data.decode("utf-16-le", errors="replace")
    print("Decoded length in chars:", len(decoded))
    
    output_path = r"c:\Users\abdul\.jules\scratch\gotchas_decoded.md"
    with open(output_path, "w", encoding="utf-8") as f_out:
        f_out.write(decoded)
    print(f"Wrote decoded content to {output_path}")
    
    # print safely
    escaped = decoded[:500].encode('ascii', 'backslashreplace').decode('ascii')
    print("First 500 chars (safe):")
    print(escaped)
except Exception as e:
    print("Failed:", e)
