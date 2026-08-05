@tool
extends Node3D

# GOD DIVER - single-file procedural cave diver for Godot 4.x
# Attach this script to one Node3D placed under your CharacterBody3D player.
# No imported model, texture, AnimationPlayer, skeleton, or extra scene is needed.

const MODEL_LAYER: int = 2
const FRONT: float = -1.0

@export_category("Model")
@export var body_height: float = 1.82
@export var model_scale: float = 1.0
@export var show_real_light: bool = true
@export var light_range: float = 22.0
@export var light_energy: float = 4.0
@export var hide_in_editor: bool = false

@export_category("Animation")
@export var animation_speed: float = 1.0
@export var walk_threshold: float = 0.25
@export var sprint_threshold: float = 6.0
@export var turn_with_head: bool = true

var suit_material: StandardMaterial3D
var suit_panel_material: StandardMaterial3D
var rubber_material: StandardMaterial3D
var metal_material: StandardMaterial3D
var tank_material: StandardMaterial3D
var glass_material: StandardMaterial3D
var skin_material: StandardMaterial3D
var lamp_material: StandardMaterial3D
var red_material: StandardMaterial3D
var visor_material: StandardMaterial3D
var status_light_material: StandardMaterial3D
var boot_material: StandardMaterial3D
var antenna_material: StandardMaterial3D

var joints: Dictionary = {}
var meshes: Dictionary = {}
var animation_time: float = 0.0
var breath_time: float = 0.0
var current_swim_blend: float = 0.0
var generated_root: Node3D

func _ready() -> void:
	_build_model()

func _notification(what: int) -> void:
	if what == NOTIFICATION_EDITOR_POST_SAVE and Engine.is_editor_hint():
		_build_model()

func _build_model() -> void:
	if generated_root and is_instance_valid(generated_root):
		generated_root.free()
	for child in get_children():
		if child.name == "GeneratedDiver":
			child.free()

	joints.clear()
	meshes.clear()
	_create_materials()

	generated_root = Node3D.new()
	generated_root.name = "GeneratedDiver"
	generated_root.scale = Vector3.ONE * model_scale * (body_height / 1.82)
	generated_root.visible = not (Engine.is_editor_hint() and hide_in_editor)
	add_child(generated_root)
	_create_body()

func _create_materials() -> void:
	suit_material = _material(Color("#28344a"), 0.55, 0.0)
	suit_panel_material = _material(Color("#12182a"), 0.52, 0.0)
	rubber_material = _material(Color("#030609"), 0.50, 0.0)
	metal_material = _material(Color("#46535d"), 0.26, 0.78)
	tank_material = _material(Color("#8a969e"), 0.30, 0.68)
	skin_material = _material(Color("#9a624a"), 0.72, 0.0)
	red_material = _material(Color("#761b1b"), 0.60, 0.0)

	glass_material = _material(Color("#0b2938"), 0.06, 0.12)
	glass_material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	glass_material.albedo_color.a = 0.62
	glass_material.metallic_specular = 0.92

	lamp_material = _material(Color("#fff3c8"), 0.18, 0.0)
	lamp_material.emission_enabled = true
	lamp_material.emission = Color("#ffd68a")
	lamp_material.emission_energy_multiplier = 3.2

	# Bright cyan LED goggle visor, like the reference art.
	visor_material = _material(Color("#083a4a"), 0.15, 0.05)
	visor_material.emission_enabled = true
	visor_material.emission = Color("#6fe8ff")
	visor_material.emission_energy_multiplier = 4.0

	# Small glowing status lights on chest / belt / shoulders.
	status_light_material = _material(Color("#0e3542"), 0.1, 0.0)
	status_light_material.emission_enabled = true
	status_light_material.emission = Color("#63e2ff")
	status_light_material.emission_energy_multiplier = 3.6

	boot_material = _material(Color("#3b2a20"), 0.62, 0.0)
	antenna_material = _material(Color("#1c2226"), 0.32, 0.55)

