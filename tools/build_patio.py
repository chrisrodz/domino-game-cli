"""Build original patio and double-six assets with Blender 4.5+.

Run: blender --background --python tools/build_patio.py
"""

import math
import random
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "domino_game/patio/web/assets"
random.seed(66)
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)


def material(name, color, roughness=0.8):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*color, 1)
    shader.inputs["Roughness"].default_value = roughness
    return mat


def texture(mat, kind):
    size = 256
    image = bpy.data.images.new(f"{kind}_texture", width=size, height=size)
    pixels = []
    base = mat.diffuse_color[:3]
    for y in range(size):
        for x in range(size):
            grain = 0.035 if kind == "wood" else 0.018
            noise = random.uniform(-grain, grain)
            if kind == "wood":
                noise += 0.025 * math.sin(y * 0.8 + math.sin(x * 0.04) * 3)
            else:
                noise += 0.012 * math.sin(x * 0.08) * math.cos(y * 0.09)
            pixels.extend([max(0, min(1, c + noise)) for c in base] + [1])
    image.pixels = pixels
    image.pack()
    node = mat.node_tree.nodes.new("ShaderNodeTexImage")
    node.image = image
    mat.node_tree.links.new(node.outputs["Color"], mat.node_tree.nodes.get("Principled BSDF").inputs["Base Color"])


WHITE = material("Warm white molded plastic", (0.83, 0.83, 0.72), 0.47)
WOOD = material("Sun-worn cedar", (0.29, 0.17, 0.075))
texture(WOOD, "wood")
FELT = material("Faded olive tabletop", (0.19, 0.25, 0.13))
texture(FELT, "felt")
EARTH = material("Patio soil", (0.14, 0.20, 0.065))
texture(EARTH, "earth")
GRASS = [material(f"Grass {i}", c) for i, c in enumerate([(0.09, 0.23, 0.035), (0.14, 0.29, 0.055), (0.19, 0.32, 0.065)])]
LEAVES = [material(f"Banana leaf {i}", c) for i, c in enumerate([(0.07, 0.25, 0.055), (0.12, 0.34, 0.07), (0.23, 0.38, 0.09)])]
TRUNK = material("Banana stems", (0.31, 0.34, 0.12))
IVORY = material("Ivory domino resin", (0.92, 0.89, 0.75), 0.32)
INK = material("Recessed charcoal pips", (0.027, 0.038, 0.025), 0.6)
TERRACOTTA = material("Terracotta", (0.46, 0.19, 0.10))


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
        modifier.segments = 3
        bpy.ops.object.modifier_apply(modifier=modifier.name)
        obj.modifiers.new("Weighted corner normals", "WEIGHTED_NORMAL")
    return finish(obj, name, mat, parent)


def rod(name, ends, mat, radius=0.035):
    start, end = (Vector(point) for point in ends)
    direction = end - start
    bpy.ops.mesh.primitive_cylinder_add(vertices=10, radius=radius, depth=direction.length, location=(start + end) / 2)
    obj = bpy.context.object
    obj.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
    return finish(obj, name, mat)


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
    box("Rounded back crown", ((0, 0.73, 2.24), (1.28, 0.14, 0.18), 0.065), WHITE, root)
    box("Back lower rail", ((0, 0.52, 1.22), (1.18, 0.13, 0.15), 0.05), WHITE, root)
    for x in [-0.40, -0.24, -0.08, 0.08, 0.24, 0.40]:
        slat = rod("Open back slat", ((x * 0.8, 0.52, 1.24), (x, 0.73, 2.18)), WHITE, 0.045)
        slat.parent = root
    root.location = location
    root.rotation_euler.z = angle


