"""Generate a single ultra-detailed realistic 3D Ancient Tree (Cổ Thụ) in Python
and render a studio 3D preview image single_tree_preview.png.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import trimesh


def create_ultra_realistic_tree(seed: int = 20260804) -> trimesh.Trimesh:
    """Create a highly detailed, realistic 3D Ancient Oak/Banyan tree mesh."""
    rng = np.random.default_rng(seed)

    # 1. TRUNK & BUTTRESS ROOT SYSTEM
    trunk_parts = []
    n_rings = 18
    n_seg = 16
    y_points = np.linspace(0.0, 8.5, n_rings)

    trunk_verts = []
    for i, y in enumerate(y_points):
        t = y / 8.5
        r = 2.2 * (1.0 - t)**1.5 + 0.6 * t

        twist = 0.4 * np.sin(y * 0.8)
        cx = 0.3 * np.sin(y * 0.5)
        cz = 0.3 * np.cos(y * 0.5)

        angles = np.linspace(0, 2 * np.pi, n_seg, endpoint=False) + twist

        # Sprawling buttress root flare near ground
        if y < 2.2:
            flare = 1.0 + 0.50 * (2.2 - y) * (np.sin(5 * angles)**2)
        else:
            flare = 1.0

        r_dist = r * flare + rng.uniform(-0.04, 0.04, n_seg)
        vx = cx + r_dist * np.cos(angles)
        vz = cz + r_dist * np.sin(angles)
        vy = np.full(n_seg, y)

        ring_v = np.column_stack([vx, vy, vz])
        trunk_verts.append(ring_v)

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
    bark_color = np.tile(np.array([75, 48, 26, 255], dtype=np.uint8), (len(trunk_verts), 1))
    trunk_mesh = trimesh.Trimesh(vertices=trunk_verts, faces=trunk_faces, vertex_colors=bark_color, process=False)
    trunk_parts.append(trunk_mesh)

    # 2. MAIN BOUGHS / BRANCHES
    bough_configs = [
        (0.2, 4.5, np.array([3.2, 4.0, 1.2]), 0.55),
        (-0.2, 4.8, np.array([-3.5, 3.8, -1.5]), 0.50),
        (0.1, 5.2, np.array([1.5, 4.2, -3.2]), 0.48),
        (-0.1, 5.5, np.array([-2.0, 4.5, 3.4]), 0.52),
    ]

    for bx, by, bz_dir, b_rad in bough_configs:
        b_length = np.linalg.norm(bz_dir)
        b_dir = bz_dir / b_length

        branch = trimesh.creation.cylinder(radius=b_rad, height=b_length, sections=10)
        up = np.array([0, 1, 0])
        axis = np.cross(up, b_dir)
        axis_len = np.linalg.norm(axis)
        if axis_len > 1e-5:
            axis /= axis_len
            angle = np.arccos(np.dot(up, b_dir))
            mat = trimesh.transformations.rotation_matrix(angle, axis)
            branch.apply_transform(mat)

        branch.vertices += np.array([bx, by, 0.0])
        branch.visual.vertex_colors = np.tile(np.array([82, 52, 28, 255], dtype=np.uint8), (len(branch.vertices), 1))
        trunk_parts.append(branch)

    # 3. ORGANIC LUSH FOLIAGE CANOPY
    foliage_parts = []
    canopy_clusters = [
        # Center dense top
        (0.0, 11.5, 0.0, 4.5, [25, 115, 35, 255]),
        (1.0, 13.0, 0.5, 3.8, [32, 135, 42, 255]),
        (-1.2, 14.0, -0.8, 3.2, [42, 155, 50, 255]),
        (0.0, 15.2, 0.0, 2.5, [55, 175, 62, 255]),
        # Right bough foliage
        (4.5, 9.2, 1.8, 4.2, [28, 122, 38, 255]),
        (5.8, 10.5, 2.2, 3.5, [35, 142, 45, 255]),
        (3.8, 11.2, 0.5, 3.0, [48, 162, 55, 255]),
        # Left bough foliage
        (-4.8, 9.0, -2.0, 4.0, [26, 118, 36, 255]),
        (-6.0, 10.2, -2.5, 3.2, [36, 140, 44, 255]),
        (-4.2, 11.0, -0.8, 3.0, [45, 158, 52, 255]),
        # Back bough foliage
        (2.0, 9.5, -4.5, 4.0, [30, 128, 40, 255]),
        (2.5, 10.8, -5.5, 3.2, [40, 148, 48, 255]),
        # Front bough foliage
        (-2.5, 10.0, 4.8, 4.2, [28, 125, 38, 255]),
        (-3.2, 11.2, 5.8, 3.4, [38, 145, 46, 255]),
        # Fillers
        (2.2, 12.5, -2.2, 3.5, [44, 160, 52, 255]),
        (-2.5, 12.8, 2.0, 3.5, [48, 165, 56, 255]),
    ]

    for cx, cy, cz, radius, color in canopy_clusters:
        ico = trimesh.creation.icosphere(subdivisions=2, radius=radius)
        noise = rng.uniform(-0.25 * radius, 0.25 * radius, ico.vertices.shape)
        ico.vertices += noise
        ico.vertices += np.array([cx, cy, cz])
        ico.visual.vertex_colors = np.tile(np.array(color, dtype=np.uint8), (len(ico.vertices), 1))
        foliage_parts.append(ico)

    tree_mesh = trimesh.util.concatenate(trunk_parts + foliage_parts)
    tree_mesh.unmerge_vertices()
    return tree_mesh


from mpl_toolkits.mplot3d.art3d import Poly3DCollection


def render_single_tree_preview(tree_mesh: trimesh.Trimesh, output: Path) -> None:
    """Render a solid 3D polygon mesh preview image of the single tree."""
    figure = plt.figure(figsize=(12, 12), facecolor="#0c1219")
    axis = figure.add_subplot(111, projection="3d")

    # Draw Ground Plane disc
    g_angles = np.linspace(0, 2 * np.pi, 40)
    g_r = np.linspace(0, 9.0, 15)
    gr_r, gr_a = np.meshgrid(g_r, g_angles)
    gx = gr_r * np.cos(gr_a)
    gz = gr_r * np.sin(gr_a)
    gy = np.full_like(gx, 0.0)
    axis.plot_surface(gx, gz, gy, color="#1b4d20", alpha=0.60, linewidth=0, shade=True)

    # Render SOLID 3D POLYGON MESH using Poly3DCollection
    verts = tree_mesh.vertices
    faces = tree_mesh.faces

    # Face colors from vertex colors
    face_colors = tree_mesh.visual.vertex_colors[faces[:, 0], :3] / 255.0

    # Directional sun light shading for 3D depth
    face_normals = tree_mesh.face_normals
    sun_dir = np.array([0.45, 0.75, 0.48])
    sun_dir /= np.linalg.norm(sun_dir)
    dot = np.clip(np.sum(face_normals * sun_dir, axis=1), 0.0, 1.0)
    light = dot * 0.55 + 0.45
    shaded_colors = np.clip(face_colors * light[:, None], 0.0, 1.0)

    # Map coordinates to Matplotlib 3D axes (X, Z, Y)
    triangles = verts[faces][:, :, [0, 2, 1]]

    poly3d = Poly3DCollection(triangles, facecolors=shaded_colors, edgecolor="none", linewidths=0, alpha=1.0)
    axis.add_collection3d(poly3d)

    axis.set_title("Procedural 3D Ancient Giant Tree (Cổ Thụ) — Solid 3D Mesh", color="white", pad=18, fontsize=14, fontweight="bold")
    axis.set_xlabel("X (m)", color="white", labelpad=8)
    axis.set_ylabel("Z (m)", color="white", labelpad=8)
    axis.set_zlabel("Height Y (m)", color="white", labelpad=8)
    axis.set_xlim(-9, 9)
    axis.set_ylim(-9, 9)
    axis.set_zlim(0, 18)
    axis.view_init(elev=18, azim=-45)
    axis.set_box_aspect((1.0, 1.0, 1.0))
    axis.set_facecolor("#0c1219")
    for pane in (axis.xaxis.pane, axis.yaxis.pane, axis.zaxis.pane):
        pane.set_facecolor((0.05, 0.08, 0.12, 1.0))
    axis.tick_params(colors="white")

    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=200, facecolor=figure.get_facecolor(), bbox_inches="tight")
    plt.close(figure)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate realistic 3D Ancient Tree.")
    parser.add_argument("--preview", type=Path, default=Path("single_tree_preview.png"))
    parser.add_argument("--output", type=Path, default=Path("cave-diving-game/assets/ancient_tree.glb"))
    args = parser.parse_args()

    tree_mesh = create_ultra_realistic_tree(seed=20260804)

    # Render Studio 3D Preview Image
    render_single_tree_preview(tree_mesh, args.preview)

    # Export GLB Model
    scene = trimesh.Scene()
    scene.add_geometry(tree_mesh, node_name="AncientTreeModel", geom_name="AncientTreeModel")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    scene.export(args.output)

    print(f"Rendered studio 3D single tree preview: {args.preview.resolve()}")
    print(f"Exported single tree GLB model: {args.output.resolve()}")


if __name__ == "__main__":
    main()
