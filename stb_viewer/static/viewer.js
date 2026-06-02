import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { LineSegments2 } from "three/addons/lines/LineSegments2.js";
import { LineSegmentsGeometry } from "three/addons/lines/LineSegmentsGeometry.js";
import { LineMaterial } from "three/addons/lines/LineMaterial.js";

const COLORS = {
  background: 0xe1dee4,
  element: 0x666666,
  node: 0x8648d2,
  supportTrans: 0x2563eb,
  supportRot: 0xd97706,
  supportAnchor: 0x374151,
  load: 0xff0000,
  reaction: 0x0d9488,
  reactionMoment: 0x9333ea,
  deform: 0x8648d2,
  nodeLabel: 0x4a148c,
  force: 0x0047ab,
};

const PRES_ZERO = 1e-10;
const FORCE_LABELS = ["", "Nx", "Vy", "Vz", "Mx", "My", "Mz"];
const FORCE_UNITS = ["", "kN", "kN", "kN", "kNm", "kNm", "kNm"];

const OPTIONS_STORAGE_KEY = "stb_viewer_options";
const MODEL_STORAGE_KEY = "stb_viewer_last_model";
const LABEL_BG = {
  elem: "rgba(55, 55, 65, 0.88)",
  material: "rgba(150, 95, 35, 0.92)",
  section: "rgba(45, 95, 175, 0.92)",
  load: "rgba(180, 40, 40, 0.88)",
  reactionForce: "rgba(13, 120, 110, 0.92)",
  reactionMoment: "rgba(147, 51, 234, 0.92)",
};

const OPTIONS_DEFAULTS = {
  loadArrowSize: 8,
  supportGizmoSize: 25,
  supportLineWidth: 2,
  dispContourLineWidth: 2.5,
  nodeLabelSize: 3,
  elemLabelSize: 3,
  materialLabelSize: 4,
  sectionLabelSize: 3,
  loadLabelSize: 3,
  reactionLabelSize: 3,
  forceLabelSize: 6,
};

const OPTIONS_LIMITS = {
  loadArrowSize: { min: 5, max: 20 },
  supportGizmoSize: { min: 25, max: 50 },
  supportLineWidth: { min: 0.5, max: 3 },
  dispContourLineWidth: { min: 0.5, max: 3 },
  nodeLabelSize: { min: 1, max: 8 },
  elemLabelSize: { min: 1, max: 8 },
  materialLabelSize: { min: 1, max: 8 },
  sectionLabelSize: { min: 1, max: 8 },
  loadLabelSize: { min: 1, max: 8 },
  reactionLabelSize: { min: 1, max: 8 },
  forceLabelSize: { min: 1, max: 10 },
};

function clampViewerOption(key, value) {
  const lim = OPTIONS_LIMITS[key];
  if (!lim || typeof value !== "number" || !isFinite(value)) return value;
  return Math.min(lim.max, Math.max(lim.min, value));
}

function clampAllViewerOptions() {
  for (const key of Object.keys(OPTIONS_LIMITS)) {
    if (typeof viewerOptions[key] === "number") {
      viewerOptions[key] = clampViewerOption(key, viewerOptions[key]);
    }
  }
}

const el = {
  viewport: document.getElementById("viewport"),
  modelSelect: document.getElementById("modelSelect"),
  btnReload: document.getElementById("btnReload"),
  btnSolve: document.getElementById("btnSolve"),
  btnInput: document.getElementById("btnInput"),
  btnOutput: document.getElementById("btnOutput"),
  lcSelect: document.getElementById("lcSelect"),
  defFactor: document.getElementById("defFactor"),
  chkDeformed: document.getElementById("chkDeformed"),
  chkDispContour: document.getElementById("chkDispContour"),
  dispLegendOverlay: document.getElementById("dispLegendOverlay"),
  dispLegendTitle: document.getElementById("dispLegendTitle"),
  dispLegendLc: document.getElementById("dispLegendLc"),
  dispLegendBar: document.getElementById("dispLegendBar"),
  dispContourMin: document.getElementById("dispContourMin"),
  dispContourMax: document.getElementById("dispContourMax"),
  btnDispContourAuto: document.getElementById("btnDispContourAuto"),
  chkSupports: document.getElementById("chkSupports"),
  chkLoads: document.getElementById("chkLoads"),
  chkLoadValues: document.getElementById("chkLoadValues"),
  chkReactions: document.getElementById("chkReactions"),
  chkReactionValues: document.getElementById("chkReactionValues"),
  chkLabels: document.getElementById("chkLabels"),
  chkElemLabels: document.getElementById("chkElemLabels"),
  chkMaterial: document.getElementById("chkMaterial"),
  chkSection: document.getElementById("chkSection"),
  chkForceValues: document.getElementById("chkForceValues"),
  forceSelect: document.getElementById("forceSelect"),
  frcDiv: document.getElementById("frcDiv"),
  frcDivVal: document.getElementById("frcDivVal"),
  frcFactor: document.getElementById("frcFactor"),
  frcFactorVal: document.getElementById("frcFactorVal"),
  forceLegend: document.getElementById("forceLegend"),
  resultsPanel: document.getElementById("resultsPanel"),
  resultsPanelHeader: document.getElementById("resultsPanelHeader"),
  btnPanelCollapse: document.getElementById("btnPanelCollapse"),
  btnTogglePanel: document.getElementById("btnTogglePanel"),
  optionsPanel: document.getElementById("optionsPanel"),
  optionsPanelHeader: document.getElementById("optionsPanelHeader"),
  btnOptionsCollapse: document.getElementById("btnOptionsCollapse"),
  btnToggleOptions: document.getElementById("btnToggleOptions"),
  btnToggleAxes: document.getElementById("btnToggleAxes"),
  optLoadArrow: document.getElementById("optLoadArrow"),
  optLoadArrowVal: document.getElementById("optLoadArrowVal"),
  optSupportGizmo: document.getElementById("optSupportGizmo"),
  optSupportGizmoVal: document.getElementById("optSupportGizmoVal"),
  optSupportLineWidth: document.getElementById("optSupportLineWidth"),
  optDispContourLineWidth: document.getElementById("optDispContourLineWidth"),
  optNodeLabel: document.getElementById("optNodeLabel"),
  optNodeLabelVal: document.getElementById("optNodeLabelVal"),
  optElemLabel: document.getElementById("optElemLabel"),
  optElemLabelVal: document.getElementById("optElemLabelVal"),
  optMaterialLabel: document.getElementById("optMaterialLabel"),
  optMaterialLabelVal: document.getElementById("optMaterialLabelVal"),
  optSectionLabel: document.getElementById("optSectionLabel"),
  optSectionLabelVal: document.getElementById("optSectionLabelVal"),
  optLoadLabel: document.getElementById("optLoadLabel"),
  optLoadLabelVal: document.getElementById("optLoadLabelVal"),
  optReactionLabel: document.getElementById("optReactionLabel"),
  optReactionLabelVal: document.getElementById("optReactionLabelVal"),
  optForceLabel: document.getElementById("optForceLabel"),
  optForceLabelVal: document.getElementById("optForceLabelVal"),
  status: document.getElementById("status"),
};

let scene, camera, renderer, controls;
let modelGroup, labelGroup, forceGroup, forceLabelGroup, axesGroup;
let currentModel = null;
let currentResultsText = null;
let viewerOptions = Object.assign({}, OPTIONS_DEFAULTS);
let wideLineMaterials = new Set();
let dispContourScaleKey = null;
let showWorldAxes = true;
const _supportDiscTexCache = new Map();

function saveLastModelPath(path) {
  const p = normalizeModelPath(path);
  if (!p) return;
  try {
    localStorage.setItem(MODEL_STORAGE_KEY, p);
  } catch (e) { /* ignore */ }
}

function normalizeModelPath(path) {
  if (!path) return null;
  let p = String(path).trim().replace(/\\/g, "/");
  while (p.startsWith("./")) p = p.slice(2);
  return p;
}

function modelInList(models, path) {
  const p = normalizeModelPath(path);
  if (!p) return null;
  return models.indexOf(p) >= 0 ? p : null;
}

function launchFileFromUrl() {
  try {
    const file = new URLSearchParams(window.location.search).get("file");
    if (!file) return null;
    return normalizeModelPath(decodeURIComponent(file));
  } catch (e) {
    return null;
  }
}

function clearLaunchFileFromUrl() {
  try {
    const url = new URL(window.location.href);
    if (!url.searchParams.has("file")) return;
    url.searchParams.delete("file");
    const next = url.pathname + url.search + url.hash;
    window.history.replaceState(null, "", next);
  } catch (e) { /* ignore */ }
}

function resolveInitialModel(models, serverDefault) {
  const launchFile = modelInList(models, launchFileFromUrl());
  if (launchFile) return launchFile;

  const server = modelInList(models, serverDefault);
  if (server) return server;

  let saved = null;
  try {
    saved = localStorage.getItem(MODEL_STORAGE_KEY);
  } catch (e) { /* ignore */ }
  const remembered = modelInList(models, saved);
  if (remembered) return remembered;

  if (models.length > 0) return models[0];
  return null;
}

function setStatus(msg) {
  el.status.textContent = msg;
}

function analysisComplete(model) {
  if (!model) return false;
  if (model.solved) return true;
  for (const n of model.nodes || []) {
    if (n.disps && Object.keys(n.disps).length > 0) return true;
  }
  if (model.results_text && model.results_text.indexOf("REAC,") >= 0) return true;
  if (model.reactions && model.reactions.length > 0) return true;
  for (const s of model.supports || []) {
    if (s.reacts && Object.keys(s.reacts).length > 0) return true;
  }
  return false;
}

function parseReactionsFromResultsText(text) {
  const out = [];
  if (!text) return out;
  for (const line of text.split("\n")) {
    const t = line.trim();
    if (!t.startsWith("REAC,")) continue;
    const parts = t.split(",").map(function (s) { return s.trim(); });
    if (parts.length < 8) continue;
    const node = parseInt(parts[2], 10);
    if (!isFinite(node)) continue;
    const vals = [];
    let ok = true;
    for (let i = 3; i < 9; i++) {
      const v = parseFloat(parts[i]);
      if (!isFinite(v)) ok = false;
      vals.push(v);
    }
    if (!ok) continue;
    out.push({ node: node, lc: String(parts[1]), values: vals });
  }
  return out;
}

function enrichModelReactions(model) {
  if (!model) return model;
  if (!model.supports) model.supports = [];

  for (const r of model.reactions || []) {
    let s = model.supports.find(function (x) { return x.node === r.node; });
    if (!s) {
      s = { node: r.node, fixed: [false, false, false, false, false, false] };
      model.supports.push(s);
    }
    if (!s.reacts) s.reacts = {};
    const lcKey = String(r.lc);
    if (!s.reacts[lcKey]) {
      s.reacts[lcKey] = [r.rx, r.ry, r.rz, r.mx, r.my, r.mz];
    }
  }

  for (const r of parseReactionsFromResultsText(model.results_text || "")) {
    let s = model.supports.find(function (x) { return x.node === r.node; });
    if (!s) {
      s = { node: r.node, fixed: [false, false, false, false, false, false] };
      model.supports.push(s);
    }
    if (!s.reacts) s.reacts = {};
    if (!s.reacts[r.lc]) s.reacts[r.lc] = r.values;
  }

  if (analysisComplete(model)) model.solved = true;
  return model;
}

