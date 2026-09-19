/**
 * Autonomous Mobile Robot (AMR) Fleet Operations Digital Twin
 * Real-time 3D WebGL Warehouse Twin powered by Three.js
 */

// --- Global State & Configuration ---
let scene, camera, renderer, controls;
let canvas, canvasWrap, hudOverlayLayer;
let warehouseGroup, robotsGroup, lasersGroup, markersGroup;
let gridData = { width: 30, height: 20, cells: [] };
let robotMeshes = new Map(); // robot_id -> { group, targetPos, targetRot, currentPos, currentRot, model, ... }
let currentFleetState = null;
let selectedRobotId = null;
let cameraMode = "overview"; // "overview" | "follow" | "topdown" | "workstation"
let showHUDs = true;
let showLasers = true;
let simPaused = false;
let simSpeed = 1.0;
let textures = {};

const AMR_COLORS = ["#00f0ff", "#ffbd59", "#a855f7", "#10b981", "#f43f5e", "#38bdf8"];

// --- Procedural Texture Generators for Industrial Warehouse Realism ---
function createFloorTexture(width, height) {
  const canvas = document.createElement("canvas");
  canvas.width = 2048;
  canvas.height = 1536;
  const ctx = canvas.getContext("2d");

  // 1. Polished concrete floor base
  const grad = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
  grad.addColorStop(0, "#182029");
  grad.addColorStop(0.5, "#141b22");
  grad.addColorStop(1, "#0f151c");
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  // Subtle concrete noise / speckle
  ctx.fillStyle = "rgba(255, 255, 255, 0.015)";
  for (let i = 0; i < 40000; i++) {
    const rx = Math.random() * canvas.width;
    const ry = Math.random() * canvas.height;
    ctx.fillRect(rx, ry, 1 + Math.random() * 2, 1 + Math.random() * 2);
  }

  // 2. Concrete slab expansion joints (grid lines)
  const cellW = canvas.width / width;
  const cellH = canvas.height / height;
  ctx.strokeStyle = "rgba(0, 0, 0, 0.4)";
  ctx.lineWidth = 3;
  for (let x = 0; x <= width; x++) {
    ctx.beginPath();
    ctx.moveTo(x * cellW, 0);
    ctx.lineTo(x * cellW, canvas.height);
    ctx.stroke();
  }
  for (let y = 0; y <= height; y++) {
    ctx.beginPath();
    ctx.moveTo(0, y * cellH);
    ctx.lineTo(canvas.width, y * cellH);
    ctx.stroke();
  }

  // 3. Painted Safety Lane Guideway Lines & Crossings
  ctx.strokeStyle = "rgba(245, 158, 11, 0.45)"; // Safety amber
  ctx.lineWidth = 6;
  ctx.setLineDash([20, 15]);
  // Central main corridors
  const midY = (height / 2) * cellH;
  ctx.beginPath();
  ctx.moveTo(cellW, midY);
  ctx.lineTo(canvas.width - cellW, midY);
  ctx.stroke();
  const midX = (width / 2) * cellW;
  ctx.beginPath();
  ctx.moveTo(midX, cellH);
  ctx.lineTo(midX, canvas.height - cellH);
  ctx.stroke();
  ctx.setLineDash([]);

  // 4. "AMR ZONE" Stencils (Matching Reference Photo)
  ctx.save();
  ctx.fillStyle = "rgba(255, 255, 255, 0.4)";
  ctx.font = "bold 42px 'JetBrains Mono', monospace";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  
  // Left aisle stencil
  ctx.fillText("AMR ZONE", cellW * 3.5, cellH * 3);
  ctx.strokeStyle = "rgba(255, 255, 255, 0.35)";
  ctx.lineWidth = 4;
  ctx.strokeRect(cellW * 1.5, cellH * 2.2, cellW * 4, cellH * 1.6);

  // Center crossing stencil
  ctx.fillText("AMR ZONE", cellW * 15, cellH * 10);
  ctx.strokeRect(cellW * 12.5, cellH * 9.2, cellW * 5, cellH * 1.6);

  // 5. CAUTION Hazard Chevron Striping (Matching Reference Photo)
  function drawHazardStripes(x, y, w, h) {
    ctx.save();
    ctx.beginPath();
    ctx.rect(x, y, w, h);
    ctx.clip();
    ctx.fillStyle = "#f59e0b";
    ctx.fillRect(x, y, w, h);
    ctx.fillStyle = "#111827";
    const stripeW = 16;
    for (let i = -h; i < w + h; i += stripeW * 2) {
      ctx.beginPath();
      ctx.moveTo(x + i, y);
      ctx.lineTo(x + i + stripeW, y);
      ctx.lineTo(x + i + stripeW - h, y + h);
      ctx.lineTo(x + i - h, y + h);
      ctx.closePath();
      ctx.fill();
    }
    ctx.restore();
  }

  // Hazard stripe zones near dock entrances
  drawHazardStripes(cellW * 1, cellH * 0.8, cellW * 3, 14);
  drawHazardStripes(cellW * (width - 4), cellH * (height - 1.2), cellW * 3, 14);

  // 6. Dock Bay Markers
  ctx.fillStyle = "rgba(255, 255, 255, 0.7)";
  ctx.font = "bold 28px 'JetBrains Mono', monospace";
  ctx.fillText("INBOUND DOCK 1", cellW * 2.5, cellH * 1.5);
  ctx.fillText("DELIVERY BAY 3", cellW * (width - 3), cellH * (height - 1.5));
  ctx.fillText("AISLE 12", cellW * 15, cellH * 2);

  ctx.restore();

  const texture = new THREE.CanvasTexture(canvas);
  texture.wrapS = THREE.ClampToEdgeWrapping;
  texture.wrapT = THREE.ClampToEdgeWrapping;
  return texture;
}

// Procedural Cardboard Box Texture with Amazon-style Shipping Barcodes & Labels
function createBoxTexture(label = "AMZ-BOX-A12", subtitle = "ELECTRONICS") {
  const canvas = document.createElement("canvas");
  canvas.width = 512;
  canvas.height = 512;
  const ctx = canvas.getContext("2d");

  // Kraft cardboard base
  ctx.fillStyle = "#c99a63";
  ctx.fillRect(0, 0, 512, 512);

  // Cardboard texture grain
  ctx.fillStyle = "rgba(0, 0, 0, 0.05)";
  for (let i = 0; i < 6000; i++) {
    ctx.fillRect(Math.random() * 512, Math.random() * 512, 2, 2);
  }

  // Shipping Tape across top/center
  ctx.fillStyle = "rgba(180, 130, 75, 0.6)";
  ctx.fillRect(0, 240, 512, 32);

  // White shipping label sticker
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(40, 80, 240, 140);
  ctx.strokeStyle = "#999999";
  ctx.strokeRect(40, 80, 240, 140);

  // Barcode lines
  ctx.fillStyle = "#111111";
  for (let x = 60; x < 260; x += 4 + Math.floor(Math.random() * 8)) {
    ctx.fillRect(x, 95, 2 + Math.floor(Math.random() * 3), 40);
  }
  ctx.font = "bold 18px monospace";
  ctx.fillText(label, 60, 160);
  ctx.font = "12px sans-serif";
  ctx.fillText("PRIORITY EXPRESS", 60, 185);

  // Large Stenciled Box Title on kraft board (Matching Reference Photo)
  ctx.fillStyle = "#222222";
  ctx.font = "bold 38px 'JetBrains Mono', monospace";
  ctx.fillText(label, 50, 340);
  ctx.font = "bold 20px 'JetBrains Mono', monospace";
  ctx.fillText(subtitle, 52, 380);

  // Fragile / Upright Icons
  ctx.fillText("↑↑ FRAGILE", 52, 440);

  const tex = new THREE.CanvasTexture(canvas);
  return tex;
}

