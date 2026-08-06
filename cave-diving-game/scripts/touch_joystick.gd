extends Control

# Virtual movement joystick. Drag starting inside the base circle; the knob then keeps
# following the same finger even if the drag moves outside the circle (standard mobile
# joystick feel), clamped to MAX_RADIUS. Emits a Vector2 in [-1,1] per axis matching the
# same X/Y convention player.gd's WASD code already uses (Y negative = forward).

signal vector_changed(vec: Vector2)

const MAX_RADIUS = 55.0
const KNOB_RADIUS = 26.0

var _center := Vector2.ZERO
var _knob := Vector2.ZERO
var _touch_index := -2  # -2 = unclaimed, -1 = mouse (desktop testing), >=0 = real touch

func _ready() -> void:
	_center = size / 2.0
	_knob = _center
	mouse_filter = MOUSE_FILTER_IGNORE  # hit-tested manually in _input, not via _gui_input
	set_process_input(true)

func _input(event: InputEvent) -> void:
	if event is InputEventScreenTouch:
		if event.pressed and _touch_index == -2 and get_global_rect().has_point(event.position):
			_touch_index = event.index
			_update_knob(event.position)
			get_viewport().set_input_as_handled()
		elif not event.pressed and event.index == _touch_index:
			_release()
	elif event is InputEventScreenDrag and event.index == _touch_index:
		_update_knob(event.position)
		get_viewport().set_input_as_handled()
	elif event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
		if event.pressed and _touch_index == -2 and get_global_rect().has_point(event.position):
			_touch_index = -1
			_update_knob(event.position)
		elif not event.pressed and _touch_index == -1:
			_release()
	elif event is InputEventMouseMotion and _touch_index == -1:
		_update_knob(event.position)

func _release() -> void:
	_touch_index = -2
	_knob = _center
	vector_changed.emit(Vector2.ZERO)
	queue_redraw()

func _update_knob(global_pos: Vector2) -> void:
	var offset = global_pos - get_global_rect().get_center()
	if offset.length() > MAX_RADIUS:
		offset = offset.normalized() * MAX_RADIUS
	_knob = _center + offset
	vector_changed.emit(offset / MAX_RADIUS)
	queue_redraw()

func _draw() -> void:
	draw_circle(_center, MAX_RADIUS, Color(1, 1, 1, 0.15))
	draw_arc(_center, MAX_RADIUS, 0, TAU, 32, Color(1, 1, 1, 0.4), 2.0)
	draw_circle(_knob, KNOB_RADIUS, Color(1, 1, 1, 0.4))