function rebuildScene() {
  if (!currentModel) return;
  try {
    enrichModelReactions(currentModel);
    buildModelScene(currentModel);
  } catch (ex) {
    console.error(ex);
    setStatus("Display error: " + ex.message);
  }
}

function refreshDisplayStatus(model) {
  const path = model.path || el.modelSelect.value || "";
  const lcKey = String(el.lcSelect.value);
  let extra = analysisComplete(model) ? " (solved)" : "";
  if (analysisComplete(model) && !modelHasForceData(model, lcKey)) {
    extra += " — force data unavailable (restart stb view)";
  }
  if ((el.chkReactions.checked || el.chkReactionValues.checked) &&
      !modelHasReactionData(model, lcKey)) {
    extra += " — no reaction data for LC " + lcKey;
  }
  setStatus(path + extra + " — " + model.nodes.length + " nodes, " + model.elements.length + " elements");
}

function applyZUpView() {
  camera.up.set(0, 0, 1);
}

function initThree() {
  scene = new THREE.Scene();
  scene.background = new THREE.Color(COLORS.background);

  const w = el.viewport.clientWidth;
  const h = el.viewport.clientHeight;
  camera = new THREE.PerspectiveCamera(45, w / h, 0.01, 1e6);
  applyZUpView();
  camera.position.set(8, -8, 6);

  renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setSize(w, h);
  renderer.setPixelRatio(window.devicePixelRatio);
  el.viewport.appendChild(renderer.domElement);

  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.target.set(0, 0, 0);

  const amb = new THREE.AmbientLight(0xffffff, 0.65);
  scene.add(amb);
  const dir = new THREE.DirectionalLight(0xffffff, 0.55);
  dir.position.set(5, 10, 7);
  scene.add(dir);

  modelGroup = new THREE.Group();
  scene.add(modelGroup);
  labelGroup = new THREE.Group();
  scene.add(labelGroup);
  forceGroup = new THREE.Group();
  scene.add(forceGroup);
  forceLabelGroup = new THREE.Group();
  scene.add(forceLabelGroup);
  axesGroup = new THREE.Group();
  scene.add(axesGroup);

  window.addEventListener("resize", onResize);
  animate();
}

function onResize() {
  const w = el.viewport.clientWidth;
  const h = el.viewport.clientHeight;
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
  renderer.setSize(w, h);
  updateWideLineResolution(w, h);
}

function updateWideLineResolution(w, h) {
  for (const mat of wideLineMaterials) {
    mat.resolution.set(w, h);
  }
}

function clearWideLineMaterials() {
  wideLineMaterials.clear();
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
  if (deformed && n.disps && n.disps[String(lc)]) {
    const d = n.disps[String(lc)];
    x += d[0] * defFac;
    y += d[1] * defFac;
    z += d[2] * defFac;
  }
  return new THREE.Vector3(x, y, z);
}

function nodeDispMagnitude(n, lc, defFac) {
  if (!n.disps || !n.disps[String(lc)]) return 0;
  const d = n.disps[String(lc)];
  const ux = d[0] * defFac;
  const uy = d[1] * defFac;
  const uz = d[2] * defFac;
  return Math.hypot(ux, uy, uz);
}

function dispMagnitudeRange(model, lc, defFac) {
  let min = Infinity;
  let max = -Infinity;
  for (const n of model.nodes || []) {
    const m = nodeDispMagnitude(n, lc, defFac);
    if (m < min) min = m;
    if (m > max) max = m;
  }
  if (!isFinite(max)) return { min: 0, max: 0 };
  if (max - min < 1e-15) max = min + 1e-15;
  return { min: min, max: max };
}

function maxDispNodeInfo(model, lc, defFac) {
  let best = null;
  for (const n of model.nodes || []) {
    const mag = nodeDispMagnitude(n, lc, defFac);
    if (!best || mag > best.mag) best = { node: n, mag: mag };
  }
  if (!best || !best.node) return null;
  return best;
}

function dispContourColor(t) {
  const c = new THREE.Color();
  const u = Math.min(1, Math.max(0, t));
  c.setHSL((1 - u) * 0.66, 1.0, 0.5);
  return c;
}

function formatDispInputValue(v) {
  const av = Math.abs(v);
  if (av < 1e-9) return "0";
  if (av < 0.01) return v.toFixed(5);
  if (av < 1) return v.toFixed(4);
  return v.toFixed(3);
}

function formatDispAbsValue(v) {
  const av = Math.abs(v);
  if (av < 1e-9) return "0";
  if (av < 0.01) return v.toFixed(5);
  if (av < 1) return v.toFixed(4);
  return v.toFixed(3);
}

function dispContourGradientCss() {
  const stops = [];
  const n = 16;
  for (let i = 0; i < n; i++) {
    const t = n > 1 ? i / (n - 1) : 0;
    const c = dispContourColor(t);
    stops.push(colorHex(c.getHex()) + " " + (t * 100) + "%");
  }
  return "linear-gradient(to top, " + stops.join(", ") + ")";
}

function syncDispContourInputs(autoRange, lc, defFac, force) {
  if (!el.dispContourMin || !el.dispContourMax) return;
  const key = String(lc) + ":" + defFac;
  if (force || dispContourScaleKey !== key) {
    dispContourScaleKey = key;
    el.dispContourMin.value = formatDispInputValue(autoRange.min);
    el.dispContourMax.value = formatDispInputValue(autoRange.max);
  }
}

function getDispContourDisplayRange() {
  let min = parseFloat(el.dispContourMin && el.dispContourMin.value);
  let max = parseFloat(el.dispContourMax && el.dispContourMax.value);
  if (!isFinite(min)) min = 0;
  if (!isFinite(max)) max = min + 1e-15;
  if (max < min) {
    const swap = max;
    max = min;
    min = swap;
  }
  if (max - min < 1e-15) max = min + 1e-15;
  return { min: min, max: max };
}

function dispContourT(mag, range) {
  const span = range.max - range.min;
  if (span < 1e-15) return 0;
  return Math.min(1, Math.max(0, (mag - range.min) / span));
}

function updateDispContourOverlay(visible, autoRange, lc, defFac, syncInputs) {
  if (!el.dispLegendOverlay) return;
  if (!visible || !autoRange || lc == null) {
    el.dispLegendOverlay.classList.remove("visible");
    el.dispLegendOverlay.hidden = true;
    dispContourScaleKey = null;
    return;
  }

  if (syncInputs) syncDispContourInputs(autoRange, lc, defFac, false);

  el.dispLegendOverlay.hidden = false;
  el.dispLegendOverlay.classList.add("visible");
  if (el.dispLegendTitle) {
    el.dispLegendTitle.textContent = "|u| (×" + defFac + ")";
  }
  if (el.dispLegendLc) {
    el.dispLegendLc.textContent = "LC " + lc;
  }
  if (el.dispLegendBar) {
    el.dispLegendBar.style.background = dispContourGradientCss();
  }
}

function applyDispContourAutoRange() {
  if (!currentModel || !analysisComplete(currentModel)) return;
  const lc = el.lcSelect.value;
  const defFac = parseFloat(el.defFactor.value) || 0;
  const autoRange = dispMagnitudeRange(currentModel, lc, defFac);
  dispContourScaleKey = null;
  syncDispContourInputs(autoRange, lc, defFac, true);
  rebuildScene();
}

function addDispContourLineSegments(positions, colors, group) {
  const lineW = dispContourLineWidthPx();
  if (lineW <= 1.01) {
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
    geo.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
    const mat = new THREE.LineBasicMaterial({
      vertexColors: true,
      linewidth: 1,
    });
    const lines = new THREE.LineSegments(geo, mat);
    lines.frustumCulled = false;
    lines.renderOrder = 12;
    group.add(lines);
    return;
  }

  const segCount = positions.length / 6;
  for (let i = 0; i < segCount; i++) {
    const base = i * 6;
    const pts = positions.slice(base, base + 6);
    const r = (colors[base] + colors[base + 3]) * 0.5;
    const g = (colors[base + 1] + colors[base + 4]) * 0.5;
    const b = (colors[base + 2] + colors[base + 5]) * 0.5;
    const hex = (Math.round(r * 255) << 16) | (Math.round(g * 255) << 8) | Math.round(b * 255);
    addWideLineSegmentsFromPts(pts, hex, group, 12, lineW);
  }
}

function addMaxDisplacementMarker(model, lc, defFac, span, deformed, group, labelGroup) {
  if (!deformed) return;
  const info = maxDispNodeInfo(model, lc, defFac);
  if (!info || info.mag < 1e-12) return;

  const p0 = nodePosition(info.node, model, lc, defFac, false);
  const p1 = nodePosition(info.node, model, lc, defFac, true);
  const dir = p1.clone().sub(p0);
  const dlen = dir.length();
  if (dlen < 1e-12) return;
  const udir = dir.clone().multiplyScalar(1 / dlen);

  const r = Math.max(span * 0.01, 0.02);
  const sphere = new THREE.Mesh(
    new THREE.SphereGeometry(r, 18, 12),
    new THREE.MeshBasicMaterial({ color: 0xff0000, depthTest: true })
  );
  sphere.position.copy(p1);
  sphere.renderOrder = 14;
  group.add(sphere);

  const geo = new THREE.BufferGeometry().setFromPoints([p0, p1]);
  const mat = new THREE.LineDashedMaterial({
    color: 0xff0000,
    dashSize: Math.max(span * 0.02, 0.02),
    gapSize: Math.max(span * 0.012, 0.012),
    depthTest: true,
  });
  const dashed = new THREE.Line(geo, mat);
  dashed.computeLineDistances();
  dashed.frustumCulled = false;
  dashed.renderOrder = 13;
  group.add(dashed);

  const labelPos = p1.clone().addScaledVector(udir, span * 0.03);
  addReactionValueLabel(
    formatDispAbsValue(info.mag),
    labelPos,
    span,
    Math.max(reactionLabelScaleFactor(), 0.03),
    labelGroup,
    "#ff0000"
  );
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
  const span = Math.max(b[1] - b[0], b[3] - b[2], b[5] - b[4], 1.0);
  applyZUpView();
  controls.target.set(cx, cy, cz);
  camera.position.set(cx + span * 1.15, cy - span * 1.15, cz + span * 0.55);
  camera.near = span * 0.001;
  camera.far = span * 100;
  camera.updateProjectionMatrix();
  controls.update();
}

function updateWorldAxes(model) {
  clearGroup(axesGroup);
  if (!showWorldAxes) return;
  const span = modelSpan(model);
  const len = Math.max(span * 0.1, 0.12);
  const origin = new THREE.Vector3(0, 0, 0);
  const lineW = Math.max(supportLineWidthPx(), 1.5);
  const axes = [
    { dir: new THREE.Vector3(1, 0, 0), color: 0xff3333 },
    { dir: new THREE.Vector3(0, 1, 0), color: 0x33cc33 },
    { dir: new THREE.Vector3(0, 0, 1), color: 0x3366ff },
  ];
  for (const ax of axes) {
    addDirectionArrow(origin, ax.dir, len, axesGroup, ax.color, lineW);
  }
}

