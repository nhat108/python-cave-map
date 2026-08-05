"""Procedural 100-Tree Species Generator for 1km Terrain.

Generates 100 unique, distinct 3D tree species/variants across 6 major botanical families:
1. Giant Redwoods (Gõ Đỏ Cổ Thụ) - 15 variants
2. Ancient Banyans & Oaks (Cổ Thụ Tán Rộng) - 20 variants
3. Coniferous Pine Forests (Thông Đại Ngàn) - 20 variants
4. Medium Hardwood Broadleaf (Cây Gỗ Tán Màng) - 25 variants
5. Flowering & Fruit Trees (Cây Hoa / Cây Rừng) - 10 variants
6. Understory Saplings & Shrubs (Cây Con / Cây Bụi) - 10 variants
"""

from __future__ import annotations

import argparse
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
import trimesh


from PIL import Image


def generate_tree_color_palette(output_path: Path = Path("cave-diving-game/assets/tree_color_palette.png")) -> dict[tuple[int, int, int], tuple[float, float]]:
    """Generate a 256x256 PNG color palette atlas and return UV coordinate mapping for each RGB color swatch."""
    palette_colors = [
        # Barks
        (165, 72, 32),   # Redwood Bark
        (82, 50, 26),    # Oak Bark
        (72, 44, 22),    # Pine Bark
        (95, 62, 35),    # Sapling Bark
        # Foliage Greens
        (25, 115, 35),   # Deep Emerald
        (40, 150, 48),   # Vibrant Green
        (20, 95, 30),    # Pine Evergreen
        (55, 175, 62),   # Light Spring Green
        # Autumn / Blossom
        (220, 150, 30),  # Golden Amber
        (210, 80, 45),   # Crimson Coral
        (160, 200, 35),  # Bright Lime
    ]

    size = 256
    n_colors = len(palette_colors)
    block_w = size // n_colors

    img_arr = np.zeros((size, size, 3), dtype=np.uint8)
    uv_map = {}

    for idx, (r, g, b) in enumerate(palette_colors):
        x_start = idx * block_w
        x_end = (idx + 1) * block_w if idx < n_colors - 1 else size
        img_arr[:, x_start:x_end] = [r, g, b]

        # Calculate UV center for this color swatch
        u_center = (x_start + x_end) / (2.0 * size)
        v_center = 0.5
        uv_map[(r, g, b)] = (u_center, v_center)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(img_arr, mode="RGB").save(output_path)
    print(f"Generated 256x256 Tree Color Palette Atlas at '{output_path.resolve()}'!")
    return uv_map


