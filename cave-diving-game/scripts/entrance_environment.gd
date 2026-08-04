extends Node3D

# A compact outdoor entrance: dry shore on the left, a dive pool in the centre,
# and a submerged route that lines up with the imported cave tunnel at Z=100.
const EXTERIOR_LAYER := 4
var shore_material: StandardMaterial3D
var grass_material: StandardMaterial3D
var rock_material: StandardMaterial3D
var water_material: StandardMaterial3D

func _ready() -> void:
	_create_materials()
	# Surface terrain and lake now come from terrain_5km.glb.
	# This script only builds the submerged stone-lined shaft to the cave.
	_create_submerged_shaft()

func _create_materials() -> void:
	shore_material = _material(Color("4e4030"), 0.95, 0.0)
	grass_material = _material(Color("2f5b35"), 0.92, 0.0)
	rock_material = _material(Color("2c3540"), 0.82, 0.05)
	water_material = _material(Color(0.05, 0.35, 0.62, 0.72), 0.08, 0.05)
	water_material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	water_material.cull_mode = BaseMaterial3D.CULL_DISABLED

func _create_shore() -> void:
	# Low grassland surrounds the pond and provides a natural exterior silhouette.
	_add_box("Grassland", Vector3(20.0, 0.35, 18.0), Vector3(11.0, 0.0, 105.5), grass_material, true)
	# The shore is intentionally raised above the pool; the player can walk to its edge.
	_add_box("Shore", Vector3(3.4, 1.4, 13.0), Vector3(8.4, 0.70, 106.0), shore_material, true)
	_add_box("ShoreStep", Vector3(1.1, 0.45, 5.0), Vector3(10.1, 0.23, 106.0), shore_material, true)

func _create_dive_pool() -> void:
	var water := MeshInstance3D.new()
	water.name = "EntranceLake"
	var plane := PlaneMesh.new()
	plane.size = Vector2(8.0, 15.0)
	water.mesh = plane
	water.position = Vector3(13.0, 1.22, 105.0)
	water.material_override = water_material
	water.layers = EXTERIOR_LAYER
	add_child(water)

	# A dark bed makes the pond feel deep while the player controller handles swimming depth.
	_add_box("LakeBed", Vector3(8.0, 0.35, 15.0), Vector3(13.0, -3.0, 105.0), rock_material, false)

func _create_rock_walls() -> void:
	# Large irregular-looking silhouettes frame the pool without blocking the entrance at Z=100.
	_add_rock("WestCliff", Vector3(5.8, 2.5, 110.2), Vector3(3.3, 4.8, 2.7))
	_add_rock("EastCliff", Vector3(17.2, 2.9, 109.5), Vector3(3.6, 5.6, 3.0))
	_add_rock("BackCliff", Vector3(12.8, 3.0, 112.0), Vector3(7.8, 5.8, 2.2))
	_add_rock("ShoreBoulderA", Vector3(9.2, 1.55, 102.5), Vector3(1.6, 1.7, 1.3))
	_add_rock("ShoreBoulderB", Vector3(6.7, 1.35, 103.0), Vector3(1.2, 1.3, 1.1))
	_add_rock("PoolBoulder", Vector3(16.1, 1.45, 103.2), Vector3(1.5, 2.2, 1.4))

func _create_submerged_shaft() -> void:
	# A vertical water shaft at the far edge of the pond descends to the tunnel at Y=-9.
	# Its open top sits beneath the lake surface; the player follows it down before entering.
	_add_box("ShaftWestWall", Vector3(1.3, 10.0, 5.4), Vector3(8.9, -3.8, 99.6), rock_material, false)
	_add_box("ShaftEastWall", Vector3(1.3, 10.0, 5.4), Vector3(15.4, -3.8, 99.6), rock_material, false)
	_add_box("ShaftLakeSide", Vector3(7.8, 10.0, 1.1), Vector3(12.15, -3.8, 102.3), rock_material, false)
	_add_rock("ShaftMouthLeft", Vector3(9.5, -6.3, 98.3), Vector3(1.2, 2.1, 1.4))
	_add_rock("ShaftMouthRight", Vector3(14.7, -6.3, 98.3), Vector3(1.2, 2.1, 1.4))
	_add_rock("ShaftMouthCeiling", Vector3(12.1, -4.6, 98.3), Vector3(3.8, 1.2, 1.4))

func _add_rock(part_name: String, location: Vector3, scale_amount: Vector3) -> void:
	var rock := MeshInstance3D.new()
	rock.name = part_name
	rock.mesh = SphereMesh.new()
	rock.position = location
	rock.scale = scale_amount
	rock.material_override = rock_material
	rock.layers = EXTERIOR_LAYER
	rock.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
	add_child(rock)

func _add_box(part_name: String, size: Vector3, location: Vector3, material: Material, add_collision: bool) -> void:
	var mesh := MeshInstance3D.new()
	mesh.name = part_name
	var box := BoxMesh.new()
	box.size = size
	mesh.mesh = box
	mesh.position = location
	mesh.material_override = material
	mesh.layers = EXTERIOR_LAYER
	mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
	add_child(mesh)
	if add_collision:
		var body := StaticBody3D.new()
		body.name = part_name + "Collision"
		body.position = location
		var collision := CollisionShape3D.new()
		var shape := BoxShape3D.new()
		shape.size = size
		collision.shape = shape
		body.add_child(collision)
		add_child(body)

func _material(color: Color, roughness: float, metallic: float) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.albedo_color = color
	material.roughness = roughness
	material.metallic = metallic
	return material
