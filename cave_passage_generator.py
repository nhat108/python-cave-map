"""Parametric cave passage generator.

Replaces the old voxel/marching-cubes cave (cave_tunnel_generator.py), whose
entrance connectivity was impossible to verify without extensive reverse
engineering and turned out to be broken. This generator instead sweeps a tube
mesh along an explicit 3D path, so the passage's shape and its connection to
the surface are known and checkable by construction, not discovered after the
fact.

World coordinates are used directly (no offset transform needed when placed
in the Godot scene) and the entrance is deliberately positioned right under
the existing sinkhole hole in terrain_5km.glb at world (0, -4.5).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import trimesh
from scipy.interpolate import CubicSpline, PchipInterpolator

RNG_SEED = 20260806


def _resample_path(points: np.ndarray, radii: np.ndarray, samples_per_segment: int = 14):
    """Interpolate the control points and radii into a dense, smooth path.

    Positions use a cubic spline with clamped endpoint tangents (direction of the adjacent
    control points) instead of the default 'not-a-knot' fit, which let the global curve
    overshoot at the entrance: the first stretch of path briefly curved backward (+Z) and
    tilted the entrance ring enough to poke a fin of rock up out of the water.

    Radii use PCHIP instead of a cubic spline. A plain cubic spline through sharply
    alternating chamber/constriction radii (e.g. 8.5, 2.4, 8.0, 2.4, ...) overshoots past
    its control values between knots -- one constriction meant to be 2.4 dipped to 1.4
    mid-segment, tight enough to risk sealing the passage. PCHIP is shape-preserving: it
    never exceeds the min/max of the two control values it's interpolating between.
    """
    t = np.arange(len(points))
    t_dense = np.linspace(0, len(points) - 1, (len(points) - 1) * samples_per_segment + 1)
    d_start = points[1] - points[0]
    d_end = points[-1] - points[-2]
    spline_xyz = CubicSpline(t, points, axis=0, bc_type=((1, d_start), (1, d_end)))
    spline_r = PchipInterpolator(t, radii)
    return spline_xyz(t_dense), spline_r(t_dense)


def _rotation_minimizing_frames(points: np.ndarray) -> np.ndarray:
    """Double-reflection RMF (Wang et al.) so the tube doesn't twist along the path."""
    n = len(points)
    tangents = np.gradient(points, axis=0)
    tangents /= np.linalg.norm(tangents, axis=1, keepdims=True)

    normals = np.zeros((n, 3))
    arbitrary = np.array([0.0, 1.0, 0.0]) if abs(tangents[0][1]) < 0.9 else np.array([1.0, 0.0, 0.0])
    n0 = np.cross(tangents[0], arbitrary)
    normals[0] = n0 / np.linalg.norm(n0)

    for i in range(n - 1):
        v1 = points[i + 1] - points[i]
        c1 = np.dot(v1, v1)
        if c1 < 1e-12:
            normals[i + 1] = normals[i]
            continue
        r_l = normals[i] - (2.0 / c1) * np.dot(v1, normals[i]) * v1
        t_l = tangents[i] - (2.0 / c1) * np.dot(v1, tangents[i]) * v1
        v2 = tangents[i + 1] - t_l
        c2 = np.dot(v2, v2)
        normals[i + 1] = r_l if c2 < 1e-12 else r_l - (2.0 / c2) * np.dot(v2, r_l) * v2
        normals[i + 1] /= np.linalg.norm(normals[i + 1])
    return normals, tangents


