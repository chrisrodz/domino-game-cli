"""Build original patio and double-six assets with Blender 4.5+.

Run: blender --background --python tools/build_patio.py
"""

import json
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "domino_game/patio/web/assets"
sys.path.insert(0, str(ROOT / "tools"))
from patio_details import courtyard, table_details  # noqa: E402
from patio_materials import material, texture  # noqa: E402

SPEC = json.loads((ASSETS / "domino-spec.json").read_text())
random.seed(66)
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)


WHITE = material("Warm white molded plastic", (0.91, 0.89, 0.81), 0.34)
WOOD = material("Oiled Caribbean mahogany", (0.105, 0.044, 0.016), 0.38)
texture(WOOD, "wood")
FELT = material("Bottle green woven baize", (0.015, 0.061, 0.035))
texture(FELT, "felt")
FELT.node_tree.nodes.get("Principled BSDF").inputs["Sheen Weight"].default_value = 0.12
FELT.node_tree.nodes.get("Principled BSDF").inputs["Sheen Tint"].default_value = (0.015, 0.035, 0.02, 1)
EARTH = material("Patio soil", (0.064, 0.074, 0.025))
texture(EARTH, "earth")
GRASS = [material(f"Grass {i}", c) for i, c in enumerate([(0.055, 0.10, 0.025), (0.065, 0.12, 0.030), (0.10, 0.15, 0.045)])]
LEAVES = [
    material(f"Banana leaf {i}", c) for i, c in enumerate([(0.03, 0.11, 0.035), (0.06, 0.16, 0.041), (0.11, 0.21, 0.055)])
]
for mat in LEAVES:
    texture(mat, "leaf")
TRUNK = material("Banana stems", (0.18, 0.22, 0.075))
VEIN = material("Leaf midribs", (0.12, 0.23, 0.065))
IVORY = material("Ivory domino resin", (0.86, 0.80, 0.65), 0.24)
texture(IVORY, "resin")
IVORY.node_tree.nodes.get("Principled BSDF").inputs["Coat Weight"].default_value = 0.28
IVORY.node_tree.nodes.get("Principled BSDF").inputs["Coat Roughness"].default_value = 0.2
INK = material("Recessed charcoal pips", (0.009, 0.012, 0.01), 0.23)
BRASS = material("Brass center spinner", (0.48, 0.35, 0.14), 0.27)
BRASS.node_tree.nodes.get("Principled BSDF").inputs["Metallic"].default_value = 0.8
BACK = material("Deep green domino backing", (0.012, 0.033, 0.024), 0.27)
BACK.node_tree.nodes.get("Principled BSDF").inputs["Coat Weight"].default_value = 0.3


def finish(obj, name, mat, parent=None):
    obj.name = name
    obj.data.materials.append(mat)
    if parent:
        obj.parent = parent
    return obj


def box(name, spec, mat, parent=None):
    location, size, bevel = spec
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        modifier = obj.modifiers.new("Soft molded edges", "BEVEL")
        modifier.width = bevel
        modifier.segments = 1 if "paver" in name else 5 if "Domino" in name else 3
        bpy.ops.object.modifier_apply(modifier=modifier.name)
        obj.modifiers.new("Weighted corner normals", "WEIGHTED_NORMAL")
    # Planar face UVs use the whole texture instead of the cube atlas quarter.
    uv = obj.data.uv_layers.active
    for polygon in obj.data.polygons:
        axis = max(range(3), key=lambda i: abs(polygon.normal[i]))
        axes = [i for i in range(3) if i != axis]
        for index in polygon.loop_indices:
            point = obj.data.vertices[obj.data.loops[index].vertex_index].co
            uv.data[index].uv = tuple(point[i] / size[i] + 0.5 for i in axes)
    return finish(obj, name, mat, parent)


def rod(name, ends, mat, radius=0.035):
    start, end = (Vector(point) for point in ends)
    direction = end - start
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=radius, depth=direction.length, location=(start + end) / 2)
    obj = bpy.context.object
    obj.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    return finish(obj, name, mat)


