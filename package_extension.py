import os
import zipfile

src_dir = r"C:\Users\om\.gemini\antigravity\scratch\algorise-ai\guardian_angel_extension"
dist_dir = r"C:\Users\om\.gemini\antigravity\scratch\algorise-ai\dist"
os.makedirs(dist_dir, exist_ok=True)

zip_path = os.path.join(dist_dir, "guardian_angel_extension_v3.0.0.zip")

with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
    for root, dirs, files in os.walk(src_dir):
        for f in files:
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, src_dir)
            z.write(full_path, arcname=rel_path)
            print(f"Added to ZIP: {rel_path}")

print(f"\nBundle created successfully at: {zip_path}")
print(f"Size: {os.path.getsize(zip_path)} bytes")
