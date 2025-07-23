// Room dimensions (moved to top to avoid ReferenceError)
const ROOM_WIDTH = 6; // Reduced from 8
const ROOM_LENGTH = 6; // Reduced from 8
const ROOM_HEIGHT = 5; // Reduced from 7

// Scene setup
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x1a1a1a); // Dark background
const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.shadowMap.enabled = true;
document.body.appendChild(renderer.domElement);

// Hide loading screen after setup
const loadingScreen = document.getElementById('loading-screen');
if (loadingScreen) loadingScreen.style.display = 'none';

// Controls setup
const controls = new THREE.PointerLockControls(camera, document.body);
scene.add(controls.getObject());

// Lighting
const ambientLight = new THREE.AmbientLight(0xffffff, 0.7); // Brighter ambient
scene.add(ambientLight);

const directionalLight = new THREE.DirectionalLight(0xffffff, 0.7);
directionalLight.position.set(5, 10, 5);
directionalLight.castShadow = true;
directionalLight.shadow.mapSize.width = 2048;
directionalLight.shadow.mapSize.height = 2048;
scene.add(directionalLight);

// Brighter ceiling light
const ceilingLight = new THREE.PointLight(0xffffff, 2.5, 30);
ceilingLight.position.set(0, ROOM_HEIGHT - 0.3, 0);
ceilingLight.castShadow = true;
scene.add(ceilingLight);

// Laboratory floor and walls
const floorGeometry = new THREE.PlaneGeometry(ROOM_WIDTH, ROOM_LENGTH);
const floorMaterial = new THREE.MeshStandardMaterial({ 
    color: 0x2c2c2c, // Darker floor
    roughness: 0.8,
    metalness: 0.2
});
const floor = new THREE.Mesh(floorGeometry, floorMaterial);
floor.rotation.x = -Math.PI / 2;
floor.receiveShadow = true;
scene.add(floor);

// Create walls
function createWall(width, height, depth, x, y, z, rotation = 0) {
    const geometry = new THREE.BoxGeometry(width, height, depth);
    const material = new THREE.MeshStandardMaterial({ 
        color: 0x333333, // Darker walls
        roughness: 0.7,
        metalness: 0.1
    });
    const wall = new THREE.Mesh(geometry, material);
    wall.position.set(x, y, z);
    wall.rotation.y = rotation;
    wall.castShadow = true;
    wall.receiveShadow = true;
    scene.add(wall);
}

// Create smaller laboratory walls
createWall(ROOM_WIDTH, ROOM_HEIGHT, 0.2, 0, ROOM_HEIGHT/2, -ROOM_LENGTH/2); // Back wall
createWall(ROOM_WIDTH, ROOM_HEIGHT, 0.2, 0, ROOM_HEIGHT/2, ROOM_LENGTH/2); // Front wall
createWall(0.2, ROOM_HEIGHT, ROOM_LENGTH, -ROOM_WIDTH/2, ROOM_HEIGHT/2, 0); // Left wall
createWall(0.2, ROOM_HEIGHT, ROOM_LENGTH, ROOM_WIDTH/2, ROOM_HEIGHT/2, 0); // Right wall

// Add roof
const roofGeometry = new THREE.PlaneGeometry(ROOM_WIDTH, ROOM_LENGTH);
const roofMaterial = new THREE.MeshStandardMaterial({ 
    color: 0x333333, // Same color as walls
    roughness: 0.7,
    metalness: 0.1
});
const roof = new THREE.Mesh(roofGeometry, roofMaterial);
roof.rotation.x = Math.PI / 2; // Rotate to be horizontal
roof.position.y = ROOM_HEIGHT; // Position at top of walls
roof.receiveShadow = true;
scene.add(roof);

// Oralyzer device group
const deviceGroup = new THREE.Group();
deviceGroup.scale.set(0.08, 0.08, 0.08); // Hand-sized
// Floating in the center of the room, above the floor
deviceGroup.position.set(0, 0.7, 0);
scene.add(deviceGroup);

// === MAIN BODY: Two-tone (top/sides silver, front/base black) ===
const bodyW = 2.7, bodyH = 2.2, bodyD = 2.1;
const bodyTopGeometry = new THREE.BoxGeometry(bodyW, bodyH, bodyD);
const bodyTopMaterial = new THREE.MeshPhysicalMaterial({ 
    color: 0xe6e7ea, 
    metalness: 0.85, 
    roughness: 0.18, 
    clearcoat: 0.7, 
    clearcoatRoughness: 0.08 
});
const bodyTop = new THREE.Mesh(bodyTopGeometry, bodyTopMaterial);
bodyTop.position.set(0, bodyH / 2, 0);
deviceGroup.add(bodyTop);

// Front/base (black)
const bodyFrontGeometry = new THREE.BoxGeometry(bodyW, bodyH, bodyD);
const bodyFrontMaterial = new THREE.MeshPhysicalMaterial({ 
    color: 0xe6e7ea, 
    metalness: 0, 
    roughness: 1, 
    clearcoat: 0, 
    clearcoatRoughness: 0 
});
const bodyFront = new THREE.Mesh(bodyFrontGeometry, bodyFrontMaterial);
bodyFront.position.set(0, bodyH / 2, 0);
bodyFront.scale.set(1.01, .01, 0.51);
bodyFront.position.z += bodyD * 0.05;
bodyFront.rotation.x = -Math.PI / 4;
deviceGroup.add(bodyFront);

// === SLANTED FRONT FACE (bezel, glossy black) ===
const faceW = 2.5, faceH = 1.2, faceD = 0.08, faceSlant = Math.PI / 7.5;
const faceGeometry = new THREE.BoxGeometry(faceW, faceH, faceD);
const faceMaterial = new THREE.MeshPhysicalMaterial({ 
    color: 0x181a23, 
    metalness: 0.85, 
    roughness: 0.12, 
    clearcoat: 1, 
    clearcoatRoughness: 0.05 
});
const face = new THREE.Mesh(faceGeometry, faceMaterial);
face.position.set(0, bodyH * 0.70, bodyD / 2 + faceD / 2 + .10);
face.rotation.x = -faceSlant;
deviceGroup.add(face);

// === SCREEN (for live UI overlay) ===
const screenW = 1.75, screenH = 0.8, screenD = 0.021; // Match oralyzer_clean.html
const screenGeometry = new THREE.BoxGeometry(screenW, screenH, screenD);
const screenOnMaterial = new THREE.MeshPhysicalMaterial({ 
    color: 0x181a23, 
    metalness: 0.2, 
    roughness: 0.1, 
    emissive: 0x1e90ff, 
    emissiveIntensity: 0.18,
    transparent: true,
    opacity: 0.95
});
const screenOffMaterial = new THREE.MeshPhysicalMaterial({ 
    color: 0x181a23, 
    metalness: 0.2, 
    roughness: 0.1, 
    emissive: 0x000000, 
    emissiveIntensity: 0,
    transparent: true,
    opacity: 0.95
});
const screenMesh = new THREE.Mesh(screenGeometry, screenOnMaterial); // Start with screen on
screenMesh.position.set(0, 0, faceD / 2 + screenD / 2 - 0.015);
face.add(screenMesh);

// Add screen border
const borderW = screenW + 0.02, borderH = screenH + 0.02, borderD = 0.005;
const borderGeometry = new THREE.BoxGeometry(borderW, borderH, borderD);
const borderMaterial = new THREE.MeshPhysicalMaterial({ 
    color: 0x181a23, 
    metalness: 0.85, 
    roughness: 0.12, 
    clearcoat: 1, 
    clearcoatRoughness: 0.05 
});
const screenBorder = new THREE.Mesh(borderGeometry, borderMaterial);
screenBorder.position.set(0, 0, faceD / 2 + screenD / 2 + borderD / 2 - 0.015);
face.add(screenBorder);

// === DOM Overlay for Main Menu ===
const screenUI = document.getElementById('screen-ui');
screenUI.style.position = 'absolute';
screenUI.style.pointerEvents = 'none';
screenUI.style.zIndex = '1000';

// Power state
let powerOn = false; // Start with screen off

