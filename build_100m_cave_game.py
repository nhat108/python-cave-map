"""
Build 100m 3D Cave Game & Assets for Godot 4 Project ('cave-diving-game')

Atmospheric Subterranean Lighting Tuning:
1. Balanced Realistic Headlamp:
   - SpotLight3D: light_energy = 4.0, spot_range = 45.0m, spot_angle = 45.0 deg, spot_attenuation = 1.0.
   - OmniLight3D (Head Fill): light_energy = 0.8, omni_range = 15.0m, omni_attenuation = 1.2.
2. Dark Atmospheric Ambient Glow:
   - ambient_light_energy = 0.12, ambient_light_color = Color(0.10, 0.14, 0.20).
3. Realistic Subterranean PBR Material Albedo & Roughness:
   - CaveRock: Color(0.42, 0.36, 0.30), roughness = 0.85.
   - CaveSediment: Color(0.35, 0.26, 0.18), roughness = 0.70.
   - CaveBoulders: Color(0.48, 0.42, 0.35), roughness = 0.75.
   - CaveSpeleothems: Color(0.55, 0.50, 0.42), roughness = 0.60.
   - CaveWater: Color(0.10, 0.52, 0.78, 0.45), roughness = 0.05.
"""

import os
import sys
import time
import numpy as np
from scipy.spatial import cKDTree
from skimage.measure import marching_cubes
import trimesh

from pyfastnoiselite.pyfastnoiselite import (
    FastNoiseLite,
    NoiseType,
    FractalType,
)

from boulder_generator import BoulderGenerator
from stalactite_generator import StalactiteGenerator
from stalagmite_generator import StalagmiteGenerator
from terrain_surface_generator import build_terrain, export_mesh
from pathlib import Path


def generate_single_stalagmite(seed=42, height=2.0, radius=0.4):
    """Helper to generate a clean 3D stalagmite mesh with outward face & vertex normals."""
    gen = StalagmiteGenerator(grid_shape=(40, 40, 60), seed=seed, style="default")
    density = gen.generate_density_field()
    mesh = gen.extract_mesh(density)
    
    mesh.vertices[:, 0] -= (np.min(mesh.vertices[:, 0]) + np.max(mesh.vertices[:, 0])) * 0.5
    mesh.vertices[:, 1] -= (np.min(mesh.vertices[:, 1]) + np.max(mesh.vertices[:, 1])) * 0.5
    mesh.vertices[:, 2] -= np.min(mesh.vertices[:, 2])

    z_max = np.max(mesh.vertices[:, 2])
    if z_max > 0:
        mesh.vertices[:, 2] *= (height / z_max)
    
    r_max = np.max(np.sqrt(mesh.vertices[:, 0]**2 + mesh.vertices[:, 1]**2))
    if r_max > 0:
        mesh.vertices[:, 0] *= (radius / r_max)
        mesh.vertices[:, 1] *= (radius / r_max)

    # Ensure outward face & vertex normals
    vecs = mesh.triangles_center - mesh.centroid
    flip_mask = np.sum(mesh.face_normals * vecs, axis=1) < 0
    mesh.faces[flip_mask] = mesh.faces[flip_mask][:, ::-1]
    mesh.vertex_normals = trimesh.geometry.mean_vertex_normals(len(mesh.vertices), mesh.faces, mesh.face_normals)
        
    return mesh


def generate_2d_water_ribbon(curve_points, radii, num_samples=300):
    """Generate a clean 2D single-layered water surface ribbon spanning the 100m tunnel width."""
    t_vals = np.linspace(0, 100.0, num_samples)
    verts = []
    faces = []

    for i in range(num_samples):
        cx, cy, cz = curve_points[int(i * (len(curve_points) - 1) / (num_samples - 1))]
        r = radii[int(i * (len(radii) - 1) / (num_samples - 1))]
        w_y = cy - 0.10

        w_left = [cx - r * 0.98, w_y, cz]
        w_right = [cx + r * 0.98, w_y, cz]
        verts.append(w_left)
        verts.append(w_right)

    for i in range(num_samples - 1):
        idx = i * 2
        faces.append([idx, idx + 1, idx + 2])
        faces.append([idx + 1, idx + 3, idx + 2])

    verts = np.array(verts, dtype=np.float32)
    faces = np.array(faces, dtype=int)

    mesh_water = trimesh.Trimesh(vertices=verts, faces=faces, process=True)
    mesh_water.vertex_normals = trimesh.geometry.mean_vertex_normals(len(verts), faces, mesh_water.face_normals)
    return mesh_water


def align_normals_inward(mesh, curve_points):
    """Ensure all cave tunnel shell face & vertex normals point INWARD toward central curve."""
    tri_z = mesh.triangles_center[:, 2]
    t_idx = np.clip((tri_z / 100.0) * (len(curve_points) - 1), 0, len(curve_points) - 1).astype(int)
    centers = curve_points[t_idx]

    vecs_inward = centers - mesh.triangles_center
    face_dots = np.sum(mesh.face_normals * vecs_inward, axis=1)

    flip_mask = face_dots < 0
    mesh.faces[flip_mask] = mesh.faces[flip_mask][:, ::-1]
    mesh.vertex_normals = trimesh.geometry.mean_vertex_normals(len(mesh.vertices), mesh.faces, mesh.face_normals)
    return mesh


