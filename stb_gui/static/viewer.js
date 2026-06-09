import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { LineSegments2 } from "three/addons/lines/LineSegments2.js";
import { LineSegmentsGeometry } from "three/addons/lines/LineSegmentsGeometry.js";
import { LineMaterial } from "three/addons/lines/LineMaterial.js";

const COLORS = {
  background: 0xe1dee4,
  element: 0x333333,
  node: 0x333333,
  supportTrans: 0xBF3434,
  supportRot: 0x618FCD,
  supportAnchor: 0x374151,
  load: 0xd45087,
  reaction: 0x0d9488,
  reactionMoment: 0x9333ea,
  ejnt: 0xff8c00,
  selected: 0xff8c00,
  selectedNode: 0xe85d5d,
  distance: 0x2563eb,
  deform: 0x4E8AC6,
  membraneFill: 0x6b8f71,
  membraneEdge: 0x2f5d3a,
  woodWallFill: 0xc9a86c,
  woodWallEdge: 0x8b6914,
  nodeLabel: 0x000000,
  force: 0x4D829E,
};

const PRES_ZERO = 1e-10;
const FORCE_LABELS = ["", "Nx", "Vy", "Vz", "Mx", "My", "Mz"];
const FORCE_UNITS = ["", "kN", "kN", "kN", "kNm", "kNm", "kNm"];

const ALPHA = {
  labelElem: 1.0,
  labelMaterial: 1.0,
  labelSection: 1.0,
  labelLoad: 1.0,
  labelReactionForce: 1.0,
  labelReactionMoment: 1.0,
  labelDefaultBg: 1.0,
  forceValueBg: 1.0,
  elementGhost: 1.0,
  membraneFill: 0.32,
  membraneEdge: 0.9,
  woodWallFill: 0.35,
  woodWallEdge: 0.9,
  opaque: 1.0,
};

const OPTIONS_STORAGE_KEY = "stb_gui_options";
const MODEL_STORAGE_KEY = "stb_gui_last_model";
const LABEL_BG = {
  elem: "rgba(47, 75, 124, 1.0)",
  material: "rgba(150, 95, 35, " + ALPHA.labelMaterial + ")",
  section: "rgba(45, 95, 175, " + ALPHA.labelSection + ")",
  load: "rgba(20, 83, 45, " + ALPHA.labelLoad + ")",
  reactionForce: "rgba(13, 120, 110, " + ALPHA.labelReactionForce + ")",
  reactionMoment: "rgba(147, 51, 234, " + ALPHA.labelReactionMoment + ")",
};

const OPTIONS_DEFAULTS = {
  loadArrowSize: 1.0,
  inputLoadType: "all",
  supportGizmoSize: 25,
  supportLineWidth: 2,
  dispContourLineWidth: 2.5,
  elementLineWidth: 2.0,
  loadLineWidth: 2.0,
  forceLineWidth: 1.0,
  nodeLabelSize: 1.0,
  elemLabelSize: 1.0,
  materialLabelSize: 1.2,
  sectionLabelSize: 1.0,
  loadLabelSize: 1.0,
  reactionLabelSize: 1.0,
  forceLabelSize: 1.5,
};

const OPTIONS_LIMITS = {
  loadArrowSize: { min: 0.1, max: 5.0 },
  supportGizmoSize: { min: 25, max: 50 },
  supportLineWidth: { min: 0.5, max: 3 },
  dispContourLineWidth: { min: 0.5, max: 3 },
  elementLineWidth: { min: 0.5, max: 3 },
  loadLineWidth: { min: 0.5, max: 3 },
  forceLineWidth: { min: 0.5, max: 3 },
  nodeLabelSize: { min: 0.1, max: 2.0 },
  elemLabelSize: { min: 0.1, max: 2.0 },
  materialLabelSize: { min: 0.1, max: 2.0 },
  sectionLabelSize: { min: 0.1, max: 2.0 },
  loadLabelSize: { min: 0.1, max: 2.0 },
  reactionLabelSize: { min: 0.1, max: 2.0 },
  forceLabelSize: { min: 0.1, max: 2.5 },
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
  btnNew: document.getElementById("btnNew"),
  btnOpen: document.getElementById("btnOpen"),
  btnSave: document.getElementById("btnSave"),
  btnClose: document.getElementById("btnClose"),
  modelPath: document.getElementById("modelPath"),
  openFileInput: document.getElementById("openFileInput"),
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
  dispLegendTicks: document.getElementById("dispLegendTicks"),
  viewerInfoOverlay: document.getElementById("viewerInfoOverlay"),
  dispContourMin: document.getElementById("dispContourMin"),
  dispContourMax: document.getElementById("dispContourMax"),
  btnDispContourAuto: document.getElementById("btnDispContourAuto"),
  chkSupports: document.getElementById("chkSupports"),
  chkEJnt: document.getElementById("chkEJnt"),
  chkLoads: document.getElementById("chkLoads"),
  loadTypeFilter: document.getElementById("loadTypeFilter"),
  chkLoadValues: document.getElementById("chkLoadValues"),
  chkReactions: document.getElementById("chkReactions"),
  chkReactionValues: document.getElementById("chkReactionValues"),
  chkLabels: document.getElementById("chkLabels"),
  chkElemLabels: document.getElementById("chkElemLabels"),
  chkMaterial: document.getElementById("chkMaterial"),
  chkSection: document.getElementById("chkSection"),
  chkMembrane: document.getElementById("chkMembrane"),
  chkWoodWall: document.getElementById("chkWoodWall"),
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
  btnToggleSelect: document.getElementById("btnToggleSelect"),
  btnToggleDistance: document.getElementById("btnToggleDistance"),
  btnToggleSelectionPanel: document.getElementById("btnToggleSelectionPanel"),
  distanceOverlay: document.getElementById("distanceOverlay"),
  selectionMarquee: document.getElementById("selectionMarquee"),
  selectionPanel: document.getElementById("selectionPanel"),
  selectionPanelHeader: document.getElementById("selectionPanelHeader"),
  btnSelectionCollapse: document.getElementById("btnSelectionCollapse"),
  selectionSummary: document.getElementById("selectionSummary"),
  selectionList: document.getElementById("selectionList"),
  btnClearSelection: document.getElementById("btnClearSelection"),
  elemContextMenu: document.getElementById("elemContextMenu"),
  contextMenuTitle: document.getElementById("contextMenuTitle"),
  contextMenuSections: document.getElementById("contextMenuSections"),
  contextMenuMaterials: document.getElementById("contextMenuMaterials"),
  contextMenuDeleteElems: document.getElementById("contextMenuDeleteElems"),
  contextMenuDeleteNodes: document.getElementById("contextMenuDeleteNodes"),
  contextMenuElemEdits: document.getElementById("contextMenuElemEdits"),
  ejntEditPanel: document.getElementById("ejntEditPanel"),
  ejntEditText: document.getElementById("ejntEditText"),
  btnEjntEditApply: document.getElementById("btnEjntEditApply"),
  btnEjntEditCancel: document.getElementById("btnEjntEditCancel"),
  btnEjntEditClose: document.getElementById("btnEjntEditClose"),
  optLoadArrow: document.getElementById("optLoadArrow"),
  optLoadArrowVal: document.getElementById("optLoadArrowVal"),
  optSupportGizmo: document.getElementById("optSupportGizmo"),
  optSupportGizmoVal: document.getElementById("optSupportGizmoVal"),
  optSupportLineWidth: document.getElementById("optSupportLineWidth"),
  optDispContourLineWidth: document.getElementById("optDispContourLineWidth"),
  optElementLineWidth: document.getElementById("optElementLineWidth"),
  optLoadLineWidth: document.getElementById("optLoadLineWidth"),
  optForceLineWidth: document.getElementById("optForceLineWidth"),
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
let modelGroup, labelGroup, forceGroup, forceLabelGroup, axesGroup, selectionGroup, distanceGroup;
let currentModel = null;
let selectionModeActive = false;
let distanceModeActive = false;
let distanceNodeIds = [];
let distanceMeters = null;
let selectedElementIds = new Set();
let selectedNodeIds = new Set();
let selectionDrag = null;
const _worldProj = new THREE.Vector3();
const _ndcScratch = new THREE.Vector3();
const _viewPosScratch = new THREE.Vector3();
const _leaderStart = new THREE.Vector3();
const _leaderEnd = new THREE.Vector3();
const _labelNdc = new THREE.Vector3();
const SELECTION_PICK_PX = 10;
const SELECTION_NODE_PICK_PX = 14;
const SELECTION_DRAG_MIN_PX = 4;
const SELECTION_LIST_LIMIT = 80;
const MAX_EDIT_UNDO = 50;
let editUndoStack = [];
let editRedoStack = [];
let editHistoryBusy = false;
let currentResultsText = null;
let viewerOptions = Object.assign({}, OPTIONS_DEFAULTS);
let wideLineMaterials = new Set();
let dispContourScaleKey = null;
let supportGizmoEntries = [];
let nodeLabelEntries = [];
let _nodeLabelLeaderMat = null;
let currentModelPath = null;
const inputEditors = new Map();
let showWorldAxes = true;
const _supportDiscTexCache = new Map();
let _nodePointTexture = null;

function saveLastModelPath(path) {
  setCurrentModelPath(path);
}

function getCurrentModelPath() {
  return currentModelPath;
}

function setCurrentModelPath(path) {
  currentModelPath = normalizeModelPath(path);
  if (el.modelPath) {
    el.modelPath.textContent = currentModelPath || "";
    el.modelPath.title = currentModelPath || "";
  }
  if (!currentModelPath) return;
  try {
    localStorage.setItem(MODEL_STORAGE_KEY, currentModelPath);
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
    updateViewerInfoOverlay(currentModel);
  } catch (ex) {
    console.error(ex);
    setStatus("Display error: " + ex.message);
  }
}

function getSceneDisplayState() {
  const lc = el.lcSelect.value;
  const defFac = parseFloat(el.defFactor.value) || 0;
  const complete = currentModel && analysisComplete(currentModel);
  const deformed = !!(el.chkDeformed && el.chkDeformed.checked && complete);
  return { lc, defFac, deformed };
}

function applyViewerInteractionControls() {
  if (!controls) return;
  if (selectionModeActive || distanceModeActive) {
    // Left click = pick; right drag = orbit (left is disabled, not enableRotate).
    controls.mouseButtons.LEFT = null;
    controls.mouseButtons.RIGHT = THREE.MOUSE.ROTATE;
    controls.mouseButtons.MIDDLE = THREE.MOUSE.DOLLY;
  } else {
    controls.mouseButtons.LEFT = THREE.MOUSE.ROTATE;
    controls.mouseButtons.RIGHT = THREE.MOUSE.PAN;
    controls.mouseButtons.MIDDLE = THREE.MOUSE.DOLLY;
  }
  controls.enableRotate = true;
}

function setSelectionMode(active) {
  selectionModeActive = !!active;
  if (selectionModeActive) {
    setDistanceMode(false, { skipInteractionUpdate: true });
  }
  if (el.btnToggleSelect) {
    el.btnToggleSelect.classList.toggle("active", selectionModeActive);
  }
  applyViewerInteractionControls();
  if (selectionModeActive && el.selectionPanel) {
    el.selectionPanel.classList.remove("hidden");
  }
}

function clearDistanceMeasurement() {
  distanceNodeIds = [];
  distanceMeters = null;
  updateDistanceVisual();
  updateDistanceOverlay();
}

function setDistanceMode(active, opts) {
  const skipInteractionUpdate = !!(opts && opts.skipInteractionUpdate);
  distanceModeActive = !!active;
  if (distanceModeActive) {
    selectionModeActive = false;
    if (el.btnToggleSelect) el.btnToggleSelect.classList.remove("active");
  }
  if (el.btnToggleDistance) {
    el.btnToggleDistance.classList.toggle("active", distanceModeActive);
  }
  if (!distanceModeActive) {
    clearDistanceMeasurement();
  } else {
    updateDistanceOverlay();
  }
  if (!skipInteractionUpdate) {
    applyViewerInteractionControls();
  }
}

function formatLengthValue(meters) {
  const av = Math.abs(meters);
  if (av < 1e-9) return "0 m";
  if (av < 0.01) return meters.toFixed(4) + " m";
  if (av < 1) return meters.toFixed(3) + " m";
  if (av < 100) return meters.toFixed(2) + " m";
  return meters.toFixed(1) + " m";
}

function nodeWorldPositionById(nodeId) {
  if (!currentModel) return null;
  const nm = nodeMap(currentModel);
  const n = nm[nodeId];
  if (!n) return null;
  const display = getSceneDisplayState();
  return nodePosition(n, currentModel, display.lc, display.defFac, display.deformed);
}

function computeDistanceBetweenNodes(id0, id1) {
  const p0 = nodeWorldPositionById(id0);
  const p1 = nodeWorldPositionById(id1);
  if (!p0 || !p1) return null;
  return p0.distanceTo(p1);
}

function addDistancePick(nodeId) {
  if (distanceNodeIds.length >= 2) {
    distanceNodeIds = [nodeId];
    distanceMeters = null;
  } else {
    distanceNodeIds.push(nodeId);
    if (distanceNodeIds.length === 2) {
      distanceMeters = computeDistanceBetweenNodes(distanceNodeIds[0], distanceNodeIds[1]);
    }
  }
  updateDistanceVisual();
  updateDistanceOverlay();
}

function updateDistanceOverlay() {
  if (!el.distanceOverlay) return;
  if (!distanceModeActive) {
    el.distanceOverlay.hidden = true;
    el.distanceOverlay.textContent = "";
    return;
  }
  el.distanceOverlay.hidden = false;
  if (distanceNodeIds.length === 0) {
    el.distanceOverlay.textContent = "Distance: click 2 nodes (0/2)";
    return;
  }
  if (distanceNodeIds.length === 1) {
    el.distanceOverlay.textContent = "Distance: click 2nd node (1/2) — N" + distanceNodeIds[0];
    return;
  }
  const n0 = distanceNodeIds[0];
  const n1 = distanceNodeIds[1];
  const distText = distanceMeters == null ? "?" : formatLengthValue(distanceMeters);
  el.distanceOverlay.textContent = "Distance: N" + n0 + " → N" + n1 + " = " + distText;
}

function updateDistanceVisual() {
  clearGroup(distanceGroup);
  if (!currentModel || distanceNodeIds.length === 0) return;

  const display = getSceneDisplayState();
  const nm = nodeMap(currentModel);
  const nodePts = [];
  const positions = [];
  for (const id of distanceNodeIds) {
    const n = nm[id];
    if (!n) continue;
    const p = nodePosition(n, currentModel, display.lc, display.defFac, display.deformed);
    nodePts.push(p.x, p.y, p.z);
    positions.push(p);
  }
  if (nodePts.length > 0) {
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.Float32BufferAttribute(nodePts, 3));
    const mat = nodePointsMaterial({
      color: COLORS.distance,
      size: 14,
      sizeAttenuation: false,
      depthTest: true,
    });
    const points = new THREE.Points(geo, mat);
    points.renderOrder = 22;
    distanceGroup.add(points);
  }
  if (positions.length === 2) {
    const p0 = positions[0];
    const p1 = positions[1];
    addWideLineSegmentsFromPts(
      [p0.x, p0.y, p0.z, p1.x, p1.y, p1.z],
      COLORS.distance,
      distanceGroup,
      23,
      elementLineWidthPx() + 2,
      ALPHA.opaque
    );
    const mid = p0.clone().add(p1).multiplyScalar(0.5);
    const span = modelSpan(currentModel);
    const label = makeTextSprite(formatLengthValue(distanceMeters || 0), span, {
      fg: "#1d4ed8",
      bg: "rgba(255, 255, 255, 0.9)",
      pad: 4,
    });
    label.position.copy(mid);
    label.renderOrder = 24;
    distanceGroup.add(label);
  }
}

function hasPickSelection() {
  return selectedElementIds.size > 0 || selectedNodeIds.size > 0;
}

function clearSelection() {
  if (!hasPickSelection()) return;
  selectedElementIds = new Set();
  selectedNodeIds = new Set();
  updateSelectionHighlight();
  updateSelectionPanel();
}