function getScreenUIHTML() {
    return `
    <div id="screen-ui-inner" style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;overflow:hidden;">
      <div id="screen-ui-main" style="position:relative;display:flex;flex-direction:column;width:700px;height:420px;background:linear-gradient(90deg,#2562b4 0%,#3fa9f5 100%);border-radius:24px;box-shadow:0 2px 24px #0004;overflow:hidden;">
        <div style="display:flex;flex-direction:row;width:100%;height:100%;">
          <div style='display:flex;flex-direction:column;align-items:flex-start;justify-content:center;width:40%;height:100%;padding:2.5em 1.2em 2.5em 2.2em;gap:1.1em;background:rgba(37,98,180,0.98);border-radius:24px 0 0 24px;'>
            <div style="display:flex;align-items:center;gap:0.7em;font-weight:bold;font-size:1.15em;color:#fff;letter-spacing:0.5px;margin-bottom:0.7em;">ADMIN</div>
            <button class='screen-btn' id='order-list-btn'><span class="menu-icon"><svg class="lower" width="28" height="28" viewBox="0 0 28 28"><circle cx="6" cy="22" r="4" fill="#fff"/><circle cx="22" cy="22" r="4" fill="#fff"/><circle cx="14" cy="6" r="4" fill="#fff"/><line x1="14" y1="6" x2="6" y2="22" stroke="#fff" stroke-width="3"/><line x1="14" y1="6" x2="22" y2="22" stroke="#fff" stroke-width="3"/></svg></span>Order List</button>
            <button class='screen-btn' id='results-btn'><span class="menu-icon"><svg class="lower" width="24" height="24" viewBox="0 0 24 24"><circle cx="6" cy="6" r="2" fill="#fff"/><circle cx="12" cy="6" r="2" fill="#fff"/><circle cx="18" cy="6" r="2" fill="#fff"/><circle cx="6" cy="12" r="2" fill="#fff"/><circle cx="12" cy="12" r="2" fill="#fff"/><circle cx="18" cy="12" r="2" fill="#fff"/><circle cx="6" cy="18" r="2" fill="#fff"/><circle cx="12" cy="18" r="2" fill="#fff"/><circle cx="18" cy="18" r="2" fill="#fff"/></svg></span>Results</button>
            <button class='screen-btn' id='system-btn'><span class="menu-icon">&#9881;</span>System</button>
            <button class='screen-btn disabled' id='logout-btn' disabled><span class="menu-icon">&#x23CF;</span>Log Out</button>
          </div>
          <div style='flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;position:relative;height:100%;background:transparent;'>
            <div style="position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);width:80%;height:80%;background:radial-gradient(circle at 60% 40%, #3fa9f5 60%, #2562b4 100%);border-radius:50%;z-index:0;"></div>
            <button class='start-btn' id='start-test-btn' style="position:relative;z-index:1;background:transparent;color:#2562b4;border:4px solid #fff;box-shadow:none;">START<br><span style="font-size:0.85em;font-weight:400;">NEW TEST</span></button>
          </div>
        </div>
        <div style='position:absolute;top:1.2em;left:2.2em;right:2.2em;display:flex;flex-direction:row;align-items:center;justify-content:space-between;color:#fff;font-size:1.08em;font-weight:bold;z-index:2;'>
          <span style="display:flex;align-items:center;gap:0.5em;">ADMIN</span>
          <span style="display:flex;align-items:center;gap:0.5em;"><svg id="ethernet-icon" width="28" height="28" viewBox="0 0 28 28" style="margin-right:0.5em;vertical-align:middle;"><circle cx="6" cy="22" r="4" fill="#fff"/><circle cx="22" cy="22" r="4" fill="#fff"/><circle cx="14" cy="6" r="4" fill="#fff"/><line x1="14" y1="6" x2="6" y2="22" stroke="#fff" stroke-width="3"/><line x1="14" y1="6" x2="22" y2="22" stroke="#fff" stroke-width="3"/></svg></span>
          <span style="display:flex;align-items:center;gap:0.4em;font-size:0.98em;"><span style="font-size:1.1em;">&#128197;</span> <span id="screen-date">2025-03-28</span></span>
          <span style="display:flex;align-items:center;gap:0.4em;font-size:0.98em;"><span style="font-size:1.1em;">&#128337;</span> <span id="screen-time">09:49:05</span></span>
        </div>
      </div>
    </div>
    `;
}

// Initialize the screen UI and attach handlers
function initializeScreenUI() {
    screenUI.innerHTML = getScreenUIHTML();
    
    // Attach button handlers after UI is initialized
    const orderBtn = document.getElementById('order-list-btn');
    const resultsBtn = document.getElementById('results-btn');
    const systemBtn = document.getElementById('system-btn');
    const logoutBtn = document.getElementById('logout-btn');
    const startTestBtn = document.getElementById('start-test-btn');
    
    if (orderBtn) orderBtn.onclick = () => alert('Order List Clicked');
    if (resultsBtn) resultsBtn.onclick = () => alert('Results Clicked');
    if (systemBtn) systemBtn.onclick = () => alert('System Clicked');
    if (logoutBtn) logoutBtn.onclick = () => alert('Log Out Clicked');
    if (startTestBtn) startTestBtn.onclick = () => alert('Start New Test Clicked');
}

// Update screen UI position and visibility
function updateScreenUIPosition() {
    const rect = renderer.domElement.getBoundingClientRect();
    const sw = screenW, sh = screenH, sd = faceD/2 + screenD/2 - 0.015;
    const corners = [
        new THREE.Vector3(-sw/2,  sh/2, sd),
        new THREE.Vector3( sw/2,  sh/2, sd),
        new THREE.Vector3(-sw/2, -sh/2, sd),
        new THREE.Vector3( sw/2, -sh/2, sd)
    ];
    corners.forEach(v => face.localToWorld(v));
    
    const toScreen = v => {
        v = v.clone().project(camera);
        return {
            x: (v.x + 1) / 2 * rect.width,
            y: (1 - (v.y + 1) / 2) * rect.height
        };
    };
    
    const pts = corners.map(toScreen);
    const minX = Math.min(...pts.map(p => p.x)), maxX = Math.max(...pts.map(p => p.x));
    const minY = Math.min(...pts.map(p => p.y)), maxY = Math.max(...pts.map(p => p.y));
    
    screenUI.style.left = `${rect.left + minX}px`;
    screenUI.style.top = `${rect.top + minY}px`;
    screenUI.style.width = `${maxX - minX}px`;
    screenUI.style.height = `${maxY - minY}px`;
    
    const normal = new THREE.Vector3(0, 0, 1);
    normal.applyQuaternion(face.getWorldQuaternion(new THREE.Quaternion()));
    const screenWorldPos = face.getWorldPosition(new THREE.Vector3());
    const camDir = camera.position.clone().sub(screenWorldPos).normalize();
    const dot = normal.dot(camDir);
    
    let opacity = 0;
    if (dot > 0.2) {
        opacity = Math.min(1, Math.max(0, (dot - 0.2) / 0.7));
        screenUI.style.display = 'block';
    } else {
        screenUI.style.display = 'none';
    }
    screenUI.style.opacity = opacity;
    
    const content = screenUI.firstElementChild;
    if (content) {
        content.style.position = 'absolute';
        content.style.left = '0';
        content.style.top = '0';
        content.style.width = '100%';
        content.style.height = '100%';
        
        const rel = p => `${((p.x - minX) / (maxX - minX) * 100).toFixed(2)}% ${((p.y - minY) / (maxY - minY) * 100).toFixed(2)}%`;
        const poly = [pts[0], pts[1], pts[3], pts[2]].map(rel).join(', ');
        content.style.clipPath = `polygon(${poly})`;
        content.style.webkitClipPath = `polygon(${poly})`;
        
        screenUI.style.pointerEvents = 'none';
        content.style.pointerEvents = 'auto';
        
        const main = content.querySelector('#screen-ui-main');
        if (main) {
            const targetW = 700, targetH = 420, targetAspect = targetW / targetH;
            const boxW = maxX - minX, boxH = maxY - minY, boxAspect = boxW / boxH;
            let scale = boxAspect > targetAspect ? boxH / targetH : boxW / targetW;
            
            main.style.position = 'absolute';
            main.style.left = '50%';
            main.style.top = '50%';
            main.style.transform = `translate(-50%, -50%) scale(${scale})`;
            main.style.width = `${targetW}px`;
            main.style.height = `${targetH}px`;
            main.style.maxWidth = 'none';
            main.style.maxHeight = 'none';
            main.style.transformOrigin = 'center center';
        }
    }
}