def build_100m_cave_level(seed=42):
    """Generate 100m 3D Cave Tunnel Level with 2D Water Ribbon, Mud Bed, Speleothems & Boulders."""
    print("\n[1/5] Generating 100m Procedural 3D Cave Tunnel & 2D Water Ribbon Surface...")
    t0 = time.time()

    # 1. 100m Cave Trajectory Curve with Entrance Pit Shaft (Connecting to 5km surface terrain sinkhole at Y=35m)
    t_vals = np.linspace(0, 100.0, 400)
    curve_x = 8.0 * np.sin(0.08 * t_vals) + 4.0 * np.sin(0.20 * t_vals)
    curve_y = 2.5 * np.cos(0.06 * t_vals) - 1.5 * np.sin(0.15 * t_vals)
    curve_z = t_vals
    radii = 4.2 + 2.2 * np.sin(0.1 * t_vals) + 1.2 * np.cos(0.25 * t_vals)

    # Smooth entrance shaft curve connecting up to (0.0, 35.0, -5.0) at the bottom of 5km terrain sinkhole
    shaft_mask = t_vals <= 18.0
    s_factor = np.zeros_like(t_vals)
    s_factor[shaft_mask] = (18.0 - t_vals[shaft_mask]) / 18.0
    s_factor = s_factor * s_factor * (3.0 - 2.0 * s_factor)
    val_norm = np.maximum(0.0, (18.0 - t_vals) / 18.0)
    curve_y = (1.0 - s_factor) * curve_y + s_factor * (2.5 + 32.5 * (val_norm ** 1.4))
    curve_x = (1.0 - s_factor) * curve_x + s_factor * 0.0
    curve_z = (1.0 - s_factor) * curve_z + s_factor * (t_vals - 5.0 * val_norm)
    radii = (1.0 - s_factor) * radii + s_factor * 8.0

    curve_points = np.stack([curve_x, curve_y, curve_z], axis=1)
    kdtree = cKDTree(curve_points)

    nx, ny, nz = 90, 110, 260
    x_arr = np.linspace(-22, 22, nx, dtype=np.float32)
    y_arr = np.linspace(-15, 42, ny, dtype=np.float32)
    z_arr = np.linspace(-10, 104, nz, dtype=np.float32)
    X, Y, Z = np.meshgrid(x_arr, y_arr, z_arr, indexing="ij")
    grid_coords = np.stack([X.ravel(), Y.ravel(), Z.ravel()], axis=1)

    dists, indices = kdtree.query(grid_coords, k=1)
    dists = dists.reshape((nx, ny, nz))
    target_radii = radii[indices.reshape((nx, ny, nz))]

    fn = FastNoiseLite(seed)
    fn.noise_type = NoiseType.NoiseType_Perlin
    fn.frequency = 0.15
    fn.fractal_octaves = 3

    coords = np.ascontiguousarray(
        np.stack([(X * 0.15).ravel(), (Y * 0.15).ravel(), (Z * 0.15).ravel()]),
        dtype=np.float32,
    )
    noise_3d = fn.gen_from_coords(coords).reshape((nx, ny, nz))

    sdf_rock = dists - target_radii + noise_3d * 0.85

    # Cap cave rock mesh so it stays strictly underground below Y = 34.0m (underneath the surface terrain)
    sdf_rock[Y >= 34.0] = -1.0

    verts_r, faces_r, normals_r, _ = marching_cubes(
        sdf_rock,
        level=0.0,
        spacing=(44.0 / nx, 57.0 / ny, 114.0 / nz),
        allow_degenerate=False,
    )
    verts_r[:, 0] -= 22.0
    verts_r[:, 1] -= 15.0
    verts_r[:, 2] -= 10.0

    mesh_rock = trimesh.Trimesh(vertices=verts_r, faces=faces_r, vertex_normals=normals_r, process=True)
    mesh_rock = align_normals_inward(mesh_rock, curve_points)
    print(f"  100m Tunnel Rock Shell created (Inward Normals Verified) in {time.time() - t0:.2f}s ({len(verts_r):,} Vertices)")

    # 2. Mud & Sand Sediment Bed Layer
    print("  Generating Mud & Sand Sediment Layer along cave floor...")
    t_indices = np.clip((Z / 100.0) * 399, 0, 399).astype(int)
    cx_grid = curve_x[t_indices]
    cy_grid = curve_y[t_indices]
    r_grid = radii[t_indices]

    dist_xy_grid = np.sqrt((X - cx_grid)**2 + (Y - cy_grid)**2)
    floor_y_grid = cy_grid - np.sqrt(np.maximum(0.1, r_grid**2 - (X - cx_grid)**2))

    fn_mud = FastNoiseLite(seed + 123)
    fn_mud.noise_type = NoiseType.NoiseType_Perlin
    fn_mud.frequency = 0.20

    coords_mud = np.ascontiguousarray(np.stack([(X*0.3).ravel(), (Y*0.3).ravel(), (Z*0.3).ravel()]), dtype=np.float32)
    n_mud = fn_mud.gen_from_coords(coords_mud).reshape((nx, ny, nz))

    mud_top_grid = floor_y_grid + 0.45 + n_mud * 0.18
    sdf_mud = Y - mud_top_grid
    sdf_mud = np.maximum(sdf_mud, dist_xy_grid - r_grid + 0.05)

    verts_m, faces_m, normals_m, _ = marching_cubes(
        sdf_mud,
        level=0.0,
        spacing=(44.0 / nx, 57.0 / ny, 114.0 / nz),
        allow_degenerate=False,
    )
    verts_m[:, 0] -= 22.0
    verts_m[:, 1] -= 15.0
    verts_m[:, 2] -= 10.0

    mesh_sediment = trimesh.Trimesh(vertices=verts_m, faces=faces_m, vertex_normals=normals_m, process=True)
    mesh_sediment.vertex_normals = trimesh.geometry.mean_vertex_normals(len(verts_m), faces_m, mesh_sediment.face_normals)

    # 3. Clean 2D Water Surface Ribbon
    print("  Generating Clean 2D Water Surface Ribbon Plane...")
    mesh_water = generate_2d_water_ribbon(curve_points, radii)
    print(f"  100m Clean 2D Water Ribbon created ({len(mesh_water.vertices):,} Vertices)")

    # 4. Ceiling Stalactites & Floor Stalagmites
    print("[2/5] Populating Ceiling Stalactites & Floor Stalagmites...")
    boul_gen = BoulderGenerator(seed)
    stal_gen = StalactiteGenerator(seed)

    speleothem_meshes = []
    boulder_meshes = []
    rng = np.random.RandomState(seed)

    rot_down = trimesh.transformations.rotation_matrix(-np.pi / 2.0, [1, 0, 0])
    rot_up = trimesh.transformations.rotation_matrix(np.pi / 2.0, [1, 0, 0])

    # Place 50 Ceiling Stalactites
    for i in range(50):
        z_pos = float(rng.uniform(4.0, 96.0))
        t_idx = int(np.clip((z_pos / 100.0) * 399, 0, 399))
        cx, cy, cz = curve_points[t_idx]
        r_curr = radii[t_idx]

        st_x = float(cx + rng.uniform(-0.35 * r_curr, 0.35 * r_curr))
        dy = float(np.sqrt(max(0.1, r_curr**2 - (st_x - cx)**2)))
        st_y_ceiling = float(cy + dy - 0.2)

        style = rng.choice(["classic", "soda_straw", "drapery", "pagoda", "twin_cluster"])
        h_st = float(rng.uniform(1.2, 3.0))

        st_mesh = stal_gen.generate_single_stalactite(
            seed=seed + i * 19,
            resolution=(32, 32, 48),
            style=style,
            height=h_st,
            radius_root=float(rng.uniform(0.35, 0.65)),
        )

        st_mesh.apply_transform(rot_down)
        st_mesh.apply_translation([st_x, st_y_ceiling - h_st, cz])

        vecs = st_mesh.triangles_center - st_mesh.centroid
        flip_mask = np.sum(st_mesh.face_normals * vecs, axis=1) < 0
        st_mesh.faces[flip_mask] = st_mesh.faces[flip_mask][:, ::-1]
        st_mesh.vertex_normals = trimesh.geometry.mean_vertex_normals(len(st_mesh.vertices), st_mesh.faces, st_mesh.face_normals)

        speleothem_meshes.append(st_mesh)

    # Place 40 Floor Stalagmites
    for i in range(40):
        z_pos = float(rng.uniform(4.0, 96.0))
        t_idx = int(np.clip((z_pos / 100.0) * 399, 0, 399))
        cx, cy, cz = curve_points[t_idx]
        r_curr = radii[t_idx]

        sm_x = float(cx + rng.uniform(-0.4 * r_curr, 0.4 * r_curr))
        dy = float(np.sqrt(max(0.1, r_curr**2 - (sm_x - cx)**2)))
        sm_y_floor = float(cy - dy + 0.35)

        h_sm = float(rng.uniform(1.0, 2.4))
        sm_mesh = generate_single_stalagmite(seed=seed + i * 23, height=h_sm, radius=float(rng.uniform(0.3, 0.6)))

        sm_mesh.apply_transform(rot_up)
        sm_mesh.apply_translation([sm_x, sm_y_floor, cz])

        vecs = sm_mesh.triangles_center - sm_mesh.centroid
        flip_mask = np.sum(sm_mesh.face_normals * vecs, axis=1) < 0
        sm_mesh.faces[flip_mask] = sm_mesh.faces[flip_mask][:, ::-1]
        sm_mesh.vertex_normals = trimesh.geometry.mean_vertex_normals(len(sm_mesh.vertices), sm_mesh.faces, sm_mesh.face_normals)

        speleothem_meshes.append(sm_mesh)

    # Place 80 Boulders Snapped to Ground
    for i in range(80):
        z_pos = float(rng.uniform(3.0, 97.0))
        t_idx = int(np.clip((z_pos / 100.0) * 399, 0, 399))
        cx, cy, cz = curve_points[t_idx]
        r_curr = radii[t_idx]

        bx = float(cx + rng.uniform(-0.55 * r_curr, 0.55 * r_curr))
        dy = float(np.sqrt(max(0.1, r_curr**2 - (bx - cx)**2)))
        b_y_floor = float(cy - dy + 0.30)

        b_style = rng.choice(["faceted_block", "fractured_prism", "jagged_wedge", "crystal_polyhedron", "chipped_boulder"])
        scale_val = float(rng.uniform(0.5, 2.2))

        b_mesh = boul_gen.generate_single_boulder(
            seed=seed + i * 31,
            resolution=32,
            style=b_style,
            scale=(rng.uniform(1.0, 1.4), rng.uniform(0.8, 1.3), rng.uniform(0.7, 1.2)),
        )
        b_mesh.apply_scale(scale_val)

        rot_mat = trimesh.transformations.random_rotation_matrix(rng.rand(3))
        b_mesh.apply_transform(rot_mat)

        y_min = float(np.min(b_mesh.vertices[:, 1]))
        b_mesh.apply_translation([bx, b_y_floor - y_min, cz])

        vecs = b_mesh.triangles_center - b_mesh.centroid
        flip_mask = np.sum(b_mesh.face_normals * vecs, axis=1) < 0
        b_mesh.faces[flip_mask] = b_mesh.faces[flip_mask][:, ::-1]
        b_mesh.vertex_normals = trimesh.geometry.mean_vertex_normals(len(b_mesh.vertices), b_mesh.faces, b_mesh.face_normals)

        boulder_meshes.append(b_mesh)

    mesh_speleothems = trimesh.util.concatenate(speleothem_meshes)
    mesh_boulders = trimesh.util.concatenate(boulder_meshes)

    scene_3d = trimesh.Scene()
    scene_3d.add_geometry(mesh_rock, node_name="CaveRock", geom_name="CaveRock")
    scene_3d.add_geometry(mesh_sediment, node_name="CaveSediment", geom_name="CaveSediment")
    scene_3d.add_geometry(mesh_water, node_name="CaveWater", geom_name="CaveWater")
    scene_3d.add_geometry(mesh_speleothems, node_name="CaveSpeleothems", geom_name="CaveSpeleothems")
    scene_3d.add_geometry(mesh_boulders, node_name="CaveBoulders", geom_name="CaveBoulders")

    return scene_3d, curve_points, radii