// --- 3D Scene Setup ---
function init3D() {
  canvas = document.querySelector("#fleet-canvas");
  canvasWrap = document.querySelector("#canvas-container");
  hudOverlayLayer = document.querySelector("#hud-overlay-layer");

  const width = canvasWrap.clientWidth;
  const height = canvasWrap.clientHeight;

  // Scene
  scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0a1017);
  scene.fog = new THREE.FogExp2(0x0a1017, 0.012);

  // Camera
  camera = new THREE.PerspectiveCamera(45, width / height, 0.5, 300);
  camera.position.set(15, 26, 32);

  // Renderer with soft shadows & ACES tone mapping
  renderer = new THREE.WebGLRenderer({
    canvas: canvas,
    antialias: true,
    powerPreference: "high-performance",
  });
  renderer.setSize(width, height);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.15;

  // Orbit Controls
  controls = new THREE.OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.06;
  controls.maxPolarAngle = Math.PI / 2 - 0.05; // Do not go beneath floor
  controls.minDistance = 6;
  controls.maxDistance = 80;
  controls.target.set(15, 0, 10);
  controls.update();

  // Lighting
  setupLighting();

  // Root Groups
  warehouseGroup = new THREE.Group();
  robotsGroup = new THREE.Group();
  lasersGroup = new THREE.Group();
  markersGroup = new THREE.Group();
  scene.add(warehouseGroup);
  scene.add(robotsGroup);
  scene.add(lasersGroup);
  scene.add(markersGroup);

  // Setup Raycasting for interactive clicks
  setupInteraction();

  // Resize Listener
  window.addEventListener("resize", onWindowResize);

  // Start Animation Loop
  requestAnimationFrame(animate);
}

function setupLighting() {
  // Ambient fill
  const ambient = new THREE.AmbientLight(0x405568, 0.9);
  scene.add(ambient);

  // Main directional ceiling sunlight
  const sunLight = new THREE.DirectionalLight(0xf0f7ff, 1.4);
  sunLight.position.set(20, 35, 25);
  sunLight.castShadow = true;
  sunLight.shadow.mapSize.width = 2048;
  sunLight.shadow.mapSize.height = 2048;
  sunLight.shadow.camera.near = 5;
  sunLight.shadow.camera.far = 70;
  const d = 25;
  sunLight.shadow.camera.left = -d;
  sunLight.shadow.camera.right = d;
  sunLight.shadow.camera.top = d;
  sunLight.shadow.camera.bottom = -d;
  sunLight.shadow.bias = -0.0005;
  scene.add(sunLight);

  // Workstation warm accent spotlight (over packing station on the left)
  const stationLight = new THREE.SpotLight(0xffeedd, 2.0, 30, Math.PI / 4, 0.4);
  stationLight.position.set(3, 12, 4);
  stationLight.target.position.set(3, 0, 4);
  scene.add(stationLight);
  scene.add(stationLight.target);
}

// --- Build Warehouse Digital Twin Environment ---
function buildWarehouse(grid) {
  // Clear previous static meshes
  while (warehouseGroup.children.length > 0) {
    const obj = warehouseGroup.children[0];
    warehouseGroup.remove(obj);
    if (obj.geometry) obj.geometry.dispose();
  }

  const { width, height, cells } = grid;

  // 1. Polished Concrete Ground Plane
  const floorGeo = new THREE.PlaneGeometry(width, height);
  const floorTex = createFloorTexture(width, height);
  const floorMat = new THREE.MeshStandardMaterial({
    map: floorTex,
    roughness: 0.38,
    metalness: 0.15,
  });
  const floorMesh = new THREE.Mesh(floorGeo, floorMat);
  floorMesh.rotation.x = -Math.PI / 2;
  floorMesh.position.set(width / 2, 0, height / 2);
  floorMesh.receiveShadow = true;
  warehouseGroup.add(floorMesh);

  // 2. High Industrial Warehouse Walls & Ceiling Trusses
  buildEnclosureAndCeiling(width, height);

  // 3. Packaging & Conveyor Workstation (Left Side - Matching Reference Photo)
  buildWorkstationArea(cells);

  // 4. Industrial Pallet Racks on Obstacle Cells
  buildStorageRacks(grid);
}

function buildEnclosureAndCeiling(width, height) {
  const wallMat = new THREE.MeshStandardMaterial({
    color: 0x1e2833,
    roughness: 0.8,
  });

  // Back Wall
  const backGeo = new THREE.BoxGeometry(width, 10, 0.4);
  const backWall = new THREE.Mesh(backGeo, wallMat);
  backWall.position.set(width / 2, 5, -0.2);
  backWall.receiveShadow = true;
  warehouseGroup.add(backWall);

  // Left Wall
  const leftGeo = new THREE.BoxGeometry(0.4, 10, height);
  const leftWall = new THREE.Mesh(leftGeo, wallMat);
  leftWall.position.set(-0.2, 5, height / 2);
  leftWall.receiveShadow = true;
  warehouseGroup.add(leftWall);

  // Steel Roof I-Beams / Trusses & Hanging Fluorescent Light Bars
  const steelMat = new THREE.MeshStandardMaterial({ color: 0x334155, metalness: 0.8, roughness: 0.4 });
  const lightBarMat = new THREE.MeshBasicMaterial({ color: 0xf0f9ff });

  for (let z = 3; z < height; z += 6) {
    // Cross truss I-beam
    const beamGeo = new THREE.BoxGeometry(width, 0.4, 0.2);
    const beam = new THREE.Mesh(beamGeo, steelMat);
    beam.position.set(width / 2, 9.8, z);
    warehouseGroup.add(beam);

    // Suspended light bars
    for (let x = 4; x < width; x += 8) {
      const barGeo = new THREE.BoxGeometry(3, 0.08, 0.3);
      const lightBar = new THREE.Mesh(barGeo, lightBarMat);
      lightBar.position.set(x, 8.8, z);
      warehouseGroup.add(lightBar);

      // Soft downward light pool
      const pl = new THREE.PointLight(0xe2f1fc, 0.4, 12);
      pl.position.set(x, 8.5, z);
      warehouseGroup.add(pl);
    }
  }

  // Overhead Zone Placards (AISLE 12, DOCK 4)
  createOverheadSign("AISLE 12", 15, 7.5, 4);
  createOverheadSign("DOCK 4", 2.5, 7.5, 2);
  createOverheadSign("DELIVERY-3", width - 4, 7.5, height - 3);
}

