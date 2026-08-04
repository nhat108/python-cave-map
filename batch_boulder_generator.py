"""
Batch 3D Boulder Generator (Sinh 100 Mẫu Đá Tảng & Đá Vụn Khác Nhau)

Features:
1. Generates 100 distinct 3D rock models (.glb & .obj) in 'boulder_pack_100/' for Godot 4.
2. Varies size categories: Large Boulders, Medium Rocks, Small Debris.
3. Varies rock styles: faceted_block, fractured_prism, jagged_wedge, crystal_polyhedron, chipped_boulder.
4. Creates a 10x10 contact sheet summary gallery ('boulder_gallery_100.png').
"""

import os
import time
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import trimesh

from boulder_generator import BoulderGenerator


def generate_100_boulders(output_dir="boulder_pack_100", count=100, seed=2026):
    """Generate 100 distinct 3D rock models with varied sizes and shapes."""
    os.makedirs(output_dir, exist_ok=True)
    print(f"=================================================================")
    print(f" Generating {count} Distinct 3D Boulder & Debris Assets")
    print(f" Output Directory: '{output_dir}/'")
    print(f"=================================================================")

    generator = BoulderGenerator(seed=seed)
    styles = [
        "faceted_block",
        "fractured_prism",
        "jagged_wedge",
        "crystal_polyhedron",
        "chipped_boulder",
    ]
    sizes = ["large", "medium", "small"]

    t0 = time.time()
    generated_meshes = []

    for i in range(1, count + 1):
        b_seed = seed + i * 47
        rng = np.random.RandomState(b_seed)

        style = styles[(i - 1) % len(styles)]
        size_type = sizes[(i - 1) % len(sizes)]

        # Base scale aspect ratio
        aspect = (
            rng.uniform(1.0, 1.45),
            rng.uniform(0.85, 1.35),
            rng.uniform(0.75, 1.25),
        )

        # Scale multiplier based on size category
        if size_type == "large":
            scale_mult = float(rng.uniform(2.5, 4.2))
        elif size_type == "medium":
            scale_mult = float(rng.uniform(1.0, 2.2))
        else:  # small
            scale_mult = float(rng.uniform(0.35, 0.85))

        # Generate individual 3D mesh at unit scale
        mesh = generator.generate_single_boulder(
            seed=b_seed,
            resolution=48 if size_type == "small" else 64,
            style=style,
            scale=aspect,
            roughness=float(rng.uniform(0.03, 0.06)),
        )

        # Apply size scale multiplier
        mesh.apply_scale(scale_mult)

        generated_meshes.append({
            "mesh": mesh,
            "id": i,
            "style": style,
            "size_type": size_type,
            "scale_mult": scale_mult,
        })

        num_str = f"{i:03d}"
        obj_path = os.path.join(output_dir, f"boulder_{num_str}.obj")
        glb_path = os.path.join(output_dir, f"boulder_{num_str}.glb")

        mesh.export(obj_path)
        mesh.export(glb_path)

        if i % 10 == 0 or i == count:
            print(f"  Processed {i}/{count} assets... (Latest: boulder_{num_str}.glb [{size_type.upper()}, {len(mesh.vertices):,} Verts])")

    total_time = time.time() - t0
    print(f"\nCompleted generating {count} 3D models in {total_time:.2f} seconds!")
    return generated_meshes, output_dir


def create_gallery_100(generated_meshes, output_image="boulder_gallery_100.png"):
    """Create a 10x10 grid contact sheet displaying all 100 boulder assets."""
    print(f"\nBuilding 10x10 Summary Contact Sheet Gallery ('{output_image}')...")
    t0 = time.time()

    fig, axes = plt.subplots(
        10, 10, figsize=(24, 24), subplot_kw={"projection": "3d"}, facecolor="#0a0807"
    )
    axes = axes.flatten()

    L = np.array([0.5, -0.6, 0.7], dtype=np.float32)
    L /= np.linalg.norm(L)

    c_base = np.array([0.76, 0.62, 0.48], dtype=np.float32)
    c_dark = np.array([0.16, 0.12, 0.09], dtype=np.float32)

    for idx, item in enumerate(generated_meshes[:100]):
        ax = axes[idx]
        ax.set_facecolor("#0a0807")

        mesh = item["mesh"]
        verts = mesh.vertices
        faces = mesh.faces
        fnormals = mesh.face_normals

        diff = np.maximum(0.0, np.dot(fnormals, L))
        colors = c_dark[None, :] + (c_base - c_dark)[None, :] * (
            0.25 + 0.75 * diff[:, None]
        )
        colors = np.clip(colors, 0.0, 1.0)

        poly = Poly3DCollection(verts[faces], facecolors=colors, linewidths=0)
        ax.add_collection3d(poly)

        max_bound = np.max(np.abs(verts)) * 1.12
        ax.set_xlim(-max_bound, max_bound)
        ax.set_ylim(-max_bound, max_bound)
        ax.set_zlim(-max_bound, max_bound)
        ax.axis("off")
        ax.view_init(elev=22, azim=-45)

        # Title annotation with ID and Size tag
        size_code = item["size_type"][0].upper() # L, M, S
        ax.set_title(
            f"#{item['id']:03d} [{size_code}]",
            color="#f0e0d0",
            fontsize=7,
            pad=-5,
        )

    plt.tight_layout()
    plt.savefig(
        output_image,
        dpi=180,
        facecolor="#0a0807",
        bbox_inches="tight",
        pad_inches=0.1,
    )
    plt.close(fig)

    dt = time.time() - t0
    print(f"Gallery '{output_image}' created in {dt:.2f} seconds!")


def main():
    meshes, output_dir = generate_100_boulders(output_dir="boulder_pack_100", count=100, seed=2026)
    create_gallery_100(meshes, output_image="boulder_gallery_100.png")

    print("\n=================================================================")
    print(" BATCH 100 BOULDERS GENERATION COMPLETE!")
    print(f" 3D Models Directory: {output_dir}/ (100 .glb & 100 .obj files)")
    print(f" Gallery Contact Sheet: boulder_gallery_100.png")
    print("=================================================================")


if __name__ == "__main__":
    main()
