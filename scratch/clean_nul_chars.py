file_path = r"c:\Users\abdul\.jules\context\05_gotchas.md"
with open(file_path, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

# Remove NUL characters
cleaned = text.replace("\x00", "")

# Ensure exactly one trailing newline
cleaned = cleaned.rstrip() + "\n"

print("Original length (chars):", len(text))
print("Cleaned length (chars):", len(cleaned))

# Print last 300 characters safely
safe_print = cleaned[-300:].encode('ascii', 'backslashreplace').decode('ascii')
print("\n--- Last 300 chars of cleaned text ---")
print(safe_print)

# Write back
with open(file_path, "w", encoding="utf-8") as f:
    f.write(cleaned)
print("\nSuccessfully cleaned and saved!")
