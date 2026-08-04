"""
Procedural 3D Cave Generator with Stalactites & Stalagmites (Thạch Nhũ & Măng Đá)

Technologies:
1. NumPy: 3D Spatial Array & Vectorized Density Math
2. PyFastNoiseLite: FastNoiseLite 3D/2D C++ bindings (1:1 Godot 4 parity)
3. scikit-image: Marching Cubes Algorithm (skimage.measure.marching_cubes)
4. Trimesh: 3D Mesh Export (.obj, .glb)
"""

import time
import numpy as np
from pyfastnoiselite.pyfastnoiselite import (
    FastNoiseLite,
    NoiseType,
    CellularDistanceFunction,
    CellularReturnType,
    FractalType,
)
from skimage.measure import marching_cubes
import trimesh

class CaveGenerator:
    def __init__(
        self,
        grid_shape=(128, 128, 128),
        seed=1337,
        cave_frequency=0.018,
        speleothem_frequency=0.05,
        roughness_frequency=0.09,
    ):
        """
        Initialize Cave Generator with grid shape and noise parameters.
        :param grid_shape: Tuple (X, Y, Z) defining 3D voxel resolution
        :param seed: Seed number (same seed produces identical result in Godot 4)
        :param cave_frequency: Frequency for base cavern hollow chamber
        :param speleothem_frequency: Frequency for stalactite/stalagmite cellular distribution
        :param roughness_frequency: High-frequency noise for limestone dripping texture
        """
        self.nx, self.ny, self.nz = grid_shape
        self.seed = seed
        self.cave_frequency = cave_frequency
        self.speleothem_frequency = speleothem_frequency
        self.roughness_frequency = roughness_frequency

        self._init_noises()

    def _init_noises(self):
        """Initialize FastNoiseLite generators with Godot 4 compatible parameters."""
        # 1. Base Cave Cavern Chamber (3D OpenSimplex2)
        self.cave_noise = FastNoiseLite(self.seed)
        self.cave_noise.noise_type = NoiseType.NoiseType_OpenSimplex2
        self.cave_noise.frequency = self.cave_frequency
        self.cave_noise.fractal_type = FractalType.FractalType_FBm
        self.cave_noise.fractal_octaves = 4
        self.cave_noise.fractal_lacunarity = 2.0
        self.cave_noise.fractal_gain = 0.5

        # 2. Speleothem Placement Noise (2D Cellular / Voronoi)
        self.cellular_noise = FastNoiseLite(self.seed + 101)
        self.cellular_noise.noise_type = NoiseType.NoiseType_Cellular
        self.cellular_noise.frequency = self.speleothem_frequency
        self.cellular_noise.cellular_distance_function = (
            CellularDistanceFunction.CellularDistanceFunction_Euclidean
        )
        self.cellular_noise.cellular_return_type = (
            CellularReturnType.CellularReturnType_Distance
        )
        self.cellular_noise.cellular_jitter = 0.85

        # 3. Speleothem Length Variation Noise (2D Perlin)
        self.length_noise = FastNoiseLite(self.seed + 202)
        self.length_noise.noise_type = NoiseType.NoiseType_Perlin
        self.length_noise.frequency = 0.03

        # 4. Surface Micro-Roughness Noise (3D Perlin for limestone dripping texture)
        self.roughness_noise = FastNoiseLite(self.seed + 303)
        self.roughness_noise.noise_type = NoiseType.NoiseType_Perlin
        self.roughness_noise.frequency = self.roughness_frequency
        self.roughness_noise.fractal_type = FractalType.FractalType_FBm
        self.roughness_noise.fractal_octaves = 3

    def _get_noise_3d_fast(self, noise_instance, scale_z=1.0):
        """Fast C++ vectorized 3D noise evaluation via PyFastNoiseLite gen_from_coords."""
        x, y, z = np.meshgrid(
            np.arange(self.nx, dtype=np.float32),
            np.arange(self.ny, dtype=np.float32),
            np.arange(self.nz, dtype=np.float32) * scale_z,
            indexing="ij",
        )
        coords = np.ascontiguousarray(
            np.stack([x.ravel(), y.ravel(), z.ravel()]), dtype=np.float32
        )
        noise_flat = noise_instance.gen_from_coords(coords)
        return noise_flat.reshape((self.nx, self.ny, self.nz))

    def _get_noise_2d_fast(self, noise_instance):
        """Fast C++ vectorized 2D noise evaluation via PyFastNoiseLite gen_from_coords."""
        x, y = np.meshgrid(
            np.arange(self.nx, dtype=np.float32),
            np.arange(self.ny, dtype=np.float32),
            indexing="ij",
        )
        coords = np.ascontiguousarray(
            np.stack([x.ravel(), y.ravel()]), dtype=np.float32
        )
        noise_flat = noise_instance.gen_from_coords(coords)
        return noise_flat.reshape((self.nx, self.ny))

    def generate_density_field(self):
        """
        Build 3D density scalar field D(x, y, z).
        D > 0: Solid Rock
        D < 0: Cavern Air
        D = 0: Cave Surface Isosurface
        """
        print(f"Generating 3D voxel density field [{self.nx}, {self.ny}, {self.nz}]...")
        t0 = time.time()

        # Coordinate grid
        x_idx = np.arange(self.nx, dtype=np.float32)
        y_idx = np.arange(self.ny, dtype=np.float32)
        z_idx = np.arange(self.nz, dtype=np.float32)
        _, _, Z = np.meshgrid(x_idx, y_idx, z_idx, indexing="ij")
        Z_norm = Z / float(self.nz)

        # -------------------------------------------------------------
        # STEP 1: Cavern Chamber Base Shape
        # -------------------------------------------------------------
        print("Computing 3D base cave cavern chamber noise...")
        cave_3d = self._get_noise_3d_fast(self.cave_noise)

        # Outer wall boundary containment
        border_x = np.abs((np.arange(self.nx) - self.nx / 2.0) / (self.nx / 2.0)) ** 4
        border_y = np.abs((np.arange(self.ny) - self.ny / 2.0) / (self.ny / 2.0)) ** 4
        border_mask = border_x[:, None, None] + border_y[None, :, None]

        # Base density (air inside, solid rock walls/floor/ceiling)
        density_chamber = (
            -1.0
            + 2.5 * (Z_norm < 0.15) * (0.15 - Z_norm)
            + 2.5 * (Z_norm > 0.85) * (Z_norm - 0.85)
            + cave_3d * 1.2
            + border_mask * 1.5
        )

        # -------------------------------------------------------------
        # STEP 2: Stalactites (Thạch Nhũ) - Ceiling Spikes Hanging Down
        # -------------------------------------------------------------
        print("Computing Stalactites (Thạch Nhũ)...")
        cellular_2d = self._get_noise_2d_fast(self.cellular_noise)  # [-1, 1]
        spike_centers = np.clip((cellular_2d + 1.0) / 2.0, 0.0, 1.0)
        # Sharp power curve for needle-like stalactite cones
        spike_intensity = np.power(spike_centers, 3.2)

        # Length variation per stalactite
        len_var = self._get_noise_2d_fast(self.length_noise)
        stalactite_length = 0.22 + 0.22 * (len_var + 1.0) / 2.0

        ceiling_z = 0.85 + cave_3d[:, :, -1] * 0.05
        ceiling_z_3d = ceiling_z[:, :, None]

        drop_dist = np.maximum(0.0, ceiling_z_3d - Z_norm)
        stalactite_len_3d = stalactite_length[:, :, None]

        taper_factor = np.clip(1.0 - (drop_dist / stalactite_len_3d), 0.0, 1.0)
        stalactite_mask = (drop_dist <= stalactite_len_3d) * (Z_norm > 0.35)

        density_stalactites = (
            stalactite_mask
            * spike_intensity[:, :, None]
            * np.power(taper_factor, 1.8)
            * 2.8
        )

        # -------------------------------------------------------------
        # STEP 3: Stalagmites (Măng Đá) - Floor Pillars Growing Up
        # -------------------------------------------------------------
        print("Computing Stalagmites (Măng Đá)...")
        floor_z = 0.15 + cave_3d[:, :, 0] * 0.05
        floor_z_3d = floor_z[:, :, None]

        rise_dist = np.maximum(0.0, Z_norm - floor_z_3d)
        stalagmite_length = 0.18 + 0.18 * (len_var + 1.0) / 2.0

        stalagmite_len_3d = stalagmite_length[:, :, None]
        taper_factor_floor = np.clip(1.0 - (rise_dist / stalagmite_len_3d), 0.0, 1.0)
        stalagmite_mask = (rise_dist <= stalagmite_len_3d) * (Z_norm < 0.65)

        density_stalagmites = (
            stalagmite_mask
            * spike_intensity[:, :, None]
            * np.power(taper_factor_floor, 2.0)
            * 2.5
        )

        # -------------------------------------------------------------
        # STEP 4: Dripping Texture & Surface Micro-Roughness
        # -------------------------------------------------------------
        print("Computing Dripping Texture & Micro-Roughness...")
        roughness_3d = self._get_noise_3d_fast(self.roughness_noise, scale_z=0.5)
        density_roughness = roughness_3d * 0.35

        # Composite total density
        total_density = (
            density_chamber
            + density_stalactites
            + density_stalagmites
            + density_roughness
        )

        dt = time.time() - t0
        print(f"3D Voxel density field generated in {dt:.3f} seconds!")
        return total_density

    def extract_mesh(self, density_field, iso_level=0.0):
        """
        Extract 3D mesh using scikit-image Marching Cubes (skimage.measure.marching_cubes).
        """
        print("Running scikit-image Marching Cubes algorithm (skimage.measure.marching_cubes)...")
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
        print(f"Marching Cubes completed in {dt:.3f} seconds!")
        print(f"Extracted Mesh Summary: {len(verts):,} Vertices | {len(faces):,} Faces")
        return mesh

    def print_godot4_config(self):
        """Print Godot 4 FastNoiseLite equivalent settings."""
        print("\n" + "=" * 65)
        print(" GODOT 4 FastNoiseLite EQUIVALENT CONFIGURATION")
        print("=" * 65)
        print(f" Seed: {self.seed}")
        print(" 1. Cavern Chamber Noise (FastNoiseLite):")
        print("    - Noise Type: OpenSimplex2 (3D)")
        print(f"    - Frequency: {self.cave_frequency}")
        print("    - Fractal Type: FBm (Octaves: 4, Lacunarity: 2.0, Gain: 0.5)")
        print(" 2. Speleothem Placement Noise (FastNoiseLite):")
        print("    - Noise Type: Cellular (Voronoi)")
        print("    - Cellular Distance Function: Euclidean")
        print("    - Cellular Return Type: Distance")
        print(f"    - Frequency: {self.speleothem_frequency}")
        print(" 3. Limestone Surface Roughness Noise (FastNoiseLite):")
        print("    - Noise Type: Perlin")
        print(f"    - Frequency: {self.roughness_frequency}")
        print("=" * 65 + "\n")


def main():
    print("=========================================================")
    print(" 3D Cave Generator with Stalactites & Stalagmites")
    print(" (Thạch Nhũ & Măng Đá)")
    print("=========================================================")

    # Resolution 128x128x128 for detailed speleothems and fast generation (<1s)
    generator = CaveGenerator(
        grid_shape=(128, 128, 128),
        seed=1337,
        cave_frequency=0.018,
        speleothem_frequency=0.05,
        roughness_frequency=0.09,
    )

    generator.print_godot4_config()

    # Step 1: Compute 3D Density Grid
    density_field = generator.generate_density_field()

    # Step 2: Run Marching Cubes
    mesh = generator.extract_mesh(density_field, iso_level=0.0)

    # Step 3: Export 3D Mesh
    obj_path = "cave_map.obj"
    glb_path = "cave_map.glb"

    print(f"Exporting mesh to OBJ: '{obj_path}'...")
    mesh.export(obj_path)

    print(f"Exporting mesh to GLB: '{glb_path}'...")
    mesh.export(glb_path)

    print("\nCave generation complete! Mesh files created successfully.")

if __name__ == "__main__":
    main()
