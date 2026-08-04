"""
Procedural 3D Stalagmite Generator & Photorealistic Renderer (Măng Đá & Cột Thạch Nhũ)

Features:
1. Multi-column stalagmite cluster geometry with fused base and secondary columns.
2. Stacked ring / scalloped plate drip profiles (nấc thạch nhũ).
3. Height-dependent bulbous node swellings & axis wobble.
4. Vertical dripping striations / fluting + FastNoiseLite surface micro-roughness.
5. Advanced 3D Mesh Extraction via Marching Cubes (exporting .obj and .glb).
6. Photorealistic Cave Renderer with multi-light setup (torch glow, overhead key light),
   Ambient Occlusion (crevice darkening), limestone material coloring, and wet specular gloss.
"""

import time
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from skimage.measure import marching_cubes
import trimesh
from PIL import Image, ImageFilter

from pyfastnoiselite.pyfastnoiselite import (
    FastNoiseLite,
    NoiseType,
    FractalType,
)


class StalagmiteGenerator:
    def __init__(self, grid_shape=(160, 160, 240), seed=42, style="default"):
        """
        Initialize stalagmite generator with 3D grid resolution, seed, and style.
        :param grid_shape: (nx, ny, nz) voxel dimensions
        :param seed: Random seed for deterministic procedural generation
        :param style: Generator style ('default', 'single', 'twin', 'cluster', 'pagoda', 'dwarf', 'needle', 'random')
        """
        self.nx, self.ny, self.nz = grid_shape
        self.seed = seed
        self.style = style
        self._init_noises()

    def _init_noises(self):
        """Initialize FastNoiseLite 3D/2D noise instances."""
        # Micro roughness for limestone surface texture
        self.roughness_noise = FastNoiseLite(self.seed)
        self.roughness_noise.noise_type = NoiseType.NoiseType_Perlin
        self.roughness_noise.frequency = 0.07
        self.roughness_noise.fractal_type = FractalType.FractalType_FBm
        self.roughness_noise.fractal_octaves = 3

        # Macro noise for ring phase perturbation
        self.ring_noise = FastNoiseLite(self.seed + 101)
        self.ring_noise.noise_type = NoiseType.NoiseType_OpenSimplex2
        self.ring_noise.frequency = 0.03

    def _get_pillars_config(self):
        """Generate pillar configuration based on generator style and random seed."""
        if self.style == "default":
            return [
                {
                    "cx": self.nx * 0.47,
                    "cy": self.ny * 0.48,
                    "r_base": 15.0 * (self.nx / 160.0),
                    "h_max": self.nz * 0.94,
                    "wobble_amp": 2.2,
                    "ring_freq": 0.24,
                    "ring_amp": 7.5,
                    "taper_exp": 0.35,
                    "type": "main",
                },
                {
                    "cx": self.nx * 0.58,
                    "cy": self.ny * 0.44,
                    "r_base": 13.0 * (self.nx / 160.0),
                    "h_max": self.nz * 0.65,
                    "wobble_amp": 1.8,
                    "ring_freq": 0.28,
                    "ring_amp": 5.5,
                    "taper_exp": 0.45,
                    "type": "secondary",
                },
                {
                    "cx": self.nx * 0.41,
                    "cy": self.ny * 0.54,
                    "r_base": 11.0 * (self.nx / 160.0),
                    "h_max": self.nz * 0.82,
                    "wobble_amp": 1.5,
                    "ring_freq": 0.22,
                    "ring_amp": 4.5,
                    "taper_exp": 0.38,
                    "type": "back",
                },
                {
                    "cx": self.nx * 0.44,
                    "cy": self.ny * 0.38,
                    "r_base": 14.0 * (self.nx / 160.0),
                    "h_max": self.nz * 0.30,
                    "wobble_amp": 0.5,
                    "ring_freq": 0.35,
                    "ring_amp": 3.5,
                    "taper_exp": 0.60,
                    "type": "base",
                },
            ]

        rng = np.random.RandomState(self.seed)
        scale_r = self.nx / 160.0
        pillars = []

        if self.style == "single":
            pillars.append({
                "cx": self.nx * 0.50,
                "cy": self.ny * 0.50,
                "r_base": float(rng.uniform(14.0, 18.0) * scale_r),
                "h_max": self.nz * float(rng.uniform(0.88, 0.96)),
                "wobble_amp": float(rng.uniform(1.5, 3.0)),
                "ring_freq": float(rng.uniform(0.20, 0.30)),
                "ring_amp": float(rng.uniform(6.0, 9.0)),
                "taper_exp": float(rng.uniform(0.30, 0.45)),
                "type": "main",
            })
        elif self.style == "twin":
            pillars.append({
                "cx": self.nx * 0.44,
                "cy": self.ny * 0.48,
                "r_base": float(rng.uniform(13.0, 16.0) * scale_r),
                "h_max": self.nz * float(rng.uniform(0.85, 0.95)),
                "wobble_amp": float(rng.uniform(1.8, 2.5)),
                "ring_freq": float(rng.uniform(0.22, 0.28)),
                "ring_amp": float(rng.uniform(5.5, 7.5)),
                "taper_exp": 0.38,
                "type": "main",
            })
            pillars.append({
                "cx": self.nx * 0.56,
                "cy": self.ny * 0.50,
                "r_base": float(rng.uniform(12.0, 15.0) * scale_r),
                "h_max": self.nz * float(rng.uniform(0.78, 0.88)),
                "wobble_amp": float(rng.uniform(1.5, 2.2)),
                "ring_freq": float(rng.uniform(0.24, 0.30)),
                "ring_amp": float(rng.uniform(5.0, 7.0)),
                "taper_exp": 0.40,
                "type": "secondary",
            })
        elif self.style == "pagoda":
            pillars.append({
                "cx": self.nx * 0.50,
                "cy": self.ny * 0.50,
                "r_base": float(rng.uniform(18.0, 24.0) * scale_r),
                "h_max": self.nz * float(rng.uniform(0.85, 0.95)),
                "wobble_amp": float(rng.uniform(1.0, 2.0)),
                "ring_freq": float(rng.uniform(0.18, 0.25)),
                "ring_amp": float(rng.uniform(9.0, 13.0)),
                "taper_exp": 0.50,
                "type": "main",
            })
        elif self.style == "dwarf":
            pillars.append({
                "cx": self.nx * 0.50,
                "cy": self.ny * 0.50,
                "r_base": float(rng.uniform(22.0, 28.0) * scale_r),
                "h_max": self.nz * float(rng.uniform(0.50, 0.65)),
                "wobble_amp": 1.0,
                "ring_freq": float(rng.uniform(0.30, 0.40)),
                "ring_amp": float(rng.uniform(6.0, 8.5)),
                "taper_exp": 0.65,
                "type": "main",
            })
        elif self.style == "needle":
            pillars.append({
                "cx": self.nx * 0.50,
                "cy": self.ny * 0.50,
                "r_base": float(rng.uniform(8.0, 11.0) * scale_r),
                "h_max": self.nz * float(rng.uniform(0.90, 0.97)),
                "wobble_amp": float(rng.uniform(2.5, 4.0)),
                "ring_freq": float(rng.uniform(0.25, 0.35)),
                "ring_amp": float(rng.uniform(3.0, 5.0)),
                "taper_exp": 0.28,
                "type": "main",
            })
        else:  # cluster / random
            num_p = rng.randint(3, 6)
            for idx in range(num_p):
                if idx == 0:
                    cx = self.nx * rng.uniform(0.45, 0.52)
                    cy = self.ny * rng.uniform(0.45, 0.52)
                    r_b = rng.uniform(13.0, 17.0) * scale_r
                    h_m = self.nz * rng.uniform(0.85, 0.95)
                    p_type = "main"
                else:
                    angle = rng.uniform(0, 2 * np.pi)
                    dist = rng.uniform(8.0, 20.0) * scale_r
                    cx = self.nx * 0.50 + dist * np.cos(angle)
                    cy = self.ny * 0.50 + dist * np.sin(angle)
                    r_b = rng.uniform(8.0, 13.0) * scale_r
                    h_m = self.nz * rng.uniform(0.30, 0.80)
                    p_type = "secondary" if idx == 1 else "base"

                pillars.append({
                    "cx": float(cx),
                    "cy": float(cy),
                    "r_base": float(r_b),
                    "h_max": float(h_m),
                    "wobble_amp": float(rng.uniform(1.2, 3.0)),
                    "ring_freq": float(rng.uniform(0.20, 0.35)),
                    "ring_amp": float(rng.uniform(4.0, 8.0)),
                    "taper_exp": float(rng.uniform(0.35, 0.55)),
                    "type": p_type,
                })
        return pillars

    def generate_density_field(self):
        """
        Build 3D voxel density field for realistic stalagmites.
        Positive (>0) = Solid stone, Negative (<0) = Air space.
        """
        print(f"Generating 3D voxel density grid [{self.nx}x{self.ny}x{self.nz}] (Style: {self.style})...")
        t0 = time.time()

        # Coordinate grid
        x_arr = np.arange(self.nx, dtype=np.float32)
        y_arr = np.arange(self.ny, dtype=np.float32)
        z_arr = np.arange(self.nz, dtype=np.float32)
        X, Y, Z = np.meshgrid(x_arr, y_arr, z_arr, indexing="ij")

        # 3D Micro Roughness Noise
        coords = np.ascontiguousarray(
            np.stack([X.ravel(), Y.ravel(), Z.ravel()]), dtype=np.float32
        )
        noise_3d = self.roughness_noise.gen_from_coords(coords).reshape(
            (self.nx, self.ny, self.nz)
        )

        # 2D Macro noise for ring distortion
        coords_2d = np.ascontiguousarray(
            np.stack([X[:, :, 0].ravel(), Y[:, :, 0].ravel()]), dtype=np.float32
        )
        noise_2d = self.ring_noise.gen_from_coords(coords_2d).reshape(
            (self.nx, self.ny)
        )[:, :, None]

        # Get pillar configurations based on style
        pillars = self._get_pillars_config()

        combined_density = np.full((self.nx, self.ny, self.nz), -100.0, dtype=np.float32)

        for p in pillars:
            cx0, cy0 = p["cx"], p["cy"]
            r_base = p["r_base"]
            h_max = p["h_max"]

            # Organic axis wobble along height Z
            wobble_x = p["wobble_amp"] * np.sin(0.04 * Z + 0.3) + p["wobble_amp"] * 0.4 * np.cos(0.09 * Z)
            wobble_y = p["wobble_amp"] * np.cos(0.035 * Z - 0.2) + p["wobble_amp"] * 0.4 * np.sin(0.11 * Z)

            cx = cx0 + wobble_x
            cy = cy0 + wobble_y

            dx = X - cx
            dy = Y - cy
            dist_xy = np.sqrt(dx * dx + dy * dy)
            angle = np.arctan2(dy, dx)

            # Height ratio [0.0, 1.0]
            z_norm = np.clip(Z / h_max, 0.0, 1.0)

            # 1. Base flare (slight flare near floor)
            base_flare = 1.0 + 0.9 * np.exp(-Z / 22.0)

            # 2. Bulbous swelling nodes & knobs along height
            node_bulbs = (
                0.38 * np.sin(0.032 * Z)
                + 0.28 * np.sin(0.075 * Z + 1.1)
                + 0.20 * np.cos(0.016 * Z - 0.4)
            )
            
            if p["type"] == "secondary":
                # Add distinctive bulbous knob head near top of secondary column
                knob_head = 0.45 * np.exp(-((Z - h_max * 0.82) ** 2) / 120.0)
                node_bulbs += knob_head

            # 3. Stacked Saucer Rings / Scalloped Aprons (Nấc thạch nhũ xếp tầng)
            # Sharp overhang ledges underneath, horizontal expanding plates
            ring_phase = p["ring_freq"] * Z + noise_2d * 1.0
            ring_wave = np.power(0.5 + 0.5 * np.sin(ring_phase), 1.6)
            ring_shelf = 0.6 * np.power(0.5 + 0.5 * np.cos(ring_phase * 0.5 + 0.5), 2.2)
            rings = p["ring_amp"] * (ring_wave + ring_shelf)

            # 4. Vertical Dripping Striations / Radial Fluting (Softened so horizontal rings stand out)
            fluting = (
                0.7 * np.cos(7 * angle + 0.03 * Z)
                + 0.4 * np.cos(12 * angle - 0.04 * Z)
                + 0.2 * np.sin(18 * angle + 0.06 * Z)
            )

            # 5. Top tip taper
            tip_taper = np.clip((1.0 - z_norm) ** p["taper_exp"], 0.0, 1.0)

            # Calculate total local radius profile
            target_radius = (
                r_base * base_flare * (1.0 + node_bulbs) + rings + fluting
            ) * tip_taper

            # Pillar signed distance field
            d_p = target_radius - dist_xy

            # Cut off above max height with rounded tip
            above_h = np.maximum(0.0, Z - h_max)
            d_p = d_p - 1.8 * above_h

            # Soft smooth-union (log-sum-exp blend)
            k = 0.30
            combined_density = (1.0 / k) * np.log(
                np.exp(np.clip(k * combined_density, -50, 50))
                + np.exp(np.clip(k * d_p, -50, 50))
            )

        # Ground floor stone layer (small base region)
        floor_dist = np.sqrt((X - self.nx * 0.47)**2 + (Y - self.ny * 0.48)**2)
        floor_layer = 2.0 - Z * 0.22 - floor_dist * 0.035 + noise_3d * 1.0
        combined_density = np.maximum(combined_density, floor_layer)

        # Composite density with micro surface roughness
        final_density = combined_density + noise_3d * 1.4

        dt = time.time() - t0
        print(f"3D Voxel density field created in {dt:.3f} seconds!")
        return final_density

    def extract_mesh(self, density_field, iso_level=0.0):
        """Extract 3D triangle mesh using Marching Cubes."""
        print("Extracting 3D mesh via skimage.measure.marching_cubes...")
        t0 = time.time()

        verts, faces, normals, values = marching_cubes(
            density_field,
            level=iso_level,
            spacing=(1.0, 1.0, 1.0),
            allow_degenerate=False,
        )

        mesh = trimesh.Trimesh(
            vertices=verts,
            faces=faces,
            vertex_normals=normals,
            process=True,
        )

        dt = time.time() - t0
        print(
            f"Mesh extracted in {dt:.3f}s: {len(verts):,} Vertices | {len(faces):,} Faces"
        )
        return mesh

    def render_photorealistic(self, mesh, output_path="rendered_stalagmite.png"):
        """
        Render photorealistic 2D image matching reference photo lighting & material.
        """
        print(f"Rendering photorealistic image to '{output_path}'...")
        t0 = time.time()

        verts = mesh.vertices
        faces = mesh.faces
        fnormals = mesh.face_normals
        fcenters = mesh.triangles_center

        # Face Shading & Lighting Calculations
        # 1. Primary Key Light (Overhead front-left light, warm cream)
        L_key = np.array([0.52, -0.58, 0.62], dtype=np.float32)
        L_key /= np.linalg.norm(L_key)

        # 2. Torch Light / Floor Lamp (Warm bright orange/yellow at bottom left)
        L_torch_pos = np.array([25.0, 15.0, 18.0], dtype=np.float32)
        dir_to_torch = L_torch_pos[None, :] - fcenters
        dist_to_torch = np.linalg.norm(dir_to_torch, axis=1, keepdims=True) + 1e-5
        L_torch_dir = dir_to_torch / dist_to_torch
        torch_attenuation = 1.0 / (1.0 + 0.0005 * dist_to_torch.ravel() ** 1.35)

        # 3. Fill Light (Soft cave ambient fill)
        L_fill = np.array([-0.4, 0.6, 0.3], dtype=np.float32)
        L_fill /= np.linalg.norm(L_fill)

        # Diffuse dot products
        diff_key = np.maximum(0.0, np.dot(fnormals, L_key))
        diff_torch = np.maximum(0.0, np.sum(fnormals * L_torch_dir, axis=1)) * torch_attenuation
        diff_fill = np.maximum(0.0, np.dot(fnormals, L_fill))

        # Under-ledge Shadow (Faces pointing downward under rings receive dark shadows)
        shadow_under = np.maximum(0.0, -fnormals[:, 2])

        # Ambient Occlusion (Crevices and under-ledges are darkened)
        height_factor = np.clip(fcenters[:, 2] / np.max(verts[:, 2]), 0.0, 1.0)
        ao = np.clip(0.40 + 0.60 * height_factor - 0.35 * shadow_under, 0.15, 1.0)

        # Specular Wet Gloss (Blinn-Phong) - Highlights top of horizontal rings
        view_dir = np.array([0.0, -1.0, 0.18], dtype=np.float32)
        view_dir /= np.linalg.norm(view_dir)

        H_key = (L_key + view_dir)
        H_key /= np.linalg.norm(H_key)
        specular_key = np.power(np.maximum(0.0, np.dot(fnormals, H_key)), 24)

        H_torch = (L_torch_dir + view_dir[None, :])
        H_torch /= np.linalg.norm(H_torch, axis=1, keepdims=True)
        specular_torch = np.power(np.maximum(0.0, np.sum(fnormals * H_torch, axis=1)), 18) * torch_attenuation

        # Colors matching the limestone reference photo
        c_base = np.array([0.96, 0.90, 0.78])    # Creamy white / ivory body
        c_mineral = np.array([0.84, 0.68, 0.44]) # Golden beige mineral deposits
        c_shadow = np.array([0.16, 0.10, 0.06])  # Deep dark brown crevice shadow
        c_torch = np.array([1.00, 0.70, 0.20])   # Warm torch flame amber
        c_key = np.array([1.00, 0.96, 0.88])     # Overhead key light
        c_spec = np.array([1.00, 0.98, 0.94])    # Wet specular shine

        # Composite face color
        face_colors = np.zeros((len(faces), 3), dtype=np.float32)
        
        mineral_mix = 0.5 + 0.5 * np.sin(fcenters[:, 2] * 0.10)
        stone_col = c_base[None, :] * (1.0 - mineral_mix[:, None] * 0.30) + c_mineral[None, :] * (mineral_mix[:, None] * 0.30)

        for i in range(3):
            col = (
                stone_col[:, i] * (0.24 * ao + 0.72 * diff_key * c_key[i] + 0.12 * diff_fill) +
                c_torch[i] * diff_torch * 0.95 +
                c_spec[i] * (specular_key * 0.55 + specular_torch * 0.55) -
                c_shadow[i] * shadow_under * 0.45
            )
            face_colors[:, i] = np.clip(col, 0.0, 1.0)

        # Plot setup with Matplotlib
        fig = plt.figure(figsize=(10, 16), facecolor="#080605")
        ax = fig.add_subplot(111, projection="3d", facecolor="#080605")

        mesh_poly = Poly3DCollection(
            verts[faces],
            facecolors=face_colors,
            linewidths=0,
            antialiased=False,
        )
        ax.add_collection3d(mesh_poly)

        # Bounds & Box Aspect Ratio for tall vertical display
        x_mid, y_mid = self.nx * 0.47, self.ny * 0.48
        ax.set_xlim(x_mid - 42, x_mid + 42)
        ax.set_ylim(y_mid - 42, y_mid + 42)
        ax.set_zlim(5, self.nz - 5)

        ax.set_box_aspect((1.0, 1.0, 2.2))

        ax.axis("off")
        ax.view_init(elev=12, azim=-70)

        plt.tight_layout()
        plt.savefig(
            output_path,
            dpi=220,
            facecolor="#080605",
            bbox_inches="tight",
            pad_inches=0,
        )
        plt.close(fig)

        # Post-processing: Add subtle cave flame glow at bottom-left corner
        try:
            img = Image.open(output_path).convert("RGB")
            w, h = img.size
            glow_layer = Image.new("RGB", (w, h), (8, 6, 5))
            # Create torch glow gradient near bottom-left
            Y_grid, X_grid = np.ogrid[:h, :w]
            torch_x, torch_y = int(w * 0.20), int(h * 0.88)
            dist_from_torch = np.sqrt((X_grid - torch_x)**2 + (Y_grid - torch_y)**2)
            glow_mask = np.clip(1.0 - (dist_from_torch / (w * 0.35)), 0.0, 1.0) ** 2.2

            img_np = np.array(img, dtype=np.float32)
            glow_col = np.array([255, 140, 40], dtype=np.float32)
            img_np += glow_col[None, None, :] * glow_mask[:, :, None] * 0.35
            img_final = Image.fromarray(np.clip(img_np, 0, 255).astype(np.uint8))
            img_final.save(output_path)
        except Exception as e:
            print(f"Post-processing note: {e}")

        dt = time.time() - t0
        print(f"Photorealistic render saved to '{output_path}' in {dt:.3f}s!")