def create_godot_project_files(project_dir="cave-diving-game", curve_points=None, radii=None):
    """Create Godot 4 project scripts, scenes, and project configurations."""
    print(f"\n[3/5] Setting up Godot 4 Project Files in '{project_dir}/'...")
    scripts_dir = os.path.join(project_dir, "scripts")
    scenes_dir = os.path.join(project_dir, "scenes")
    assets_dir = os.path.join(project_dir, "assets")

    os.makedirs(scripts_dir, exist_ok=True)
    os.makedirs(scenes_dir, exist_ok=True)
    os.makedirs(assets_dir, exist_ok=True)

    spawn_x = -180.00
    spawn_y = 85.00
    spawn_z = 150.00

    # 1. Main Cave Manager Script ('res://scripts/main_cave.gd')
    main_script_path = os.path.join(scripts_dir, "main_cave.gd")
    with open(main_script_path, "w", encoding="utf-8") as f:
        f.write(f"""extends Node3D

# Main Cave Manager: Realistic Subterranean PBR Materials & Precision Collisions

@onready var terrain_surface = $Terrain5km
@onready var cave_level = $CaveLevel
@onready var player = $Player

func _ready():
	print("Initializing 5km Surface Landscape & 100m Subterranean Collisions...")
	if terrain_surface:
		_setup_cave_materials_and_collisions(terrain_surface)
	if cave_level:
		_setup_cave_materials_and_collisions(cave_level)

	if player:
		player.global_transform.origin = Vector3({spawn_x}, {spawn_y}, {spawn_z})
		player.rotation_degrees.y = 45.0

func _setup_cave_materials_and_collisions(node: Node):
	if node is MeshInstance3D:
		var mat = StandardMaterial3D.new()

		if "Terrain" in node.name or "NaturalTerrain" in node.name:
			var tex = load("res://assets/terrain_texture.png")
			if tex:
				mat.albedo_texture = tex
			else:
				mat.vertex_color_use_as_albedo = true
			mat.roughness = 0.85
			mat.metallic = 0.0
			mat.cull_mode = BaseMaterial3D.CULL_BACK
			node.create_trimesh_collision()
		elif "Tree" in node.name or "TerrainTrees" in node.name:
			mat.vertex_color_use_as_albedo = true
			mat.roughness = 0.85
			mat.metallic = 0.0
			mat.cull_mode = BaseMaterial3D.CULL_BACK
			node.create_trimesh_collision()
		elif "Lake" in node.name or "lake" in node.name or "SurfaceLake" in node.name:
			mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
			mat.vertex_color_use_as_albedo = true
			mat.albedo_color = Color(1.0, 1.0, 1.0, 0.70)
			mat.roughness = 0.05
			mat.metallic = 0.0
			mat.cull_mode = BaseMaterial3D.CULL_DISABLED
			node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		elif "Sediment" in node.name or "sediment" in node.name:
			mat.cull_mode = BaseMaterial3D.CULL_BACK
			mat.albedo_color = Color(0.35, 0.26, 0.18)
			mat.roughness = 0.70
			mat.metallic = 0.0
			mat.specular = 0.25
			node.create_trimesh_collision()
		elif "Boulders" in node.name or "boulder" in node.name:
			mat.cull_mode = BaseMaterial3D.CULL_BACK
			mat.albedo_color = Color(0.48, 0.42, 0.35)
			mat.roughness = 0.75
			mat.metallic = 0.0
			mat.specular = 0.25
			node.create_trimesh_collision()
		elif "Speleothems" in node.name:
			mat.cull_mode = BaseMaterial3D.CULL_BACK
			mat.albedo_color = Color(0.55, 0.50, 0.42)
			mat.roughness = 0.60
			mat.metallic = 0.0
			mat.specular = 0.35
			node.create_trimesh_collision()
		else:
			# Main Limestone Cave Walls Material
			mat.cull_mode = BaseMaterial3D.CULL_DISABLED
			mat.albedo_color = Color(0.42, 0.36, 0.30)
			mat.roughness = 0.85
			mat.metallic = 0.0
			mat.specular = 0.25
			node.create_trimesh_collision()

		node.material_override = mat
		print("Configured PBR Material & Collision for: ", node.name)

	for child in node.get_children():
		_setup_cave_materials_and_collisions(child)
""")
    print("  Created res://scripts/main_cave.gd")

    # 2. Player Script with 1st/3rd Person Views & 3D Diver Model ('res://scripts/player.gd')
    player_script_path = os.path.join(scripts_dir, "player.gd")
    with open(player_script_path, "w", encoding="utf-8") as f:
        f.write("""extends CharacterBody3D

# First-Person and Third-Person Cave Diving Controller for Godot 4

const WALK_SPEED = 4.5
const SWIM_SPEED = 6.0
const SPRINT_SPEED = 8.5
const JUMP_VELOCITY = 5.0
const MOUSE_SENSITIVITY = 0.002

var gravity = ProjectSettings.get_setting("physics/3d/default_gravity")
var flashlight_on = true
var is_swimming = false
var third_person_view = false

@onready var head = $Head
@onready var camera = $Head/Camera3D
@onready var flashlight = $Head/Camera3D/SpotLight3D
@onready var head_omni = $Head/Camera3D/OmniLight3D
@onready var third_person_camera = $Head/Camera3D/ThirdPersonSpringArm3D/ThirdPersonCamera3D
@onready var state_label = $CanvasLayer/Control/StateLabel
@onready var flashlight_label = $CanvasLayer/Control/FlashlightLabel
@onready var view_mode_label = $CanvasLayer/Control/ViewModeLabel

func _ready():
	Input.set_mouse_mode(Input.MOUSE_MODE_CAPTURED)
	_update_headlamp_visibility()
	_update_view_mode()

func _update_headlamp_visibility():
	if flashlight:
		flashlight.visible = flashlight_on
	if head_omni:
		head_omni.visible = flashlight_on
	if flashlight_label:
		flashlight_label.text = "[F] Headlamp: " + ("ON" if flashlight_on else "OFF")

func _toggle_view_mode() -> void:
	third_person_view = !third_person_view
	_update_view_mode()

func _update_view_mode() -> void:
	if camera:
		camera.current = !third_person_view
	if third_person_camera:
		third_person_camera.current = third_person_view
	if view_mode_label:
		view_mode_label.text = "[V] View: " + ("THIRD PERSON" if third_person_view else "FIRST PERSON")

func _input(event):
	if event is InputEventMouseMotion and Input.get_mouse_mode() == Input.MOUSE_MODE_CAPTURED:
		head.rotate_y(-event.relative.x * MOUSE_SENSITIVITY)
		camera.rotate_x(-event.relative.y * MOUSE_SENSITIVITY)
		camera.rotation.x = clamp(camera.rotation.x, deg_to_rad(-85), deg_to_rad(85))

	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		Input.set_mouse_mode(Input.MOUSE_MODE_CAPTURED)

	if (event is InputEventKey and event.pressed and event.keycode == KEY_F and not event.echo) or event.is_action_pressed("toggle_flashlight"):
		flashlight_on = !flashlight_on
		_update_headlamp_visibility()

	if (event is InputEventKey and event.pressed and event.keycode == KEY_V and not event.echo) or event.is_action_pressed("toggle_view"):
		_toggle_view_mode()

	if event.is_action_pressed("ui_cancel") or (event is InputEventKey and event.pressed and event.keycode == KEY_ESCAPE):
		if Input.get_mouse_mode() == Input.MOUSE_MODE_CAPTURED:
			Input.set_mouse_mode(Input.MOUSE_MODE_VISIBLE)
		else:
			Input.set_mouse_mode(Input.MOUSE_MODE_CAPTURED)

func _get_move_vector() -> Vector2:
	var x = 0.0
	var y = 0.0
	if Input.is_physical_key_pressed(KEY_D) or Input.is_physical_key_pressed(KEY_RIGHT): x += 1.0
	if Input.is_physical_key_pressed(KEY_A) or Input.is_physical_key_pressed(KEY_LEFT): x -= 1.0
	if Input.is_physical_key_pressed(KEY_S) or Input.is_physical_key_pressed(KEY_DOWN): y += 1.0
	if Input.is_physical_key_pressed(KEY_W) or Input.is_physical_key_pressed(KEY_UP): y -= 1.0
	return Vector2(x, y).normalized()

func _is_sprint_pressed() -> bool:
	return Input.is_physical_key_pressed(KEY_SHIFT) or Input.is_physical_key_pressed(KEY_CTRL)

func _is_jump_pressed() -> bool:
	return Input.is_physical_key_pressed(KEY_SPACE) or Input.is_physical_key_pressed(KEY_E)

func _physics_process(delta):
	var z_pos = global_transform.origin.z
	var x_pos = global_transform.origin.x
	var player_y = global_transform.origin.y

	var dist_cenote = sqrt(x_pos * x_pos + (z_pos - (-5.0)) * (z_pos - (-5.0)))
	var is_underwater = false

	if dist_cenote < 25.0 and player_y < 45.2:
		is_underwater = true
	elif z_pos <= 10.0 and player_y < 35.0:
		is_underwater = true

	is_swimming = is_underwater

	if state_label:
		state_label.text = "[UNDERWATER DIVING]" if is_underwater else "[AIR / WALKING]"

	var move_vec = _get_move_vector()
	var is_sprint = _is_sprint_pressed()
	var current_speed = SPRINT_SPEED if is_sprint else (SWIM_SPEED if is_underwater else WALK_SPEED)

	if is_underwater:
		var camera_basis = camera.global_transform.basis
		var swim_dir = (camera_basis.x * move_vec.x + camera_basis.z * move_vec.y).normalized()

		var vertical_move = 0.0
		if _is_jump_pressed():
			vertical_move += 1.0
		if Input.is_physical_key_pressed(KEY_C) or Input.is_physical_key_pressed(KEY_Q):
			vertical_move -= 1.0

		var idle_sink = -0.8 if vertical_move == 0.0 and move_vec.length() == 0 else 0.0

		velocity.x = move_toward(velocity.x, swim_dir.x * current_speed, current_speed * 5.0 * delta)
		velocity.y = move_toward(velocity.y, (swim_dir.y * current_speed) + (vertical_move * SWIM_SPEED) + idle_sink, SWIM_SPEED * 5.0 * delta)
		velocity.z = move_toward(velocity.z, swim_dir.z * current_speed, current_speed * 5.0 * delta)

	else:
		velocity.y -= gravity * delta

		if _is_jump_pressed() and is_on_floor():
			velocity.y = JUMP_VELOCITY

		var direction = (head.global_transform.basis * Vector3(move_vec.x, 0, move_vec.y)).normalized()

		if direction:
			velocity.x = direction.x * current_speed
			velocity.z = direction.z * current_speed
		else:
			velocity.x = move_toward(velocity.x, 0, current_speed * 6.0 * delta)
			velocity.z = move_toward(velocity.z, 0, current_speed * 6.0 * delta)

	move_and_slide()
""")
    print("  Created res://scripts/player.gd")

    # 3. Player Scene with 3D Diver Model & 3rd Person View ('res://scenes/player.tscn')
    player_scene_path = os.path.join(scenes_dir, "player.tscn")
    with open(player_scene_path, "w", encoding="utf-8") as f:
        f.write("""[gd_scene load_steps=4 format=3]

[ext_resource type="Script" path="res://scripts/player.gd" id="1_player"]
[ext_resource type="Script" path="res://scripts/diver_model.gd" id="2_diver_model"]

[sub_resource type="CapsuleShape3D" id="CapsuleShape3D_player"]
radius = 0.45
height = 1.8

[node name="Player" type="CharacterBody3D"]
script = ExtResource("1_player")

[node name="CollisionShape3D" type="CollisionShape3D" parent="."]
transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0.9, 0)
shape = SubResource("CapsuleShape3D_player")

[node name="Head" type="Node3D" parent="."]
transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1.5, 0)

[node name="Camera3D" type="Camera3D" parent="Head"]
fov = 75.0

[node name="SpotLight3D" type="SpotLight3D" parent="Head/Camera3D"]
transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0.2, -0.1, -0.2)
light_color = Color(0.95, 0.98, 1, 1)
light_energy = 4.0
spot_range = 45.0
spot_attenuation = 1.0
spot_angle = 45.0

[node name="OmniLight3D" type="OmniLight3D" parent="Head/Camera3D"]
transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0.0, 0.1, -0.3)
light_color = Color(0.90, 0.95, 1, 1)
light_energy = 0.8
omni_range = 15.0
omni_attenuation = 1.2

[node name="ThirdPersonSpringArm3D" type="SpringArm3D" parent="Head/Camera3D"]
spring_length = 4.0
margin = 0.2
collision_mask = 1

[node name="ThirdPersonCamera3D" type="Camera3D" parent="Head/Camera3D/ThirdPersonSpringArm3D"]
fov = 75.0

[node name="DiverVisual" type="Node3D" parent="."]
script = ExtResource("2_diver_model")

[node name="CanvasLayer" type="CanvasLayer" parent="."]

[node name="Control" type="Control" parent="CanvasLayer"]
layout_mode = 3
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0
grow_horizontal = 2
grow_vertical = 2
mouse_filter = 2

[node name="StateLabel" type="Label" parent="CanvasLayer/Control"]
layout_mode = 0
offset_left = 20.0
offset_top = 20.0
offset_right = 300.0
offset_bottom = 50.0
mouse_filter = 2
text = "[UNDERWATER DIVING]"

[node name="FlashlightLabel" type="Label" parent="CanvasLayer/Control"]
layout_mode = 0
offset_left = 20.0
offset_top = 55.0
offset_right = 300.0
offset_bottom = 85.0
mouse_filter = 2
text = "[F] Headlamp: ON"

[node name="ViewModeLabel" type="Label" parent="CanvasLayer/Control"]
layout_mode = 0
offset_left = 20.0
offset_top = 90.0
offset_right = 300.0
offset_bottom = 120.0
mouse_filter = 2
text = "[V] View: FIRST PERSON"

[node name="ControlsLabel" type="Label" parent="CanvasLayer/Control"]
layout_mode = 0
offset_left = 20.0
offset_top = 125.0
offset_right = 550.0
offset_bottom = 155.0
mouse_filter = 2
text = "WASD: Move • Mouse: Look • Space: Up • C: Down • V: Toggle 1st/3rd View"
""")
    print("  Created res://scenes/player.tscn")

    # 4. Main Cave Scene with Realistic Ambient Environment & Sunlight ('res://scenes/main_cave.tscn')
    main_scene_path = os.path.join(scenes_dir, "main_cave.tscn")
    with open(main_scene_path, "w", encoding="utf-8") as f:
        f.write(f"""[gd_scene load_steps=8 format=3]

[ext_resource type="Script" path="res://scripts/main_cave.gd" id="1_main_script"]
[ext_resource type="PackedScene" path="res://scenes/player.tscn" id="2_player_inst"]
[ext_resource type="PackedScene" path="res://assets/cave_tunnel_100m.glb" id="3_cave_mesh"]
[ext_resource type="PackedScene" path="res://assets/terrain_5km.glb" id="4_terrain_mesh"]

[sub_resource type="ProceduralSkyMaterial" id="ProceduralSkyMaterial_sun"]
sky_top_color = Color(0.25, 0.50, 0.85, 1)
sky_horizon_color = Color(0.65, 0.78, 0.90, 1)
ground_bottom_color = Color(0.15, 0.12, 0.10, 1)

[sub_resource type="Sky" id="Sky_outdoor"]
sky_material = SubResource("ProceduralSkyMaterial_sun")

[sub_resource type="Environment" id="Environment_cave"]
background_mode = 2
sky = SubResource("Sky_outdoor")
ambient_light_source = 3
ambient_light_color = Color(0.40, 0.50, 0.65, 1)
ambient_light_energy = 0.60
tonemap_mode = 2

[node name="MainCave" type="Node3D"]
script = ExtResource("1_main_script")

[node name="WorldEnvironment" type="WorldEnvironment" parent="."]
environment = SubResource("Environment_cave")

[node name="SunLight" type="DirectionalLight3D" parent="."]
transform = Transform3D(0.866, -0.354, 0.354, 0, 0.707, 0.707, -0.5, -0.612, 0.612, 0, 120, 0)
light_color = Color(1.0, 0.96, 0.88, 1)
light_energy = 1.3
shadow_enabled = true

[node name="Terrain5km" parent="." instance=ExtResource("4_terrain_mesh")]

[node name="Player" parent="." instance=ExtResource("2_player_inst")]
transform = Transform3D(-1, 0, -8.74228e-08, 0, 1, 0, 8.74228e-08, 0, -1, {spawn_x}, {spawn_y}, {spawn_z})
""")
    print("  Created res://scenes/main_cave.tscn (Sunlit Surface & Subterranean Environment)")

    # 5. Update 'project.godot'
    project_godot_path = os.path.join(project_dir, "project.godot")
    with open(project_godot_path, "w", encoding="utf-8") as f:
        f.write("""; Engine configuration file.
config_version=5

[application]
config/name="cave-diving-game"
config/features=PackedStringArray("4.7", "Forward Plus")
config/icon="res://icon.svg"
run/main_scene="res://scenes/main_cave.tscn"

[display]
window/stretch/mode="canvas_items"
window/stretch/aspect="expand"

[input]
move_forward={
"deadzone": 0.5,
"events": [Object(InputEventKey,"resource_local_to_scene":false,"resource_name":"","device":-1,"window_id":0,"alt_pressed":false,"shift_pressed":false,"ctrl_pressed":false,"meta_pressed":false,"pressed":false,"keycode":87,"physical_keycode":87,"key_label":0,"unicode":119,"echo":false,"script":null)]
}
move_backward={
"deadzone": 0.5,
"events": [Object(InputEventKey,"resource_local_to_scene":false,"resource_name":"","device":-1,"window_id":0,"alt_pressed":false,"shift_pressed":false,"ctrl_pressed":false,"meta_pressed":false,"pressed":false,"keycode":83,"physical_keycode":83,"key_label":0,"unicode":115,"echo":false,"script":null)]
}
move_left={
"deadzone": 0.5,
"events": [Object(InputEventKey,"resource_local_to_scene":false,"resource_name":"","device":-1,"window_id":0,"alt_pressed":false,"shift_pressed":false,"ctrl_pressed":false,"meta_pressed":false,"pressed":false,"keycode":65,"physical_keycode":65,"key_label":0,"unicode":97,"echo":false,"script":null)]
}
move_right={
"deadzone": 0.5,
"events": [Object(InputEventKey,"resource_local_to_scene":false,"resource_name":"","device":-1,"window_id":0,"alt_pressed":false,"shift_pressed":false,"ctrl_pressed":false,"meta_pressed":false,"pressed":false,"keycode":68,"physical_keycode":68,"key_label":0,"unicode":100,"echo":false,"script":null)]
}
jump={
"deadzone": 0.5,
"events": [Object(InputEventKey,"resource_local_to_scene":false,"resource_name":"","device":-1,"window_id":0,"alt_pressed":false,"shift_pressed":false,"ctrl_pressed":false,"meta_pressed":false,"pressed":false,"keycode":32,"physical_keycode":32,"key_label":0,"unicode":32,"echo":false,"script":null)]
}
sprint={
"deadzone": 0.5,
"events": [Object(InputEventKey,"resource_local_to_scene":false,"resource_name":"","device":-1,"window_id":0,"alt_pressed":false,"shift_pressed":false,"ctrl_pressed":false,"meta_pressed":false,"pressed":false,"keycode":4194325,"physical_keycode":4194325,"key_label":0,"unicode":0,"echo":false,"script":null)]
}
toggle_flashlight={
"deadzone": 0.5,
"events": [Object(InputEventKey,"resource_local_to_scene":false,"resource_name":"","device":-1,"window_id":0,"alt_pressed":false,"shift_pressed":false,"ctrl_pressed":false,"meta_pressed":false,"pressed":false,"keycode":70,"physical_keycode":70,"key_label":0,"unicode":102,"echo":false,"script":null)]
}

[rendering]
renderer/rendering_method="forward_plus"
""")
    print("  Updated project.godot")