func _create_body() -> void:
	# Human silhouette: pelvis, tapered torso, shoulders, neck and head.
	var pelvis := _joint("Pelvis", generated_root, Vector3(0.0, 0.92, 0.0))
	_add_ellipsoid("PelvisMesh", pelvis, Vector3(0.0, 0.0, 0.01), Vector3(0.23, 0.205, 0.195), suit_material)
	_add_box("CrotchPanel", pelvis, Vector3(0.0, -0.10, -0.17), Vector3(0.25, 0.18, 0.035), suit_panel_material, Vector3(deg_to_rad(-8.0), 0.0, 0.0))

	var spine := _joint("Spine", pelvis, Vector3(0.0, 0.23, 0.0))
	_add_capsule("Abdomen", spine, Vector3(0.0, 0.11, 0.0), 0.185, 0.34, suit_material)
	_add_ellipsoid("RibCage", spine, Vector3(0.0, 0.36, 0.0), Vector3(0.285, 0.34, 0.205), suit_material)
	_add_box("ChestPanel", spine, Vector3(0.0, 0.38, -0.205), Vector3(0.24, 0.26, 0.025), suit_panel_material, Vector3(deg_to_rad(-3.0), 0.0, 0.0))
	_add_box("LeftChestStrap", spine, Vector3(-0.16, 0.34, -0.218), Vector3(0.035, 0.35, 0.018), rubber_material, Vector3(0.0, 0.0, deg_to_rad(-8.0)))
	_add_box("RightChestStrap", spine, Vector3(0.16, 0.34, -0.218), Vector3(0.035, 0.35, 0.018), rubber_material, Vector3(0.0, 0.0, deg_to_rad(8.0)))
	# Twin glowing chest status lights (rebreather indicators).
	_add_cylinder("ChestLightL", spine, Vector3(-0.08, 0.40, -0.222), 0.042, 0.02, status_light_material, Vector3(deg_to_rad(87.0), 0.0, 0.0))
	_add_cylinder("ChestLightR", spine, Vector3(0.08, 0.40, -0.222), 0.042, 0.02, status_light_material, Vector3(deg_to_rad(87.0), 0.0, 0.0))
	# Larger central chest core light (rebreather gauge), like the reference art.
	_add_cylinder("ChestCoreRing", spine, Vector3(0.0, 0.22, -0.220), 0.068, 0.016, metal_material, Vector3(deg_to_rad(87.0), 0.0, 0.0))
	_add_cylinder("ChestCoreLight", spine, Vector3(0.0, 0.22, -0.226), 0.05, 0.012, status_light_material, Vector3(deg_to_rad(87.0), 0.0, 0.0))
	_add_box("WeightBelt", pelvis, Vector3(0.0, 0.05, 0.0), Vector3(0.31, 0.048, 0.225), rubber_material)
	_add_box("BeltBuckle", pelvis, Vector3(0.0, 0.05, -0.235), Vector3(0.055, 0.044, 0.018), metal_material)
	# Twin glowing hip/belt status lights.
	_add_cylinder("BeltLightL", pelvis, Vector3(-0.16, 0.05, -0.215), 0.036, 0.018, status_light_material, Vector3(deg_to_rad(87.0), 0.0, 0.0))
	_add_cylinder("BeltLightR", pelvis, Vector3(0.16, 0.05, -0.215), 0.036, 0.018, status_light_material, Vector3(deg_to_rad(87.0), 0.0, 0.0))

	var neck := _joint("Neck", spine, Vector3(0.0, 0.71, 0.0))
	_add_joint_bulb("NeckBulb", neck, 0.122, rubber_material)
	_add_cylinder("NeckSeal", neck, Vector3(0.0, -0.015, 0.0), 0.135, 0.09, rubber_material)
	var head := _joint("HeadJoint", neck, Vector3(0.0, 0.18, 0.0))
	_add_ellipsoid("Hood", head, Vector3(0.0, 0.07, 0.005), Vector3(0.205, 0.245, 0.205), rubber_material)
	_add_ellipsoid("VisibleFace", head, Vector3(0.0, 0.055, -0.184), Vector3(0.137, 0.135, 0.027), skin_material)
	_add_mask(head)
	_add_head_lamp(head)

	_add_back_equipment(spine)
	_add_arm(spine, -1.0)
	_add_arm(spine, 1.0)
	_add_leg(pelvis, -1.0)
	_add_leg(pelvis, 1.0)