// Update screen UI visibility
function updateScreenUIVisibility() {
    if (!powerOn) {
        screenUI.style.display = 'none';
        screenMesh.material = screenOffMaterial;
        return;
    }
    
    const normal = new THREE.Vector3(0, 0, 1);
    normal.applyQuaternion(face.getWorldQuaternion(new THREE.Quaternion()));
    const screenWorldPos = face.getWorldPosition(new THREE.Vector3());
    const camDir = camera.position.clone().sub(screenWorldPos).normalize();
    const dot = normal.dot(camDir);
    
    if (dot > 0.2) {
        screenUI.style.display = 'block';
        screenMesh.material = screenOnMaterial;
    } else {
        screenUI.style.display = 'none';
        screenMesh.material = screenOffMaterial;
    }
}

// Update overlay on resize/animation
window.addEventListener('resize', () => {
    updateScreenUIPosition();
});

// Update after each render
const origAnimate = animate;
animate = function() {
    origAnimate();
    updateScreenUIPosition();
    updateScreenUIVisibility();
};

// === TRAY (with handle/lip and slot) ===
const trayW = 0.9, trayL = 1.35, trayWall = 0.035, trayDepth = 0.18;
const trayShape = new THREE.Shape();
trayShape.moveTo(-trayW/2, 0);
trayShape.lineTo(trayW/2, 0);
trayShape.lineTo(trayW/2, trayL);
trayShape.lineTo(-trayW/2, trayL);
trayShape.lineTo(-trayW/2, 0);
const trayExtrudeSettings = { steps: 1, depth: trayDepth, bevelEnabled: false };
const trayGeometry = new THREE.ExtrudeGeometry(trayShape, trayExtrudeSettings);
const trayMaterial = new THREE.MeshPhysicalMaterial({ color: 0x181a23, metalness: 0.6, roughness: 0.22 });
const tray = new THREE.Mesh(trayGeometry, trayMaterial);
tray.position.set(0, 0.05, bodyD / 2 - 0.01);
tray.rotation.x = -Math.PI / 2;
deviceGroup.add(tray);
// Lip
const lipW = trayW * 0.95, lipH = trayWall * 2.8, lipD = trayWall * 3.2;
const lipGeometry = new THREE.BoxGeometry(lipW, lipH, lipD);
const lipMaterial = new THREE.MeshPhysicalMaterial({ color: 0x23232b, metalness: 0.5, roughness: 0.2, clearcoat: 1 });
const lip = new THREE.Mesh(lipGeometry, lipMaterial);
lip.position.set(0, 0 - lipH / 2 + 0.01, trayDepth / 2 + lipD / 2 - 0.01);
tray.add(lip);

// === LOW POLY SQUARE ===
const squareGroup = new THREE.Group();
squareGroup.scale.set(0.08, 0.08, 0.08); // Match Oralyzer scale
// Position to the left of Oralyzer
squareGroup.position.set(-1.5, 0.7, 0); // 1.5 units to the left of Oralyzer
scene.add(squareGroup);

// Create a simple low-poly square
const squareGeometry = new THREE.BoxGeometry(2, 2, 2);
const squareMaterial = new THREE.MeshPhysicalMaterial({ 
    color: 0x4CAF50, // Green color
    metalness: 0.3,
    roughness: 0.4,
    clearcoat: 0.5
});
const square = new THREE.Mesh(squareGeometry, squareMaterial);
square.position.set(0, 0, 0);
squareGroup.add(square);

// Add some simple details to make it more interesting
const detailGeometry = new THREE.BoxGeometry(0.3, 0.3, 0.3);
const detailMaterial = new THREE.MeshPhysicalMaterial({ 
    color: 0x2E7D32, // Darker green
    metalness: 0.4,
    roughness: 0.3
});

// Add details on each face
const detailPositions = [
    [0, 0, 1.1],  // Front
    [0, 0, -1.1], // Back
    [1.1, 0, 0],  // Right
    [-1.1, 0, 0], // Left
    [0, 1.1, 0],  // Top
    [0, -1.1, 0]  // Bottom
];

detailPositions.forEach(pos => {
    const detail = new THREE.Mesh(detailGeometry, detailMaterial);
    detail.position.set(...pos);
    squareGroup.add(detail);
});

// Add a subtle rotation animation
let squareRotation = 0;
setInterval(() => {
    if (!isOralyzerModalOpen) {
        squareRotation += 0.01;
        squareGroup.rotation.y = squareRotation;
    }
}, 16);

// === POWER BUTTON (with glowing border and icon) ===
const buttonW = 0.44, buttonH = 0.15, buttonD = 0.045, buttonRadius = 0.09;
const buttonGlowGeometry = new THREE.BoxGeometry(buttonW + 0.03, buttonH + 0.03, buttonD + 0.01);
const buttonGlowMaterial = new THREE.MeshPhysicalMaterial({ color: 0x00bfff, metalness: 0.7, roughness: 0.18, emissive: 0x00bfff, emissiveIntensity: 0.32, transparent: true, opacity: 0.22, clearcoat: 1 });
const buttonGlow = new THREE.Mesh(buttonGlowGeometry, buttonGlowMaterial);
buttonGlow.position.set(0, 0.45, bodyD / 2 + buttonD / 2 + 0.004);
deviceGroup.add(buttonGlow);
const buttonGeometry = new THREE.BoxGeometry(buttonW, buttonH, buttonD);
const buttonMaterial = new THREE.MeshPhysicalMaterial({ color: 0xe6e7ea, metalness: 0.7, roughness: 0.16, clearcoat: 1, clearcoatRoughness: 0.06, emissive: 0x22223b, emissiveIntensity: 0.08 });
const button = new THREE.Mesh(buttonGeometry, buttonMaterial);
button.position.set(0, 0.45, bodyD / 2 + buttonD / 2 + 0.01);
deviceGroup.add(button);
// Power icon (simple extruded shape)
const powerIconGeometry = new THREE.TorusGeometry(0.045, 0.01, 8, 32, Math.PI * 1.7);
const powerIconMaterial = new THREE.MeshPhysicalMaterial({ color: 0xffffff, metalness: 0.1, roughness: 0.1, emissive: 0x99eaff, emissiveIntensity: 1.1 });
const powerIcon = new THREE.Mesh(powerIconGeometry, powerIconMaterial);
powerIcon.position.set(0, 0, buttonD / 2 + 0.013);
button.add(powerIcon);

// === ETHERNET PORT (with blinking light) ===
const ethW = 0.19, ethH = 0.19, ethD = 0.13, ethInset = 0.01;
const ethX = bodyW/2 - ethW/2 - 0.10;
const ethY = ethH/2 + 0.10;
const backZ = -bodyD/2;
const ethPortGeo = new THREE.BoxGeometry(ethW, ethH, ethD);
const ethPortMat = new THREE.MeshPhysicalMaterial({ color: 0x181a23, metalness: 0.7, roughness: 0.3, clearcoat: 0.5, clearcoatRoughness: 0.1 });
const ethPort = new THREE.Mesh(ethPortGeo, ethPortMat);
ethPort.position.set(ethX, ethY, backZ + ethD/2 + ethInset);
deviceGroup.add(ethPort);
// Link lights
const lightW = 0.03, lightH = 0.016, lightD = 0.018;
const lightY = ethY + ethH/2 + lightH/2 + 0.004;
const lightZ = backZ + lightD/2 + 0.018;
const greenMat = new THREE.MeshPhysicalMaterial({ color: 0x00ff44, metalness: 0.2, roughness: 0.1, emissive: 0x00ff44, emissiveIntensity: 10.0 });
const greenLight = new THREE.Mesh(new THREE.BoxGeometry(lightW, lightH, lightD), greenMat);
greenLight.position.set(ethX - 0.055, lightY, lightZ);
deviceGroup.add(greenLight);
const yellowMat = new THREE.MeshPhysicalMaterial({ color: 0xffd700, metalness: 0.2, roughness: 0.1, emissive: 0xffd700, emissiveIntensity: 10.0 });
const yellowLight = new THREE.Mesh(new THREE.BoxGeometry(lightW, lightH, lightD), yellowMat);
yellowLight.position.set(ethX + 0.055, lightY, lightZ);
deviceGroup.add(yellowLight);
let yellowOn = true, yellowBlinkTimer = 0, yellowBlinkInterval = 0.2;
function updateEthernetLights(dt) {
    yellowBlinkTimer += dt;
    if (yellowBlinkTimer > yellowBlinkInterval) {
        yellowOn = !yellowOn;
        yellowMat.emissiveIntensity = yellowOn ? 10.0 : 0.08;
        yellowMat.color.setHex(yellowOn ? 0xffd700 : 0x222200);
        yellowBlinkTimer = 0;
        yellowBlinkInterval = 0.08 + Math.random() * 0.5;
    }
}