function setSelectedElementIds(ids, mode) {
  const next = mode === "replace" ? new Set() : new Set(selectedElementIds);
  for (const id of ids) {
    if (mode === "toggle") {
      if (next.has(id)) next.delete(id);
      else next.add(id);
    } else {
      next.add(id);
    }
  }
  selectedElementIds = next;
  updateSelectionHighlight();
  updateSelectionPanel();
}

function setSelectedNodeIds(ids, mode) {
  const next = mode === "replace" ? new Set() : new Set(selectedNodeIds);
  for (const id of ids) {
    if (mode === "toggle") {
      if (next.has(id)) next.delete(id);
      else next.add(id);
    } else {
      next.add(id);
    }
  }
  selectedNodeIds = next;
  updateSelectionHighlight();
  updateSelectionPanel();
}

function replacePickSelection(nodeIds, elemIds) {
  setSelectedNodeIds(nodeIds, "replace");
  setSelectedElementIds(elemIds, "replace");
}

function addPickSelection(nodeIds, elemIds) {
  setSelectedNodeIds(nodeIds, "add");
  setSelectedElementIds(elemIds, "add");
}

function viewportMousePoint(ev) {
  const rect = el.viewport.getBoundingClientRect();
  return {
    x: ev.clientX - rect.left,
    y: ev.clientY - rect.top,
  };
}

function worldToScreenPoint(worldVec) {
  _worldProj.copy(worldVec).project(camera);
  const w = el.viewport.clientWidth || 1;
  const h = el.viewport.clientHeight || 1;
  return {
    x: (_worldProj.x * 0.5 + 0.5) * w,
    y: (-_worldProj.y * 0.5 + 0.5) * h,
  };
}

function distPointToSegment2d(px, py, ax, ay, bx, by) {
  const dx = bx - ax;
  const dy = by - ay;
  const lenSq = dx * dx + dy * dy;
  if (lenSq < 1e-12) return Math.hypot(px - ax, py - ay);
  let t = ((px - ax) * dx + (py - ay) * dy) / lenSq;
  t = Math.max(0, Math.min(1, t));
  const qx = ax + t * dx;
  const qy = ay + t * dy;
  return Math.hypot(px - qx, py - qy);
}

function pointInRect(px, py, x0, y0, x1, y1) {
  const minX = Math.min(x0, x1);
  const maxX = Math.max(x0, x1);
  const minY = Math.min(y0, y1);
  const maxY = Math.max(y0, y1);
  return px >= minX && px <= maxX && py >= minY && py <= maxY;
}

function segmentsIntersect2d(ax, ay, bx, by, cx, cy, dx, dy) {
  function orient(px, py, qx, qy, rx, ry) {
    return (qy - py) * (rx - qx) - (qx - px) * (ry - qy);
  }
  function onSeg(px, py, qx, qy, rx, ry) {
    return Math.min(px, qx) <= rx && rx <= Math.max(px, qx) &&
      Math.min(py, qy) <= ry && ry <= Math.max(py, qy);
  }
  const o1 = orient(ax, ay, bx, by, cx, cy);
  const o2 = orient(ax, ay, bx, by, dx, dy);
  const o3 = orient(cx, cy, dx, dy, ax, ay);
  const o4 = orient(cx, cy, dx, dy, bx, by);
  if (o1 * o2 < 0 && o3 * o4 < 0) return true;
  if (Math.abs(o1) < 1e-9 && onSeg(ax, ay, bx, by, cx, cy)) return true;
  if (Math.abs(o2) < 1e-9 && onSeg(ax, ay, bx, by, dx, dy)) return true;
  if (Math.abs(o3) < 1e-9 && onSeg(cx, cy, dx, dy, ax, ay)) return true;
  if (Math.abs(o4) < 1e-9 && onSeg(cx, cy, dx, dy, bx, by)) return true;
  return false;
}

function segmentIntersectsRect(ax, ay, bx, by, x0, y0, x1, y1) {
  if (pointInRect(ax, ay, x0, y0, x1, y1) || pointInRect(bx, by, x0, y0, x1, y1)) {
    return true;
  }
  const minX = Math.min(x0, x1);
  const maxX = Math.max(x0, x1);
  const minY = Math.min(y0, y1);
  const maxY = Math.max(y0, y1);
  const edges = [
    [minX, minY, maxX, minY],
    [maxX, minY, maxX, maxY],
    [maxX, maxY, minX, maxY],
    [minX, maxY, minX, minY],
  ];
  for (const e of edges) {
    if (segmentsIntersect2d(ax, ay, bx, by, e[0], e[1], e[2], e[3])) return true;
  }
  return false;
}

function elementScreenSegment(elem, nm, display) {
  const n0 = nm[elem.n0];
  const n1 = nm[elem.n1];
  if (!n0 || !n1) return null;
  const p0 = nodePosition(n0, currentModel, display.lc, display.defFac, display.deformed);
  const p1 = nodePosition(n1, currentModel, display.lc, display.defFac, display.deformed);
  const s0 = worldToScreenPoint(p0);
  const s1 = worldToScreenPoint(p1);
  return { s0, s1 };
}

function pickElementAtScreen(px, py, thresholdPx) {
  if (!currentModel) return null;
  const display = getSceneDisplayState();
  const nm = nodeMap(currentModel);
  let bestId = null;
  let bestDist = thresholdPx;
  for (const e of currentModel.elements) {
    const seg = elementScreenSegment(e, nm, display);
    if (!seg) continue;
    const d = distPointToSegment2d(px, py, seg.s0.x, seg.s0.y, seg.s1.x, seg.s1.y);
    if (d < bestDist) {
      bestDist = d;
      bestId = e.id;
    }
  }
  return bestId;
}

function elementsInScreenRect(x0, y0, x1, y1) {
  const ids = [];
  if (!currentModel) return ids;
  const display = getSceneDisplayState();
  const nm = nodeMap(currentModel);
  for (const e of currentModel.elements) {
    const seg = elementScreenSegment(e, nm, display);
    if (!seg) continue;
    if (segmentIntersectsRect(seg.s0.x, seg.s0.y, seg.s1.x, seg.s1.y, x0, y0, x1, y1)) {
      ids.push(e.id);
    }
  }
  return ids;
}

function nodesInScreenRect(x0, y0, x1, y1) {
  const ids = [];
  if (!currentModel) return ids;
  const display = getSceneDisplayState();
  const minX = Math.min(x0, x1);
  const maxX = Math.max(x0, x1);
  const minY = Math.min(y0, y1);
  const maxY = Math.max(y0, y1);
  for (const n of currentModel.nodes) {
    const p = nodePosition(n, currentModel, display.lc, display.defFac, display.deformed);
    const s = worldToScreenPoint(p);
    if (s.x >= minX && s.x <= maxX && s.y >= minY && s.y <= maxY) {
      ids.push(n.id);
    }
  }
  return ids;
}

function pickNodeAtScreen(px, py, thresholdPx) {
  if (!currentModel) return null;
  const display = getSceneDisplayState();
  const limit = thresholdPx == null ? SELECTION_NODE_PICK_PX : thresholdPx;
  let bestNode = null;
  let bestNodeDist = limit;
  for (const n of currentModel.nodes) {
    const p = nodePosition(n, currentModel, display.lc, display.defFac, display.deformed);
    const s = worldToScreenPoint(p);
    const d = Math.hypot(px - s.x, py - s.y);
    if (d < bestNodeDist) {
      bestNodeDist = d;
      bestNode = n.id;
    }
  }
  return bestNode;
}

function pickTargetAtScreen(px, py) {
  if (!currentModel) return null;
  const bestNode = pickNodeAtScreen(px, py, SELECTION_NODE_PICK_PX);
  let bestNodeDist = SELECTION_NODE_PICK_PX;
  if (bestNode != null) {
    const display = getSceneDisplayState();
    const nm = nodeMap(currentModel);
    const n = nm[bestNode];
    if (n) {
      const p = nodePosition(n, currentModel, display.lc, display.defFac, display.deformed);
      const s = worldToScreenPoint(p);
      bestNodeDist = Math.hypot(px - s.x, py - s.y);
    }
  }
  const bestElem = pickElementAtScreen(px, py, SELECTION_PICK_PX);
  if (bestNode != null && bestElem == null) return { kind: "node", id: bestNode };
  if (bestElem != null && bestNode == null) return { kind: "elem", id: bestElem };
  if (bestNode != null && bestElem != null) {
    if (bestNodeDist <= SELECTION_PICK_PX) {
      return { kind: "node", id: bestNode };
    }
    return { kind: "elem", id: bestElem };
  }
  return null;
}

function elementIJArrowLength(model, elemLen) {
  const span = modelSpan(model);
  const minLen = Math.max(span * 0.012, 0.04);
  const maxLen = Math.max(span * 0.06, minLen * 2);
  return THREE.MathUtils.clamp(elemLen * 0.42, minLen, Math.min(maxLen, elemLen * 0.85));
}

function addElementIJDirectionArrow(p0, p1, model, group, color, lineWidthPx) {
  const dir = p1.clone().sub(p0);
  const len = dir.length();
  if (len < 1e-12) return;
  dir.normalize();
  const arrowLen = elementIJArrowLength(model, len);
  const mid = p0.clone().add(p1).multiplyScalar(0.5);
  const half = arrowLen * 0.5;
  const tail = mid.clone().addScaledVector(dir, -half);
  const head = mid.clone().addScaledVector(dir, half);
  addDirectedArrow(tail, head, group, color, lineWidthPx, 0.95, 22);
}

function updateSelectionHighlight() {
  clearGroup(selectionGroup);
  if (!currentModel || !hasPickSelection()) return;
  const display = getSceneDisplayState();
  const nm = nodeMap(currentModel);
  const pts = [];
  for (const e of currentModel.elements) {
    if (!selectedElementIds.has(e.id)) continue;
    const n0 = nm[e.n0];
    const n1 = nm[e.n1];
    if (!n0 || !n1) continue;
    const p0 = nodePosition(n0, currentModel, display.lc, display.defFac, display.deformed);
    const p1 = nodePosition(n1, currentModel, display.lc, display.defFac, display.deformed);
    pts.push(p0.x, p0.y, p0.z, p1.x, p1.y, p1.z);
  }
  if (pts.length > 0) {
    addWideLineSegmentsFromPts(
      pts,
      COLORS.selected,
      selectionGroup,
      20,
      elementLineWidthPx() + 2.5,
      ALPHA.opaque
    );
  }
  const arrowWidth = elementLineWidthPx() + 1.5;
  for (const e of currentModel.elements) {
    if (!selectedElementIds.has(e.id)) continue;
    const n0 = nm[e.n0];
    const n1 = nm[e.n1];
    if (!n0 || !n1) continue;
    const p0 = nodePosition(n0, currentModel, display.lc, display.defFac, display.deformed);
    const p1 = nodePosition(n1, currentModel, display.lc, display.defFac, display.deformed);
    addElementIJDirectionArrow(
      p0, p1, currentModel, selectionGroup, COLORS.selected, arrowWidth
    );
  }
  if (selectedNodeIds.size > 0) {
    const nodePts = [];
    for (const n of currentModel.nodes) {
      if (!selectedNodeIds.has(n.id)) continue;
      const p = nodePosition(n, currentModel, display.lc, display.defFac, display.deformed);
      nodePts.push(p.x, p.y, p.z);
    }
    if (nodePts.length > 0) {
      const geo = new THREE.BufferGeometry();
      geo.setAttribute("position", new THREE.Float32BufferAttribute(nodePts, 3));
      const mat = nodePointsMaterial({
        color: COLORS.selectedNode,
        size: 12,
        sizeAttenuation: false,
        depthTest: true,
      });
      const points = new THREE.Points(geo, mat);
      points.renderOrder = 21;
      selectionGroup.add(points);
    }
  }
}

function elementSummaryText(elem) {
  const sec = elem.section || ("SEC " + (elem.section_id != null ? elem.section_id : "?"));
  const mat = elem.material_name || "";
  return mat ? sec + " / " + mat : sec;
}

function formatOutInt(v) {
  const s = String(v);
  return s.length >= 6 ? s : s.padStart(6, " ");
}

function formatOutScientific(val) {
  if (!isFinite(val)) return "         ?";
  if (val === 0 || Math.abs(val) < PRES_ZERO) return " 0.000e+00";
  const neg = val < 0;
  const av = Math.abs(val);
  let exp = Math.floor(Math.log10(av));
  let mant = av / Math.pow(10, exp);
  if (mant >= 10) {
    mant /= 10;
    exp += 1;
  }
  const m = (neg ? -mant : mant).toFixed(3);
  const e = (exp >= 0 ? "+" : "-") + String(Math.abs(exp)).padStart(2, "0");
  return (m + "e" + e).padStart(10, " ");
}

const NDSP_OUT_HEADER = [
  "# --- NODAL DISPLACEMENT ---",
  "#        LC,  NODE,         X,         Y,         Z,   Theta X,   Theta Y,   Theta Z",
  "#                          (m)        (m)        (m)      (rad)      (rad)      (rad)",
];

const EFRC_OUT_HEADER = [
  "# --- ELEMENT FORCE ---",
  "#        LC,  ELEM,        Ni,       Qyi,       Qzi,       Mxi,       Myi,       Mzi         Nj,       Qyj,       Qzj,       Mxj,       Myj,       Mzj,       Myc,       Mzc",
  "#                         (kN)       (kN)       (kN)      (kNm)      (kNm)      (kNm)       (kN)       (kN)       (kN)      (kNm)      (kNm)      (kNm)      (kNm)      (kNm)",
];

function formatNdspOutLine(lc, nodeId, disps) {
  const props = ["NDSP", formatOutInt(lc), formatOutInt(nodeId)];
  for (let i = 0; i < 6; i++) {
    props.push(formatOutScientific(disps[i]));
  }
  return props.join(",");
}

function formatEfrcOutLine(lc, elemId, forces) {
  const props = ["EFRC", formatOutInt(lc), formatOutInt(elemId)];
  for (let i = 0; i < 14; i++) {
    const raw = forces[i] || 0;
    const v = Math.abs(raw) < PRES_ZERO ? 0 : raw;
    props.push(formatOutScientific(v * 1e-3));
  }
  return props.join(",");
}

function nodeNdspOutBlock(model, nodeId, lcKey) {
  const nm = {};
  for (const n of model.nodes || []) nm[n.id] = n;
  const n = nm[nodeId];
  if (!n || !n.disps) return null;
  const disps = n.disps[String(lcKey)];
  if (!disps || disps.length < 6) return null;
  return NDSP_OUT_HEADER.join("\n") + "\n" + formatNdspOutLine(lcKey, nodeId, disps);
}

function elementEfrcOutBlock(model, elemId, lcKey) {
  const byId = {};
  for (const e of model.elements || []) byId[e.id] = e;
  const e = byId[elemId];
  if (!e || !e.forces) return null;
  const forces = e.forces[String(lcKey)];
  if (!forces || forces.length < 14) return null;
  return EFRC_OUT_HEADER.join("\n") + "\n" + formatEfrcOutLine(lcKey, elemId, forces);
}

