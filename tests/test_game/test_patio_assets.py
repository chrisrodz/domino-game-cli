"""Check shipped Blender exports without requiring Blender in CI."""

import json
import struct
from itertools import product
from pathlib import Path

import pytest

ASSETS = Path(__file__).resolve().parents[2] / "domino_game/patio/web/assets"
SPEC = json.loads((ASSETS / "domino-spec.json").read_text())


def glb(name):
    payload = (ASSETS / name).read_bytes()
    magic, version, length = struct.unpack_from("<4sII", payload)
    assert (magic, version, length) == (b"glTF", 2, len(payload))
    json_length, kind = struct.unpack_from("<I4s", payload, 12)
    assert kind == b"JSON"
    return json.loads(payload[20 : 20 + json_length])


def height_bounds(asset, node):
    positions = asset["meshes"][node["mesh"]]["primitives"][0]["attributes"]["POSITION"]
    bounds = asset["accessors"][positions]
    translation = node.get("translation", [0, 0, 0])[1]
    return [bounds[edge][1] + translation for edge in ("min", "max")]


def test_double_six_library_preserves_pips_and_physical_dimensions():
    asset = glb("dominoes.glb")
    roots = {node["name"]: node for node in asset["nodes"] if node["name"].startswith("tile_")}
    assert set(roots) == {f"tile_{left}_{right}" for left in range(7) for right in range(left, 7)}
    for name, root in roots.items():
        _, left, right = name.split("_")
        children = [asset["nodes"][index] for index in root["children"]]
        assert sum(node["name"].startswith("Inset pip") for node in children) == int(left) + int(right)
        body = next(node for node in children if node["name"].startswith("Domino body"))
        backing = next(node for node in children if node["name"].startswith("Domino green backing"))
        body_bottom, body_top = height_bounds(asset, body)
        back_bottom, back_top = height_bounds(asset, backing)
        assert body_top == pytest.approx(SPEC["height"])
        assert back_bottom == pytest.approx(0, abs=1e-7)
        # The green back must be exposed; coplanar ivory causes flickering when face down.
        assert body_bottom > back_bottom + 0.02
        assert back_top < body_bottom + 0.003
        for node in [body, backing]:
            positions = asset["meshes"][node["mesh"]]["primitives"][0]["attributes"]["POSITION"]
            bounds = asset["accessors"][positions]
            assert bounds["max"][0] - bounds["min"][0] == pytest.approx(SPEC["length"])
            assert bounds["max"][2] - bounds["min"][2] == pytest.approx(SPEC["width"])


@pytest.mark.parametrize("name", ["patio.glb", "dominoes.glb"])
def test_pbr_assets_are_self_contained(name):
    asset = glb(name)
    assert all("uri" not in image and "bufferView" in image for image in asset["images"])
    assert all("uri" not in buffer for buffer in asset["buffers"])
    textured = [mat for mat in asset["materials"] if "baseColorTexture" in mat["pbrMetallicRoughness"]]
    assert textured
    for mat in textured:
        assert "normalTexture" in mat
        assert "metallicRoughnessTexture" in mat["pbrMetallicRoughness"]
    assert not any(node["name"].startswith("Presentation") for node in asset["nodes"])


def test_felt_sheen_does_not_wash_out_playing_surface():
    felt = next(mat for mat in glb("patio.glb")["materials"] if mat["name"] == "Bottle green woven baize")
    sheen = felt["extensions"]["KHR_materials_sheen"]["sheenColorFactor"]
    assert max(sheen) < 0.1


def transform_point(point, node):
    if "matrix" in node:
        matrix = node["matrix"]
        return [sum(matrix[column * 4 + row] * point[column] for column in range(3)) + matrix[12 + row] for row in range(3)]
    point = [value * scale for value, scale in zip(point, node.get("scale", [1, 1, 1]), strict=True)]
    x, y, z, w = node.get("rotation", [0, 0, 0, 1])
    # Quaternion rotation, applied after scale and before translation as glTF specifies.
    cross = [y * point[2] - z * point[1], z * point[0] - x * point[2], x * point[1] - y * point[0]]
    second = [y * cross[2] - z * cross[1], z * cross[0] - x * cross[2], x * cross[1] - y * cross[0]]
    return [point[i] + 2 * (w * cross[i] + second[i]) + node.get("translation", [0, 0, 0])[i] for i in range(3)]


def test_foliage_clears_all_four_chairs():
    asset = glb("patio.glb")
    nodes = asset["nodes"]
    parents = {child: index for index, node in enumerate(nodes) for child in node.get("children", [])}

    def world_bounds(index):
        points = []
        for primitive in asset["meshes"][nodes[index]["mesh"]]["primitives"]:
            bounds = asset["accessors"][primitive["attributes"]["POSITION"]]
            for corner in product(*zip(bounds["min"], bounds["max"], strict=True)):
                ancestor = index
                while ancestor is not None:
                    corner = transform_point(corner, nodes[ancestor])
                    ancestor = parents.get(ancestor)
                points.append(corner)
        return [(min(p[axis] for p in points), max(p[axis] for p in points)) for axis in range(3)]

    plants = [
        (node["name"], world_bounds(index))
        for index, node in enumerate(nodes)
        if "mesh" in node
        and node["name"].startswith(("Banana leaf", "Leaf midrib", "Young banana stem", "Layered banana", "Fibrous stem"))
    ]
    chairs = [node for node in nodes if node["name"].startswith("White monobloc chair")]
    assert len(chairs) == 4
    assert plants
    for chair in chairs:
        parts = [world_bounds(index) for index in chair["children"]]
        # Reserve a small gap around the whole seat, not just the solid frame/slats.
        clearance = [(min(p[axis][0] for p in parts) - 0.1, max(p[axis][1] for p in parts) + 0.1) for axis in range(3)]
        for name, bounds in plants:
            overlaps = all(a[0] < b[1] and b[0] < a[1] for a, b in zip(clearance, bounds, strict=True))
            assert not overlaps, f"{name} intrudes into {chair['name']} clearance"
