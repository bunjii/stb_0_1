import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

const COLORS = {
  background: 0xe1dee4,
  element: 0x666666,
  node: 0x666666,
  support: 0x5eff4d,
  load: 0xff0000,
  deform: 0x8648d2,
};

const el = {
  viewport: document.getElementById("viewport"),
  modelSelect: document.getElementById("modelSelect"),
  btnReload: document.getElementById("btnReload"),
  chkSolve: document.getElementById("chkSolve"),
  lcSelect: document.getElementById("lcSelect"),
  defFactor: document.getElementById("defFactor"),
  chkDeformed: document.getElementById("chkDeformed"),
  chkLoads: document.getElementById("chkLoads"),
  chkLabels: document.getElementById("chkLabels"),
  status: document.getElementById("status"),
};

let scene, camera, renderer, controls;
let modelGroup, labelGroup;
let currentModel = null;

function setStatus(msg) {
  el.status.textContent = msg;
}

function initThree() {
  scene = new THREE.Scene();
  scene.background = new THREE.Color(COLORS.background);

  const w = el.viewport.clientWidth;
  const h = el.viewport.clientHeight;
  camera = new THREE.PerspectiveCamera(45, w / h, 0.01, 1e6);
  camera.position.set(10, 8, 12);

  renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setSize(w, h);
  renderer.setPixelRatio(window.devicePixelRatio);
  el.viewport.appendChild(renderer.domElement);

  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;

  const amb = new THREE.AmbientLight(0xffffff, 0.65);
  scene.add(amb);
  const dir = new THREE.DirectionalLight(0xffffff, 0.55);
  dir.position.set(5, 10, 7);
  scene.add(dir);

  modelGroup = new THREE.Group();
  scene.add(modelGroup);
  labelGroup = new THREE.Group();
  scene.add(labelGroup);

  window.addEventListener("resize", onResize);
  animate();
}

function onResize() {
  const w = el.viewport.clientWidth;
  const h = el.viewport.clientHeight;
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
  renderer.setSize(w, h);
}

function animate() {
  requestAnimationFrame(animate);
  controls.update();
  renderer.render(scene, camera);
}

function nodeMap(model) {
  const m = {};
  for (const n of model.nodes) {
    m[n.id] = n;
  }
  return m;
}

function nodePosition(n, model, lc, defFac, deformed) {
  let x = n.x, y = n.y, z = n.z;
  if (deformed && model.solved && n.disps && n.disps[String(lc)]) {
    const d = n.disps[String(lc)];
    x += d[0] * defFac;
    y += d[1] * defFac;
    z += d[2] * defFac;
  }
  return new THREE.Vector3(x, y, z);
}

function clearGroup(g) {
  while (g.children.length > 0) {
    const c = g.children[0];
    g.remove(c);
    if (c.geometry) c.geometry.dispose();
    if (c.material) {
      if (Array.isArray(c.material)) c.material.forEach((m) => m.dispose());
      else c.material.dispose();
    }
  }
}

function fitCamera(model) {
  const b = model.bounds;
  if (!b) return;
  const cx = 0.5 * (b[0] + b[1]);
  const cy = 0.5 * (b[2] + b[3]);
  const cz = 0.5 * (b[4] + b[5]);
  const sx = b[1] - b[0];
  const sy = b[3] - b[2];
  const sz = b[5] - b[4];
  const span = Math.max(sx, sy, sz, 1.0);
  controls.target.set(cx, cy, cz);
  camera.position.set(cx + span * 1.2, cy + span * 0.8, cz + span * 1.2);
  camera.near = span * 0.001;
  camera.far = span * 100;
  camera.updateProjectionMatrix();
}

function buildModelScene(model) {
  clearGroup(modelGroup);
  clearGroup(labelGroup);

  const lc = el.lcSelect.value;
  const defFac = parseFloat(el.defFactor.value) || 0;
  const deformed = el.chkDeformed.checked && model.solved;
  const showLoads = el.chkLoads.checked;
  const showLabels = el.chkLabels.checked;
  const nm = nodeMap(model);

  const linePts = [];
  for (const e of model.elements) {
    const n0 = nm[e.n0];
    const n1 = nm[e.n1];
    if (!n0 || !n1) continue;
    const p0 = nodePosition(n0, model, lc, defFac, deformed);
    const p1 = nodePosition(n1, model, lc, defFac, deformed);
    linePts.push(p0.x, p0.y, p0.z, p1.x, p1.y, p1.z);
  }

  if (linePts.length > 0) {
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.Float32BufferAttribute(linePts, 3));
    const mat = new THREE.LineBasicMaterial({
      color: deformed ? COLORS.deform : COLORS.element,
      linewidth: 1,
    });
    modelGroup.add(new THREE.LineSegments(geo, mat));
  }

  const nodePts = [];
  for (const n of model.nodes) {
    const p = nodePosition(n, model, lc, defFac, deformed);
    nodePts.push(p.x, p.y, p.z);
  }
  if (nodePts.length > 0) {
    const ngeo = new THREE.BufferGeometry();
    ngeo.setAttribute("position", new THREE.Float32BufferAttribute(nodePts, 3));
    const nmat = new THREE.PointsMaterial({
      color: COLORS.node,
      size: Math.max(0.04, (model.bounds ? (model.bounds[1] - model.bounds[0]) * 0.012 : 0.05)),
      sizeAttenuation: true,
    });
    modelGroup.add(new THREE.Points(ngeo, nmat));
  }

  const supSize = model.bounds
    ? Math.max(0.08, (model.bounds[1] - model.bounds[0]) * 0.025)
    : 0.15;
  for (const s of model.supports) {
    const n = nm[s.node];
    if (!n) continue;
    const p = nodePosition(n, model, lc, defFac, deformed);
    const cone = new THREE.Mesh(
      new THREE.ConeGeometry(supSize * 0.35, supSize, 4),
      new THREE.MeshBasicMaterial({ color: COLORS.support })
    );
    cone.position.copy(p);
    cone.position.y -= supSize * 0.5;
    modelGroup.add(cone);
  }

  if (showLoads && model.point_loads) {
    const loadScale = model.bounds
      ? Math.max(0.5, (model.bounds[1] - model.bounds[0]) * 0.08)
      : 1.0;
    const loadPts = [];
    for (const l of model.point_loads) {
      if (String(l.lc) !== String(lc)) continue;
      const n = nm[l.node];
      if (!n) continue;
      const p = nodePosition(n, model, lc, defFac, deformed);
      const fx = l.px, fy = l.py, fz = l.pz;
      const mag = Math.sqrt(fx * fx + fy * fy + fz * fz);
      if (mag < 1e-9) continue;
      const dx = (fx / mag) * loadScale;
      const dy = (fy / mag) * loadScale;
      const dz = (fz / mag) * loadScale;
      loadPts.push(p.x, p.y, p.z, p.x + dx, p.y + dy, p.z + dz);
    }
    if (loadPts.length > 0) {
      const lgeo = new THREE.BufferGeometry();
      lgeo.setAttribute("position", new THREE.Float32BufferAttribute(loadPts, 3));
      const lmat = new THREE.LineBasicMaterial({ color: COLORS.load });
      modelGroup.add(new THREE.LineSegments(lgeo, lmat));
    }
  }

  if (showLabels) {
    const span = model.bounds ? (model.bounds[1] - model.bounds[0]) : 1;
    for (const n of model.nodes) {
      const p = nodePosition(n, model, lc, defFac, deformed);
      const sprite = makeTextSprite(String(n.id), span);
      sprite.position.set(p.x, p.y + span * 0.02, p.z);
      labelGroup.add(sprite);
    }
  }
}

