import * as THREE from "three";
import { OrbitControls } from "/vendor/controls/OrbitControls.js";
import { GLTFLoader } from "/vendor/loaders/GLTFLoader.js";
import { mergeGeometries } from "/vendor/utils/BufferGeometryUtils.js";
import { RoomEnvironment } from "/vendor/environments/RoomEnvironment.js";
import { createSceneRenderer } from "./scene-renderer.js";
import { layoutBoard } from "./domino-layout.js";
import { previewPlacement } from "./placement-preview.js";

const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
// Your rack leans toward you so pips stay readable from the patio camera.
const HAND_TILT = 0.95;
const HAND_SPACING = 0.43;
const seatLocations = [
  [0, 2.55, 4.15],
  [4.45, 2.55, 0],
  [0, 2.65, -4.15],
  [-4.45, 2.55, 0],
];

export class PatioScene {
  constructor(canvas, { onSelect, onPlace, onPreview, onLand, spec }) {
    this.canvas = canvas;
    this.onSelect = onSelect;
    this.onLand = onLand;
    this.spec = spec;
    this.renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
      powerPreference: "high-performance",
    });
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, 1.75));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFShadowMap;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.04;
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color("#c6cbbb");
    this.scene.fog = new THREE.Fog("#c6cbbb", 22, 48);
    const environment = new RoomEnvironment();
    const pmrem = new THREE.PMREMGenerator(this.renderer);
    this.scene.environment = pmrem.fromScene(environment, 0.04).texture;
    this.scene.environmentIntensity = 0.48;
    environment.dispose();
    pmrem.dispose();
    this.camera = new THREE.PerspectiveCamera(38, 1, 0.1, 70);
    this.camera.position.set(0, 9.2, 10.2);
    this.controls = new OrbitControls(this.camera, canvas);
    this.controls.target.set(0, 1.8, 0);
    this.controls.enableDamping = !reducedMotion;
    this.controls.enablePan = false;
    this.controls.minDistance = 5.5;
    this.controls.maxDistance = 23;
    this.controls.minPolarAngle = 0;
    this.controls.maxPolarAngle = Math.PI / 2.6;
    this.controls.saveState();
    this.scene.add(new THREE.HemisphereLight("#dce9f2", "#706044", 0.85));
    const sun = new THREE.DirectionalLight("#ffe5bf", 3.6);
    sun.position.set(-3, 9, 6);
    sun.castShadow = true;
    const shadowSize = matchMedia("(pointer: coarse)").matches ? 2048 : 4096;
    sun.shadow.mapSize.set(shadowSize, shadowSize);
    Object.assign(sun.shadow.camera, {
      left: -12,
      right: 12,
      top: 12,
      bottom: -12,
      near: 0.5,
      far: 35,
    });
    sun.shadow.bias = -0.0002;
    sun.shadow.normalBias = 0.012;
    sun.shadow.radius = 3;
    this.scene.add(sun);
    const fill = new THREE.DirectionalLight("#c1d8ec", 0.5);
    fill.position.set(5, 5, -5);
    this.scene.add(fill);
    this.templates = new Map();
    this.boardTiles = new Map();
    this.handTiles = new Map();
    this.hiddenTiles = [];
    this.foliage = [];
    this.selection = null;
    this.raycaster = new THREE.Raycaster();
    this.pointer = new THREE.Vector2();
    this.endButtons = ["left", "right", "first"].map((end) => {
      const button = document.createElement("button");
      button.className = "end-port";
      button.dataset.end = end;
      button.hidden = true;
      button.addEventListener("click", () => onPlace(end));
      button.addEventListener("pointerenter", () => onPreview(end));
      button.addEventListener("focus", () => onPreview(end));
      button.addEventListener("pointerleave", () => onPreview(null));
      button.addEventListener("blur", () => onPreview(null));
      document.querySelector("#board-ends").append(button);
      return button;
    });
    this.keyTags = Array.from({ length: 7 }, (_, index) => {
      const tag = document.createElement("span");
      tag.className = "hand-key";
      tag.textContent = index + 1;
      tag.hidden = true;
      document.querySelector("#hand-keys").append(tag);
      return tag;
    });
    this.hovered = null;
    this.playable = new Set();
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
      const id = this.tileAt(event);
      if (id) this.onSelect(id);
    });
    canvas.addEventListener("pointermove", (event) => {
      if (event.pointerType !== "mouse" || event.buttons) return;
      const id = this.tileAt(event);
      const playable = id && this.playable?.has(id) ? id : null;
      canvas.style.cursor = playable ? "pointer" : "";
      if (playable !== this.hovered) {
        this.hovered = playable;
        this.paintHand();
      }
    });
    canvas.addEventListener("pointerleave", () => {
      canvas.style.cursor = "";
      if (this.hovered) {
        this.hovered = null;
        this.paintHand();
      }
    });
    this.pipeline = createSceneRenderer(this.renderer, this.scene, this.camera);
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
    const anisotropy = Math.min(8, this.renderer.capabilities.getMaxAnisotropy());
    for (const asset of [patio, dominoes]) {
      asset.scene.traverse((node) => {
        if (!node.isMesh) return;
        for (const key of ["map", "normalMap", "roughnessMap"]) {
          if (node.material[key]) node.material[key].anisotropy = anisotropy;
        }
      });
    }
    // Batch static Blender meshes by material; otherwise each leaf vein is a draw call.
    patio.scene.updateMatrixWorld(true);
    const batches = new Map();
    patio.scene.traverse((node) => {
      if (!node.isMesh) return;
      const geometry = node.geometry.clone().applyMatrix4(node.matrixWorld);
      const key = node.material.uuid + Object.keys(geometry.attributes).sort().join(",");
      if (!batches.has(key))
        batches.set(key, {
          material: node.material,
          geometries: [],
          leaf: node.name.includes("Banana_leaf") || node.name.includes("Leaf_midrib"),
        });
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
          parts.set(child.material.uuid, {
            material: child.material,
            geometries: [],
            name: child.name,
          });
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

  tileAt(event) {
    const rect = this.canvas.getBoundingClientRect();
    this.pointer.set(
      ((event.clientX - rect.left) / rect.width) * 2 - 1,
      (-(event.clientY - rect.top) / rect.height) * 2 + 1,
    );
    this.raycaster.setFromCamera(this.pointer, this.camera);
    return this.raycaster.intersectObjects([...this.handTiles.values()], true)[0]?.object.userData.tileId ?? null;
  }

  paintHand() {
    for (const [id, group] of this.handTiles) {
      const legal = this.playable.has(id);
      const lift = id === this.selection ? 0.17 : id === this.hovered ? 0.08 : 0;
      group.position.y = group.userData.restY + lift;
      group.traverse((node) => {
        if (!node.isMesh || !node.name.startsWith("Domino_body")) return;
        node.material.emissive.set(id === this.selection ? "#587b38" : id === this.hovered ? "#3c5528" : "#000000");
        node.material.emissiveIntensity = 0.24;
        node.material.color.set(legal ? "#fff5dc" : "#cfcabb");
      });
    }
  }

  resize() {
    const { width, height } = this.canvas.getBoundingClientRect();
    if (!width || !height) return;
    this.renderer.setSize(width, height, false);
    this.camera.aspect = width / height;
    this.camera.fov = width < 760 ? 53 : 38;
    this.camera.updateProjectionMatrix();
    this.pipeline.resize(width, height);
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
      if (node.isMesh && (group.userData.preview || node.name.startsWith("Domino_body"))) node.material.dispose();
    });
  }

  positionBoard(layout) {
    for (const placement of layout.tiles) {
      const group = this.boardTiles.get(placement.id);
      group.userData.target = new THREE.Vector3(placement.x, 1.83, placement.z);
      group.userData.angle = placement.angle;
      group.scale.setScalar(layout.scale);
      if (!group.userData.flight) {
        group.position.copy(group.userData.target);
        group.rotation.set(0, placement.angle, 0);
      }
    }
  }

  clearPreview() {
    if (!this.ghost) return;
    this.remove(this.ghost);
    this.ghost = null;
    this.positionBoard(this.layout);
  }

  preview(tileId, position) {
    this.clearPreview();
    if (!tileId || !position || !this.state) return;
    const candidate = previewPlacement(this.state, {
      tileId,
      position,
      spec: this.spec,
    });
    if (!candidate) return;
    // Preview the whole candidate layout; long chains may recenter or scale on placement.
    this.positionBoard({
      ...candidate.layout,
      tiles: candidate.layout.tiles.filter((tile) => tile.id !== tileId),
    });
    const tile = candidate.board.find((tile) => tile.id === tileId);
    const placement = candidate.layout.tiles.find((tile) => tile.id === tileId);
    this.ghost = this.tile(tile);
    this.ghost.userData.preview = true;
    this.ghost.traverse((node) => {
      if (!node.isMesh) return;
      if (!node.name.startsWith("Domino_body")) node.material = node.material.clone();
      node.material.transparent = true;
      node.material.opacity = 0.62;
      node.material.depthWrite = false;
      node.castShadow = false;
    });
    this.ghost.position.set(placement.x, 1.83, placement.z);
    this.ghost.rotation.y = placement.angle;
    this.ghost.scale.setScalar(candidate.layout.scale);
  }

  update(state, { selected, busy, active }) {
    if (!this.templates.size) return;
    this.clearPreview();
    this.selection = selected;
    this.playable = new Set(active ? state.moves.map((move) => move.tile) : []);
    if (!this.playable.has(this.hovered)) this.hovered = null;
    const boardIds = new Set(state.board.map((tile) => tile.id));
    for (const [id, group] of this.boardTiles) {
      if (!boardIds.has(id)) {
        this.remove(group);
        this.boardTiles.delete(id);
      }
    }
    this.layout = layoutBoard(state.board, {
      spec: this.spec,
      opening: state.opening,
    });
    state.board.forEach((tile) => {
      let group = this.boardTiles.get(tile.id);
      if (!group) {
        group = this.tile(tile);
        const event = state.history.at(-1);
        const fresh = this.state?.round === state.round && this.state.board.length + 1 === state.board.length;
        if (fresh && event?.tile?.id === tile.id) {
          const handTile = this.handTiles.get(tile.id);
          const from =
            handTile?.position.clone() ??
            new THREE.Vector3(
              event.player === 1 ? 2.78 : event.player === 3 ? -2.78 : 0,
              1.95,
              event.player === 2 ? -2.55 : 0,
            );
          group.userData.flight = {
            from,
            angle: handTile?.rotation.y ?? (event.player === 2 ? Math.PI / 2 : 0),
            flip: handTile?.rotation.x ?? (event.player ? Math.PI : 0),
            start: performance.now(),
          };
          if (reducedMotion) {
            group.userData.flight = null;
            this.onLand();
          }
        }
        this.boardTiles.set(tile.id, group);
      }
    });
    this.positionBoard(this.layout);
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
      // Revealed hands lie flat after the round so every seat reads the same way.
      const tilt = state.phase === "playing" ? HAND_TILT : 0;
      group.userData.restY = 1.83 + (this.spec.length / 2) * Math.sin(tilt) + 0.01;
      group.position.set((index - (hand.length - 1) / 2) * HAND_SPACING, group.userData.restY, 2.55);
      group.rotation.set(tilt, -Math.PI / 2, 0);
    });
    this.handOrder = hand.map((tile) => tile.id);
    this.paintHand();
    for (const group of this.hiddenTiles) this.remove(group);
    this.hiddenTiles = [];
    for (let player = 1; player < 4; player++) {
      for (let i = 0; i < state.players[player].count; i++) {
        const reveal = state.players[player].hand;
        const group = this.tile(reveal ? reveal[i] : { id: "0-0" }, {
          hidden: !reveal,
        });
        const offset = (i - (state.players[player].count - 1) / 2) * 0.37;
        if (player === 2) {
          group.position.set(-offset, reveal ? 1.83 : 1.83 + this.spec.height, -2.55);
          group.rotation.y = Math.PI / 2;
        } else {
          group.position.set(player === 1 ? 2.78 : -2.78, reveal ? 1.83 : 1.83 + this.spec.height, offset);
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
    this.endButtons.forEach((button) => {
      const end = button.dataset.end;
      const fits = active && state.moves.some((move) => move.tile === selected && move.position === end);
      if (end === "first") {
        button.hidden = !fits;
        button.disabled = busy;
        button.textContent = `Lead ${selected ?? ""}`;
        button.setAttribute("aria-label", `Lead the round with ${selected}`);
        return;
      }
      button.hidden = !this.layout.ends || !active;
      button.disabled = busy || !fits;
      button.textContent = `${end === "left" ? "L" : "R"} \u00b7 ${state.ends[end] ?? "-"}`;
      button.setAttribute("aria-label", `Play ${selected ?? "a tile"} on the ${end} end, matching ${state.ends[end]}`);
    });
    this.keyTags.forEach((tag, index) => {
      tag.hidden = state.phase !== "playing" || state.autoplay || index >= hand.length;
      tag.classList.toggle("playable", this.playable.has(hand[index]?.id));
      tag.classList.toggle("selected", hand[index]?.id === selected);
    });
    this.state = state;
  }

  setView(overhead) {
    this.controls.target.set(0, 1.8, 0);
    this.cameraDestination = overhead
      ? new THREE.Vector3(0, this.camera.aspect < 1 ? 9.4 : 10.4, 0.001)
      : new THREE.Vector3(0, 9.2, 10.2);
    this.controls.enabled = false;
    if (reducedMotion) {
      this.camera.position.copy(this.cameraDestination);
      this.cameraDestination = null;
      this.controls.enabled = true;
    }
  }

  frame(time) {
    if (this.cameraDestination) {
      this.camera.position.lerp(this.cameraDestination, 0.09);
      if (this.camera.position.distanceTo(this.cameraDestination) < 0.02) {
        this.camera.position.copy(this.cameraDestination);
        this.cameraDestination = null;
        this.controls.enabled = true;
      }
    }
    for (const group of this.boardTiles.values()) {
      const flight = group.userData.flight;
      if (!flight) continue;
      const progress = Math.min(1, (time - flight.start) / 380);
      const eased = 1 - (1 - progress) ** 3;
      group.position.copy(flight.from).lerp(group.userData.target, eased);
      group.position.y += Math.sin(progress * Math.PI) * 0.6;
      const delta = Math.atan2(
        Math.sin(group.userData.angle - flight.angle),
        Math.cos(group.userData.angle - flight.angle),
      );
      group.rotation.set(flight.flip * (1 - eased), flight.angle + delta * eased, 0);
      if (progress === 1) {
        group.userData.flight = null;
        this.onLand();
      }
    }
    if (!reducedMotion)
      this.foliage.forEach((mesh) => {
        mesh.rotation.y = Math.sin(time * 0.0006) * 0.002;
      });
    if (this.cameraDestination) this.camera.lookAt(this.controls.target);
    else this.controls.update();
    this.camera.updateMatrixWorld();
    const rect = this.canvas.getBoundingClientRect();
    this.endButtons.forEach((button) => {
      if (button.hidden) return;
      if (button.dataset.end === "first") {
        const center = new THREE.Vector3(0, 1.95, 0).project(this.camera);
        button.style.left = `${((center.x + 1) / 2) * rect.width}px`;
        button.style.top = `${((1 - center.y) / 2) * rect.height}px`;
        return;
      }
      if (!this.layout?.ends) return;
      const { point, direction } = this.layout.ends[button.dataset.end];
      const projected = new THREE.Vector3(point[0], 1.95, point[1]).project(this.camera);
      const extended = new THREE.Vector3(point[0] + direction[0], 1.95, point[1] + direction[1]).project(this.camera);
      const dx = (extended.x - projected.x) * rect.width;
      const dy = (projected.y - extended.y) * rect.height;
      const magnitude = Math.hypot(dx, dy) || 1;
      const unit = [dx / magnitude, dy / magnitude];
      // Screen-space clearance keeps touch targets away from the pips at every zoom.
      const clearance =
        (Math.abs(unit[0]) * button.offsetWidth) / 2 + (Math.abs(unit[1]) * button.offsetHeight) / 2 + 12;
      const x = ((projected.x + 1) / 2) * rect.width + unit[0] * clearance;
      const y = ((1 - projected.y) / 2) * rect.height + unit[1] * clearance;
      button.style.left = `${Math.max(button.offsetWidth / 2 + 8, Math.min(rect.width - button.offsetWidth / 2 - 8, x))}px`;
      button.style.top = `${y}px`;
      button.style.visibility =
        projected.z > 1 || Math.abs(projected.x) > 0.96 || Math.abs(projected.y) > 0.92 ? "hidden" : "visible";
    });
    this.keyTags.forEach((tag, index) => {
      const group = this.handTiles.get(this.handOrder?.[index]);
      if (tag.hidden || !group) return;
      const projected = new THREE.Vector3(group.position.x, 1.84, 2.55 + this.spec.length * 0.62).project(this.camera);
      tag.style.left = `${((projected.x + 1) / 2) * rect.width}px`;
      tag.style.top = `${((1 - projected.y) / 2) * rect.height}px`;
      tag.style.visibility = projected.z > 1 || Math.abs(projected.y) > 0.98 ? "hidden" : "visible";
    });
    seatLocations.forEach((location, index) => {
      const projected = new THREE.Vector3(...location).project(this.camera);
      const tag = this.tags[index];
      const x = ((projected.x + 1) / 2) * rect.width;
      tag.style.left = `${Math.max(tag.offsetWidth / 2 + 8, Math.min(rect.width - tag.offsetWidth / 2 - 8, x))}px`;
      tag.style.top = `${((-projected.y + 1) / 2) * rect.height - (index % 2 ? 24 : 0)}px`;
      tag.hidden = projected.z > 1 || Math.abs(projected.x) > 0.95 || Math.abs(projected.y) > 0.82;
    });
    this.pipeline.render();
  }
}
