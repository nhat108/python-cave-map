"""
Procedural 3D Cave Tunnel Network & Subterranean Passage System
(Hệ Thống Đường Ống Hang Động 3D & Sump Subterranean River)

Features:
1. 3D Skeletal Passage Network: Entrance pit shafts, horizontal conduits, deep vertical sumps, and subterranean rivers.
2. Dual-Zone Environment: Upper dry air chambers (hang khô) & submerged water-table sumps (hang ngầm ngập nước).
3. Mountain Topography & 3D Voxel Marching Cubes Mesh Extraction.
4. Exporting 3D Mesh formats (.obj, .glb) for rock matrix and subterranean water bodies.
5. Photorealistic 3D Cross-Section Cutaway & Perspective Renderings ('rendered_cave_system.png').
"""

import os
import time
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from scipy.spatial import cKDTree
from skimage.measure import marching_cubes
import trimesh
from PIL import Image, ImageDraw

from pyfastnoiselite.pyfastnoiselite import (
    FastNoiseLite,
    NoiseType,
    FractalType,
)


class CaveTunnelGenerator:
    def __init__(self, grid_shape=(220, 120, 160), seed=1337, water_level=80.0):
        """
        Initialize 3D Cave Tunnel Generator.
        :param grid_shape: (nx, ny, nz) voxel resolution
        :param seed: Random seed for procedural terrain & tunnel noise
        :param water_level: Z elevation of the subterranean water table
        """
        self.nx, self.ny, self.nz = grid_shape
        self.seed = seed
        self.water_level = water_level
        self._init_noises()

    def _init_noises(self):
        """Initialize FastNoiseLite generators for mountain terrain & rock erosion walls."""
        # 1. Mountain terrain height noise (2D)
        self.terrain_noise = FastNoiseLite(self.seed)
        self.terrain_noise.noise_type = NoiseType.NoiseType_Perlin
        self.terrain_noise.frequency = 0.015
        self.terrain_noise.fractal_type = FractalType.FractalType_FBm
        self.terrain_noise.fractal_octaves = 3

        # 2. Cave wall rock erosion texture (3D)
        self.rock_noise = FastNoiseLite(self.seed + 101)
        self.rock_noise.noise_type = NoiseType.NoiseType_OpenSimplex2
        self.rock_noise.frequency = 0.04
        self.rock_noise.fractal_type = FractalType.FractalType_FBm
        self.rock_noise.fractal_octaves = 3

        # 3. Passage radius swell/squeeze noise (1D/3D)
        self.radius_noise = FastNoiseLite(self.seed + 202)
        self.radius_noise.noise_type = NoiseType.NoiseType_Perlin
        self.radius_noise.frequency = 0.025

    def _build_cave_skeleton(self):
        """
        Generate 3D skeletal trajectories (curves) for the subterranean cave network:
        - Entrance Pit Shaft (Giếng lối vào)
        - Main Horizontal Conduit (Đường ống chính)
        - Deep Vertical Pit Sump (Giếng ngầm đáy sâu)
        - Branching Loop Passage (Đường nối nhánh phụ)
        """
        skeletal_points = []
        point_radii = []

        # 1. Entrance Pit Shaft (From top mountain surface down to upper dry chamber)
        t1 = np.linspace(0, 1, 100, dtype=np.float32)
        x1 = 48.0 + 4.0 * np.sin(3.0 * np.pi * t1)
        y1 = 60.0 + 3.0 * np.cos(2.0 * np.pi * t1)
        z1 = 150.0 - 40.0 * t1
        r1 = 5.5 + 1.5 * np.sin(10.0 * t1)

        pts1 = np.stack([x1, y1, z1], axis=1)
        skeletal_points.append(pts1)
        point_radii.append(r1)

        # 2. Main Horizontal Conduit (Spans x=20 to x=205, dipping below water level)
        t2 = np.linspace(0, 1, 350, dtype=np.float32)
        x2 = 20.0 + 185.0 * t2
        y2 = 60.0 + 12.0 * np.sin(2.5 * np.pi * t2)
        
        # Height profile Z: dips below water_level=80 into flooded sumps
        z2 = (
            110.0
            - 45.0 * np.sin(np.pi * t2 ** 0.8)
            + 15.0 * np.sin(3.0 * np.pi * t2)
            + 8.0 * np.cos(5.0 * np.pi * t2)
        )
        r2 = 9.0 + 4.5 * np.sin(4.0 * np.pi * t2) + 2.0 * np.cos(9.0 * np.pi * t2)

        pts2 = np.stack([x2, y2, z2], axis=1)
        skeletal_points.append(pts2)
        point_radii.append(r2)

        # 3. Deep Vertical Pit Sump (Dips vertically from x=82 down to z=18 deep sump bottom)
        t3 = np.linspace(0, 1, 180, dtype=np.float32)
        x3 = 82.0 + 5.0 * np.sin(4.0 * np.pi * t3)
        y3 = 58.0 + 4.0 * np.cos(3.0 * np.pi * t3)
        z3 = 98.0 - 80.0 * t3
        r3 = 8.0 + 3.0 * np.sin(5.0 * np.pi * t3)

        pts3 = np.stack([x3, y3, z3], axis=1)
        skeletal_points.append(pts3)
        point_radii.append(r3)

        # 4. Branching Loop Passage (Connects left upper chamber down into the deep sump)
        t4 = np.linspace(0, 1, 150, dtype=np.float32)
        x4 = 32.0 + 48.0 * t4
        y4 = 62.0 + 6.0 * np.sin(2.0 * np.pi * t4)
        z4 = 92.0 - 55.0 * t4 + 10.0 * np.sin(np.pi * t4)
        r4 = 7.0 + 2.5 * np.cos(3.0 * np.pi * t4)

        pts4 = np.stack([x4, y4, z4], axis=1)
        skeletal_points.append(pts4)
        point_radii.append(r4)

        # Concatenate all skeletal points & radii
        all_pts = np.concatenate(skeletal_points, axis=0)
        all_radii = np.concatenate(point_radii, axis=0)

        return all_pts, all_radii

    def generate_density_field(self):
        """
        Build 3D voxel density field for the cave system.
        D > 0: Solid Rock Mountain Matrix
        D < 0: Hollow Cave Tunnel Cavity
        """
        print(f"Generating 3D Voxel Cave Field [{self.nx}x{self.ny}x{self.nz}]...")
        t0 = time.time()

        # Coordinate grid
        x_arr = np.arange(self.nx, dtype=np.float32)
        y_arr = np.arange(self.ny, dtype=np.float32)
        z_arr = np.arange(self.nz, dtype=np.float32)
        X, Y, Z = np.meshgrid(x_arr, y_arr, z_arr, indexing="ij")

        # 1. Compute 2D Mountain Topography
        coords_2d = np.ascontiguousarray(
            np.stack([X[:, :, 0].ravel(), Y[:, :, 0].ravel()]), dtype=np.float32
        )
        terrain_n2d = self.terrain_noise.gen_from_coords(coords_2d).reshape(
            (self.nx, self.ny)
        )
        # Mountain profile with peak at left/center and gentle slope down to right
        mountain_height = 145.0 + 18.0 * np.sin(X[:, :, 0] * 0.02) + terrain_n2d * 14.0
        terrain_z = mountain_height[:, :, None]

        # 2. Compute 3D Rock Erosion Texture Noise
        coords_3d = np.ascontiguousarray(
            np.stack([X.ravel(), Y.ravel(), Z.ravel()]), dtype=np.float32
        )
        rock_n3d = self.rock_noise.gen_from_coords(coords_3d).reshape(
            (self.nx, self.ny, self.nz)
        )

        # 3. Compute Distance Field to Cave Skeleton
        print("Computing fast KD-Tree spatial distance to cave passage skeleton...")
        skel_pts, skel_radii = self._build_cave_skeleton()
        
        grid_pts = np.stack([X.ravel(), Y.ravel(), Z.ravel()], axis=1)
        tree = cKDTree(skel_pts)
        dists, indices = tree.query(grid_pts, k=1)
        
        dist_field = dists.reshape((self.nx, self.ny, self.nz))
        target_radii = skel_radii[indices].reshape((self.nx, self.ny, self.nz))

        # Tunnel signed distance: Negative inside tunnel, Positive in solid rock
        tunnel_sdf = dist_field - (target_radii + rock_n3d * 3.5)

        # Combine with mountain terrain: Outside mountain (above Z_terrain) is air
        density_field = np.where(Z > terrain_z, Z - terrain_z + 2.0, tunnel_sdf)

        dt = time.time() - t0
        print(f"3D Cave density field created in {dt:.3f} seconds!")
        return density_field, terrain_z

    def extract_meshes(self, density_field, terrain_z):
        """
        Extract 3D meshes for:
        1. Cave Rock Matrix & Cavity Walls
        2. Subterranean Water Body
        """
        print("Extracting 3D Cave Meshes via Marching Cubes...")
        t0 = time.time()

        # 1. Cave Rock interior walls mesh (density_field = 0.0)
        verts_rock, faces_rock, normals_rock, _ = marching_cubes(
            density_field,
            level=0.0,
            spacing=(1.0, 1.0, 1.0),
            allow_degenerate=False,
        )
        mesh_rock = trimesh.Trimesh(
            vertices=verts_rock,
            faces=faces_rock,
            vertex_normals=normals_rock,
            process=True,
        )

        # 2. Subterranean Water Mesh (Water body filling hollow tunnels below water_level)
        # Water occupies voxels where density < 0 and Z < water_level
        water_mask = (density_field < 0.0) & (
            np.arange(self.nz, dtype=np.float32)[None, None, :] <= self.water_level
        )
        water_sdf = np.where(water_mask, -1.0, 1.0)
        
        try:
            verts_water, faces_water, normals_water, _ = marching_cubes(
                water_sdf,
                level=0.0,
                spacing=(1.0, 1.0, 1.0),
                allow_degenerate=False,
            )
            mesh_water = trimesh.Trimesh(
                vertices=verts_water,
                faces=faces_water,
                vertex_normals=normals_water,
                process=True,
            )
        except Exception:
            mesh_water = None

        dt = time.time() - t0
        print(
            f"Meshes extracted in {dt:.3f}s: Rock={len(verts_rock):,} Vertices | {len(faces_rock):,} Faces"
        )
        return mesh_rock, mesh_water

    def render_cave_system(
        self, density_field, terrain_z, output_path="rendered_cave_system.png"
    ):
        """
        Render a 3D Side-Cutaway Cross-Section Diagram & Perspective view of the cave system matching the reference photo.
        """
        print(f"Rendering 3D Cave System Diagram to '{output_path}'...")
        t0 = time.time()

        # Take 2D Cross-Section slice along Y = ny // 2 (Center line cutaway)
        y_cut = self.ny // 2
        cut_density = density_field[:, y_cut, :]  # Shape: (nx, nz)
        cut_terrain = np.squeeze(terrain_z[:, y_cut])  # Shape: (nx,)

        X_grid, Z_grid = np.meshgrid(
            np.arange(self.nx), np.arange(self.nz), indexing="ij"
        )

        # Matplotlib Figure
        fig, ax = plt.subplots(figsize=(16, 9), facecolor="#0c0a08")
        ax.set_facecolor("#0c0a08")

        # 1. Background Sky & Distance Mountain Outlines
        sky_gradient = np.linspace(0.12, 0.02, 100)[:, None]
        ax.imshow(
            np.tile(sky_gradient, (1, 100, 3)),
            extent=[0, self.nx, 130, self.nz + 20],
            aspect="auto",
            origin="lower",
        )

        # Distant Mountain Range silhouette
        m1_x = np.linspace(0, self.nx, 300)
        m1_z = 135.0 + 12.0 * np.sin(m1_x * 0.03) + 8.0 * np.cos(m1_x * 0.07)
        ax.fill_between(m1_x, m1_z, 0, color="#161b22", alpha=0.9, zorder=1)

        # 2. Main Mountain Rock Matrix (Dark Solid Bedrock)
        rock_mask = Z_grid <= cut_terrain[:, None]
        
        # Bedrock texture background
        bedrock_img = np.zeros((self.nx, self.nz, 3), dtype=np.float32)
        # Deep charcoal bedrock color
        bedrock_img[:, :] = [0.12, 0.11, 0.10]
        
        # Highlight mountain surface outline
        ax.plot(
            np.arange(self.nx),
            cut_terrain,
            color="#4a5568",
            linewidth=2.5,
            zorder=3,
        )

        # 3. Hollow Cave Passage Cavities (Air & Water zones)
        air_mask = (cut_density < 0.0) & (Z_grid > self.water_level) & rock_mask
        water_mask = (cut_density < 0.0) & (Z_grid <= self.water_level) & rock_mask

        # Plot Subterranean Water Table Line (Glowing blue water level)
        ax.axhline(
            y=self.water_level,
            color="#00bcff",
            linestyle="--",
            linewidth=1.2,
            alpha=0.7,
            zorder=4,
            label="Subterranean Water Table (Mặt nước ngầm)",
        )

        # Composite 2D/3D Cutaway Image Array (nx, nz, 3)
        cutaway_rgb = np.zeros((self.nx, self.nz, 3), dtype=np.float32)

        # Background sky/mountain above terrain
        sky_mask = ~rock_mask
        cutaway_rgb[sky_mask] = np.array([0.06, 0.08, 0.10], dtype=np.float32)

        # Solid Rock Matrix
        cutaway_rgb[rock_mask] = np.array([0.14, 0.13, 0.12], dtype=np.float32)

        # Dry Air Cave Passages (Warm cave shadow grey / dark limestone interior)
        cutaway_rgb[air_mask] = np.array([0.28, 0.25, 0.22], dtype=np.float32)

        # Submerged Sump / Water Tunnels (Rich luminous sapphire blue)
        cutaway_rgb[water_mask] = np.array([0.00, 0.40, 0.78], dtype=np.float32)

        # Draw Cutaway Image
        ax.imshow(
            np.transpose(cutaway_rgb, (1, 0, 2)),
            extent=[0, self.nx, 0, self.nz],
            aspect="auto",
            origin="lower",
            zorder=2,
        )

        # 4. Tunnel Cave Wall Contour Lines (Bright outline around all passages)
        ax.contour(
            X_grid,
            Z_grid,
            cut_density,
            levels=[0.0],
            colors=["#8a9ba8"],
            linewidths=[1.4],
            zorder=5,
        )

        # Water surface glow inside cave passages
        ax.contour(
            X_grid,
            Z_grid,
            np.where(cut_density < 0.0, Z_grid - self.water_level, 100.0),
            levels=[0.0],
            colors=["#38bdf8"],
            linewidths=[2.0],
            zorder=6,
        )

        # 5. Annotations & Labels
        ax.text(
            48, 155, "Entrance Shaft\n(Giếng Lối Vào)",
            color="#e2e8f0", fontsize=9, fontweight="bold",
            ha="center", bbox=dict(boxstyle="round,pad=0.3", facecolor="#1e293b", alpha=0.8),
            zorder=10
        )
        ax.text(
            35, 115, "Dry Upper Passage\n(Hang Khô)",
            color="#fef08a", fontsize=9, fontweight="bold",
            ha="center", bbox=dict(boxstyle="round,pad=0.3", facecolor="#292524", alpha=0.8),
            zorder=10
        )
        ax.text(
            78, 25, "Deep Vertical Sump\n(Giếng Ngầm Đáy Sâu)",
            color="#7dd3fc", fontsize=9, fontweight="bold",
            ha="center", bbox=dict(boxstyle="round,pad=0.3", facecolor="#0c4a6e", alpha=0.8),
            zorder=10
        )
        ax.text(
            150, 62, "Submerged Sump River Conduit\n(Đường Ống Sông Ngầm Ngập Nước)",
            color="#38bdf8", fontsize=9, fontweight="bold",
            ha="center", bbox=dict(boxstyle="round,pad=0.3", facecolor="#0369a1", alpha=0.85),
            zorder=10
        )

        ax.set_xlim(0, self.nx)
        ax.set_ylim(0, self.nz + 15)
        ax.axis("off")

        # Title
        plt.title(
            "Procedural 3D Subterranean Cave System & Sump Conduit Network\n(Sơ Đồ Mặt Cắt & Cấu Trúc 3D Hang Động)",
            color="#f8fafc",
            fontsize=13,
            pad=12,
            fontweight="bold",
        )

        plt.tight_layout()
        plt.savefig(
            output_path,
            dpi=200,
            facecolor="#0c0a08",
            bbox_inches="tight",
            pad_inches=0.2,
        )
        plt.close(fig)

        dt = time.time() - t0
        print(f"Photorealistic 3D Cave System diagram saved to '{output_path}' in {dt:.3f}s!")

    def render_3d_perspective(
        self, mesh_rock, mesh_water, output_path="rendered_cave_3d_mesh.png"
    ):
        """
        Render 3D Perspective Isometric view of the hollow cave passage network & water body in full 3D space.
        """
        print(f"Rendering 3D Perspective View of Cave Mesh to '{output_path}'...")
        t0 = time.time()

        fig = plt.figure(figsize=(14, 10), facecolor="#0c0a08")
        ax = fig.add_subplot(111, projection="3d", facecolor="#0c0a08")

        # 1. Plot Cave Rock Matrix (Hollow tunnel interior surface)
        verts_r = mesh_rock.vertices
        faces_r = mesh_rock.faces
        fnormals_r = mesh_rock.face_normals

        # Light direction vector
        L = np.array([0.5, -0.6, 0.6], dtype=np.float32)
        L /= np.linalg.norm(L)

        diff_r = np.maximum(0.0, np.dot(fnormals_r, L))
        
        # Color: Dark cave rock walls with directional shading
        c_rock_base = np.array([0.38, 0.34, 0.30], dtype=np.float32)
        c_rock_dark = np.array([0.10, 0.09, 0.08], dtype=np.float32)
        
        colors_r = c_rock_dark[None, :] + (c_rock_base - c_rock_dark)[None, :] * (0.25 + 0.75 * diff_r[:, None])
        colors_r = np.clip(colors_r, 0.0, 1.0)

        # Poly3DCollection for cave rock mesh
        poly_rock = Poly3DCollection(verts_r[faces_r], facecolors=colors_r, linewidths=0, alpha=0.90)
        ax.add_collection3d(poly_rock)

        # 2. Plot Subterranean Water Body (Glowing blue water mesh)
        if mesh_water is not None and len(mesh_water.faces) > 0:
            verts_w = mesh_water.vertices
            faces_w = mesh_water.faces
            fnormals_w = mesh_water.face_normals
            
            diff_w = np.maximum(0.0, np.dot(fnormals_w, L))
            c_water = np.array([0.0, 0.60, 0.98], dtype=np.float32)
            colors_w = c_water[None, :] * (0.45 + 0.55 * diff_w[:, None])
            colors_w = np.clip(colors_w, 0.0, 1.0)

            poly_water = Poly3DCollection(verts_w[faces_w], facecolors=colors_w, linewidths=0, alpha=0.75)
            ax.add_collection3d(poly_water)

        ax.set_xlim(0, self.nx)
        ax.set_ylim(0, self.ny)
        ax.set_zlim(0, self.nz)
        ax.set_box_aspect((self.nx / 100.0, self.ny / 100.0, self.nz / 100.0))

        ax.axis("off")
        ax.view_init(elev=26, azim=-52)

        plt.title(
            "Procedural 3D Cave Passage Network (Isometric 3D View)\n(Mô Hình Hang Động 3D Không Gian 3 Chiều)",
            color="#f8fafc",
            fontsize=13,
            pad=10,
            fontweight="bold",
        )

        plt.tight_layout()
        plt.savefig(
            output_path, dpi=180, facecolor="#0c0a08", bbox_inches="tight", pad_inches=0.2
        )
        plt.close(fig)

        dt = time.time() - t0
        print(f"3D Perspective view saved to '{output_path}' in {dt:.3f}s!")


