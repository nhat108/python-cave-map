"""Procedural 3D Tree Generator and Scatterer for 1km Terrain.

Generates low-poly pine / broadleaf / ancient giant trees and scatters them naturally
across grass meadow areas on the terrain.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import numpy as np
import trimesh
from terrain_surface_generator import build_terrain, WORLD_SIZE_METERS


def create_ancient_tree(seed: int = 42) -> trimesh.Trimesh:
    """Generate a massive ancient giant tree (Cổ Thụ) with sprawling roots and huge canopy."""
    rng = np.random.default_rng(seed)

    # Giant Trunk (height ~ 14m, radius_bottom ~ 1.8m, radius_top ~ 0.5m)
    trunk_h = 14.0
    r_bot, r_top = 1.8, 0.5
    segments = 12

    angles = np.linspace(0, 2 * np.pi, segments, endpoint=False)
    # Add root flare noise
    root_flare = 1.0 + 0.3 * np.sin(4 * angles)
    bot_verts = np.column_stack([r_bot * root_flare * np.cos(angles), np.zeros(segments), r_bot * root_flare * np.sin(angles)])
    top_verts = np.column_stack([r_top * np.cos(angles), np.full(segments, trunk_h), r_top * np.sin(angles)])

    trunk_vertices = np.vstack([bot_verts, top_verts])
    trunk_faces = []
    for i in range(segments):
        ni = (i + 1) % segments
        trunk_faces.append([i, ni, segments + i])
        trunk_faces.append([ni, segments + ni, segments + i])

    trunk_faces = np.array(trunk_faces, dtype=np.int64)
    trunk_colors = np.tile(np.array([75, 45, 22, 255], dtype=np.uint8), (len(trunk_vertices), 1))
    trunk_mesh = trimesh.Trimesh(vertices=trunk_vertices, faces=trunk_faces, vertex_colors=trunk_colors, process=False)

    # Massive Sprawling Canopy: 6 overlapping foliage clouds
    foliage_parts = []
    foliage_configs = [
        (0.0, 11.0, 0.0, 6.5, [25, 115, 35, 255]),   # Main wide base
        (3.5, 12.5, -2.0, 5.0, [32, 130, 40, 255]),  # Sprawling right branch
        (-3.0, 13.0, 2.5, 4.8, [38, 145, 45, 255]),  # Sprawling left branch
        (1.5, 15.0, 1.5, 4.2, [45, 160, 52, 255]),   # Upper middle cloud
        (-1.5, 16.5, -1.0, 3.8, [52, 175, 58, 255]),  # Top canopy
        (0.0, 18.0, 0.0, 3.0, [60, 190, 65, 255]),   # High peak foliage
    ]

    for cx, cy, cz, radius, color in foliage_configs:
        ico = trimesh.creation.icosphere(subdivisions=1, radius=radius)
        noise = rng.uniform(-0.35, 0.35, ico.vertices.shape)
        ico.vertices += noise
        ico.vertices += np.array([cx, cy, cz])
        ico.visual.vertex_colors = np.tile(np.array(color, dtype=np.uint8), (len(ico.vertices), 1))
        foliage_parts.append(ico)

    ancient_tree = trimesh.util.concatenate([trunk_mesh] + foliage_parts)
    ancient_tree.unmerge_vertices()
    return ancient_tree


def create_pine_tree(seed: int = 42) -> trimesh.Trimesh:
    """Generate a tall coniferous pine tree."""
    rng = np.random.default_rng(seed)

    trunk_h = 10.0
    r_bot, r_top = 0.30, 0.08
    segments = 6

    angles = np.linspace(0, 2 * np.pi, segments, endpoint=False)
    bot_verts = np.column_stack([r_bot * np.cos(angles), np.zeros(segments), r_bot * np.sin(angles)])
    top_verts = np.column_stack([r_top * np.cos(angles), np.full(segments, trunk_h), r_top * np.sin(angles)])

    trunk_vertices = np.vstack([bot_verts, top_verts])
    trunk_faces = []
    for i in range(segments):
        ni = (i + 1) % segments
        trunk_faces.append([i, ni, segments + i])
        trunk_faces.append([ni, segments + ni, segments + i])

    trunk_mesh = trimesh.Trimesh(vertices=trunk_vertices, faces=np.array(trunk_faces), vertex_colors=np.tile(np.array([70, 42, 20, 255], dtype=np.uint8), (len(trunk_vertices), 1)), process=False)

    # Conical Foliage Tiers
    foliage_parts = []
    tiers = [
        (4.0, 3.2, 2.5, [18, 90, 30, 255]),
        (6.5, 2.5, 2.2, [22, 110, 38, 255]),
        (9.0, 1.8, 1.8, [28, 130, 45, 255]),
        (11.2, 1.0, 1.2, [35, 150, 52, 255]),
    ]
    for y_pos, radius, height_val, color in tiers:
        cone = trimesh.creation.cone(radius=radius, height=height_val, sections=7)
        cone.vertices[:, 1] += y_pos
        cone.visual.vertex_colors = np.tile(np.array(color, dtype=np.uint8), (len(cone.vertices), 1))
        foliage_parts.append(cone)

    pine = trimesh.util.concatenate([trunk_mesh] + foliage_parts)
    pine.unmerge_vertices()
    return pine


def create_single_tree(seed: int = 42) -> trimesh.Trimesh:
    """Generate a medium broadleaf meadow tree."""
    rng = np.random.default_rng(seed)

    trunk_h = 5.5
    r_bot, r_top = 0.42, 0.15
    segments = 8

    angles = np.linspace(0, 2 * np.pi, segments, endpoint=False)
    bot_verts = np.column_stack([r_bot * np.cos(angles), np.zeros(segments), r_bot * np.sin(angles)])
    top_verts = np.column_stack([r_top * np.cos(angles), np.full(segments, trunk_h), r_top * np.sin(angles)])

    trunk_vertices = np.vstack([bot_verts, top_verts])
    trunk_faces = []
    for i in range(segments):
        ni = (i + 1) % segments
        trunk_faces.append([i, ni, segments + i])
        trunk_faces.append([ni, segments + ni, segments + i])

    trunk_faces = np.array(trunk_faces, dtype=np.int64)
    trunk_colors = np.tile(np.tile(np.array([85, 52, 28, 255], dtype=np.uint8), (len(trunk_vertices), 1)), (1, 1))
    trunk_mesh = trimesh.Trimesh(vertices=trunk_vertices, faces=trunk_faces, vertex_colors=trunk_colors, process=False)

    foliage_parts = []
    foliage_configs = [
        (0.0, 4.5, 0.0, 2.8, [35, 135, 45, 255]),
        (0.4, 5.8, -0.3, 2.2, [45, 160, 50, 255]),
        (-0.3, 7.0, 0.3, 1.7, [55, 180, 60, 255]),
    ]

    for cx, cy, cz, radius, color in foliage_configs:
        ico = trimesh.creation.icosphere(subdivisions=1, radius=radius)
        noise = rng.uniform(-0.18, 0.18, ico.vertices.shape)
        ico.vertices += noise
        ico.vertices += np.array([cx, cy, cz])
        ico.visual.vertex_colors = np.tile(np.array(color, dtype=np.uint8), (len(ico.vertices), 1))
        foliage_parts.append(ico)

    tree_mesh = trimesh.util.concatenate([trunk_mesh] + foliage_parts)
    tree_mesh.unmerge_vertices()
    return tree_mesh


def generate_tree_instances(
    x: np.ndarray,
    height: np.ndarray,
    z: np.ndarray,
    spacing: float,
    count: int = 3500,
    seed: int = 20260804,
) -> trimesh.Trimesh:
    """Scatter 3,500+ procedural trees and giant jungle bush clusters across 1km terrain."""
    rng = np.random.default_rng(seed)

    dz_drow, dz_dcol = np.gradient(height, spacing, spacing)
    slope = np.sqrt(dz_drow**2 + dz_dcol**2)

    WATER_LEVEL = 12.0
    valid_mask = (height > WATER_LEVEL + 3.5) & (slope < 0.55) & (height < 90.0)

    valid_indices = np.argwhere(valid_mask)
    if len(valid_indices) == 0:
        return trimesh.Trimesh()

    chosen_idx = rng.choice(len(valid_indices), size=min(count, len(valid_indices)), replace=False)

    # Pre-generate 100 unique species variants catalog
    from generate_100_tree_species import generate_all_100_tree_species
    tree_catalog = generate_all_100_tree_species()

    tree_meshes = []
    for idx in chosen_idx:
        r, c = valid_indices[idx]
        tx = x[r, c] + rng.uniform(-spacing * 0.45, spacing * 0.45)
        ty = height[r, c]
        tz = z[r, c] + rng.uniform(-spacing * 0.45, spacing * 0.45)

        # Avoid sinkhole entrance
        if np.sqrt(tx**2 + (tz + 5.0)**2) < 14.0:
            continue

        # Sample randomly from all 100 tree species
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

    combined_trees = trimesh.util.concatenate(tree_meshes)
    return combined_trees


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate and scatter 1,200+ 3D trees on 1km terrain.")
    parser.add_argument("--output", type=Path, default=Path("cave-diving-game/assets/terrain_trees.glb"))
    parser.add_argument("--count", type=int, default=1200)
    args = parser.parse_args()

    x, height, z = build_terrain(resolution=320, seed=20260804)
    spacing = WORLD_SIZE_METERS / (320 - 1)

    trees_mesh = generate_tree_instances(x, height, z, spacing, count=args.count)

    scene = trimesh.Scene()
    scene.add_geometry(trees_mesh, node_name="TerrainTrees", geom_name="TerrainTrees")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    scene.export(args.output)
    print(f"Generated primeval forest with {args.count} procedural 3D trees in '{args.output.resolve()}'!")


if __name__ == "__main__":
    main()
