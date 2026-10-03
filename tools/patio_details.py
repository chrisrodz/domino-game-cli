"""Handcrafted courtyard, table joinery and ceramic details for El Patio."""

import math
import random

import bpy
from patio_materials import material, texture


def lathe(name, profile, mat, location):
    """Revolve a closed cross-section; cups have genuine rims and inner walls."""
    segments = 48
    vertices = [
        (r * math.cos(i * math.tau / segments), r * math.sin(i * math.tau / segments), z)
        for r, z in profile
        for i in range(segments)
    ]
    faces = []
    for row in range(len(profile) - 1):
        for i in range(segments):
            a, b = row * segments + i, row * segments + (i + 1) % segments
            faces.append((a, b, b + segments, a + segments))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    mesh.materials.append(mat)
    for face in mesh.polygons:
        face.use_smooth = True
    return obj


def courtyard(builders):
    box, rod = builders
    mortar = material("Warm limestone grout", (0.25, 0.23, 0.17))
    clay = material("Handmade terracotta pavers", (0.32, 0.135, 0.07), 0.83)
    texture(clay, "clay")
    variants = [clay]
    for i, color in enumerate([(0.37, 0.17, 0.10), (0.28, 0.115, 0.062), (0.40, 0.20, 0.12)]):
        mat = clay.copy()
        mat.name = f"Kiln variation {i}"
        # Tint the same authored maps, keeping the texture payload shared.
        shader = mat.node_tree.nodes.get("Principled BSDF")
        mat.node_tree.links.remove(shader.inputs["Base Color"].links[0])
        shader.inputs["Base Color"].default_value = (*color, 1)
        variants.append(mat)
    box("Courtyard foundation", ((0, 0, -0.095), (11.7, 11.0, 0.13), 0.12), mortar)
    for row in range(15):
        for col in range(16):
            x, y = (col - 7.5) * 0.72, (row - 7) * 0.72
            tile = box("Fired clay paver", ((x, y, -0.035), (0.702, 0.702, 0.07), 0.018), random.choice(variants))
            tile.rotation_euler.z = random.choice([0, math.pi / 2, math.pi, -math.pi / 2])
    cream = material("Limewashed garden wall", (0.64, 0.59, 0.43))
    texture(cream, "plaster")
    cap = material("Weathered limestone coping", (0.46, 0.41, 0.29))
    for x in range(-8, 9, 2):
        box("Garden wall", ((x, 7.5, 0.62), (2, 0.34, 1.4), 0.035), cream)
        box("Wall cap", ((x, 7.5, 1.35), (2.02, 0.48, 0.10), 0.03), cap)
    for x in [-6.0, 6.0]:
        for y in [-3.8, 3.2]:
            lathe(
                "Terracotta planter",
                [
                    (0, 0),
                    (0.30, 0),
                    (0.42, 0.08),
                    (0.55, 0.81),
                    (0.59, 0.84),
                    (0.59, 0.92),
                    (0.50, 0.92),
                    (0.48, 0.80),
                    (0.29, 0.12),
                    (0, 0.12),
                ],
                clay,
                (x, y, 0),
            )
    # A few low boundary posts give the courtyard scale without obscuring play.
    for x in [-5.9, 5.9]:
        rod("Garden edging", ((x, -5.3, -0.025), (x, 5.3, -0.025)), cap, 0.055)


def table_details(builders, palette):
    box, rod, curved_rod = builders
    wood, brass, felt, ink = palette
    for y in [-2.72, 2.72]:
        box("Mortise apron", ((0, y, 1.43), (5.98, 0.14, 0.30), 0.035), wood)
    for x in [-2.92, 2.92]:
        box("Mortise apron", ((x, 0, 1.43), (0.14, 5.44, 0.30), 0.035), wood)
    # Contrasting piping is clear of the outermost hand and all legal board layouts.
    thread = material("Sage felt binding", (0.15, 0.23, 0.13), 0.94)
    for y in [-2.83, 2.83]:
        rod("Felt piping", ((-3.03, y, 1.829), (3.03, y, 1.829)), thread, 0.008)
    for x in [-3.03, 3.03]:
        rod("Felt piping", ((x, -2.83, 1.829), (x, 2.83, 1.829)), thread, 0.008)
    for x in [-3.18, 3.18]:
        for y in [-2.98, 2.98]:
            box("Brass corner cap", ((x, y, 1.909), (0.19, 0.19, 0.016), 0.028), brass)
            for offset in [-0.049, 0.049]:
                bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=6, radius=0.017, location=(x + offset, y, 1.921))
                screw = bpy.context.object
                screw.name = "Corner rivet"
                screw.scale.z = 0.25
                screw.data.materials.append(brass)
    # Inset identity stays on the near wooden rail, outside the felt.
    box("Maker plate", ((0, -3.055, 1.905), (0.83, 0.092, 0.015), 0.018), brass)
    bpy.ops.object.text_add(location=(0, -3.079, 1.915))
    label = bpy.context.object
    label.name = "El Patio maker engraving"
    label.data.body = "E L  P A T I O"
    label.data.align_x = "CENTER"
    label.data.size = 0.054
    label.data.extrude = 0.0004
    bpy.ops.object.convert(target="MESH")
    label.data.materials.append(ink)
    ceramic = material("Sea salt ceramic glaze", (0.73, 0.76, 0.65), 0.22)
    shader = ceramic.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Coat Weight"].default_value = 0.35
    shader.inputs["Coat Roughness"].default_value = 0.18
    coffee = material("Dark espresso", (0.025, 0.008, 0.002), 0.18)
    crema = material("Espresso crema", (0.38, 0.17, 0.046), 0.65)
    for x, y in [(-2.86, 2.56), (2.86, -2.56)]:
        lathe(
            "Ceramic saucer",
            [(0, 0), (0.20, 0), (0.235, 0.025), (0.23, 0.045), (0.15, 0.028), (0, 0.028)],
            ceramic,
            (x, y, 1.829),
        )
        lathe(
            "Espresso cup",
            [
                (0, 0),
                (0.085, 0),
                (0.10, 0.035),
                (0.14, 0.22),
                (0.139, 0.238),
                (0.119, 0.238),
                (0.116, 0.21),
                (0.073, 0.027),
                (0, 0.027),
            ],
            ceramic,
            (x, y, 1.856),
        )
        lathe("Espresso surface", [(0, 0), (0.115, 0), (0.115, 0.004), (0, 0.004)], coffee, (x, y, 2.063))
        points = [
            (x + 0.133 + math.sin(i / 24 * math.pi) * 0.11, y, 1.978 + math.cos(i / 24 * math.pi) * 0.078) for i in range(25)
        ]
        curved_rod("Glazed cup handle", points, ceramic, 0.023)
        points = [(x + 0.108 * math.cos(i * math.tau / 48), y + 0.108 * math.sin(i * math.tau / 48), 2.068) for i in range(49)]
        curved_rod("Crema at cup rim", points, crema, 0.003)