func _add_mask(head: Node3D) -> void:
	# Wide glowing cyan goggle visor (wraps further around than a flat pane).
	# One continuous lens with no bridge piece crossing in front of it, so it reads as a
	# single glowing band instead of two separate "eyes" like the reference art.
	_add_box("MaskRim", head, Vector3(0.0, 0.085, -0.218), Vector3(0.2, 0.1, 0.04), rubber_material, Vector3(deg_to_rad(-5.0), 0.0, 0.0))
	_add_ellipsoid("MaskGlass", head, Vector3(0.0, 0.085, -0.245), Vector3(0.178, 0.086, 0.03), visor_material, Vector3(deg_to_rad(-5.0), 0.0, 0.0))
	_add_box("MaskStrapL", head, Vector3(-0.176, 0.075, -0.03), Vector3(0.018, 0.032, 0.18), rubber_material, Vector3(0.0, deg_to_rad(-7.0), 0.0))
	_add_box("MaskStrapR", head, Vector3(0.176, 0.075, -0.03), Vector3(0.018, 0.032, 0.18), rubber_material, Vector3(0.0, deg_to_rad(7.0), 0.0))

	# Round comm/ear pods on each side of the head, like the reference headset units.
	_add_cylinder("EarPodL", head, Vector3(-0.205, 0.09, -0.06), 0.055, 0.04, rubber_material, Vector3(0.0, 0.0, deg_to_rad(90.0)))
	_add_cylinder("EarPodR", head, Vector3(0.205, 0.09, -0.06), 0.055, 0.04, rubber_material, Vector3(0.0, 0.0, deg_to_rad(90.0)))

	# Gas-mask style filter/rebreather under the visor, with round intake vents.
	_add_cylinder("Regulator", head, Vector3(0.0, -0.06, -0.235), 0.075, 0.09, rubber_material, Vector3(deg_to_rad(90.0), 0.0, 0.0))
	_add_cylinder("RegulatorVent", head, Vector3(0.0, -0.06, -0.282), 0.05, 0.02, metal_material, Vector3(deg_to_rad(90.0), 0.0, 0.0))
	_add_tube("RegulatorHose", head, Vector3(0.10, -0.06, -0.2), Vector3(0.25, -0.22, 0.13), 0.014, rubber_material)

	# Whip antenna sticking up from the back of the helmet.
	_add_cylinder("AntennaBase", head, Vector3(0.03, 0.28, 0.13), 0.014, 0.03, metal_material)
	_add_tube("Antenna", head, Vector3(0.03, 0.29, 0.13), Vector3(0.05, 0.62, 0.10), 0.006, antenna_material)

func _add_head_lamp(head: Node3D) -> void:
	_add_box("LampStrapFront", head, Vector3(0.0, 0.205, -0.03), Vector3(0.215, 0.024, 0.035), rubber_material)
	_add_box("LampMount", head, Vector3(0.0, 0.245, -0.09), Vector3(0.06, 0.038, 0.05), metal_material)
	_add_cylinder("LampHousing", head, Vector3(0.0, 0.247, -0.15), 0.042, 0.08, metal_material, Vector3(deg_to_rad(90.0), 0.0, 0.0))
	# Warm amber lens (not cyan) so the headlamp doesn't read as a third glowing "eye"
	# above the goggles.
	_add_cylinder("LampLens", head, Vector3(0.0, 0.247, -0.195), 0.026, 0.01, lamp_material, Vector3(deg_to_rad(90.0), 0.0, 0.0))

	if show_real_light and not Engine.is_editor_hint():
		var light := SpotLight3D.new()
		light.name = "ProceduralHeadLamp"
		light.position = Vector3(0.0, 0.247, -0.21)
		light.rotation.x = deg_to_rad(-90.0)
		light.light_color = Color("#bdf2ff")
		light.light_energy = light_energy
		light.spot_range = light_range
		light.spot_angle = 31.0
		light.shadow_enabled = true
		head.add_child(light)