// === BOBBING ANIMATION (cinematic, freeze/resume on hover) ===
let oralyzerBobbingPhase = 0;
let oralyzerBobbingPaused = false;
let oralyzerBobbingStoredPhase = 0;
let oralyzerBobbingStoredY = deviceGroup.position.y;
let oralyzerBobbingStoredRot = 0;

// Add interval for continuous bobbing
setInterval(() => {
    if (!oralyzerBobbingPaused && !isOralyzerModalOpen) {
        oralyzerBobbingPhase += 0.012; // Slower
        const bobY = oralyzerBaseY + Math.sin(oralyzerBobbingPhase) * 0.06; // Lower amplitude
        const tilt = Math.sin(oralyzerBobbingPhase * 0.7) * 0.04; // Subtle tilt
        deviceGroup.position.y = bobY;
        deviceGroup.rotation.z = tilt;
    } else {
        // Freeze at last position/rotation
        deviceGroup.position.y = oralyzerBobbingStoredY;
        deviceGroup.rotation.z = oralyzerBobbingStoredRot;
    }
}, 16); // ~60fps

// === GLOWING ACCENT LINES (bright cyan/blue) ===
const outlinePoints = [
    new THREE.Vector3(-faceW/2 + 0.07, faceH/2 - 0.07, faceD / 2 + 0.01),
    new THREE.Vector3(faceW/2 - 0.07, faceH/2 - 0.07, faceD / 2 + 0.01),
    new THREE.Vector3(faceW/2 - 0.07, -faceH/2 + 0.07, faceD / 2 + 0.01),
    new THREE.Vector3(-faceW/2 + 0.07, -faceH/2 + 0.07, faceD / 2 + 0.01),
    new THREE.Vector3(-faceW/2 + 0.07, faceH/2 - 0.07, faceD / 2 + 0.01)
];
const outlineGeometry = new THREE.BufferGeometry().setFromPoints(outlinePoints);
const outlineMaterial = new THREE.LineBasicMaterial({ color: 0x00eaff, linewidth: 3 });
const outline = new THREE.Line(outlineGeometry, outlineMaterial);
face.add(outline);

// Base accent
const baseAccentPoints = [
    new THREE.Vector3(-bodyW/2, 0, -bodyD/2 + 0.01),
    new THREE.Vector3(bodyW/2, 0, -bodyD/2 + 0.01),
    new THREE.Vector3(bodyW/2, 0, bodyD/2 - 0.01),
    new THREE.Vector3(-bodyW/2, 0, bodyD/2 - 0.01),
    new THREE.Vector3(-bodyW/2, 0, -bodyD/2 + 0.01)
];
const baseAccentGeometry = new THREE.BufferGeometry().setFromPoints(baseAccentPoints);
const baseAccent = new THREE.Line(baseAccentGeometry, outlineMaterial);
deviceGroup.add(baseAccent);

// === ULTRASOUND MACHINE ===
const ultrasoundGroup = new THREE.Group();
ultrasoundGroup.scale.set(0.08, 0.08, 0.08); // Match Oralyzer scale
// Position next to Oralyzer
ultrasoundGroup.position.set(1.5, 0.7, 0); // 1.5 units to the right of Oralyzer
scene.add(ultrasoundGroup);

// === MAIN BODY ===
const ultrasoundBodyW = 2.5, ultrasoundBodyH = 2.8, ultrasoundBodyD = 1.8;
const ultrasoundBodyGeometry = new THREE.BoxGeometry(ultrasoundBodyW, ultrasoundBodyH, ultrasoundBodyD);
const ultrasoundBodyMaterial = new THREE.MeshPhysicalMaterial({ 
    color: 0xffffff, 
    metalness: 0.2, 
    roughness: 0.3, 
    clearcoat: 0.5 
});
const ultrasoundBody = new THREE.Mesh(ultrasoundBodyGeometry, ultrasoundBodyMaterial);
ultrasoundBody.position.set(0, ultrasoundBodyH/2, 0);
ultrasoundGroup.add(ultrasoundBody);

// === MAIN DISPLAY ===
const ultrasoundScreenW = 1.8, ultrasoundScreenH = 1.2, ultrasoundScreenD = 0.05;
const ultrasoundScreenGeometry = new THREE.BoxGeometry(ultrasoundScreenW, ultrasoundScreenH, ultrasoundScreenD);
const ultrasoundScreenMaterial = new THREE.MeshPhysicalMaterial({ 
    color: 0x000000, 
    metalness: 0.1, 
    roughness: 0.1, 
    emissive: 0x1e90ff, 
    emissiveIntensity: 0.2 
});
const ultrasoundScreen = new THREE.Mesh(ultrasoundScreenGeometry, ultrasoundScreenMaterial);
ultrasoundScreen.position.set(0, ultrasoundBodyH * 0.7, ultrasoundBodyD/2 + ultrasoundScreenD/2);
ultrasoundGroup.add(ultrasoundScreen);

// Screen border
const ultrasoundScreenBorderW = ultrasoundScreenW + 0.05, ultrasoundScreenBorderH = ultrasoundScreenH + 0.05, ultrasoundScreenBorderD = 0.02;
const ultrasoundScreenBorderGeometry = new THREE.BoxGeometry(ultrasoundScreenBorderW, ultrasoundScreenBorderH, ultrasoundScreenBorderD);
const ultrasoundScreenBorderMaterial = new THREE.MeshPhysicalMaterial({ 
    color: 0x333333, 
    metalness: 0.3, 
    roughness: 0.4 
});
const ultrasoundScreenBorder = new THREE.Mesh(ultrasoundScreenBorderGeometry, ultrasoundScreenBorderMaterial);
ultrasoundScreenBorder.position.set(0, ultrasoundBodyH * 0.7, ultrasoundBodyD/2 + ultrasoundScreenD/2 + ultrasoundScreenBorderD/2);
ultrasoundGroup.add(ultrasoundScreenBorder);

// === CONTROL PANEL ===
// Main control panel
const panelW = 1.6, panelH = 0.4, panelD = 0.05;
const panelGeometry = new THREE.BoxGeometry(panelW, panelH, panelD);
const panelMaterial = new THREE.MeshPhysicalMaterial({ 
    color: 0x333333, 
    metalness: 0.3, 
    roughness: 0.4 
});
const panel = new THREE.Mesh(panelGeometry, panelMaterial);
panel.position.set(0, ultrasoundBodyH * 0.3, ultrasoundBodyD/2 + panelD/2);
ultrasoundGroup.add(panel);

// Function buttons
const functionButtonGeometry = new THREE.CylinderGeometry(0.05, 0.05, 0.02, 16);
const functionButtonMaterial = new THREE.MeshPhysicalMaterial({ 
    color: 0x4CAF50, 
    metalness: 0.3, 
    roughness: 0.4 
});

// Add function buttons in a grid
for(let row = 0; row < 2; row++) {
    for(let col = 0; col < 3; col++) {
        const button = new THREE.Mesh(functionButtonGeometry, functionButtonMaterial);
        button.position.set(
            -0.4 + col * 0.4, 
            ultrasoundBodyH * 0.3 + (row * 0.15), 
            ultrasoundBodyD/2 + panelD/2 + 0.02
        );
        button.rotation.x = Math.PI/2;
        ultrasoundGroup.add(button);
    }
}

