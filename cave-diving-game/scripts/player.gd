extends CharacterBody3D

# First-Person Cave Diving Controller for Godot 4 (forward-facing spot headlamp)

const WALK_SPEED = 4.5
const SWIM_SPEED = 6.0
const SPRINT_SPEED = 8.5
const JUMP_VELOCITY = 5.0
const MOUSE_SENSITIVITY = 0.002

var gravity = ProjectSettings.get_setting("physics/3d/default_gravity")
var flashlight_on = true
var is_swimming = false
var third_person_view = false
var swim_up_button_held = false
var swim_down_button_held = false

@onready var head = $Head
@onready var camera = $Head/Camera3D
@onready var flashlight = $Head/Camera3D/SpotLight3D
@onready var third_person_camera = $Head/Camera3D/ThirdPersonSpringArm3D/ThirdPersonCamera3D
@onready var distance_label = $CanvasLayer/Control/DistanceLabel
@onready var flashlight_label = $CanvasLayer/Control/FlashlightLabel
@onready var state_label = $CanvasLayer/Control/StateLabel
@onready var view_mode_button = $CanvasLayer/Control/ViewModeButton
@onready var swim_up_button = $CanvasLayer/Control/SwimUpButton
@onready var swim_down_button = $CanvasLayer/Control/SwimDownButton

func _ready():
	Input.set_mouse_mode(Input.MOUSE_MODE_CAPTURED)
	_update_headlamp_visibility()
	view_mode_button.pressed.connect(_toggle_view_mode)
	swim_up_button.button_down.connect(_on_swim_up_button_down)
	swim_up_button.button_up.connect(_on_swim_up_button_up)
	swim_down_button.button_down.connect(_on_swim_down_button_down)
	swim_down_button.button_up.connect(_on_swim_down_button_up)
	_update_view_mode()

func _update_headlamp_visibility():
	if flashlight:
		flashlight.visible = flashlight_on
	if flashlight_label:
		flashlight_label.text = "[F] Headlamp: " + ("ON" if flashlight_on else "OFF")

func _toggle_view_mode() -> void:
	third_person_view = !third_person_view
	_update_view_mode()

func _update_view_mode() -> void:
	camera.current = !third_person_view
	third_person_camera.current = third_person_view
	view_mode_button.text = "[V] View: " + ("THIRD PERSON" if third_person_view else "FIRST PERSON")

func _on_swim_up_button_down() -> void:
	swim_up_button_held = true

func _on_swim_up_button_up() -> void:
	swim_up_button_held = false

func _on_swim_down_button_down() -> void:
	swim_down_button_held = true

func _on_swim_down_button_up() -> void:
	swim_down_button_held = false

func _unhandled_input(event):
	if event is InputEventMouseMotion and Input.get_mouse_mode() == Input.MOUSE_MODE_CAPTURED:
		head.rotate_y(-event.relative.x * MOUSE_SENSITIVITY)
		camera.rotate_x(-event.relative.y * MOUSE_SENSITIVITY)
		camera.rotation.x = clamp(camera.rotation.x, deg_to_rad(-85), deg_to_rad(85))

	if event.is_action_pressed("toggle_flashlight"):
		flashlight_on = !flashlight_on
		_update_headlamp_visibility()
	if event.is_action_pressed("toggle_view"):
		_toggle_view_mode()

	if event.is_action_pressed("ui_cancel"):
		if Input.get_mouse_mode() == Input.MOUSE_MODE_CAPTURED:
			Input.set_mouse_mode(Input.MOUSE_MODE_VISIBLE)
		else:
			Input.set_mouse_mode(Input.MOUSE_MODE_CAPTURED)

func _physics_process(delta):
	var z_pos = global_transform.origin.z
	
	var cx = 8.0 * sin(0.08 * z_pos) + 4.0 * sin(0.20 * z_pos)
	var cy = 2.5 * cos(0.06 * z_pos) - 1.5 * sin(0.15 * z_pos)
	var r_curr = 4.2 + 2.2 * sin(0.1 * z_pos) + 1.2 * cos(0.25 * z_pos)

	var floor_y = cy - r_curr + 0.8
	var ceiling_y = cy + r_curr - 0.9
	var water_surface_y = cy - 0.10

	var player_y = global_transform.origin.y
	var is_underwater = (player_y < water_surface_y)
	is_swimming = is_underwater

	if state_label:
		state_label.text = "[UNDERWATER DIVING]" if is_underwater else "[AIR / WALKING]"

	if is_underwater:
		var current_speed = SPRINT_SPEED if Input.is_action_pressed("sprint") else SWIM_SPEED
		var input_dir = Input.get_vector("move_left", "move_right", "move_forward", "move_backward")
		var camera_basis = camera.global_transform.basis
		var swim_dir = (camera_basis.x * input_dir.x + camera_basis.z * input_dir.y).normalized()

		var vertical_move = 0.0
		if Input.is_action_pressed("jump") or swim_up_button_held:
			vertical_move += 1.0
		if Input.is_physical_key_pressed(KEY_C) or Input.is_physical_key_pressed(KEY_CTRL) or swim_down_button_held:
			vertical_move -= 1.0

		var idle_sink = -0.8 if vertical_move == 0.0 and input_dir.length() == 0 else 0.0

		velocity.x = move_toward(velocity.x, swim_dir.x * current_speed, current_speed * 5.0 * delta)
		velocity.y = move_toward(velocity.y, (swim_dir.y * current_speed) + (vertical_move * SWIM_SPEED) + idle_sink, SWIM_SPEED * 5.0 * delta)
		velocity.z = move_toward(velocity.z, swim_dir.z * current_speed, current_speed * 5.0 * delta)

	else:
		velocity.y -= gravity * delta

		if Input.is_action_just_pressed("jump") and is_on_floor():
			velocity.y = JUMP_VELOCITY

		var current_speed = SPRINT_SPEED if Input.is_action_pressed("sprint") else WALK_SPEED
		var input_dir = Input.get_vector("move_left", "move_right", "move_forward", "move_backward")
		var direction = (head.global_transform.basis * Vector3(input_dir.x, 0, input_dir.y)).normalized()

		if direction:
			velocity.x = direction.x * current_speed
			velocity.z = direction.z * current_speed
		else:
			velocity.x = move_toward(velocity.x, 0, current_speed * 6.0 * delta)
			velocity.z = move_toward(velocity.z, 0, current_speed * 6.0 * delta)

	move_and_slide()

	global_transform.origin.y = clamp(global_transform.origin.y, floor_y, ceiling_y)
	global_transform.origin.x = clamp(global_transform.origin.x, cx - r_curr + 0.6, cx + r_curr - 0.6)

	if distance_label:
		var dist_m = clamp(global_transform.origin.z, 0.0, 100.0)
		distance_label.text = "Cave Position: Z=%.1fm / 100m" % dist_m