func _add_back_equipment(spine: Node3D) -> void:
	_add_box("BackPlate", spine, Vector3(0.0, 0.34, 0.235), Vector3(0.245, 0.39, 0.045), rubber_material)
	for side in [-1.0, 1.0]:
		var x: float = side * 0.145
		_add_cylinder("Tank_%s" % side, spine, Vector3(x, 0.36, 0.33), 0.105, 0.66, tank_material)
		_add_ellipsoid("TankTop_%s" % side, spine, Vector3(x, 0.70, 0.33), Vector3(0.108, 0.075, 0.108), metal_material)
		_add_ellipsoid("TankBottom_%s" % side, spine, Vector3(x, 0.02, 0.33), Vector3(0.108, 0.065, 0.108), rubber_material)
		_add_cylinder("TankValve_%s" % side, spine, Vector3(x, 0.78, 0.33), 0.035, 0.08, metal_material)
	_add_box("TankBandTop", spine, Vector3(0.0, 0.56, 0.34), Vector3(0.285, 0.035, 0.125), rubber_material)
	_add_box("TankBandBottom", spine, Vector3(0.0, 0.18, 0.34), Vector3(0.285, 0.035, 0.125), rubber_material)

func _add_arm(spine: Node3D, side: float) -> void:
	var prefix := "Left" if side < 0.0 else "Right"
	var shoulder := _joint(prefix + "Shoulder", spine, Vector3(side * 0.335, 0.56, 0.0))
	# Negative Z on the left and positive Z on the right pushes both arms away from the torso.
	shoulder.rotation.z = deg_to_rad(side * 11.0)
	_add_ellipsoid(prefix + "ShoulderPad", shoulder, Vector3(side * 0.018, -0.018, 0.0), Vector3(0.125, 0.115, 0.12), suit_panel_material)
	_add_cylinder(prefix + "ShoulderLight", shoulder, Vector3(side * 0.02, -0.018, -0.118), 0.038, 0.016, status_light_material, Vector3(deg_to_rad(90.0), 0.0, 0.0))
	_add_capsule(prefix + "UpperArmMesh", shoulder, Vector3(side * 0.018, -0.165, 0.0), 0.098, 0.33, suit_material)

	var elbow := _joint(prefix + "Elbow", shoulder, Vector3(side * 0.035, -0.325, 0.0))
	_add_joint_bulb(prefix + "ElbowBulb", elbow, 0.102, suit_material)
	_add_box(prefix + "ElbowPad", elbow, Vector3(0.0, -0.005, -0.075), Vector3(0.075, 0.065, 0.025), suit_panel_material, Vector3(deg_to_rad(-12.0), 0.0, 0.0))
	_add_capsule(prefix + "ForearmMesh", elbow, Vector3(side * 0.012, -0.15, -0.005), 0.082, 0.30, suit_material)

	var wrist := _joint(prefix + "Wrist", elbow, Vector3(side * 0.02, -0.30, -0.01))
	_add_joint_bulb(prefix + "WristBulb", wrist, 0.086, suit_material)
	_add_cylinder(prefix + "WristSeal", wrist, Vector3.ZERO, 0.078, 0.05, rubber_material)
	_add_ellipsoid(prefix + "Glove", wrist, Vector3(0.0, -0.09, -0.018), Vector3(0.082, 0.115, 0.06), rubber_material)
	for finger in range(4):
		var fx: float = (float(finger) - 1.5) * 0.027
		_add_capsule(prefix + "Finger%d" % finger, wrist, Vector3(fx, -0.19, -0.035), 0.017, 0.10, rubber_material)
	_add_capsule(prefix + "Thumb", wrist, Vector3(side * 0.085, -0.12, -0.02), 0.022, 0.09, rubber_material, Vector3(0.0, 0.0, deg_to_rad(side * 35.0)))