// === KEYBOARD PANEL ===
const keyboardW = 1.4, keyboardH = 0.3, keyboardD = 0.02;
const keyboardGeometry = new THREE.BoxGeometry(keyboardW, keyboardH, keyboardD);
const keyboardMaterial = new THREE.MeshPhysicalMaterial({ 
    color: 0x222222, 
    metalness: 0.2, 
    roughness: 0.5 
});
const keyboard = new THREE.Mesh(keyboardGeometry, keyboardMaterial);
keyboard.position.set(0, ultrasoundBodyH * 0.15, ultrasoundBodyD/2 + keyboardD/2);
ultrasoundGroup.add(keyboard);

// Add keyboard keys
const keyGeometry = new THREE.BoxGeometry(0.08, 0.08, 0.01);
const keyMaterial = new THREE.MeshPhysicalMaterial({ 
    color: 0x444444, 
    metalness: 0.1, 
    roughness: 0.6 
});

// Add a grid of keys
for(let row = 0; row < 3; row++) {
    for(let col = 0; col < 4; col++) {
        const key = new THREE.Mesh(keyGeometry, keyMaterial);
        key.position.set(
            -0.6 + col * 0.4, 
            ultrasoundBodyH * 0.15 + (row * 0.1) - 0.1, 
            ultrasoundBodyD/2 + keyboardD/2 + 0.01
        );
        ultrasoundGroup.add(key);
    }
}

// === TRANSDUCER HOLDER ===
const holderW = 0.4, holderH = 0.3, holderD = 0.2;
const holderGeometry = new THREE.BoxGeometry(holderW, holderH, holderD);
const holderMaterial = new THREE.MeshPhysicalMaterial({ 
    color: 0x666666, 
    metalness: 0.4, 
    roughness: 0.3 
});
const holder = new THREE.Mesh(holderGeometry, holderMaterial);
holder.position.set(ultrasoundBodyW/2 + holderW/2, ultrasoundBodyH * 0.6, 0);
ultrasoundGroup.add(holder);

// Transducer
const transducerW = 0.3, transducerH = 0.15, transducerD = 0.1;
const transducerGeometry = new THREE.BoxGeometry(transducerW, transducerH, transducerD);
const transducerMaterial = new THREE.MeshPhysicalMaterial({ 
    color: 0x333333, 
    metalness: 0.5, 
    roughness: 0.2 
});
const transducer = new THREE.Mesh(transducerGeometry, transducerMaterial);
transducer.position.set(ultrasoundBodyW/2 + holderW/2, ultrasoundBodyH * 0.6, holderD/2 + transducerD/2);
ultrasoundGroup.add(transducer);

// Transducer cable
const cableGeometry = new THREE.CylinderGeometry(0.02, 0.02, 0.8, 8);
const cableMaterial = new THREE.MeshPhysicalMaterial({ 
    color: 0x222222, 
    metalness: 0.1, 
    roughness: 0.8 
});
const cable = new THREE.Mesh(cableGeometry, cableMaterial);
cable.position.set(ultrasoundBodyW/2 + holderW/2, ultrasoundBodyH * 0.6 - 0.4, holderD/2 + transducerD/2);
cable.rotation.x = Math.PI/2;
ultrasoundGroup.add(cable);

// === WHEELS AND CASTERS ===
const wheelRadius = 0.15, wheelThickness = 0.1;
const wheelGeometry = new THREE.CylinderGeometry(wheelRadius, wheelRadius, wheelThickness, 16);
const wheelMaterial = new THREE.MeshPhysicalMaterial({ 
    color: 0x666666, 
    metalness: 0.5, 
    roughness: 0.3 
});

// Add four wheels with casters
const wheelPositions = [
    [-ultrasoundBodyW/2 + 0.3, 0, -ultrasoundBodyD/2 + 0.3],
    [ultrasoundBodyW/2 - 0.3, 0, -ultrasoundBodyD/2 + 0.3],
    [-ultrasoundBodyW/2 + 0.3, 0, ultrasoundBodyD/2 - 0.3],
    [ultrasoundBodyW/2 - 0.3, 0, ultrasoundBodyD/2 - 0.3]
];

wheelPositions.forEach(pos => {
    // Caster base
    const casterBaseGeometry = new THREE.CylinderGeometry(0.2, 0.2, 0.05, 16);
    const casterBase = new THREE.Mesh(casterBaseGeometry, wheelMaterial);
    casterBase.position.set(...pos);
    casterBase.position.y += 0.1;
    ultrasoundGroup.add(casterBase);

    // Wheel
    const wheel = new THREE.Mesh(wheelGeometry, wheelMaterial);
    wheel.position.set(...pos);
    wheel.rotation.z = Math.PI/2;
    ultrasoundGroup.add(wheel);
});

// === HANDLE AND SUPPORTS ===
// Main handle
const handleGeometry = new THREE.CylinderGeometry(0.08, 0.08, 0.4, 16);
const handleMaterial = new THREE.MeshPhysicalMaterial({ 
    color: 0x666666, 
    metalness: 0.5, 
    roughness: 0.3 
});
const handle = new THREE.Mesh(handleGeometry, handleMaterial);
handle.position.set(0, ultrasoundBodyH + 0.2, 0);
handle.rotation.x = Math.PI/2;
ultrasoundGroup.add(handle);

// Handle supports
const supportGeometry = new THREE.CylinderGeometry(0.03, 0.03, 0.3, 8);
const supportMaterial = new THREE.MeshPhysicalMaterial({ 
    color: 0x666666, 
    metalness: 0.5, 
    roughness: 0.3 
});

// Add two supports
for(let i = -1; i <= 1; i += 2) {
    const support = new THREE.Mesh(supportGeometry, supportMaterial);
    support.position.set(i * 0.3, ultrasoundBodyH + 0.05, 0);
    support.rotation.z = Math.PI/2;
    ultrasoundGroup.add(support);
}

// === STATUS LIGHTS ===
const lightGeometry = new THREE.CylinderGeometry(0.02, 0.02, 0.01, 16);
const lightPositions = [
    { pos: [-ultrasoundBodyW/2 + 0.2, ultrasoundBodyH - 0.2, ultrasoundBodyD/2 + 0.01], color: 0x00ff00 },
    { pos: [-ultrasoundBodyW/2 + 0.2, ultrasoundBodyH - 0.3, ultrasoundBodyD/2 + 0.01], color: 0xff0000 },
    { pos: [-ultrasoundBodyW/2 + 0.2, ultrasoundBodyH - 0.4, ultrasoundBodyD/2 + 0.01], color: 0xffff00 }
];

lightPositions.forEach(light => {
    const lightMaterial = new THREE.MeshPhysicalMaterial({ 
        color: light.color, 
        metalness: 0.2, 
        roughness: 0.3,
        emissive: light.color,
        emissiveIntensity: 0.5
    });
    const statusLight = new THREE.Mesh(lightGeometry, lightMaterial);
    statusLight.position.set(...light.pos);
    statusLight.rotation.x = Math.PI/2;
    ultrasoundGroup.add(statusLight);
});

// === VENTILATION GRILLS ===
const grillGeometry = new THREE.BoxGeometry(0.4, 0.1, 0.02);
const grillMaterial = new THREE.MeshPhysicalMaterial({ 
    color: 0x444444, 
    metalness: 0.3, 
    roughness: 0.6 
});

// Add ventilation grills on sides
for(let side = -1; side <= 1; side += 2) {
    const grill = new THREE.Mesh(grillGeometry, grillMaterial);
    grill.position.set(
        side * (ultrasoundBodyW/2 + 0.01),
        ultrasoundBodyH * 0.4,
        0
    );
    grill.rotation.y = side * Math.PI/2;
    ultrasoundGroup.add(grill);
}

// === INTERACTIVITY: Raycasting for hover/click ===
const raycaster = new THREE.Raycaster();
const mouse = new THREE.Vector2(0, 0); // Center of screen
let isOralyzerHovered = false;
let isOralyzerModalOpen = false; // Track modal state
let oralyzerBaseY = deviceGroup.position.y;

