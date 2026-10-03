let faceSequence = 0;
const NS = "http://www.w3.org/2000/svg";

function element(name, attributes) {
  const node = document.createElementNS(NS, name);
  for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, value);
  return node;
}

export function tileFace(tile, spec) {
  const scale = 100 / spec.width;
  const length = spec.length * scale;
  const svg = element("svg", { viewBox: `0 0 100 ${length}`, class: "domino-face", "aria-hidden": "true" });
  const prefix = `face-${faceSequence++}`;
  const defs = element("defs", {});
  for (const [name, colors] of [
    ["resin", ["#fffbed", "#eee4c9", "#f7efd9"]],
    ["pip", ["#070e0b", "#17271e", "#374339"]],
    ["brass", ["#f2dca0", "#b08b3d", "#755723"]],
  ]) {
    const gradient = element("linearGradient", { id: `${prefix}-${name}`, x2: "85%", y2: "100%" });
    colors.forEach((color, index) => gradient.append(element("stop", { offset: `${index * 50}%`, "stop-color": color })));
    defs.append(gradient);
  }
  svg.append(defs);
  svg.append(
    element("rect", {
      x: 1, y: 1, width: 98, height: length - 2, rx: spec.bevel * scale,
      class: "tile-resin", style: `fill: url(#${prefix}-resin)`,
    }),
    element("rect", {
      x: 3, y: 3, width: 94, height: length - 6, rx: spec.bevel * scale - 1,
      fill: "none", stroke: "#fffdf1", "stroke-width": 1.3,
    }),
  );
  [tile.left, tile.right].forEach((value, half) => {
    const centerY = length * (half ? 0.75 : 0.25);
    for (const cell of spec.pips[value]) {
      svg.append(
        element("circle", {
          cx: 50 + ((cell % 3) - 1) * spec.pipSpacing * scale,
          cy: centerY + (Math.floor(cell / 3) - 1) * spec.pipSpacing * scale,
          r: spec.pipRadius * scale,
          class: "tile-pip",
          style: `fill: url(#${prefix}-pip)`,
        }),
      );
    }
  });
  svg.append(
    element("rect", {
      x: 10,
      y: length / 2 - (spec.dividerWidth * scale) / 2,
      width: 80,
      height: spec.dividerWidth * scale,
      rx: 1,
      class: "tile-divider",
    }),
  );
  svg.append(element("circle", {
    cx: 50, cy: length / 2, r: spec.pinRadius * scale,
    class: "tile-pin", style: `fill: url(#${prefix}-brass)`,
  }));
  return svg;
}