function createOverheadSign(text, x, y, z) {
  const canvas = document.createElement("canvas");
  canvas.width = 256;
  canvas.height = 64;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#1e293b";
  ctx.fillRect(0, 0, 256, 64);
  ctx.strokeStyle = "#38bdf8";
  ctx.lineWidth = 4;
  ctx.strokeRect(2, 2, 252, 60);
  ctx.fillStyle = "#ffffff";
  ctx.font = "bold 26px 'JetBrains Mono', monospace";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(text, 128, 32);

  const tex = new THREE.CanvasTexture(canvas);
  const mat = new THREE.MeshBasicMaterial({ map: tex, side: THREE.DoubleSide });
  const geo = new THREE.PlaneGeometry(2.4, 0.6);
  const mesh = new THREE.Mesh(geo, mat);
  mesh.position.set(x, y, z);
  mesh.rotation.y = Math.PI / 4;
  warehouseGroup.add(mesh);
}

// Build Workstation, Conveyor Belt, Terminal Monitor (Left Side of Image)
function buildWorkstationArea(cells) {
  const stationGroup = new THREE.Group();
  stationGroup.position.set(2.5, 0, 3.5);

  const aluMat = new THREE.MeshStandardMaterial({ color: 0x94a3b8, metalness: 0.8, roughness: 0.2 });
  const darkMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, roughness: 0.6 });
  const yellowBollardMat = new THREE.MeshStandardMaterial({ color: 0xf59e0b, roughness: 0.4 });

  // 1. Packaging Desk
  const deskTopGeo = new THREE.BoxGeometry(2.6, 0.1, 1.4);
  const deskTop = new THREE.Mesh(deskTopGeo, darkMat);
  deskTop.position.set(0, 1.2, 0);
  deskTop.castShadow = true;
  deskTop.receiveShadow = true;
  stationGroup.add(deskTop);

  // Legs
  for (const [lx, lz] of [[-1.2, -0.6], [1.2, -0.6], [-1.2, 0.6], [1.2, 0.6]]) {
    const legGeo = new THREE.CylinderGeometry(0.04, 0.04, 1.2);
    const leg = new THREE.Mesh(legGeo, aluMat);
    leg.position.set(lx, 0.6, lz);
    stationGroup.add(leg);
  }

  // 2. PC Terminal Monitor & Scanner Console
  const monitorGeo = new THREE.BoxGeometry(0.8, 0.5, 0.05);
  const screenTex = createScreenTexture();
  const monitorMat = new THREE.MeshBasicMaterial({ map: screenTex });
  const monitor = new THREE.Mesh(monitorGeo, monitorMat);
  monitor.position.set(0, 1.7, -0.4);
  monitor.rotation.y = 0.1;
  stationGroup.add(monitor);

  const standGeo = new THREE.CylinderGeometry(0.03, 0.03, 0.5);
  const stand = new THREE.Mesh(standGeo, aluMat);
  stand.position.set(0, 1.45, -0.4);
  stationGroup.add(stand);

  // 3. Conveyor Roller Track Assembly
  const conveyorGeo = new THREE.BoxGeometry(4.0, 0.2, 0.9);
  const conveyorMat = new THREE.MeshStandardMaterial({ color: 0x334155, metalness: 0.7, roughness: 0.3 });
  const conveyor = new THREE.Mesh(conveyorGeo, conveyorMat);
  conveyor.position.set(-1.6, 0.9, 1.6);
  conveyor.castShadow = true;
  stationGroup.add(conveyor);

  // Roller Cylinders
  const rollerGeo = new THREE.CylinderGeometry(0.04, 0.04, 0.85, 12);
  const rollerMat = new THREE.MeshStandardMaterial({ color: 0xcbd5e1, metalness: 0.9, roughness: 0.2 });
  for (let rx = -3.4; rx <= 0.2; rx += 0.22) {
    const roller = new THREE.Mesh(rollerGeo, rollerMat);
    roller.rotation.x = Math.PI / 2;
    roller.position.set(rx, 1.02, 1.6);
    stationGroup.add(roller);
  }

  // Yellow Safety Bollards
  for (const bx of [-3.8, 0.5]) {
    const bollardGeo = new THREE.CylinderGeometry(0.08, 0.08, 1.1, 16);
    const bollard = new THREE.Mesh(bollardGeo, yellowBollardMat);
    bollard.position.set(bx, 0.55, 2.3);
    bollard.castShadow = true;
    stationGroup.add(bollard);
  }

  warehouseGroup.add(stationGroup);
}

function createScreenTexture() {
  const canvas = document.createElement("canvas");
  canvas.width = 256;
  canvas.height = 160;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#0284c7";
  ctx.fillRect(0, 0, 256, 160);
  ctx.fillStyle = "#ffffff";
  ctx.font = "bold 14px monospace";
  ctx.fillText("WAREHOUSE WMS · NODE 1", 10, 24);
  ctx.fillStyle = "#e0f2fe";
  ctx.font = "11px monospace";
  ctx.fillText("INBOUND BUFFER: 84%", 10, 50);
  ctx.fillText("DISPATCH QUEUE: READY", 10, 70);
  ctx.fillText("AUTONOMOUS ROUTING: OK", 10, 90);
  ctx.fillStyle = "#38bdf8";
  ctx.fillRect(10, 110, 236, 18);
  ctx.fillStyle = "#0369a1";
  ctx.fillText("PACKING LINE VERIFIED", 15, 124);
  return new THREE.CanvasTexture(canvas);
}