function makeTextSprite(text, span) {
  const canvas = document.createElement("canvas");
  const ctx = canvas.getContext("2d");
  const fs = 28;
  ctx.font = fs + "px monospace";
  const w = ctx.measureText(text).width + 8;
  canvas.width = w;
  canvas.height = fs + 8;
  ctx.font = fs + "px monospace";
  ctx.fillStyle = "rgba(0,0,0,0.55)";
  ctx.fillRect(0, 0, w, fs + 8);
  ctx.fillStyle = "#ffffff";
  ctx.fillText(text, 4, fs);
  const tex = new THREE.CanvasTexture(canvas);
  const mat = new THREE.SpriteMaterial({ map: tex, depthTest: false });
  const sp = new THREE.Sprite(mat);
  const sc = span * 0.06;
  sp.scale.set(sc * (w / (fs + 8)), sc, 1);
  return sp;
}

function fillLcSelect(model) {
  el.lcSelect.innerHTML = "";
  const lcs = model.load_cases || [];
  if (lcs.length === 0) {
    const opt = document.createElement("option");
    opt.value = "0";
    opt.textContent = "—";
    el.lcSelect.appendChild(opt);
    return;
  }
  for (const lc of lcs) {
    const opt = document.createElement("option");
    opt.value = String(lc);
    opt.textContent = "LC " + lc;
    el.lcSelect.appendChild(opt);
  }
}

async function fetchModelList() {
  const res = await fetch("/api/models");
  if (!res.ok) throw new Error("Failed to list models");
  return res.json();
}

async function fetchModel(path, solve) {
  const url = "/api/model?path=" + encodeURIComponent(path) + "&solve=" + (solve ? "1" : "0");
  const res = await fetch(url);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

async function loadSelectedModel() {
  const path = el.modelSelect.value;
  if (!path) return;
  setStatus("Loading " + path + "…");
  try {
    const solve = el.chkSolve.checked;
    currentModel = await fetchModel(path, solve);
    fillLcSelect(currentModel);
    el.chkDeformed.disabled = !currentModel.solved;
    if (!currentModel.solved) el.chkDeformed.checked = false;
    buildModelScene(currentModel);
    fitCamera(currentModel);
    const extra = currentModel.solved ? " (solved)" : "";
    setStatus(path + extra + " — " + currentModel.nodes.length + " nodes, " + currentModel.elements.length + " elements");
  } catch (ex) {
    setStatus("Error: " + ex.message);
  }
}

async function bootstrap() {
  initThree();
  try {
    const data = await fetchModelList();
    el.modelSelect.innerHTML = "";
    for (const p of data.models) {
      const opt = document.createElement("option");
      opt.value = p;
      opt.textContent = p;
      el.modelSelect.appendChild(opt);
    }
    if (data.default && data.models.indexOf(data.default) >= 0) {
      el.modelSelect.value = data.default;
    } else if (data.models.length > 0) {
      el.modelSelect.value = data.models[0];
    }
    await loadSelectedModel();
  } catch (ex) {
    setStatus("Error: " + ex.message);
  }
}

el.btnReload.addEventListener("click", () => loadSelectedModel());
el.modelSelect.addEventListener("change", () => loadSelectedModel());
el.chkSolve.addEventListener("change", () => loadSelectedModel());
el.lcSelect.addEventListener("change", () => {
  if (currentModel) buildModelScene(currentModel);
});
el.defFactor.addEventListener("change", () => {
  if (currentModel) buildModelScene(currentModel);
});
el.chkDeformed.addEventListener("change", () => {
  if (currentModel) buildModelScene(currentModel);
});
el.chkLoads.addEventListener("change", () => {
  if (currentModel) buildModelScene(currentModel);
});
el.chkLabels.addEventListener("change", () => {
  if (currentModel) buildModelScene(currentModel);
});

bootstrap();
