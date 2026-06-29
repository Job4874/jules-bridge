file_path = r"c:\Users\abdul\.jules\context\05_gotchas.md"
with open(file_path, "r", encoding="utf-8", errors="replace") as f:
    text_head = f.read()

def reverse_step(text):
    out_bytes = bytearray()
    for char in text:
        val = ord(char)
        out_bytes.append(val & 0xFF)
        out_bytes.append(val >> 8)
    return out_bytes

try:
    print("Step 1 recovery...")
    bytes_1 = reverse_step(text_head)
    print("Bytes 1 length:", len(bytes_1))
    text_1 = bytes_1.decode("utf-8", errors="replace")
    print("Text 1 length:", len(text_1))
    
    # Save intermediate text
    with open("scratch/gotchas_intermediate.md", "w", encoding="utf-8") as f:
        f.write(text_1)
        
    print("Step 2 recovery...")
    bytes_2 = reverse_step(text_1)
    print("Bytes 2 length:", len(bytes_2))
    text_2 = bytes_2.decode("utf-8", errors="replace")
    print("Text 2 length:", len(text_2))
    
    # Save final recovered text
    with open("scratch/gotchas_recovered.md", "w", encoding="utf-8") as f:
        f.write(text_2)
    print("Successfully recovered to scratch/gotchas_recovered.md!")
    
    # Print the first 500 characters safely
    safe_print = text_2[:500].encode('ascii', 'backslashreplace').decode('ascii')
    print("\n--- Final Recovered Gotchas (first 500 chars) ---")
    print(safe_print)
    
except Exception as e:
    print("Recovery failed:", e)