function buildModelScene(model) {
  clearGroup(modelGroup);
  clearGroup(labelGroup);
  clearWideLineMaterials();

  enrichModelReactions(model);

  const lc = el.lcSelect.value;
  const lcKey = String(lc);
  const defFac = parseFloat(el.defFactor.value) || 0;
  const complete = analysisComplete(model);
  const deformed = el.chkDeformed.checked && complete;
  const showDispContour = el.chkDispContour && el.chkDispContour.checked && complete;
  const showSupports = !el.chkSupports || el.chkSupports.checked;
  const showLoads = el.chkLoads.checked;
  const showLoadValues = el.chkLoadValues.checked;
  const showReactionValues = el.chkReactionValues && el.chkReactionValues.checked && complete;
  const showLabels = el.chkLabels.checked;
  const showElemLabels = el.chkElemLabels.checked;
  const showMaterial = el.chkMaterial.checked;
  const showSection = el.chkSection.checked;
  const nm = nodeMap(model);
  const em = elemMap(model);
  const span = modelSpan(model);
  const nodeLabelScale = nodeLabelScaleFactor();
  const elemLabelScale = elemLabelScaleFactor();
  const materialLabelScale = materialLabelScaleFactor();
  const sectionLabelScale = sectionLabelScaleFactor();
  const loadLabelScale = loadLabelScaleFactor();
  const reactionLabelScale = reactionLabelScaleFactor();

  const linePts = [];
  const linePtsDef = [];
  const contourPts = [];
  const contourColors = [];
  let dispAutoRange = null;
  let dispDisplayRange = null;

  if (showDispContour) {
    dispAutoRange = dispMagnitudeRange(model, lc, defFac);
    syncDispContourInputs(dispAutoRange, lc, defFac, false);
    dispDisplayRange = getDispContourDisplayRange();
    updateDispContourOverlay(true, dispAutoRange, lc, defFac, false);
  } else {
    updateDispContourOverlay(false, null, null, defFac, false);
  }

  for (const e of model.elements) {
    const n0 = nm[e.n0];
    const n1 = nm[e.n1];
    if (!n0 || !n1) continue;
    const p0u = nodePosition(n0, model, lc, defFac, false);
    const p1u = nodePosition(n1, model, lc, defFac, false);
    linePts.push(p0u.x, p0u.y, p0u.z, p1u.x, p1u.y, p1u.z);

    if (showDispContour && dispDisplayRange) {
      const useDefPos = deformed;
      const p0c = nodePosition(n0, model, lc, defFac, useDefPos);
      const p1c = nodePosition(n1, model, lc, defFac, useDefPos);
      contourPts.push(p0c.x, p0c.y, p0c.z, p1c.x, p1c.y, p1c.z);
      const m0 = nodeDispMagnitude(n0, lc, defFac);
      const m1 = nodeDispMagnitude(n1, lc, defFac);
      const c0 = dispContourColor(dispContourT(m0, dispDisplayRange));
      const c1 = dispContourColor(dispContourT(m1, dispDisplayRange));
      contourColors.push(c0.r, c0.g, c0.b, c1.r, c1.g, c1.b);
    }

    if (deformed && !showDispContour) {
      const p0d = nodePosition(n0, model, lc, defFac, true);
      const p1d = nodePosition(n1, model, lc, defFac, true);
      linePtsDef.push(p0d.x, p0d.y, p0d.z, p1d.x, p1d.y, p1d.z);
    }
  }

  if (linePts.length > 0) {
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.Float32BufferAttribute(linePts, 3));
    const mat = new THREE.LineBasicMaterial({
      color: COLORS.element,
      linewidth: 1,
      transparent: deformed || showDispContour,
      opacity: (deformed || showDispContour) ? 0.45 : 1.0,
    });
    modelGroup.add(new THREE.LineSegments(geo, mat));
  }

  if (showDispContour && contourPts.length > 0) {
    addDispContourLineSegments(contourPts, contourColors, modelGroup);
  } else if (deformed && linePtsDef.length > 0) {
    const geoDef = new THREE.BufferGeometry();
    geoDef.setAttribute("position", new THREE.Float32BufferAttribute(linePtsDef, 3));
    const matDef = new THREE.LineBasicMaterial({
      color: COLORS.deform,
      linewidth: 1,
    });
    modelGroup.add(new THREE.LineSegments(geoDef, matDef));
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

  addMaxDisplacementMarker(model, lc, defFac, span, deformed, modelGroup, labelGroup);

  const supSize = supportGizmoSize(model);
  if (showSupports) {
    for (const s of model.supports) {
      const n = nm[s.node];
      if (!n) continue;
      const p = nodePosition(n, model, lc, defFac, deformed);
      addSupportDisc(p, s.fixed, supSize, modelGroup);
    }
  }

  if (showLoads) {
    const arrowBase = loadArrowLength(model);
    const maxPMag = maxPointLoadMag(model, lc);
    const maxWMag = maxElementLoadMag(model, lc);

    if (model.point_loads) {
      for (const l of model.point_loads) {
        if (String(l.lc) !== String(lc)) continue;
        const n = nm[l.node];
        if (!n) continue;
        const p = nodePosition(n, model, lc, defFac, deformed);
        const fx = l.px, fy = l.py, fz = l.pz;
        const mag = Math.sqrt(fx * fx + fy * fy + fz * fz);
        if (mag < 1e-9) continue;
        const dir = new THREE.Vector3(fx / mag, fy / mag, fz / mag);
        const len = scaledReactionArrowLength(arrowBase, mag, maxPMag);
        const tip = addLoadArrow(p, dir, len, modelGroup);
        if (showLoadValues && tip) {
          const labelText = formatLoadPointValue(l, dir);
          if (labelText) {
            addLoadValueLabel(
              labelText,
              loadValueLabelPoint(tip, dir, span, loadLabelScale),
              span,
              loadLabelScale,
              labelGroup
            );
          }
        }
      }
    }

    drawElementInputLoads(model, {
      lc,
      defFac,
      deformed,
      span,
      nm,
      em,
      arrowBase,
      maxWMag,
      showValues: showLoadValues,
      loadLabelScale,
    });
  }

  const showReactionLabels = complete && (
    el.chkReactionValues.checked || (el.chkReactions && el.chkReactions.checked)
  );

  drawSupportReactions(model, {
    lc,
    lcKey,
    defFac,
    deformed,
    showValues: showReactionLabels,
    span,
    nm,
    reactionLabelScale,
  });

  if (showLabels) {
    for (const n of model.nodes) {
      const p = nodePosition(n, model, lc, defFac, deformed);
      const sprite = makeTextSprite(String(n.id), span, {
        scaleFactor: nodeLabelScale,
        bg: null,
        fg: colorHex(COLORS.nodeLabel),
        opaque: true,
      });
      sprite.renderOrder = 16;
      sprite.position.copy(nodeLabelPoint(p, span, nodeLabelScale));
      labelGroup.add(sprite);
    }
  }

  for (const e of model.elements) {
    const n0 = nm[e.n0];
    const n1 = nm[e.n1];
    if (!n0 || !n1) continue;
    const p0 = nodePosition(n0, model, lc, defFac, deformed);
    const p1 = nodePosition(n1, model, lc, defFac, deformed);

    if (showElemLabels) {
      const p = offsetLabelPoint(elemPointAlong(p0, p1, 0.55), p0, p1, 0);
      addElemLabel(String(e.id), p, span, elemLabelScale, labelGroup, LABEL_BG.elem);
    }
    if (showMaterial) {
      const text = elementMaterialText(e);
      if (text) {
        const p = offsetLabelPoint(elemPointAlong(p0, p1, 0.67), p0, p1, 1);
        addElemLabel(text, p, span, materialLabelScale, labelGroup, LABEL_BG.material);
      }
    }
    if (showSection) {
      const text = elementSectionText(e);
      if (text) {
        const p = elemPointAlong(p0, p1, 0.25);
        addElemLabel(text, p, span, sectionLabelScale, labelGroup, LABEL_BG.section);
      }
    }
  }

  buildForceDiagrams(model);
  updateWorldAxes(model);
  refreshDisplayStatus(model);
}

function formatForceValue(val) {
  if (Math.abs(val) < PRES_ZERO) return "0";
  return (val * 1e-3).toFixed(1);
}

function modelSpan(model) {
  const b = model.bounds;
  if (!b) return 1;
  return Math.max(b[1] - b[0], b[3] - b[2], b[5] - b[4], 1e-6);
}

function supportGizmoSize(model) {
  const span = modelSpan(model);
  const base = Math.max(span * 0.022, 0.07);
  const pct = parseFloat(viewerOptions.supportGizmoSize);
  if (!isFinite(pct) || pct < 1) return base;
  return base * (pct / 100);
}

function axisPerpendiculars(d) {
  const dir = d.clone().normalize();
  let u = new THREE.Vector3().crossVectors(dir, new THREE.Vector3(0, 1, 0));
  if (u.lengthSq() < 1e-12) {
    u = new THREE.Vector3().crossVectors(dir, new THREE.Vector3(1, 0, 0));
  }
  u.normalize();
  const v = new THREE.Vector3().crossVectors(dir, u).normalize();
  return { u, v };
}

function arcInPlane(center, axis, radius, startAngle, endAngle, segments) {
  const { u, v } = axisPerpendiculars(axis);
  const pts = [];
  for (let i = 0; i <= segments; i++) {
    const t = startAngle + (endAngle - startAngle) * (i / segments);
    pts.push(center.clone()
      .addScaledVector(u, Math.cos(t) * radius)
      .addScaledVector(v, Math.sin(t) * radius));
  }
  return pts;
}

function addLinePair(p0, p1, pts) {
  pts.push(p0.x, p0.y, p0.z, p1.x, p1.y, p1.z);
}

function addLineSegmentsFromPts(pts, color, group, renderOrder) {
  if (pts.length < 6) return;
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.Float32BufferAttribute(pts, 3));
  geo.computeBoundingSphere();
  const lines = new THREE.LineSegments(
    geo,
    new THREE.LineBasicMaterial({ color: color, depthTest: true })
  );
  lines.frustumCulled = false;
  lines.renderOrder = renderOrder;
  group.add(lines);
}

function clampLineWidthPx(v, fallback) {
  const n = parseFloat(v);
  if (!isFinite(n) || n < 0.5) return fallback;
  return Math.min(n, OPTIONS_LIMITS.supportLineWidth.max);
}

function supportLineWidthPx() {
  return clampLineWidthPx(viewerOptions.supportLineWidth, 2);
}

function dispContourLineWidthPx() {
  return clampLineWidthPx(viewerOptions.dispContourLineWidth, 2.5);
}

function addWideLineSegmentsFromPts(pts, color, group, renderOrder, lineWidthPx) {
  if (pts.length < 6) return;
  const geo = new LineSegmentsGeometry();
  geo.setPositions(pts);
  const mat = new LineMaterial({
    color: color,
    linewidth: lineWidthPx,
    worldUnits: false,
  });
  const w = el.viewport.clientWidth || 1;
  const h = el.viewport.clientHeight || 1;
  mat.resolution.set(w, h);
  wideLineMaterials.add(mat);
  const lines = new LineSegments2(geo, mat);
  lines.frustumCulled = false;
  lines.renderOrder = renderOrder;
  group.add(lines);
}

