"""
Procedural 3D Cave Boulders & Debris Generator (Đá Tảng Đa Mặt Sắc Cạnh & Thảm Đá Vụn Hang Động)

Features:
1. Multi-Faceted Polyhedral Rock Generator: 16 to 24 intersecting cleavage planes, corner chips, notch fractures, solid 3D volumetric thickness, and FastNoiseLite micro erosion.
2. Boulder Pack Export: Generates 10 distinct multi-faceted 3D boulder assets (.obj & .glb) in 'boulder_pack/'.
3. Cave Breakdown Debris Scene: Scatters 180 multi-faceted breakdown rocks across a sloping cave collapse floor.
4. Photorealistic Renderer: Portal sunlight shaft, directional rim lighting, moss/lichen top tints, deep shadow crevices, and wet specular highlights ('rendered_boulders_debris.png').
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


class BoulderGenerator:
    def __init__(self, seed=42):
        """Initialize procedural 3D boulder generator with random seed."""
        self.seed = seed

    def generate_single_boulder(
        self,
        seed=None,
        resolution=64,
        style="random",
        scale=(1.0, 1.0, 1.0),
        roughness=0.04,
    ):
        """
        Generate a single multi-faceted, highly angular 3D cave breakdown boulder mesh.
        :param seed: Random seed for deterministic boulder shape
        :param resolution: Grid resolution (e.g., 64x64x64)
        :param style: Rock shape style ('faceted_block', 'fractured_prism', 'jagged_wedge', 'crystal_polyhedron', 'chipped_boulder', 'random')
        :param scale: (sx, sy, sz) aspect ratio scaling (solid 3D thickness)
        :param roughness: Surface micro noise erosion intensity
        """
        if seed is None:
            seed = self.seed

        rng = np.random.RandomState(seed)
        # Normalize aspect ratios to avoid grid boundary overflow
        s_max = max(scale)
        sx, sy, sz = scale[0] / s_max, scale[1] / s_max, scale[2] / s_max

        x_arr = np.linspace(-1.5, 1.5, resolution, dtype=np.float32)
        y_arr = np.linspace(-1.5, 1.5, resolution, dtype=np.float32)
        z_arr = np.linspace(-1.5, 1.5, resolution, dtype=np.float32)
        X, Y, Z = np.meshgrid(x_arr, y_arr, z_arr, indexing="ij")

        Xc = X / sx
        Yc = Y / sy
        Zc = Z / sz

        # Core 3D Volume Bounds (Ensures solid watertight thickness)
        box_dist = np.maximum.reduce([np.abs(Xc / 1.1), np.abs(Yc / 1.05), np.abs(Zc / 0.95)]) - 0.60

        # Define 16 to 24 multi-faceted cleavage cutting planes
        if style == "faceted_block":
            num_planes = rng.randint(18, 24)
            normals = rng.randn(num_planes, 3).astype(np.float32)
            normals /= np.linalg.norm(normals, axis=1, keepdims=True) + 1e-8
            dists = rng.uniform(0.38, 0.70, size=num_planes).astype(np.float32)

        elif style == "fractured_prism":
            num_planes = rng.randint(16, 22)
            normals = rng.randn(num_planes, 3).astype(np.float32)
            normals /= np.linalg.norm(normals, axis=1, keepdims=True) + 1e-8
            dists = rng.uniform(0.35, 0.68, size=num_planes).astype(np.float32)

        elif style == "jagged_wedge":
            num_planes = rng.randint(15, 20)
            normals = rng.randn(num_planes, 3).astype(np.float32)
            normals /= np.linalg.norm(normals, axis=1, keepdims=True) + 1e-8
            dists = rng.uniform(0.32, 0.65, size=num_planes).astype(np.float32)

        elif style == "crystal_polyhedron":
            num_planes = rng.randint(20, 26)
            normals = rng.randn(num_planes, 3).astype(np.float32)
            normals /= np.linalg.norm(normals, axis=1, keepdims=True) + 1e-8
            dists = rng.uniform(0.40, 0.72, size=num_planes).astype(np.float32)

        else:  # chipped_boulder / random
            num_planes = rng.randint(16, 22)
            normals = rng.randn(num_planes, 3).astype(np.float32)
            normals /= np.linalg.norm(normals, axis=1, keepdims=True) + 1e-8
            dists = rng.uniform(0.35, 0.68, size=num_planes).astype(np.float32)

        # Compute sharp multi-faceted polyhedron Signed Distance Field
        sdf = box_dist
        for i in range(num_planes):
            dot = Xc * normals[i, 0] + Yc * normals[i, 1] + Zc * normals[i, 2]
            plane_d = dot - dists[i]
            sdf = np.maximum(sdf, plane_d)

        # Add 1-2 corner chip notch indentations
        num_chips = rng.randint(1, 3)
        for _ in range(num_chips):
            chip_pos = rng.uniform(-0.5, 0.5, size=3).astype(np.float32)
            chip_radius = float(rng.uniform(0.25, 0.45))
            dist_to_chip = np.sqrt((Xc - chip_pos[0]) ** 2 + (Yc - chip_pos[1]) ** 2 + (Zc - chip_pos[2]) ** 2)
            notch = np.maximum(0.0, chip_radius - dist_to_chip) ** 1.8 * 2.0
            sdf -= notch

        # Micro rock noise for stone texture
        fn = FastNoiseLite(seed)
        fn.noise_type = NoiseType.NoiseType_Perlin
        fn.frequency = 3.0
        fn.fractal_type = FractalType.FractalType_FBm
        fn.fractal_octaves = 3

        coords = np.ascontiguousarray(
            np.stack([(X * 3.0).ravel(), (Y * 3.0).ravel(), (Z * 3.0).ravel()]),
            dtype=np.float32,
        )
        noise_3d = fn.gen_from_coords(coords).reshape(
            (resolution, resolution, resolution)
        )

        sdf += noise_3d * roughness

        # Marching Cubes Mesh Extraction
        verts, faces, normals_mesh, _ = marching_cubes(
            sdf,
            level=0.0,
            spacing=(2.8 / resolution, 2.8 / resolution, 2.8 / resolution),
            allow_degenerate=False,
        )
        verts -= np.mean(verts, axis=0)

        mesh = trimesh.Trimesh(
            vertices=verts,
            faces=faces,
            vertex_normals=normals_mesh,
            process=True,
        )
        return mesh

    def generate_boulder_pack(self, count=10, output_dir="boulder_pack"):
        """Generate a library of 10 multi-faceted 3D boulder assets (.obj & .glb)."""
        os.makedirs(output_dir, exist_ok=True)
        print(f"\nGenerating 3D Multi-Faceted Boulder Asset Pack ({count} variations) in '{output_dir}/'...")
        t0 = time.time()

        styles = [
            "faceted_block", "fractured_prism", "jagged_wedge", "crystal_polyhedron", "chipped_boulder",
            "faceted_block", "fractured_prism", "jagged_wedge", "crystal_polyhedron", "chipped_boulder"
        ]

        boulder_meshes = []
        for i in range(1, count + 1):
            seed = self.seed + i * 37
            rng = np.random.RandomState(seed)
            style = styles[i - 1]

            # Aspect ratio scale with solid 3D depth (no paper-thin plates)
            scale = (
                rng.uniform(1.0, 1.45),
                rng.uniform(0.85, 1.35),
                rng.uniform(0.75, 1.25),
            )

            mesh = self.generate_single_boulder(
                seed=seed,
                resolution=64,
                style=style,
                scale=scale,
                roughness=float(rng.uniform(0.03, 0.06)),
            )
            boulder_meshes.append(mesh)

            num_str = f"{i:02d}"
            obj_path = os.path.join(output_dir, f"boulder_{num_str}.obj")
            glb_path = os.path.join(output_dir, f"boulder_{num_str}.glb")

            mesh.export(obj_path)
            mesh.export(glb_path)
            print(f"  [Asset #{num_str}] Saved boulder_{num_str}.glb (Style: {style}, {len(mesh.vertices):,} Vertices)")

        dt = time.time() - t0
        print(f"Multi-Faceted Boulder Pack generated in {dt:.2f}s!")
        return boulder_meshes

    def generate_cave_breakdown_scene(self, seed=42, num_boulders=180):
        """
        Generate a complete 3D Cave Collapse breakdown scene with 180 multi-faceted boulders.
        """
        print(f"\nGenerating 3D Cave Breakdown & Debris Scene ({num_boulders} Multi-Faceted Boulders)...")
        t0 = time.time()

        rng = np.random.RandomState(seed)

        # 1. Base Cave Floor & Collapse Slope Terrain
        nx, ny, nz = 160, 160, 100
        x_arr = np.linspace(0, 80, nx, dtype=np.float32)
        y_arr = np.linspace(0, 80, ny, dtype=np.float32)
        z_arr = np.linspace(0, 50, nz, dtype=np.float32)
        X, Y, Z = np.meshgrid(x_arr, y_arr, z_arr, indexing="ij")

        dist_from_left = X / 80.0
        floor_z = 6.0 + 32.0 * (dist_from_left ** 1.6) + 3.0 * np.sin(X * 0.1) * np.cos(Y * 0.1)
        ceiling_z = 45.0 - 15.0 * ((X - 40.0) / 40.0) ** 2 + 5.0 * np.sin(Y * 0.08)

        cave_hollow = (Z >= floor_z) & (Z <= ceiling_z)
        cave_sdf = np.ascontiguousarray(
            np.where(cave_hollow, -1.0, 1.0), dtype=np.float32
        )

        verts_cave, faces_cave, normals_cave, _ = marching_cubes(
            cave_sdf,
            level=0.0,
            spacing=(80.0 / nx, 80.0 / ny, 50.0 / nz),
            allow_degenerate=False,
        )
        mesh_cave = trimesh.Trimesh(
            vertices=verts_cave,
            faces=faces_cave,
            vertex_normals=normals_cave,
            process=True,
        )

        # 2. Scatter Multi-Faceted Boulders & Debris onto the Cave Floor Slope
        combined_meshes = [mesh_cave]
        boulder_instances = []
        styles = ["faceted_block", "fractured_prism", "jagged_wedge", "crystal_polyhedron", "chipped_boulder"]

        for i in range(num_boulders):
            b_seed = seed + i * 43
            b_rng = np.random.RandomState(b_seed)

            bias = b_rng.power(1.6)
            bx = 10.0 + 65.0 * bias
            by = b_rng.uniform(10.0, 70.0)
            bz = 6.0 + 32.0 * ((bx / 80.0) ** 1.6) + b_rng.uniform(-0.5, 1.5)

            size_type = b_rng.choice(["large", "medium", "small"], p=[0.15, 0.40, 0.45])
            if size_type == "large":
                scale_val = b_rng.uniform(2.5, 5.0)
            elif size_type == "medium":
                scale_val = b_rng.uniform(1.0, 2.2)
            else:
                scale_val = b_rng.uniform(0.3, 0.8)

            style = b_rng.choice(styles)
            aspect = (
                b_rng.uniform(1.0, 1.45),
                b_rng.uniform(0.85, 1.35),
                b_rng.uniform(0.75, 1.25),
            )

            b_mesh = self.generate_single_boulder(
                seed=b_seed,
                resolution=32 if size_type == "small" else 48,
                style=style,
                scale=aspect,
                roughness=float(b_rng.uniform(0.03, 0.06)),
            )

            b_mesh.apply_scale(scale_val)
            rot_matrix = trimesh.transformations.random_rotation_matrix(b_rng.rand(3))
            b_mesh.apply_transform(rot_matrix)
            b_mesh.apply_translation([bx, by, bz])

            combined_meshes.append(b_mesh)
            boulder_instances.append({
                "mesh": b_mesh,
                "center": np.array([bx, by, bz]),
                "scale": scale_val,
                "size_type": size_type,
            })

        print(f"Combining {len(combined_meshes):,} mesh components into full scene...")
        scene_mesh = trimesh.util.concatenate(combined_meshes)

        dt = time.time() - t0
        print(f"Cave Breakdown Scene generated in {dt:.2f}s! ({len(scene_mesh.vertices):,} Vertices)")
        return scene_mesh, boulder_instances, mesh_cave

    def render_photorealistic_scene(
        self,
        scene_mesh,
        boulder_instances,
        mesh_cave,
        output_path="rendered_boulders_debris.png",
    ):
        """
        Render photorealistic 3D Cave Breakdown Scene with Portal Sunlight,
        Mossy Rock Top Tints, Facet Speculars, and Deep Shadow Crevices.
        """
        print(f"Rendering photorealistic Cave Boulders Scene to '{output_path}'...")
        t0 = time.time()

        scene_boulders_mesh = trimesh.util.concatenate([b["mesh"] for b in boulder_instances])

        verts = scene_boulders_mesh.vertices
        faces = scene_boulders_mesh.faces
        fnormals = scene_boulders_mesh.face_normals
        fcenters = scene_boulders_mesh.triangles_center

        # Lighting Rig
        L_sun = np.array([-0.65, 0.40, -0.65], dtype=np.float32)
        L_sun /= np.linalg.norm(L_sun)

        L_bounce = np.array([0.2, 0.1, 0.9], dtype=np.float32)
        L_bounce /= np.linalg.norm(L_bounce)

        L_fill = np.array([0.5, -0.5, 0.5], dtype=np.float32)
        L_fill /= np.linalg.norm(L_fill)

        diff_sun = np.maximum(0.0, np.dot(fnormals, -L_sun))
        diff_bounce = np.maximum(0.0, np.dot(fnormals, L_bounce))
        diff_fill = np.maximum(0.0, np.dot(fnormals, L_fill))

        portal_proximity = np.clip((fcenters[:, 0] - 10.0) / 65.0, 0.0, 1.0) ** 1.3
        sun_intensity = diff_sun * (0.25 + 1.5 * portal_proximity)

        shadow_under = np.maximum(0.0, -fnormals[:, 2])
        ao = np.clip(0.35 + 0.65 * (fcenters[:, 2] / 40.0) - 0.35 * shadow_under, 0.15, 1.0)

        view_dir = np.array([-0.8, -0.5, 0.35], dtype=np.float32)
        view_dir /= np.linalg.norm(view_dir)

        H_sun = (-L_sun + view_dir)
        H_sun /= np.linalg.norm(H_sun)
        specular_sun = np.power(np.maximum(0.0, np.dot(fnormals, H_sun)), 20) * sun_intensity

        top_facing = np.maximum(0.0, fnormals[:, 2])
        moss_mask = np.clip(top_facing * (0.25 + 0.75 * portal_proximity) * (1.0 - shadow_under), 0.0, 1.0) ** 1.6

        c_rock_base = np.array([0.76, 0.62, 0.48], dtype=np.float32)
        c_rock_dark = np.array([0.16, 0.12, 0.09], dtype=np.float32)
        c_sun_light = np.array([1.00, 0.94, 0.82], dtype=np.float32)
        c_moss = np.array([0.45, 0.58, 0.24], dtype=np.float32)
        c_spec = np.array([1.00, 0.98, 0.94], dtype=np.float32)

        face_colors = np.zeros((len(faces), 3), dtype=np.float32)
        stone_col = c_rock_base[None, :] * (1.0 - moss_mask[:, None] * 0.55) + c_moss[None, :] * (moss_mask[:, None] * 0.55)

        for i in range(3):
            col = (
                stone_col[:, i] * (0.22 * ao + 0.65 * sun_intensity * c_sun_light[i] + 0.18 * diff_fill) +
                stone_col[:, i] * diff_bounce * 0.15 +
                c_spec[i] * specular_sun * 0.45 -
                c_rock_dark[i] * shadow_under * 0.40
            )
            face_colors[:, i] = np.clip(col, 0.0, 1.0)

        fig = plt.figure(figsize=(14, 10), facecolor="#0a0807")
        ax = fig.add_subplot(111, projection="3d", facecolor="#0a0807")

        mesh_poly = Poly3DCollection(
            verts[faces],
            facecolors=face_colors,
            linewidths=0,
            antialiased=False,
        )
        ax.add_collection3d(mesh_poly)

        ax.set_xlim(8, 72)
        ax.set_ylim(8, 72)
        ax.set_zlim(0, 42)

        ax.set_box_aspect((1.5, 1.0, 0.70))

        ax.axis("off")
        ax.view_init(elev=20, azim=-125)

        plt.tight_layout()
        plt.savefig(
            output_path,
            dpi=220,
            facecolor="#0a0807",
            bbox_inches="tight",
            pad_inches=0,
        )
        plt.close(fig)

        try:
            img = Image.open(output_path).convert("RGB")
            w, h = img.size
            Y_grid, X_grid = np.ogrid[:h, :w]
            portal_x, portal_y = int(w * 0.82), int(h * 0.22)
            dist_from_portal = np.sqrt((X_grid - portal_x)**2 + (Y_grid - portal_y)**2)
            bloom_mask = np.clip(1.0 - (dist_from_portal / (w * 0.45)), 0.0, 1.0) ** 2.0

            img_np = np.array(img, dtype=np.float32)
            bloom_col = np.array([255, 235, 190], dtype=np.float32)
            img_np += bloom_col[None, None, :] * bloom_mask[:, :, None] * 0.30
            img_final = Image.fromarray(np.clip(img_np, 0, 255).astype(np.uint8))
            img_final.save(output_path)
        except Exception as e:
            print(f"Post-processing note: {e}")

        dt = time.time() - t0
        print(f"Photorealistic Cave Boulders Scene saved to '{output_path}' in {dt:.3f}s!")


def main():
    print("=================================================================")
    print(" Procedural 3D Cave Boulders & Debris Generator (Multi-Faceted)")
    print(" (Đá Tảng Đa Mặt Sắc Cạnh & Thảm Đá Vụn Sụt Lở Hang Động)")
    print("=================================================================")

    generator = BoulderGenerator(seed=1337)

    # 1. Generate 3D Boulder Asset Pack (10 multi-faceted boulder models for Godot)
    boulder_pack_dir = "boulder_pack"
    generator.generate_boulder_pack(count=10, output_dir=boulder_pack_dir)

    # 2. Generate Full Cave Breakdown Scene with 180 scattered multi-faceted boulders
    scene_mesh, boulder_instances, mesh_cave = generator.generate_cave_breakdown_scene(
        seed=1337, num_boulders=180
    )

    # 3. Render Photorealistic Image
    render_path = "rendered_boulders_debris.png"
    generator.render_photorealistic_scene(
        scene_mesh, boulder_instances, mesh_cave, output_path=render_path
    )

    # 4. Export Complete 3D Breakdown Scene Mesh (.obj & .glb)
    obj_scene = "cave_boulders_debris.obj"
    glb_scene = "cave_boulders_debris.glb"

    print(f"Exporting 3D Cave Breakdown Scene to OBJ: '{obj_scene}'...")
    scene_mesh.export(obj_scene)

    print(f"Exporting 3D Cave Breakdown Scene to GLB: '{glb_scene}'...")
    scene_mesh.export(glb_scene)

    print("\nCave Boulders & Debris generation complete!")
    print(f"Output preview image: {render_path}")
    print(f"Output 3D scene models: {obj_scene}, {glb_scene}")
    print(f"Output 3D asset pack directory: {boulder_pack_dir}/ (10 GLB models)")


if __name__ == "__main__":
    main()