def curved_rod(name, points, mat, radius=0.035):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = radius
    curve.bevel_resolution = 3
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for point, coordinates in zip(spline.points, points):
        point.co = (*coordinates, 1)
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.convert(target="MESH")
    return finish(bpy.context.object, name, mat)


def chair(location, angle):
    root = bpy.data.objects.new("White monobloc chair", None)
    bpy.context.collection.objects.link(root)
    box("Contoured seat", ((0, 0, 0.92), (1.24, 1.18, 0.15), 0.12), WHITE, root)
    for x in [-0.48, 0.48]:
        for y in [-0.42, 0.42]:
            leg = rod("Splayed chair leg", ((x * 1.2, y * 1.35, 0.04), (x, y, 0.91)), WHITE, 0.075)
            leg.parent = root
        box("Rounded armrest", ((x * 1.22, 0.1, 1.47), (0.12, 1.1, 0.12), 0.055), WHITE, root)
        support = rod("Arm support", ((x * 1.22, -0.3, 0.95), (x * 1.22, -0.3, 1.45)), WHITE, 0.055)
        support.parent = root
        back = rod("Back frame", ((x * 1.15, 0.49, 1.02), (x * 1.22, 0.73, 2.25)), WHITE, 0.085)
        back.parent = root
    crown = curved_rod(
        "Arched chair back",
        [(-0.61 + i * 0.061, 0.73, 2.18 + 0.16 * math.sin(i / 20 * math.pi)) for i in range(21)],
        WHITE,
        0.08,
    )
    crown.parent = root
    box("Back lower rail", ((0, 0.52, 1.22), (1.18, 0.13, 0.15), 0.05), WHITE, root)
    for x in [-0.40, -0.24, -0.08, 0.08, 0.24, 0.40]:
        slat = box("Molded back slat", ((x, 0.635, 1.74), (0.095, 0.07, 0.92), 0.032), WHITE)
        slat.rotation_euler.x = -0.21
        slat.parent = root
    root.location = location
    root.rotation_euler.z = angle


