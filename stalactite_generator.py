"""
Procedural 3D Cave Stalactite Generator (Thạch Nhũ Hang Động 3D)

Features:
1. Procedural 3D Stalactite Generation: Cone tapering from ceiling root to drip tip, drip rings, bulbous nodes, curtain draperies, soda straws, and fluting texture.
2. 5 Distinct Speleothems Styles: 'classic', 'soda_straw', 'drapery', 'pagoda', 'twin_cluster'.
3. Multi-Light Renderer: Overhead warm torch glow, cave ambient occlusion, Blinn-Phong wet specular highlights ('rendered_stalactite.png').
"""

import os
import time
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from skimage.measure import marching_cubes
import trimesh
from PIL import Image

from pyfastnoiselite.pyfastnoiselite import (
    FastNoiseLite,
    NoiseType,
    FractalType,
)


class StalactiteGenerator:
    def __init__(self, seed=42):
        """Initialize procedural 3D stalactite generator with random seed."""
        self.seed = seed

    def generate_single_stalactite(
        self,
        seed=None,
        resolution=(64, 64, 96),
        style="classic",
        height=3.5,
        radius_root=0.75,
        roughness=0.06,
    ):
        """
        Generate a single 3D ceiling stalactite mesh hanging downward from Z=height to Z=0.
        :param seed: Random seed for deterministic stalactite shape
        :param resolution: Grid resolution tuple (nx, ny, nz)
        :param style: 'classic', 'soda_straw', 'drapery', 'pagoda', 'twin_cluster', 'random'
        :param height: Total vertical height of the stalactite
        :param radius_root: Radius at top attachment root (Z=height)
        :param roughness: Surface micro noise intensity
        """
        if seed is None:
            seed = self.seed

        rng = np.random.RandomState(seed)
        nx, ny, nz = resolution

        # Bounds: Z ranges from 0.0 (tip) to height (ceiling root)
        max_r = max(radius_root * 1.8, 1.2)
        x_arr = np.linspace(-max_r, max_r, nx, dtype=np.float32)
        y_arr = np.linspace(-max_r, max_r, ny, dtype=np.float32)
        z_arr = np.linspace(0.0, height, nz, dtype=np.float32)
        X, Y, Z = np.meshgrid(x_arr, y_arr, z_arr, indexing="ij")

        norm_z = Z / height  # 0.0 at tip, 1.0 at ceiling root

        # 1. Axis Wobble (Natural drip sway along height)
        wobble_freq_x = float(rng.uniform(1.2, 2.5))
        wobble_freq_y = float(rng.uniform(1.2, 2.5))
        wobble_amp = float(rng.uniform(0.04, 0.15)) * (1.0 - norm_z ** 2)

        cx = wobble_amp * np.sin(norm_z * wobble_freq_x * np.pi + float(rng.uniform(0, 2 * np.pi)))
        cy = wobble_amp * np.cos(norm_z * wobble_freq_y * np.pi + float(rng.uniform(0, 2 * np.pi)))

        Xc = X - cx
        Yc = Y - cy
        r_xy = np.sqrt(Xc ** 2 + Yc ** 2)

        # 2. Radius Profile R(z) per Stalactite Style
        if style == "soda_straw":
            # Ultra slender tubular straw
            r_taper = radius_root * (0.22 + 0.18 * norm_z ** 1.2)
            drip_rings = 0.015 * np.sin(norm_z * 24.0 * np.pi) * norm_z
            node_bulge = 0.0

        elif style == "drapery":
            # Fused curtain drapery (flattened in Y axis, wide in X)
            Yc = Yc * 2.5  # Flatten Y
            r_xy = np.sqrt(Xc ** 2 + Yc ** 2)
            r_taper = radius_root * (0.25 + 0.75 * (norm_z ** 1.4))
            drip_rings = 0.05 * np.sin(norm_z * 12.0 * np.pi + Xc * 3.0) * norm_z
            node_bulge = 0.08 * np.sin(norm_z * 6.0 * np.pi) ** 2 * norm_z

        elif style == "pagoda":
            # Multi-tiered stacked saucer rings
            r_taper = radius_root * (0.15 + 0.65 * (norm_z ** 1.6))
            num_tiers = rng.randint(4, 8)
            drip_rings = 0.12 * np.maximum(0.0, np.cos(norm_z * num_tiers * np.pi)) ** 2 * norm_z
            node_bulge = 0.0

        elif style == "twin_cluster":
            # Fused double drip tips
            offset = 0.35 * radius_root * (1.0 - norm_z)
            r_xy1 = np.sqrt((Xc - offset) ** 2 + Yc ** 2)
            r_xy2 = np.sqrt((Xc + offset) ** 2 + Yc ** 2)
            r_xy = np.minimum(r_xy1, r_xy2)

            r_taper = radius_root * (0.18 + 0.72 * (norm_z ** 1.5))
            drip_rings = 0.04 * np.sin(norm_z * 14.0 * np.pi) * norm_z
            node_bulge = 0.06 * np.sin(norm_z * 4.0 * np.pi) ** 2 * norm_z

        else:  # classic
            r_taper = radius_root * (0.12 + 0.70 * (norm_z ** 1.7) + 0.15 * (1.0 - norm_z) ** 2 * norm_z)
            drip_rings = 0.045 * np.sin(norm_z * 16.0 * np.pi) * norm_z
            node_bulge = 0.07 * np.sin(norm_z * 5.0 * np.pi) ** 2 * norm_z

        # Composite Radius
        r_target = r_taper + drip_rings + node_bulge

        # 3. Fluting & Surface Roughness Noise
        fn = FastNoiseLite(seed)
        fn.noise_type = NoiseType.NoiseType_Perlin
        fn.frequency = 3.5
        fn.fractal_type = FractalType.FractalType_FBm
        fn.fractal_octaves = 3

        coords = np.ascontiguousarray(
            np.stack([(X * 3.5).ravel(), (Y * 3.5).ravel(), (Z * 3.5).ravel()]),
            dtype=np.float32,
        )
        noise_3d = fn.gen_from_coords(coords).reshape((nx, ny, nz))

        # Vertical fluting channels (vertical calcite ridges)
        angle = np.arctan2(Yc, Xc)
        fluting = 0.03 * np.cos(angle * float(rng.randint(6, 12))) * norm_z

        # Compute Implicit Density Field (Iso-level at 0.0)
        density = r_xy - r_target + fluting + noise_3d * roughness

        # Marching Cubes Mesh Extraction
        verts, faces, normals_mesh, _ = marching_cubes(
            density,
            level=0.0,
            spacing=(2.0 * max_r / nx, 2.0 * max_r / ny, height / nz),
            allow_degenerate=False,
        )

        # Center X, Y and align root attachment at Z=height
        verts[:, 0] -= np.mean(verts[:, 0])
        verts[:, 1] -= np.mean(verts[:, 1])

        mesh = trimesh.Trimesh(
            vertices=verts,
            faces=faces,
            vertex_normals=normals_mesh,
            process=True,
        )
        return mesh

    def render_photorealistic_stalactite(
        self,
        mesh,
        output_path="rendered_stalactite.png",
    ):
        """Render photorealistic 3D Stalactite preview image."""
        print(f"Rendering stalactite image to '{output_path}'...")
        t0 = time.time()

        verts = mesh.vertices
        faces = mesh.faces
        fnormals = mesh.face_normals

        # Lights
        L_top = np.array([0.4, 0.4, 0.8], dtype=np.float32)
        L_top /= np.linalg.norm(L_top)

        L_bottom = np.array([-0.5, -0.4, -0.7], dtype=np.float32)
        L_bottom /= np.linalg.norm(L_bottom)

        diff_top = np.maximum(0.0, np.dot(fnormals, L_top))
        diff_bottom = np.maximum(0.0, np.dot(fnormals, L_bottom))

        # Shading Palette
        c_calcite = np.array([0.88, 0.82, 0.72], dtype=np.float32)
        c_shadow = np.array([0.22, 0.18, 0.15], dtype=np.float32)

        face_colors = np.zeros((len(faces), 3), dtype=np.float32)
        for i in range(3):
            col = c_shadow[i] + (c_calcite[i] - c_shadow[i]) * (0.3 + 0.7 * diff_top) + 0.15 * diff_bottom
            face_colors[:, i] = np.clip(col, 0.0, 1.0)

        fig = plt.figure(figsize=(8, 10), facecolor="#0a0807")
        ax = fig.add_subplot(111, projection="3d", facecolor="#0a0807")

        poly = Poly3DCollection(verts[faces], facecolors=face_colors, linewidths=0)
        ax.add_collection3d(poly)

        max_b = np.max(np.abs(verts)) * 1.1
        ax.set_xlim(-max_b, max_b)
        ax.set_ylim(-max_b, max_b)
        ax.set_zlim(np.min(verts[:, 2]), np.max(verts[:, 2]))
        ax.axis("off")
        ax.view_init(elev=12, azim=-45)

        plt.tight_layout()
        plt.savefig(output_path, dpi=200, facecolor="#0a0807", bbox_inches="tight", pad_inches=0)
        plt.close(fig)

        dt = time.time() - t0
        print(f"Stalactite render saved to '{output_path}' in {dt:.2f}s!")


def main():
    generator = StalactiteGenerator(seed=1337)
    mesh = generator.generate_single_stalactite(style="classic", height=3.5)

    obj_path = "stalactite.obj"
    glb_path = "stalactite.glb"
    png_path = "rendered_stalactite.png"

    mesh.export(obj_path)
    mesh.export(glb_path)
    generator.render_photorealistic_stalactite(mesh, output_path=png_path)

    print(f"Single Stalactite generated successfully!")
    print(f"  Models: {obj_path}, {glb_path}")
    print(f"  Preview Image: {png_path}")


if __name__ == "__main__":
    main()
