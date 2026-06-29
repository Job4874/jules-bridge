file_path = r"c:\Users\abdul\.jules\context\05_gotchas.md"
with open(file_path, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

# Let's try encoding as utf-16le, and then decoding as utf-8
try:
    bytes_recovered = text.encode("utf-16-le", errors="replace")
    text_recovered = bytes_recovered.decode("utf-8", errors="replace")
    
    # Write to a recovered file
    out_path = r"c:\Users\abdul\.jules\scratch\gotchas_recovered_utf16le.md"
    with open(out_path, "w", encoding="utf-8") as f_out:
        f_out.write(text_recovered)
    print(f"Successfully recovered to {out_path}!")
    
    # print first 200 chars safely
    safe_print = text_recovered[:200].encode('ascii', 'backslashreplace').decode('ascii')
    print("First 200 recovered chars:")
    print(safe_print)
except Exception as e:
    print("Failed UTF-16LE -> UTF-8:", e)