def leaf(origin, spec, mat):
    angle, length, width, lift = spec
    vertices, faces = [], []
    steps = 32
    columns = 9
    for i in range(steps + 1):
        t = i / steps
        spread = math.sin(math.pi * t) ** 0.65 * width
        drop = lift * math.sin(t * math.pi / 1.6) - length * 0.34 * t * t
        for column in range(columns):
            side = column / ((columns - 1) / 2) - 1
            # Narrow tears taper at the edge instead of rectangular missing faces.
            tear = 0.79 if i in (12, 22, 27) and abs(side) > 0.99 else 1
            lateral = side * spread * tear
            along = t * length
            vertices.append(
                (
                    origin[0] + along * math.cos(angle) - lateral * math.sin(angle),
                    origin[1] + along * math.sin(angle) + lateral * math.cos(angle),
                    origin[2] + drop - abs(side) ** 1.5 * spread * 0.25 + math.sin(t * 20 + side * 4) * abs(side) * 0.022,
                )
            )
    for i in range(steps):
        for side in range(columns - 1):
            a = i * columns + side
            faces.append((a, a + 1, a + 1 + columns, a + columns))
    mesh = bpy.data.meshes.new("Curved banana leaf")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    uv = mesh.uv_layers.new(name="Leaf veins")
    for polygon in mesh.polygons:
        for loop_index in polygon.loop_indices:
            vertex_index = mesh.loops[loop_index].vertex_index
            uv.data[loop_index].uv = (vertex_index % columns / (columns - 1), vertex_index // columns / steps)
    obj = bpy.data.objects.new("Banana leaf", mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    mat.use_backface_culling = False
    curved_rod("Leaf midrib", [vertices[i * columns + columns // 2] for i in range(steps + 1)], VEIN, 0.009)


def banana_tree(location, height):
    x, y = location
    bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=0.24, radius2=0.13, depth=height, location=(x + 0.08, y, height / 2))
    trunk = finish(bpy.context.object, "Layered banana pseudostem", TRUNK)
    for polygon in trunk.data.polygons:
        polygon.use_smooth = True
    for i in range(6):
        angle = i * math.tau / 6
        start = (x + math.cos(angle) * 0.19, y + math.sin(angle) * 0.19, 0.1)
        end = (x + 0.14 + math.cos(angle) * 0.12, y + math.sin(angle) * 0.12, height * 0.92)
        rod("Fibrous stem sheath", (start, end), VEIN, 0.027)
    for i in range(7):
        angle = i * 2.399 + random.random() * 0.3
        leaf(
            (x + 0.16, y, height - random.random() * 0.45),
            (angle, random.uniform(2.2, 3.6), random.uniform(0.46, 0.72), random.uniform(0.1, 0.9)),
            LEAVES[i % 3],
        )
    rod("Old stem sheath", ((x + 0.14, y, height * 0.65), (x + 0.23, y, height - 0.3)), WOOD, 0.018)
    for offset in [-0.6, 0.7]:
        stem = (x + offset, y + 0.4, height * 0.46)
        rod("Young banana stem", ((stem[0], stem[1], 0), stem), TRUNK, 0.11)
        for i in range(4):
            leaf(stem, (i * 1.65 + offset, 1.7, 0.4, 0.35), LEAVES[i % 3])


# A finite, gently irregular backyard gives the scene a tabletop-diorama silhouette.
bpy.ops.mesh.primitive_cylinder_add(vertices=72, radius=10.2, depth=0.30, location=(0, 0, -0.22))
finish(bpy.context.object, "Earthen yard", EARTH)
courtyard((box, rod))
box("Table timber frame", ((0, 0, 1.65), (6.6, 6.2, 0.25), 0.08), WOOD)
box("Green playing surface", ((0, 0, 1.79), (6.27, 5.87, 0.07), 0.035), FELT)
for x in [-2.9, 2.9]:
    for y in [-2.7, 2.7]:
        box("Table leg", ((x, y, 0.8), (0.21, 0.21, 1.6), 0.025), WOOD)
for y in [-2.65, 2.65]:
    box("Table cross brace", ((0, y, 0.48), (5.9, 0.14, 0.14), 0.025), WOOD)
for x in [-3.19, 3.19]:
    box("Wood table rim", ((x, 0, 1.84), (0.15, 6.2, 0.13), 0.035), WOOD)
for y in [-2.99, 2.99]:
    box("Wood table rim", ((0, y, 1.84), (6.12, 0.15, 0.13), 0.035), WOOD)
for y in [-2.92, 2.92]:
    box("Domino rack", ((0, y, 1.9), (3.8, 0.10, 0.15), 0.025), WOOD)
table_details((box, rod, curved_rod), (WOOD, BRASS, FELT, INK))
chair((0, -4.0, 0), math.pi)
chair((0.1, 4.0, 0), -0.12)
chair((-4.25, 0.15, 0), math.pi / 2 + 0.1)
chair((4.25, 0.15, 0), -math.pi / 2 - 0.08)
for location, height in [
    ((-5.8, 4.3), 4.7),
    ((-2.8, 6.4), 5.2),
    ((0.6, 6.8), 4.6),
    ((4.4, 5.3), 5.1),
    ((6.3, 2.8), 4.1),
    ((-6.4, 0.4), 3.5),
    ((-7.8, -2.7), 3.1),
]:
    banana_tree(location, height)

for x in [-6.0, 6.0]:
    for y in [-3.8, 3.2]:
        for i in range(11):
            leaf((x, y, 0.82), (i * 2.399, 1.15, 0.14, 0.9), LEAVES[i % 3])

# Grass clusters use one combined mesh, keeping the browser draw count small.
for material_index, mat in enumerate(GRASS):
    vertices, faces = [], []
    for _ in range(2400):
        x, y = random.uniform(-9.5, 9.5), random.uniform(-9.5, 9.5)
        if x * x + y * y > 90 or (abs(x) < 5.9 and abs(y) < 5.55):
            continue
        height = random.uniform(0.035, 0.11)
        angle = random.uniform(0, math.tau)
        a, b = math.cos(angle) * 0.012, math.sin(angle) * 0.012
        index = len(vertices)
        vertices.extend([(x - a, y - b, -0.06), (x + a, y + b, -0.06), (x + height * 0.25, y, height)])
        faces.append((index, index + 1, index + 2))
    mesh = bpy.data.meshes.new("Grass tufts")
    mesh.from_pydata(vertices, [], faces)
    obj = bpy.data.objects.new(f"Grass patch {material_index}", mesh)
    bpy.context.collection.objects.link(obj)
    mesh.materials.append(mat)
    mat.use_backface_culling = False

for _i in range(16):
    x, y = random.uniform(-8, 8), random.uniform(-8, 8)
    if abs(x) < 6 and abs(y) < 5.6:
        continue
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=random.uniform(0.1, 0.25), location=(x, y, 0))
    obj = finish(bpy.context.object, "Yard stone", EARTH)
    obj.scale.z = 0.4

environment = list(bpy.context.scene.objects)
ASSETS.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action="DESELECT")
for obj in environment:
    obj.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(ASSETS / "patio.glb"), export_format="GLB", use_selection=True, export_apply=True)

tiles = []
for left in range(7):
    for right in range(left, 7):
        before = set(bpy.context.scene.objects)
        root = bpy.data.objects.new(f"tile_{left}_{right}", None)
        bpy.context.collection.objects.link(root)
        body = box(
            "Domino body",
            ((0, 0, (SPEC["height"] + 0.024) / 2), (SPEC["length"], SPEC["width"], SPEC["height"] - 0.024), SPEC["bevel"]),
            IVORY,
            root,
        )
        box("Domino green backing", ((0, 0, 0.013), (SPEC["length"], SPEC["width"], 0.026), 0.012), BACK, root)
        box(
            "Center groove",
            ((0, 0, SPEC["height"] - 0.001), (SPEC["dividerWidth"], SPEC["width"] * 0.8, 0.004), 0.001),
            INK,
            root,
        )
        cutters = []
        for side, value in [(-1, left), (1, right)]:
            for cell in SPEC["pips"][value]:
                px, py = cell // 3 - 1, cell % 3 - 1
                location = (side * SPEC["length"] / 4 + px * SPEC["pipSpacing"], py * SPEC["pipSpacing"], SPEC["height"])
                bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=SPEC["pipRadius"], depth=0.034, location=location)
                cutters.append(bpy.context.object)
                bpy.ops.mesh.primitive_uv_sphere_add(
                    segments=24,
                    ring_count=12,
                    radius=SPEC["pipRadius"],
                    location=(location[0], location[1], SPEC["height"] - 0.013),
                )
                pip = finish(bpy.context.object, "Inset pip", INK, root)
                pip.scale.z = 0.25
                for polygon in pip.data.polygons:
                    polygon.use_smooth = True
        if cutters:
            bpy.ops.object.select_all(action="DESELECT")
            for cutter in cutters:
                cutter.select_set(True)
            bpy.context.view_layer.objects.active = cutters[0]
            bpy.ops.object.join()
            cutter = bpy.context.object
            bpy.context.view_layer.objects.active = body
            cut = body.modifiers.new("Recessed pip wells", "BOOLEAN")
            cut.operation = "DIFFERENCE"
            cut.object = cutter
            bpy.ops.object.modifier_apply(modifier=cut.name)
            bpy.data.objects.remove(cutter, do_unlink=True)
        bpy.ops.mesh.primitive_uv_sphere_add(
            segments=24, ring_count=12, radius=SPEC["pinRadius"], location=(0, 0, SPEC["height"] + 0.002)
        )
        pin = finish(bpy.context.object, "Brass center pin", BRASS, root)
        pin.scale.z = 0.5
        bpy.ops.mesh.primitive_torus_add(
            major_segments=32, minor_segments=8, major_radius=0.044, minor_radius=0.0025, location=(0, 0, 0.001)
        )
        finish(bpy.context.object, "Back maker medallion", BRASS, root)
        root.location = (15 + left, right, 0)
        tiles.extend(set(bpy.context.scene.objects) - before)
