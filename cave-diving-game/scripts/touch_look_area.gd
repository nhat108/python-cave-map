extends Control

# Full-screen drag-to-look area (standard mobile FPS convention), except inside the
# joystick/buttons -- listed by name below, since they need to keep handling their own
# touches. Update EXCLUDE_NAMES if those siblings get renamed.

signal look_delta(delta: Vector2)

const EXCLUDE_NAMES = ["Joystick", "ButtonUp", "ButtonDown", "ButtonSprint", "ButtonFlashlight", "ButtonView"]

var _touch_index := -2  # -2 = unclaimed, -1 = mouse (desktop testing), >=0 = real touch
var _exclude_nodes: Array[Control] = []

func _ready() -> void:
	mouse_filter = MOUSE_FILTER_IGNORE
	for n in EXCLUDE_NAMES:
		var node = get_node_or_null("../" + n)
		if node:
			_exclude_nodes.append(node)

func _is_excluded(pos: Vector2) -> bool:
	for c in _exclude_nodes:
		if c.get_global_rect().has_point(pos):
			return true
	return false

func _input(event: InputEvent) -> void:
	if event is InputEventScreenTouch:
		if event.pressed and _touch_index == -2:
			if _is_excluded(event.position):
				return
			_touch_index = event.index
		elif not event.pressed and event.index == _touch_index:
			_touch_index = -2
	elif event is InputEventScreenDrag and event.index == _touch_index:
		look_delta.emit(event.relative)
		get_viewport().set_input_as_handled()
	elif event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
		if event.pressed and _touch_index == -2:
			if _is_excluded(event.position):
				return
			_touch_index = -1
		elif not event.pressed and _touch_index == -1:
			_touch_index = -2
	elif event is InputEventMouseMotion and _touch_index == -1:
		look_delta.emit(event.relative)
