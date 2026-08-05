extends CharacterBody3D

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
