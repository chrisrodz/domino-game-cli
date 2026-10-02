import { tileFace } from "./tile-face.js";

export function enableHandDrag({ rack, spec, select, preview, place }) {
  let gesture = null;
  let suppressClick = false;

  function targetAt(x, y) {
    const targets = [...document.querySelectorAll("#board-ends button, #placement button")].filter(
      (button) => !button.hidden && !button.disabled && getComputedStyle(button).visibility !== "hidden",
    );
    return (
      targets
        .map((button) => {
          const rect = button.getBoundingClientRect();
          const inside = x >= rect.left - 16 && x <= rect.right + 16 && y >= rect.top - 16 && y <= rect.bottom + 16;
          return {
            button,
            inside,
            distance: Math.hypot(x - rect.x - rect.width / 2, y - rect.y - rect.height / 2),
          };
        })
        .filter((target) => target.inside)
        .sort((a, b) => a.distance - b.distance)[0]?.button ?? null
    );
  }

  function clean() {
    const pointer = gesture?.pointer;
    gesture?.ghost?.remove();
    gesture?.target?.classList.remove("drop-target");
    rack.classList.remove("dragging");
    preview(null);
    gesture = null;
    if (pointer !== undefined && rack.hasPointerCapture(pointer)) rack.releasePointerCapture(pointer);
  }

  rack.addEventListener("pointerdown", (event) => {
    const button = event.target.closest("button[data-tile]");
    // Touch retains horizontal rack scrolling and the existing tap controls.
    if (event.pointerType !== "mouse" || event.button !== 0 || !button || button.disabled) return;
    gesture = {
      id: button.dataset.tile,
      pointer: event.pointerId,
      x: event.clientX,
      y: event.clientY,
      active: false,
    };
  });

  window.addEventListener("pointermove", (event) => {
    if (!gesture || gesture.pointer !== event.pointerId) return;
    if (!gesture.active && Math.hypot(event.clientX - gesture.x, event.clientY - gesture.y) < 7) return;
    if (!gesture.active) {
      gesture.active = true;
      rack.setPointerCapture(event.pointerId);
      select(gesture.id);
      const [left, right] = gesture.id.split("-").map(Number);
      gesture.ghost = document.createElement("div");
      gesture.ghost.className = "drag-ficha";
      gesture.ghost.setAttribute("aria-hidden", "true");
      gesture.ghost.append(tileFace({ left, right }, spec));
      document.body.append(gesture.ghost);
      rack.classList.add("dragging");
    }
    gesture.ghost.style.transform = `translate(${event.clientX - 25}px, ${event.clientY - 50}px) rotate(-7deg)`;
    const target = targetAt(event.clientX, event.clientY);
    if (target !== gesture.target) {
      gesture.target?.classList.remove("drop-target");
      gesture.target = target;
      target?.classList.add("drop-target");
      preview(target ? (target.dataset.end ?? (target.id === "play-right" ? "right" : "left")) : null);
    }
  });

  window.addEventListener("pointerup", (event) => {
    if (!gesture || gesture.pointer !== event.pointerId) return;
    if (gesture.active) {
      const target = targetAt(event.clientX, event.clientY);
      suppressClick = true;
      clean();
      if (target) place(target.dataset.end ?? (target.id === "play-right" ? "right" : "left"));
      setTimeout(() => {
        suppressClick = false;
      }, 0);
    } else clean();
    if (rack.hasPointerCapture(event.pointerId)) rack.releasePointerCapture(event.pointerId);
  });
  rack.addEventListener("pointercancel", clean);
  rack.addEventListener("lostpointercapture", clean);
  rack.addEventListener(
    "click",
    (event) => {
      if (suppressClick) {
        event.preventDefault();
        event.stopPropagation();
      }
    },
    true,
  );
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") clean();
  });
  window.addEventListener("blur", clean);
}