def build_web_preview(project_dir="cave-diving-game"):
    print("\n[4/5] Building Standalone WebGL 3D Explorer Preview ('cave-diving-game/index.html')...")
    index_path = os.path.join(project_dir, "index.html")

    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>3D Cave Diving & Surface Terrain Explorer (Godot 4 Parity)</title>
    <style>
        body { margin: 0; overflow: hidden; background-color: #05080c; font-family: sans-serif; color: #fff; }
        #canvas-container { width: 100vw; height: 100vh; }
        #overlay {
            position: absolute; top: 15px; left: 15px;
            background: rgba(5, 10, 18, 0.85); padding: 15px 20px;
            border-radius: 8px; border: 1px solid #1a2936;
            pointer-events: none; max-width: 400px;
        }
        h2 { margin: 0 0 8px 0; font-size: 16px; color: #4db8ff; }
        p { margin: 4px 0; font-size: 12px; color: #a0b2c6; }
        kbd { background: #1f3347; padding: 2px 6px; border-radius: 4px; font-weight: bold; color: #fff; }
        #instructions {
            position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
            background: rgba(0,0,0,0.85); padding: 30px; border-radius: 12px;
            text-align: center; cursor: pointer; border: 2px solid #4db8ff;
        }
    </style>
    <!-- Three.js & GLTFLoader CDN -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/GLTFLoader.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/PointerLockControls.js"></script>
</head>
<body>
    <div id="canvas-container"></div>
    <div id="overlay">
        <h2>3D Cave & Surface Terrain Explorer</h2>
        <p>Connected 5km Surface Sinkhole & 100m Subterranean Cave</p>
        <p><kbd>W</kbd> <kbd>A</kbd> <kbd>S</kbd> <kbd>D</kbd> : Swim 3D inside cave</p>
        <p><kbd>Space</kbd> / <kbd>E</kbd> : Ascend | <kbd>Shift</kbd> / <kbd>Q</kbd> : Descend</p>
        <p><kbd>F</kbd> : Toggle Headlamp Spotlight</p>
    </div>
    <div id="instructions">
        <h1>Click to Explore 3D Connected Cave</h1>
        <p>Balanced Subterranean Environment & Surface Sinkhole Portal</p>
    </div>

    <script>
        const container = document.getElementById('canvas-container');
        const instructions = document.getElementById('instructions');

        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x05080c);
        scene.fog = new THREE.FogExp2(0x05080c, 0.008);

        const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 5000.0);
        camera.position.set(0.0, 33.0, -12.0);

        const controls = new THREE.PointerLockControls(camera, document.body);
        instructions.addEventListener('click', () => { controls.lock(); });
        controls.addEventListener('lock', () => { instructions.style.display = 'none'; });
        controls.addEventListener('unlock', () => { instructions.style.display = 'block'; });

        // Ambient Light
        const ambientLight = new THREE.AmbientLight(0x1a2433, 0.6);
        scene.add(ambientLight);

        // Diver Headlamp
        const flashlight = new THREE.SpotLight(0xf0f8ff, 4.0, 45, Math.PI / 4, 0.5, 1.0);
        flashlight.position.set(0.2, -0.1, -0.2);
        flashlight.target.position.set(0, 0, -5);
        camera.add(flashlight);
        camera.add(flashlight.target);

        const headOmni = new THREE.PointLight(0xf0f8ff, 0.8, 15);
        headOmni.position.set(0.0, 0.1, -0.3);
        camera.add(headOmni);

        scene.add(camera);

        let flashlightOn = true;

        // Load GLB Models
        const loader = new THREE.GLTFLoader();

        loader.load('assets/terrain_5km.glb', (gltf) => {
            const terrainScene = gltf.scene;
            scene.add(terrainScene);
        });

        loader.load('assets/cave_tunnel_100m.glb', (gltf) => {
            const caveScene = gltf.scene;
            caveScene.traverse((child) => {
                if (child.isMesh) {
                    if (child.name.includes("Water")) {
                        child.material = new THREE.MeshStandardMaterial({
                            color: 0x1985c7, roughness: 0.05,
                            transparent: true, opacity: 0.45, side: THREE.DoubleSide
                        });
                    } else if (child.name.includes("Sediment")) {
                        child.material = new THREE.MeshStandardMaterial({ color: 0x59422e, roughness: 0.70 });
                    } else if (child.name.includes("Speleothems")) {
                        child.material = new THREE.MeshStandardMaterial({ color: 0x8c806b, roughness: 0.60 });
                    } else if (child.name.includes("Boulders")) {
                        child.material = new THREE.MeshStandardMaterial({ color: 0x7a6b59, roughness: 0.75 });
                    } else {
                        child.material = new THREE.MeshStandardMaterial({ color: 0x6b5c4d, roughness: 0.85 });
                    }
                }
            });
            scene.add(caveScene);
        });

        let moveFwd = false, moveBwd = false, moveLeft = false, moveRight = false, moveUp = false, moveDown = false, isSprint = false;

        document.addEventListener('keydown', (e) => {
            switch(e.code) {
                case 'KeyW': moveFwd = true; break;
                case 'KeyS': moveBwd = true; break;
                case 'KeyA': moveLeft = true; break;
                case 'KeyD': moveRight = true; break;
                case 'Space': case 'KeyE': moveUp = true; break;
                case 'ShiftLeft': case 'KeyQ': moveDown = true; break;
                case 'KeyF':
                    flashlightOn = !flashlightOn;
                    flashlight.visible = flashlightOn;
                    headOmni.visible = flashlightOn;
                    break;
            }
        });

        document.addEventListener('keyup', (e) => {
            switch(e.code) {
                case 'KeyW': moveFwd = false; break;
                case 'KeyS': moveBwd = false; break;
                case 'KeyA': moveLeft = false; break;
                case 'KeyD': moveRight = false; break;
                case 'Space': case 'KeyE': moveUp = false; break;
                case 'ShiftLeft': case 'KeyQ': moveDown = false; break;
            }
        });

        let prevTime = performance.now();
        function animate() {
            requestAnimationFrame(animate);

            const time = performance.now();
            const delta = (time - prevTime) / 1000;
            prevTime = time;

            if (controls.isLocked) {
                    velocity.x -= velocity.x * 6.0 * delta;
                    velocity.y -= velocity.y * 6.0 * delta;
                    velocity.z -= velocity.z * 6.0 * delta;

                    const dirZ = Number(moveFwd) - Number(moveBwd);
                    const dirX = Number(moveRight) - Number(moveLeft);
                    const dirY = Number(moveUp) - Number(moveDown);
                    const idleSink = (dirY === 0 && dirZ === 0 && dirX === 0) ? -0.8 : 0.0;

                    if (dirZ !== 0) velocity.z -= dirZ * speed * 6.0 * delta;
                    if (dirX !== 0) velocity.x -= dirX * speed * 6.0 * delta;
                    velocity.y += (dirY * speed + idleSink) * 6.0 * delta;

                    controls.moveForward(-velocity.z * delta);
                    controls.moveRight(-velocity.x * delta);
                    camera.position.y += velocity.y * delta;
                } else {
                    velocity.y -= gravity * delta;
                    if (moveUp && camera.position.y <= waterSurfaceY + 0.2) {
                        velocity.y = 5.0;
                    }
                    camera.position.y += velocity.y * delta;

                    const speed = isSprint ? 8.5 : 4.5;
                    const dirZ = Number(moveFwd) - Number(moveBwd);
                    const dirX = Number(moveRight) - Number(moveLeft);
                    controls.moveForward(-dirZ * speed * delta);
                    controls.moveRight(-dirX * speed * delta);
                }

                if (camera.position.y < floorY) camera.position.y = floorY;
                if (camera.position.y > ceilingY) camera.position.y = ceilingY;
                if (camera.position.x < cx - rCurr + 0.6) camera.position.x = cx - rCurr + 0.6;
                if (camera.position.x > cx + rCurr - 0.6) camera.position.x = cx + rCurr - 0.6;

                const depth = Math.min(Math.max(camera.position.z, 0.0), 100.0);
                hudDist.innerText = `Position: Z=${depth.toFixed(1)}m / 100.0m`;
            }
            renderer.render(scene, camera);
        }
        animate();

        window.addEventListener('resize', () => {
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        });
        animate();
    </script>
