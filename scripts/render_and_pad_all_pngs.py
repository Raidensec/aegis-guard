import os
import subprocess
from pathlib import Path
from PIL import Image

def process_diagrams():
    project_root = Path(__file__).resolve().parent.parent
    mermaid_dir = project_root / "docs" / "mermaid"
    png_dir = project_root / "docs" / "mermaid_pngs"
    png_dir.mkdir(parents=True, exist_ok=True)
    
    # List all mermaid files
    mermaid_files = sorted(list(mermaid_dir.glob("*.mermaid")))
    print(f"Found {len(mermaid_files)} mermaid files.")
    
    for mf in mermaid_files:
        name = mf.stem
        temp_png = png_dir / f"{name}_temp.png"
        final_png = png_dir / f"{name}.png"
        
        print(f"Rendering {name}...")
        # Run mmdc with transparent background
        cmd = [
            "npx", "-y", "@mermaid-js/mermaid-cli",
            "-i", str(mf),
            "-o", str(temp_png),
            "-b", "transparent"
        ]
        
        try:
            res = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        except subprocess.CalledProcessError as e:
            print(f"Error rendering {name}: {e.stderr.decode()}")
            continue
            
        if not temp_png.exists():
            print(f"Temporary PNG not found for {name}")
            continue
            
        # Open the image and pad it to golden ratio
        img = Image.open(temp_png)
        w, h = img.size
        
        # Determine whether it should be landscape (1.618) or portrait (1/1.618 = 0.618)
        if w >= h:
            target_ratio = 1.618
            if w / h > target_ratio:
                # Too wide: need to increase height
                h_new = int(round(w / target_ratio))
                w_new = w
            else:
                # Too tall: need to increase width
                w_new = int(round(h * target_ratio))
                h_new = h
        else:
            target_ratio = 1 / 1.618 # 0.618
            if w / h < target_ratio:
                # Too tall: need to increase width
                w_new = int(round(h * target_ratio))
                h_new = h
            else:
                # Too wide: need to increase height
                h_new = int(round(w / target_ratio))
                w_new = w
                
        # Create a new transparent image with the new size
        new_img = Image.new("RGBA", (w_new, h_new), (0, 0, 0, 0))
        
        # Paste the original image centered
        offset_x = (w_new - w) // 2
        offset_y = (h_new - h) // 2
        new_img.paste(img, (offset_x, offset_y))
        
        # Save as final PNG
        new_img.save(final_png, "PNG")
        
        # Clean up temp file
        try:
            os.remove(temp_png)
        except OSError:
            pass
            
        # Verify final aspect ratio
        actual_ratio = w_new / h_new
        print(f"  Processed {name}: {w}x{h} -> {w_new}x{h_new} (Ratio: {actual_ratio:.4f})")

if __name__ == "__main__":
    process_diagrams()