// Build Industrial Multi-Tier Pallet Racks on Obstacle Cells
function buildStorageRacks(grid) {
  const { width, height, cells } = grid;

  // Shared rack materials
  const blueUprightMat = new THREE.MeshStandardMaterial({
    color: 0x1d4ed8, // Industrial Blue
    metalness: 0.6,
    roughness: 0.35,
  });
  const orangeBeamMat = new THREE.MeshStandardMaterial({
    color: 0xe65c00, // Safety Orange
    metalness: 0.5,
    roughness: 0.4,
  });
  const palletMat = new THREE.MeshStandardMaterial({
    color: 0xb4824d, // Pine wood pallet
    roughness: 0.8,
  });

  const boxTextures = [
    createBoxTexture("AMZ-BOX-A12", "ELECTRONICS"),
    createBoxTexture("GEAR-UNIT X1", "PRECISION"),
    createBoxTexture("TOTE-B5", "FRAGILE ITEMS"),
    createBoxTexture("MED-BOX-4", "BIO-HEALTH"),
  ];

  for (let y = 1; y < height - 1; y++) {
    for (let x = 1; x < width - 1; x++) {
      if (cells[y] && cells[y][x] === 1) {
        // Build high-bay rack at cell (x, y)
        const rackGroup = new THREE.Group();
        rackGroup.position.set(x + 0.5, 0, y + 0.5);

        const rw = 0.92;
        const rd = 0.88;
        const rh = 3.6;

        // 4 Blue Upright Posts
        const postGeo = new THREE.BoxGeometry(0.06, rh, 0.06);
        for (const [px, pz] of [
          [-rw / 2, -rd / 2],
          [rw / 2, -rd / 2],
          [-rw / 2, rd / 2],
          [rw / 2, rd / 2],
        ]) {
          const post = new THREE.Mesh(postGeo, blueUprightMat);
          post.position.set(px, rh / 2, pz);
          post.castShadow = true;
          post.receiveShadow = true;
          rackGroup.add(post);
        }

        // 3 Shelf Levels (Safety Orange Load Beams & Pallets)
        const shelfHeights = [0.8, 1.8, 2.8];
        const beamGeo = new THREE.BoxGeometry(rw, 0.08, 0.05);
        const palletGeo = new THREE.BoxGeometry(rw * 0.86, 0.06, rd * 0.84);

        shelfHeights.forEach((sh, sIdx) => {
          // Front & back orange horizontal beams
          const frontBeam = new THREE.Mesh(beamGeo, orangeBeamMat);
          frontBeam.position.set(0, sh, rd / 2);
          rackGroup.add(frontBeam);

          const backBeam = new THREE.Mesh(beamGeo, orangeBeamMat);
          backBeam.position.set(0, sh, -rd / 2);
          rackGroup.add(backBeam);

          // Wooden Pallet
          const pallet = new THREE.Mesh(palletGeo, palletMat);
          pallet.position.set(0, sh + 0.04, 0);
          pallet.castShadow = true;
          rackGroup.add(pallet);

          // Cardboard cartons / Totes on shelf
          if ((x + y + sIdx) % 2 === 0) {
            const tex = boxTextures[(x + y + sIdx) % boxTextures.length];
            const boxMat = new THREE.MeshStandardMaterial({
              map: tex,
              roughness: 0.6,
            });
            const boxH = 0.55;
            const boxW = 0.58;
            const boxGeo = new THREE.BoxGeometry(boxW, boxH, rd * 0.7);
            const box = new THREE.Mesh(boxGeo, boxMat);
            box.position.set((sIdx % 2 ? 0.08 : -0.08), sh + 0.07 + boxH / 2, 0);
            box.castShadow = true;
            box.receiveShadow = true;
            rackGroup.add(box);
          } else if ((x + y + sIdx) % 3 === 0) {
            // Blue/Gray Industrial Storage Tote
            const toteMat = new THREE.MeshStandardMaterial({
              color: sIdx % 2 === 0 ? 0x2563eb : 0x475569,
              roughness: 0.4,
              metalness: 0.1,
            });
            const toteGeo = new THREE.BoxGeometry(0.65, 0.4, 0.55);
            const tote = new THREE.Mesh(toteGeo, toteMat);
            tote.position.set(0, sh + 0.07 + 0.2, 0);
            tote.castShadow = true;
            rackGroup.add(tote);
          }
        });

        warehouseGroup.add(rackGroup);
      }
    }
  }
}

// --- 3D Realistic AMR Robot Mesh Builders ---

// 1. Build ATR-400 (Heavy Cargo Transport AMR - with Dual Tracks, Cyan LED, Cargo Deck)
function buildATR400Mesh(robot, colorHex) {
  const root = new THREE.Group();

  const chassisWhiteMat = new THREE.MeshStandardMaterial({
    color: 0xf1f5f9,
    metalness: 0.35,
    roughness: 0.25,
  });
  const skirtDarkMat = new THREE.MeshStandardMaterial({
    color: 0x1e293b,
    metalness: 0.5,
    roughness: 0.5,
  });
  const cyanGlowMat = new THREE.MeshBasicMaterial({
    color: 0x00f0ff,
  });
  const rubberTreadMat = new THREE.MeshStandardMaterial({
    color: 0x0f172a,
    roughness: 0.9,
    metalness: 0.1,
  });

  // Main Low-Profile Sculpted Chassis Body
  const bodyGeo = new THREE.BoxGeometry(0.72, 0.22, 0.88);
  const body = new THREE.Mesh(bodyGeo, chassisWhiteMat);
  body.position.y = 0.22;
  body.castShadow = true;
  root.add(body);

  // Lower Chamfered Bumper Skirt
  const skirtGeo = new THREE.BoxGeometry(0.78, 0.12, 0.94);
  const skirt = new THREE.Mesh(skirtGeo, skirtDarkMat);
  skirt.position.y = 0.1;
  skirt.castShadow = true;
  root.add(skirt);

  // Dual Side Continuous Crawler Tread Track Assemblies
  for (const side of [-0.41, 0.41]) {
    // Rubber Track Belt
    const trackGeo = new THREE.BoxGeometry(0.12, 0.18, 0.9);
    const track = new THREE.Mesh(trackGeo, rubberTreadMat);
    track.position.set(side, 0.12, 0);
    track.castShadow = true;
    root.add(track);

    // Track Sprockets / Wheels (3 on each side)
    const wheelMat = new THREE.MeshStandardMaterial({ color: 0x475569, metalness: 0.8, roughness: 0.3 });
    for (const wz of [-0.3, 0, 0.3]) {
      const wheelGeo = new THREE.CylinderGeometry(0.08, 0.08, 0.13, 16);
      const wheel = new THREE.Mesh(wheelGeo, wheelMat);
      wheel.rotation.z = Math.PI / 2;
      wheel.position.set(side, 0.11, wz);
      root.add(wheel);
    }
  }

  // Front Glowing LED Lightbar (Cyan) - Matching Reference Photo
  const lightGeo = new THREE.BoxGeometry(0.6, 0.04, 0.04);
  const frontLight = new THREE.Mesh(lightGeo, cyanGlowMat);
  frontLight.position.set(0, 0.22, 0.45);
  root.add(frontLight);

  // Front Bumper Name Plate ("PICKER-1" / ATR-400)
  const plateCanvas = document.createElement("canvas");
  plateCanvas.width = 128;
  plateCanvas.height = 32;
  const pCtx = plateCanvas.getContext("2d");
  pCtx.fillStyle = "#0f172a";
  pCtx.fillRect(0, 0, 128, 32);
  pCtx.fillStyle = "#38bdf8";
  pCtx.font = "bold 16px monospace";
  pCtx.textAlign = "center";
  pCtx.textBaseline = "middle";
  pCtx.fillText(String(robot.robot_id).replace("robot-", "PICKER-"), 64, 16);
  const plateTex = new THREE.CanvasTexture(plateCanvas);
  const plateMesh = new THREE.Mesh(
    new THREE.PlaneGeometry(0.38, 0.09),
    new THREE.MeshBasicMaterial({ map: plateTex })
  );
  plateMesh.position.set(0, 0.22, 0.455);
  root.add(plateMesh);

  // Top Elevating Cargo Deck
  const deckGeo = new THREE.BoxGeometry(0.66, 0.04, 0.74);
  const deck = new THREE.Mesh(deckGeo, skirtDarkMat);
  deck.position.y = 0.35;
  root.add(deck);

  // Payload Cargo Box (Amazon-style labeled shipping carton)
  const boxTex = createBoxTexture("AMZ-BOX-A12", "ELECTRONICS");
  const boxMat = new THREE.MeshStandardMaterial({ map: boxTex, roughness: 0.6 });
  const cargoBox = new THREE.Mesh(new THREE.BoxGeometry(0.56, 0.38, 0.62), boxMat);
  cargoBox.position.set(0, 0.56, 0);
  cargoBox.castShadow = true;
  cargoBox.name = "cargo";
  root.add(cargoBox);

  // Top Rotating LIDAR Puck
  const lidarPuck = new THREE.Mesh(
    new THREE.CylinderGeometry(0.05, 0.05, 0.06, 16),
    new THREE.MeshStandardMaterial({ color: 0x0284c7, metalness: 0.9, roughness: 0.1 })
  );
  lidarPuck.position.set(0, 0.36, -0.32);
  root.add(lidarPuck);

  return root;
}