def main():
    print("=================================================================")
    print(" Procedural 3D Stalagmite Generator & Photorealistic Renderer")
    print(" (Măng Đá & Cột Thạch Nhũ)")
    print("=================================================================")

    # Resolution 160x160x240 for crisp speleothem detail
    generator = StalagmiteGenerator(grid_shape=(160, 160, 240), seed=1337)

    # 1. Compute 3D Density Grid
    density_field = generator.generate_density_field()

    # 2. Marching Cubes Mesh Extraction
    mesh = generator.extract_mesh(density_field, iso_level=0.0)

    # 3. Render Photorealistic Preview Image
    render_path = "rendered_stalagmite.png"
    generator.render_photorealistic(mesh, output_path=render_path)

    # 4. Export 3D Mesh Models
    obj_path = "stalagmite.obj"
    glb_path = "stalagmite.glb"

    print(f"Exporting 3D mesh to OBJ: '{obj_path}'...")
    mesh.export(obj_path)

    print(f"Exporting 3D mesh to GLB: '{glb_path}'...")
    mesh.export(glb_path)

    print("\nStalagmite generation and rendering complete!")
    print(f"Output preview image: {render_path}")
    print(f"Output 3D models: {obj_path}, {glb_path}")


if __name__ == "__main__":
    main()
