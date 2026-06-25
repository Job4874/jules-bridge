import os
import sys

def read_markdown_asset(target_path):
    print(f"[*] Extracting system text metrics from path: {target_path}")
    if not os.path.exists(target_path):
        print(f"[-] Operational failure: Target item missing at location {target_path}")
        return False
        
    try:
        # utf-8-sig automatically intercepts and strips leading BOM allocations cleanly
        with open(target_path, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()
        print("\n=== START ASSET READ ===")
        print(content)
        print("=== END ASSET READ ===\n")
        return True
    except Exception as e:
        print(f"[-] Unhandled exception during file ingestion loop: {str(e)}")
        return False

if __name__ == '__main__':
    # Default to README lookup pattern if parameters are empty
    file_target = sys.argv[1] if len(sys.argv) > 1 else "README.md"
    read_markdown_asset(file_target)