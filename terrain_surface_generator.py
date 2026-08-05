"""Render a natural 5 km x 5 km terrain surface for the cave-diving world.

The terrain is a smooth heightfield (not a voxel/block world).  It combines
large mountain forms, medium ridges, fine erosion-like detail, and a lake basin
that can later become the surface entrance to the underwater cave system.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LightSource
from PIL import Image
import trimesh


WORLD_SIZE_METERS = 1_000.0
WATER_LEVEL = 12.0


def value_noise(shape: tuple[int, int], cells: int, rng: np.random.Generator) -> np.ndarray:
    """Generate smooth, tile-safe value noise without external noise packages."""
    grid = rng.normal(0.0, 1.0, (cells + 1, cells + 1))
    y = np.linspace(0.0, cells, shape[0], endpoint=False)
    x = np.linspace(0.0, cells, shape[1], endpoint=False)
    yi, xi = np.floor(y).astype(int), np.floor(x).astype(int)
    yf, xf = y - yi, x - xi
    # Smoothstep interpolation prevents visible grid cells.
    yf = yf * yf * (3.0 - 2.0 * yf)
    xf = xf * xf * (3.0 - 2.0 * xf)
    a = grid[yi[:, None], xi[None, :]]
    b = grid[(yi + 1)[:, None], xi[None, :]]
    c = grid[yi[:, None], (xi + 1)[None, :]]
    d = grid[(yi + 1)[:, None], (xi + 1)[None, :]]
    return (a * (1.0 - xf) + c * xf) * (1.0 - yf[:, None]) + (b * (1.0 - xf) + d * xf) * yf[:, None]


def fbm(shape: tuple[int, int], rng: np.random.Generator) -> np.ndarray:
    """Fractal Brownian motion: broad landforms plus progressively finer detail."""
    terrain = np.zeros(shape, dtype=np.float64)
    amplitude = 1.0
    total_amplitude = 0.0
    for cells in (4, 8, 16, 32, 64, 128):
        terrain += value_noise(shape, cells, rng) * amplitude
        total_amplitude += amplitude
        amplitude *= 0.50
    terrain /= total_amplitude
    terrain -= terrain.mean()
    return terrain / max(terrain.std(), 1e-6)


def build_terrain(resolution: int, seed: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return X, Y, Z grids in metres for a 1 km natural landscape."""
    rng = np.random.default_rng(seed)
    axis = np.linspace(-WORLD_SIZE_METERS / 2.0, WORLD_SIZE_METERS / 2.0, resolution)
    x, z = np.meshgrid(axis, axis)
    nx, nz = x / WORLD_SIZE_METERS, z / WORLD_SIZE_METERS

    broad = fbm((resolution, resolution), rng)
    detail = fbm((resolution, resolution), rng)
    edge_rise = 45.0 * (nx * nx + nz * nz)
    ridges = 18.0 * np.abs(detail) ** 1.35
    micro = 3.5 * detail  # Crisp micro-detail for rich surface texture
    height = 25.0 + broad * 18.0 + ridges + edge_rise + micro

    # Lake basin near world centre
    lake_x, lake_z = 60.0, 40.0
    basin = np.exp(-(((x - lake_x) / 160.0) ** 2 + ((z - lake_z) / 120.0) ** 2))
    height -= basin * 38.0

    lake_mask = basin > 0.38
    height[lake_mask] = np.minimum(height[lake_mask], WATER_LEVEL - 2.5 - basin[lake_mask] * 8.0)
    return x, height, z


