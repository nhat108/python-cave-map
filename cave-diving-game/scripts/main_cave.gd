extends Node3D

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
		# At the lake surface directly above the cave entrance hole (world ~(0,-4.5)),
		# so testing the cave doesn't require swimming across the whole lake first.
		player.global_transform.origin = Vector3(0.0, 13.0, -4.5)
		player.rotation_degrees.y = 0.0

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
		elif "Water" in node.name:
			# Underground pool: dark and murky, not a bright sky-reflecting surface
			# like the outdoor lake.
			mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
			mat.albedo_color = Color(0.03, 0.10, 0.14, 0.85)
			mat.roughness = 0.25
			mat.metallic = 0.0
			mat.cull_mode = BaseMaterial3D.CULL_DISABLED
			node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		elif "Sediment" in node.name or "sediment" in node.name:
			mat.cull_mode = BaseMaterial3D.CULL_BACK
			mat.albedo_color = Color(0.35, 0.26, 0.18)
			mat.roughness = 0.70
			mat.metallic = 0.0
			mat.metallic_specular = 0.25
			node.create_trimesh_collision()
		elif "Boulders" in node.name or "boulder" in node.name:
			mat.cull_mode = BaseMaterial3D.CULL_BACK
			mat.albedo_color = Color(0.48, 0.42, 0.35)
			mat.roughness = 0.75
			mat.metallic = 0.0
			mat.metallic_specular = 0.25
			node.create_trimesh_collision()
		elif "Speleothems" in node.name:
			mat.cull_mode = BaseMaterial3D.CULL_BACK
			mat.albedo_color = Color(0.55, 0.50, 0.42)
			mat.roughness = 0.60
			mat.metallic = 0.0
			mat.metallic_specular = 0.35
			node.create_trimesh_collision()
		else:
			# Main Limestone Cave Walls Material
			mat.cull_mode = BaseMaterial3D.CULL_DISABLED
			mat.albedo_color = Color(0.42, 0.36, 0.30)
			mat.roughness = 0.85
			mat.metallic = 0.0
			mat.metallic_specular = 0.25
			node.create_trimesh_collision()

		node.material_override = mat
		print("Configured PBR Material & Collision for: ", node.name)

	for child in node.get_children():
		_setup_cave_materials_and_collisions(child)
