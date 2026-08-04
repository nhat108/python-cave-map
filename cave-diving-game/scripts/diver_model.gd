@tool
extends Node3D

# A lightweight procedural cave-diver model.  It is rendered on layer 2 so the
# first-person camera can hide it while editor or third-person cameras can show it.
const MODEL_LAYER := 2

var suit_material: StandardMaterial3D
var rubber_material: StandardMaterial3D
var metal_material: StandardMaterial3D
var glass_material: StandardMaterial3D
var lamp_material: StandardMaterial3D
var swim_time := 0.0

func _ready() -> void:
	# Keep the generated parts visible in the editor as well as at runtime.
	# This makes player.tscn a useful visual preview scene.
	for child in get_children():
		child.free()
	_create_materials()
	_create_body()

func _create_materials() -> void:
	suit_material = _material(Color("17212c"), 0.82, 0.0)
	rubber_material = _material(Color("070b10"), 0.58, 0.0)
	metal_material = _material(Color("3f4d58"), 0.32, 0.72)
	glass_material = _material(Color("102632"), 0.12, 0.2)
	lamp_material = _material(Color("fff0c4"), 0.25, 0.0)
	lamp_material.emission_enabled = true
	lamp_material.emission = Color("ffd27d")
	lamp_material.emission_energy_multiplier = 1.2

func _create_body() -> void:
	# Body and helmet
	_add_part("Torso", CapsuleMesh.new(), Vector3(0, 1.00, 0), Vector3(0.54, 0.40, 0.31), suit_material)
	_add_part("Hips", SphereMesh.new(), Vector3(0, 0.59, 0), Vector3(0.39, 0.23, 0.27), suit_material)
	_add_part("NeckSeal", CylinderMesh.new(), Vector3(0, 1.43, 0), Vector3(0.17, 0.07, 0.17), rubber_material)
	_add_part("Helmet", SphereMesh.new(), Vector3(0, 1.64, 0), Vector3(0.25, 0.27, 0.25), rubber_material)
	_add_part("FaceMask", BoxMesh.new(), Vector3(0, 1.63, -0.22), Vector3(0.31, 0.17, 0.08), glass_material)
	_add_part("MaskRim", BoxMesh.new(), Vector3(0, 1.63, -0.265), Vector3(0.35, 0.21, 0.035), rubber_material)
	_add_part("HeadlampStrap", BoxMesh.new(), Vector3(0, 1.77, -0.05), Vector3(0.46, 0.045, 0.045), rubber_material)
	_add_part("HeadlampMount", BoxMesh.new(), Vector3(0, 1.80, -0.10), Vector3(0.13, 0.08, 0.10), metal_material)
	_add_part("HeadlampHousing", BoxMesh.new(), Vector3(0, 1.83, -0.15), Vector3(0.15, 0.07, 0.12), metal_material)
	_add_part("HeadlampLens", SphereMesh.new(), Vector3(0, 1.83, -0.22), Vector3(0.08, 0.05, 0.025), lamp_material)

	# Life-support pack on the diver's back (+Z).
	for side in [-0.18, 0.18]:
		_add_part("AirTank", CylinderMesh.new(), Vector3(side, 1.10, 0.26), Vector3(0.11, 0.38, 0.11), metal_material)
		_add_part("TankCap", SphereMesh.new(), Vector3(side, 1.49, 0.26), Vector3(0.115, 0.045, 0.115), rubber_material)
	_add_part("Backplate", BoxMesh.new(), Vector3(0, 1.06, 0.19), Vector3(0.38, 0.61, 0.06), rubber_material)
	_add_part("WeightBelt", BoxMesh.new(), Vector3(0, 0.66, 0), Vector3(0.56, 0.075, 0.36), metal_material)

	# Limbs and fins.
	_add_limb("LeftUpperArm", Vector3(-0.39, 1.17, 0), -22.0, 0.23)
	_add_limb("RightUpperArm", Vector3(0.39, 1.17, 0), 22.0, 0.23)
	_add_limb("LeftForearm", Vector3(-0.49, 0.88, -0.01), -10.0, 0.22)
	_add_limb("RightForearm", Vector3(0.49, 0.88, -0.01), 10.0, 0.22)
	_add_part("LeftGlove", SphereMesh.new(), Vector3(-0.53, 0.65, -0.02), Vector3(0.10, 0.13, 0.09), rubber_material)
	_add_part("RightGlove", SphereMesh.new(), Vector3(0.53, 0.65, -0.02), Vector3(0.10, 0.13, 0.09), rubber_material)
	_add_leg("LeftLeg", Vector3(-0.17, 0.59, 0))
	_add_leg("RightLeg", Vector3(0.17, 0.59, 0))