function supportDiscTextureKey(fixed) {
  return fixed.map(function (f) { return f ? "1" : "0"; }).join("");
}

function hatchSupportSector(ctx, cx, cy, r, startAngle, endAngle, strokeColor) {
  ctx.save();
  ctx.beginPath();
  ctx.moveTo(cx, cy);
  ctx.arc(cx, cy, r, startAngle, endAngle);
  ctx.closePath();
  ctx.clip();

  ctx.strokeStyle = strokeColor;
  ctx.lineWidth = 2;
  const step = 5;
  const span = r * 2.4;
  for (let d = -span; d < span; d += step) {
    ctx.beginPath();
    ctx.moveTo(cx - span, cy + d);
    ctx.lineTo(cx + span, cy + d - span);
    ctx.stroke();
  }
  ctx.restore();
}

function createSupportDiscTexture(fixed) {
  const key = supportDiscTextureKey(fixed);
  if (_supportDiscTexCache.has(key)) {
    return _supportDiscTexCache.get(key);
  }

  const px = 160;
  const canvas = document.createElement("canvas");
  canvas.width = px;
  canvas.height = px;
  const ctx = canvas.getContext("2d");
  const cx = px / 2;
  const cy = px / 2;
  const r = px / 2 - 6;
  const sectorColors = [
    COLORS.supportTrans, COLORS.supportTrans, COLORS.supportTrans,
    COLORS.supportRot, COLORS.supportRot, COLORS.supportRot,
  ];
  const outline = colorHex(COLORS.supportAnchor);

  ctx.clearRect(0, 0, px, px);

  for (let i = 0; i < 6; i++) {
    const a0 = -Math.PI / 2 + i * (Math.PI / 3);
    const a1 = a0 + Math.PI / 3;
    if (fixed[i]) {
      hatchSupportSector(ctx, cx, cy, r, a0, a1, colorHex(sectorColors[i]));
    }
  }

  ctx.strokeStyle = outline;
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.arc(cx, cy, r, 0, Math.PI * 2);
  ctx.stroke();

  for (let i = 0; i < 6; i++) {
    const a = -Math.PI / 2 + i * (Math.PI / 3);
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(cx + r * Math.cos(a), cy + r * Math.sin(a));
    ctx.stroke();
  }

  const tex = new THREE.CanvasTexture(canvas);
  tex.needsUpdate = true;
  _supportDiscTexCache.set(key, tex);
  return tex;
}

function addSupportDisc(center, fixed, size, group) {
  const tex = createSupportDiscTexture(fixed);
  const mat = new THREE.SpriteMaterial({
    map: tex,
    transparent: true,
    depthTest: true,
    depthWrite: false,
  });
  const sp = new THREE.Sprite(mat);
  sp.position.copy(center);
  sp.scale.set(size * 2, size * 2, 1);
  sp.renderOrder = 8;
  group.add(sp);
}

function loadArrowLength(model) {
  const span = modelSpan(model);
  const pct = parseFloat(viewerOptions.loadArrowSize);
  if (!isFinite(pct) || pct < 1) return span * 0.3;
  return span * (pct / 100);
}

function elemPointAlong(p0, p1, t) {
  return new THREE.Vector3().lerpVectors(p0, p1, t);
}

function offsetLabelPoint(p, p0, p1, side) {
  if (!side) return p;
  const along = new THREE.Vector3().subVectors(p1, p0);
  const elemLen = along.length();
  if (elemLen < 1e-12) return p;
  let perp = new THREE.Vector3().crossVectors(along, new THREE.Vector3(0, 1, 0));
  if (perp.lengthSq() < 1e-12) {
    perp = new THREE.Vector3().crossVectors(along, new THREE.Vector3(1, 0, 0));
  }
  perp.normalize().multiplyScalar(elemLen * 0.04 * side);
  return p.clone().add(perp);
}

function elementMaterialText(e) {
  const name = e.material_name != null ? e.material_name : e.material;
  if (name != null && String(name).trim() !== "") return String(name).trim();
  if (e.material_id !== undefined && e.material_id !== null) return String(e.material_id);
  return "";
}

function elementSectionText(e) {
  if (e.section != null && String(e.section).trim() !== "") return String(e.section).trim();
  if (e.section_id !== undefined && e.section_id !== null) return String(e.section_id);
  return "";
}

function formatLoadPointValue(l, dir) {
  const fdot = l.px * dir.x + l.py * dir.y + l.pz * dir.z;
  const fmag = Math.hypot(l.px, l.py, l.pz);
  if (fmag > 1e-6) return formatReactionValue(fdot);
  const mmag = Math.hypot(l.mx, l.my, l.mz);
  if (mmag > 1e-6) return formatReactionValue(mmag);
  return "";
}

function isGravityLoad(ld) {
  return !!(ld && (ld.gravity === true || ld.gravity === 1));
}

function formatLoadDistributedValue(mag, isGravity, displayValue) {
  if (displayValue) return displayValue;
  if (Math.abs(mag) < 1e-6) return "";
  const text = formatReactionValue(mag);
  return isGravity ? text + "G" : text;
}

function labelWorldHeight(span, scaleFactor, fallback) {
  return span * (scaleFactor != null ? scaleFactor : (fallback != null ? fallback : 0.03));
}

function labelOffsetDistance(span, scaleFactor, fallback) {
  return labelWorldHeight(span, scaleFactor, fallback) * 0.5 * 1.2;
}

function nodeLabelPoint(nodePoint, span, scaleFactor) {
  const pad = labelOffsetDistance(span, scaleFactor, 0.03);
  return new THREE.Vector3(nodePoint.x, nodePoint.y + pad, nodePoint.z);
}

function loadValueLabelPoint(tip, dir, span, scaleFactor) {
  const d = dir.clone().normalize();
  return tip.clone().addScaledVector(d, labelOffsetDistance(span, scaleFactor, 0.03));
}

function addLoadValueLabel(text, point, span, scaleFactor, group) {
  if (!text) return;
  addReactionValueLabel(text, point, span, scaleFactor, group, colorHex(COLORS.load));
}

function elemMap(model) {
  const em = {};
  for (const e of model.elements) em[e.id] = e;
  return em;
}

function localVecToGlobal(v, elem) {
  if (!elem || !elem.vx || !elem.vy || !elem.vz) return v;
  const vx = elem.vx;
  const vy = elem.vy;
  const vz = elem.vz;
  return new THREE.Vector3(
    vx[0] * v.x + vy[0] * v.y + vz[0] * v.z,
    vx[1] * v.x + vy[1] * v.y + vz[1] * v.z,
    vx[2] * v.x + vy[2] * v.y + vz[2] * v.z
  );
}

function elementLoadVector(w, t, elem, isGlobal) {
  const v = new THREE.Vector3(
    w[0] + t * (w[3] - w[0]),
    w[1] + t * (w[4] - w[1]),
    w[2] + t * (w[5] - w[2])
  );
  return isGlobal ? v : localVecToGlobal(v, elem);
}

function elementLoadMagnitude(w) {
  const m0 = Math.hypot(w[0], w[1], w[2]);
  const m1 = Math.hypot(w[3], w[4], w[5]);
  return Math.max(m0, m1);
}

function maxElementLoadMag(model, lc) {
  let max = 0;
  for (const ld of model.element_loads || []) {
    if (String(ld.lc) !== String(lc)) continue;
    max = Math.max(max, elementLoadMagnitude(ld.w));
  }
  return max;
}

function maxPointLoadMag(model, lc) {
  let max = 0;
  for (const l of model.point_loads || []) {
    if (String(l.lc) !== String(lc)) continue;
    max = Math.max(max, Math.hypot(l.px, l.py, l.pz));
  }
  return max;
}

function drawElementInputLoads(model, opts) {
  const {
    lc, defFac, deformed, span, nm, em, arrowBase, maxWMag,
    showValues, loadLabelScale,
  } = opts;
  const loads = model.element_loads;
  if (!loads || loads.length === 0) return;

  for (const ld of loads) {
    if (String(ld.lc) !== String(lc)) continue;
    const e = em[ld.elem];
    if (!e) continue;
    const n0 = nm[e.n0];
    const n1 = nm[e.n1];
    if (!n0 || !n1) continue;

    const w = ld.w;
    const mag = elementLoadMagnitude(w);
    if (mag < 1e-9) continue;

    const t = 0.5;
    const p0 = nodePosition(n0, model, lc, defFac, deformed);
    const p1 = nodePosition(n1, model, lc, defFac, deformed);
    const p = elemPointAlong(p0, p1, t);
    const wGlob = elementLoadVector(w, t, e, ld.global);
    if (wGlob.lengthSq() < 1e-18) continue;

    const dir = wGlob.clone().normalize();
    const len = scaledReactionArrowLength(arrowBase, mag, maxWMag);
    const tip = addLoadArrow(p, dir, len, modelGroup);
    if (showValues && tip) {
      const labelText = formatLoadDistributedValue(mag, isGravityLoad(ld), ld.display_value);
      if (labelText) {
        addLoadValueLabel(
          labelText,
          loadValueLabelPoint(tip, dir, span, loadLabelScale),
          span,
          loadLabelScale,
          labelGroup
        );
      }
    }
  }
}

function formatReactionValue(val) {
  if (Math.abs(val) < 1e-6) return "0";
  return val.toFixed(1);
}

function supportReactsForLc(model, s, lcKey) {
  if (s.reacts) {
    if (s.reacts[lcKey]) return s.reacts[lcKey];
    const alt = String(Number(lcKey));
    if (s.reacts[alt]) return s.reacts[alt];
  }
  for (const r of model.reactions || []) {
    if (r.node === s.node && String(r.lc) === lcKey) {
      return [r.rx, r.ry, r.rz, r.mx, r.my, r.mz];
    }
  }
  return null;
}

function modelHasReactionData(model, lcKey) {
  enrichModelReactions(model);
  for (const s of model.supports || []) {
    if (supportReactsForLc(model, s, lcKey)) return true;
  }
  return false;
}

function orientMeshAxisX(mesh, dir) {
  const xAxis = dir.clone().normalize();
  let refUp = new THREE.Vector3(0, 0, 1);
  if (Math.abs(xAxis.dot(refUp)) > 0.92) {
    refUp = new THREE.Vector3(0, 1, 0);
  }
  const yAxis = new THREE.Vector3().crossVectors(refUp, xAxis).normalize();
  const zAxis = new THREE.Vector3().crossVectors(xAxis, yAxis).normalize();
  mesh.setRotationFromMatrix(new THREE.Matrix4().makeBasis(xAxis, yAxis, zAxis));
}

function createLabelTexture(canvas, opaqueText) {
  const tex = new THREE.CanvasTexture(canvas);
  tex.needsUpdate = true;
  tex.minFilter = THREE.LinearFilter;
  tex.magFilter = THREE.LinearFilter;
  tex.premultiplyAlpha = opaqueText;
  if (renderer && renderer.capabilities) {
    tex.anisotropy = Math.min(4, renderer.capabilities.getMaxAnisotropy());
  }
  return tex;
}

