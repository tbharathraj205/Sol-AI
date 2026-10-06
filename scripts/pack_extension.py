"""
Packaging script for SOL AI Chrome Extension.
Compresses the extension/ directory into a deployable sol-ai-extension.zip
stored inside frontend/public/ for direct download from the web application.
"""

import os
import sys
import zipfile
from pathlib import Path

def pack_extension():
    project_root = Path(__file__).resolve().parents[1]
    extension_dir = project_root / "extension"
    output_zip = project_root / "frontend" / "public" / "sol-ai-extension.zip"

    if not extension_dir.exists():
        print(f"Error: Extension directory not found at {extension_dir}")
        sys.exit(1)

    # Ensure frontend/public directory exists
    output_zip.parent.mkdir(parents=True, exist_ok=True)

    exclude_patterns = {
        ".gitkeep",
        ".DS_Store",
        "Thumbs.db",
        "__pycache__",
    }

    print(f"Packaging extension from: {extension_dir}")
    print(f"Output zip destination:   {output_zip}")

    total_files = 0
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(extension_dir):
            for file in files:
                if any(file.endswith(ex) or file == ex for ex in exclude_patterns):
                    continue

                file_path = Path(root) / file
                arcname = file_path.relative_to(extension_dir)

                zipf.write(file_path, arcname)
                total_files += 1
                print(f"  + Added: {arcname}")

    zip_size_kb = output_zip.stat().st_size / 1024
    print(f"\nSuccessfully packed {total_files} files into {output_zip.name} ({zip_size_kb:.1f} KB)")

if __name__ == "__main__":
    pack_extension()