def terrain_colors(height: np.ndarray, spacing: float) -> np.ndarray:
    """Color the surface by height, slope, and micro-face lighting variation."""
    dz_drow, dz_dcol = np.gradient(height, spacing, spacing)
    slope = np.sqrt(dz_drow * dz_drow + dz_dcol * dz_dcol)

    # Compute surface normals per vertex for crisp 3D facet lighting
    normals = np.empty((*height.shape, 3), dtype=np.float64)
    normals[:, :, 0] = -dz_drow
    normals[:, :, 1] = 1.0
    normals[:, :, 2] = -dz_dcol
    norm_len = np.sqrt(normals[:, :, 0] ** 2 + normals[:, :, 1] ** 2 + normals[:, :, 2] ** 2)
    normals /= np.maximum(norm_len[:, :, None], 1e-6)

    # Directional sun vector
    sun_dir = np.array([0.45, 0.75, 0.48], dtype=np.float64)
    sun_dir /= np.linalg.norm(sun_dir)
    dot = np.clip(np.sum(normals * sun_dir, axis=2), 0.0, 1.0)
    light = dot * 0.65 + 0.45  # Scale light factor between 0.45 and 1.10

    colors = np.empty((*height.shape, 3), dtype=np.float64)

    water = height <= WATER_LEVEL
    beach = (height > WATER_LEVEL) & (height <= WATER_LEVEL + 4.0)
    rock = (height > WATER_LEVEL + 4.0) & ((slope > 0.65) | (height > 90.0))
    grass = ~(water | beach | rock)

    colors[water] = np.array([0.08, 0.42, 0.78])
    colors[beach] = np.array([0.76, 0.62, 0.38])
    colors[grass] = np.array([0.22, 0.35, 0.16])  # Warm Prairie Olive Green
    colors[rock] = np.array([0.28, 0.26, 0.24])

    # Apply lighting variation to land vertices for crisp 3D faceted depth
    land_mask = ~water
    colors[land_mask] = np.clip(colors[land_mask] * light[land_mask, None], 0.0, 1.0)
    return colors


def generate_terrain_texture(height: np.ndarray, spacing: float, tex_size: int = 1024) -> Image.Image:
    """Generate a high-resolution 2D PBR Albedo Texture map (PNG) for the terrain."""
    h_img = Image.fromarray(height).resize((tex_size, tex_size), Image.Resampling.BILINEAR)
    h_arr = np.array(h_img, dtype=np.float64)

    dz_drow, dz_dcol = np.gradient(h_arr, spacing * (height.shape[0] / tex_size))
    slope = np.sqrt(dz_drow**2 + dz_dcol**2)

    # Multi-scale Noise for Grass, Rock, and Sand textures
    rng = np.random.default_rng(20260804)
    grass_noise = fbm((tex_size, tex_size), rng)
    rock_noise = fbm((tex_size, tex_size), rng)

    # Base Colors
    # Prairie Grass: blend warm olive moss (0.16, 0.28, 0.12) with golden prairie green (0.26, 0.38, 0.16)
    grass_col = np.zeros((tex_size, tex_size, 3), dtype=np.float64)
    t_g = (grass_noise - grass_noise.min()) / max(grass_noise.max() - grass_noise.min(), 1e-6)
    grass_col[:, :, 0] = 0.16 + 0.12 * t_g
    grass_col[:, :, 1] = 0.28 + 0.12 * t_g
    grass_col[:, :, 2] = 0.12 + 0.06 * t_g

    # Rock: blend dark slate (0.18, 0.17, 0.16) with mountain granite (0.40, 0.38, 0.35)
    rock_col = np.zeros((tex_size, tex_size, 3), dtype=np.float64)
    t_r = (rock_noise - rock_noise.min()) / max(rock_noise.max() - rock_noise.min(), 1e-6)
    rock_col[:, :, 0] = 0.18 + 0.24 * t_r
    rock_col[:, :, 1] = 0.17 + 0.22 * t_r
    rock_col[:, :, 2] = 0.16 + 0.20 * t_r

    # Sand: warm golden sand (0.78, 0.65, 0.42)
    sand_col = np.zeros((tex_size, tex_size, 3), dtype=np.float64)
    sand_col[:, :, 0] = 0.78 + 0.04 * grass_noise
    sand_col[:, :, 1] = 0.65 + 0.04 * grass_noise
    sand_col[:, :, 2] = 0.42 + 0.03 * grass_noise

    # Lake floor mud
    mud_col = np.array([0.08, 0.25, 0.45])

    water = h_arr <= WATER_LEVEL
    beach = (h_arr > WATER_LEVEL) & (h_arr <= WATER_LEVEL + 4.0)
    rock = (h_arr > WATER_LEVEL + 4.0) & ((slope > 0.65) | (h_arr > 90.0))
    grass = ~(water | beach | rock)

    final_tex = np.zeros((tex_size, tex_size, 3), dtype=np.float64)
    final_tex[grass] = grass_col[grass]
    final_tex[rock] = rock_col[rock]
    final_tex[beach] = sand_col[beach]
    final_tex[water] = mud_col

    # Sun directional lighting for 3D depth
    sun_dir = np.array([0.45, 0.75, 0.48], dtype=np.float64)
    sun_dir /= np.linalg.norm(sun_dir)
    normals = np.empty((tex_size, tex_size, 3), dtype=np.float64)
    normals[:, :, 0] = -dz_drow
    normals[:, :, 1] = 1.0
    normals[:, :, 2] = -dz_dcol
    norm_len = np.sqrt(normals[:, :, 0]**2 + normals[:, :, 1]**2 + normals[:, :, 2]**2)
    normals /= np.maximum(norm_len[:, :, None], 1e-6)

    dot = np.clip(np.sum(normals * sun_dir, axis=2), 0.0, 1.0)
    light = dot * 0.65 + 0.45

    land_mask = ~water
    final_tex[land_mask] = np.clip(final_tex[land_mask] * light[land_mask, None], 0.0, 1.0)
    return Image.fromarray((final_tex * 255.0).astype(np.uint8), mode="RGB")