function updateSelectionPanel() {
  if (!el.selectionSummary || !el.selectionList) return;
  const elemCount = selectedElementIds.size;
  const nodeCount = selectedNodeIds.size;
  if (!hasPickSelection()) {
    el.selectionSummary.textContent = "Nothing picked";
    el.selectionList.innerHTML = "";
    return;
  }
  const parts = [];
  if (elemCount > 0) {
    parts.push(elemCount + " element" + (elemCount === 1 ? "" : "s"));
  }
  if (nodeCount > 0) {
    parts.push(nodeCount + " node" + (nodeCount === 1 ? "" : "s"));
  }
  let summary = parts.join(", ") + " picked";
  if (elemCount > 0 && currentModel) {
    const byId = {};
    for (const e of currentModel.elements) {
      byId[e.id] = e;
    }
    const sectionCounts = {};
    for (const id of selectedElementIds) {
      const e = byId[id];
      if (!e) continue;
      const key = elementSummaryText(e);
      sectionCounts[key] = (sectionCounts[key] || 0) + 1;
    }
    const breakdown = Object.keys(sectionCounts).sort().map(function (k) {
      return sectionCounts[k] + "× " + k;
    });
    if (breakdown.length > 0 && breakdown.length <= 5) {
      summary += " — " + breakdown.join(", ");
    }
  }
  el.selectionSummary.textContent = summary;
  el.selectionList.innerHTML = "";

  const rows = [];
  for (const id of Array.from(selectedNodeIds).sort((a, b) => a - b)) {
    rows.push({ kind: "node", id: id });
  }
  for (const id of Array.from(selectedElementIds).sort((a, b) => a - b)) {
    rows.push({ kind: "elem", id: id });
  }
  const byElem = {};
  for (const e of currentModel ? currentModel.elements : []) {
    byElem[e.id] = e;
  }
  const byNode = {};
  for (const n of currentModel ? currentModel.nodes : []) {
    byNode[n.id] = n;
  }
  const solved = currentModel && analysisComplete(currentModel);
  const lcKey = String(el.lcSelect ? el.lcSelect.value : "");
  const show = rows.slice(0, SELECTION_LIST_LIMIT);
  for (const row of show) {
    const li = document.createElement("li");
    if (row.kind === "node") {
      const n = byNode[row.id];
      const pos = n
        ? " (" + n.x.toFixed(2) + ", " + n.y.toFixed(2) + ", " + n.z.toFixed(2) + ")"
        : "";
      const title = document.createElement("div");
      title.className = "selection-row-title";
      title.textContent = "NODE " + row.id + pos;
      li.appendChild(title);
      if (solved) {
        const outLine = document.createElement("div");
        outLine.className = "selection-out-line";
        const line = nodeNdspOutBlock(currentModel, row.id, lcKey);
        outLine.textContent = line != null
          ? line
          : "(no NDSP for LC " + lcKey + ")";
        li.appendChild(outLine);
      }
      li.addEventListener("click", function () {
        replacePickSelection([row.id], []);
      });
    } else {
      const e = byElem[row.id];
      const title = document.createElement("div");
      title.className = "selection-row-title";
      title.textContent = "ELEM " + row.id + " — " + (e ? elementSummaryText(e) : "?");
      li.appendChild(title);
      if (solved) {
        const outLine = document.createElement("div");
        outLine.className = "selection-out-line";
        const line = elementEfrcOutBlock(currentModel, row.id, lcKey);
        outLine.textContent = line != null
          ? line
          : "(no EFRC for LC " + lcKey + ")";
        li.appendChild(outLine);
      }
      li.addEventListener("click", function () {
        replacePickSelection([], [row.id]);
      });
    }
    el.selectionList.appendChild(li);
  }
  if (rows.length > SELECTION_LIST_LIMIT) {
    const li = document.createElement("li");
    li.className = "selection-more";
    li.textContent = "... and " + (rows.length - SELECTION_LIST_LIMIT) + " more";
    el.selectionList.appendChild(li);
  }
}

function updateSelectionMarquee(x0, y0, x1, y1) {
  if (!el.selectionMarquee) return;
  const left = Math.min(x0, x1);
  const top = Math.min(y0, y1);
  const width = Math.abs(x1 - x0);
  const height = Math.abs(y1 - y0);
  el.selectionMarquee.style.left = left + "px";
  el.selectionMarquee.style.top = top + "px";
  el.selectionMarquee.style.width = width + "px";
  el.selectionMarquee.style.height = height + "px";
  el.selectionMarquee.hidden = width < 1 && height < 1;
}

function hideSelectionMarquee() {
  if (!el.selectionMarquee) return;
  el.selectionMarquee.hidden = true;
  el.selectionMarquee.style.width = "0";
  el.selectionMarquee.style.height = "0";
}

function finishSelectionDrag(ev) {
  if (!selectionDrag) return;
  const drag = selectionDrag;
  selectionDrag = null;
  hideSelectionMarquee();
  if (controls) controls.enabled = true;

  const end = viewportMousePoint(ev);
  const dx = end.x - drag.startX;
  const dy = end.y - drag.startY;
  const extend = !!(ev.ctrlKey || ev.metaKey);

  if (Math.hypot(dx, dy) < SELECTION_DRAG_MIN_PX) {
    const picked = pickTargetAtScreen(end.x, end.y);
    if (picked == null) {
      if (!extend) clearSelection();
    } else if (extend) {
      if (picked.kind === "node") setSelectedNodeIds([picked.id], "toggle");
      else setSelectedElementIds([picked.id], "toggle");
    } else if (picked.kind === "node") {
      replacePickSelection([picked.id], []);
    } else {
      replacePickSelection([], [picked.id]);
    }
    return;
  }

  const elemIds = elementsInScreenRect(drag.startX, drag.startY, end.x, end.y);
  const nodeIds = nodesInScreenRect(drag.startX, drag.startY, end.x, end.y);
  if (elemIds.length === 0 && nodeIds.length === 0) {
    if (!extend) clearSelection();
    return;
  }
  if (extend) addPickSelection(nodeIds, elemIds);
  else replacePickSelection(nodeIds, elemIds);
}

function initSelectionInteraction() {
  if (!el.viewport) return;

  el.viewport.addEventListener("mousedown", (ev) => {
    if (!selectionModeActive) return;
    if (ev.button !== 0) return;
    if (isViewerOverlayTarget(ev.target)) return;
    const pt = viewportMousePoint(ev);
    selectionDrag = {
      startX: pt.x,
      startY: pt.y,
      pointerId: ev.pointerId,
    };
    if (controls) controls.enabled = false;
    updateSelectionMarquee(pt.x, pt.y, pt.x, pt.y);
    ev.preventDefault();
    ev.stopPropagation();
  });

  window.addEventListener("mousemove", (ev) => {
    if (!selectionDrag) return;
    const pt = viewportMousePoint(ev);
    updateSelectionMarquee(selectionDrag.startX, selectionDrag.startY, pt.x, pt.y);
  });

  window.addEventListener("mouseup", (ev) => {
    if (!selectionDrag) return;
    if (ev.button !== 0) return;
    finishSelectionDrag(ev);
  });

  document.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape" && !isViewerTextInputTarget(ev.target)) {
      if (distanceModeActive) clearDistanceMeasurement();
      else clearSelection();
    }
  });
}

function initDistanceInteraction() {
  if (!el.viewport) return;

  el.viewport.addEventListener("mousedown", (ev) => {
    if (!distanceModeActive) return;
    if (ev.button !== 0) return;
    if (isViewerOverlayTarget(ev.target)) return;
    const pt = viewportMousePoint(ev);
    const nodeId = pickNodeAtScreen(pt.x, pt.y, SELECTION_NODE_PICK_PX);
    if (nodeId == null) return;
    addDistancePick(nodeId);
    ev.preventDefault();
    ev.stopPropagation();
  });
}

function isViewerOverlayTarget(target) {
  if (!target || !el.viewport) return false;
  if (target === el.viewport || target === renderer.domElement) return false;
  return el.viewport.contains(target);
}

function selectedElementIdList() {
  return Array.from(selectedElementIds).sort(function (a, b) { return a - b; });
}

function selectedNodeIdList() {
  return Array.from(selectedNodeIds).sort(function (a, b) { return a - b; });
}

function hideEjntEditor() {
  if (el.ejntEditPanel) el.ejntEditPanel.hidden = true;
  if (el.ejntEditText) el.ejntEditText.value = "";
}

async function fetchEjntLines(path, elementIds) {
  const ids = elementIds.join(",");
  const url = "/api/model/ejnt-lines?path=" + encodeURIComponent(path)
    + "&element_ids=" + encodeURIComponent(ids);
  const res = await fetch(url);
  if (!res.ok) {
    const err = await res.json().catch(function () { return {}; });
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

async function openEjntEditor() {
  const path = getCurrentModelPath();
  if (!path) return;
  if (selectedElementIds.size === 0) {
    setStatus("Pick one or more elements first");
    return;
  }
  const elemIds = selectedElementIdList();
  hideContextMenu();
  setStatus("Loading EJNT lines…");
  try {
    const data = await fetchEjntLines(path, elemIds);
    const header = data.header || "";
    const lines = (data.lines || []).map(function (row) { return row.line; }).join("\n");
    if (el.ejntEditText) el.ejntEditText.value = header + lines;
    if (el.ejntEditPanel) el.ejntEditPanel.hidden = false;
    if (el.ejntEditText) el.ejntEditText.focus();
    setStatus(path + " — edit EJNT for element(s) " + elemIds.join(", "));
  } catch (ex) {
    setStatus("Error: " + ex.message);
    window.alert("Failed to load EJNT lines: " + ex.message);
  }
}

function applyEjntEditor() {
  if (!el.ejntEditText) return;
  applyModelEdit({
    action: "set_ejnt_lines",
    lines_text: el.ejntEditText.value,
  });
  hideEjntEditor();
}

function hideContextMenu() {
  if (el.elemContextMenu) el.elemContextMenu.hidden = true;
}

function populateContextMenuCatalog() {
  if (!el.contextMenuSections || !el.contextMenuMaterials || !currentModel) return;
  el.contextMenuSections.innerHTML = "";
  el.contextMenuMaterials.innerHTML = "";

  const sections = currentModel.sections || [];
  for (const s of sections) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "context-menu-item";
    const mat = s.material_name || ("MAT " + s.material_id);
    btn.textContent = "SECT " + s.id + " — " + s.name + " (" + mat + ")";
    btn.addEventListener("click", function () {
      hideContextMenu();
      applyModelEdit({ action: "set_section", section_id: s.id });
    });
    el.contextMenuSections.appendChild(btn);
  }

  const materials = currentModel.materials || [];
  for (const m of materials) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "context-menu-item";
    btn.textContent = "MATE " + m.id + " — " + m.name;
    btn.addEventListener("click", function () {
      hideContextMenu();
      const ok = window.confirm(
        "Change material to MATE " + m.id + " (" + m.name + ")?\n" +
        "All elements sharing the same section will be affected."
      );
      if (!ok) return;
      applyModelEdit({ action: "set_material", material_id: m.id });
    });
    el.contextMenuMaterials.appendChild(btn);
  }
}

function showContextMenu(clientX, clientY) {
  if (!el.elemContextMenu || !hasPickSelection()) return;
  if (selectedElementIds.size > 0) populateContextMenuCatalog();
  const elemCount = selectedElementIds.size;
  const nodeCount = selectedNodeIds.size;
  if (el.contextMenuDeleteElems) {
    el.contextMenuDeleteElems.hidden = elemCount === 0;
  }
  if (el.contextMenuDeleteNodes) {
    el.contextMenuDeleteNodes.hidden = nodeCount === 0;
  }
  if (el.contextMenuElemEdits) {
    el.contextMenuElemEdits.hidden = elemCount === 0;
  }
  if (el.contextMenuTitle) {
    const titleParts = [];
    if (elemCount > 0) {
      titleParts.push(elemCount + " element" + (elemCount === 1 ? "" : "s"));
    }
    if (nodeCount > 0) {
      titleParts.push(nodeCount + " node" + (nodeCount === 1 ? "" : "s"));
    }
    el.contextMenuTitle.textContent = titleParts.join(", ") + " picked";
  }
  el.elemContextMenu.hidden = false;
  const margin = 8;
  const rect = el.elemContextMenu.getBoundingClientRect();
  let left = clientX;
  let top = clientY;
  if (left + rect.width > window.innerWidth - margin) {
    left = window.innerWidth - rect.width - margin;
  }
  if (top + rect.height > window.innerHeight - margin) {
    top = window.innerHeight - rect.height - margin;
  }
  el.elemContextMenu.style.left = Math.max(margin, left) + "px";
  el.elemContextMenu.style.top = Math.max(margin, top) + "px";
}

function resetEditHistory() {
  editUndoStack = [];
  editRedoStack = [];
}

function pushEditUndoSnapshot(path, text) {
  if (!path || text == null) return;
  editUndoStack.push({ path: path, text: text });
  if (editUndoStack.length > MAX_EDIT_UNDO) {
    editUndoStack.shift();
  }
  editRedoStack = [];
}

function pruneSelectionToModel() {
  if (!currentModel) return;
  const validElems = new Set(currentModel.elements.map(function (e) { return e.id; }));
  const validNodes = new Set(currentModel.nodes.map(function (n) { return n.id; }));
  selectedElementIds = new Set(
    Array.from(selectedElementIds).filter(function (id) { return validElems.has(id); })
  );
  selectedNodeIds = new Set(
    Array.from(selectedNodeIds).filter(function (id) { return validNodes.has(id); })
  );
  updateSelectionHighlight();
  updateSelectionPanel();
}

async function restoreEditHistoryEntry(snapshot, redoTarget) {
  const path = getCurrentModelPath();
  if (!snapshot || snapshot.path !== path) {
    setStatus("Undo/redo history does not match the current model");
    return false;
  }
  if (editHistoryBusy) return false;
  editHistoryBusy = true;
  hideContextMenu();
  try {
    const current = await fetchInputText(path);
    redoTarget.push({ path: path, text: current });
    await saveInputText(path, snapshot.text);
    await loadSelectedModel(false, { keepSelection: true });
    pruneSelectionToModel();
    return true;
  } catch (ex) {
    redoTarget.pop();
    setStatus("Undo/redo error: " + ex.message);
    window.alert("Undo/redo failed: " + ex.message);
    return false;
  } finally {
    editHistoryBusy = false;
  }
}

async function undoModelEdit() {
  if (editUndoStack.length === 0) {
    setStatus("Nothing to undo");
    return;
  }
  const snap = editUndoStack.pop();
  const ok = await restoreEditHistoryEntry(snap, editRedoStack);
  if (ok) {
    setStatus((getCurrentModelPath() || "") + " — undo (Ctrl+Z)");
  } else if (snap) {
    editUndoStack.push(snap);
  }
}

async function redoModelEdit() {
  if (editRedoStack.length === 0) {
    setStatus("Nothing to redo");
    return;
  }
  const snap = editRedoStack.pop();
  const ok = await restoreEditHistoryEntry(snap, editUndoStack);
  if (ok) {
    setStatus((getCurrentModelPath() || "") + " — redo (Ctrl+Y)");
  } else if (snap) {
    editRedoStack.push(snap);
  }
}

function initEditHistoryShortcuts() {
  document.addEventListener("keydown", function (ev) {
    if (isViewerTextInputTarget(ev.target)) return;
    const mod = ev.ctrlKey || ev.metaKey;
    if (!mod) return;
    const key = ev.key;
    if (key === "z" || key === "Z") {
      if (ev.shiftKey) return;
      ev.preventDefault();
      undoModelEdit();
      return;
    }
    if (key === "y" || key === "Y") {
      ev.preventDefault();
      redoModelEdit();
    }
  });
}

async function applyModelEdit(extra) {
  const path = getCurrentModelPath();
  if (!path) return;
  let payload;
  if (extra.action === "delete_nodes") {
    if (selectedNodeIds.size === 0) return;
    payload = {
      action: "delete_nodes",
      node_ids: selectedNodeIdList(),
    };
  } else {
    if (selectedElementIds.size === 0) return;
    payload = Object.assign({ element_ids: selectedElementIdList() }, extra);
  }
  hideContextMenu();
  setStatus("Applying edit…");
  let undoPushed = false;
  try {
    const beforeText = await fetchInputText(path);
    pushEditUndoSnapshot(path, beforeText);
    undoPushed = true;
    const url = "/api/model/edit?path=" + encodeURIComponent(path);
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(function () { return {}; });
      throw new Error(err.detail || res.statusText);
    }
    const body = await res.json();
    const destructive = payload.action === "delete" || payload.action === "delete_nodes";
    const prevElems = new Set(selectedElementIds);
    const prevNodes = new Set(selectedNodeIds);
    await loadSelectedModel(false, { keepSelection: !destructive });
    if (!destructive) {
      selectedElementIds = prevElems;
      selectedNodeIds = prevNodes;
      pruneSelectionToModel();
    }
    let msg = path + " — edit saved";
    if (body.warnings && body.warnings.length) {
      msg += " (" + body.warnings[0] + ")";
    }
    setStatus(msg);
  } catch (ex) {
    if (undoPushed) editUndoStack.pop();
    setStatus("Edit error: " + ex.message);
    window.alert("Edit failed: " + ex.message);
  }
}