function buildLabelCanvas(text, span, opts) {
  opts = opts || {};
  const bgSpecified = Object.prototype.hasOwnProperty.call(opts, "bg");
  const bg = bgSpecified ? opts.bg : "rgba(0,0,0,0.55)";
  const fg = opts.fg || "#ffffff";
  const pad = opts.pad != null ? opts.pad : 4;
  const factor = opts.scaleFactor != null ? opts.scaleFactor : 0.06;
  const quality = labelTextureQualityScale(factor);
  const baseFs = 28;

  const canvas = document.createElement("canvas");
  const ctx = canvas.getContext("2d");
  const fs = baseFs * quality;
  const padPx = pad * quality;
  const fontSpec = fs + "px monospace";

  ctx.font = fontSpec;
  const textW = ctx.measureText(text).width;
  canvas.width = Math.ceil(textW + padPx * 2);
  canvas.height = fs + padPx * 2;

  ctx.font = fontSpec;
  ctx.imageSmoothingEnabled = true;
  if (ctx.imageSmoothingQuality) {
    ctx.imageSmoothingQuality = "high";
  }

  if (bg != null && bg !== "transparent") {
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
  }
  ctx.fillStyle = fg;
  ctx.globalAlpha = 1;
  ctx.fillText(text, padPx, quality * (baseFs + pad - 2));

  const opaqueText = opts.opaque && (bg == null || bg === "transparent");
  if (opaqueText) {
    premultiplyCanvasAlpha(canvas);
  }

  const worldH = span * factor;
  const worldW = worldH * (canvas.width / canvas.height);
  return { canvas, opaqueText, worldW, worldH };
}

function makeTextPlaneMesh(text, span, opts) {
  const { canvas, opaqueText, worldW, worldH } = buildLabelCanvas(text, span, opts);
  const tex = createLabelTexture(canvas, opaqueText);
  const mat = new THREE.MeshBasicMaterial({
    map: tex,
    transparent: true,
    depthTest: false,
    depthWrite: false,
    side: THREE.DoubleSide,
    opacity: 1,
    premultipliedAlpha: opaqueText,
    alphaTest: opaqueText ? 0.01 : 0,
  });
  const mesh = new THREE.Mesh(new THREE.PlaneGeometry(worldW, worldH), mat);
  mesh.renderOrder = 15;
  return { mesh, worldW, worldH };
}

function addOrientedReactionLabel(text, contact, axisDir, span, scaleFactor, group, fgColor, fromNodeSign) {
  const d = axisDir.clone().normalize();
  const { mesh, worldW } = makeTextPlaneMesh(text, span, {
    bg: null,
    fg: fgColor,
    pad: 2,
    scaleFactor: scaleFactor,
  });
  orientMeshAxisX(mesh, d);
  const pad = labelOffsetDistance(span, scaleFactor, 0.03);
  mesh.position.copy(contact).addScaledVector(d, fromNodeSign * (pad + worldW * 0.5));
  group.add(mesh);
}

function drawSupportReactions(model, opts) {
  const {
    lc, lcKey, defFac, deformed, showValues, span, nm, reactionLabelScale,
  } = opts;
  if (!showValues) return;
  if (!analysisComplete(model) || !model.supports || model.supports.length === 0) return;

  for (const s of model.supports) {
    const r = supportReactsForLc(model, s, lcKey);
    if (!r) continue;
    const n = nm[s.node];
    if (!n) continue;
    const p = nodePosition(n, model, lc, defFac, deformed);
    const fx = r[0], fy = r[1], fz = r[2];
    const mx = r[3], my = r[4], mz = r[5];

    const forceAxes = [
      new THREE.Vector3(1, 0, 0),
      new THREE.Vector3(0, 1, 0),
      new THREE.Vector3(0, 0, 1),
    ];
    const forces = [fx, fy, fz];
    for (let i = 0; i < 3; i++) {
      const fval = forces[i];
      if (Math.abs(fval) < 1e-9) continue;
      const dir = forceAxes[i].clone().multiplyScalar(fval >= 0 ? 1 : -1);
      addOrientedReactionLabel(
        formatReactionValue(fval),
        p,
        dir,
        span,
        reactionLabelScale,
        labelGroup,
        colorHex(COLORS.reaction),
        -1
      );
    }

    const momentAxes = [
      new THREE.Vector3(1, 0, 0),
      new THREE.Vector3(0, 1, 0),
      new THREE.Vector3(0, 0, 1),
    ];
    const moments = [mx, my, mz];
    for (let i = 0; i < 3; i++) {
      const mval = moments[i];
      if (Math.abs(mval) < 1e-9) continue;
      const axisDir = momentAxes[i].clone().multiplyScalar(mval >= 0 ? 1 : -1);
      addOrientedReactionLabel(
        formatReactionValue(mval),
        p,
        axisDir,
        span,
        reactionLabelScale,
        labelGroup,
        colorHex(COLORS.reactionMoment),
        1
      );
    }
  }
}

function maxReactionForceMag(model, lcKey) {
  let max = 0;
  for (const s of model.supports || []) {
    const r = supportReactsForLc(model, s, lcKey);
    if (!r) continue;
    for (let i = 0; i < 3; i++) {
      max = Math.max(max, Math.abs(r[i]));
    }
  }
  return max;
}

function maxReactionMomentMag(model, lcKey) {
  let max = 0;
  for (const s of model.supports || []) {
    const r = supportReactsForLc(model, s, lcKey);
    if (!r) continue;
    for (let i = 3; i < 6; i++) {
      const mag = Math.abs(r[i]);
      if (mag > max) max = mag;
    }
  }
  return max;
}

function scaledReactionArrowLength(baseLen, mag, maxMag) {
  if (maxMag < 1e-9) return baseLen * 0.5;
  return baseLen * Math.max(0.2, mag / maxMag);
}

function colorHex(c) {
  return "#" + (c >>> 0).toString(16).padStart(6, "0");
}

function addReactionValueLabel(text, point, span, scaleFactor, group, fgColor) {
  const sprite = makeTextSprite(text, span, {
    bg: null,
    fg: fgColor,
    pad: 2,
    scaleFactor: scaleFactor,
  });
  sprite.position.copy(point);
  sprite.renderOrder = 15;
  group.add(sprite);
}

function addElemLabel(text, point, span, scaleFactor, group, bg) {
  const sprite = makeTextSprite(text, span, {
    bg: bg || LABEL_BG.elem,
    fg: "#ffffff",
    pad: 4,
    scaleFactor: scaleFactor,
  });
  sprite.position.copy(point);
  sprite.renderOrder = 15;
  group.add(sprite);
}

function addAnnotationLabel(text, point, dir, span, scaleFactor, group, bg) {
  if (!text) return;
  const offset = dir.clone().normalize().multiplyScalar(span * 0.04);
  const pos = point.clone().add(offset);
  addElemLabel(text, pos, span, scaleFactor, group, bg || LABEL_BG.load);
}

function arrowPerpendicular(dir) {
  const d = dir.clone().normalize();
  const ref = Math.abs(d.y) < 0.9
    ? new THREE.Vector3(0, 1, 0)
    : new THREE.Vector3(1, 0, 0);
  return new THREE.Vector3().crossVectors(d, ref).normalize();
}

function addDirectedArrow(tail, head, group, color, lineWidthPx) {
  const d = head.clone().sub(tail);
  const length = d.length();
  if (length < 1e-12) return head.clone();
  const dir = d.clone().normalize();
  const headLen = Math.max(length * 0.22, length * 0.08);
  const headWide = headLen * 0.55;
  const wingBase = head.clone().addScaledVector(dir, -headLen);
  const perp = arrowPerpendicular(dir);
  const wingA = wingBase.clone().addScaledVector(perp, headWide);
  const wingB = wingBase.clone().addScaledVector(perp, -headWide);

  if (lineWidthPx != null) {
    const pts = [];
    addLinePair(tail, head, pts);
    addLinePair(wingA, head, pts);
    addLinePair(wingB, head, pts);
    addWideLineSegmentsFromPts(pts, color, group, 5, lineWidthPx);
    return head.clone();
  }

  const lineMat = new THREE.LineBasicMaterial({ color: color, depthTest: true });
  const shaftGeo = new THREE.BufferGeometry().setFromPoints([tail, head]);
  shaftGeo.computeBoundingSphere();
  const shaft = new THREE.Line(shaftGeo, lineMat);
  shaft.frustumCulled = false;
  shaft.renderOrder = 5;
  group.add(shaft);

  const headPts = [
    wingA.x, wingA.y, wingA.z, head.x, head.y, head.z,
    wingB.x, wingB.y, wingB.z, head.x, head.y, head.z,
  ];
  const headGeo = new THREE.BufferGeometry();
  headGeo.setAttribute("position", new THREE.Float32BufferAttribute(headPts, 3));
  headGeo.computeBoundingSphere();
  const headLines = new THREE.LineSegments(headGeo, lineMat);
  headLines.frustumCulled = false;
  headLines.renderOrder = 6;
  group.add(headLines);

  return head.clone();
}

function addDirectionArrow(origin, dir, length, group, color, lineWidthPx) {
  const d = dir.clone().normalize();
  const tip = origin.clone().addScaledVector(d, length);
  return addDirectedArrow(origin, tip, group, color, lineWidthPx);
}

function addLoadArrow(origin, dir, length, group) {
  return addDirectionArrow(origin, dir, length, group, COLORS.load);
}

function nodeLabelScaleFactor() {
  const v = parseFloat(viewerOptions.nodeLabelSize);
  if (!isFinite(v) || v < 1) return 0.03;
  return v / 100;
}

function elemLabelScaleFactor() {
  const v = parseFloat(viewerOptions.elemLabelSize);
  if (!isFinite(v) || v < 1) return 0.03;
  return v / 100;
}

function materialLabelScaleFactor() {
  const v = parseFloat(viewerOptions.materialLabelSize);
  if (!isFinite(v) || v < 1) return 0.04;
  return v / 100;
}

function sectionLabelScaleFactor() {
  const v = parseFloat(viewerOptions.sectionLabelSize);
  if (!isFinite(v) || v < 1) return 0.03;
  return v / 100;
}

function loadLabelScaleFactor() {
  const v = parseFloat(viewerOptions.loadLabelSize);
  if (!isFinite(v) || v < 1) return 0.03;
  return v / 100;
}

function reactionLabelScaleFactor() {
  const v = parseFloat(viewerOptions.reactionLabelSize);
  if (!isFinite(v) || v < 1) return 0.03;
  return v / 100;
}

function setForceControlsEnabled(enabled) {
  el.forceSelect.disabled = !enabled;
  el.frcDiv.disabled = !enabled;
  el.frcFactor.disabled = !enabled;
  el.chkForceValues.disabled = !enabled;
  if (!enabled) {
    el.forceSelect.value = "0";
    updateForceLegend(0, null);
  }
}

function setReactionControlsEnabled(enabled) {
  if (!el.chkReactions || !el.chkReactionValues) return;
  if (!enabled) {
    el.chkReactions.checked = false;
    el.chkReactionValues.checked = false;
  }
}

function setDispContourControlsEnabled(enabled) {
  if (!el.chkDispContour) return;
  el.chkDispContour.disabled = !enabled;
  if (!enabled) {
    el.chkDispContour.checked = false;
    updateDispContourOverlay(false, null, null, 0, false);
  }
}

function forceLabelScaleFactor() {
  const v = parseFloat(viewerOptions.forceLabelSize);
  if (!isFinite(v) || v < 1) return 0.06;
  return v / 100;
}

