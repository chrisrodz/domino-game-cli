"""Deterministic, packed PBR textures that travel with the Blender/glTF assets."""

import bpy
import numpy as np


def material(name, color, roughness=0.8):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*color, 1)
    shader.inputs["Roughness"].default_value = roughness
    return mat


def image_node(mat, name, pixels, *, color=False):
    height, width = pixels.shape[:2]
    image = bpy.data.images.new(name, width=width, height=height, alpha=False)
    image.colorspace_settings.name = "sRGB" if color else "Non-Color"
    rgba = np.ones((height, width, 4), dtype=np.float32)
    rgba[:, :, :3] = pixels
    image.pixels.foreach_set(rgba.ravel())
    image.pack()
    node = mat.node_tree.nodes.new("ShaderNodeTexImage")
    node.image = image
    node.label = name
    return node


def texture(mat, kind):
    """Author albedo, tangent normals and packed roughness without external files."""
    size = 512
    rng = np.random.default_rng(66)
    y, x = np.mgrid[0:size, 0:size] / size
    tau = np.pi * 2
    fine = rng.normal(0, 1, (size, size))
    cloud = np.sin(x * tau * 3 + np.sin(y * tau * 2)) * np.cos(y * tau * 4)
    relief = fine * 0.02
    variation = cloud * 0.035 + fine * 0.014
    strength = 0.5
    if kind == "wood":
        flow = y * tau * 46 + 3 * np.sin(x * tau * 2) + 0.6 * np.sin(x * tau * 7)
        pores = np.maximum(0, np.sin(flow * 3)) ** 18
        variation = np.sin(flow) * 0.13 + np.sin(flow * 0.5) * 0.065 - pores * 0.12 + fine * 0.015
        relief = np.sin(flow) * 0.3 - pores * 0.3
        strength = 1.2
    elif kind == "felt":
        weave = np.sin(x * tau * 128) * np.cos(y * tau * 128)
        variation = fine * 0.023 + weave * 0.035 + cloud * 0.018
        relief = weave * 0.09 + fine * 0.02
        strength = 0.6
    elif kind == "leaf":
        rib = np.maximum(0, np.cos((y * 62 + np.abs(x - 0.5) * 14) * tau)) ** 12
        spine = np.exp(-(((x - 0.5) / 0.013) ** 2))
        variation = rib * 0.10 + spine * 0.3 + np.sin(x * np.pi) * 0.14 - 0.1 + cloud * 0.06
        relief = rib * 0.12 + spine * 0.8
        strength = 1.8
    elif kind == "earth":
        variation = cloud * 0.13 + fine * 0.075
        relief = cloud * 0.3 + fine * 0.15
    elif kind == "clay":
        variation = cloud * 0.08 + fine * 0.025
        relief = fine * 0.075 + cloud * 0.1
    elif kind == "plaster":
        variation = cloud * 0.04 + fine * 0.018
        relief = fine * 0.12
    elif kind == "resin":
        variation = cloud * 0.008 + fine * 0.002
        relief = fine * 0.004
        strength = 0.1
    base = np.array(mat.diffuse_color[:3])
    linear = np.clip(base[None, None, :] * (1 + variation[:, :, None]), 0, 1)
    srgb = np.where(linear <= 0.0031308, linear * 12.92, 1.055 * linear ** (1 / 2.4) - 0.055)
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    shader = nodes.get("Principled BSDF")
    albedo = image_node(mat, f"{mat.name} - albedo", srgb, color=True)
    links.new(albedo.outputs["Color"], shader.inputs["Base Color"])
    dy, dx = np.gradient(relief)
    normal = np.stack((-dx * strength, -dy * strength, np.ones_like(dx)), axis=-1)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    normals = image_node(mat, f"{mat.name} - normal", normal * 0.5 + 0.5)
    mapping = nodes.new("ShaderNodeNormalMap")
    links.new(normals.outputs["Color"], mapping.inputs["Color"])
    links.new(mapping.outputs["Normal"], shader.inputs["Normal"])
    roughness = np.clip(shader.inputs["Roughness"].default_value + variation * 0.2, 0.05, 1)
    orm = np.stack((np.ones_like(x), roughness, np.zeros_like(x)), axis=-1)
    packed = image_node(mat, f"{mat.name} - roughness", orm)
    channels = nodes.new("ShaderNodeSeparateColor")
    links.new(packed.outputs["Color"], channels.inputs["Color"])
    links.new(channels.outputs["Green"], shader.inputs["Roughness"])
    albedo.location = (-620, 280)
    normals.location = (-620, -20)
    packed.location = (-620, -320)
    mapping.location = (-300, -20)
    channels.location = (-300, -320)
