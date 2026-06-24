import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon, QPixmap
from PIL import Image

def main():
    # Create a temporary QApplication to initialize Qt's SVG rendering engine
    app = QApplication(sys.argv)
    
    root_dir = Path(__file__).resolve().parent.parent
    logo_svg = root_dir / "ui" / "resources" / "logo.svg"
    logo_ico = root_dir / "ui" / "resources" / "logo.ico"
    
    if not logo_svg.exists():
        print(f"Error: {logo_svg} not found")
        sys.exit(1)
        
    print(f"Loading {logo_svg}...")
    icon = QIcon(str(logo_svg))
    
    temp_png = logo_ico.parent / "logo_temp_256.png"
    
    try:
        # Render a single high-resolution 256x256 image
        pixmap = icon.pixmap(256, 256)
        pixmap.save(str(temp_png), "PNG")
        print(f"Rendered high-res PNG to {temp_png}")
        
        # Open with Pillow and save as multi-resolution ICO
        with Image.open(temp_png) as img:
            sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
            img.save(
                logo_ico,
                format="ICO",
                sizes=sizes
            )
        print(f"Successfully generated multi-resolution ICO at: {logo_ico}")
        
    finally:
        # Clean up temporary PNG file
        if temp_png.exists():
            try:
                temp_png.unlink()
                print("Cleaned up temporary PNG.")
            except Exception as e:
                print(f"Failed to delete temp file {temp_png}: {e}")

if __name__ == "__main__":
    main()