func _add_leg(pelvis: Node3D, side: float) -> void:
	var prefix := "Left" if side < 0.0 else "Right"
	var hip := _joint(prefix + "Hip", pelvis, Vector3(side * 0.145, -0.13, 0.0))
	_add_capsule(prefix + "HipJoint", hip, Vector3(0.0, -0.055, 0.0), 0.125, 0.16, suit_material)
	_add_capsule(prefix + "Thigh", hip, Vector3(0.0, -0.225, 0.0), 0.125, 0.45, suit_material)

	var knee := _joint(prefix + "Knee", hip, Vector3(0.0, -0.44, 0.0))
	_add_joint_bulb(prefix + "KneeBulb", knee, 0.13, suit_material)
	_add_box(prefix + "KneePad", knee, Vector3(0.0, -0.015, -0.105), Vector3(0.105, 0.085, 0.028), suit_panel_material, Vector3(deg_to_rad(-10.0), 0.0, 0.0))
	_add_capsule(prefix + "Shin", knee, Vector3(0.0, -0.21, 0.012), 0.105, 0.42, suit_material)

	var ankle := _joint(prefix + "Ankle", knee, Vector3(0.0, -0.41, 0.02))
	_add_joint_bulb(prefix + "AnkleBulb", ankle, 0.109, suit_material)
	_add_cylinder(prefix + "AnkleSeal", ankle, Vector3.ZERO, 0.105, 0.07, rubber_material)
	_add_box(prefix + "Boot", ankle, Vector3(0.0, -0.075, -0.105), Vector3(0.12, 0.085, 0.20), boot_material, Vector3(deg_to_rad(-6.0), 0.0, 0.0))
	_add_box(prefix + "BootSole", ankle, Vector3(0.0, -0.125, -0.09), Vector3(0.125, 0.02, 0.22), rubber_material, Vector3(deg_to_rad(-6.0), 0.0, 0.0))
	var fin := _joint(prefix + "Fin", ankle, Vector3(0.0, -0.07, -0.20))
	_add_wedge_fin(prefix + "FinMesh", fin, side)

	if side < 0.0:
		_add_thigh_holster(hip)

func _add_thigh_holster(hip: Node3D) -> void:
	# Compact dive knife holstered on the left thigh, like the reference art
	# (a small sheathed tool, not a full-size weapon).
	_add_box("HolsterStrap", hip, Vector3(0.0, -0.14, -0.13), Vector3(0.09, 0.025, 0.016), rubber_material, Vector3(deg_to_rad(-8.0), 0.0, 0.0))
	var knife := _joint("ThighKnife", hip, Vector3(-0.02, -0.26, -0.15))
	knife.rotation = Vector3(deg_to_rad(-4.0), deg_to_rad(8.0), deg_to_rad(4.0))
	_add_box("KnifeSheath", knife, Vector3(0.0, -0.02, 0.0), Vector3(0.018, 0.075, 0.012), rubber_material)
	_add_box("KnifeHandle", knife, Vector3(0.0, 0.065, 0.0), Vector3(0.014, 0.035, 0.014), metal_material)
	_add_box("KnifeGuard", knife, Vector3(0.0, 0.035, 0.0), Vector3(0.026, 0.008, 0.016), metal_material)

func _add_wedge_fin(part_name: String, parent: Node3D, side: float) -> void:
	var mesh := ArrayMesh.new()
	var vertices := PackedVector3Array([
		Vector3(-0.105, 0.025, 0.03), Vector3(0.105, 0.025, 0.03),
		Vector3(-0.155, 0.005, -0.43), Vector3(0.155, 0.005, -0.43),
		Vector3(-0.105, -0.025, 0.03), Vector3(0.105, -0.025, 0.03),
		Vector3(-0.155, -0.018, -0.43), Vector3(0.155, -0.018, -0.43)
	])
	var indices := PackedInt32Array([
		0, 2, 1, 1, 2, 3,
		4, 5, 6, 5, 7, 6,
		0, 4, 2, 4, 6, 2,
		1, 3, 5, 5, 3, 7,
		2, 6, 3, 3, 6, 7,
		0, 1, 4, 1, 5, 4
	])
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = vertices
	arrays[Mesh.ARRAY_INDEX] = indices
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	var instance := _mesh_instance(part_name, mesh, rubber_material)
	parent.add_child(instance)

func _process(delta: float) -> void:
	if Engine.is_editor_hint() or not generated_root:
		return
	var diver := get_parent() as CharacterBody3D
	if diver == null:
		return

	var swim_value: Variant = diver.get("is_swimming")
	var is_swimming: bool = bool(swim_value) if swim_value != null else false
	var horizontal_speed: float = Vector2(diver.velocity.x, diver.velocity.z).length()
	var is_moving := horizontal_speed > walk_threshold
	var is_sprinting := horizontal_speed > sprint_threshold
	var on_floor := diver.is_on_floor()
	var head := diver.get_node_or_null("Head") as Node3D

	animation_time += delta * animation_speed
	breath_time += delta * animation_speed
	current_swim_blend = move_toward(current_swim_blend, 1.0 if is_swimming else 0.0, delta * 3.5)

	var swim_rotation: float = -PI * 0.5 * current_swim_blend
	rotation.x = lerp_angle(rotation.x, swim_rotation, clamp(delta * 7.0, 0.0, 1.0))
	position = position.lerp(Vector3(0.0, 0.78 * current_swim_blend, 0.0), clamp(delta * 6.0, 0.0, 1.0))
	if turn_with_head and head:
		rotation.y = lerp_angle(rotation.y, head.rotation.y, clamp(delta * 10.0, 0.0, 1.0))

	if is_swimming:
		_animate_swim(delta, horizontal_speed)
	elif not on_floor:
		_animate_air(diver.velocity.y)
	elif is_moving:
		_animate_walk(delta, horizontal_speed, is_sprinting)
	else:
		_animate_idle(delta)