def build_tube(
    control_points: list[tuple[float, float, float]],
    control_radii: list[float],
    rng: np.random.Generator,
    ring_segments: int = 28,
    cap_start: bool = False,
    cap_end: bool = True,
    roughness: float = 0.14,
    floor_flatten: float = 0.6,
) -> trimesh.Trimesh:
    """Sweep an irregular tube along a path. Returns a Trimesh with the interior hollow.

    A plain noisy circle still silhouettes as a tube ("ruot ngua" / intestine) no matter how
    rough its surface is. Three extra touches break that: a slowly-varying elliptical squash
    changes the cross-section shape itself along the path (tall fissure here, wide gap there),
    two octaves of angular noise give both rock-scale and grain-scale irregularity, and a
    world-space floor clip flattens the lower part of each ring like settled sediment/debris
    instead of staying circular all the way around.
    """
    pts = np.array(control_points, dtype=np.float64)
    radii = np.array(control_radii, dtype=np.float64)
    path, path_r = _resample_path(pts, radii)
    normals, tangents = _rotation_minimizing_frames(path)
    binormals = np.cross(tangents, normals)

    n_rings = len(path)
    n_ctrl = len(control_points)
    angle = np.linspace(0, 2 * np.pi, ring_segments, endpoint=False)

    # Coarse octave (few wide lobes -> scallops/boulders) + fine octave (many small ripples
    # -> rock grain). Kept well below the amplitude that caused the earlier jagged-fin bug.
    phase_coarse = rng.uniform(0, 2 * np.pi, ring_segments)
    freq_coarse = rng.uniform(1.5, 2.5, ring_segments)
    phase_fine = rng.uniform(0, 2 * np.pi, ring_segments)
    freq_fine = rng.uniform(5.0, 8.0, ring_segments)

    # Elliptical squash, orientation and strength both spline-interpolated from random
    # per-control-point values so the cross-section shape itself drifts along the path
    # instead of always being a noisy circle.
    t_ctrl = np.arange(n_ctrl)
    t_dense = np.linspace(0, n_ctrl - 1, n_rings)
    squash_strength = CubicSpline(t_ctrl, rng.uniform(0.05, 0.25, n_ctrl))(t_dense)
    squash_axis = CubicSpline(t_ctrl, rng.uniform(0, np.pi, n_ctrl))(t_dense)

    verts = np.zeros((n_rings * ring_segments, 3))
    for i in range(n_rings):
        wobble = (
            1.0
            + 0.65 * roughness * np.sin(angle * freq_coarse + phase_coarse + i * 0.1)
            + 0.35 * roughness * np.sin(angle * freq_fine + phase_fine + i * 0.2)
        )
        wobble *= 1.0 + squash_strength[i] * np.cos(2.0 * (angle - squash_axis[i]))
        r = path_r[i] * wobble
        ring = (
            path[i]
            + np.outer(np.cos(angle), normals[i]) * r[:, None]
            + np.outer(np.sin(angle), binormals[i]) * r[:, None]
        )

        # Flatten the lower part of the ring toward a debris/sediment floor instead of
        # leaving it circular. Proportional to each ring's own below-center depth (not a
        # fixed world height), so it adapts as the tube tilts along the path.
        below_center = path[i, 1] - ring[:, 1]
        max_below = below_center.max()
        if max_below > 1e-6:
            floor_level = path[i, 1] - floor_flatten * max_below
            ring[:, 1] = np.maximum(ring[:, 1], floor_level)

        verts[i * ring_segments:(i + 1) * ring_segments] = ring

    faces = []
    for i in range(n_rings - 1):
        for j in range(ring_segments):
            a = i * ring_segments + j
            b = i * ring_segments + (j + 1) % ring_segments
            c = (i + 1) * ring_segments + j
            d = (i + 1) * ring_segments + (j + 1) % ring_segments
            faces.append([a, c, b])
            faces.append([b, c, d])
    faces = np.array(faces)

    if cap_start:
        center_idx = len(verts)
        verts = np.vstack([verts, path[0]])
        for j in range(ring_segments):
            a, b = j, (j + 1) % ring_segments
            faces = np.vstack([faces, [center_idx, b, a]])
    if cap_end:
        center_idx = len(verts)
        verts = np.vstack([verts, path[-1]])
        base = (n_rings - 1) * ring_segments
        for j in range(ring_segments):
            a, b = base + j, base + (j + 1) % ring_segments
            faces = np.vstack([faces, [center_idx, a, b]])

    return trimesh.Trimesh(vertices=verts, faces=faces, process=False)


def _make_spike(base_radius: float, height: float, rng: np.random.Generator, segments: int = 9) -> trimesh.Trimesh:
    """A rough cone/icicle standing on the XZ plane at y=0, apex at (0, height, 0).

    Used for both stalactites and stalagmites -- same shape, just placed and re-based at
    opposite ends of the same wall-normal axis (see _scatter_decorations).
    """
    angle = np.linspace(0, 2 * np.pi, segments, endpoint=False)
    wobble = 1.0 + rng.uniform(-0.18, 0.18, segments)
    base = np.stack(
        [base_radius * wobble * np.cos(angle), np.zeros(segments), base_radius * wobble * np.sin(angle)], axis=1
    )
    verts = np.vstack([base, [0.0, height, 0.0], [0.0, 0.0, 0.0]])
    apex_idx, center_idx = segments, segments + 1
    faces = []
    for j in range(segments):
        a, b = j, (j + 1) % segments
        faces.append([a, b, apex_idx])
        faces.append([center_idx, b, a])
    return trimesh.Trimesh(vertices=verts, faces=np.array(faces), process=False)