def leaf(origin, spec, mat):
    angle, length, width, lift = spec
    vertices, faces = [], []
    steps = 14
    for i in range(steps + 1):
        t = i / steps
        spread = math.sin(math.pi * t) ** 0.7 * width
        drop = lift * math.sin(t * math.pi / 1.6) - length * 0.18 * t * t
        for side in [-1, 0, 1]:
            torn = 0.85 if side and i in (5, 9, 12) else 1
            lateral = side * spread * torn
            along = t * length
            vertices.append(
                (
                    origin[0] + along * math.cos(angle) - lateral * math.sin(angle),
                    origin[1] + along * math.sin(angle) + lateral * math.cos(angle),
                    origin[2] + drop - abs(side) * spread * 0.16,
                )
            )
    for i in range(steps):
        for side in range(2):
            a = i * 3 + side
            faces.append((a, a + 1, a + 4, a + 3))
    mesh = bpy.data.meshes.new("Curved banana leaf")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new("Banana leaf", mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    mat.use_backface_culling = False
    for i in range(steps):
        rod("Leaf midrib", (vertices[i * 3 + 1], vertices[(i + 1) * 3 + 1]), TRUNK, 0.013)


def banana_tree(location, height):
    x, y = location
    rod("Banana trunk", ((x, y, 0), (x + 0.16, y, height)), TRUNK, 0.19)
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
box("Table timber frame", ((0, 0, 1.65), (6.1, 4.8, 0.25), 0.08), WOOD)
box("Olive playing surface", ((0, 0, 1.79), (5.77, 4.47, 0.07), 0.035), FELT)
for x in [-2.65, 2.65]:
    for y in [-2.0, 2.0]:
        box("Table leg", ((x, y, 0.8), (0.21, 0.21, 1.6), 0.025), WOOD)
for y in [-1.98, 1.98]:
    box("Table cross brace", ((0, y, 0.48), (5.5, 0.14, 0.14), 0.025), WOOD)
for x in [-2.94, 2.94]:
    box("Wood table rim", ((x, 0, 1.84), (0.15, 4.8, 0.13), 0.035), WOOD)
for y in [-2.32, 2.32]:
    box("Wood table rim", ((0, y, 1.84), (5.87, 0.15, 0.13), 0.035), WOOD)
for y in [-2.08, 2.08]:
    box("Domino rack", ((0, y, 1.9), (3.25, 0.12, 0.15), 0.025), WOOD)
chair((0, -3.25, 0), math.pi)
chair((0.1, 3.3, 0), -0.12)
chair((-4.02, 0.15, 0), math.pi / 2 + 0.1)
chair((4.02, 0.15, 0), -math.pi / 2 - 0.08)
for location, height in [
    ((-5.8, 4.3), 4.7),
    ((-2.8, 6.4), 5.2),
    ((0.6, 6.8), 4.6),
    ((4.4, 5.3), 5.1),
    ((6.3, 2.8), 4.1),
    ((-6.4, 0.4), 3.5),
    ((5.8, -3.4), 3.1),
]:
    banana_tree(location, height)

# Grass clusters use one combined mesh, keeping the browser draw count small.
for material_index, mat in enumerate(GRASS):
    vertices, faces = [], []
    for _ in range(2400):
        x, y = random.uniform(-9.5, 9.5), random.uniform(-9.5, 9.5)
        if x * x + y * y > 90 or (abs(x) < 3.6 and abs(y) < 3.1):
            continue
        height = random.uniform(0.08, 0.25)
        angle = random.uniform(0, math.tau)
        a, b = math.cos(angle) * 0.026, math.sin(angle) * 0.026
        index = len(vertices)
        vertices.extend([(x - a, y - b, -0.06), (x + a, y + b, -0.06), (x + height * 0.25, y, height)])
        faces.append((index, index + 1, index + 2))
    mesh = bpy.data.meshes.new("Grass tufts")
    mesh.from_pydata(vertices, [], faces)
    obj = bpy.data.objects.new(f"Grass patch {material_index}", mesh)
    bpy.context.collection.objects.link(obj)
    mesh.materials.append(mat)

for _i in range(16):
    x, y = random.uniform(-8, 8), random.uniform(-8, 8)
    if abs(x) < 4 and abs(y) < 4:
        continue
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=random.uniform(0.1, 0.25), location=(x, y, 0))
    obj = finish(bpy.context.object, "Yard stone", EARTH)
    obj.scale.z = 0.4