func _animate_idle(delta: float) -> void:
	generated_root.position = generated_root.position.lerp(Vector3.ZERO, clamp(delta * 8.0, 0.0, 1.0))
	var breath: float = sin(breath_time * 1.7) * 0.028
	_pose("Spine", Vector3(breath * 0.35, 0.0, 0.0), delta, 5.0)
	_pose("HeadJoint", Vector3(-breath * 0.2, sin(breath_time * 0.31) * 0.025, 0.0), delta, 3.0)
	_pose("LeftShoulder", Vector3(breath, deg_to_rad(-3.0), deg_to_rad(-11.0)), delta, 5.0)
	_pose("RightShoulder", Vector3(-breath, deg_to_rad(3.0), deg_to_rad(11.0)), delta, 5.0)
	_pose("LeftElbow", Vector3(deg_to_rad(-8.0), 0.0, deg_to_rad(-2.0)), delta, 5.0)
	_pose("RightElbow", Vector3(deg_to_rad(-8.0), 0.0, deg_to_rad(2.0)), delta, 5.0)
	_pose_legs_neutral(delta)

func _animate_walk(delta: float, speed: float, sprinting: bool) -> void:
	# Split into explicit float assignments for stricter Godot 4 parsers.
	var cadence: float = speed * 1.15
	cadence = maxf(5.4, minf(cadence, 11.5))
	cadence = cadence * animation_speed
	animation_time += delta * cadence
	var phase: float = animation_time
	var amplitude: float = 0.78 if sprinting else clampf(speed * 0.09, 0.32, 0.58)
	var left_swing: float = sin(phase) * amplitude
	var right_swing: float = -left_swing
	var bob: float = absf(sin(phase)) * (0.035 if sprinting else 0.018)
	generated_root.position.y = -bob

	_pose("Spine", Vector3(deg_to_rad(10.0 if sprinting else 3.5), sin(phase) * 0.035, sin(phase) * 0.025), delta, 10.0)
	_pose("Pelvis", Vector3(0.0, -sin(phase) * 0.055, -sin(phase * 2.0) * 0.025), delta, 10.0)
	_pose_leg("Left", left_swing, delta, sprinting)
	_pose_leg("Right", right_swing, delta, sprinting)
	_pose_arm("Left", -left_swing * 0.72, delta, sprinting)
	_pose_arm("Right", -right_swing * 0.72, delta, sprinting)

func _pose_leg(prefix: String, swing: float, delta: float, sprinting: bool) -> void:
	var knee_bend: float = maxf(0.0, -swing) * (1.55 if sprinting else 1.15) + (0.10 if sprinting else 0.04)
	var ankle_comp: float = -knee_bend * 0.42 + swing * 0.10
	_pose(prefix + "Hip", Vector3(swing, 0.0, 0.0), delta, 14.0)
	_pose(prefix + "Knee", Vector3(knee_bend, 0.0, 0.0), delta, 15.0)
	_pose(prefix + "Ankle", Vector3(ankle_comp, 0.0, 0.0), delta, 15.0)
	_pose(prefix + "Fin", Vector3(-swing * 0.12, 0.0, 0.0), delta, 12.0)

func _pose_arm(prefix: String, swing: float, delta: float, sprinting: bool) -> void:
	var side: float = -1.0 if prefix == "Left" else 1.0
	_pose(prefix + "Shoulder", Vector3(swing, 0.0, deg_to_rad(side * 11.0)), delta, 12.0)
	_pose(prefix + "Elbow", Vector3(-abs(swing) * (0.85 if sprinting else 0.48) - 0.10, 0.0, deg_to_rad(side * 2.0)), delta, 13.0)
	_pose(prefix + "Wrist", Vector3(abs(swing) * 0.16, 0.0, 0.0), delta, 12.0)