def _make_boulder(radius: float, rng: np.random.Generator) -> trimesh.Trimesh:
    mesh = trimesh.creation.icosphere(subdivisions=1, radius=radius)
    noise = 1.0 + rng.uniform(-0.28, 0.28, len(mesh.vertices))
    mesh.vertices = mesh.vertices * noise[:, None]
    return mesh


def _make_sediment_mound(radius: float, rng: np.random.Generator) -> trimesh.Trimesh:
    mesh = trimesh.creation.icosphere(subdivisions=1, radius=radius)
    verts = mesh.vertices.copy()
    verts[:, 1] *= 0.3
    noise = 1.0 + rng.uniform(-0.2, 0.2, len(verts))
    mesh.vertices = verts * noise[:, None]
    return mesh


def _orient_to_wall(local_mesh: trimesh.Trimesh, position: np.ndarray, into_room: np.ndarray, rng: np.random.Generator) -> trimesh.Trimesh:
    """Rotate a mesh built with +Y as its 'grows away from the wall' axis so +Y instead
    points along `into_room`, then move it to `position`. A small random tilt keeps a field
    of these from all pointing exactly the same way.
    """
    up = into_room + rng.uniform(-0.2, 0.2, 3)
    up = up / np.linalg.norm(up)
    ref = rng.normal(size=3)
    ref -= np.dot(ref, up) * up
    while np.linalg.norm(ref) < 1e-6:
        ref = rng.normal(size=3)
        ref -= np.dot(ref, up) * up
    right = ref / np.linalg.norm(ref)
    forward = np.cross(right, up)
    rot = np.column_stack([right, up, forward])
    mesh = local_mesh.copy()
    mesh.vertices = mesh.vertices @ rot.T + position
    return mesh


def _scatter_decorations(
    control_points: list[tuple[float, float, float]],
    control_radii: list[float],
    rng: np.random.Generator,
    skip_start_rings: int = 20,
    min_radius: float = 3.0,
    stride: int = 4,
):
    """Walk the same centerline the tube was swept along and scatter speleothems, boulders
    and sediment mounds near the wall.

    Kept deliberately conservative about *where*: nothing in the first `skip_start_rings`
    (keeps the entrance clear) and nothing where the passage radius is below `min_radius`
    (keeps decor out of the already-tight constrictions), so props can never be what ends up
    sealing a passage the way the bare geometry almost did twice already.
    """
    pts = np.array(control_points, dtype=np.float64)
    radii = np.array(control_radii, dtype=np.float64)
    path, path_r = _resample_path(pts, radii)
    normals, tangents = _rotation_minimizing_frames(path)
    binormals = np.cross(tangents, normals)
    world_down = np.array([0.0, -1.0, 0.0])

    speleothem_parts, boulder_parts, sediment_parts = [], [], []

    for i in range(skip_start_rings, len(path), stride):
        r = path_r[i]
        if r < min_radius:
            continue
        theta_down = np.arctan2(np.dot(binormals[i], world_down), np.dot(normals[i], world_down))

        def wall_point(theta: float, depth_frac: float) -> tuple[np.ndarray, np.ndarray]:
            d = np.cos(theta) * normals[i] + np.sin(theta) * binormals[i]
            pos = path[i] + depth_frac * r * d
            return pos, -d  # position, into-room direction

        if rng.uniform() < 0.7:
            pos, into_room = wall_point(theta_down + rng.uniform(-0.8, 0.8), 0.82)
            height = r * rng.uniform(0.18, 0.4)
            spike = _make_spike(height * rng.uniform(0.12, 0.22), height, rng)
            stalagmite = _orient_to_wall(spike, pos, into_room, rng)
            speleothem_parts.append(stalagmite)

        if rng.uniform() < 0.7:
            pos, into_room = wall_point(theta_down + np.pi + rng.uniform(-0.8, 0.8), 0.82)
            height = r * rng.uniform(0.18, 0.4)
            spike = _make_spike(height * rng.uniform(0.12, 0.22), height, rng)
            stalactite = _orient_to_wall(spike, pos, into_room, rng)
            speleothem_parts.append(stalactite)

        if rng.uniform() < 0.5:
            pos, into_room = wall_point(theta_down + rng.uniform(-1.1, 1.1), 0.85)
            boulder = _orient_to_wall(_make_boulder(r * rng.uniform(0.10, 0.22), rng), pos, into_room, rng)
            boulder_parts.append(boulder)

        if rng.uniform() < 0.45:
            pos, into_room = wall_point(theta_down + rng.uniform(-1.0, 1.0), 0.88)
            mound = _orient_to_wall(_make_sediment_mound(r * rng.uniform(0.18, 0.38), rng), pos, into_room, rng)
            sediment_parts.append(mound)

    return speleothem_parts, boulder_parts, sediment_parts