# Small familiar table objects, outside the playable area.
for x, y in [(-2.57, 1.83), (2.55, -1.80)]:
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.13, depth=0.25, location=(x, y, 1.98))
    finish(bpy.context.object, "Coffee cup", TERRACOTTA)
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.108, depth=0.012, location=(x, y, 2.112))
    finish(bpy.context.object, "Coffee", INK)
    bpy.ops.mesh.primitive_torus_add(
        major_radius=0.09, minor_radius=0.027, location=(x + 0.15, y, 1.99), rotation=(math.pi / 2, 0, 0)
    )
    finish(bpy.context.object, "Cup handle", TERRACOTTA)

environment = list(bpy.context.scene.objects)
ASSETS.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action="DESELECT")
for obj in environment:
    obj.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(ASSETS / "patio.glb"), export_format="GLB", use_selection=True, export_apply=True)

PIPS = {
    0: [],
    1: [(0, 0)],
    2: [(-1, -1), (1, 1)],
    3: [(-1, -1), (0, 0), (1, 1)],
    4: [(-1, -1), (1, -1), (-1, 1), (1, 1)],
    5: [(-1, -1), (1, -1), (0, 0), (-1, 1), (1, 1)],
    6: [(-1, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (1, 1)],
}
tiles = []
for left in range(7):
    for right in range(left, 7):
        before = set(bpy.context.scene.objects)
        root = bpy.data.objects.new(f"tile_{left}_{right}", None)
        bpy.context.collection.objects.link(root)
        box("Domino body", ((0, 0, 0.065), (0.59, 0.30, 0.13), 0.025), IVORY, root)
        box("Center groove", ((0, 0, 0.131), (0.007, 0.26, 0.004), 0.001), INK, root)
        for side, value in [(-1, left), (1, right)]:
            for px, py in PIPS[value]:
                bpy.ops.mesh.primitive_uv_sphere_add(
                    segments=10, ring_count=6, radius=0.020, location=(side * 0.15 + px * 0.055, py * 0.077, 0.131)
                )
                pip = finish(bpy.context.object, "Inset pip", INK, root)
                pip.scale.z = 0.14
        root.location = (15 + left, right, 0)
        tiles.extend(set(bpy.context.scene.objects) - before)
bpy.ops.object.select_all(action="DESELECT")
for obj in tiles:
    obj.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(ASSETS / "dominoes.glb"), export_format="GLB", use_selection=True, export_apply=True)

bpy.ops.object.light_add(type="SUN", location=(5, -6, 10))
bpy.context.object.name = "Late afternoon sun"
bpy.context.object.rotation_euler = (0.45, -0.5, -0.5)
bpy.context.object.data.energy = 2.2
bpy.context.object.data.angle = 0.15
bpy.ops.object.camera_add(location=(8.8, -11.8, 12))
camera = bpy.context.object
camera.rotation_euler = (Vector((0, 0, 1.5)) - camera.location).to_track_quat("-Z", "Y").to_euler()
bpy.context.scene.camera = camera
camera.data.type = "ORTHO"
camera.data.ortho_scale = 17
bpy.context.scene.world.color = (0.4, 0.4, 0.3)
bpy.context.scene.render.engine = "CYCLES"
bpy.context.scene.cycles.samples = 16
bpy.context.scene.render.resolution_x = 1600
bpy.context.scene.render.resolution_y = 1200
bpy.context.scene.render.resolution_percentage = 100
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(ASSETS / "el-patio.blend"))
print(f"Patio and 28 domino meshes exported to {ASSETS}")