# Identical details share mesh data in glTF; only the pip-cut ivory bodies are unique.
shared_details = {}
for obj in tiles:
    role = obj.name.split(".")[0]
    if role in {"Inset pip", "Domino green backing", "Center groove", "Brass center pin", "Back maker medallion"}:
        obj.data = shared_details.setdefault(role, obj.data)
bpy.ops.object.select_all(action="DESELECT")
for obj in tiles:
    obj.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(ASSETS / "dominoes.glb"), export_format="GLB", use_selection=True, export_apply=True)


# Keep the editable library separate from a camera-ready arrangement.
def collection(name, objects):
    group = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(group)
    for obj in objects:
        for old in list(obj.users_collection):
            old.objects.unlink(obj)
        group.objects.link(obj)
    return group


collection("01 - Courtyard and furniture", environment)
collection("02 - Double-six master library", tiles)
showcase = collection("03 - Presentation tiles (not exported)", [])
placements = [
    ("1_3", -1.44, 0, 0),
    ("3_5", -0.8, 0, 0),
    ("5_5", -0.32, 0, math.pi / 2),
    ("5_6", 0.16, 0, 0),
    ("2_6", 0.8, 0, math.pi),
    ("2_4", 1.44, 0, 0),
]
placements += [
    (name, (i - 3) * 0.43, -2.55, math.pi / 2) for i, name in enumerate(["0_0", "0_4", "1_5", "2_3", "3_4", "4_6", "6_6"])
]
for name, x, y, angle in placements:
    original = bpy.data.objects[f"tile_{name}"]
    root = original.copy()
    root.name = f"Presentation {name}"
    showcase.objects.link(root)
    root.location = (x, y, 1.83)
    root.rotation_euler.z = angle
    for child in original.children:
        part = child.copy()
        showcase.objects.link(part)
        part.parent = root