def build_tree_variant(variant_id: int, uv_map: dict | None = None) -> trimesh.Trimesh:
    """Build a unique 3D tree or giant bush mesh for variant (0..99) with tall heights and dense foliage."""
    rng = np.random.default_rng(20260804 + variant_id * 1009)

    # 1. Family Classification & Increased Heights
    if variant_id < 15:
        # Giant Redwoods (Gõ Đỏ Cổ Thụ Khổng Lồ) - INCREASED HEIGHT: 35m to 48m!
        height = rng.uniform(35.0, 48.0)
        r_base, r_top = rng.uniform(3.2, 4.8), rng.uniform(0.8, 1.3)
        bark_rgb = (165, 72, 32)
        leaf_rgb = (25, 115, 35)
        tree_type = "redwood"
    elif variant_id < 35:
        # Ancient Oak / Banyan - INCREASED HEIGHT: 22m to 32m!
        height = rng.uniform(22.0, 32.0)
        r_base, r_top = rng.uniform(2.2, 3.5), rng.uniform(0.5, 0.9)
        bark_rgb = (82, 50, 26)
        leaf_rgb = (40, 150, 48)
        tree_type = "ancient_oak"
    elif variant_id < 55:
        # Coniferous Pines - INCREASED HEIGHT: 18m to 30m!
        height = rng.uniform(18.0, 30.0)
        r_base, r_top = rng.uniform(0.45, 0.85), rng.uniform(0.10, 0.20)
        bark_rgb = (72, 44, 22)
        leaf_rgb = (20, 95, 30)
        tree_type = "pine"
    elif variant_id < 75:
        # Medium Broadleaf - INCREASED HEIGHT: 10m to 18m!
        height = rng.uniform(10.0, 18.0)
        r_base, r_top = rng.uniform(0.45, 0.85), rng.uniform(0.15, 0.28)
        bark_rgb = (82, 50, 26)
        leaf_rgb = (55, 175, 62)
        tree_type = "broadleaf"
    elif variant_id < 85:
        # Autumn / Blossom Trees - Height: 7m to 14m
        height = rng.uniform(7.0, 14.0)
        r_base, r_top = rng.uniform(0.35, 0.60), rng.uniform(0.12, 0.22)
        bark_rgb = (95, 62, 35)
        leaf_rgb = rng.choice([(220, 150, 30), (210, 80, 45), (160, 200, 35)])
        tree_type = "flowering"
    else:
        # DENSE JUNGLE BUSHES & GIANT SHRUBS (Bụi Cây Rừng Khổng Lồ)
        height = rng.uniform(1.8, 4.2)
        r_base, r_top = rng.uniform(0.12, 0.25), rng.uniform(0.05, 0.10)
        bark_rgb = (80, 55, 30)
        leaf_rgb = rng.choice([(30, 135, 40), (45, 165, 52), (20, 105, 32)])
        tree_type = "bush"

    # SPECIAL GENERATION FOR GIANT JUNGLE BUSHES
    if tree_type == "bush":
        foliage_parts = []
        n_spheres = rng.integers(5, 12)
        for _ in range(n_spheres):
            b_rad = rng.uniform(1.2, 2.8)
            bx = rng.uniform(-1.8, 1.8)
            bz = rng.uniform(-1.8, 1.8)
            by = rng.uniform(0.8, height)

            ico = trimesh.creation.icosphere(subdivisions=1, radius=b_rad)
            noise = rng.uniform(-0.15 * b_rad, 0.15 * b_rad, ico.vertices.shape)
            ico.vertices += noise
            ico.vertices += np.array([bx, by, bz])

            b_color = np.array([*leaf_rgb, 255], dtype=np.uint8)
            ico.visual.vertex_colors = np.tile(b_color, (len(ico.vertices), 1))
            foliage_parts.append(ico)

        bush_mesh = trimesh.util.concatenate(foliage_parts)
        bush_mesh.unmerge_vertices()
        min_y = float(np.min(bush_mesh.vertices[:, 1]))
        bush_mesh.vertices[:, 1] -= min_y
        return bush_mesh

    # 2. TRUNK GEOMETRY & CONNECTOR BRANCHES
    trunk_max_y = height * 0.88 if tree_type == "pine" else height * 0.72
    n_rings = max(10, int(height * 0.9))
    n_seg = 12 if tree_type in ["redwood", "ancient_oak"] else 8
    y_points = np.linspace(0.0, trunk_max_y, n_rings)

    trunk_verts = []
    for i, y in enumerate(y_points):
        t = y / trunk_max_y
        r = r_base * (1.0 - t)**1.4 + r_top * t

        angles = np.linspace(0, 2 * np.pi, n_seg, endpoint=False)
        flare = (1.0 + 0.45 * (1.5 - y) * (np.sin(5 * angles)**2)) if (y < 1.5 and tree_type in ["redwood", "ancient_oak"]) else 1.0
        r_dist = r * flare + rng.uniform(-0.015, 0.015, n_seg)

        vx = r_dist * np.cos(angles)
        vz = r_dist * np.sin(angles)
        vy = np.full(n_seg, y)
        trunk_verts.append(np.column_stack([vx, vy, vz]))

    trunk_verts = np.vstack(trunk_verts)
    trunk_faces = []
    for ring in range(n_rings - 1):
        for s in range(n_seg):
            ns = (s + 1) % n_seg
            v0 = ring * n_seg + s
            v1 = ring * n_seg + ns
            v2 = (ring + 1) * n_seg + s
            v3 = (ring + 1) * n_seg + ns
            trunk_faces.append([v0, v1, v2])
            trunk_faces.append([v1, v3, v2])

    trunk_faces = np.array(trunk_faces, dtype=np.int64)
    trunk_colors = np.tile(np.array([*bark_rgb, 255], dtype=np.uint8), (len(trunk_verts), 1))
    trunk_mesh = trimesh.Trimesh(vertices=trunk_verts, faces=trunk_faces, vertex_colors=trunk_colors, process=False)

    wood_parts = [trunk_mesh]
    foliage_parts = []

    if tree_type == "pine":
        n_tiers = rng.integers(4, 7)
        y_start = height * 0.25
        tier_y_positions = np.linspace(y_start, height * 0.95, n_tiers)

        for t_idx, y_pos in enumerate(tier_y_positions):
            t_ratio = 1.0 - (t_idx / n_tiers)
            c_rad = max(0.7, height * 0.24 * t_ratio)
            c_h = height * 0.32 * t_ratio
            cone = trimesh.creation.cone(radius=c_rad, height=c_h, sections=8)
            cone.vertices[:, 1] += (y_pos - c_h * 0.35)

            c_color = np.array([*leaf_rgb, 255], dtype=np.uint8)
            cone.visual.vertex_colors = np.tile(c_color, (len(cone.vertices), 1))
            foliage_parts.append(cone)
    else:
        n_clusters = rng.integers(4, 10) if tree_type in ["redwood", "ancient_oak"] else rng.integers(3, 6)
        canopy_base_y = height * 0.35

        for c_i in range(n_clusters):
            if c_i == 0:
                offset_x, offset_z = 0.0, 0.0
                offset_y = height * 0.65
                c_radius = rng.uniform(height * 0.22, height * 0.35)
            else:
                offset_x = rng.uniform(-height * 0.25, height * 0.25)
                offset_z = rng.uniform(-height * 0.25, height * 0.25)
                offset_y = canopy_base_y + rng.uniform(0.0, height * 0.45)
                c_radius = rng.uniform(height * 0.16, height * 0.30)

            dist_to_trunk = np.sqrt(offset_x**2 + offset_z**2)
            if dist_to_trunk > 0.3:
                b_dir = np.array([offset_x, 0.0, offset_z])
                b_dir /= dist_to_trunk
                b_rad = max(0.08, r_top * 0.75)
                branch = trimesh.creation.cylinder(radius=b_rad, height=dist_to_trunk, sections=6)

                up = np.array([0, 1, 0])
                axis = np.cross(up, b_dir)
                axis_len = np.linalg.norm(axis)
                if axis_len > 1e-5:
                    axis /= axis_len
                    angle = np.arccos(np.dot(up, b_dir))
                    mat = trimesh.transformations.rotation_matrix(angle, axis)
                    branch.apply_transform(mat)

                branch.vertices += np.array([offset_x * 0.5, offset_y, offset_z * 0.5])
                branch.visual.vertex_colors = np.tile(np.array([*bark_rgb, 255], dtype=np.uint8), (len(branch.vertices), 1))
                wood_parts.append(branch)

            ico = trimesh.creation.icosphere(subdivisions=1, radius=c_radius)
            noise = rng.uniform(-0.18 * c_radius, 0.18 * c_radius, ico.vertices.shape)
            ico.vertices += noise
            ico.vertices += np.array([offset_x, offset_y, offset_z])

            c_color = np.array([*leaf_rgb, 255], dtype=np.uint8)
            ico.visual.vertex_colors = np.tile(c_color, (len(ico.vertices), 1))
            foliage_parts.append(ico)

    tree_mesh = trimesh.util.concatenate(wood_parts + foliage_parts)
    tree_mesh.unmerge_vertices()

    # CHECKLIST ITEM 1: ENFORCE STRICT PIVOT POINT (0, 0, 0) AT BASE OF TRUNK
    min_y = float(np.min(tree_mesh.vertices[:, 1]))
    tree_mesh.vertices[:, 1] -= min_y  # Base Y sits exactly at 0.0
    tree_mesh.vertices[:, 0] -= np.mean(trunk_verts[:n_seg, 0])  # Center X at 0.0
    tree_mesh.vertices[:, 2] -= np.mean(trunk_verts[:n_seg, 2])  # Center Z at 0.0

    return tree_mesh