// 2. Build ATR-600 (Articulated Robotic Arm AMR - Manipulator Arm & Tote)
function buildATR600Mesh(robot, colorHex) {
  const root = new THREE.Group();

  const chassisWhiteMat = new THREE.MeshStandardMaterial({
    color: 0xe2e8f0,
    metalness: 0.4,
    roughness: 0.3,
  });
  const skirtDarkMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, metalness: 0.6, roughness: 0.4 });
  const armJointMat = new THREE.MeshStandardMaterial({ color: 0x0284c7, metalness: 0.8, roughness: 0.2 });
  const armLinkMat = new THREE.MeshStandardMaterial({ color: 0xf8fafc, metalness: 0.3, roughness: 0.2 });

  // Chassis Base
  const base = new THREE.Mesh(new THREE.BoxGeometry(0.76, 0.24, 0.96), chassisWhiteMat);
  base.position.y = 0.23;
  base.castShadow = true;
  root.add(base);

  // Continuous Rubber Treads
  const rubberMat = new THREE.MeshStandardMaterial({ color: 0x0f172a, roughness: 0.9 });
  for (const side of [-0.42, 0.42]) {
    const track = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.2, 0.98), rubberMat);
    track.position.set(side, 0.13, 0);
    track.castShadow = true;
    root.add(track);
  }

  // Cyan LED Strip
  const light = new THREE.Mesh(
    new THREE.BoxGeometry(0.64, 0.04, 0.04),
    new THREE.MeshBasicMaterial({ color: 0x00f0ff })
  );
  light.position.set(0, 0.22, 0.49);
  root.add(light);

  // Front Label ("ATR-600")
  const plateCanvas = document.createElement("canvas");
  plateCanvas.width = 128;
  plateCanvas.height = 32;
  const pCtx = plateCanvas.getContext("2d");
  pCtx.fillStyle = "#0f172a";
  pCtx.fillRect(0, 0, 128, 32);
  pCtx.fillStyle = "#38bdf8";
  pCtx.font = "bold 16px monospace";
  pCtx.textAlign = "center";
  pCtx.textBaseline = "middle";
  pCtx.fillText("ATR-600", 64, 16);
  const plateTex = new THREE.CanvasTexture(plateCanvas);
  const plateMesh = new THREE.Mesh(
    new THREE.PlaneGeometry(0.36, 0.09),
    new THREE.MeshBasicMaterial({ map: plateTex })
  );
  plateMesh.position.set(0, 0.22, 0.495);
  root.add(plateMesh);

  // Articulated Robotic Arm Assembly (Turret -> Shoulder -> Elbow -> Forearm -> Gripper)
  const armGroup = new THREE.Group();
  armGroup.position.set(0, 0.36, 0.1);

  // Base Rotating Turret
  const turret = new THREE.Mesh(new THREE.CylinderGeometry(0.16, 0.18, 0.12, 24), armJointMat);
  turret.position.y = 0.06;
  armGroup.add(turret);

  // Shoulder Joint
  const shoulder = new THREE.Mesh(new THREE.SphereGeometry(0.12, 16, 16), armJointMat);
  shoulder.position.y = 0.18;
  armGroup.add(shoulder);

  // Lower Boom Arm
  const boom = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.08, 0.6, 16), armLinkMat);
  boom.position.set(0, 0.44, -0.1);
  boom.rotation.x = -0.4;
  armGroup.add(boom);

  // Elbow Joint
  const elbow = new THREE.Mesh(new THREE.SphereGeometry(0.09, 16, 16), armJointMat);
  elbow.position.set(0, 0.68, -0.22);
  armGroup.add(elbow);

  // Forearm Link
  const forearm = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, 0.55, 16), armLinkMat);
  forearm.position.set(0, 0.85, 0.02);
  forearm.rotation.x = 0.8;
  armGroup.add(forearm);

  // Gripper Wrist & Clamp Fingers
  const wrist = new THREE.Mesh(new THREE.BoxGeometry(0.14, 0.08, 0.1), armJointMat);
  wrist.position.set(0, 1.02, 0.24);
  armGroup.add(wrist);

  // Tote Box being held / manipulated by the arm (Matching Reference Photo)
  const toteMat = new THREE.MeshStandardMaterial({ color: 0x3b82f6, roughness: 0.4 });
  const heldTote = new THREE.Mesh(new THREE.BoxGeometry(0.42, 0.28, 0.38), toteMat);
  heldTote.position.set(0, 0.98, 0.48);
  heldTote.castShadow = true;
  armGroup.add(heldTote);

  root.add(armGroup);
  root.userData.armGroup = armGroup;

  return root;
}

// --- Dynamic Laser Path Guidance Lines ---
function updateLaserPath(robotId, currentPos, pathPoints, colorHex) {
  const lineName = `laser_${robotId}`;
  let lineMesh = lasersGroup.getObjectByName(lineName);

  if (!showLasers || !pathPoints || pathPoints.length === 0) {
    if (lineMesh) lineMesh.visible = false;
    return;
  }

  const points = [
    new THREE.Vector3(currentPos.x, 0.04, currentPos.z),
    ...pathPoints.map(p => new THREE.Vector3(p[0] + 0.5, 0.04, p[1] + 0.5)),
  ];

  const curve = new THREE.CatmullRomCurve3(points);
  const samplePoints = curve.getPoints(points.length * 4);
  const geo = new THREE.BufferGeometry().setFromPoints(samplePoints);

  if (!lineMesh) {
    const mat = new THREE.LineDashedMaterial({
      color: colorHex || 0x00f0ff,
      linewidth: 3,
      scale: 1,
      dashSize: 0.3,
      gapSize: 0.15,
      transparent: true,
      opacity: 0.85,
    });
    lineMesh = new THREE.Line(geo, mat);
    lineMesh.name = lineName;
    lineMesh.computeLineDistances();
    lasersGroup.add(lineMesh);
  } else {
    lineMesh.geometry.dispose();
    lineMesh.geometry = geo;
    lineMesh.computeLineDistances();
    lineMesh.visible = true;
  }
}

// --- Floating 3D Holographic HUD System ---
function updateHUDPlacards(robots) {
  if (!showHUDs) {
    hudOverlayLayer.innerHTML = "";
    return;
  }

  const width = canvasWrap.clientWidth;
  const height = canvasWrap.clientHeight;
  const tempV = new THREE.Vector3();

  let html = "";
  robots.forEach((r, idx) => {
    const rData = robotMeshes.get(r.robot_id);
    if (!rData) return;

    // Get 3D head position above robot
    tempV.copy(rData.currentPos);
    tempV.y += (r.model === "ATR-600" ? 1.8 : 1.3);

    // Project 3D coordinate to 2D screen coordinate
    tempV.project(camera);

    // Check if behind camera
    if (tempV.z > 1.0) return;

    const screenX = (tempV.x * 0.5 + 0.5) * width;
    const screenY = (-(tempV.y * 0.5) + 0.5) * height;

    const isSelected = selectedRobotId === r.robot_id;
    const b = Math.max(0, Math.min(100, Number(r.battery || 0)));
    const speed = Number(r.speed_mps || 0).toFixed(1);
    const payload = Number(r.payload_kg || 0).toFixed(1);
    const status = String(r.status || "idle");
    const taskStage = String(r.task_stage || "standby");

    html += `
      <div class="hud-card ${isSelected ? "selected" : ""}" 
           style="left:${screenX}px; top:${screenY}px;"
           onclick="selectRobot('${r.robot_id}')">
        <div class="hud-title">
          <span>${escapeHtml(r.model || "ATR-400")} #${escapeHtml(String(r.robot_id).replace("robot-", ""))}</span>
          <span class="badge-model">${escapeHtml(r.model || "AMR")}</span>
        </div>
        <div class="hud-row">
          <span>Status:</span>
          <span class="hud-val status-${status}">${escapeHtml(status.toUpperCase())}</span>
        </div>
        <div class="hud-row">
          <span>Task:</span>
          <span class="hud-val">${escapeHtml(taskStage)}</span>
        </div>
        <div class="hud-row">
          <span>Speed:</span>
          <span class="hud-val">${speed} m/s</span>
        </div>
        <div class="hud-row">
          <span>Battery:</span>
          <span class="hud-val">${b.toFixed(0)}%</span>
        </div>
      </div>
    `;
  });

  hudOverlayLayer.innerHTML = html;
}

