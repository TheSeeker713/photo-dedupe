# Photo Deduplication Tool Icon Generator
# Creates a simple icon for the Windows build

from PIL import Image, ImageDraw, ImageFont
import sys
from pathlib import Path

def create_app_icon():
    """Create a simple app icon for PhotoDedupe."""
    
    # Create a 256x256 icon with camera and duplicate symbols
    size = 256
    img = Image.new('RGBA', (size, size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    
    # Background circle
    margin = 20
    draw.ellipse([margin, margin, size-margin, size-margin], 
                fill=(52, 152, 219, 255), outline=(41, 128, 185, 255), width=4)
    
    # Camera body (main rectangle)
    cam_left = size // 4
    cam_top = size // 2.5
    cam_right = size * 3 // 4
    cam_bottom = size * 2 // 3
    
    draw.rectangle([cam_left, cam_top, cam_right, cam_bottom], 
                  fill=(255, 255, 255, 255), outline=(52, 73, 94, 255), width=3)
    
    # Camera lens (circle)
    lens_center_x = size // 2
    lens_center_y = int(size // 1.8)
    lens_radius = size // 8
    
    draw.ellipse([lens_center_x - lens_radius, lens_center_y - lens_radius,
                 lens_center_x + lens_radius, lens_center_y + lens_radius],
                fill=(52, 73, 94, 255), outline=(44, 62, 80, 255), width=2)
    
    # Inner lens
    inner_radius = lens_radius // 2
    draw.ellipse([lens_center_x - inner_radius, lens_center_y - inner_radius,
                 lens_center_x + inner_radius, lens_center_y + inner_radius],
                fill=(255, 255, 255, 255))
    
    # Viewfinder
    vf_width = size // 8
    vf_height = size // 12
    vf_x = lens_center_x - vf_width // 2
    vf_y = cam_top - vf_height
    
    draw.rectangle([vf_x, vf_y, vf_x + vf_width, vf_y + vf_height],
                  fill=(255, 255, 255, 255), outline=(52, 73, 94, 255), width=2)
    
    # Flash
    flash_size = size // 16
    flash_x = cam_right - flash_size - 10
    flash_y = cam_top + 10
    
    draw.ellipse([flash_x, flash_y, flash_x + flash_size, flash_y + flash_size],
                fill=(255, 235, 59, 255), outline=(243, 156, 18, 255), width=2)
    
    # Duplicate indicator (two overlapping squares in corner)
    dup_size = size // 6
    dup_x = size - dup_size - 15
    dup_y = 15
    offset = 8
    
    # Back square
    draw.rectangle([dup_x + offset, dup_y + offset, 
                   dup_x + dup_size + offset, dup_y + dup_size + offset],
                  fill=(231, 76, 60, 200), outline=(192, 57, 43, 255), width=2)
    
    # Front square
    draw.rectangle([dup_x, dup_y, dup_x + dup_size, dup_y + dup_size],
                  fill=(241, 196, 15, 200), outline=(243, 156, 18, 255), width=2)
    
    return img

def save_icon_formats(img, base_path):
    """Save icon in multiple formats and sizes."""
    # Save as ICO with multiple sizes
    ico_sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    ico_images = []
    
    for size in ico_sizes:
        resized = img.resize(size, Image.Resampling.LANCZOS)
        ico_images.append(resized)
    
    ico_path = base_path / 'app_icon.ico'
    ico_images[0].save(ico_path, format='ICO', sizes=[(img.width, img.height) for img in ico_images])
    
    # Save as PNG for reference
    png_path = base_path / 'app_icon.png'
    img.save(png_path, format='PNG')
    
    print(f"Created app icon: {ico_path}")
    print(f"Created PNG reference: {png_path}")

if __name__ == "__main__":
    assets_dir = Path(__file__).parent
    
    try:
        icon_img = create_app_icon()
        save_icon_formats(icon_img, assets_dir)
        print("✅ App icon created successfully!")
        
    except Exception as e:
        print(f"❌ Error creating app icon: {e}")
        # Create a simple fallback icon
        simple_img = Image.new('RGBA', (256, 256), (52, 152, 219, 255))
        draw = ImageDraw.Draw(simple_img)
        draw.text((128, 128), "📷", anchor="mm", font_size=100)
        simple_img.save(assets_dir / 'app_icon.ico', format='ICO')
        print("Created simple fallback icon")