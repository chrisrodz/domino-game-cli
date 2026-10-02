import * as THREE from "three";
import { OrbitControls } from "/vendor/controls/OrbitControls.js";
import { GLTFLoader } from "/vendor/loaders/GLTFLoader.js";
import { mergeGeometries } from "/vendor/utils/BufferGeometryUtils.js";

const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
const seatLocations = [
  [0, 2.55, 3.5],
  [4.2, 2.55, 0],
  [0, 2.65, -3.5],
  [-4.2, 2.55, 0],
];

export class PatioScene {
  constructor(canvas, onSelect) {
    this.canvas = canvas;
    this.onSelect = onSelect;
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: "high-performance" });
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, 1.75));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.05;
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color("#b8c2a5");
    this.scene.fog = new THREE.Fog("#b8c2a5", 21, 44);
    this.camera = new THREE.PerspectiveCamera(38, 1, 0.1, 70);
    this.camera.position.set(7.7, 9.5, 11.4);
    this.controls = new OrbitControls(this.camera, canvas);
    this.controls.target.set(0, 1.35, 0);
    this.controls.enableDamping = !reducedMotion;
    this.controls.enablePan = false;
    this.controls.minDistance = 8;
    this.controls.maxDistance = 23;
    this.controls.minPolarAngle = 0.06;
    this.controls.maxPolarAngle = Math.PI / 2.6;
    this.controls.saveState();
    this.scene.add(new THREE.HemisphereLight("#fff8df", "#7e8967", 2.4));
    const sun = new THREE.DirectionalLight("#fff1c5", 3.3);
    sun.position.set(-5, 11, 5);
    sun.castShadow = true;
    sun.shadow.mapSize.set(2048, 2048);
    Object.assign(sun.shadow.camera, { left: -12, right: 12, top: 12, bottom: -12, near: 0.5, far: 35 });
    sun.shadow.bias = -0.0002;
    sun.shadow.normalBias = 0.025;
    sun.shadow.radius = 3;
    this.scene.add(sun);
    this.templates = new Map();
    this.boardTiles = new Map();
    this.handTiles = new Map();
    this.hiddenTiles = [];
    this.foliage = [];
    this.selection = null;
    this.raycaster = new THREE.Raycaster();
    this.pointer = new THREE.Vector2();
    this.tags = seatLocations.map((_, index) => {
      const tag = document.createElement("div");
      tag.className = "player-tag";
      tag.innerHTML = '<span class="player-dot"></span><strong></strong><small></small>';
      tag.dataset.player = index;
      document.querySelector("#players").append(tag);
      return tag;
    });
    canvas.addEventListener("pointerdown", (event) => {
      this.down = [event.clientX, event.clientY];
    });
    canvas.addEventListener("pointerup", (event) => {
      if (!this.down || Math.hypot(event.clientX - this.down[0], event.clientY - this.down[1]) > 6) return;
      const rect = canvas.getBoundingClientRect();
      this.pointer.set(
        ((event.clientX - rect.left) / rect.width) * 2 - 1,
        (-(event.clientY - rect.top) / rect.height) * 2 + 1,
      );
      this.raycaster.setFromCamera(this.pointer, this.camera);
      const hit = this.raycaster.intersectObjects([...this.handTiles.values()], true)[0];
      if (hit) this.onSelect(hit.object.userData.tileId);
    });
    this.resizeObserver = new ResizeObserver(() => this.resize());
    this.resizeObserver.observe(canvas.parentElement);
    this.resize();
    this.renderer.setAnimationLoop((time) => this.frame(time));
  }

  async load() {
    const loader = new GLTFLoader();
    const [patio, dominoes] = await Promise.all([
      loader.loadAsync("/assets/patio.glb"),
      loader.loadAsync("/assets/dominoes.glb"),
    ]);
    // Batch static Blender meshes by material; otherwise each leaf vein is a draw call.
    patio.scene.updateMatrixWorld(true);
    const batches = new Map();
    patio.scene.traverse((node) => {
      if (!node.isMesh) return;
      const geometry = node.geometry.clone().applyMatrix4(node.matrixWorld);
      const key = node.material.uuid + Object.keys(geometry.attributes).sort().join(",");
      if (!batches.has(key))
        batches.set(key, { material: node.material, geometries: [], leaf: node.name.includes("Banana_leaf") });
      batches.get(key).geometries.push(geometry);
    });
    for (const batch of batches.values()) {
      const geometry = mergeGeometries(batch.geometries);
      if (!geometry) throw new Error("Could not assemble the Blender patio meshes.");
      const mesh = new THREE.Mesh(geometry, batch.material);
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      this.scene.add(mesh);
      if (batch.leaf) this.foliage.push(mesh);
      for (const source of batch.geometries) source.dispose();
    }
    dominoes.scene.updateMatrixWorld(true);
    dominoes.scene.traverse((node) => {
      const match = node.name.match(/^tile_(\d)_(\d)$/);
      if (!match) return;
      const template = new THREE.Group();
      const inverse = node.matrixWorld.clone().invert();
      const parts = new Map();
      node.traverse((child) => {
        if (!child.isMesh) return;
        if (!parts.has(child.material.uuid))
          parts.set(child.material.uuid, { material: child.material, geometries: [], name: child.name });
        const local = new THREE.Matrix4().multiplyMatrices(inverse, child.matrixWorld);
        parts.get(child.material.uuid).geometries.push(child.geometry.clone().applyMatrix4(local));
      });
      for (const part of parts.values()) {
        const mesh = new THREE.Mesh(mergeGeometries(part.geometries), part.material);
        mesh.name = part.name;
        template.add(mesh);
        part.geometries.forEach((geometry) => geometry.dispose());
      }
      this.templates.set(`${match[1]}-${match[2]}`, template);
    });
    if (this.templates.size !== 28) throw new Error(`Expected 28 Blender dominoes, loaded ${this.templates.size}.`);
  }

  resize() {
    const { width, height } = this.canvas.getBoundingClientRect();
    if (!width || !height) return;
    this.renderer.setSize(width, height, false);
    this.camera.aspect = width / height;
    this.camera.fov = width < 760 ? 53 : 38;
    this.camera.updateProjectionMatrix();
  }

  tile(tile, { hidden = false, selectable = false } = {}) {
    const group = this.templates.get(tile.id).clone(true);
    group.position.set(0, 0, 0);
    group.traverse((node) => {
      if (!node.isMesh) return;
      node.castShadow = true;
      node.receiveShadow = true;
      if (selectable) node.userData.tileId = tile.id;
      if (node.name.startsWith("Domino_body")) node.material = node.material.clone();
    });
    if (hidden) group.rotation.x = Math.PI;
    this.scene.add(group);
    return group;
  }

  remove(group) {
    this.scene.remove(group);
    group.traverse((node) => {
      if (node.isMesh && node.name.startsWith("Domino_body")) node.material.dispose();
    });
  }

  layout(count) {
    if (count <= 7)
      return Array.from({ length: count }, (_, i) => ({ x: (i - (count - 1) / 2) * 0.64, z: -0.15, angle: 0 }));
    const path = [];
    for (let row = 0; row < 4; row++) {
      const reverse = row % 2 === 1;
      for (let col = 0; col < 7; col++)
        path.push({ x: (reverse ? 3 - col : col - 3) * 0.64, z: -1.15 + row * 0.7, angle: reverse ? Math.PI : 0 });
      if (row < 3) path.push({ x: (reverse ? -1 : 1) * 2.23, z: -0.8 + row * 0.7, angle: -Math.PI / 2 });
    }
    return path.slice(0, count);
  }

  update(state, selected) {
    if (!this.templates.size) return;
    this.selection = selected;
    const boardIds = new Set(state.board.map((tile) => tile.id));
    for (const [id, group] of this.boardTiles) {
      if (!boardIds.has(id)) {
        this.remove(group);
        this.boardTiles.delete(id);
      }
    }
    const path = this.layout(state.board.length);
    state.board.forEach((tile, index) => {
      let group = this.boardTiles.get(tile.id);
      if (!group) {
        group = this.tile(tile);
        group.position.set(path[index].x, reducedMotion ? 1.83 : 2.5, path[index].z);
        this.boardTiles.set(tile.id, group);
      }
      const { x, z, angle } = path[index];
      group.userData.target = new THREE.Vector3(x, 1.83, z);
      group.rotation.y = angle + (tile.left > tile.right ? Math.PI : 0) + (tile.left === tile.right ? Math.PI / 2 : 0);
    });
    const hand = state.players[0].hand;
    const handIds = new Set(hand.map((tile) => tile.id));
    for (const [id, group] of this.handTiles) {
      if (!handIds.has(id)) {
        this.remove(group);
        this.handTiles.delete(id);
      }
    }
    hand.forEach((tile, index) => {
      let group = this.handTiles.get(tile.id);
      if (!group) {
        group = this.tile(tile, { selectable: true });
        this.handTiles.set(tile.id, group);
      }
      group.position.set((index - (hand.length - 1) / 2) * 0.4, 1.91, 1.75);
      group.rotation.set(0, Math.PI / 2, 0);
      const legal = state.moves.some((move) => move.tile === tile.id);
      group.position.y += selected === tile.id ? 0.17 : 0;
      group.traverse((node) => {
        if (node.isMesh && node.name.startsWith("Domino_body")) {
          node.material.emissive.set(selected === tile.id ? "#587b38" : "#000000");
          node.material.emissiveIntensity = 0.24;
          node.material.color.set(legal ? "#fff9dd" : "#e5e0c9");
        }
      });
    });
    for (const group of this.hiddenTiles) this.remove(group);
    this.hiddenTiles = [];
    for (let player = 1; player < 4; player++) {
      for (let i = 0; i < state.players[player].count; i++) {
        const reveal = state.players[player].hand;
        const group = this.tile(reveal ? reveal[i] : { id: "0-0" }, { hidden: !reveal });
        const offset = (i - (state.players[player].count - 1) / 2) * 0.37;
        if (player === 2) {
          group.position.set(-offset, reveal ? 1.86 : 1.99, -1.92);
          group.rotation.y = Math.PI / 2;
        } else {
          group.position.set(player === 1 ? 2.62 : -2.62, reveal ? 1.86 : 1.99, offset);
          group.rotation.y = 0;
        }
        this.hiddenTiles.push(group);
      }
    }
    state.players.forEach((player, index) => {
      this.tags[index].classList.toggle("active", state.phase === "playing" && state.turn === index);
      this.tags[index].querySelector("strong").textContent = player.name;
      this.tags[index].querySelector("small").textContent =
        `${player.count} ${player.count === 1 ? "tile" : "tiles"}${player.passed ? " / passed" : ""}`;
    });
  }

  setView(overhead) {
    this.controls.target.set(0, 1.35, 0);
    this.cameraDestination = overhead ? new THREE.Vector3(0, 12.5, 0.15) : new THREE.Vector3(7.7, 9.5, 11.4);
    if (reducedMotion) {
      this.camera.position.copy(this.cameraDestination);
      this.cameraDestination = null;
    }
  }

  frame(time) {
    if (this.cameraDestination) {
      this.camera.position.lerp(this.cameraDestination, 0.09);
      if (this.camera.position.distanceTo(this.cameraDestination) < 0.02) this.cameraDestination = null;
    }
    for (const group of this.boardTiles.values()) {
      if (group.userData.target) group.position.lerp(group.userData.target, reducedMotion ? 1 : 0.17);
    }
    if (!reducedMotion)
      this.foliage.forEach((mesh, index) => {
        mesh.rotation.y = Math.sin(time * 0.0006 + index) * 0.003;
      });
    this.controls.update();
    this.camera.updateMatrixWorld();
    const rect = this.canvas.getBoundingClientRect();
    seatLocations.forEach((location, index) => {
      const projected = new THREE.Vector3(...location).project(this.camera);
      const tag = this.tags[index];
      tag.style.left = `${((projected.x + 1) / 2) * rect.width}px`;
      tag.style.top = `${((-projected.y + 1) / 2) * rect.height}px`;
      tag.hidden = projected.z > 1 || Math.abs(projected.x) > 0.95 || Math.abs(projected.y) > 0.82;
    });
    this.renderer.render(this.scene, this.camera);
  }
}