// --- Main Render & Smooth Interpolation Loop (60 FPS) ---
let lastTime = performance.now();

function animate(time) {
  requestAnimationFrame(animate);

  const delta = (time - lastTime) / 1000;
  lastTime = time;

  // Smoothly interpolate each robot towards its server target position & heading
  robotMeshes.forEach((rData, robotId) => {
    const lerpFactor = Math.min(1, delta * 12);

    // Smooth position lerp
    rData.currentPos.lerp(rData.targetPos, lerpFactor);
    rData.group.position.copy(rData.currentPos);

    // Smooth heading slerp
    let diffRot = rData.targetRot - rData.currentRot;
    // Normalize to [-PI, PI]
    while (diffRot < -Math.PI) diffRot += Math.PI * 2;
    while (diffRot > Math.PI) diffRot -= Math.PI * 2;
    rData.currentRot += diffRot * lerpFactor;
    rData.group.rotation.y = rData.currentRot;

    // Subtle robotic arm idle/reach animation for ATR-600
    if (rData.group.userData.armGroup) {
      const arm = rData.group.userData.armGroup;
      arm.rotation.y = Math.sin(time * 0.003 + robotId.charCodeAt(robotId.length - 1)) * 0.15;
    }
  });

  // Camera Following Mode (Chase Cam)
  if (cameraMode === "follow" && selectedRobotId) {
    const sel = robotMeshes.get(selectedRobotId);
    if (sel) {
      const targetCamPos = new THREE.Vector3(
        sel.currentPos.x - Math.sin(sel.currentRot) * 9,
        sel.currentPos.y + 7,
        sel.currentPos.z - Math.cos(sel.currentRot) * 9
      );
      camera.position.lerp(targetCamPos, 0.06);
      controls.target.lerp(sel.currentPos, 0.08);
    }
  }

  controls.update();
  renderer.render(scene, camera);

  // Update floating HUD overlays in 2D perspective
  if (currentFleetState && currentFleetState.robots) {
    updateHUDPlacards(currentFleetState.robots);
  }
}

// --- Sync State Received from WebSocket / API ---
function syncFleetState(state) {
  currentFleetState = state;

  // Initialize or update warehouse grid geometry if first message
  if (!gridData.cells || gridData.cells.length === 0 || gridData.width !== state.grid.width) {
    gridData = state.grid;
    buildWarehouse(gridData);
    populateLocationDropdowns(gridData);
  }

  // Update top metrics & sidebar counts
  renderTelemetry(state);

  // Sync 3D Robots
  const activeIds = new Set();
  (state.robots || []).forEach((r, idx) => {
    activeIds.add(r.robot_id);
    const colorHex = AMR_COLORS[idx % AMR_COLORS.length];

    let rData = robotMeshes.get(r.robot_id);
    if (!rData) {
      // Build 3D mesh
      const group = (r.model === "ATR-600")
        ? buildATR600Mesh(r, colorHex)
        : buildATR400Mesh(r, colorHex);

      group.position.set(r.position[0] + 0.5, 0, r.position[1] + 0.5);
      robotsGroup.add(group);

      rData = {
        group,
        model: r.model || "ATR-400",
        currentPos: group.position.clone(),
        targetPos: new THREE.Vector3(r.position[0] + 0.5, 0, r.position[1] + 0.5),
        currentRot: -r.heading_degrees * (Math.PI / 180),
        targetRot: -r.heading_degrees * (Math.PI / 180),
        colorHex,
      };
      robotMeshes.set(r.robot_id, rData);
    } else {
      // Update target pos & rot
      rData.targetPos.set(r.position[0] + 0.5, 0, r.position[1] + 0.5);
      rData.targetRot = -r.heading_degrees * (Math.PI / 180);
    }

    // Update laser paths
    updateLaserPath(r.robot_id, rData.currentPos, r.path, colorHex);
  });

  // Remove decommissioned robots
  robotMeshes.forEach((rData, robotId) => {
    if (!activeIds.has(robotId)) {
      robotsGroup.remove(rData.group);
      const laserMesh = lasersGroup.getObjectByName(`laser_${robotId}`);
      if (laserMesh) lasersGroup.remove(laserMesh);
      robotMeshes.delete(robotId);
    }
  });

  // If a robot is selected, update inspector
  if (selectedRobotId) {
    const sel = (state.robots || []).find(r => r.robot_id === selectedRobotId);
    if (sel) updateInspector(sel);
  }
}

// --- Telemetry, Metrics & Sidebar Rendering ---
function renderTelemetry(state) {
  const metrics = state.metrics || {};
  const robots = state.robots || [];
  const tasks = state.tasks || [];

  // Header badges
  document.querySelector("#header-active-count").textContent = robots.length;
  document.querySelector("#robot-count").textContent = `${robots.length} ONLINE`;
  document.querySelector("#task-count").textContent = `${tasks.length} QUEUED`;

  // Performance metrics
  document.querySelector("#completed").textContent = metrics.completed ?? 0;
  document.querySelector("#collisions").textContent = metrics.collisions ?? 0;
  document.querySelector("#deadlocks").textContent = metrics.deadlocks ?? 0;
  document.querySelector("#avg-time").textContent = `${Number(metrics.avg_completion_time || 0).toFixed(1)}s`;

  // Render Robots List
  const robotListEl = document.querySelector("#robot-list");
  if (robots.length === 0) {
    robotListEl.innerHTML = `<p class="empty-hint">No active robots in warehouse</p>`;
  } else {
    robotListEl.innerHTML = robots.map((r, i) => {
      const b = Math.max(0, Math.min(100, Number(r.battery || 0)));
      const color = AMR_COLORS[i % AMR_COLORS.length];
      const isSelected = r.robot_id === selectedRobotId;
      return `
        <article class="robot-card ${isSelected ? "active" : ""}" onclick="selectRobot('${r.robot_id}')">
          <div class="robot-card-head">
            <span class="robot-card-title" style="color:${color}">
              ${escapeHtml(r.model || "AMR")} · ${escapeHtml(r.robot_id)}
            </span>
            <span class="robot-card-status">${escapeHtml(r.status)}</span>
          </div>
          <div class="battery-track">
            <div class="battery-fill" style="width:${b}%; background:${b < 25 ? "#ef4444" : color}"></div>
          </div>
          <div class="battery-label">
            <span>Battery Health</span>
            <span>${b.toFixed(1)}%</span>
          </div>
          <div class="robot-card-meta">
            <span>Speed: <b>${Number(r.speed_mps || 0).toFixed(1)} m/s</b></span>
            <span>Payload: <b>${Number(r.payload_kg || 0).toFixed(1)} kg</b></span>
            <span>Stage: <b>${escapeHtml(r.task_stage || "idle")}</b></span>
            <span>Pos: <b>(${r.position[0]}, ${r.position[1]})</b></span>
          </div>
        </article>
      `;
    }).join("");
  }

  // Render Task List
  const taskListEl = document.querySelector("#task-list");
  if (tasks.length === 0) {
    taskListEl.innerHTML = `<p class="empty-hint">No queued transport missions</p>`;
  } else {
    taskListEl.innerHTML = tasks.map(t => {
      const pClass = `p${t.priority || 2}`;
      return `
        <article class="task-card">
          <div class="task-main">
            <strong>${escapeHtml(t.item_name || t.id)}</strong>
            <span>Pickup: (${t.pickup.join(",")}) → Drop: (${t.dropoff.join(",")})</span>
            <div><small style="color:#38bdf8">${t.assigned_to ? "Assigned to " + escapeHtml(t.assigned_to) : "In Auction"}</small></div>
          </div>
          <span class="task-priority-tag ${pClass}">P${t.priority || 2}</span>
        </article>
      `;
    }).join("");
  }
}