function updateForceLegend(forceId, lc) {
  if (forceId === 0 || lc == null) {
    el.forceLegend.classList.remove("visible");
    el.forceLegend.textContent = "";
    return;
  }
  const unit = FORCE_UNITS[forceId] || "";
  el.forceLegend.classList.add("visible");
  el.forceLegend.textContent =
    "ELEMENT FORCE: " + FORCE_LABELS[forceId] + " [" + unit + "]\n" +
    "LOAD CASE: " + lc;
}

function computeDispFac(model, forceId, lcKey, frcFactor) {
  const b = model.bounds;
  if (!b) return 1;
  const span = Math.max(b[1] - b[0], b[3] - b[2], b[5] - b[4], 1);
  const knRows = forceId <= 3;
  const rows = knRows ? [0, 1, 2, 6, 7, 8] : [3, 4, 5, 9, 10, 11];
  let overallMax = 0;

  for (const e of model.elements) {
    const f = e.forces && e.forces[lcKey];
    if (!f) continue;
    for (const r of rows) {
      overallMax = Math.max(overallMax, Math.abs(f[r] || 0));
    }
  }

  if (!knRows) {
    for (const e of model.elements) {
      const f = e.forces && e.forces[lcKey];
      const lds = e.local_wloads && e.local_wloads[lcKey];
      if (!f || !lds) continue;
      const len = e.len || 1;
      const wzi = lds[2], wzj = lds[5], wyi = lds[1], wyj = lds[4];
      const qzi = f[2], myi = f[4], qyi = f[1], mzi = f[5];
      let wXc = wzi + (wzj - wzi) * 0.5;
      let mXc = myi + qzi * 0.5 * len + (1 / 6) * (wzi + 2 * wXc) * (0.5 * len) ** 2;
      overallMax = Math.max(overallMax, Math.abs(mXc));
      wXc = wyi + (wyj - wyi) * 0.5;
      mXc = mzi - qyi * 0.5 * len - (1 / 6) * (wyi + 2 * wXc) * (0.5 * len) ** 2;
      overallMax = Math.max(overallMax, Math.abs(mXc));
    }
  }

  if (overallMax < PRES_ZERO) return span * 0.01;
  return 0.01 * frcFactor * span / overallMax;
}

function modelHasForceData(model, lcKey) {
  if (!model || !analysisComplete(model) || !model.elements || model.elements.length === 0) {
    return false;
  }
  if (model.schema != null && model.schema < 2) {
    return false;
  }
  return model.elements.some(function (e) {
    return e.forces && e.forces[lcKey] && e.vy && e.vz && e.len != null;
  });
}

function addForceStemAndSpline(stemPts, splinePts, group) {
  if (stemPts.length >= 6) {
    const stemGeo = new THREE.BufferGeometry();
    stemGeo.setAttribute("position", new THREE.Float32BufferAttribute(stemPts, 3));
    stemGeo.computeBoundingSphere();
    const stems = new THREE.LineSegments(
      stemGeo,
      new THREE.LineBasicMaterial({ color: COLORS.force, depthTest: true })
    );
    stems.frustumCulled = false;
    stems.renderOrder = 10;
    group.add(stems);
  }
  if (splinePts.length >= 2) {
    const lineGeo = new THREE.BufferGeometry().setFromPoints(splinePts);
    lineGeo.computeBoundingSphere();
    const spline = new THREE.Line(
      lineGeo,
      new THREE.LineBasicMaterial({ color: COLORS.force, depthTest: true })
    );
    spline.frustumCulled = false;
    spline.renderOrder = 11;
    group.add(spline);
  }
}

function addForceValueLabel(text, point, model, group) {
  const span = modelSpan(model);
  const sprite = makeTextSprite(text, span, {
    bg: "rgba(0, 71, 171, 0.82)",
    fg: "#ffffff",
    pad: 6,
    scaleFactor: forceLabelScaleFactor(),
  });
  sprite.renderOrder = 20;
  sprite.position.copy(point);
  group.add(sprite);
}

function buildForceDiagrams(model) {
  clearGroup(forceGroup);
  clearGroup(forceLabelGroup);

  const forceId = parseInt(el.forceSelect.value, 10) || 0;
  const lcKey = el.lcSelect.value;
  updateForceLegend(forceId, forceId > 0 ? lcKey : null);

  if (forceId === 0 || !analysisComplete(model)) return;
  if (forceId === 4) return;

  if (!modelHasForceData(model, lcKey)) {
    return;
  }

  const lc = lcKey;
  const defFac = parseFloat(el.defFactor.value) || 0;
  const deformed = el.chkDeformed.checked && analysisComplete(model);
  const divNum = parseInt(el.frcDiv.value, 10) || 8;
  const frcFactor = parseFloat(el.frcFactor.value) || 10;
  const dispFac = computeDispFac(model, forceId, lcKey, frcFactor);
  const nm = nodeMap(model);
  const showValues = el.chkForceValues.checked;

  for (const e of model.elements) {
    const n0 = nm[e.n0];
    const n1 = nm[e.n1];
    const f = e.forces && e.forces[lcKey];
    if (!n0 || !n1 || !f || e.len == null || !e.vy || !e.vz) continue;

    const p0 = nodePosition(n0, model, lc, defFac, deformed);
    const p1 = nodePosition(n1, model, lc, defFac, deformed);
    const lds = (e.local_wloads && e.local_wloads[lcKey]) || [0, 0, 0, 0, 0, 0];
    const stemPts = [];
    const splinePts = [];
    const labels = [];

    if (forceId === 1) {
      let vz = new THREE.Vector3().fromArray(e.vz);
      if (e.is_vxz && e.vx && e.vx[2] < PRES_ZERO) vz.multiplyScalar(-1);
      const ni = f[0], nj = f[6];
      const nXc = 0.5 * ni + 0.5 * nj;
      const mp = new THREE.Vector3().lerpVectors(p0, p1, 0.5).addScaledVector(vz, dispFac * nXc);

      for (let i = 0; i <= divNum; i++) {
        const t = i / divNum;
        const pt = new THREE.Vector3().lerpVectors(p0, p1, t);
        const nX = ni + (nj - ni) * t;
        const ptF = pt.clone().addScaledVector(vz, dispFac * nX);
        stemPts.push(pt.x, pt.y, pt.z, ptF.x, ptF.y, ptF.z);
        splinePts.push(ptF);
      }
      labels.push(
        { val: ni, pt: splinePts[0] },
        { val: nXc, pt: mp },
        { val: nj, pt: splinePts[splinePts.length - 1] },
      );
    } else if (forceId === 2) {
      const vy = new THREE.Vector3().fromArray(e.vy);
      const wyi = lds[1], wyj = lds[4];
      const qyi = f[1], qyj = f[7];
      const wXc = wyi + (wyj - wyi) * 0.5;
      const qXc = qyi + 0.5 * (wyi + wXc) * 0.5 * e.len;
      const mp = new THREE.Vector3().lerpVectors(p0, p1, 0.5).addScaledVector(vy, dispFac * qXc);

      for (let i = 0; i <= divNum; i++) {
        const t = i / divNum;
        const x = t * e.len;
        const pt = new THREE.Vector3().lerpVectors(p0, p1, t);
        const wX = wyi + (wyj - wyi) * t;
        const qX = qyi + 0.5 * (wyi + wX) * x;
        const ptF = pt.clone().addScaledVector(vy, dispFac * qX);
        stemPts.push(pt.x, pt.y, pt.z, ptF.x, ptF.y, ptF.z);
        splinePts.push(ptF);
      }
      labels.push(
        { val: qyi, pt: splinePts[0] },
        { val: qXc, pt: mp },
        { val: qyj, pt: splinePts[splinePts.length - 1] },
      );
    } else if (forceId === 3) {
      const vz = new THREE.Vector3().fromArray(e.vz);
      const wzi = lds[2], wzj = lds[5];
      const qzi = f[2], qzj = f[8];
      const wXc = wzi + (wzj - wzi) * 0.5;
      const qXc = -qzi - 0.5 * (wzi + wXc) * 0.5 * e.len;
      const mp = new THREE.Vector3().lerpVectors(p0, p1, 0.5).addScaledVector(vz, dispFac * qXc);

      for (let i = 0; i <= divNum; i++) {
        const t = i / divNum;
        const x = t * e.len;
        const pt = new THREE.Vector3().lerpVectors(p0, p1, t);
        const wX = wzi + (wzj - wzi) * t;
        const qX = -qzi - 0.5 * (wzi + wX) * x;
        const ptF = pt.clone().addScaledVector(vz, dispFac * qX);
        stemPts.push(pt.x, pt.y, pt.z, ptF.x, ptF.y, ptF.z);
        splinePts.push(ptF);
      }
      labels.push(
        { val: qzi, pt: splinePts[0] },
        { val: qXc, pt: mp },
        { val: qzj, pt: splinePts[splinePts.length - 1] },
      );
    } else if (forceId === 5) {
      let vz = new THREE.Vector3().fromArray(e.vz);
      if (e.is_vxz) vz.multiplyScalar(-1);
      const wzi = lds[2], wzj = lds[5];
      const qzi = f[2], myi = f[4], myj = f[10];
      const wXc = wzi + (wzj - wzi) * 0.5;
      const mXc = myi + qzi * 0.5 * e.len + (1 / 6) * (wzi + 2 * wXc) * (0.5 * e.len) ** 2;
      const mp = new THREE.Vector3().lerpVectors(p0, p1, 0.5).addScaledVector(vz, -dispFac * mXc);

      for (let i = 0; i <= divNum; i++) {
        const t = i / divNum;
        const x = t * e.len;
        const pt = new THREE.Vector3().lerpVectors(p0, p1, t);
        const wX = wzi + (wzj - wzi) * t;
        const mX = myi + qzi * x + (1 / 6) * (wzi + 2 * wX) * x * x;
        const ptF = pt.clone().addScaledVector(vz, -dispFac * mX);
        stemPts.push(pt.x, pt.y, pt.z, ptF.x, ptF.y, ptF.z);
        splinePts.push(ptF);
      }
      labels.push(
        { val: myi, pt: splinePts[0] },
        { val: mXc, pt: mp },
        { val: myj, pt: splinePts[splinePts.length - 1] },
      );
    } else if (forceId === 6) {
      let vy = new THREE.Vector3().fromArray(e.vy);
      if (e.is_vxz) vy.multiplyScalar(-1);
      const wyi = lds[1], wyj = lds[4];
      const qyi = f[1], mzi = f[5], mzj = f[11];
      const wXc = wyi + (wyj - wyi) * 0.5;
      const mXc = mzi - qyi * 0.5 * e.len - (1 / 6) * (wyi + 2 * wXc) * (0.5 * e.len) ** 2;
      const mp = new THREE.Vector3().lerpVectors(p0, p1, 0.5).addScaledVector(vy, dispFac * mXc);

      for (let i = 0; i <= divNum; i++) {
        const t = i / divNum;
        const x = t * e.len;
        const pt = new THREE.Vector3().lerpVectors(p0, p1, t);
        const wX = wyi + (wyj - wyi) * t;
        const mX = mzi - qyi * x - (1 / 6) * (wyi + 2 * wX) * x * x;
        const ptF = pt.clone().addScaledVector(vy, dispFac * mX);
        stemPts.push(pt.x, pt.y, pt.z, ptF.x, ptF.y, ptF.z);
        splinePts.push(ptF);
      }
      labels.push(
        { val: mzi, pt: splinePts[0] },
        { val: mXc, pt: mp },
        { val: mzj, pt: splinePts[splinePts.length - 1] },
      );
    }

    addForceStemAndSpline(stemPts, splinePts, forceGroup);
    if (showValues) {
      for (const item of labels) {
        addForceValueLabel(formatForceValue(item.val), item.pt, model, forceLabelGroup);
      }
    }
  }
}

