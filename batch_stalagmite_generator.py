"""
Batch 3D Stalagmite Generator (Sinh 20 mẫu măng đá đa dạng kích thước & kiểu dáng)

Uses StalagmiteGenerator class from stalagmite_generator.py to generate
20 unique 3D stalagmite models (.obj, .glb) and rendered preview images (.png).
Also creates a summary contact-sheet gallery image 'stalagmite_gallery_20.png'.
"""

import os
import time
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from stalagmite_generator import StalagmiteGenerator


def batch_generate(output_dir="output_20_stalagmites"):
    """Generate 20 distinct stalagmite models with varying sizes and styles."""
    os.makedirs(output_dir, exist_ok=True)

    print("=================================================================")
    print(" BATCH GENERATING 20 UNIQUE 3D STALAGMITE MODELS & RENDERS")
    print("=================================================================")

    # 20 configurations with different sizes, seeds, and styles
    configs = [
        {"id": 1,  "name": "Classic_Cluster",     "grid": (160, 160, 240), "seed": 42,  "style": "default"},
        {"id": 2,  "name": "Slender_Single",      "grid": (120, 120, 200), "seed": 101, "style": "single"},
        {"id": 3,  "name": "Twin_Towers",         "grid": (140, 140, 220), "seed": 102, "style": "twin"},
        {"id": 4,  "name": "Heavy_Pagoda",        "grid": (150, 150, 210), "seed": 103, "style": "pagoda"},
        {"id": 5,  "name": "Bulbous_Dwarf",       "grid": (160, 160, 140), "seed": 104, "style": "dwarf"},
        {"id": 6,  "name": "Tall_Needle",         "grid": (100, 100, 250), "seed": 105, "style": "needle"},
        {"id": 7,  "name": "Multi_Group",         "grid": (160, 160, 220), "seed": 106, "style": "cluster"},
        {"id": 8,  "name": "Medium_Ringed",       "grid": (110, 110, 180), "seed": 107, "style": "single"},
        {"id": 9,  "name": "High_Twin_Spire",     "grid": (150, 150, 240), "seed": 108, "style": "twin"},
        {"id": 10, "name": "Massive_Flowstone",   "grid": (170, 170, 230), "seed": 109, "style": "pagoda"},
        {"id": 11, "name": "Small_Knob",          "grid": (140, 140, 130), "seed": 110, "style": "dwarf"},
        {"id": 12, "name": "Ultra_Tall_Needle",   "grid": (110, 110, 260), "seed": 111, "style": "needle"},
        {"id": 13, "name": "Giant_Speleothem",    "grid": (180, 180, 240), "seed": 112, "style": "cluster"},
        {"id": 14, "name": "Organic_Formation_A", "grid": (130, 130, 190), "seed": 113, "style": "random"},
        {"id": 15, "name": "Organic_Formation_B", "grid": (140, 140, 200), "seed": 114, "style": "random"},
        {"id": 16, "name": "Organic_Formation_C", "grid": (150, 150, 210), "seed": 115, "style": "random"},
        {"id": 17, "name": "Curved_Column",       "grid": (130, 130, 230), "seed": 116, "style": "single"},
        {"id": 18, "name": "Fused_Twin_Spire",    "grid": (160, 160, 200), "seed": 117, "style": "twin"},
        {"id": 19, "name": "Mini_Pagoda",         "grid": (140, 140, 180), "seed": 118, "style": "pagoda"},
        {"id": 20, "name": "Cathedral_Speleothem","grid": (170, 170, 250), "seed": 119, "style": "cluster"},
    ]

    rendered_images = []
    total_t0 = time.time()

    for idx, cfg in enumerate(configs, 1):
        num_str = f"{idx:02d}"
        name = cfg["name"]
        grid = cfg["grid"]
        seed = cfg["seed"]
        style = cfg["style"]

        print(f"\n[{num_str}/20] Generating Stalagmite #{num_str} ({name}) - Size: {grid}, Seed: {seed}, Style: '{style}'...")
        t0 = time.time()

        # Instantiate generator
        generator = StalagmiteGenerator(grid_shape=grid, seed=seed, style=style)

        # 1. Density field
        density = generator.generate_density_field()

        # 2. Mesh extraction
        mesh = generator.extract_mesh(density)

        # 3. Export 3D models
        obj_file = os.path.join(output_dir, f"stalagmite_{num_str}_{name}.obj")
        glb_file = os.path.join(output_dir, f"stalagmite_{num_str}_{name}.glb")
        mesh.export(obj_file)
        mesh.export(glb_file)

        # 4. Render 2D image
        png_file = os.path.join(output_dir, f"stalagmite_{num_str}_{name}.png")
        generator.render_photorealistic(mesh, output_path=png_file)
        rendered_images.append(png_file)

        dt = time.time() - t0
        print(f"Sample #{num_str} complete in {dt:.2f}s | Vertices: {len(mesh.vertices):,}, Faces: {len(mesh.faces):,}")

    # Generate 4x5 Gallery Contact Sheet
    print("\nCreating 4x5 Summary Gallery image 'stalagmite_gallery_20.png'...")
    create_gallery(rendered_images, configs, "stalagmite_gallery_20.png")

    total_dt = time.time() - total_t0
    print("\n=================================================================")
    print(f" SUCCESS: 20 Stalagmite models generated in {total_dt:.2f}s!")
    print(f" Output Directory: {output_dir}")
    print(" Gallery Summary: stalagmite_gallery_20.png")
    print("=================================================================")


def create_gallery(img_paths, configs, output_gallery_path="stalagmite_gallery_20.png"):
    """Combine 20 rendered preview images into a 4-row x 5-column summary image."""
    cols, rows = 5, 4
    cell_w, cell_h = 320, 420
    header_h = 60

    canvas_w = cols * cell_w
    canvas_h = rows * cell_h + header_h

    gallery = Image.new("RGB", (canvas_w, canvas_h), (8, 6, 5))
    draw = ImageDraw.Draw(gallery)

    # Draw Title Header
    draw.rectangle([(0, 0), (canvas_w, header_h)], fill=(18, 14, 12))
    draw.text((20, 16), "Procedural 3D Stalagmite Collection (20 Variations)", fill=(240, 220, 190))

    for idx, (path, cfg) in enumerate(zip(img_paths, configs)):
        r = idx // cols
        c = idx % cols
        x = c * cell_w
        y = header_h + r * cell_h

        try:
            img = Image.open(path).convert("RGB")
            img.thumbnail((cell_w - 16, cell_h - 40), Image.Resampling.LANCZOS)
            
            # Center image in cell
            offset_x = x + (cell_w - img.width) // 2
            offset_y = y + (cell_h - 30 - img.height) // 2
            gallery.paste(img, (offset_x, offset_y))

            # Cell Border & Label
            draw.rectangle([(x + 2, y + 2), (x + cell_w - 2, y + cell_h - 2)], outline=(40, 32, 25), width=1)
            
            label = f"#{idx+1:02d} {cfg['name']}\nSize: {cfg['grid'][0]}x{cfg['grid'][1]}x{cfg['grid'][2]}"
            draw.text((x + 10, y + cell_h - 32), label, fill=(200, 180, 150))
        except Exception as e:
            print(f"Gallery tile warning for {path}: {e}")

    gallery.save(output_gallery_path, quality=95)
    print(f"Gallery contact sheet saved to '{output_gallery_path}'")


if __name__ == "__main__":
    batch_generate()