// --- Inspector Drawer ---
function selectRobot(robotId) {
  selectedRobotId = robotId;
  const drawer = document.querySelector("#inspector-drawer");
  drawer.classList.remove("hidden");

  // Highlight in sidebar
  document.querySelectorAll(".robot-card").forEach(c => c.classList.remove("active"));

  if (currentFleetState) {
    const r = (currentFleetState.robots || []).find(x => x.robot_id === robotId);
    if (r) {
      updateInspector(r);
      document.querySelector("#followed-robot-name").textContent = `TRACKING: ${r.model} #${r.robot_id}`;
    }
  }

  // Smoothly center camera target on selected robot
  const rData = robotMeshes.get(robotId);
  if (rData && cameraMode === "follow") {
    controls.target.copy(rData.currentPos);
  }
}

function updateInspector(robot) {
  document.querySelector("#insp-model").textContent = robot.model || "ATR-400";
  document.querySelector("#insp-name").textContent = robot.robot_id;
  document.querySelector("#insp-status").textContent = robot.status;
  document.querySelector("#insp-task").textContent = robot.task_stage || "Standby";
  document.querySelector("#insp-speed").textContent = `${Number(robot.speed_mps || 0).toFixed(1)} m/s`;
  const b = Math.max(0, Math.min(100, Number(robot.battery || 0)));
  document.querySelector("#insp-battery-fill").style.width = `${b}%`;
  document.querySelector("#insp-battery-text").textContent = `${b.toFixed(0)}%`;
  document.querySelector("#insp-payload").textContent = `${Number(robot.payload_kg || 0).toFixed(1)} kg`;
  document.querySelector("#insp-pos").textContent = `(${robot.position[0]}, ${robot.position[1]})`;
}

// --- Interactive Click Raycasting ---
function setupInteraction() {
  const raycaster = new THREE.Raycaster();
  const mouse = new THREE.Vector2();

  canvas.addEventListener("pointerdown", (event) => {
    // Only primary click
    if (event.button !== 0) return;

    const rect = canvas.getBoundingClientRect();
    mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);
    const intersects = raycaster.intersectObjects(robotsGroup.children, true);

    if (intersects.length > 0) {
      // Find top group
      let hit = intersects[0].object;
      while (hit.parent && hit.parent !== robotsGroup) {
        hit = hit.parent;
      }
      // Look up robot id
      for (const [rid, rData] of robotMeshes.entries()) {
        if (rData.group === hit) {
          selectRobot(rid);
          break;
        }
      }
    }
  });
}

// --- Camera Modes & Controls ---
function setCameraMode(mode) {
  cameraMode = mode;
  document.querySelectorAll(".btn-cam").forEach(b => {
    b.classList.toggle("active", b.dataset.cam === mode);
  });

  const w = gridData.width || 30;
  const h = gridData.height || 20;

  if (mode === "overview") {
    // Classic isometric warehouse digital twin
    gsapAnimateCam(w * 0.5, 26, h * 1.6, w * 0.5, 0, h * 0.5);
  } else if (mode === "topdown") {
    // Tactical top-down view
    gsapAnimateCam(w * 0.5, 42, h * 0.5 + 0.1, w * 0.5, 0, h * 0.5);
  } else if (mode === "workstation") {
    // Close-up on conveyor and packing dock
    gsapAnimateCam(6, 6, 8, 2.5, 1, 3.5);
  } else if (mode === "follow") {
    if (!selectedRobotId && currentFleetState?.robots?.length > 0) {
      selectRobot(currentFleetState.robots[0].robot_id);
    }
  }
}