def generate_all_100_tree_species() -> list[trimesh.Trimesh]:
    """Generate all 100 unique procedural tree species mapped to Texture Palette Atlas."""
    generate_tree_color_palette()
    tree_catalog = []
    for vid in range(100):
        tree = build_tree_variant(vid)
        tree_catalog.append(tree)
    return tree_catalog


def render_100_trees_grid_preview(tree_catalog: list[trimesh.Trimesh], output: Path) -> None:
    """Render a 10x10 matrix overview image of all 100 tree species side by side."""
    fig, axes = plt.subplots(10, 10, figsize=(20, 20), facecolor="#080d14", subplot_kw={"projection": "3d"})
    fig.suptitle("100 Procedural 3D Tree Species Catalog (10x10 Family Matrix)", color="white", fontsize=20, fontweight="bold", y=0.92)

    for vid in range(100):
        row = vid // 10
        col = vid % 10
        ax = axes[row, col]

        t_mesh = tree_catalog[vid]
        verts = t_mesh.vertices
        faces = t_mesh.faces

        if hasattr(t_mesh.visual, "vertex_colors") and t_mesh.visual.vertex_colors is not None and len(t_mesh.visual.vertex_colors) > 0:
            colors = t_mesh.visual.vertex_colors[faces[:, 0], :3] / 255.0
        else:
            colors = np.tile(np.array([0.2, 0.6, 0.2]), (len(faces), 1))

        # Simple light shading
        face_normals = t_mesh.face_normals
        sun_dir = np.array([0.45, 0.75, 0.48])
        sun_dir /= np.linalg.norm(sun_dir)
        dot = np.clip(np.sum(face_normals * sun_dir, axis=1), 0.0, 1.0)
        light = dot * 0.50 + 0.50
        shaded_c = np.clip(colors * light[:, None], 0.0, 1.0)

        triangles = verts[faces][:, :, [0, 2, 1]]
        poly3d = Poly3DCollection(triangles, facecolors=shaded_c, edgecolor="none", alpha=1.0)
        ax.add_collection3d(poly3d)

        max_h = max(np.max(verts[:, 1]), 5.0)
        ax.set_xlim(-max_h * 0.5, max_h * 0.5)
        ax.set_ylim(-max_h * 0.5, max_h * 0.5)
        ax.set_zlim(0, max_h * 1.1)
        ax.view_init(elev=18, azim=-45)
        ax.set_box_aspect((1.0, 1.0, 1.0))
        ax.axis("off")

    output.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output, dpi=160, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)