def render(output: Path, resolution: int, seed: int) -> None:
    x, height, z = build_terrain(resolution, seed)
    spacing = WORLD_SIZE_METERS / (resolution - 1)
    
    # Generate high-resolution 2D Texture Image
    tex_img = generate_terrain_texture(height, spacing, tex_size=1024)
    tex_path = Path("cave-diving-game/assets/terrain_texture.png")
    tex_path.parent.mkdir(parents=True, exist_ok=True)
    tex_img.save(tex_path)

    # Convert texture image to matplotlib array for plot_surface
    tex_arr = np.array(tex_img, dtype=np.float64) / 255.0

    surface_height = np.maximum(height, WATER_LEVEL)

    figure = plt.figure(figsize=(16, 10), facecolor="#101820")
    axis = figure.add_subplot(111, projection="3d")
    axis.plot_surface(
        x,
        z,
        surface_height,
        facecolors=tex_arr,
        rstride=1,
        cstride=1,
        linewidth=0,
        antialiased=True,
        shade=False,
    )

    # Plot 1,200+ 3D procedural trees (including ancient giant trees) onto Python preview
    try:
        rng_t = np.random.default_rng(20260804)
        dz_drow, dz_dcol = np.gradient(height, spacing, spacing)
        slope = np.sqrt(dz_drow**2 + dz_dcol**2)
        valid_mask = (height > WATER_LEVEL + 3.5) & (slope < 0.55) & (height < 90.0)
        valid_indices = np.argwhere(valid_mask)
        chosen_idx = rng_t.choice(len(valid_indices), size=min(1200, len(valid_indices)), replace=False)

        tree_x, tree_z, tree_y_base, tree_y_top, sizes, colors = [], [], [], [], [], []

        for idx in chosen_idx:
            r, c = valid_indices[idx]
            tx = x[r, c] + rng_t.uniform(-spacing * 0.45, spacing * 0.45)
            tz = z[r, c] + rng_t.uniform(-spacing * 0.45, spacing * 0.45)
            ty = height[r, c]
            if np.sqrt(tx**2 + (tz + 5.0)**2) < 14.0:
                continue

            r_type = rng_t.random()
            if r_type < 0.15:  # Ancient Giant Tree
                h_tree = rng_t.uniform(14.0, 18.0)
                s_canopy = rng_t.uniform(220, 380)
                col = '#1e7b28'
            elif r_type < 0.60:  # Medium Tree
                h_tree = rng_t.uniform(5.5, 8.5)
                s_canopy = rng_t.uniform(80, 140)
                col = '#2fb83d'
            else:  # Pine Tree
                h_tree = rng_t.uniform(8.0, 12.0)
                s_canopy = rng_t.uniform(60, 110)
                col = '#166624'

            tree_x.append(tx)
            tree_z.append(tz)
            tree_y_base.append(ty)
            tree_y_top.append(ty + h_tree)
            sizes.append(s_canopy)
            colors.append(col)

        tree_x = np.array(tree_x)
        tree_z = np.array(tree_z)
        tree_y_base = np.array(tree_y_base)
        tree_y_top = np.array(tree_y_top)

        # Draw 3D Tree Trunks
        for i in range(len(tree_x)):
            axis.plot([tree_x[i], tree_x[i]], [tree_z[i], tree_z[i]], [tree_y_base[i], tree_y_top[i]], color='#55341c', linewidth=1.5, alpha=0.85)

        # Draw 3D Tree Canopies
        axis.scatter(tree_x, tree_z, tree_y_top, c=colors, s=sizes, alpha=0.95, depthshade=True, edgecolors='#0d3b12', linewidths=0.5)
    except Exception as e:
        print(f"Tree render preview note: {e}")

    axis.set_title("Natural 1 km × 1 km Surface Terrain with 1,200+ Primeval Forest Trees", color="white", pad=18)
    axis.set_xlabel("East / West (m)", color="white", labelpad=10)
    axis.set_ylabel("North / South (m)", color="white", labelpad=10)
    axis.set_zlabel("Elevation (m)", color="white", labelpad=8)
    axis.set_xlim(-500, 500)
    axis.set_ylim(-500, 500)
    axis.set_zlim(-20, 180)
    axis.view_init(elev=37, azim=-52)
    axis.set_box_aspect((1.0, 1.0, 0.34))
    axis.set_facecolor("#101820")
    for pane in (axis.xaxis.pane, axis.yaxis.pane, axis.zaxis.pane):
        pane.set_facecolor((0.07, 0.10, 0.13, 1.0))
    axis.tick_params(colors="white")
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=180, facecolor=figure.get_facecolor(), bbox_inches="tight")
    plt.close(figure)