function gsapAnimateCam(tx, ty, tz, lx, ly, lz) {
  // Smoothly move camera
  const startPos = camera.position.clone();
  const startTarget = controls.target.clone();
  const endPos = new THREE.Vector3(tx, ty, tz);
  const endTarget = new THREE.Vector3(lx, ly, lz);

  const startTime = performance.now();
  const dur = 800; // ms

  function step() {
    const elapsed = performance.now() - startTime;
    const t = Math.min(1, elapsed / dur);
    const ease = t * (2 - t); // Ease out

    camera.position.lerpVectors(startPos, endPos, ease);
    controls.target.lerpVectors(startTarget, endTarget, ease);

    if (t < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

// --- Window Resize Handler ---
function onWindowResize() {
  if (!canvasWrap || !camera || !renderer) return;
  const width = canvasWrap.clientWidth;
  const height = canvasWrap.clientHeight;
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
  renderer.setSize(width, height);
}

// --- WebSocket Connection ---
function connectWebSocket() {
  const protocol = location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${protocol}://${location.host}/ws`);
  const badge = document.querySelector("#connection");
  const textEl = badge.querySelector(".status-text");

  socket.addEventListener("open", () => {
    badge.className = "connection online";
    textEl.textContent = "Live Telemetry";
  });

  socket.addEventListener("message", (event) => {
    try {
      const state = JSON.parse(event.data);
      syncFleetState(state);
    } catch (e) {
      console.error("Error parsing websocket message:", e);
    }
  });

  socket.addEventListener("close", () => {
    badge.className = "connection offline";
    textEl.textContent = "Reconnecting";
    setTimeout(connectWebSocket, 1000);
  });

  socket.addEventListener("error", () => {
    socket.close();
  });
}

// --- Modal & REST API Actions ---
function setupUIEvents() {
  // Modal toggles
  document.querySelector("#btn-open-add-robot").addEventListener("click", () => {
    document.querySelector("#modal-add-robot").classList.remove("hidden");
  });
  document.querySelector("#btn-open-add-task").addEventListener("click", () => {
    // Populate robot assignee list
    const select = document.querySelector("#task-assign-select");
    select.innerHTML = `<option value="">Auto Decentralized Auction</option>`;
    if (currentFleetState?.robots) {
      currentFleetState.robots.forEach(r => {
        select.innerHTML += `<option value="${r.robot_id}">${r.model} · ${r.robot_id}</option>`;
      });
    }
    document.querySelector("#modal-add-task").classList.remove("hidden");
  });

  document.querySelectorAll(".modal-close").forEach(btn => {
    btn.addEventListener("click", (e) => {
      const modalId = e.currentTarget.dataset.modal;
      document.querySelector(`#${modalId}`).classList.add("hidden");
    });
  });

  // Close modal when clicking outside
  document.querySelectorAll(".modal-backdrop").forEach(backdrop => {
    backdrop.addEventListener("click", (e) => {
      if (e.target === backdrop) backdrop.classList.add("hidden");
    });
  });

  // Add Robot Form Submission
  document.querySelector("#form-add-robot").addEventListener("submit", async (e) => {
    e.preventDefault();
    const model = document.querySelector('input[name="robot_model"]:checked').value;
    const idInput = document.querySelector("#robot-id-input").value.trim();
    const battery = parseFloat(document.querySelector("#robot-battery-input").value) || 100;
    const spawnType = document.querySelector("#robot-spawn-select").value;

    let pos = null;
    if (spawnType === "dock1") pos = [1, 1];
    else if (spawnType === "dock2") pos = [1, 2];
    else if (spawnType === "dock3") pos = [2, 1];
    else if (spawnType === "custom") {
      pos = [
        parseInt(document.querySelector("#robot-x").value, 10) || 5,
        parseInt(document.querySelector("#robot-y").value, 10) || 5,
      ];
    }

    try {
      const res = await fetch("/api/robots", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: model,
          battery: battery,
          id: idInput || null,
          pos: pos,
        }),
      });
      const data = await res.json();
      if (data.status === "ok") {
        document.querySelector("#modal-add-robot").classList.add("hidden");
        selectRobot(data.robot.robot_id);
      }
    } catch (err) {
      console.error("Failed to add robot:", err);
    }
  });

  // Spawn location custom coords toggle
  document.querySelector("#robot-spawn-select").addEventListener("change", (e) => {
    document.querySelector("#custom-coords-row").classList.toggle("hidden", e.target.value !== "custom");
  });

  // Add Task Form Submission
  document.querySelector("#form-add-task").addEventListener("submit", async (e) => {
    e.preventDefault();
    const cargo = document.querySelector("#task-cargo-input").value.trim() || "AMZ-BOX-A12";
    const priority = parseInt(document.querySelector("#task-priority-select").value, 10) || 2;
    const assignedTo = document.querySelector("#task-assign-select").value || null;
    const pickupVal = document.querySelector("#task-pickup-select").value.split(",").map(Number);
    const dropoffVal = document.querySelector("#task-dropoff-select").value.split(",").map(Number);

    try {
      const res = await fetch("/api/tasks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          item_name: cargo,
          priority: priority,
          pickup: pickupVal,
          dropoff: dropoffVal,
          assigned_to: assignedTo,
        }),
      });
      const data = await res.json();
      if (data.status === "ok") {
        document.querySelector("#modal-add-task").classList.add("hidden");
      }
    } catch (err) {
      console.error("Failed to create task:", err);
    }
  });

  // Cargo preset chips
  document.querySelectorAll(".cargo-chips .chip").forEach(chip => {
    chip.addEventListener("click", () => {
      document.querySelectorAll(".cargo-chips .chip").forEach(c => c.classList.remove("active"));
      chip.classList.add("active");
      document.querySelector("#task-cargo-input").value = chip.dataset.cargo;
    });
  });

  // Quick Task Button
  document.querySelector("#btn-quick-task").addEventListener("click", async () => {
    await fetch("/api/simulation/control", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "random_task" }),
    });
  });

  // Sim Play / Pause Toggle
  document.querySelector("#btn-sim-toggle").addEventListener("click", async () => {
    simPaused = !simPaused;
    document.querySelector("#sim-play-icon").textContent = simPaused ? "▶" : "⏸";
    await fetch("/api/simulation/control", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: simPaused ? "pause" : "resume" }),
    });
  });

  // Speed selector
  document.querySelectorAll(".btn-speed").forEach(btn => {
    btn.addEventListener("click", async () => {
      document.querySelectorAll(".btn-speed").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const speed = parseFloat(btn.dataset.speed);
      await fetch("/api/simulation/control", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "speed", speed: speed }),
      });
    });
  });

  // Camera preset buttons
  document.querySelectorAll(".btn-cam").forEach(btn => {
    btn.addEventListener("click", () => setCameraMode(btn.dataset.cam));
  });

  // Visual Overlay Toggles
  document.querySelector("#toggle-hud").addEventListener("change", (e) => {
    showHUDs = e.target.checked;
    if (!showHUDs) hudOverlayLayer.innerHTML = "";
  });
  document.querySelector("#toggle-lasers").addEventListener("change", (e) => {
    showLasers = e.target.checked;
    lasersGroup.visible = showLasers;
  });

  // Inspector Drawer Close & Actions
  document.querySelector("#btn-close-inspector").addEventListener("click", () => {
    document.querySelector("#inspector-drawer").classList.add("hidden");
    selectedRobotId = null;
    document.querySelectorAll(".robot-card").forEach(c => c.classList.remove("active"));
  });

  document.querySelector("#btn-insp-follow").addEventListener("click", () => {
    setCameraMode("follow");
  });

  document.querySelector("#btn-insp-decommission").addEventListener("click", async () => {
    if (!selectedRobotId) return;
    try {
      await fetch(`/api/robots/${selectedRobotId}`, { method: "DELETE" });
      document.querySelector("#inspector-drawer").classList.add("hidden");
      selectedRobotId = null;
    } catch (err) {
      console.error("Failed to decommission robot:", err);
    }
  });
}

function populateLocationDropdowns(grid) {
  const pickupSel = document.querySelector("#task-pickup-select");
  const dropoffSel = document.querySelector("#task-dropoff-select");
  const w = grid.width;
  const h = grid.height;

  pickupSel.innerHTML = `
    <option value="1,1">Inbound Dock 1 (1, 1)</option>
    <option value="1,2">Inbound Dock 2 (1, 2)</option>
    <option value="2,1">Workstation Buffer (2, 1)</option>
    <option value="${Math.floor(w/3)},${Math.floor(h/2)}">Aisle 12 Shelf Bay A</option>
    <option value="${Math.floor(w*0.6)},${Math.floor(h/2)}">Aisle 14 Shelf Bay B</option>
  `;

  dropoffSel.innerHTML = `
    <option value="${w-2},${h-2}">Outbound Delivery Bay 1 (${w-2}, ${h-2})</option>
    <option value="${w-3},${h-2}">Outbound Delivery Bay 2 (${w-3}, ${h-2})</option>
    <option value="${w-2},${h-3}">Outbound Delivery Bay 3 (${w-2}, ${h-3})</option>
    <option value="${Math.floor(w/2)},${Math.floor(h/2)}">Central Sorting Conveyor</option>
  `;
}

function escapeHtml(value) {
  const e = document.createElement("span");
  e.textContent = String(value ?? "");
  return e.innerHTML;
}

// --- Initialization ---
window.addEventListener("DOMContentLoaded", () => {
  init3D();
  setupUIEvents();
  connectWebSocket();
});