bpy.ops.object.light_add(type="SUN", location=(5, -6, 10))
bpy.context.object.name = "Late afternoon sun"
bpy.context.object.rotation_euler = (0.45, -0.5, -0.5)
bpy.context.object.data.energy = 3.0
bpy.context.object.data.color = (1.0, 0.91, 0.76)
bpy.context.object.data.angle = 0.12
bpy.ops.object.camera_add(location=(7.7, -10.5, 10.8))
camera = bpy.context.object
camera.rotation_euler = (Vector((0, 0.4, 1.4)) - camera.location).to_track_quat("-Z", "Y").to_euler()
bpy.context.scene.camera = camera
camera.data.type = "ORTHO"
camera.data.ortho_scale = 13.8
world = bpy.context.scene.world
world.use_nodes = True
world.node_tree.nodes.get("Background").inputs["Color"].default_value = (0.58, 0.72, 0.88, 1)
world.node_tree.nodes.get("Background").inputs["Strength"].default_value = 0.6
bpy.context.scene.view_settings.view_transform = "AgX"
bpy.context.scene.render.engine = "CYCLES"
bpy.context.scene.cycles.samples = 64
bpy.context.scene.cycles.use_denoising = True
bpy.context.scene.render.resolution_x = 1600
bpy.context.scene.render.resolution_y = 1200
bpy.context.scene.render.resolution_percentage = 100
bpy.context.preferences.filepaths.save_version = 0
# Open the native file on the finished composition instead of the last export selection.
bpy.ops.object.select_all(action="DESELECT")
for area in bpy.context.screen.areas:
    if area.type == "VIEW_3D":
        area.spaces.active.region_3d.view_perspective = "CAMERA"
bpy.ops.wm.save_as_mainfile(filepath=str(ASSETS / "el-patio.blend"))
print(f"Patio and 28 domino meshes exported to {ASSETS}")
