import * as THREE from "three";
import { EffectComposer } from "/vendor/postprocessing/EffectComposer.js";
import { RenderPass } from "/vendor/postprocessing/RenderPass.js";
import { SSAOPass } from "/vendor/postprocessing/SSAOPass.js";
import { OutputPass } from "/vendor/postprocessing/OutputPass.js";

// Contact shading grounds tiles and joinery without baking shadows into moving pieces.
export function createSceneRenderer(renderer, scene, camera) {
  // Avoid offscreen buffers entirely on touch devices and GPUs without float targets.
  if (matchMedia("(pointer: coarse)").matches || !renderer.extensions.has("EXT_color_buffer_float")) {
    return {
      resize() {},
      render() { renderer.render(scene, camera); },
    };
  }
  const target = new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType });
  target.samples = 4;
  const composer = new EffectComposer(renderer, target);
  composer.addPass(new RenderPass(scene, camera));
  const occlusion = new SSAOPass(scene, camera, 1, 1, 16);
  occlusion.kernelRadius = 0.32;
  occlusion.minDistance = 0.001;
  occlusion.maxDistance = 0.035;
  composer.addPass(occlusion);
  composer.addPass(new OutputPass());
  return {
    resize(width, height) {
      composer.setSize(width, height);
      occlusion.setSize(Math.ceil(width), Math.ceil(height));
    },
    render() {
      composer.render();
    },
  };
}