function initContextMenu() {
  if (!el.elemContextMenu || !renderer) return;

  renderer.domElement.addEventListener("mousedown", function (ev) {
    if (!selectionModeActive || ev.button !== 2 || !hasPickSelection()) return;
    ev.stopPropagation();
  }, true);

  renderer.domElement.addEventListener("contextmenu", function (ev) {
    if (!selectionModeActive || !hasPickSelection()) return;
    ev.preventDefault();
    ev.stopPropagation();
    showContextMenu(ev.clientX, ev.clientY);
  });

  el.elemContextMenu.addEventListener("click", function (ev) {
    const btn = ev.target.closest("[data-action]");
    if (!btn) return;
    const action = btn.getAttribute("data-action");
    if (action === "delete") {
      const count = selectedElementIds.size;
      const ok = window.confirm("Delete " + count + " element" + (count === 1 ? "" : "s") + "?");
      if (!ok) return;
      applyModelEdit({ action: "delete" });
      return;
    }
    if (action === "delete-nodes") {
      const count = selectedNodeIds.size;
      const ok = window.confirm(
        "Delete " + count + " node" + (count === 1 ? "" : "s") +
        " and all elements connected to them?"
      );
      if (!ok) return;
      applyModelEdit({ action: "delete_nodes" });
      return;
    }
    if (action === "ejnt-edit") {
      openEjntEditor();
      return;
    }
  });

  if (el.btnEjntEditApply) {
    el.btnEjntEditApply.addEventListener("click", () => applyEjntEditor());
  }
  if (el.btnEjntEditCancel) {
    el.btnEjntEditCancel.addEventListener("click", () => hideEjntEditor());
  }
  if (el.btnEjntEditClose) {
    el.btnEjntEditClose.addEventListener("click", () => hideEjntEditor());
  }

  document.addEventListener("mousedown", function (ev) {
    if (!el.elemContextMenu || el.elemContextMenu.hidden) return;
    if (el.elemContextMenu.contains(ev.target)) return;
    hideContextMenu();
  });

  document.addEventListener("keydown", function (ev) {
    if (ev.key === "Escape") {
      if (el.ejntEditPanel && !el.ejntEditPanel.hidden) {
        hideEjntEditor();
        ev.stopPropagation();
        return;
      }
      hideContextMenu();
    }
  });
}

function refreshDisplayStatus(model) {
  const path = model.path || getCurrentModelPath() || "";
  const lcKey = String(el.lcSelect.value);
  let extra = analysisComplete(model) ? " (solved)" : "";
  if (analysisComplete(model) && !modelHasForceData(model, lcKey)) {
    extra += " — force data unavailable (restart stb gui)";
  }
  if ((el.chkReactions.checked || el.chkReactionValues.checked) &&
      !modelHasReactionData(model, lcKey)) {
    extra += " — no reaction data for LC " + lcKey;
  }
  setStatus(path + extra + " — " + model.nodes.length + " nodes, " + model.elements.length + " elements");
}

function boolOnOff(v) {
  return v ? "ON" : "OFF";
}

function selectedForceLabel() {
  const id = parseInt(el.forceSelect.value, 10) || 0;
  if (id <= 0 || id >= FORCE_LABELS.length) return "None";
  return FORCE_LABELS[id];
}

function updateViewerInfoOverlay(model) {
  if (!el.viewerInfoOverlay) return;
  if (!model) {
    el.viewerInfoOverlay.textContent = "No model loaded.";
    return;
  }

  const path = normalizeModelPath(model.path || getCurrentModelPath() || "");
  const fileName = path ? path.replace(/^.*\//, "") : "(none)";
  const lc = String(el.lcSelect.value || "");
  const solved = analysisComplete(model);
  const defFac = parseFloat(el.defFactor.value) || 0;
  const forceComp = selectedForceLabel();

  const pointLoads = model.point_loads ? model.point_loads.length : 0;
  const elemLoads = model.element_loads ? model.element_loads.length : 0;
  const supports = model.supports ? model.supports.length : 0;

  const displayLines = [];
  if (el.chkDeformed.checked) displayLines.push("deformed shape x" + defFac.toFixed(1));
  if (el.chkDispContour && el.chkDispContour.checked) displayLines.push("disp contour");
  if (el.chkLoads.checked) {
    displayLines.push("input loads (" + loadTypeFilterValue() + ")");
    if (el.chkLoadValues.checked) displayLines.push("load values");
  }
  if (el.chkReactions && el.chkReactions.checked) displayLines.push("reactions");
  if (el.chkReactionValues && el.chkReactionValues.checked) displayLines.push("reaction values");
  if (!el.chkSupports || el.chkSupports.checked) displayLines.push("supports");
  if (el.chkEJnt && el.chkEJnt.checked) displayLines.push("EJNT markers");
  if (el.chkLabels && el.chkLabels.checked) displayLines.push("node IDs");
  if (el.chkElemLabels && el.chkElemLabels.checked) displayLines.push("element IDs");
  if (el.chkMaterial && el.chkMaterial.checked) displayLines.push("material labels");
  if (el.chkSection && el.chkSection.checked) displayLines.push("section labels");
  if (el.chkMembrane && el.chkMembrane.checked) {
    const nmem = model.membrane_elements ? model.membrane_elements.length : 0;
    displayLines.push("DMEM (" + nmem + ")");
  }
  if (el.chkWoodWall && el.chkWoodWall.checked) {
    const nwrw = model.wood_rated_walls ? model.wood_rated_walls.length : 0;
    displayLines.push("WRW (" + nwrw + ")");
  }
  if (forceComp !== "None") {
    displayLines.push(
      "force diagram: " + forceComp +
      " (div " + (el.frcDiv ? el.frcDiv.value : "-") +
      ", x" + (el.frcFactor ? el.frcFactor.value : "-") + ")"
    );
    if (el.chkForceValues && el.chkForceValues.checked) displayLines.push("force values");
  }

  const lines = [
    "[File]",
    "file: " + fileName,
    "path: " + (path || "(none)"),
    "solved: " + boolOnOff(solved),
    "analysis date: " + (model.date_analysis || "-"),
    "LC: " + lc,
    "nodes: " + (model.nodes ? model.nodes.length : 0),
    "elements: " + (model.elements ? model.elements.length : 0),
    "DMEM: " + (model.membrane_elements ? model.membrane_elements.length : 0),
    "WRW: " + (model.wood_rated_walls ? model.wood_rated_walls.length : 0),
    "supports: " + supports,
    "point loads: " + pointLoads,
    "element loads: " + elemLoads,
  ];

  if (displayLines.length > 0) {
    lines.push(
      "",
      "[Display]",
      ...displayLines
    );
  }

  lines.push(
    "",
    "[Options]",
    "load arrow scale: " + Number(viewerOptions.loadArrowSize).toFixed(1),
    "load label scale: " + Number(viewerOptions.loadLabelSize).toFixed(0),
    "reaction label scale: " + Number(viewerOptions.reactionLabelSize).toFixed(0),
  );

  el.viewerInfoOverlay.textContent = lines.join("\n");
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
  controls.dampingFactor = 0.2;
  controls.target.set(0, 0, 0);

  const amb = new THREE.AmbientLight(0xffffff, 0.65);
  scene.add(amb);
  const dir = new THREE.DirectionalLight(0xffffff, 0.55);
  dir.position.set(5, 10, 7);
  scene.add(dir);

  modelGroup = new THREE.Group();
  scene.add(modelGroup);
  selectionGroup = new THREE.Group();
  scene.add(selectionGroup);
  distanceGroup = new THREE.Group();
  scene.add(distanceGroup);
  labelGroup = new THREE.Group();
  scene.add(labelGroup);
  forceGroup = new THREE.Group();
  scene.add(forceGroup);
  forceLabelGroup = new THREE.Group();
  scene.add(forceLabelGroup);
  axesGroup = new THREE.Group();
  scene.add(axesGroup);

  window.addEventListener("resize", onResize);
  applyViewerInteractionControls();
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
  updateSupportGizmoPositions();
  updateNodeLabelPositions();
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
  const ux = d[0];
  const uy = d[1];
  const uz = d[2];
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
    if (!best || mag > best.mag) {
      const p0 = nodePosition(n, model, lc, defFac, false);
      const p1 = nodePosition(n, model, lc, defFac, true);
      best = { node: n, mag: mag, p0: p0, p1: p1 };
    }
  }
  if (!best) return null;
  return best;
}

function nodeDispVector(n, lc, defFac) {
  if (!n.disps || !n.disps[String(lc)]) return new THREE.Vector3(0, 0, 0);
  const d = n.disps[String(lc)];
  return new THREE.Vector3(d[0], d[1], d[2]);
}

function globalVecToLocal(v, elem) {
  if (!elem || !elem.vx || !elem.vy || !elem.vz) return v.clone();
  const vx = new THREE.Vector3().fromArray(elem.vx);
  const vy = new THREE.Vector3().fromArray(elem.vy);
  const vz = new THREE.Vector3().fromArray(elem.vz);
  return new THREE.Vector3(v.dot(vx), v.dot(vy), v.dot(vz));
}

function beamDispLocalAtT(dl, L, t) {
  const u1 = dl[0], v1 = dl[1], w1 = dl[2];
  let ry1 = dl[4], rz1 = dl[5];
  const u2 = dl[6], v2 = dl[7], w2 = dl[8];
  let ry2 = dl[10], rz2 = dl[11];

  const N1 = 1 - t;
  const N2 = t;
  const H1 = 1 - 3 * t * t + 2 * t * t * t;
  const H2 = L * (t - 2 * t * t + t * t * t);
  const H3 = 3 * t * t - 2 * t * t * t;
  const H4 = L * (-t * t + t * t * t);

  const u = N1 * u1 + N2 * u2;
  const v = H1 * v1 + H2 * rz1 + H3 * v2 + H4 * rz2;
  const w = H1 * w1 - H2 * ry1 + H3 * w2 - H4 * ry2;
  return new THREE.Vector3(u, v, w);
}

function applyJointEffectiveEndRotations(dl, e, lcKey) {
  if (!e || !isFinite(e.len) || e.len <= 1e-12) return dl;
  const keys = ["lyi", "lyj", "lzi", "lzj", "PHIy", "PHIz"];
  for (const k of keys) {
    if (!isFinite(e[k])) return dl;
  }

  const L = e.len;
  const lyi = e.lyi;
  const lyj = e.lyj;
  const lzi = e.lzi;
  const lzj = e.lzj;
  const PHIy = e.PHIy;
  const PHIz = e.PHIz;
  const rlyi = 1 - lyi;
  const rlyj = 1 - lyj;
  const rlzi = 1 - lzi;
  const rlzj = 1 - lzj;

  const denV = 2 + (2 + PHIy) * lzi + (2 + PHIy) * lzj + 4 * PHIy * lzi * lzj;
  const denW = 2 + (2 + PHIz) * lyi + (2 + PHIz) * lyj + 4 * PHIz * lyi * lyj;
  if (Math.abs(denV) < 1e-12 || Math.abs(denW) < 1e-12) return dl;

  const Av = (1 + PHIy) / denV;
  const Aw = (1 + PHIz) / denW;
  const v1 = dl[1], rz1 = dl[5], v2 = dl[7], rz2 = dl[11];
  const w1 = dl[2], ry1 = dl[4], w2 = dl[8], ry2 = dl[10];

  const rz1Eff = Av * (
    (-2 * rlzi * (1 + 2 * lzj) / L) * v1 +
    ((4 + PHIy + (2 + 5 * PHIy) * lzj) * lzi) * rz1 +
    (2 * rlzi * (1 + 2 * lzj) / L) * v2 +
    (-(2 - PHIy) * rlzi * lzj) * rz2
  );
  const rz2Eff = Av * (
    (-2 * rlzj * (1 + 2 * lzi) / L) * v1 +
    (-(2 - PHIy) * rlzj * lzi) * rz1 +
    (2 * rlzj * (1 + 2 * lzi) / L) * v2 +
    ((4 + PHIy + (2 + 5 * PHIy) * lzi) * lzj) * rz2
  );

  const ry1Eff = Aw * (
    (2 * rlyi * (1 + 2 * lyj) / L) * w1 +
    ((4 + PHIz + (2 + 5 * PHIz) * lyj) * lyi) * ry1 +
    (-2 * rlyi * (1 + 2 * lyj) / L) * w2 +
    (-(2 - PHIz) * rlyi * lyj) * ry2
  );
  const ry2Eff = Aw * (
    (2 * rlyj * (1 + 2 * lyi) / L) * w1 +
    (-(2 - PHIz) * rlyj * lyi) * ry1 +
    (-2 * rlyj * (1 + 2 * lyi) / L) * w2 +
    ((4 + PHIz + (2 + 5 * PHIz) * lyi) * lyj) * ry2
  );

  const out = dl.slice();
  out[4] = ry1Eff;
  out[5] = rz1Eff;
  out[10] = ry2Eff;
  out[11] = rz2Eff;

  // If end moments are effectively zero at both ends, the member should
  // deform linearly in that bending plane (no curvature from end moments).
  const fs = e && e.forces && e.forces[lcKey];
  if (fs && fs.length >= 13) {
    const MOM_TOL = 1e-6;
    const v1 = dl[1], v2 = dl[7];
    const w1 = dl[2], w2 = dl[8];
    if (Math.abs(fs[5]) <= MOM_TOL && Math.abs(fs[12]) <= MOM_TOL) {
      const rzLin = (v2 - v1) / L;
      out[5] = rzLin;
      out[11] = rzLin;
    }
    if (Math.abs(fs[4]) <= MOM_TOL && Math.abs(fs[11]) <= MOM_TOL) {
      const ryLin = -(w2 - w1) / L;
      out[4] = ryLin;
      out[10] = ryLin;
    }
  }
  return out;
}

function elemDeformedPoints(e, n0, n1, model, lc, defFac, nDiv) {
  const lcKey = String(lc);
  const p0u = nodePosition(n0, model, lc, defFac, false);
  const p1u = nodePosition(n1, model, lc, defFac, false);

  const hasShape =
    e.vx && e.vy && e.vz && e.len && e.len > 1e-12 &&
    n0.disps && n1.disps && n0.disps[lcKey] && n1.disps[lcKey];

  if (!hasShape) {
    const p0d = nodePosition(n0, model, lc, defFac, true);
    const p1d = nodePosition(n1, model, lc, defFac, true);
    return {
      pts: [p0d, p1d],
      mags: [nodeDispMagnitude(n0, lc, defFac), nodeDispMagnitude(n1, lc, defFac)],
    };
  }

  const d0g = n0.disps[lcKey];
  const d1g = n1.disps[lcKey];
  const t0l = globalVecToLocal(new THREE.Vector3(d0g[0], d0g[1], d0g[2]), e);
  const r0l = globalVecToLocal(new THREE.Vector3(d0g[3], d0g[4], d0g[5]), e);
  const t1l = globalVecToLocal(new THREE.Vector3(d1g[0], d1g[1], d1g[2]), e);
  const r1l = globalVecToLocal(new THREE.Vector3(d1g[3], d1g[4], d1g[5]), e);
  const dl = [
    t0l.x, t0l.y, t0l.z, r0l.x, r0l.y, r0l.z,
    t1l.x, t1l.y, t1l.z, r1l.x, r1l.y, r1l.z,
  ];
  const dlEff = applyJointEffectiveEndRotations(dl, e, lcKey);

  const pts = [];
  const mags = [];
  for (let i = 0; i <= nDiv; i++) {
    const t = i / nDiv;
    const pl = beamDispLocalAtT(dlEff, e.len, t);
    const pg = localVecToGlobal(pl, e);
    const pBase = elemPointAlong(p0u, p1u, t);
    pts.push(pBase.clone().addScaledVector(pg, defFac));
    mags.push(pg.length());
  }
  return { pts: pts, mags: mags };
}