</body>
</html>
"""
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print("  Created cave-diving-game/index.html")


def main():
    print("=================================================================")
    print(" 3D 100m Cave Diving & Exploration Game Generator")
    print(" Project Path: 'cave-diving-game/'")
    print("=================================================================")

    assets_dir = "cave-diving-game/assets"
    os.makedirs(assets_dir, exist_ok=True)

    # 0. Build 5km Surface Terrain GLB with Connected Sinkhole
    print("\n[0/5] Generating 5km Natural Surface Terrain GLB with Connected Cave Sinkhole...")
    tx, th, tz = build_terrain(320, 20260804)
    export_mesh(tx, th, tz, Path(os.path.join(assets_dir, "terrain_5km.glb")))

    # 1. Build 100m Cave Tunnel Level Scene
    cave_scene, curve_points, radii = build_100m_cave_level(seed=2026)

    # 2. Save Mesh Files to 'cave-diving-game/assets/'
    glb_level_path = os.path.join(assets_dir, "cave_tunnel_100m.glb")

    print(f"\n[5/5] Exporting 100m Cave Level Scene GLB...")
    print(f"  Exporting GLB: '{glb_level_path}'...")
    cave_scene.export(glb_level_path)

    # 3. Create Godot Project Files
    create_godot_project_files(project_dir="cave-diving-game", curve_points=curve_points, radii=radii)

    # 4. Create Web Preview
    build_web_preview(project_dir="cave-diving-game")

    print("\n=================================================================")
    print(" 3D CAVE GAME GENERATION COMPLETE!")
    print(" Godot 4 Main Scene: cave-diving-game/scenes/main_cave.tscn")
    print(" 100m Level Model:   cave-diving-game/assets/cave_tunnel_100m.glb")
    print(" 5km Terrain Model:  cave-diving-game/assets/terrain_5km.glb")
    print(" WebGL 3D Preview:   cave-diving-game/index.html")
    print("=================================================================")


if __name__ == "__main__":
    main()