func _animate_air(vertical_velocity: float) -> void:
	generated_root.position = Vector3.ZERO
	var rise: float = clampf(vertical_velocity / 7.0, -1.0, 1.0)
	_pose_now("Spine", Vector3(deg_to_rad(-4.0), 0.0, 0.0))
	_pose_now("LeftHip", Vector3(-0.28 + rise * 0.12, 0.0, 0.0))
	_pose_now("RightHip", Vector3(0.22 - rise * 0.10, 0.0, 0.0))
	_pose_now("LeftKnee", Vector3(0.82, 0.0, 0.0))
	_pose_now("RightKnee", Vector3(0.58, 0.0, 0.0))
	_pose_now("LeftShoulder", Vector3(-0.22, 0.0, deg_to_rad(-22.0)))
	_pose_now("RightShoulder", Vector3(-0.22, 0.0, deg_to_rad(22.0)))
	_pose_now("LeftElbow", Vector3(-0.35, 0.0, 0.0))
	_pose_now("RightElbow", Vector3(-0.35, 0.0, 0.0))

func _animate_swim(delta: float, speed: float) -> void:
	generated_root.position = generated_root.position.lerp(Vector3.ZERO, clamp(delta * 6.0, 0.0, 1.0))
	var active := speed > walk_threshold
	var rate: float = 4.8 if active else 1.8
	animation_time += delta * rate * animation_speed
	var phase: float = animation_time
	var kick: float = sin(phase * 2.0)
	var stroke: float = sin(phase)
	var glide: float = sin(phase * 0.5)

	_pose("Spine", Vector3(deg_to_rad(3.0) + glide * 0.025, 0.0, 0.0), delta, 7.0)
	_pose("HeadJoint", Vector3(deg_to_rad(-12.0), 0.0, 0.0), delta, 7.0)
	_pose("LeftHip", Vector3(kick * 0.23, 0.0, 0.0), delta, 9.0)
	_pose("RightHip", Vector3(-kick * 0.23, 0.0, 0.0), delta, 9.0)
	_pose("LeftKnee", Vector3(max(0.0, -kick) * 0.48 + 0.06, 0.0, 0.0), delta, 10.0)
	_pose("RightKnee", Vector3(max(0.0, kick) * 0.48 + 0.06, 0.0, 0.0), delta, 10.0)
	_pose("LeftAnkle", Vector3(-kick * 0.24, 0.0, 0.0), delta, 11.0)
	_pose("RightAnkle", Vector3(kick * 0.24, 0.0, 0.0), delta, 11.0)
	_pose("LeftFin", Vector3(-kick * 0.34, 0.0, 0.0), delta, 12.0)
	_pose("RightFin", Vector3(kick * 0.34, 0.0, 0.0), delta, 12.0)

	# Alternating relaxed cave-diving stroke, less cartoony than a wide windmill.
	_pose("LeftShoulder", Vector3(-0.48 + stroke * 0.30, 0.14, deg_to_rad(-18.0)), delta, 8.0)
	_pose("RightShoulder", Vector3(-0.48 - stroke * 0.30, -0.14, deg_to_rad(18.0)), delta, 8.0)
	_pose("LeftElbow", Vector3(-0.58 - stroke * 0.25, 0.0, -0.08), delta, 9.0)
	_pose("RightElbow", Vector3(-0.58 + stroke * 0.25, 0.0, 0.08), delta, 9.0)
	_pose("LeftWrist", Vector3(0.16, 0.0, -0.08), delta, 9.0)
	_pose("RightWrist", Vector3(0.16, 0.0, 0.08), delta, 9.0)

func _pose_legs_neutral(delta: float) -> void:
	for prefix in ["Left", "Right"]:
		_pose(prefix + "Hip", Vector3.ZERO, delta, 6.0)
		_pose(prefix + "Knee", Vector3(0.035, 0.0, 0.0), delta, 6.0)
		_pose(prefix + "Ankle", Vector3.ZERO, delta, 6.0)
		_pose(prefix + "Fin", Vector3.ZERO, delta, 6.0)