def main():
    print("=================================================================")
    print(" Procedural 3D Cave Tunnel Network & Subterranean River Generator")
    print(" (Hệ Thống Đường Ống Hang Động 3D & Sump)")
    print("=================================================================")

    # Resolution (220, 120, 160) for wide landscape cave network layout
    generator = CaveTunnelGenerator(
        grid_shape=(220, 120, 160), seed=1337, water_level=80.0
    )

    # 1. Compute 3D Density Grid
    density_field, terrain_z = generator.generate_density_field()

    # 2. Extract 3D Meshes
    mesh_rock, mesh_water = generator.extract_meshes(density_field, terrain_z)

    # 3. Render 3D Cutaway Diagram & 3D Perspective Images
    diagram_path = "rendered_cave_system.png"
    mesh_3d_path = "rendered_cave_3d_mesh.png"
    
    generator.render_cave_system(density_field, terrain_z, output_path=diagram_path)
    generator.render_3d_perspective(mesh_rock, mesh_water, output_path=mesh_3d_path)

    # 4. Export 3D Mesh Models
    obj_rock = "cave_system_rock.obj"
    glb_rock = "cave_system_rock.glb"

    print(f"Exporting 3D Cave Rock Mesh to OBJ: '{obj_rock}'...")
    mesh_rock.export(obj_rock)

    print(f"Exporting 3D Cave Rock Mesh to GLB: '{glb_rock}'...")
    mesh_rock.export(glb_rock)

    if mesh_water is not None:
        obj_water = "cave_system_water.obj"
        glb_water = "cave_system_water.glb"
        print(f"Exporting Subterranean Water Body to OBJ: '{obj_water}'...")
        mesh_water.export(obj_water)
        print(f"Exporting Subterranean Water Body to GLB: '{glb_water}'...")
        mesh_water.export(glb_water)

    print("\n3D Cave System generation and rendering complete!")
    print(f"Output diagram render: {diagram_path}")
    print(f"Output 3D mesh render: {mesh_3d_path}")
    print(f"Output 3D models: {obj_rock}, {glb_rock}")


if __name__ == "__main__":
    main()
