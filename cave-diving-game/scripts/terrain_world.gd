@tool
extends Node3D

# Godot imports the generated GLB with the default layer.  Put only the outdoor
# terrain on layer 3 so the sun affects it while the buried cave stays dark.
const EXTERIOR_LAYER := 4

var terrain_material: StandardMaterial3D
var lake_material: StandardMaterial3D

func _ready() -> void:
	_create_materials()
	_configure_meshes(self)

func _create_materials() -> void:
	# The GLB carries the Python-generated cỏ/đá/cát palette as vertex colors.
	terrain_material = StandardMaterial3D.new()
	terrain_material.vertex_color_use_as_albedo = true
	terrain_material.roughness = 0.88
	terrain_material.metallic = 0.0

	lake_material = StandardMaterial3D.new()
	lake_material.albedo_color = Color(0.035, 0.22, 0.55, 0.74)
	lake_material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	lake_material.roughness = 0.08
	lake_material.metallic = 0.12
	lake_material.cull_mode = BaseMaterial3D.CULL_DISABLED

func _configure_meshes(node: Node) -> void:
	if node is MeshInstance3D:
		node.layers = EXTERIOR_LAYER
		if node.name == "NaturalTerrain5km":
			node.material_override = terrain_material
			node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
			if not Engine.is_editor_hint():
				node.create_trimesh_collision()
		elif node.name == "SurfaceLake":
			node.material_override = lake_material
			node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	for child in node.get_children():
		_configure_meshes(child)