function labelTextureQualityScale(scaleFactor) {
  const f = scaleFactor != null ? scaleFactor : 0.06;
  const dpr = typeof window !== "undefined" ? (window.devicePixelRatio || 1) : 1;
  return Math.min(16, Math.max(2, Math.round((f / 0.03) * dpr * 1.5)));
}

function premultiplyCanvasAlpha(canvas) {
  const ctx = canvas.getContext("2d");
  const img = ctx.getImageData(0, 0, canvas.width, canvas.height);
  const d = img.data;
  for (let i = 0; i < d.length; i += 4) {
    const a = d[i + 3] / 255;
    if (a <= 0) continue;
    d[i] = Math.round(d[i] * a);
    d[i + 1] = Math.round(d[i + 1] * a);
    d[i + 2] = Math.round(d[i + 2] * a);
  }
  ctx.putImageData(img, 0, 0);
}

function makeTextSprite(text, span, opts) {
  const { canvas, opaqueText, worldW, worldH } = buildLabelCanvas(text, span, opts);
  const tex = createLabelTexture(canvas, opaqueText);
  const mat = new THREE.SpriteMaterial({
    map: tex,
    depthTest: false,
    depthWrite: false,
    transparent: true,
    opacity: 1,
    premultipliedAlpha: opaqueText,
    alphaTest: opaqueText ? 0.01 : 0,
  });
  const sp = new THREE.Sprite(mat);
  sp.scale.set(worldW, worldH, 1);
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

function outputFileName(path) {
  const base = path.replace(/^.*\//, "").replace(/\.dat$/i, "");
  return base + "_out.dat";
}

function showTextDocumentWindow(text, title) {
  const pdfName = title.replace(/\.dat$/i, ".pdf");
  const w = window.open("", "_blank", "width=920,height=720,scrollbars=yes,resizable=yes");
  if (!w) {
    setStatus("Popup blocked — allow popups for this site");
    return;
  }
  const doc = w.document;
  doc.open();
  doc.write("<!DOCTYPE html><html><head><meta charset=\"UTF-8\"><title>");
  doc.write(title);
  doc.write("</title><style>");
  doc.write("body{margin:0;background:#1e1e24;color:#e8e6ed;}");
  doc.write("pre,body{font-family:'Liberation Mono','DejaVu Sans Mono','Nimbus Mono PS','Courier New',Courier,monospace;}");
  doc.write(".toolbar{padding:8px 12px;background:#252530;border-bottom:1px solid #3a3a48;display:flex;gap:8px;align-items:center;flex-wrap:wrap;}");
  doc.write(".toolbar button{background:#5eff4d;color:#111;border:none;border-radius:4px;padding:6px 12px;font-weight:600;cursor:pointer;}");
  doc.write("header.doc-title{padding:8px 12px;font-weight:600;border-bottom:1px solid #3a3a48;font-size:13px;}");
  doc.write("pre{margin:0;padding:12px;font-size:11px;line-height:1.2;white-space:pre;overflow:auto;}");
  doc.write("@page{size:A4 landscape;margin:10mm;}");
  doc.write("@media print{");
  doc.write(".no-print{display:none !important;}");
  doc.write("html,body{background:#fff;color:#000;margin:0;padding:0;}");
  doc.write("header.doc-title{display:none;}");
  doc.write("pre{padding:0;margin:0;font-size:6pt;line-height:1.15;white-space:pre;overflow:visible;}");
  doc.write("}");
  doc.write("</style></head><body>");
  doc.write("<div class=\"toolbar no-print\">");
  doc.write("<button type=\"button\" id=\"btnPdf\">Save as PDF (A4 landscape)</button>");
  doc.write("</div>");
  doc.write("<header class=\"doc-title\">");
  doc.write(title);
  doc.write("</header><pre></pre></body></html>");
  doc.close();
  doc.querySelector("pre").textContent = text;
  doc.getElementById("btnPdf").onclick = function () {
    doc.title = pdfName;
    w.print();
  };
}

function showResultsWindow(text, path) {
  showTextDocumentWindow(text, outputFileName(path));
}

async function fetchInputText(path) {
  const url = "/api/input?path=" + encodeURIComponent(path);
  const res = await fetch(url);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || res.statusText);
  }
  return res.text();
}

async function openInputWindow() {
  const path = el.modelSelect.value;
  if (!path) return;

  setStatus("Loading " + path + "…");
  try {
    const text = await fetchInputText(path);
    showTextDocumentWindow(text, path);
    setStatus(path + " — input file opened in new window");
  } catch (ex) {
    setStatus("Error: " + ex.message);
  }
}

async function openResultsWindow() {
  const path = el.modelSelect.value;
  if (!path) return;

  let text = currentResultsText;

  if (text == null || text == "") {
    setStatus("Solving " + path + " for output…");
    try {
      currentModel = await fetchModel(path, true);
      text = currentModel.results_text;
      if (text == null || text == "") {
        throw new Error("No result text from server — restart: stb view");
      }
      currentResultsText = text;
      fillLcSelect(currentModel);
      enrichModelReactions(currentModel);
      const complete = analysisComplete(currentModel);
      el.chkDeformed.disabled = !complete;
      setForceControlsEnabled(complete);
      setReactionControlsEnabled(complete);
      setDispContourControlsEnabled(complete);
      if (complete) el.chkReactions.checked = true;
      buildModelScene(currentModel);
    } catch (ex) {
      setStatus("Error: " + ex.message);
      return;
    }
  }

  showResultsWindow(text, path);
  setStatus(path + " — output opened in new window");
}

async function loadSelectedModel(solve) {
  const path = el.modelSelect.value;
  if (!path) return;
  if (solve) {
    setStatus("Solving " + path + "…");
  } else {
    setStatus("Loading " + path + "…");
    currentResultsText = null;
  }
  try {
    currentModel = await fetchModel(path, solve);
    if (solve) {
      currentResultsText = currentModel.results_text || null;
    }
    enrichModelReactions(currentModel);
    fillLcSelect(currentModel);
    const complete = analysisComplete(currentModel);
    el.chkDeformed.disabled = !complete;
    setForceControlsEnabled(complete);
    setReactionControlsEnabled(complete);
    setDispContourControlsEnabled(complete);
    if (!complete) el.chkDeformed.checked = false;
    if (!complete && el.chkDispContour) el.chkDispContour.checked = false;
    if (solve && complete) {
      el.chkReactions.checked = true;
    }
    buildModelScene(currentModel);
    if (!solve || !complete) {
      fitCamera(currentModel);
    }
    saveLastModelPath(path);
  } catch (ex) {
    setStatus("Error: " + ex.message);
  }
}

async function bootstrap() {
  initThree();
  initViewerOptions();
  initDraggablePanel({
    panel: el.resultsPanel,
    header: el.resultsPanelHeader,
    collapseBtn: el.btnPanelCollapse,
    toggleBtn: el.btnTogglePanel,
    storageKey: "stb_viewer_results_panel",
    defaultHidden: false,
  });
  initDraggablePanel({
    panel: el.optionsPanel,
    header: el.optionsPanelHeader,
    collapseBtn: el.btnOptionsCollapse,
    toggleBtn: el.btnToggleOptions,
    storageKey: "stb_viewer_options_panel",
    defaultHidden: true,
  });
  try {
    const data = await fetchModelList();
    el.modelSelect.innerHTML = "";
    for (const p of data.models) {
      const opt = document.createElement("option");
      opt.value = p;
      opt.textContent = p;
      el.modelSelect.appendChild(opt);
    }
    const launchFile = launchFileFromUrl();
    const initial = resolveInitialModel(data.models, data.default);
    if (initial) el.modelSelect.value = initial;
    if (launchFile && initial === launchFile) clearLaunchFileFromUrl();
    await loadSelectedModel(false);
  } catch (ex) {
    setStatus("Error: " + ex.message);
  }
}

el.btnReload.addEventListener("click", () => loadSelectedModel(false));
el.btnSolve.addEventListener("click", () => loadSelectedModel(true));

function isViewerTextInputTarget(target) {
  if (!target) return false;
  const tag = target.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || target.isContentEditable;
}

document.addEventListener("keydown", (ev) => {
  if (ev.key !== "F5" && ev.code !== "F5") return;
  if (isViewerTextInputTarget(ev.target)) return;
  ev.preventDefault();
  loadSelectedModel(true);
});

el.btnToggleAxes.addEventListener("click", () => {
  showWorldAxes = !showWorldAxes;
  el.btnToggleAxes.classList.toggle("active", showWorldAxes);
  if (currentModel) {
    updateWorldAxes(currentModel);
  } else {
    clearGroup(axesGroup);
  }
});

el.btnInput.addEventListener("click", () => openInputWindow());
el.btnOutput.addEventListener("click", () => openResultsWindow());
el.modelSelect.addEventListener("change", () => loadSelectedModel(false));
el.lcSelect.addEventListener("change", () => {
  dispContourScaleKey = null;
  if (currentModel) rebuildScene();
});
el.defFactor.addEventListener("change", () => {
  dispContourScaleKey = null;
  if (currentModel) rebuildScene();
});
el.chkDeformed.addEventListener("change", () => {
  if (currentModel) rebuildScene();
});
el.chkDispContour.addEventListener("change", () => {
  if (currentModel && el.chkDispContour.checked) {
    dispContourScaleKey = null;
  }
  if (currentModel) rebuildScene();
});
if (el.dispContourMin) {
  el.dispContourMin.addEventListener("change", () => {
    if (currentModel) rebuildScene();
  });
}
if (el.dispContourMax) {
  el.dispContourMax.addEventListener("change", () => {
    if (currentModel) rebuildScene();
  });
}
if (el.btnDispContourAuto) {
  el.btnDispContourAuto.addEventListener("click", () => applyDispContourAutoRange());
}
el.chkSupports.addEventListener("change", () => {
  if (currentModel) rebuildScene();
});
el.chkLoads.addEventListener("change", () => {
  if (currentModel) rebuildScene();
});
el.chkLoadValues.addEventListener("change", () => {
  if (currentModel) rebuildScene();
});
el.chkReactions.addEventListener("change", () => {
  if (currentModel) rebuildScene();
});
el.chkReactionValues.addEventListener("change", () => {
  if (currentModel) rebuildScene();
});
el.chkLabels.addEventListener("change", () => {
  if (currentModel) rebuildScene();
});
el.chkElemLabels.addEventListener("change", () => {
  if (currentModel) rebuildScene();
});
el.chkMaterial.addEventListener("change", () => {
  if (currentModel) rebuildScene();
});
el.chkSection.addEventListener("change", () => {
  if (currentModel) rebuildScene();
});
el.forceSelect.addEventListener("change", () => {
  if (currentModel) rebuildScene();
});
el.frcDiv.addEventListener("input", () => {
  el.frcDivVal.textContent = el.frcDiv.value;
  if (currentModel) rebuildScene();
});
el.frcFactor.addEventListener("input", () => {
  el.frcFactorVal.textContent = el.frcFactor.value;
  if (currentModel) rebuildScene();
});
el.chkForceValues.addEventListener("change", () => {
  if (currentModel) rebuildScene();
});