function maxDispPointInfo(model, lc, defFac, nm) {
  let best = maxDispNodeInfo(model, lc, defFac);
  const nDiv = 20;
  for (const e of model.elements || []) {
    const n0 = nm[e.n0];
    const n1 = nm[e.n1];
    if (!n0 || !n1 || !n0.disps || !n1.disps) continue;
    if (!n0.disps[String(lc)] || !n1.disps[String(lc)]) continue;
    if (!e.vx || !e.vy || !e.vz || !e.len || e.len <= 1e-12) continue;

    const d0g = n0.disps[String(lc)];
    const d1g = n1.disps[String(lc)];
    const t0 = new THREE.Vector3(d0g[0], d0g[1], d0g[2]);
    const r0 = new THREE.Vector3(d0g[3], d0g[4], d0g[5]);
    const t1 = new THREE.Vector3(d1g[0], d1g[1], d1g[2]);
    const r1 = new THREE.Vector3(d1g[3], d1g[4], d1g[5]);

    const t0l = globalVecToLocal(t0, e);
    const r0l = globalVecToLocal(r0, e);
    const t1l = globalVecToLocal(t1, e);
    const r1l = globalVecToLocal(r1, e);
    const dl = [
      t0l.x, t0l.y, t0l.z, r0l.x, r0l.y, r0l.z,
      t1l.x, t1l.y, t1l.z, r1l.x, r1l.y, r1l.z,
    ];
    const dlEff = applyJointEffectiveEndRotations(dl, e, String(lc));

    const p0u = nodePosition(n0, model, lc, defFac, false);
    const p1u = nodePosition(n1, model, lc, defFac, false);

    for (let i = 1; i < nDiv; i++) {
      const t = i / nDiv;
      const pl = beamDispLocalAtT(dlEff, e.len, t);
      const pg = localVecToGlobal(pl, e);
      const mag = pg.length();
      if (!best || mag > best.mag) {
        const pBase = elemPointAlong(p0u, p1u, t);
        best = { mag: mag, p0: pBase, p1: pBase.clone().addScaledVector(pg, defFac), elem: e, t: t };
      }
    }
  }
  return best;
}

function dispContourColor(t) {
  const c = new THREE.Color();
  const u = Math.min(1, Math.max(0, t));
  c.setHSL((1 - u) * 0.66, 1.0, 0.5);
  return c;
}

const DISP_CONTOUR_TICK_FRACTIONS = [0.25, 0.5, 0.75];

function formatDispInputValue(meters) {
  const mm = meters * 1e3;
  const av = Math.abs(mm);
  if (av < 1e-6) return "0";
  if (av < 0.01) return mm.toFixed(3);
  if (av < 1) return mm.toFixed(2);
  if (av < 100) return mm.toFixed(1);
  return mm.toFixed(0);
}

function formatDispTickValueMm(meters) {
  const mm = meters * 1e3;
  const av = Math.abs(mm);
  if (av < 1e-6) return "0";
  if (av < 1) return mm.toFixed(2);
  if (av < 100) return mm.toFixed(1);
  return mm.toFixed(0);
}

function formatDispAbsValue(v) {
  const mm = v * 1e3;
  if (Math.abs(mm) < 1e-6) return "0.0 mm";
  return mm.toFixed(1) + " mm";
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
  let minMm = parseFloat(el.dispContourMin && el.dispContourMin.value);
  let maxMm = parseFloat(el.dispContourMax && el.dispContourMax.value);
  if (!isFinite(minMm)) minMm = 0;
  if (!isFinite(maxMm)) maxMm = minMm + 1e-12;
  if (maxMm < minMm) {
    const swap = maxMm;
    maxMm = minMm;
    minMm = swap;
  }
  if (maxMm - minMm < 1e-12) maxMm = minMm + 1e-12;
  return { min: minMm / 1e3, max: maxMm / 1e3 };
}