func _add_limb(part_name: String, position: Vector3, angle_degrees: float, length: float) -> void:
	var arm := _add_part(part_name, CapsuleMesh.new(), position, Vector3(0.15, length, 0.16), suit_material)
	arm.rotation.z = deg_to_rad(angle_degrees)

func _add_leg(part_name: String, hip_position: Vector3) -> void:
	# The pivot stays at the hip, so a kick never pulls the leg away from the torso.
	var hip_pivot := Node3D.new()
	hip_pivot.name = part_name
	hip_pivot.position = hip_position
	add_child(hip_pivot)
	_add_part_to(hip_pivot, part_name + "Mesh", CapsuleMesh.new(), Vector3(0, -0.36, 0), Vector3(0.18, 0.36, 0.19), suit_material)
	_add_part_to(hip_pivot, part_name.replace("Leg", "Fin"), BoxMesh.new(), Vector3(0, -0.74, -0.22), Vector3(0.19, 0.06, 0.45), rubber_material)

func _process(delta: float) -> void:
	if Engine.is_editor_hint():
		return
	var diver := get_parent() as CharacterBody3D
	if diver == null:
		return
	var is_swimming: bool = diver.is_swimming
	var is_moving := diver.velocity.length() > 0.2
	var target_rotation_x := -PI * 0.5 if is_swimming else 0.0
	var target_position := Vector3(0.0, 0.82, 0.0) if is_swimming else Vector3.ZERO
	rotation.x = lerp_angle(rotation.x, target_rotation_x, min(delta * 6.0, 1.0))
	position = position.lerp(target_position, min(delta * 6.0, 1.0))
	if is_swimming:
		# Tread gently when idle and use a faster, wider stroke while moving.
		swim_time += delta * (5.5 if is_moving else 2.2)
		_set_swim_pose(sin(swim_time), sin(swim_time * 2.0))
	else:
		_set_swim_pose(0.0, 0.0)

func _set_swim_pose(stroke: float, kick: float) -> void:
	# Wide alternating arm strokes and a flutter-kick that remains visible in third person.
	_set_rotation("LeftUpperArm", Vector3(0.0, 0.0, deg_to_rad(-22.0) + stroke * 0.62))
	_set_rotation("RightUpperArm", Vector3(0.0, 0.0, deg_to_rad(22.0) - stroke * 0.62))
	_set_rotation("LeftForearm", Vector3(0.0, 0.0, deg_to_rad(-10.0) - stroke * 0.48))
	_set_rotation("RightForearm", Vector3(0.0, 0.0, deg_to_rad(10.0) + stroke * 0.48))
	_set_rotation("LeftLeg", Vector3(kick * 0.48, 0.0, 0.0))
	_set_rotation("RightLeg", Vector3(-kick * 0.48, 0.0, 0.0))
	_set_rotation("LeftFin", Vector3(kick * 0.68, 0.0, 0.0))
	_set_rotation("RightFin", Vector3(-kick * 0.68, 0.0, 0.0))

func _set_rotation(part_name: String, rotation_value: Vector3) -> void:
	var part := get_node_or_null(part_name) as Node3D
	if part:
		part.rotation = rotation_value

func _add_part(part_name: String, mesh: PrimitiveMesh, position: Vector3, scale_amount: Vector3, material: Material) -> MeshInstance3D:
	var instance := _create_part(part_name, mesh, position, scale_amount, material)
	add_child(instance)
	return instance

func _add_part_to(parent_node: Node3D, part_name: String, mesh: PrimitiveMesh, position: Vector3, scale_amount: Vector3, material: Material) -> MeshInstance3D:
	var instance := _create_part(part_name, mesh, position, scale_amount, material)
	parent_node.add_child(instance)
	return instance

func _create_part(part_name: String, mesh: PrimitiveMesh, position: Vector3, scale_amount: Vector3, material: Material) -> MeshInstance3D:
	var instance := MeshInstance3D.new()
	instance.name = part_name
	instance.mesh = mesh
	instance.position = position
	instance.scale = scale_amount
	instance.material_override = material
	instance.layers = MODEL_LAYER
	instance.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
	return instance

func _material(color: Color, roughness: float, metallic: float) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.albedo_color = color
	material.roughness = roughness
	material.metallic = metallic
	return material
