"""
Batch 3D Stalactite & Speleothem Generator (Sinh 100 Mẫu Thạch Nhũ Hang Động Khác Nhau)

Features:
1. Generates 100 distinct 3D stalactite models (.glb & .obj) in 'stalactite_pack_100/' for Godot 4.
2. Varies size categories: Large Speleothems, Medium Stalactites, Small Drip Straws.
3. Varies styles: classic, soda_straw, drapery, pagoda, twin_cluster.
4. Creates a 10x10 contact sheet summary gallery ('stalactite_gallery_100.png').
"""

import os
import time
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import trimesh

from stalactite_generator import StalactiteGenerator


def generate_100_stalactites(output_dir="stalactite_pack_100", count=100, seed=2026):
    """Generate 100 distinct 3D ceiling stalactite models with varied sizes and styles."""
    os.makedirs(output_dir, exist_ok=True)
    print(f"=================================================================")
    print(f" Generating {count} Distinct 3D Stalactite & Speleothem Assets")
    print(f" Output Directory: '{output_dir}/'")
    print(f"=================================================================")

    generator = StalactiteGenerator(seed=seed)
    styles = [
        "classic",
        "soda_straw",
        "drapery",
        "pagoda",
        "twin_cluster",
    ]
    sizes = ["large", "medium", "small"]

    t0 = time.time()
    generated_meshes = []

    for i in range(1, count + 1):
        b_seed = seed + i * 53
        rng = np.random.RandomState(b_seed)

        style = styles[(i - 1) % len(styles)]
        size_type = sizes[(i - 1) % len(sizes)]

        # Height & Root Radius scaling based on size category
        if size_type == "large":
            height = float(rng.uniform(4.0, 6.2))
            radius_root = float(rng.uniform(0.70, 1.10))
        elif size_type == "medium":
            height = float(rng.uniform(2.4, 3.8))
            radius_root = float(rng.uniform(0.45, 0.70))
        else:  # small
            height = float(rng.uniform(1.2, 2.2))
            radius_root = float(rng.uniform(0.25, 0.45))

        # Resolution based on size
        res = (48, 48, 72) if size_type == "small" else (64, 64, 96)

        # Generate individual stalactite mesh
        mesh = generator.generate_single_stalactite(
            seed=b_seed,
            resolution=res,
            style=style,
            height=height,
            radius_root=radius_root,
            roughness=float(rng.uniform(0.04, 0.08)),
        )

        generated_meshes.append({
            "mesh": mesh,
            "id": i,
            "style": style,
            "size_type": size_type,
            "height": height,
        })

        num_str = f"{i:03d}"
        obj_path = os.path.join(output_dir, f"stalactite_{num_str}.obj")
        glb_path = os.path.join(output_dir, f"stalactite_{num_str}.glb")

        mesh.export(obj_path)
        mesh.export(glb_path)

        if i % 10 == 0 or i == count:
            print(f"  Processed {i}/{count} assets... (Latest: stalactite_{num_str}.glb [Style: {style}, {size_type.upper()}, {len(mesh.vertices):,} Verts])")

    total_time = time.time() - t0
    print(f"\nCompleted generating {count} 3D stalactite models in {total_time:.2f} seconds!")
    return generated_meshes, output_dir


def create_gallery_100(generated_meshes, output_image="stalactite_gallery_100.png"):
    """Create a 10x10 grid contact sheet displaying all 100 stalactite assets."""
    print(f"\nBuilding 10x10 Summary Contact Sheet Gallery ('{output_image}')...")
    t0 = time.time()

    fig, axes = plt.subplots(
        10, 10, figsize=(24, 24), subplot_kw={"projection": "3d"}, facecolor="#0a0807"
    )
    axes = axes.flatten()

    L_top = np.array([0.4, 0.4, 0.8], dtype=np.float32)
    L_top /= np.linalg.norm(L_top)

    c_calcite = np.array([0.88, 0.82, 0.72], dtype=np.float32)
    c_shadow = np.array([0.22, 0.18, 0.15], dtype=np.float32)

    for idx, item in enumerate(generated_meshes[:100]):
        ax = axes[idx]
        ax.set_facecolor("#0a0807")

        mesh = item["mesh"]
        verts = mesh.vertices
        faces = mesh.faces
        fnormals = mesh.face_normals

        diff = np.maximum(0.0, np.dot(fnormals, L_top))
        colors = c_shadow[None, :] + (c_calcite - c_shadow)[None, :] * (
            0.30 + 0.70 * diff[:, None]
        )
        colors = np.clip(colors, 0.0, 1.0)

        poly = Poly3DCollection(verts[faces], facecolors=colors, linewidths=0)
        ax.add_collection3d(poly)

        # Center and bound framing
        max_bound = np.max(np.abs(verts[:, :2])) * 1.2
        if max_bound < 0.2:
            max_bound = 0.5

        ax.set_xlim(-max_bound, max_bound)
        ax.set_ylim(-max_bound, max_bound)
        ax.set_zlim(np.min(verts[:, 2]), np.max(verts[:, 2]))
        ax.axis("off")
        ax.view_init(elev=14, azim=-45)

        # Title annotation with ID and Size tag
        size_code = item["size_type"][0].upper()  # L, M, S
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
    meshes, output_dir = generate_100_stalactites(output_dir="stalactite_pack_100", count=100, seed=2026)
    create_gallery_100(meshes, output_image="stalactite_gallery_100.png")

    print("\n=================================================================")
    print(" BATCH 100 STALACTITES GENERATION COMPLETE!")
    print(f" 3D Models Directory: {output_dir}/ (100 .glb & 100 .obj files)")
    print(f" Gallery Contact Sheet: stalactite_gallery_100.png")
    print("=================================================================")


if __name__ == "__main__":
    main()