def scatter_100_tree_species_on_terrain(
    x: np.ndarray,
    height: np.ndarray,
    z: np.ndarray,
    spacing: float,
    tree_catalog: list[trimesh.Trimesh],
    count: int = 1500,
    seed: int = 20260804,
) -> trimesh.Trimesh:
    """Scatter all 100 tree species across green meadow areas on 1km terrain."""
    rng = np.random.default_rng(seed)

    dz_drow, dz_dcol = np.gradient(height, spacing, spacing)
    slope = np.sqrt(dz_drow**2 + dz_dcol**2)

    WATER_LEVEL = 12.0
    valid_mask = (height > WATER_LEVEL + 3.5) & (slope < 0.55) & (height < 90.0)

    valid_indices = np.argwhere(valid_mask)
    if len(valid_indices) == 0:
        return trimesh.Trimesh()

    chosen_idx = rng.choice(len(valid_indices), size=min(count, len(valid_indices)), replace=False)

    tree_meshes = []
    for idx in chosen_idx:
        r, c = valid_indices[idx]
        tx = x[r, c] + rng.uniform(-spacing * 0.45, spacing * 0.45)
        ty = height[r, c]
        tz = z[r, c] + rng.uniform(-spacing * 0.45, spacing * 0.45)

        if np.sqrt(tx**2 + (tz + 5.0)**2) < 14.0:
            continue

        # Pick one of the 100 tree species variants randomly
        species_id = rng.integers(0, len(tree_catalog))
        base_tree = tree_catalog[species_id]

        scale = rng.uniform(0.75, 1.35)
        rot_y = rng.uniform(0, 2 * np.pi)

        mat = trimesh.transformations.rotation_matrix(rot_y, [0, 1, 0])
        mat[:3, :3] *= scale
        mat[:3, 3] = [tx, ty, tz]

        t_copy = base_tree.copy()
        t_copy.apply_transform(mat)
        tree_meshes.append(t_copy)

    if not tree_meshes:
        return trimesh.Trimesh()

    combined = trimesh.util.concatenate(tree_meshes)
    return combined


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate 100 tree species catalog.")
    parser.add_argument("--preview", type=Path, default=Path("hundred_trees_grid_preview.png"))
    parser.add_argument("--output", type=Path, default=Path("cave-diving-game/assets/terrain_trees_100_species.glb"))
    args = parser.parse_args()

    print("Generating 100 unique procedural 3D tree species...")
    catalog = generate_all_100_tree_species()

    print(f"Rendering 10x10 species matrix grid into '{args.preview.resolve()}'...")
    render_100_trees_grid_preview(catalog, args.preview)

    print("Exporting 100 species GLB catalog asset...")
    scene = trimesh.Scene()
    combined_catalog = trimesh.util.concatenate(catalog)
    scene.add_geometry(combined_catalog, node_name="HundredTreeSpeciesCatalog", geom_name="HundredTreeSpeciesCatalog")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    scene.export(args.output)
    print("100 Tree species generation complete!")


if __name__ == "__main__":
    main()