// Modal overlay creation
let modal = document.getElementById('oralyzer-modal');
if (!modal) {
    modal = document.createElement('div');
    modal.id = 'oralyzer-modal';
    modal.style.position = 'fixed';
    modal.style.left = '0';
    modal.style.top = '0';
    modal.style.width = '100vw';
    modal.style.height = '100vh';
    modal.style.background = 'rgba(20, 24, 32, 0.92)';
    modal.style.display = 'none';
    modal.style.zIndex = '9999';
    modal.style.justifyContent = 'center';
    modal.style.alignItems = 'center';
    modal.innerHTML = `
        <div style="background:#23243a;padding:32px 24px;border-radius:18px;box-shadow:0 8px 32px #0008;max-width:90vw;max-height:80vh;position:relative;">
            <button id="close-oralyzer-modal" style="position:absolute;top:12px;right:16px;font-size:1.5em;background:none;border:none;color:#fff;cursor:pointer;">&times;</button>
            <div id="oralyzer-modal-content" style="color:#fff;min-width:300px;min-height:120px;text-align:center;">
                <h2>Oralyzer</h2>
                <p>This is a placeholder for the Oralyzer functionality.</p>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
    document.getElementById('close-oralyzer-modal').onclick = () => {
        modal.style.display = 'none';
        isOralyzerModalOpen = false;
    };
}

// Helper to show modal with Oralyzer UI
async function showOralyzerModal() {
    // Fetch the Oralyzer_clean.html content
    const response = await fetch('/oralyzer/clean');
    const html = await response.text();
    // Extract the <body> content for modal
    const bodyMatch = html.match(/<body[^>]*>([\s\S]*?)<\/body>/i);
    const bodyContent = bodyMatch ? bodyMatch[1] : html;
    modal.innerHTML = `
        <div style="background:#23243a;padding:32px 24px;border-radius:18px;box-shadow:0 8px 32px #0008;max-width:90vw;max-height:80vh;position:relative;overflow:auto;">
            <button id="close-oralyzer-modal" style="position:absolute;top:12px;right:16px;font-size:1.5em;background:none;border:none;color:#fff;cursor:pointer;">&times;</button>
            <div id="oralyzer-modal-content" style="color:#fff;min-width:300px;min-height:120px;text-align:center;">${bodyContent}</div>
        </div>
    `;
    document.getElementById('close-oralyzer-modal').onclick = () => {
        modal.style.display = 'none';
        isOralyzerModalOpen = false;
    };
    modal.style.display = 'flex';
    isOralyzerModalOpen = true;
}

// === HTML2CANVAS for live UI preview ===
(function injectHtml2Canvas() {
    if (!window.html2canvas) {
        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js';
        script.onload = () => { window.html2canvasLoaded = true; };
        document.head.appendChild(script);
    }
})();

// Movement controls
const moveSpeed = 3;
const runSpeed = 6;
const jumpForce = 3.5;
const gravity = 10;
let velocityY = 0;
let isGrounded = true;
const keys = {};

document.addEventListener('keydown', (e) => {
    keys[e.key.toLowerCase()] = true;
    if (e.key === 'Escape') {
        if (controls.isLocked) {
            controls.unlock();
            document.getElementById('menu').style.display = 'block';
        } else {
            controls.lock();
            document.getElementById('menu').style.display = 'none';
        }
    }
});

document.addEventListener('keyup', (e) => {
    keys[e.key.toLowerCase()] = false;
});

// Menu controls
document.getElementById('toggle-lights').addEventListener('click', () => {
    ambientLight.intensity = ambientLight.intensity === 0.5 ? 0 : 0.5;
});

document.getElementById('reset-position').addEventListener('click', () => {
    controls.getObject().position.set(0, 1, 0);
    controls.getObject().rotation.set(0, 0, 0);
});

// Click to start
document.addEventListener('click', () => {
    if (!controls.isLocked) {
        controls.lock();
        document.getElementById('menu').style.display = 'none';
    }
});

// === Cinematic Load-In Animation ===
let cinematicActive = true;
const cinematicDuration = 1.8; // Shorter duration for snappier spawn
let cinematicTime = 0;

// Spawn animation parameters
const spawnHeight = 8; // Start high above
const spawnTarget = new THREE.Vector3(0, 1.2, 3.5); // Final position
const spawnLookAt = new THREE.Vector3(0, 0.85, 0); // Look at Oralyzer

// Smooth easing functions
function easeOutBounce(t) {
    const n1 = 7.5625;
    const d1 = 2.75;
    if (t < 1 / d1) {
        return n1 * t * t;
    } else if (t < 2 / d1) {
        return n1 * (t -= 1.5 / d1) * t + 0.75;
    } else if (t < 2.5 / d1) {
        return n1 * (t -= 2.25 / d1) * t + 0.9375;
    } else {
        return n1 * (t -= 2.625 / d1) * t + 0.984375;
    }
}

function easeOutCubic(t) {
    return 1 - Math.pow(1 - t, 3);
}

// Initialize cinematic state
controls.unlock();
document.getElementById('menu').style.display = 'none';
document.getElementById('crosshair').style.display = 'none';
if (loadingScreen) {
    loadingScreen.style.display = 'block';
    loadingScreen.style.opacity = '1';
}

// Set initial camera position (high above)
controls.getObject().position.set(0, spawnHeight, spawnTarget.z);
controls.getObject().lookAt(spawnLookAt);

// Animation loop
function animate() {
    requestAnimationFrame(animate);

    if (cinematicActive) {
        cinematicTime += Math.min(1/60, (performance.now() - prevTime) / 1000);
        let t = Math.min(1, cinematicTime / cinematicDuration);
        
        // Apply bounce easing for vertical movement
        const bounceT = easeOutBounce(t);
        
        // Calculate current position
        const currentPos = new THREE.Vector3();
        currentPos.lerpVectors(
            new THREE.Vector3(0, spawnHeight, spawnTarget.z),
            spawnTarget,
            bounceT
        );
        
        // Add slight forward momentum
        const forwardOffset = Math.sin(t * Math.PI) * 0.5;
        currentPos.z += forwardOffset;
        
        // Add subtle horizontal sway
        const swayAmount = Math.sin(t * Math.PI * 2) * 0.1;
        currentPos.x += swayAmount;
        
        // Update camera position
        controls.getObject().position.copy(currentPos);
        
        // Smooth look-at with slight delay
        const lookAtProgress = easeOutCubic(Math.min(1, t * 1.5));
        const currentLookAt = new THREE.Vector3();
        currentLookAt.lerpVectors(
            new THREE.Vector3(0, spawnHeight - 1, spawnTarget.z),
            spawnLookAt,
            lookAtProgress
        );
        controls.getObject().lookAt(currentLookAt);
        
        // Fade out loading screen near the end
        if (t > 0.6) {
            const fadeProgress = (t - 0.6) / 0.4;
            if (loadingScreen) {
                loadingScreen.style.opacity = (1 - fadeProgress).toFixed(2);
            }
        }
        
        if (t >= 1) {
            cinematicActive = false;
            // Set final position and orientation
            controls.getObject().position.copy(spawnTarget);
            controls.getObject().lookAt(spawnLookAt);
            
            // Hide loading screen and stop dots animation
            if (loadingScreen) {
                loadingScreen.style.display = 'none';
            }
            
            // Show crosshair only after cinematic is complete
            document.getElementById('crosshair').style.display = 'block';
            
            // Lock controls
            controls.lock();

            // Enable screen and show UI after cinematic
            powerOn = true;
            initializeScreenUI();
        }
        
        prevTime = performance.now();
        renderer.render(scene, camera);
        return;
    }

    if (controls.isLocked) {
        const time = performance.now();
        const delta = (time - prevTime) / 1000;

        let moveX = 0;
        let moveZ = 0;
        const speed = keys['shift'] ? runSpeed : moveSpeed;

        if (keys['w']) moveZ += 1;
        if (keys['s']) moveZ -= 1;
        if (keys['a']) moveX -= 1;
        if (keys['d']) moveX += 1;

        // Jumping
        if (keys[' '] && isGrounded) {
            velocityY = jumpForce;
            isGrounded = false;
        }

        // Apply gravity
        velocityY -= gravity * delta;
        controls.getObject().position.y += velocityY * delta;

        // Ground check
        if (controls.getObject().position.y <= 1) {
            controls.getObject().position.y = 1;
            velocityY = 0;
            isGrounded = true;
        }

        if (moveX !== 0 && moveZ !== 0) {
            const norm = Math.sqrt(2) / 2;
            moveX *= norm;
            moveZ *= norm;
        }

        controls.moveRight(moveX * speed * delta);
        controls.moveForward(moveZ * speed * delta);

        // Collision detection with walls
        const pos = controls.getObject().position;
        pos.x = Math.max(-ROOM_WIDTH/2 + 0.5, Math.min(ROOM_WIDTH/2 - 0.5, pos.x));
        pos.z = Math.max(-ROOM_LENGTH/2 + 0.5, Math.min(ROOM_LENGTH/2 - 0.5, pos.z));

        // Raycast from camera center
        raycaster.setFromCamera(mouse, camera);
        const intersects = raycaster.intersectObject(deviceGroup, true);
        if (intersects.length > 0) {
            if (!isOralyzerHovered) {
                isOralyzerHovered = true;
                outline.material.color.set(0xffff00); // Highlight outline (yellow)
                renderer.domElement.style.cursor = 'pointer';
                // Freeze bobbing at current phase
                oralyzerBobbingPaused = true;
                oralyzerBobbingStoredPhase = oralyzerBobbingPhase;
                oralyzerBobbingStoredY = deviceGroup.position.y;
                oralyzerBobbingStoredRot = deviceGroup.rotation.z;
            }
        } else {
            if (isOralyzerHovered) {
                isOralyzerHovered = false;
                outline.material.color.set(0x00eaff); // Default cyan
                renderer.domElement.style.cursor = '';
                // Resume bobbing from stored phase
                oralyzerBobbingPaused = false;
            }
        }

        // Ethernet port blinking light
        updateEthernetLights(delta);

        prevTime = time;
    }

    renderer.render(scene, camera);
}

let prevTime = performance.now();
animate();

// Handle window resize
window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
});

// Camera/player start position
// controls.getObject().position.set(0, 1.2, 2.5); // In front of Oralyzer, a bit back
// controls.getObject().rotation.set(0, 0, 0);

// Add a visible floor grid for orientation
const gridHelper = new THREE.GridHelper(ROOM_WIDTH, ROOM_WIDTH, 0x4CAF50, 0x333333);
gridHelper.position.y = 0.01;
scene.add(gridHelper);

// On Oralyzer click, load UI into modal and offscreenDiv for live preview
renderer.domElement.addEventListener('click', async (e) => {
    if (isOralyzerHovered && controls.isLocked) {
        // Create fullscreen iframe
        const fullscreenContainer = document.createElement('div');
        fullscreenContainer.style.position = 'fixed';
        fullscreenContainer.style.top = '0';
        fullscreenContainer.style.left = '0';
        fullscreenContainer.style.width = '100vw';
        fullscreenContainer.style.height = '100vh';
        fullscreenContainer.style.background = '#23243a';
        fullscreenContainer.style.zIndex = '9999';
        fullscreenContainer.style.display = 'flex';
        fullscreenContainer.style.flexDirection = 'column';
        
        // Add header with back button
        const header = document.createElement('div');
        header.style.padding = '1em';
        header.style.background = 'rgba(0,0,0,0.2)';
        header.style.display = 'flex';
        header.style.alignItems = 'center';
        header.style.gap = '1em';
        
        const backButton = document.createElement('button');
        backButton.innerHTML = '← Back to 3D View';
        backButton.style.background = '#fff2';
        backButton.style.color = '#fff';
        backButton.style.border = 'none';
        backButton.style.padding = '0.5em 1em';
        backButton.style.borderRadius = '8px';
        backButton.style.cursor = 'pointer';
        backButton.style.fontSize = '1.1em';
        backButton.onclick = () => {
            document.body.removeChild(fullscreenContainer);
            controls.lock();
        };
        
        header.appendChild(backButton);
        fullscreenContainer.appendChild(header);
        
        // Add iframe
        const iframe = document.createElement('iframe');
        iframe.style.flex = '1';
        iframe.style.border = 'none';
        iframe.style.width = '100%';
        iframe.style.height = '100%';
        iframe.src = '/oralyzer/clean';
        fullscreenContainer.appendChild(iframe);
        
        document.body.appendChild(fullscreenContainer);
        controls.unlock();
    }
});

// === 3D Power Button and Tray Interactivity ===
// Raycaster for power button and tray
const clickableObjects = [button, lip];
renderer.domElement.addEventListener('mousedown', (event) => {
    if (!controls.isLocked) return;
    // Calculate mouse position in normalized device coordinates
    const rect = renderer.domElement.getBoundingClientRect();
    const mouseX = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    const mouseY = -((event.clientY - rect.top) / rect.height) * 2 + 1;
    raycaster.setFromCamera({x: mouseX, y: mouseY}, camera);
    const intersects = raycaster.intersectObjects(clickableObjects, true);
    if (intersects.length > 0) {
        const obj = intersects[0].object;
        // Power button
        if (obj === button || button.children.includes(obj)) {
            // Try to trigger power button in modal/offscreenDiv
            const powerBtn = offscreenDiv.querySelector('.power-btn, button.power, #power-btn, .powerButton');
            if (powerBtn) powerBtn.click();
            const modalPowerBtn = document.getElementById('oralyzer-modal-content')?.querySelector('.power-btn, button.power, #power-btn, .powerButton');
            if (modalPowerBtn) modalPowerBtn.click();
        }
        // Tray
        if (obj === lip) {
            const trayBtn = offscreenDiv.querySelector('.tray-btn, button.tray, #tray-btn, .trayButton');
            if (trayBtn) trayBtn.click();
            const modalTrayBtn = document.getElementById('oralyzer-modal-content')?.querySelector('.tray-btn, button.tray, #tray-btn, .trayButton');
            if (modalTrayBtn) modalTrayBtn.click();
        }
    }
});

// Add click handler for screen UI
screenUI.addEventListener('click', (e) => {
    if (!controls.isLocked) return;
    
    // Find the closest button to the click position
    const buttons = screenUI.querySelectorAll('button');
    let closestButton = null;
    let minDistance = Infinity;
    
    buttons.forEach(button => {
        const rect = button.getBoundingClientRect();
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;
        const distance = Math.sqrt(
            Math.pow(e.clientX - centerX, 2) + 
            Math.pow(e.clientY - centerY, 2)
        );
        
        if (distance < minDistance) {
            minDistance = distance;
            closestButton = button;
        }
    });
    
    // If we found a button and it's close enough to the click
    if (closestButton && minDistance < 50) {
        handleButtonClick(closestButton);
    }
});

// Add hover effect for buttons
screenUI.addEventListener('mousemove', (e) => {
    if (!controls.isLocked) return;
    
    const buttons = screenUI.querySelectorAll('button');
    buttons.forEach(button => {
        const rect = button.getBoundingClientRect();
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;
        const distance = Math.sqrt(
            Math.pow(e.clientX - centerX, 2) + 
            Math.pow(e.clientY - centerY, 2)
        );
        
        if (distance < 50) {
            button.style.transform = 'scale(1.05)';
            button.style.transition = 'transform 0.2s ease';
        } else {
            button.style.transform = '';
        }
    });
});

// Add button click functionality
function handleButtonClick(button) {
    if (!button) return;
    
    // Add click animation
    button.style.transform = 'scale(0.95)';
    setTimeout(() => {
        button.style.transform = '';
    }, 100);

    // Handle different button actions
    switch(button.id) {
        case 'order-list-btn':
            showOrderList();
            break;
        case 'results-btn':
            showResultsDashboard();
            break;
        case 'system-btn':
            showSystemMenu();
            break;
        case 'start-test-btn':
            startNewTest();
            break;
    }
}

// Function to show order list
function showOrderList() {
    const main = document.getElementById('screen-ui-main');
    if (!main) return;
    // Save current menu to restore later
    if (!main.dataset.original) {
        main.dataset.original = main.innerHTML;
    }
    main.innerHTML = `
        <div style="width:100%;height:100%;display:flex;flex-direction:column;align-items:center;justify-content:flex-start;background:linear-gradient(90deg,#2562b4 0%,#3fa9f5 100%);border-radius:24px;position:relative;">
            <div style='width:100%;text-align:left;margin-bottom:0.7em;position:sticky;top:0;z-index:2;display:flex;align-items:center;gap:1em;background:linear-gradient(90deg,#2562b4 0%,#3fa9f5 100%);padding:1.2em 0 0.5em 0;border-radius:24px 24px 0 0;'>
                <button id="order-list-back-btn" style="background:#fff2;color:#2562b4;font-size:1.1em;font-weight:600;padding:0.5em 1.6em;border:none;border-radius:18px;box-shadow:0 2px 8px #0002;cursor:pointer;margin-left:2em;">← Back</button>
                <h2 style="color:#fff;font-size:2em;font-weight:700;letter-spacing:0.5px;margin:0 0 0 1em;">Order List</h2>
            </div>
            <div style="flex:1;width:100%;padding:0 2em;overflow-y:auto;">
                <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:1em;padding:1em 0;">
                    <!-- Sample orders -->
                    <div style="background:#fff2;border-radius:12px;padding:1em;color:#fff;">
                        <h3 style="margin:0 0 0.5em 0;">Order #12345</h3>
                        <p style="margin:0;">Status: Pending</p>
                    </div>
                    <div style="background:#fff2;border-radius:12px;padding:1em;color:#fff;">
                        <h3 style="margin:0 0 0.5em 0;">Order #12346</h3>
                        <p style="margin:0;">Status: Completed</p>
                    </div>
                </div>
            </div>
        </div>
    `;
    // Back button handler
    document.getElementById('order-list-back-btn').onclick = () => {
        main.innerHTML = main.dataset.original;
        addScreenUIHandlers();
    };
}

// Function to show results dashboard
function showResultsDashboard() {
    const main = document.getElementById('screen-ui-main');
    if (!main) return;
    // Save current menu to restore later
    if (!main.dataset.original) {
        main.dataset.original = main.innerHTML;
    }
    main.innerHTML = `
        <div style="width:100%;height:100%;display:flex;flex-direction:column;align-items:center;justify-content:flex-start;background:linear-gradient(90deg,#2562b4 0%,#3fa9f5 100%);border-radius:24px;position:relative;">
            <div style='width:100%;text-align:left;margin-bottom:0.7em;position:sticky;top:0;z-index:2;display:flex;align-items:center;gap:1em;background:linear-gradient(90deg,#2562b4 0%,#3fa9f5 100%);padding:1.2em 0 0.5em 0;border-radius:24px 24px 0 0;'>
                <button id="results-back-btn" style="background:#fff2;color:#2562b4;font-size:1.1em;font-weight:600;padding:0.5em 1.6em;border:none;border-radius:18px;box-shadow:0 2px 8px #0002;cursor:pointer;margin-left:2em;">← Back</button>
                <h2 style="color:#fff;font-size:2em;font-weight:700;letter-spacing:0.5px;margin:0 0 0 1em;">Results Dashboard</h2>
            </div>
            <div style="flex:1;width:100%;padding:0 2em;overflow-y:auto;">
                <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:1em;padding:1em 0;">
                    <!-- Sample results -->
                    <div style="background:#fff2;border-radius:12px;padding:1em;color:#fff;">
                        <h3 style="margin:0 0 0.5em 0;">Test #12345</h3>
                        <p style="margin:0;">Result: Normal</p>
                    </div>
                    <div style="background:#fff2;border-radius:12px;padding:1em;color:#fff;">
                        <h3 style="margin:0 0 0.5em 0;">Test #12346</h3>
                        <p style="margin:0;">Result: Abnormal</p>
                    </div>
                </div>
            </div>
        </div>
    `;
    // Back button handler
    document.getElementById('results-back-btn').onclick = () => {
        main.innerHTML = main.dataset.original;
        addScreenUIHandlers();
    };
}

// Function to show system menu
function showSystemMenu() {
    const main = document.getElementById('screen-ui-main');
    if (!main) return;
    // Save current menu to restore later
    if (!main.dataset.original) {
        main.dataset.original = main.innerHTML;
    }
    main.innerHTML = `
        <div style="width:100%;height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;background:linear-gradient(90deg,#2562b4 0%,#3fa9f5 100%);border-radius:24px;position:relative;">
            <div style='position:absolute;top:0;left:0;width:auto;display:flex;align-items:center;gap:1em;padding:1.2em 0 0.5em 2.2em;z-index:2;background:transparent;'>
                <button id="sys-back-btn" style="background:#fff2;color:#2562b4;font-size:1.1em;font-weight:600;padding:0.5em 1.6em;border:none;border-radius:18px;box-shadow:0 2px 8px #0002;cursor:pointer;">← Back</button>
                <h2 style="color:#fff;font-size:2em;font-weight:700;letter-spacing:0.5px;margin:0;">System Menu</h2>
            </div>
            <div style="display:grid;grid-template-columns:repeat(2,1fr);grid-template-rows:repeat(2,1fr);gap:1em;width:90%;max-width:500px;height:260px;align-items:center;justify-items:center;">
                <button class='screen-btn' id="status-btn" style="border-radius:999px;padding:1.1em 0;font-size:1.18em;font-weight:600;background:#fff2;color:#fff;border:1.5px solid #3fa9f5;display:flex;align-items:center;justify-content:center;gap:0.7em;width:100%;min-width:0;">Status</button>
                <button class='screen-btn' id="update-btn" style="border-radius:999px;padding:1.1em 0;font-size:1.18em;font-weight:600;background:#fff2;color:#fff;border:1.5px solid #3fa9f5;display:flex;align-items:center;justify-content:center;gap:0.7em;width:100%;min-width:0;">Update</button>
                <button class='screen-btn' id="settings-btn" style="border-radius:999px;padding:1.1em 0;font-size:1.18em;font-weight:600;background:#fff2;color:#fff;border:1.5px solid #3fa9f5;display:flex;align-items:center;justify-content:center;gap:0.7em;width:100%;min-width:0;">Settings</button>
                <button class='screen-btn' id="maintenance-btn" style="border-radius:999px;padding:1.1em 0;font-size:1.18em;font-weight:600;background:#fff2;color:#fff;border:1.5px solid #3fa9f5;display:flex;align-items:center;justify-content:center;gap:0.7em;width:100%;min-width:0;">Maintenance</button>
            </div>
        </div>
    `;
    // Back button handler
    document.getElementById('sys-back-btn').onclick = () => {
        main.innerHTML = main.dataset.original;
        addScreenUIHandlers();
    };
}

// Function to start new test
function startNewTest() {
    const main = document.getElementById('screen-ui-main');
    if (!main) return;
    // Save current menu to restore later
    if (!main.dataset.original) {
        main.dataset.original = main.innerHTML;
    }
    main.innerHTML = `
        <div style="width:100%;height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;background:linear-gradient(90deg,#2562b4 0%,#3fa9f5 100%);border-radius:24px;position:relative;">
            <div style='width:100%;text-align:left;margin-bottom:0.7em;position:sticky;top:0;z-index:2;display:flex;align-items:center;gap:1em;background:linear-gradient(90deg,#2562b4 0%,#3fa9f5 100%);padding:1.2em 0 0.5em 0;border-radius:24px 24px 0 0;'>
                <button id="test-back-btn" style="background:#fff2;color:#2562b4;font-size:1.1em;font-weight:600;padding:0.5em 1.6em;border:none;border-radius:18px;box-shadow:0 2px 8px #0002;cursor:pointer;margin-left:2em;">← Back</button>
                <h2 style="color:#fff;font-size:2em;font-weight:700;letter-spacing:0.5px;margin:0 0 0 1em;">New Test</h2>
            </div>
            <div style="flex:1;width:100%;padding:0 2em;overflow-y:auto;">
                <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;">
                    <div style="background:#fff2;border-radius:12px;padding:2em;color:#fff;text-align:center;">
                        <h3 style="margin:0 0 1em 0;">Test in Progress...</h3>
                        <div style="width:100px;height:100px;border:4px solid #fff;border-top-color:transparent;border-radius:50%;animation:spin 1s linear infinite;margin:0 auto;"></div>
                    </div>
                </div>
            </div>
        </div>
    `;
    // Back button handler
    document.getElementById('test-back-btn').onclick = () => {
        main.innerHTML = main.dataset.original;
        addScreenUIHandlers();
    };
}

// Add screen UI handlers
function addScreenUIHandlers() {
    document.getElementById('order-list-btn').onclick = () => showOrderList();
    document.getElementById('results-btn').onclick = () => showResultsDashboard();
    document.getElementById('system-btn').onclick = () => showSystemMenu();
    document.getElementById('start-test-btn').onclick = () => startNewTest();
}

// Initialize handlers
addScreenUIHandlers(); 