extends Node3D

# Main Cave Manager: Standard CULL_BACK PBR Cave Materials & Precision Collisions

@onready var cave_level = $CaveLevel
@onready var player = $Player

func _ready():
	print("Initializing 100m Cave Diving Environment with Precision CULL_BACK PBR Headlamp Lighting...")
	_setup_cave_materials_and_collisions(cave_level)

	if player:
		player.global_transform.origin = Vector3(164.6, 7.35, -337.0)
		player.rotation_degrees.y = 0.0

func _setup_cave_materials_and_collisions(node: Node):
	if node is MeshInstance3D:
		var mat = StandardMaterial3D.new()

		if "Water" in node.name or "water" in node.name:
			mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
			mat.albedo_color = Color(0.12, 0.58, 0.85, 0.45) # Clear translucent water
			mat.roughness = 0.05
			mat.metallic = 0.0
			mat.cull_mode = BaseMaterial3D.CULL_DISABLED
			node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		elif "Sediment" in node.name or "sediment" in node.name:
			mat.cull_mode = BaseMaterial3D.CULL_BACK
			mat.albedo_color = Color(0.52, 0.40, 0.28)
			mat.roughness = 0.45
			mat.metallic = 0.0
			mat.specular = 0.35
			node.create_trimesh_collision()
		elif "Boulders" in node.name or "boulder" in node.name:
			mat.cull_mode = BaseMaterial3D.CULL_BACK
			mat.albedo_color = Color(0.72, 0.64, 0.54)
			mat.roughness = 0.65
			mat.metallic = 0.0
			mat.specular = 0.35
			node.create_trimesh_collision()
		elif "Speleothems" in node.name:
			mat.cull_mode = BaseMaterial3D.CULL_BACK
			mat.albedo_color = Color(0.85, 0.78, 0.68)
			mat.roughness = 0.45
			mat.metallic = 0.0
			mat.specular = 0.45
			node.create_trimesh_collision()
		else:
			# Main Limestone Cave Walls Material (Standard Backface Culling for PBR Normal Accuracy!)
			mat.cull_mode = BaseMaterial3D.CULL_BACK
			mat.albedo_color = Color(0.68, 0.60, 0.50)
			mat.roughness = 0.75
			mat.metallic = 0.0
			mat.specular = 0.35
			node.create_trimesh_collision()

		node.material_override = mat
		print("Configured PBR Material & Collision for: ", node.name)

	for child in node.get_children():
		_setup_cave_materials_and_collisions(child)