function updateDispContourTicks(rangeMeters) {
  if (!el.dispLegendTicks) return;
  el.dispLegendTicks.replaceChildren();
  if (!rangeMeters) return;
  const span = rangeMeters.max - rangeMeters.min;
  for (const frac of DISP_CONTOUR_TICK_FRACTIONS) {
    const valueM = rangeMeters.min + frac * span;
    const tick = document.createElement("div");
    tick.className = "viewport-disp-legend-tick";
    tick.style.bottom = (frac * 100) + "%";

    const label = document.createElement("span");
    label.className = "viewport-disp-legend-tick-label";
    label.textContent = formatDispTickValueMm(valueM);

    const line = document.createElement("span");
    line.className = "viewport-disp-legend-tick-line";
    line.setAttribute("aria-hidden", "true");

    tick.append(label, line);
    el.dispLegendTicks.append(tick);
  }
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
    updateDispContourTicks(null);
    return;
  }

  if (syncInputs) syncDispContourInputs(autoRange, lc, defFac, false);

  el.dispLegendOverlay.hidden = false;
  el.dispLegendOverlay.classList.add("visible");
  if (el.dispLegendTitle) {
    el.dispLegendTitle.textContent = "|u| (mm, ×" + defFac + ")";
  }
  if (el.dispLegendLc) {
    el.dispLegendLc.textContent = "LC " + lc;
  }
  if (el.dispLegendBar) {
    el.dispLegendBar.style.background = dispContourGradientCss();
  }
  updateDispContourTicks(getDispContourDisplayRange());
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
  const nm = nodeMap(model);
  const info = maxDispPointInfo(model, lc, defFac, nm);
  if (!info || info.mag < 1e-12 || !info.p0 || !info.p1) return;

  const p0 = info.p0.clone();
  const p1 = info.p1.clone();
  const dir = p1.clone().sub(p0);
  const dlen = dir.length();
  if (dlen < 1e-12) return;
  const udir = dir.clone().multiplyScalar(1 / dlen);

  const r = Math.max(span * 0.01, 0.02) * 0.4;
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

  const labelPos = p1.clone().addScaledVector(udir, span * 0.012);
  addReactionValueLabel(
    formatDispAbsValue(info.mag),
    labelPos,
    span,
    Math.max(reactionLabelScaleFactor(), 0.03) * 0.4,
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
  supportGizmoEntries = [];
  nodeLabelEntries = [];

  enrichModelReactions(model);

  const lc = el.lcSelect.value;
  const lcKey = String(lc);
  const defFac = parseFloat(el.defFactor.value) || 0;
  const complete = analysisComplete(model);
  const deformed = el.chkDeformed.checked && complete;
  const showDispContour = el.chkDispContour && el.chkDispContour.checked && complete;
  const showSupports = !el.chkSupports || el.chkSupports.checked;
  const showEJnt = !!(el.chkEJnt && el.chkEJnt.checked);
  const showLoads = el.chkLoads.checked;
  const showLoadValues = el.chkLoadValues.checked;
  const showReactionValues = el.chkReactionValues && el.chkReactionValues.checked && complete;
  const showLabels = el.chkLabels.checked;
  const showElemLabels = el.chkElemLabels.checked;
  const showMaterial = el.chkMaterial.checked;
  const showSection = el.chkSection.checked;
  const showMembrane = !!(el.chkMembrane && el.chkMembrane.checked);
  const showWoodWall = !!(el.chkWoodWall && el.chkWoodWall.checked);
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

  const defDiv = 16;
  for (const e of model.elements) {
    const n0 = nm[e.n0];
    const n1 = nm[e.n1];
    if (!n0 || !n1) continue;
    const p0u = nodePosition(n0, model, lc, defFac, false);
    const p1u = nodePosition(n1, model, lc, defFac, false);
    linePts.push(p0u.x, p0u.y, p0u.z, p1u.x, p1u.y, p1u.z);

    const needCurve = (deformed && !showDispContour) || (showDispContour && deformed && dispDisplayRange);
    const curve = needCurve ? elemDeformedPoints(e, n0, n1, model, lc, defFac, defDiv) : null;

    if (showDispContour && dispDisplayRange) {
      if (deformed && curve) {
        for (let i = 0; i < curve.pts.length - 1; i++) {
          const a = curve.pts[i];
          const b = curve.pts[i + 1];
          contourPts.push(a.x, a.y, a.z, b.x, b.y, b.z);
          const ca = dispContourColor(dispContourT(curve.mags[i], dispDisplayRange));
          const cb = dispContourColor(dispContourT(curve.mags[i + 1], dispDisplayRange));
          contourColors.push(ca.r, ca.g, ca.b, cb.r, cb.g, cb.b);
        }
      } else {
        contourPts.push(p0u.x, p0u.y, p0u.z, p1u.x, p1u.y, p1u.z);
        const m0 = nodeDispMagnitude(n0, lc, defFac);
        const m1 = nodeDispMagnitude(n1, lc, defFac);
        const c0 = dispContourColor(dispContourT(m0, dispDisplayRange));
        const c1 = dispContourColor(dispContourT(m1, dispDisplayRange));
        contourColors.push(c0.r, c0.g, c0.b, c1.r, c1.g, c1.b);
      }
    }

    if (deformed && !showDispContour && curve) {
      for (let i = 0; i < curve.pts.length - 1; i++) {
        const a = curve.pts[i];
        const b = curve.pts[i + 1];
        linePtsDef.push(a.x, a.y, a.z, b.x, b.y, b.z);
      }
    }
  }

  if (linePts.length > 0) {
    addWideLineSegmentsFromPts(
      linePts,
      COLORS.element,
      modelGroup,
      2,
      elementLineWidthPx(),
      (deformed || showDispContour) ? ALPHA.elementGhost : ALPHA.opaque
    );
  }

  if (showDispContour && contourPts.length > 0) {
    addDispContourLineSegments(contourPts, contourColors, modelGroup);
  } else if (deformed && linePtsDef.length > 0) {
    addWideLineSegmentsFromPts(
      linePtsDef,
      COLORS.deform,
      modelGroup,
      3,
      elementLineWidthPx(),
      ALPHA.opaque
    );
  }

  const nodePts = [];
  for (const n of model.nodes) {
    const p = nodePosition(n, model, lc, defFac, deformed);
    nodePts.push(p.x, p.y, p.z);
  }
  if (nodePts.length > 0) {
    const ngeo = new THREE.BufferGeometry();
    ngeo.setAttribute("position", new THREE.Float32BufferAttribute(nodePts, 3));
    const nmat = nodePointsMaterial({
      color: COLORS.node,
      size: nodeMarkerSize(model),
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
      const sp = addSupportDisc(
        supportGizmoCenter(p, model, supSize, camera, renderer),
        s.fixed, supSize, modelGroup
      );
      supportGizmoEntries.push({ nodePos: p, gizmoRadius: supSize, sprite: sp });
    }
  }
  if (showEJnt) {
    drawEJntMarkers(model, {
      lc,
      defFac,
      deformed,
      nm,
      group: modelGroup,
    });
  }

  if (showMembrane) {
    drawMembraneElements(model, {
      lc,
      defFac,
      deformed,
      nm,
      group: modelGroup,
    });
  }

  if (showWoodWall) {
    drawWoodRatedWalls(model, {
      lc,
      defFac,
      deformed,
      nm,
      group: modelGroup,
    });
  }

  if (showLoads) {
    const arrowBase = loadArrowLength(model);
    const maxPMag = maxPointLoadMag(model, lc);
    const maxWMag = maxElementLoadMag(model, lc);

    if (model.point_loads && shouldDrawPointLoad()) {
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
              loadValueLabelPoint(p, tip, span, loadLabelScale),
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
      });
      sprite.renderOrder = 16;
      const lineGeo = new THREE.BufferGeometry();
      lineGeo.setAttribute("position", new THREE.Float32BufferAttribute(6, 3));
      const line = new THREE.Line(lineGeo, nodeLabelLeaderMaterial());
      line.frustumCulled = false;
      line.renderOrder = 15;
      const entry = {
        nodePos: p.clone(),
        span: span,
        scaleFactor: nodeLabelScale,
        sprite: sprite,
        line: line,
      };
      updateNodeLabelEntry(entry, model, camera, renderer);
      labelGroup.add(sprite);
      labelGroup.add(line);
      nodeLabelEntries.push(entry);
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
      addElemLabel(String(e.id), p, span, elemLabelScale, labelGroup, LABEL_BG.elem, false);
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
  updateViewerInfoOverlay(model);
  updateSelectionHighlight();
  updateDistanceVisual();
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

function nodeMarkerSize(model) {
  return Math.max(0.04, (model.bounds ? (model.bounds[1] - model.bounds[0]) * 0.012 : 0.05));
}

function createNodePointTexture() {
  if (_nodePointTexture) return _nodePointTexture;
  const px = 64;
  const canvas = document.createElement("canvas");
  canvas.width = px;
  canvas.height = px;
  const ctx = canvas.getContext("2d");
  ctx.beginPath();
  ctx.arc(px / 2, px / 2, px / 2 - 0.5, 0, Math.PI * 2);
  ctx.fillStyle = "#ffffff";
  ctx.fill();
  _nodePointTexture = new THREE.CanvasTexture(canvas);
  _nodePointTexture.needsUpdate = true;
  return _nodePointTexture;
}

function nodePointsMaterial(opts) {
  return new THREE.PointsMaterial({
    color: opts.color,
    size: opts.size,
    sizeAttenuation: opts.sizeAttenuation !== false,
    map: createNodePointTexture(),
    transparent: true,
    alphaTest: 0.05,
    depthTest: opts.depthTest !== false,
  });
}

function supportGizmoSize(model) {
  const span = modelSpan(model);
  const base = Math.max(span * 0.022, 0.07);
  const pct = parseFloat(viewerOptions.supportGizmoSize);
  if (!isFinite(pct) || pct < 1) return base;
  return base * (pct / 100);
}

function billboardPixelSize(worldPos, worldDiameter, camera, renderer) {
  _viewPosScratch.copy(worldPos).applyMatrix4(camera.matrixWorldInverse);
  const dist = Math.max(-_viewPosScratch.z, 1e-6);
  const height = renderer.domElement.clientHeight;
  const scale = height * camera.projectionMatrix.elements[5] * 0.5 * renderer.getPixelRatio();
  return worldDiameter * (scale / dist);
}

// PointsMaterial map circle: visible diameter is ~half of billboardPixelSize estimate.
const NODE_POINT_RENDER_DIAMETER_SCALE = 0.5;
const SUPPORT_GIZMO_VISUAL_RADIUS_FACTOR =
  (160 / 2 - 6) / (160 / 2);

function nodeMarkerPixelRadius(worldPos, model, camera, renderer) {
  const diameterPx = billboardPixelSize(worldPos, nodeMarkerSize(model), camera, renderer);
  return diameterPx * NODE_POINT_RENDER_DIAMETER_SCALE * 0.5;
}

function supportGizmoPixelRadius(worldPos, gizmoRadius, camera, renderer) {
  const diameterPx = billboardPixelSize(worldPos, gizmoRadius * 2, camera, renderer);
  return diameterPx * 0.5 * SUPPORT_GIZMO_VISUAL_RADIUS_FACTOR;
}

function supportGizmoCenter(nodePos, model, gizmoRadius, camera, renderer, target) {
  const out = target || new THREE.Vector3();
  const nodeSize = nodeMarkerSize(model);
  if (!camera || !renderer || renderer.domElement.clientHeight < 1) {
    return out.copy(nodePos).add(new THREE.Vector3(0, 0, -(nodeSize * 0.5 + gizmoRadius)));
  }

  const offsetPx = nodeMarkerPixelRadius(nodePos, model, camera, renderer)
    + supportGizmoPixelRadius(nodePos, gizmoRadius, camera, renderer);

  _ndcScratch.copy(nodePos).project(camera);
  const height = renderer.domElement.clientHeight;
  _ndcScratch.y -= (offsetPx / height) * 2;
  return out.copy(_ndcScratch).unproject(camera);
}

function nodeLabelLeaderMaterial() {
  if (!_nodeLabelLeaderMat) {
    _nodeLabelLeaderMat = new THREE.LineBasicMaterial({
      color: COLORS.nodeLabel,
      transparent: true,
      opacity: 0.38,
      depthTest: false,
    });
  }
  return _nodeLabelLeaderMat;
}

function computeNodeLabelPlacement(nodePos, model, camera, renderer) {
  const width = renderer.domElement.clientWidth;
  const height = renderer.domElement.clientHeight;
  if (width < 1 || height < 1) {
    return {
      labelPos: nodePos.clone().add(new THREE.Vector3(0, nodeMarkerSize(model) * 0.8, 0)),
      leaderStart: nodePos.clone(),
    };
  }

  const nodeRadiusPx = nodeMarkerPixelRadius(nodePos, model, camera, renderer);
  const screenDx = 20;
  const screenDy = 24;
  const dirLen = Math.hypot(screenDx, screenDy) || 1;
  const sx = screenDx / dirLen;
  const sy = screenDy / dirLen;

  _ndcScratch.copy(nodePos).project(camera);

  const edgePx = nodeRadiusPx + 2;
  _labelNdc.set(
    _ndcScratch.x + (sx * edgePx / width) * 2,
    _ndcScratch.y + (sy * edgePx / height) * 2,
    _ndcScratch.z
  );
  _leaderStart.copy(_labelNdc).unproject(camera);

  const labelPx = nodeRadiusPx + 18;
  _labelNdc.set(
    _ndcScratch.x + (sx * labelPx / width) * 2,
    _ndcScratch.y + (sy * labelPx / height) * 2,
    _ndcScratch.z
  );
  _leaderEnd.copy(_labelNdc).unproject(camera);

  return { labelPos: _leaderEnd.clone(), leaderStart: _leaderStart.clone() };
}

function updateNodeLabelEntry(entry, model, camera, renderer) {
  const placement = computeNodeLabelPlacement(entry.nodePos, model, camera, renderer);
  entry.sprite.position.copy(placement.labelPos);
  const pos = entry.line.geometry.attributes.position;
  pos.setXYZ(0, placement.leaderStart.x, placement.leaderStart.y, placement.leaderStart.z);
  pos.setXYZ(1, placement.labelPos.x, placement.labelPos.y, placement.labelPos.z);
  pos.needsUpdate = true;
  entry.line.geometry.computeBoundingSphere();
}

function updateNodeLabelPositions() {
  if (!camera || !renderer || !currentModel || nodeLabelEntries.length === 0) return;
  for (const entry of nodeLabelEntries) {
    updateNodeLabelEntry(entry, currentModel, camera, renderer);
  }
}

function updateSupportGizmoPositions() {
  if (!camera || !renderer || !currentModel || supportGizmoEntries.length === 0) return;
  for (const entry of supportGizmoEntries) {
    supportGizmoCenter(
      entry.nodePos, currentModel, entry.gizmoRadius, camera, renderer, entry.sprite.position
    );
  }
}

function ejntMarkerRadius(model) {
  const span = modelSpan(model);
  const supHalf = supportGizmoSize(model);
  return Math.max(supHalf * 0.3, span * 0.004, 0.012);
}

function ejntByElementId(model) {
  const map = Object.create(null);
  for (const j of model.element_joints || []) {
    if (j && j.elem_id != null) map[j.elem_id] = j;
  }
  return map;
}

function ejntEndHasRelease(j, end) {
  if (!j) return false;
  if (end === "i") return j.ryi != null || j.rzi != null;
  return j.ryj != null || j.rzj != null;
}

function drawEJntMarkers(model, opts) {
  const { lc, defFac, deformed, nm, group } = opts;
  const r = ejntMarkerRadius(model);
  const supportHalf = supportGizmoSize(model);
  const geo = new THREE.SphereGeometry(r, 16, 12);
  const mat = new THREE.MeshBasicMaterial({ color: COLORS.ejnt, depthTest: true });
  const ejntMap = ejntByElementId(model);

  for (const e of model.elements || []) {
    if (!e) continue;
    const j = ejntMap[e.id];
    const showI = ejntEndHasRelease(j, "i");
    const showJ = ejntEndHasRelease(j, "j");
    if (!showI && !showJ) continue;
    const n0 = nm[e.n0];
    const n1 = nm[e.n1];
    if (!n0 || !n1) continue;
    const p0 = nodePosition(n0, model, lc, defFac, deformed);
    const p1 = nodePosition(n1, model, lc, defFac, deformed);
    const len = p0.distanceTo(p1);
    if (len < 1e-12) continue;

    const offset = supportHalf + r;
    let t0 = offset / len;
    let t1 = 1 - offset / len;
    if (!(t0 < t1)) {
      t0 = 0.35;
      t1 = 0.65;
    }

    if (showI) {
      const m0 = new THREE.Mesh(geo, mat);
      m0.position.copy(elemPointAlong(p0, p1, t0));
      m0.renderOrder = 9;
      group.add(m0);
    }
    if (showJ) {
      const m1 = new THREE.Mesh(geo, mat);
      m1.position.copy(elemPointAlong(p0, p1, t1));
      m1.renderOrder = 9;
      group.add(m1);
    }
  }
}

function drawWoodRatedWalls(model, opts) {
  const { lc, defFac, deformed, nm, group } = opts;
  const items = model.wood_rated_walls || [];
  if (!items.length) return;

  const fillPos = [];
  const edgePts = [];

  for (const wall of items) {
    const ids = wall.nodes;
    if (!ids || ids.length !== 4) continue;
    const n0 = nm[ids[0]];
    const n1 = nm[ids[1]];
    const n2 = nm[ids[2]];
    const n3 = nm[ids[3]];
    if (!n0 || !n1 || !n2 || !n3) continue;
    const p0 = nodePosition(n0, model, lc, defFac, deformed);
    const p1 = nodePosition(n1, model, lc, defFac, deformed);
    const p2 = nodePosition(n2, model, lc, defFac, deformed);
    const p3 = nodePosition(n3, model, lc, defFac, deformed);
    fillPos.push(
      p0.x, p0.y, p0.z,
      p1.x, p1.y, p1.z,
      p2.x, p2.y, p2.z,
      p0.x, p0.y, p0.z,
      p2.x, p2.y, p2.z,
      p3.x, p3.y, p3.z
    );
    edgePts.push(
      p0.x, p0.y, p0.z, p1.x, p1.y, p1.z,
      p1.x, p1.y, p1.z, p2.x, p2.y, p2.z,
      p2.x, p2.y, p2.z, p3.x, p3.y, p3.z,
      p3.x, p3.y, p3.z, p0.x, p0.y, p0.z
    );
  }

  if (fillPos.length === 0) return;

  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.Float32BufferAttribute(fillPos, 3));
  geo.computeVertexNormals();
  const mat = new THREE.MeshBasicMaterial({
    color: COLORS.woodWallFill,
    transparent: true,
    opacity: ALPHA.woodWallFill,
    side: THREE.DoubleSide,
    depthWrite: false,
  });
  const mesh = new THREE.Mesh(geo, mat);
  mesh.renderOrder = 3;
  group.add(mesh);

  addWideLineSegmentsFromPts(
    edgePts,
    COLORS.woodWallEdge,
    group,
    4,
    Math.max(elementLineWidthPx() * 0.9, 0.5),
    ALPHA.woodWallEdge
  );
}

function drawMembraneElements(model, opts) {
  const { lc, defFac, deformed, nm, group } = opts;
  const items = model.membrane_elements || [];
  if (!items.length) return;

  const fillPos = [];
  const edgePts = [];

  for (const mem of items) {
    const ids = mem.nodes;
    if (!ids || ids.length !== 3) continue;
    const n0 = nm[ids[0]];
    const n1 = nm[ids[1]];
    const n2 = nm[ids[2]];
    if (!n0 || !n1 || !n2) continue;
    const p0 = nodePosition(n0, model, lc, defFac, deformed);
    const p1 = nodePosition(n1, model, lc, defFac, deformed);
    const p2 = nodePosition(n2, model, lc, defFac, deformed);
    fillPos.push(
      p0.x, p0.y, p0.z,
      p1.x, p1.y, p1.z,
      p2.x, p2.y, p2.z
    );
    edgePts.push(
      p0.x, p0.y, p0.z, p1.x, p1.y, p1.z,
      p1.x, p1.y, p1.z, p2.x, p2.y, p2.z,
      p2.x, p2.y, p2.z, p0.x, p0.y, p0.z
    );
  }

  if (fillPos.length === 0) return;

  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.Float32BufferAttribute(fillPos, 3));
  geo.computeVertexNormals();
  const mat = new THREE.MeshBasicMaterial({
    color: COLORS.membraneFill,
    transparent: true,
    opacity: ALPHA.membraneFill,
    side: THREE.DoubleSide,
    depthWrite: false,
  });
  const mesh = new THREE.Mesh(geo, mat);
  mesh.renderOrder = 4;
  group.add(mesh);

  addWideLineSegmentsFromPts(
    edgePts,
    COLORS.membraneEdge,
    group,
    5,
    Math.max(elementLineWidthPx() * 0.85, 0.5),
    ALPHA.membraneEdge
  );
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

function clampLineWidthPx(v, fallback, maxVal) {
  const n = parseFloat(v);
  if (!isFinite(n) || n < 0.5) return fallback;
  return Math.min(n, maxVal != null ? maxVal : OPTIONS_LIMITS.supportLineWidth.max);
}

function supportLineWidthPx() {
  return clampLineWidthPx(viewerOptions.supportLineWidth, 2, OPTIONS_LIMITS.supportLineWidth.max);
}

function dispContourLineWidthPx() {
  return clampLineWidthPx(viewerOptions.dispContourLineWidth, 2.5, OPTIONS_LIMITS.dispContourLineWidth.max);
}

function elementLineWidthPx() {
  return clampLineWidthPx(viewerOptions.elementLineWidth, 1.5, OPTIONS_LIMITS.elementLineWidth.max);
}

function loadLineWidthPx() {
  return clampLineWidthPx(viewerOptions.loadLineWidth, 1.5, OPTIONS_LIMITS.loadLineWidth.max);
}

function forceLineWidthPx() {
  return clampLineWidthPx(viewerOptions.forceLineWidth, 1.5, OPTIONS_LIMITS.forceLineWidth.max);
}

function addWideLineSegmentsFromPts(pts, color, group, renderOrder, lineWidthPx, opacity) {
  if (pts.length < 6) return;
  const geo = new LineSegmentsGeometry();
  geo.setPositions(pts);
  const mat = new LineMaterial({
    color: color,
    linewidth: lineWidthPx,
    worldUnits: false,
    transparent: opacity != null && opacity < ALPHA.opaque,
    opacity: opacity != null ? opacity : ALPHA.opaque,
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

function fillSupportSector(ctx, cx, cy, r, startAngle, endAngle, fillColor) {
  ctx.save();
  ctx.beginPath();
  ctx.moveTo(cx, cy);
  ctx.arc(cx, cy, r, startAngle, endAngle);
  ctx.closePath();
  ctx.fillStyle = fillColor;
  ctx.fill();
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
  const outline = "#000000";

  ctx.clearRect(0, 0, px, px);

  for (let i = 0; i < 6; i++) {
    const a0 = -Math.PI / 2 + i * (Math.PI / 3);
    const a1 = a0 + Math.PI / 3;
    if (fixed[i]) {
      fillSupportSector(ctx, cx, cy, r, a0, a1, colorHex(sectorColors[i]));
    }
  }

  ctx.strokeStyle = outline;
  ctx.globalAlpha = ALPHA.opaque;
  ctx.lineWidth = 10.0;
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
  return sp;
}

function loadArrowLength(model) {
  const span = modelSpan(model);
  const pct = parseFloat(viewerOptions.loadArrowSize);
  if (!isFinite(pct) || pct <= 0) return span * 0.01;
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

const LOAD_DIV_NUM = 8;

function isGravityLoad(ld) {
  return !!(ld && (ld.gravity === true || ld.gravity === 1));
}

function isAreaLoad(ld) {
  return !!(ld && (ld.area_load === true || ld.area_load === 1));
}

function formatLoadDistributedValue(mag, isGravity, isArea, displayValue) {
  if (displayValue) return displayValue;
  if (Math.abs(mag) < 1e-6) return "";
  const text = formatReactionValue(mag);
  if (isGravity) return text + "G";
  if (isArea) return text + "A";
  return text;
}

function distributedLoadAxes(elem, isGlobal) {
  if (isGlobal) {
    return [
      new THREE.Vector3(1, 0, 0),
      new THREE.Vector3(0, 1, 0),
      new THREE.Vector3(0, 0, 1),
    ];
  }
  if (!elem || !elem.vx || !elem.vy || !elem.vz) return null;
  return [
    new THREE.Vector3().fromArray(elem.vx),
    new THREE.Vector3().fromArray(elem.vy),
    new THREE.Vector3().fromArray(elem.vz),
  ];
}

function labelWorldHeight(span, scaleFactor, fallback) {
  return span * (scaleFactor != null ? scaleFactor : (fallback != null ? fallback : 0.03));
}

function labelOffsetDistance(span, scaleFactor, fallback) {
  return labelWorldHeight(span, scaleFactor, fallback) * 0.5 * 1.2;
}

function loadValueOffsetDistance(span, scaleFactor) {
  // Requested rule: move by text-height * 1.2 from the shaft end.
  return labelWorldHeight(span, scaleFactor, 0.03) * 1.2;
}

function loadValueLabelPoint(tail, tip, span, scaleFactor) {
  const axis = new THREE.Vector3().subVectors(tip, tail);
  if (axis.lengthSq() < 1e-18) return tail.clone();
  axis.normalize();
  const pad = loadValueOffsetDistance(span, scaleFactor);
  return tail.clone().addScaledVector(axis, -pad);
}

function loadTypeFilterValue() {
  const t = viewerOptions.inputLoadType;
  if (t === "area" || t === "gravity" || t === "linepoint") return t;
  return "all";
}

function shouldDrawPointLoad() {
  const t = loadTypeFilterValue();
  return t === "all" || t === "linepoint";
}

function shouldDrawElementLoad(ld) {
  const t = loadTypeFilterValue();
  if (t === "all") return true;
  if (t === "area") return isAreaLoad(ld);
  if (t === "gravity") return isGravityLoad(ld);
  if (t === "linepoint") return !isAreaLoad(ld) && !isGravityLoad(ld);
  return true;
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
    if (!shouldDrawElementLoad(ld)) continue;
    const e = em[ld.elem];
    if (!e) continue;
    const n0 = nm[e.n0];
    const n1 = nm[e.n1];
    if (!n0 || !n1) continue;

    const w = ld.w;
    if (elementLoadMagnitude(w) < 1e-9) continue;

    const p0 = nodePosition(n0, model, lc, defFac, deformed);
    const p1 = nodePosition(n1, model, lc, defFac, deformed);
    drawTrapezoidalDistributedLoad(ld, e, p0, p1, {
      arrowBase,
      maxWMag,
      span,
      loadLabelScale,
      showValues,
    });
  }
}

function drawTrapezoidalDistributedLoad(ld, e, p0, p1, opts) {
  const { arrowBase, maxWMag, span, loadLabelScale, showValues } = opts;
  const w = ld.w;
  const axes = distributedLoadAxes(e, ld.global);
  if (!axes) {
    drawSingleDistributedLoadArrow(ld, e, p0, p1, opts);
    return;
  }

  const along = new THREE.Vector3().subVectors(p1, p0);
  const elemLen = along.length();
  if (elemLen < 1e-9) return;
  along.normalize();

  const loadColor = COLORS.load;
  const hasProfile = Array.isArray(ld.w_profile) && ld.w_profile.length >= 2;

  for (let axisIdx = 0; axisIdx < 3; axisIdx++) {
    const w0 = hasProfile ? ld.w_profile[0][axisIdx + 1] : w[axisIdx];
    const w1 = hasProfile ? ld.w_profile[ld.w_profile.length - 1][axisIdx + 1] : w[axisIdx + 3];
    if (hasProfile) {
      let maxAbs = 0;
      for (let i = 0; i < ld.w_profile.length; i++) {
        maxAbs = Math.max(maxAbs, Math.abs(ld.w_profile[i][axisIdx + 1]));
      }
      if (maxAbs < PRES_ZERO) continue;
    } else {
      if (Math.abs(w0) < PRES_ZERO && Math.abs(w1) < PRES_ZERO) continue;
    }

    const axis = axes[axisIdx];
    const isParallel = Math.abs(axis.dot(along)) > 0.999;
    const outlineOffsets = [];

    for (let j = 0; j <= LOAD_DIV_NUM; j++) {
      const t = j / LOAD_DIV_NUM;
      const pt = elemPointAlong(p0, p1, t);
      const wAt = hasProfile ? profileAxisValue(ld.w_profile, axisIdx, t) : (w0 + t * (w1 - w0));
      if (Math.abs(wAt) < PRES_ZERO) continue;

      const vOff = distributedLoadOffset(axis, wAt, arrowBase, maxWMag);

      if (isParallel) {
        if (j === LOAD_DIV_NUM) continue;
        const tip = pt.clone().add(vOff);
        addDirectedArrow(pt, tip, modelGroup, loadColor, loadLineWidthPx());
      } else {
        const ept = pt.clone().sub(vOff);
        outlineOffsets.push(ept);
        addDirectedArrow(ept, pt, modelGroup, loadColor, loadLineWidthPx());
      }
    }

    if (!isParallel && outlineOffsets.length >= 2) {
      const outlinePts = [];
      for (let i = 0; i < outlineOffsets.length - 1; i++) {
        addLinePair(outlineOffsets[i], outlineOffsets[i + 1], outlinePts);
      }
      addWideLineSegmentsFromPts(outlinePts, loadColor, modelGroup, 4, loadLineWidthPx(), 1.0);
      if (!isAreaLoad(ld)) {
        addDirectedArrow(outlineOffsets[0], p0, modelGroup, loadColor, loadLineWidthPx());
        addDirectedArrow(
          outlineOffsets[outlineOffsets.length - 1],
          p1,
          modelGroup,
          loadColor,
          loadLineWidthPx()
        );
      } else {
        const endPts = [];
        addLinePair(outlineOffsets[0], p0, endPts);
        addLinePair(outlineOffsets[outlineOffsets.length - 1], p1, endPts);
        addWideLineSegmentsFromPts(endPts, loadColor, modelGroup, 4, loadLineWidthPx(), 1.0);
      }
    }
  }

  if (showValues) {
    const t = 0.5;
    const pt = elemPointAlong(p0, p1, t);
    const wGlob = hasProfile ? profileLoadVector(ld.w_profile, e, t, ld.global) : elementLoadVector(w, t, e, ld.global);
    if (wGlob.lengthSq() > 1e-18) {
      const mag = wGlob.length();
      const dir = wGlob.clone().normalize();
      const labelText = formatLoadDistributedValue(
        mag,
        isGravityLoad(ld),
        isAreaLoad(ld),
        ld.display_value
      );
      if (labelText) {
        const seg = distributedArrowSegmentAt(ld, axes, p0, p1, t, hasProfile, w, arrowBase, maxWMag);
        const tail = seg ? seg.tail : pt.clone();
        const tip = seg ? seg.tip : pt.clone().addScaledVector(dir, scaledReactionArrowLength(arrowBase, mag, maxWMag));
        addLoadValueLabel(
          labelText,
          loadValueLabelPoint(tail, tip, span, loadLabelScale),
          span,
          loadLabelScale,
          labelGroup
        );
      }
    }
    drawDistributedEndLabels(ld, e, p0, p1, opts);
  }
}

function drawSingleDistributedLoadArrow(ld, e, p0, p1, opts) {
  const { arrowBase, maxWMag, span, loadLabelScale, showValues } = opts;
  const w = ld.w;
  const t = 0.5;
  const pt = elemPointAlong(p0, p1, t);
  const wGlob = elementLoadVector(w, t, e, ld.global);
  if (wGlob.lengthSq() < 1e-18) return;
  const mag = wGlob.length();
  const dir = wGlob.clone().normalize();
  const len = scaledReactionArrowLength(arrowBase, mag, maxWMag);
  const tip = addLoadArrow(pt, dir, len, modelGroup);
  if (showValues && tip) {
    const labelText = formatLoadDistributedValue(
      mag,
      isGravityLoad(ld),
      isAreaLoad(ld),
      ld.display_value
    );
    if (labelText) {
      addLoadValueLabel(
        labelText,
        loadValueLabelPoint(pt, tip, span, loadLabelScale),
        span,
        loadLabelScale,
        labelGroup
      );
    }
  }
}

function drawDistributedEndLabels(ld, e, p0, p1, opts) {
  const { arrowBase, maxWMag, span, loadLabelScale } = opts;
  const hasProfile = Array.isArray(ld.w_profile) && ld.w_profile.length >= 2;
  const w = ld.w;
  const axes = distributedLoadAxes(e, ld.global);
  let bestAxis = 0;
  let bestMag = 0;
  for (let i = 0; i < 3; i++) {
    let m = 0;
    if (hasProfile) {
      for (let k = 0; k < ld.w_profile.length; k++) {
        m = Math.max(m, Math.abs(ld.w_profile[k][i + 1]));
      }
    } else {
      const wi = w[i];
      const wj = w[i + 3];
      m = Math.max(Math.abs(wi), Math.abs(wj));
    }
    if (m > bestMag) {
      bestMag = m;
      bestAxis = i;
    }
  }
  if (bestMag < 1e-9) return;

  const ends = [
    { t: 0, val: hasProfile ? ld.w_profile[0][bestAxis + 1] : w[bestAxis] },
    { t: 1, val: hasProfile ? ld.w_profile[ld.w_profile.length - 1][bestAxis + 1] : w[bestAxis + 3] },
  ];
  for (const end of ends) {
    const pt = elemPointAlong(p0, p1, end.t);
    const wGlob = hasProfile ? profileLoadVector(ld.w_profile, e, end.t, ld.global) : elementLoadVector(w, end.t, e, ld.global);
    if (wGlob.lengthSq() < 1e-18) continue;
    const seg = distributedArrowSegmentAt(ld, axes, p0, p1, end.t, hasProfile, w, arrowBase, maxWMag);
    const dir = wGlob.clone().normalize();
    const tail = seg ? seg.tail : pt.clone();
    const tip = seg ? seg.tip : pt.clone().addScaledVector(dir, scaledReactionArrowLength(arrowBase, Math.abs(end.val), maxWMag));
    const text = formatReactionValue(end.val);
    addLoadValueLabel(
      text,
      loadValueLabelPoint(tail, tip, span, loadLabelScale),
      span,
      loadLabelScale,
      labelGroup
    );
  }
}

function distributedLoadOffset(axis, wAt, arrowBase, maxWMag) {
  const len = scaledReactionArrowLength(arrowBase, Math.abs(wAt), maxWMag);
  const sgn = wAt >= 0 ? 1 : -1;
  return axis.clone().multiplyScalar(len * sgn);
}

function distributedArrowSegmentAt(ld, axes, p0, p1, t, hasProfile, w, arrowBase, maxWMag) {
  if (!axes) return null;
  const axisIdx = dominantAxisAtT(ld, t, hasProfile, w);
  const axis = axes[axisIdx];
  if (!axis) return null;
  const pt = elemPointAlong(p0, p1, t);
  const wAt = hasProfile ? profileAxisValue(ld.w_profile, axisIdx, t) : (w[axisIdx] + t * (w[axisIdx + 3] - w[axisIdx]));
  if (Math.abs(wAt) < PRES_ZERO) return null;
  const along = new THREE.Vector3().subVectors(p1, p0).normalize();
  const isParallel = Math.abs(axis.dot(along)) > 0.999;
  const vOff = distributedLoadOffset(axis, wAt, arrowBase, maxWMag);
  if (isParallel) {
    return { tail: pt.clone(), tip: pt.clone().add(vOff) };
  }
  const ept = pt.clone().sub(vOff);
  return { tail: ept, tip: pt.clone() };
}

function dominantAxisAtT(ld, t, hasProfile, w) {
  const comps = hasProfile
    ? [
        profileAxisValue(ld.w_profile, 0, t),
        profileAxisValue(ld.w_profile, 1, t),
        profileAxisValue(ld.w_profile, 2, t),
      ]
    : [
        w[0] + t * (w[3] - w[0]),
        w[1] + t * (w[4] - w[1]),
        w[2] + t * (w[5] - w[2]),
      ];
  let idx = 0;
  let best = Math.abs(comps[0]);
  for (let i = 1; i < 3; i++) {
    const a = Math.abs(comps[i]);
    if (a > best) {
      best = a;
      idx = i;
    }
  }
  return idx;
}

function profileAxisValue(profile, axisIdx, t) {
  if (!Array.isArray(profile) || profile.length === 0) return 0;
  if (t <= profile[0][0]) return profile[0][axisIdx + 1];
  for (let i = 0; i < profile.length - 1; i++) {
    const p0 = profile[i];
    const p1 = profile[i + 1];
    if (t > p1[0]) continue;
    const dt = p1[0] - p0[0];
    if (Math.abs(dt) < PRES_ZERO) return p0[axisIdx + 1];
    const r = (t - p0[0]) / dt;
    return p0[axisIdx + 1] + r * (p1[axisIdx + 1] - p0[axisIdx + 1]);
  }
  return profile[profile.length - 1][axisIdx + 1];
}

function profileLoadVector(profile, elem, t, isGlobal) {
  const wx = profileAxisValue(profile, 0, t);
  const wy = profileAxisValue(profile, 1, t);
  const wz = profileAxisValue(profile, 2, t);
  return elementLoadVector([wx, wy, wz, wx, wy, wz], 0, elem, isGlobal);
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
  const bg = bgSpecified ? opts.bg : "rgba(0,0,0," + ALPHA.labelDefaultBg + ")";
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
  ctx.globalAlpha = ALPHA.opaque;
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
    opacity: ALPHA.opaque,
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

function addElemLabel(text, point, span, scaleFactor, group, bg, transparent) {
  const sprite = makeTextSprite(text, span, {
    bg: bg || LABEL_BG.elem,
    fg: "#ffffff",
    pad: 4,
    scaleFactor: scaleFactor,
    transparent: transparent !== false,
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

function addDirectedArrow(tail, head, group, color, lineWidthPx, headScale, renderOrder) {
  const d = head.clone().sub(tail);
  const length = d.length();
  if (length < 1e-12) return head.clone();
  const dir = d.clone().normalize();
  const hs = (headScale != null && isFinite(headScale) && headScale > 0) ? headScale : 1.0;
  const headLen = Math.max(length * 0.22 * hs, length * 0.08 * hs);
  const headWide = headLen * 0.55;
  const wingBase = head.clone().addScaledVector(dir, -headLen);
  const perp = arrowPerpendicular(dir);
  const wingA = wingBase.clone().addScaledVector(perp, headWide);
  const wingB = wingBase.clone().addScaledVector(perp, -headWide);
  const ro = (renderOrder != null && isFinite(renderOrder)) ? renderOrder : 5;

  if (lineWidthPx != null) {
    const pts = [];
    addLinePair(tail, head, pts);
    addLinePair(wingA, head, pts);
    addLinePair(wingB, head, pts);
    addWideLineSegmentsFromPts(pts, color, group, ro, lineWidthPx);
    return head.clone();
  }

  const lineMat = new THREE.LineBasicMaterial({ color: color, depthTest: true });
  const shaftGeo = new THREE.BufferGeometry().setFromPoints([tail, head]);
  shaftGeo.computeBoundingSphere();
  const shaft = new THREE.Line(shaftGeo, lineMat);
  shaft.frustumCulled = false;
  shaft.renderOrder = ro;
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
  headLines.renderOrder = ro + 1;
  group.add(headLines);

  return head.clone();
}

function addDirectionArrow(origin, dir, length, group, color, lineWidthPx, headScale) {
  const d = dir.clone().normalize();
  const tip = origin.clone().addScaledVector(d, length);
  return addDirectedArrow(origin, tip, group, color, lineWidthPx, headScale);
}

function addLoadArrow(origin, dir, length, group) {
  // Slightly slimmer load arrows for better readability on dense scenes.
  return addDirectionArrow(origin, dir, length, group, COLORS.load, loadLineWidthPx(), 0.75);
}

function nodeLabelScaleFactor() {
  const v = parseFloat(viewerOptions.nodeLabelSize);
  if (!isFinite(v) || v <= 0) return 0.03;
  return v / 100;
}

function elemLabelScaleFactor() {
  const v = parseFloat(viewerOptions.elemLabelSize);
  if (!isFinite(v) || v <= 0) return 0.03;
  return v / 100;
}

function materialLabelScaleFactor() {
  const v = parseFloat(viewerOptions.materialLabelSize);
  if (!isFinite(v) || v <= 0) return 0.04;
  return v / 100;
}

function sectionLabelScaleFactor() {
  const v = parseFloat(viewerOptions.sectionLabelSize);
  if (!isFinite(v) || v <= 0) return 0.03;
  return v / 100;
}

function loadLabelScaleFactor() {
  const v = parseFloat(viewerOptions.loadLabelSize);
  if (!isFinite(v) || v <= 0) return 0.03;
  return v / 100;
}

function reactionLabelScaleFactor() {
  const v = parseFloat(viewerOptions.reactionLabelSize);
  if (!isFinite(v) || v <= 0) return 0.03;
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
  if (!isFinite(v) || v <= 0) return 0.06;
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
  const rowMap = {
    1: [0, 6],
    2: [1, 7],
    3: [2, 8],
    4: [3, 9],
    5: [4, 10, 12],
    6: [5, 11, 13],
  };
  const rows = rowMap[forceId] || [];
  let overallMax = 0;

  for (const e of model.elements) {
    const f = e.forces && e.forces[lcKey];
    if (!f) continue;
    for (const r of rows) {
      overallMax = Math.max(overallMax, Math.abs(f[r] || 0));
    }
  }

  if (forceId === 5 || forceId === 6) {
    for (const e of model.elements) {
      const f = e.forces && e.forces[lcKey];
      const lds = e.local_wloads && e.local_wloads[lcKey];
      if (!f || !lds) continue;
      const len = e.len || 1;
      const wzi = lds[2], wzj = lds[5], wyi = lds[1], wyj = lds[4];
      if (forceId === 5) {
        const qzi = f[2], myi = f[4];
        const wXc = wzi + (wzj - wzi) * 0.5;
        const mXc = myi + qzi * 0.5 * len + (1 / 6) * (wzi + 2 * wXc) * (0.5 * len) ** 2;
        overallMax = Math.max(overallMax, Math.abs(mXc));
      } else if (forceId === 6) {
        const qyi = f[1], mzi = f[5];
        const wXc = wyi + (wyj - wyi) * 0.5;
        const mXc = mzi - qyi * 0.5 * len - (1 / 6) * (wyi + 2 * wXc) * (0.5 * len) ** 2;
        overallMax = Math.max(overallMax, Math.abs(mXc));
      }
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
  const w = forceLineWidthPx();
  if (stemPts.length >= 6) {
    addWideLineSegmentsFromPts(stemPts, COLORS.force, group, 10, w, 1.0);
  }
  if (splinePts.length >= 2) {
    const linePts = [];
    for (let i = 0; i < splinePts.length - 1; i++) {
      addLinePair(splinePts[i], splinePts[i + 1], linePts);
    }
    addWideLineSegmentsFromPts(linePts, COLORS.force, group, 11, w, 1.0);
  }
}

function addForceValueLabel(text, point, model, group) {
  const span = modelSpan(model);
  const sprite = makeTextSprite(text, span, {
    bg: "rgba(0, 71, 171, " + ALPHA.forceValueBg + ")",
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
      const qXc = -qyi - 0.5 * (wyi + wXc) * 0.5 * e.len;
      const mp = new THREE.Vector3().lerpVectors(p0, p1, 0.5).addScaledVector(vy, dispFac * qXc);

      for (let i = 0; i <= divNum; i++) {
        const t = i / divNum;
        const x = t * e.len;
        const pt = new THREE.Vector3().lerpVectors(p0, p1, t);
        const wX = wyi + (wyj - wyi) * t;
        const qX = -qyi - 0.5 * (wyi + wX) * x;
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
  const useTransparent = !(opts && opts.transparent === false);
  const mat = new THREE.SpriteMaterial({
    map: tex,
    depthTest: false,
    depthWrite: false,
    transparent: useTransparent,
    opacity: ALPHA.opaque,
    premultipliedAlpha: opaqueText,
    alphaTest: useTransparent ? (opaqueText ? 0.01 : 0) : 0,
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
  const file = path.replace(/^.*\//, "");
  const stem = file.replace(/\.[^./]+$/i, "");
  const dir = path.includes("/") ? path.slice(0, path.lastIndexOf("/") + 1) : "";
  return dir + stem + ".out";
}

function showTextDocumentWindow(text, title) {
  const pdfName = title.replace(/\.(dat|out)$/i, ".pdf");
  const saveName = title;
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
  doc.write(".toolbar button{background:#e1dee4;color:#111;border:none;border-radius:4px;padding:6px 12px;font-weight:600;cursor:pointer;}");
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
  doc.write("<button type=\"button\" id=\"btnSaveTxt\">Save text</button>");
  doc.write("<button type=\"button\" id=\"btnPdf\">Save as PDF (A4 landscape)</button>");
  doc.write("</div>");
  doc.write("<header class=\"doc-title\">");
  doc.write(title);
  doc.write("</header><pre></pre></body></html>");
  doc.close();
  doc.querySelector("pre").textContent = text;
  doc.getElementById("btnSaveTxt").onclick = function () {
    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = doc.createElement("a");
    a.href = url;
    a.download = saveName;
    doc.body.appendChild(a);
    a.click();
    doc.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(url); }, 0);
  };
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

async function saveInputText(path, text) {
  const url = "/api/input?path=" + encodeURIComponent(path);
  const res = await fetch(url, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: text }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

function registerInputEditor(path, win, getText) {
  inputEditors.set(path, { win: win, getText: getText });
  const timer = setInterval(() => {
    if (!win.closed) return;
    clearInterval(timer);
    const entry = inputEditors.get(path);
    if (entry && entry.win === win) inputEditors.delete(path);
  }, 500);
}

function getInputEditorText(path) {
  const entry = inputEditors.get(path);
  if (entry && entry.win && !entry.win.closed) return entry.getText();
  return null;
}

function showInputEditorWindow(text, path) {
  const w = window.open("", "_blank", "width=980,height=760,scrollbars=yes,resizable=yes");
  if (!w) {
    setStatus("Popup blocked — allow popups for this site");
    return;
  }
  const doc = w.document;
  doc.open();
  doc.write("<!DOCTYPE html><html><head><meta charset=\"UTF-8\"><title>");
  doc.write(path);
  doc.write("</title><style>");
  doc.write("body{margin:0;background:#1e1e24;color:#e8e6ed;font-family:'Segoe UI',system-ui,sans-serif;}");
  doc.write(".toolbar{padding:8px 12px;background:#252530;border-bottom:1px solid #3a3a48;display:flex;gap:8px;align-items:center;}");
  doc.write(".toolbar button{background:#e1dee4;color:#111;border:none;border-radius:4px;padding:6px 12px;font-weight:600;cursor:pointer;}");
  doc.write(".toolbar button.secondary{background:#3a3a48;color:#e8e6ed;}");
  doc.write(".status{margin-left:auto;color:#aaa;font-size:12px;}");
  doc.write("textarea{width:100%;height:calc(100vh - 52px);box-sizing:border-box;border:0;outline:none;padding:12px;background:#111319;color:#e8e6ed;font-family:'Liberation Mono','DejaVu Sans Mono',monospace;font-size:12px;line-height:1.25;resize:none;}");
  doc.write("</style></head><body>");
  doc.write("<div class=\"toolbar\"><button id=\"btnSave\">Save</button><button id=\"btnReload\" class=\"secondary\">Reload</button><span id=\"status\" class=\"status\">ready</span></div>");
  doc.write("<textarea id=\"txt\"></textarea>");
  doc.write("</body></html>");
  doc.close();

  const textarea = doc.getElementById("txt");
  const statusEl = doc.getElementById("status");
  textarea.value = text;
  registerInputEditor(path, w, () => textarea.value);

  function setWinStatus(msg) {
    if (statusEl) statusEl.textContent = msg;
  }

  doc.getElementById("btnSave").addEventListener("click", async () => {
    try {
      setWinStatus("saving...");
      await saveInputText(path, textarea.value);
      resetEditHistory();
      setWinStatus("saved");
      setStatus(path + " — input file saved (undo history cleared)");
      if (getCurrentModelPath() === path) await loadSelectedModel(false);
    } catch (ex) {
      setWinStatus("save failed");
      setStatus("Error: " + ex.message);
      alert("Save failed: " + ex.message);
    }
  });

  doc.getElementById("btnReload").addEventListener("click", async () => {
    try {
      setWinStatus("reloading...");
      const latest = await fetchInputText(path);
      textarea.value = latest;
      setWinStatus("reloaded");
    } catch (ex) {
      setWinStatus("reload failed");
      alert("Reload failed: " + ex.message);
    }
  });
}

async function saveCurrentModel() {
  const path = getCurrentModelPath();
  if (!path) {
    setStatus("No model open");
    return;
  }
  setStatus("Saving " + path + "…");
  try {
    const edited = getInputEditorText(path);
    const text = edited != null ? edited : await fetchInputText(path);
    await saveInputText(path, text);
    resetEditHistory();
    if (getCurrentModelPath() === path) await loadSelectedModel(false);
    setStatus(path + " — saved");
  } catch (ex) {
    setStatus("Error: " + ex.message);
  }
}

async function openInputWindow() {
  const path = getCurrentModelPath();
  if (!path) return;

  setStatus("Loading " + path + "…");
  try {
    const text = await fetchInputText(path);
    showInputEditorWindow(text, path);
    setStatus(path + " — input file opened (editable)");
  } catch (ex) {
    setStatus("Error: " + ex.message);
  }
}

async function openResultsWindow() {
  const path = getCurrentModelPath();
  if (!path) return;

  let text = currentResultsText;

  if (text == null || text == "") {
    setStatus("Solving " + path + " for output…");
    try {
      currentModel = await fetchModel(path, true);
      text = currentModel.results_text;
      if (text == null || text == "") {
        throw new Error("No result text from server — restart: stb gui");
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

async function createNewModel() {
  setStatus("Creating new model…");
  try {
    const res = await fetch("/api/model/new", { method: "POST" });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || res.statusText);
    }
    const data = await res.json();
    setCurrentModelPath(data.path);
    await loadSelectedModel(false);
    await openInputWindow();
    setStatus(data.path + " — new model");
  } catch (ex) {
    setStatus("Error: " + ex.message);
  }
}

function promptOpenModelFile() {
  if (el.openFileInput) el.openFileInput.click();
}

async function openUploadedModelFile(file) {
  if (!file) return;
  setStatus("Opening " + file.name + "…");
  try {
    const text = await file.text();
    const res = await fetch("/api/model/open", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename: file.name, text: text }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || res.statusText);
    }
    const data = await res.json();
    setCurrentModelPath(data.path);
    await loadSelectedModel(false);
    setStatus(data.path + " — opened");
  } catch (ex) {
    setStatus("Error: " + ex.message);
  }
}

async function closeApplication() {
  setStatus("Shutting down…");
  try {
    await fetch("/api/shutdown", { method: "POST" });
  } catch (e) { /* server may exit before response completes */ }
  currentModel = null;
  currentModelPath = null;
  document.body.innerHTML = "<p style=\"padding:2rem;font-family:system-ui,sans-serif;color:#333\">"
    + "Structural Toolbox server stopped. You can close this tab.</p>";
}

async function loadSelectedModel(solve, options) {
  options = options || {};
  const path = getCurrentModelPath();
  if (!path) return;
  if (!options.keepSelection) clearSelection();
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
  initSelectionInteraction();
  initDistanceInteraction();
  initContextMenu();
  initEditHistoryShortcuts();
  initDraggablePanel({
    panel: el.selectionPanel,
    header: el.selectionPanelHeader,
    collapseBtn: el.btnSelectionCollapse,
    toggleBtn: el.btnToggleSelectionPanel,
    storageKey: "stb_gui_selection_panel",
    defaultHidden: true,
  });
  initDraggablePanel({
    panel: el.resultsPanel,
    header: el.resultsPanelHeader,
    collapseBtn: el.btnPanelCollapse,
    toggleBtn: el.btnTogglePanel,
    storageKey: "stb_gui_results_panel",
    defaultHidden: false,
  });
  initDraggablePanel({
    panel: el.optionsPanel,
    header: el.optionsPanelHeader,
    collapseBtn: el.btnOptionsCollapse,
    toggleBtn: el.btnToggleOptions,
    storageKey: "stb_gui_options_panel",
    defaultHidden: true,
  });
  try {
    const data = await fetchModelList();
    const launchFile = launchFileFromUrl();
    const initial = resolveInitialModel(data.models, data.default);
    if (initial) {
      setCurrentModelPath(initial);
      if (launchFile && initial === launchFile) clearLaunchFileFromUrl();
      await loadSelectedModel(false);
    } else {
      setCurrentModelPath(null);
      setStatus("Ready — use New or Open");
    }
  } catch (ex) {
    setStatus("Error: " + ex.message);
  }
}

el.btnNew.addEventListener("click", () => createNewModel());
el.btnOpen.addEventListener("click", () => promptOpenModelFile());
el.btnSave.addEventListener("click", () => saveCurrentModel());
el.btnClose.addEventListener("click", () => closeApplication());
if (el.openFileInput) {
  el.openFileInput.addEventListener("change", () => {
    const file = el.openFileInput.files && el.openFileInput.files[0];
    el.openFileInput.value = "";
    openUploadedModelFile(file);
  });
}

el.btnReload.addEventListener("click", () => loadSelectedModel(false));
el.btnSolve.addEventListener("click", () => loadSelectedModel(true));

function isViewerTextInputTarget(target) {
  if (!target) return false;
  const tag = target.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || target.isContentEditable;
}

document.addEventListener("keydown", (ev) => {
  if (isViewerTextInputTarget(ev.target)) return;

  if (ev.key === "F5" || ev.code === "F5") {
    ev.preventDefault();
    loadSelectedModel(true);
    return;
  }

  if (ev.key === "p" || ev.key === "P") {
    if (ev.ctrlKey || ev.metaKey || ev.altKey) return;
    ev.preventDefault();
    setSelectionMode(!selectionModeActive);
    return;
  }

  if (ev.key === "d" || ev.key === "D") {
    if (ev.ctrlKey || ev.metaKey || ev.altKey) return;
    ev.preventDefault();
    setDistanceMode(!distanceModeActive);
  }
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

if (el.btnToggleSelect) {
  el.btnToggleSelect.addEventListener("click", () => {
    setSelectionMode(!selectionModeActive);
  });
}

if (el.btnToggleDistance) {
  el.btnToggleDistance.addEventListener("click", () => {
    setDistanceMode(!distanceModeActive);
  });
}

if (el.btnClearSelection) {
  el.btnClearSelection.addEventListener("click", () => clearSelection());
}

el.btnInput.addEventListener("click", () => openInputWindow());
el.btnOutput.addEventListener("click", () => openResultsWindow());
el.lcSelect.addEventListener("change", () => {
  dispContourScaleKey = null;
  if (currentModel) rebuildScene();
  updateSelectionPanel();
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
if (el.chkEJnt) {
  el.chkEJnt.addEventListener("change", () => {
    if (currentModel) rebuildScene();
  });
}
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
if (el.chkMembrane) {
  el.chkMembrane.addEventListener("change", () => {
    if (currentModel) rebuildScene();
  });
}
if (el.chkWoodWall) {
  el.chkWoodWall.addEventListener("change", () => {
    if (currentModel) rebuildScene();
  });
}
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
    "loadArrowSize", parseFloat(el.optLoadArrow.value) || OPTIONS_DEFAULTS.loadArrowSize);
  viewerOptions.supportGizmoSize = clampViewerOption(
    "supportGizmoSize", parseInt(el.optSupportGizmo.value, 10) || OPTIONS_DEFAULTS.supportGizmoSize);
  viewerOptions.supportLineWidth = clampViewerOption(
    "supportLineWidth", parseFloat(el.optSupportLineWidth.value) || OPTIONS_DEFAULTS.supportLineWidth);
  viewerOptions.dispContourLineWidth = clampViewerOption(
    "dispContourLineWidth", parseFloat(el.optDispContourLineWidth.value) || OPTIONS_DEFAULTS.dispContourLineWidth);
  viewerOptions.elementLineWidth = clampViewerOption(
    "elementLineWidth", parseFloat(el.optElementLineWidth.value) || OPTIONS_DEFAULTS.elementLineWidth);
  viewerOptions.loadLineWidth = clampViewerOption(
    "loadLineWidth", parseFloat(el.optLoadLineWidth.value) || OPTIONS_DEFAULTS.loadLineWidth);
  viewerOptions.forceLineWidth = clampViewerOption(
    "forceLineWidth", parseFloat(el.optForceLineWidth.value) || OPTIONS_DEFAULTS.forceLineWidth);
  viewerOptions.nodeLabelSize = clampViewerOption(
    "nodeLabelSize", parseFloat(el.optNodeLabel.value) || OPTIONS_DEFAULTS.nodeLabelSize);
  viewerOptions.elemLabelSize = clampViewerOption(
    "elemLabelSize", parseFloat(el.optElemLabel.value) || OPTIONS_DEFAULTS.elemLabelSize);
  viewerOptions.materialLabelSize = clampViewerOption(
    "materialLabelSize", parseFloat(el.optMaterialLabel.value) || OPTIONS_DEFAULTS.materialLabelSize);
  viewerOptions.sectionLabelSize = clampViewerOption(
    "sectionLabelSize", parseFloat(el.optSectionLabel.value) || OPTIONS_DEFAULTS.sectionLabelSize);
  viewerOptions.loadLabelSize = clampViewerOption(
    "loadLabelSize", parseFloat(el.optLoadLabel.value) || OPTIONS_DEFAULTS.loadLabelSize);
  viewerOptions.reactionLabelSize = clampViewerOption(
    "reactionLabelSize", parseFloat(el.optReactionLabel.value) || OPTIONS_DEFAULTS.reactionLabelSize);
  viewerOptions.forceLabelSize = clampViewerOption(
    "forceLabelSize", parseFloat(el.optForceLabel.value) || OPTIONS_DEFAULTS.forceLabelSize);
  if (el.loadTypeFilter) {
    viewerOptions.inputLoadType = el.loadTypeFilter.value || OPTIONS_DEFAULTS.inputLoadType;
  }
}

function applyOptionsToUi() {
  el.optLoadArrow.value = String(viewerOptions.loadArrowSize);
  el.optLoadArrowVal.textContent = Number(viewerOptions.loadArrowSize).toFixed(1);
  el.optSupportGizmo.value = String(viewerOptions.supportGizmoSize);
  el.optSupportGizmoVal.textContent = String(viewerOptions.supportGizmoSize);
  el.optSupportLineWidth.value = String(viewerOptions.supportLineWidth);
  el.optDispContourLineWidth.value = String(viewerOptions.dispContourLineWidth);
  if (el.optElementLineWidth) el.optElementLineWidth.value = String(viewerOptions.elementLineWidth);
  if (el.optLoadLineWidth) el.optLoadLineWidth.value = String(viewerOptions.loadLineWidth);
  if (el.optForceLineWidth) el.optForceLineWidth.value = String(viewerOptions.forceLineWidth);
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
  if (el.loadTypeFilter) {
    el.loadTypeFilter.value = loadTypeFilterValue();
  }
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
    if (typeof st.elementLineWidth === "number") viewerOptions.elementLineWidth = st.elementLineWidth;
    if (typeof st.loadLineWidth === "number") viewerOptions.loadLineWidth = st.loadLineWidth;
    if (typeof st.forceLineWidth === "number") viewerOptions.forceLineWidth = st.forceLineWidth;
    if (typeof st.nodeLabelSize === "number") viewerOptions.nodeLabelSize = st.nodeLabelSize;
    if (typeof st.elemLabelSize === "number") viewerOptions.elemLabelSize = st.elemLabelSize;
    if (typeof st.materialLabelSize === "number") viewerOptions.materialLabelSize = st.materialLabelSize;
    if (typeof st.sectionLabelSize === "number") viewerOptions.sectionLabelSize = st.sectionLabelSize;
    if (typeof st.loadLabelSize === "number") viewerOptions.loadLabelSize = st.loadLabelSize;
    if (typeof st.reactionLabelSize === "number") viewerOptions.reactionLabelSize = st.reactionLabelSize;
    if (typeof st.forceLabelSize === "number") viewerOptions.forceLabelSize = st.forceLabelSize;
    if (typeof st.inputLoadType === "string") viewerOptions.inputLoadType = st.inputLoadType;
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
    el.optLoadArrowVal.textContent = Number(el.optLoadArrow.value).toFixed(1);
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
  if (el.optElementLineWidth) {
    el.optElementLineWidth.addEventListener("input", onOptionsChanged);
    el.optElementLineWidth.addEventListener("change", onOptionsChanged);
  }
  if (el.optLoadLineWidth) {
    el.optLoadLineWidth.addEventListener("input", onOptionsChanged);
    el.optLoadLineWidth.addEventListener("change", onOptionsChanged);
  }
  if (el.optForceLineWidth) {
    el.optForceLineWidth.addEventListener("input", onOptionsChanged);
    el.optForceLineWidth.addEventListener("change", onOptionsChanged);
  }
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
  if (el.loadTypeFilter) {
    el.loadTypeFilter.addEventListener("change", onOptionsChanged);
  }
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