def build_cave(seed: int = RNG_SEED) -> trimesh.Trimesh:
    rng = np.random.default_rng(seed)

    # Main passage: entrance (right under the terrain hole at world (0,-4.5)) winding
    # down to a large dead-end chamber. World Y=3.5 matches the real terrain height
    # measured around the hole; the entrance ring sits just below it so it's reachable
    # by falling straight through the hole.
    main_points = [
        (0.0, 3.5, -4.5),
        (0.0, 0.0, -5.0),
        (1.0, -5.0, -9.0),
        (3.0, -9.0, -15.0),
        (2.0, -14.0, -23.0),
        (-2.0, -18.0, -31.0),
        (-6.0, -20.0, -41.0),
        (-10.0, -24.0, -53.0),
        (-14.0, -26.0, -65.0),
        (-12.0, -22.0, -77.0),
        (-8.0, -20.0, -89.0),
        (-10.0, -24.0, -101.0),
    ]
    # Entrance ring is deliberately much wider than the ~8x11m real terrain hole so any
    # point falling through it lands inside the tube. Past that, real cave passages don't
    # taper smoothly -- they alternate between big rooms and tight squeezes -- so the radii
    # swing hard between ~2.4 (constriction, still 2x the swept-noise margin above a player)
    # and 6.5-8 (chamber) instead of the old gentle 2.8-8.5 glide.
    main_radii = [8.5, 6.0, 3.0, 2.4, 5.5, 2.6, 8.0, 2.4, 3.0, 7.0, 2.8, 6.5]

    # Branch: splits off the big junction chamber at main_points[6]. Starts noticeably
    # smaller than that chamber's radius so it reads as a side passage opening out of the
    # room instead of two same-size tubes crossing through each other.
    branch_points = [
        (-6.0, -20.0, -41.0),
        (-15.0, -16.0, -44.0),
        (-24.0, -13.0, -47.0),
        (-32.0, -10.0, -50.0),
    ]
    branch_radii = [3.0, 2.2, 4.5, 2.0]

    main_tube = build_tube(main_points, main_radii, rng, cap_start=False, cap_end=True)
    branch_tube = build_tube(branch_points, branch_radii, rng, cap_start=False, cap_end=True)

    cave = trimesh.util.concatenate([main_tube, branch_tube])
    cave.vertex_normals  # force normal computation while topology is still simple
    cave.invert()  # tube faces point outward by construction; flip so interior is visible from inside

    spel_main, boulder_main, sediment_main = _scatter_decorations(main_points, main_radii, rng)
    spel_branch, boulder_branch, sediment_branch = _scatter_decorations(
        branch_points, branch_radii, rng, skip_start_rings=4
    )

    def _combine(parts_a, parts_b):
        parts = parts_a + parts_b
        if not parts:
            return None
        mesh = trimesh.util.concatenate(parts)
        mesh.vertex_normals
        return mesh

    speleothems = _combine(spel_main, spel_branch)
    boulders = _combine(boulder_main, boulder_branch)
    sediment = _combine(sediment_main, sediment_branch)

    return cave, speleothems, boulders, sediment, main_points, branch_points


if __name__ == "__main__":
    cave, speleothems, boulders, sediment, main_points, branch_points = build_cave()
    print(f"Cave mesh: {len(cave.vertices)} verts, {len(cave.faces)} faces, watertight={cave.is_watertight}")
    for name, mesh in [("Speleothems", speleothems), ("Boulders", boulders), ("Sediment", sediment)]:
        if mesh is not None:
            print(f"{name}: {len(mesh.vertices)} verts, {len(mesh.faces)} faces")
    out = Path("cave-diving-game/assets/cave_passage_v2.glb")
    out.parent.mkdir(parents=True, exist_ok=True)
    scene = trimesh.Scene()
    scene.add_geometry(cave, node_name="CavePassage", geom_name="CavePassage")
    if speleothems is not None:
        scene.add_geometry(speleothems, node_name="Speleothems", geom_name="Speleothems")
    if boulders is not None:
        scene.add_geometry(boulders, node_name="Boulders", geom_name="Boulders")
    if sediment is not None:
        scene.add_geometry(sediment, node_name="Sediment", geom_name="Sediment")
    scene.export(out)
    print(f"Exported {out}")