func _pose(joint_name: String, target: Vector3, delta: float, speed: float) -> void:
	var node: Node3D = joints.get(joint_name) as Node3D
	if node:
		node.rotation.x = lerp_angle(node.rotation.x, target.x, clamp(delta * speed, 0.0, 1.0))
		node.rotation.y = lerp_angle(node.rotation.y, target.y, clamp(delta * speed, 0.0, 1.0))
		node.rotation.z = lerp_angle(node.rotation.z, target.z, clamp(delta * speed, 0.0, 1.0))

func _pose_now(joint_name: String, target: Vector3) -> void:
	var node: Node3D = joints.get(joint_name) as Node3D
	if node:
		node.rotation = target

func _joint(joint_name: String, parent: Node3D, position_value: Vector3) -> Node3D:
	var node := Node3D.new()
	node.name = joint_name
	node.position = position_value
	parent.add_child(node)
	joints[joint_name] = node
	return node

func _add_capsule(part_name: String, parent: Node3D, pos: Vector3, radius: float, height: float, material: Material, rot: Vector3 = Vector3.ZERO) -> MeshInstance3D:
	var mesh := CapsuleMesh.new()
	mesh.radius = radius
	mesh.height = max(height, radius * 2.0)
	mesh.radial_segments = 16
	mesh.rings = 8
	return _add_mesh(part_name, parent, mesh, pos, Vector3.ONE, material, rot)

func _add_ellipsoid(part_name: String, parent: Node3D, pos: Vector3, size: Vector3, material: Material, rot: Vector3 = Vector3.ZERO) -> MeshInstance3D:
	var mesh := SphereMesh.new()
	mesh.radius = 1.0
	mesh.height = 2.0
	mesh.radial_segments = 20
	mesh.rings = 12
	return _add_mesh(part_name, parent, mesh, pos, size, material, rot)

func _add_joint_bulb(part_name: String, parent: Node3D, radius: float, material: Material) -> MeshInstance3D:
	# A same-material sphere centered exactly on a joint pivot. The capsules on either side
	# taper to a point right at the pivot, so without this they meet tip-to-tip and pinch
	# into a wasp-waist "ball joint" instead of reading as one continuous limb.
	return _add_ellipsoid(part_name, parent, Vector3.ZERO, Vector3.ONE * radius, material)

func _add_cylinder(part_name: String, parent: Node3D, pos: Vector3, radius: float, height: float, material: Material, rot: Vector3 = Vector3.ZERO) -> MeshInstance3D:
	var mesh := CylinderMesh.new()
	mesh.top_radius = radius
	mesh.bottom_radius = radius
	mesh.height = height
	mesh.radial_segments = 18
	return _add_mesh(part_name, parent, mesh, pos, Vector3.ONE, material, rot)

func _add_box(part_name: String, parent: Node3D, pos: Vector3, half_extents: Vector3, material: Material, rot: Vector3 = Vector3.ZERO) -> MeshInstance3D:
	var mesh := BoxMesh.new()
	mesh.size = half_extents * 2.0
	return _add_mesh(part_name, parent, mesh, pos, Vector3.ONE, material, rot)

func _add_tube(part_name: String, parent: Node3D, start: Vector3, finish: Vector3, radius: float, material: Material) -> MeshInstance3D:
	var midpoint := (start + finish) * 0.5
	var length: float = start.distance_to(finish)
	var instance := _add_cylinder(part_name, parent, midpoint, radius, length, material)
	instance.look_at_from_position(midpoint, finish, Vector3.UP)
	instance.rotate_object_local(Vector3.RIGHT, PI * 0.5)
	return instance

func _add_mesh(part_name: String, parent: Node3D, mesh: Mesh, pos: Vector3, scale_value: Vector3, material: Material, rot: Vector3 = Vector3.ZERO) -> MeshInstance3D:
	var instance := _mesh_instance(part_name, mesh, material)
	instance.position = pos
	instance.rotation = rot
	instance.scale = scale_value
	parent.add_child(instance)
	meshes[part_name] = instance
	return instance

func _mesh_instance(part_name: String, mesh: Mesh, material: Material) -> MeshInstance3D:
	var instance := MeshInstance3D.new()
	instance.name = part_name
	instance.mesh = mesh
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