def grid_faces(resolution: int) -> np.ndarray:
    """Build two smooth triangles for each heightfield cell."""
    indices = np.arange(resolution * resolution, dtype=np.int64).reshape(resolution, resolution)
    top_left = indices[:-1, :-1].ravel()
    top_right = indices[:-1, 1:].ravel()
    bottom_left = indices[1:, :-1].ravel()
    bottom_right = indices[1:, 1:].ravel()
    return np.vstack(
        (
            np.column_stack((top_left, bottom_left, top_right)),
            np.column_stack((top_right, bottom_left, bottom_right)),
        )
    )


def export_heightmap(height: np.ndarray, output: Path) -> None:
    """Write a 16-bit heightmap; Godot can import this for a terrain plugin."""
    normalized = (height - height.min()) / max(height.max() - height.min(), 1e-6)
    pixels = np.round(normalized * np.iinfo(np.uint16).max).astype(np.uint16)
    output.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(pixels, mode="I;16").save(output)


def export_mesh(x: np.ndarray, height: np.ndarray, z: np.ndarray, output: Path) -> None:
    """Export terrain and a flat, irregular lake surface into one Godot-ready GLB."""
    resolution = x.shape[0]
    spacing = WORLD_SIZE_METERS / (resolution - 1)
    faces = grid_faces(resolution)
    terrain_vertices = np.column_stack((x.ravel(), height.ravel(), z.ravel()))

    # Smooth per-vertex normals from the height gradient. Without these, the glTF
    # has no NORMAL attribute and Godot auto-generates flat per-face normals,
    # which makes the heightfield look like faceted low-poly chunks under directional
    # light instead of the smooth terrain it actually is.
    dz_drow, dz_dcol = np.gradient(height, spacing, spacing)
    terrain_normals = np.dstack((-dz_drow, np.ones_like(height), -dz_dcol)).reshape(-1, 3)
    terrain_normals = terrain_normals / np.linalg.norm(terrain_normals, axis=1, keepdims=True)

    # Cut out open entrance portal hole at bottom of sinkhole (radius < 7.8m at (0, -5))
    dist_v = np.sqrt((terrain_vertices[:, 0] - 0.0) ** 2 + (terrain_vertices[:, 2] - (-5.0)) ** 2)
    hole_mask = ~(
        (dist_v[faces[:, 0]] < 7.8)
        & (dist_v[faces[:, 1]] < 7.8)
        & (dist_v[faces[:, 2]] < 7.8)
    )
    faces = faces[hole_mask]

    # Map UV coordinates (0..1 across X and Z)
    u = (x.ravel() + WORLD_SIZE_METERS / 2.0) / WORLD_SIZE_METERS
    v = (z.ravel() + WORLD_SIZE_METERS / 2.0) / WORLD_SIZE_METERS
    uvs = np.column_stack((u, v))

    terrain_rgb = terrain_colors(height, spacing)
    terrain_rgba = np.column_stack((terrain_rgb.reshape(-1, 3) * 255, np.full(len(terrain_vertices), 255))).astype(np.uint8)
    terrain = trimesh.Trimesh(vertices=terrain_vertices, faces=faces, vertex_colors=terrain_rgba, visual=trimesh.visual.TextureVisuals(uv=uvs), process=False)
    # unmerge_vertices() re-indexes every per-vertex array to one-vertex-per-face-corner;
    # precompute that same re-indexing for the normals so we can re-assert it later. (Relying
    # on trimesh's cache to carry the normals through untouched is not reliable once the lake
    # and 220 trees are also built and added to the scene -- something along that path evicts
    # the cached array, so the exported terrain silently loses its NORMAL attribute again.)
    unmerged_terrain_normals = terrain_normals[faces.reshape(-1)]
    terrain.vertex_normals = unmerged_terrain_normals
    terrain.unmerge_vertices()

    raw_faces = grid_faces(resolution)
    submerged = height <= WATER_LEVEL
    cell_mask = submerged[:-1, :-1] & submerged[1:, :-1] & submerged[:-1, 1:] & submerged[1:, 1:]
    lake_faces = raw_faces.reshape(2, resolution - 1, resolution - 1, 3)[:, cell_mask].reshape(-1, 3)
    lake_vertices = terrain_vertices.copy()
    lake_vertices[:, 1] = WATER_LEVEL
    lake_rgba = np.tile(np.array((18, 91, 181, 190), dtype=np.uint8), (len(lake_vertices), 1))
    lake = trimesh.Trimesh(vertices=lake_vertices, faces=lake_faces, vertex_colors=lake_rgba, process=False)

    scene = trimesh.Scene()
    scene.add_geometry(terrain, node_name="NaturalTerrain5km", geom_name="NaturalTerrain5km")
    scene.add_geometry(lake, node_name="SurfaceLake", geom_name="SurfaceLake")

    # Add 220 procedural 3D trees scattered across green meadows
    try:
        from procedural_tree_generator import generate_tree_instances
        trees_mesh = generate_tree_instances(x, height, z, WORLD_SIZE_METERS / (resolution - 1), count=220)
        if len(trees_mesh.vertices) > 0:
            scene.add_geometry(trees_mesh, node_name="TerrainTrees", geom_name="TerrainTrees")
    except Exception as e:
        print(f"Tree generation warning: {e}")

    # Re-assert immediately before export: see the comment above unmerge_vertices().
    terrain.vertex_normals = unmerged_terrain_normals
    output.parent.mkdir(parents=True, exist_ok=True)
    scene.export(output)


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a natural 5 km terrain preview.")
    parser.add_argument("--output", type=Path, default=Path("rendered_5km_terrain.png"))
    parser.add_argument("--heightmap", type=Path, default=Path("cave-diving-game/assets/terrain_5km_heightmap.png"))
    parser.add_argument("--mesh", type=Path, default=Path("cave-diving-game/assets/terrain_5km.glb"))
    parser.add_argument("--resolution", type=int, default=320)
    parser.add_argument("--seed", type=int, default=20260804)
    args = parser.parse_args()
    x, height, z = build_terrain(args.resolution, args.seed)
    render(args.output, args.resolution, args.seed)
    export_heightmap(height, args.heightmap)
    export_mesh(x, height, z, args.mesh)
    print(f"Rendered natural terrain preview: {args.output.resolve()}")
    print(f"Exported Godot heightmap: {args.heightmap.resolve()}")
    print(f"Exported Godot mesh: {args.mesh.resolve()}")


if __name__ == "__main__":
    main()
