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


WORLD_SIZE_METERS = 5_000.0
WATER_LEVEL = 72.0


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
    for cells in (3, 6, 12, 24, 48, 96):
        terrain += value_noise(shape, cells, rng) * amplitude
        total_amplitude += amplitude
        amplitude *= 0.48
    terrain /= total_amplitude
    terrain -= terrain.mean()
    return terrain / max(terrain.std(), 1e-6)


def build_terrain(resolution: int, seed: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return X, Y, Z grids in metres for a 5 km natural landscape."""
    rng = np.random.default_rng(seed)
    axis = np.linspace(-WORLD_SIZE_METERS / 2.0, WORLD_SIZE_METERS / 2.0, resolution)
    x, z = np.meshgrid(axis, axis)
    nx, nz = x / WORLD_SIZE_METERS, z / WORLD_SIZE_METERS

    broad = fbm((resolution, resolution), rng)
    detail = fbm((resolution, resolution), rng)
    # A rolling mountainous region that rises toward the edges.
    edge_rise = 135.0 * (nx * nx + nz * nz)
    ridges = 48.0 * np.abs(detail) ** 1.35
    height = 150.0 + broad * 112.0 + ridges + edge_rise

    # A broad lake basin near the world centre with a narrow natural outflow valley.
    lake_x, lake_z = 260.0, 180.0
    basin = np.exp(-(((x - lake_x) / 690.0) ** 2 + ((z - lake_z) / 530.0) ** 2))
    height -= basin * 235.0
    valley = np.exp(-((x - lake_x) / 310.0) ** 2) * np.exp(-((z + 1_150.0) / 1_250.0) ** 2)
    height -= valley * 92.0

    # Keep the lake floor gently below the waterline for a readable shoreline.
    lake_mask = basin > 0.38
    height[lake_mask] = np.minimum(height[lake_mask], WATER_LEVEL - 6.0 - basin[lake_mask] * 46.0)
    return x, height, z


def terrain_colors(height: np.ndarray, spacing: float) -> np.ndarray:
    """Color the surface by height and slope: water, sand, grass, and bare rock."""
    dz_drow, dz_dcol = np.gradient(height, spacing, spacing)
    slope = np.sqrt(dz_drow * dz_drow + dz_dcol * dz_dcol)
    colors = np.empty((*height.shape, 3), dtype=np.float64)

    water = height <= WATER_LEVEL
    beach = (height > WATER_LEVEL) & (height <= WATER_LEVEL + 15.0)
    rock = (height > WATER_LEVEL + 15.0) & ((slope > 0.55) | (height > 310.0))
    grass = ~(water | beach | rock)

    colors[water] = (0.04, 0.24, 0.52)
    colors[beach] = (0.58, 0.47, 0.27)
    colors[grass] = (0.16, 0.36, 0.14)
    colors[rock] = (0.26, 0.25, 0.22)
    return colors


def render(output: Path, resolution: int, seed: int) -> None:
    x, height, z = build_terrain(resolution, seed)
    spacing = WORLD_SIZE_METERS / (resolution - 1)
    colors = terrain_colors(height, spacing)
    # Preserve the terrain floor in ``height`` but render a physically flat lake surface.
    surface_height = np.maximum(height, WATER_LEVEL)
    lighting = LightSource(azdeg=315, altdeg=45)
    shaded = lighting.shade_rgb(colors, surface_height, vert_exag=0.7, blend_mode="soft")

    figure = plt.figure(figsize=(16, 10), facecolor="#101820")
    axis = figure.add_subplot(111, projection="3d")
    axis.plot_surface(
        x,
        z,
        surface_height,
        facecolors=shaded,
        rstride=2,
        cstride=2,
        linewidth=0,
        antialiased=True,
        shade=False,
    )
    axis.set_title("Natural 5 km × 5 km Surface Terrain — Lake Above Cave Entrance", color="white", pad=18)
    axis.set_xlabel("East / West (m)", color="white", labelpad=10)
    axis.set_ylabel("North / South (m)", color="white", labelpad=10)
    axis.set_zlabel("Elevation (m)", color="white", labelpad=8)
    axis.set_xlim(-2_500, 2_500)
    axis.set_ylim(-2_500, 2_500)
    axis.set_zlim(-80, 520)
    axis.view_init(elev=37, azim=-52)
    axis.set_box_aspect((1.0, 1.0, 0.34))
    axis.set_facecolor("#101820")
    for pane in (axis.xaxis.pane, axis.yaxis.pane, axis.zaxis.pane):
        pane.set_facecolor((0.07, 0.10, 0.13, 1.0))
    axis.tick_params(colors="white")
    figure.text(
        0.02,
        0.02,
        "Blue basin: surface lake. The future cave entrance descends beneath its deepest point.",
        color="white",
        fontsize=11,
    )
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
    faces = grid_faces(resolution)
    terrain_vertices = np.column_stack((x.ravel(), height.ravel(), z.ravel()))
    terrain_rgb = terrain_colors(height, WORLD_SIZE_METERS / (resolution - 1))
    terrain_rgba = np.column_stack((terrain_rgb.reshape(-1, 3) * 255, np.full(resolution * resolution, 255))).astype(np.uint8)
    terrain = trimesh.Trimesh(vertices=terrain_vertices, faces=faces, vertex_colors=terrain_rgba, process=False)

    # Only cells entirely under the water level become lake faces, preserving a natural shoreline.
    submerged = height <= WATER_LEVEL
    cell_mask = submerged[:-1, :-1] & submerged[1:, :-1] & submerged[:-1, 1:] & submerged[1:, 1:]
    lake_faces = faces.reshape(2, resolution - 1, resolution - 1, 3)[:, cell_mask].reshape(-1, 3)
    lake_vertices = terrain_vertices.copy()
    lake_vertices[:, 1] = WATER_LEVEL
    lake_rgba = np.tile(np.array((18, 91, 181, 190), dtype=np.uint8), (len(lake_vertices), 1))
    lake = trimesh.Trimesh(vertices=lake_vertices, faces=lake_faces, vertex_colors=lake_rgba, process=False)

    scene = trimesh.Scene()
    scene.add_geometry(terrain, node_name="NaturalTerrain5km", geom_name="NaturalTerrain5km")
    scene.add_geometry(lake, node_name="SurfaceLake", geom_name="SurfaceLake")
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
    # Render uses the same deterministic terrain data that becomes the runtime assets.
    render(args.output, args.resolution, args.seed)
    export_heightmap(height, args.heightmap)
    export_mesh(x, height, z, args.mesh)
    print(f"Rendered natural terrain preview: {args.output.resolve()}")
    print(f"Exported Godot heightmap: {args.heightmap.resolve()}")
    print(f"Exported Godot mesh: {args.mesh.resolve()}")


if __name__ == "__main__":
    main()
