"""Generate a Giant Redwood / Cổ Thụ Gõ Đỏ 3D tree species in Python
matching the user's reference photo with massive reddish trunk, buttress roots,
and high evergreen canopy.
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


def create_giant_redwood_tree(seed: int = 20260804) -> trimesh.Trimesh:
    """Create a massive Giant Redwood / Cổ Thụ Gõ Đỏ 3D tree mesh."""
    rng = np.random.default_rng(seed)

    # 1. TALL MASSIVE REDWOOD TRUNK WITH VERTICAL BARK GROOVES & BASE FLARE
    trunk_h = 26.0
    n_rings = 24
    n_seg = 20
    y_points = np.linspace(0.0, trunk_h, n_rings)

    trunk_verts = []
    trunk_colors = []

    for i, y in enumerate(y_points):
        t = y / trunk_h
        # Taper radius from 3.2m at base to 0.7m at top
        r = 3.2 * (1.0 - t)**1.8 + 0.7 * t

        angles = np.linspace(0, 2 * np.pi, n_seg, endpoint=False)

        # Base buttress root flare near ground
        if y < 3.5:
            flare = 1.0 + 0.55 * (3.5 - y) * (np.sin(6 * angles)**2)
        else:
            flare = 1.0

        # Bark vertical ridges (groove striations)
        ridge = 1.0 + 0.08 * np.sin(10 * angles)

        r_dist = r * flare * ridge + rng.uniform(-0.03, 0.03, n_seg)
        vx = r_dist * np.cos(angles)
        vz = r_dist * np.sin(angles)
        vy = np.full(n_seg, y)

        ring_v = np.column_stack([vx, vy, vz])
        trunk_verts.append(ring_v)

        # Reddish-cinnamon redwood bark color variation
        for a in angles:
            groove_darkness = 0.75 + 0.25 * np.sin(10 * a)
            r_c = int(165 * groove_darkness)
            g_c = int(72 * groove_darkness)
            b_c = int(32 * groove_darkness)
            trunk_colors.append([r_c, g_c, b_c, 255])

    trunk_verts = np.vstack(trunk_verts)
    trunk_colors = np.array(trunk_colors, dtype=np.uint8)

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
    trunk_mesh = trimesh.Trimesh(vertices=trunk_verts, faces=trunk_faces, vertex_colors=trunk_colors, process=False)

    # 2. HIGH EVERGREEN NEEDLE CANOPY TIERS (Starting high up at Y=14m to Y=28m)
    foliage_parts = []
    canopy_tiers = [
        # Lower tier branches
        (0.0, 14.5, 0.0, 6.2, [22, 105, 38, 255]),
        (3.2, 16.0, -1.8, 4.8, [28, 118, 42, 255]),
        (-3.0, 16.5, 2.2, 4.5, [32, 125, 45, 255]),
        # Middle tier branches
        (0.0, 18.5, 0.0, 5.5, [35, 135, 48, 255]),
        (-2.2, 20.0, -2.5, 4.2, [40, 145, 52, 255]),
        (2.5, 20.8, 1.8, 4.0, [45, 155, 55, 255]),
        # Upper tier branches
        (0.0, 23.0, 0.0, 4.8, [48, 165, 58, 255]),
        (1.5, 25.0, -1.2, 3.5, [55, 178, 65, 255]),
        (-1.2, 26.5, 1.0, 2.8, [62, 190, 72, 255]),
        # Top peak tip
        (0.0, 28.2, 0.0, 2.0, [70, 205, 80, 255]),
    ]

    for cx, cy, cz, radius, color in canopy_tiers:
        ico = trimesh.creation.icosphere(subdivisions=2, radius=radius)
        noise = rng.uniform(-0.20 * radius, 0.20 * radius, ico.vertices.shape)
        ico.vertices += noise
        ico.vertices += np.array([cx, cy, cz])
        ico.visual.vertex_colors = np.tile(np.array(color, dtype=np.uint8), (len(ico.vertices), 1))
        foliage_parts.append(ico)

    redwood_mesh = trimesh.util.concatenate([trunk_mesh] + foliage_parts)
    redwood_mesh.unmerge_vertices()
    return redwood_mesh


def render_redwood_preview(tree_mesh: trimesh.Trimesh, output: Path) -> None:
    """Render a solid 3D polygon preview of the Giant Redwood tree with human scale reference."""
    figure = plt.figure(figsize=(12, 14), facecolor="#0c1219")
    axis = figure.add_subplot(111, projection="3d")

    # Ground Plane
    g_angles = np.linspace(0, 2 * np.pi, 40)
    g_r = np.linspace(0, 12.0, 15)
    gr_r, gr_a = np.meshgrid(g_r, g_angles)
    gx = gr_r * np.cos(gr_a)
    gz = gr_r * np.sin(gr_a)
    gy = np.full_like(gx, 0.0)
    axis.plot_surface(gx, gz, gy, color="#1c4822", alpha=0.60, linewidth=0, shade=True)

    # Render SOLID 3D POLYGON MESH using Poly3DCollection
    verts = tree_mesh.vertices
    faces = tree_mesh.faces

    face_colors = tree_mesh.visual.vertex_colors[faces[:, 0], :3] / 255.0

    # Directional sun lighting
    face_normals = tree_mesh.face_normals
    sun_dir = np.array([0.45, 0.75, 0.48])
    sun_dir /= np.linalg.norm(sun_dir)
    dot = np.clip(np.sum(face_normals * sun_dir, axis=1), 0.0, 1.0)
    light = dot * 0.55 + 0.45
    shaded_colors = np.clip(face_colors * light[:, None], 0.0, 1.0)

    # Map coordinates (X, Z, Y)
    triangles = verts[faces][:, :, [0, 2, 1]]

    poly3d = Poly3DCollection(triangles, facecolors=shaded_colors, edgecolor="none", linewidths=0, alpha=1.0)
    axis.add_collection3d(poly3d)

    # Draw 1.8m Human Scale Reference Figure next to the tree base (matching reference photo!)
    hx = np.array([2.5, 2.5])
    hz = np.array([0.0, 0.0])
    hy = np.array([0.0, 1.8])
    axis.plot(hx, hz, hy, color="#ff3333", linewidth=4.0, label="1.8m Human Scale")
    axis.scatter([2.5], [0.0], [1.8], color="#ffcc00", s=60)

    axis.set_title("Giant Redwood Species (Cây Gõ Đỏ Cổ Thụ Khổng Lồ) — Solid 3D Mesh", color="white", pad=18, fontsize=14, fontweight="bold")
    axis.set_xlabel("X (m)", color="white", labelpad=8)
    axis.set_ylabel("Z (m)", color="white", labelpad=8)
    axis.set_zlabel("Height Y (m)", color="white", labelpad=8)
    axis.set_xlim(-12, 12)
    axis.set_ylim(-12, 12)
    axis.set_zlim(0, 30)
    axis.view_init(elev=16, azim=-42)
    axis.set_box_aspect((1.0, 1.0, 1.2))
    axis.set_facecolor("#0c1219")
    for pane in (axis.xaxis.pane, axis.yaxis.pane, axis.zaxis.pane):
        pane.set_facecolor((0.05, 0.08, 0.12, 1.0))
    axis.tick_params(colors="white")

    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=200, facecolor=figure.get_facecolor(), bbox_inches="tight")
    plt.close(figure)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Giant Redwood tree species.")
    parser.add_argument("--preview", type=Path, default=Path("redwood_tree_preview.png"))
    parser.add_argument("--output", type=Path, default=Path("cave-diving-game/assets/giant_redwood.glb"))
    args = parser.parse_args()

    tree_mesh = create_giant_redwood_tree(seed=20260804)

    # Render Studio 3D Preview Image
    render_redwood_preview(tree_mesh, args.preview)

    # Export GLB Model
    scene = trimesh.Scene()
    scene.add_geometry(tree_mesh, node_name="GiantRedwoodModel", geom_name="GiantRedwoodModel")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    scene.export(args.output)

    print(f"Rendered studio 3D redwood preview: {args.preview.resolve()}")
    print(f"Exported giant redwood GLB model: {args.output.resolve()}")


if __name__ == "__main__":
    main()