function readOptionsFromUi() {
  viewerOptions.loadArrowSize = clampViewerOption(
    "loadArrowSize", parseInt(el.optLoadArrow.value, 10) || OPTIONS_DEFAULTS.loadArrowSize);
  viewerOptions.supportGizmoSize = clampViewerOption(
    "supportGizmoSize", parseInt(el.optSupportGizmo.value, 10) || OPTIONS_DEFAULTS.supportGizmoSize);
  viewerOptions.supportLineWidth = clampViewerOption(
    "supportLineWidth", parseFloat(el.optSupportLineWidth.value) || OPTIONS_DEFAULTS.supportLineWidth);
  viewerOptions.dispContourLineWidth = clampViewerOption(
    "dispContourLineWidth", parseFloat(el.optDispContourLineWidth.value) || OPTIONS_DEFAULTS.dispContourLineWidth);
  viewerOptions.nodeLabelSize = clampViewerOption(
    "nodeLabelSize", parseInt(el.optNodeLabel.value, 10) || OPTIONS_DEFAULTS.nodeLabelSize);
  viewerOptions.elemLabelSize = clampViewerOption(
    "elemLabelSize", parseInt(el.optElemLabel.value, 10) || OPTIONS_DEFAULTS.elemLabelSize);
  viewerOptions.materialLabelSize = clampViewerOption(
    "materialLabelSize", parseInt(el.optMaterialLabel.value, 10) || OPTIONS_DEFAULTS.materialLabelSize);
  viewerOptions.sectionLabelSize = clampViewerOption(
    "sectionLabelSize", parseInt(el.optSectionLabel.value, 10) || OPTIONS_DEFAULTS.sectionLabelSize);
  viewerOptions.loadLabelSize = clampViewerOption(
    "loadLabelSize", parseInt(el.optLoadLabel.value, 10) || OPTIONS_DEFAULTS.loadLabelSize);
  viewerOptions.reactionLabelSize = clampViewerOption(
    "reactionLabelSize", parseInt(el.optReactionLabel.value, 10) || OPTIONS_DEFAULTS.reactionLabelSize);
  viewerOptions.forceLabelSize = clampViewerOption(
    "forceLabelSize", parseInt(el.optForceLabel.value, 10) || OPTIONS_DEFAULTS.forceLabelSize);
}

function applyOptionsToUi() {
  el.optLoadArrow.value = String(viewerOptions.loadArrowSize);
  el.optLoadArrowVal.textContent = String(viewerOptions.loadArrowSize);
  el.optSupportGizmo.value = String(viewerOptions.supportGizmoSize);
  el.optSupportGizmoVal.textContent = String(viewerOptions.supportGizmoSize);
  el.optSupportLineWidth.value = String(viewerOptions.supportLineWidth);
  el.optDispContourLineWidth.value = String(viewerOptions.dispContourLineWidth);
  el.optNodeLabel.value = String(viewerOptions.nodeLabelSize);
  el.optNodeLabelVal.textContent = String(viewerOptions.nodeLabelSize);
  el.optElemLabel.value = String(viewerOptions.elemLabelSize);
  el.optElemLabelVal.textContent = String(viewerOptions.elemLabelSize);
  el.optMaterialLabel.value = String(viewerOptions.materialLabelSize);
  el.optMaterialLabelVal.textContent = String(viewerOptions.materialLabelSize);
  el.optSectionLabel.value = String(viewerOptions.sectionLabelSize);
  el.optSectionLabelVal.textContent = String(viewerOptions.sectionLabelSize);
  el.optLoadLabel.value = String(viewerOptions.loadLabelSize);
  el.optLoadLabelVal.textContent = String(viewerOptions.loadLabelSize);
  el.optReactionLabel.value = String(viewerOptions.reactionLabelSize);
  el.optReactionLabelVal.textContent = String(viewerOptions.reactionLabelSize);
  el.optForceLabel.value = String(viewerOptions.forceLabelSize);
  el.optForceLabelVal.textContent = String(viewerOptions.forceLabelSize);
}

function saveViewerOptions() {
  try {
    localStorage.setItem(OPTIONS_STORAGE_KEY, JSON.stringify(viewerOptions));
  } catch (e) { /* ignore */ }
}

function loadViewerOptions() {
  try {
    const raw = localStorage.getItem(OPTIONS_STORAGE_KEY);
    if (!raw) return;
    const st = JSON.parse(raw);
    if (typeof st.loadArrowSize === "number") viewerOptions.loadArrowSize = st.loadArrowSize;
    if (typeof st.supportGizmoSize === "number") viewerOptions.supportGizmoSize = st.supportGizmoSize;
    if (typeof st.supportLineWidth === "number") viewerOptions.supportLineWidth = st.supportLineWidth;
    if (typeof st.dispContourLineWidth === "number") viewerOptions.dispContourLineWidth = st.dispContourLineWidth;
    if (typeof st.nodeLabelSize === "number") viewerOptions.nodeLabelSize = st.nodeLabelSize;
    if (typeof st.elemLabelSize === "number") viewerOptions.elemLabelSize = st.elemLabelSize;
    if (typeof st.materialLabelSize === "number") viewerOptions.materialLabelSize = st.materialLabelSize;
    if (typeof st.sectionLabelSize === "number") viewerOptions.sectionLabelSize = st.sectionLabelSize;
    if (typeof st.loadLabelSize === "number") viewerOptions.loadLabelSize = st.loadLabelSize;
    if (typeof st.reactionLabelSize === "number") viewerOptions.reactionLabelSize = st.reactionLabelSize;
    if (typeof st.forceLabelSize === "number") viewerOptions.forceLabelSize = st.forceLabelSize;
    clampAllViewerOptions();
  } catch (e) { /* ignore */ }
}

function onOptionsChanged() {
  readOptionsFromUi();
  saveViewerOptions();
  if (currentModel) rebuildScene();
}

function initViewerOptions() {
  loadViewerOptions();
  applyOptionsToUi();
  el.optLoadArrow.addEventListener("input", () => {
    el.optLoadArrowVal.textContent = el.optLoadArrow.value;
    onOptionsChanged();
  });
  el.optSupportGizmo.addEventListener("input", () => {
    el.optSupportGizmoVal.textContent = el.optSupportGizmo.value;
    onOptionsChanged();
  });
  el.optSupportLineWidth.addEventListener("input", onOptionsChanged);
  el.optSupportLineWidth.addEventListener("change", onOptionsChanged);
  el.optDispContourLineWidth.addEventListener("input", onOptionsChanged);
  el.optDispContourLineWidth.addEventListener("change", onOptionsChanged);
  el.optNodeLabel.addEventListener("input", () => {
    el.optNodeLabelVal.textContent = el.optNodeLabel.value;
    onOptionsChanged();
  });
  el.optElemLabel.addEventListener("input", () => {
    el.optElemLabelVal.textContent = el.optElemLabel.value;
    onOptionsChanged();
  });
  el.optMaterialLabel.addEventListener("input", () => {
    el.optMaterialLabelVal.textContent = el.optMaterialLabel.value;
    onOptionsChanged();
  });
  el.optSectionLabel.addEventListener("input", () => {
    el.optSectionLabelVal.textContent = el.optSectionLabel.value;
    onOptionsChanged();
  });
  el.optLoadLabel.addEventListener("input", () => {
    el.optLoadLabelVal.textContent = el.optLoadLabel.value;
    onOptionsChanged();
  });
  el.optReactionLabel.addEventListener("input", () => {
    el.optReactionLabelVal.textContent = el.optReactionLabel.value;
    onOptionsChanged();
  });
  el.optForceLabel.addEventListener("input", () => {
    el.optForceLabelVal.textContent = el.optForceLabel.value;
    onOptionsChanged();
  });
}

function initDraggablePanel(cfg) {
  const panel = cfg.panel;
  const header = cfg.header;
  const collapseBtn = cfg.collapseBtn;

  function savePanelState() {
    try {
      const rect = panel.getBoundingClientRect();
      localStorage.setItem(cfg.storageKey, JSON.stringify({
        left: rect.left,
        top: rect.top,
        collapsed: panel.classList.contains("collapsed"),
        hidden: panel.classList.contains("hidden"),
      }));
    } catch (e) { /* ignore */ }
  }

  function loadPanelState() {
    try {
      const raw = localStorage.getItem(cfg.storageKey);
      if (!raw) {
        if (cfg.defaultHidden) panel.classList.add("hidden");
        return;
      }
      const st = JSON.parse(raw);
      if (st.hidden) panel.classList.add("hidden");
      else panel.classList.remove("hidden");
      if (st.collapsed) {
        panel.classList.add("collapsed");
        collapseBtn.textContent = "+";
      }
      if (typeof st.left === "number" && typeof st.top === "number") {
        panel.style.left = st.left + "px";
        panel.style.top = st.top + "px";
        panel.style.right = "auto";
      }
    } catch (e) {
      if (cfg.defaultHidden) panel.classList.add("hidden");
    }
  }

  function clampPanelPosition() {
    const rect = panel.getBoundingClientRect();
    const margin = 8;
    let left = rect.left;
    let top = rect.top;
    const maxLeft = window.innerWidth - rect.width - margin;
    const maxTop = window.innerHeight - rect.height - margin;
    left = Math.max(margin, Math.min(left, maxLeft));
    top = Math.max(margin, Math.min(top, maxTop));
    panel.style.left = left + "px";
    panel.style.top = top + "px";
    panel.style.right = "auto";
  }

  loadPanelState();

  cfg.toggleBtn.addEventListener("click", () => {
    panel.classList.toggle("hidden");
    savePanelState();
  });

  collapseBtn.addEventListener("click", (ev) => {
    ev.stopPropagation();
    panel.classList.toggle("collapsed");
    collapseBtn.textContent = panel.classList.contains("collapsed") ? "+" : "−";
    savePanelState();
  });

  let drag = null;
  header.addEventListener("mousedown", (ev) => {
    if (ev.target === collapseBtn) return;
    const rect = panel.getBoundingClientRect();
    drag = {
      startX: ev.clientX,
      startY: ev.clientY,
      left: rect.left,
      top: rect.top,
    };
    ev.preventDefault();
  });

  document.addEventListener("mousemove", (ev) => {
    if (!drag) return;
    if (panel.classList.contains("hidden")) return;
    const dx = ev.clientX - drag.startX;
    const dy = ev.clientY - drag.startY;
    panel.style.left = drag.left + dx + "px";
    panel.style.top = drag.top + dy + "px";
    panel.style.right = "auto";
  });

  document.addEventListener("mouseup", () => {
    if (!drag) return;
    drag = null;
    clampPanelPosition();
    savePanelState();
  });

  window.addEventListener("resize", () => {
    if (!panel.classList.contains("hidden")) clampPanelPosition();
  });
}

bootstrap();
