import * as THREE from 'three';
import { PointerLockControls } from 'three/addons/controls/PointerLockControls.js';

// --- Global Variables ---
let camera, scene, renderer, controls;
let moveForward = false;
let moveBackward = false;
let moveLeft = false;
let moveRight = false;
let raycaster;

let time;
let prevTime = performance.now();
const velocity = new THREE.Vector3();
const direction = new THREE.Vector3();

// Game State
let isGameActive = false;
let score = 0;
const bullets = [];
const enemies = [];
const enemySpeed = 10;

let lastEnemySpawn = 0;

// Ammo System
const MAX_AMMO = 6;
let currentAmmo = MAX_AMMO;
let isReloading = false;

// Health System
const MAX_HEALTH = 10;
let currentHealth = MAX_HEALTH;


// Gun Model
let gun;
const gunRecoilPosition = new THREE.Vector3(0.5, -0.5, -1);
const gunRestPosition = new THREE.Vector3(0.5, -0.5, -1);


// Config
// Config
const BULLET_SPEED = 100;
const PLAYER_SPEED = 80;
const SPAWN_RATE = 2000;
const RELOAD_TIME = 1000;


// --- Initialization ---
// (Calls moved to end of file)


function init() {
    // 1. Scene
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x050510); // Dark Blue-ish Black
    scene.fog = new THREE.Fog(0x050510, 0, 100);

    // 2. Camera
    camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000); // Changed near plane to 0.1 to see gun
    camera.position.y = 1.6; // Eye level

    // Add Gun to Camera
    gun = new THREE.Group();

    // Gun Body
    const gunBodyGeo = new THREE.BoxGeometry(0.2, 0.2, 0.6);
    const gunMat = new THREE.MeshStandardMaterial({ color: 0x333333, metalness: 0.8, roughness: 0.2 });
    const gunBody = new THREE.Mesh(gunBodyGeo, gunMat);
    gunBody.position.set(0, 0, 0);
    gun.add(gunBody);

    // Gun Handle
    const handleGeo = new THREE.BoxGeometry(0.15, 0.4, 0.2);
    const handle = new THREE.Mesh(handleGeo, gunMat);
    handle.position.set(0, -0.2, 0.1);
    handle.rotation.x = Math.PI / 6;
    gun.add(handle);

    // Neon Strip
    const stripGeo = new THREE.BoxGeometry(0.05, 0.05, 0.5);
    const stripMat = new THREE.MeshBasicMaterial({ color: 0x00ffff });
    const strip = new THREE.Mesh(stripGeo, stripMat);
    strip.position.set(0, 0.11, 0);
    gun.add(strip);

    gun.position.copy(gunRestPosition);
    camera.add(gun);
    scene.add(camera); // Add camera to scene so children are rendered


    // 3. Renderer
    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.shadowMap.enabled = true; // Enable shadows
    document.body.appendChild(renderer.domElement);

    // 4. Lights
    const hemiLight = new THREE.HemisphereLight(0xffffff, 0x444444, 0.8); // Sky color, Ground color, Intensity
    hemiLight.position.set(0, 20, 0);
    scene.add(hemiLight);

    const dirLight = new THREE.DirectionalLight(0xffffff, 0.8); // Sunlight
    dirLight.position.set(-3, 10, -10);
    dirLight.castShadow = true;
    dirLight.shadow.camera.top = 20;
    dirLight.shadow.camera.bottom = -20;
    dirLight.shadow.camera.left = -20;
    dirLight.shadow.camera.right = 20;
    dirLight.shadow.camera.near = 0.1;
    dirLight.shadow.camera.far = 40;
    scene.add(dirLight);

    // Add point lights for neon feel
    const pointLight1 = new THREE.PointLight(0x00ffff, 1, 50);
    pointLight1.position.set(10, 5, 10);
    scene.add(pointLight1);

    const pointLight2 = new THREE.PointLight(0xff00ff, 1, 50);
    pointLight2.position.set(-10, 5, -10);
    scene.add(pointLight2);


    // 5. Controls
    controls = new PointerLockControls(camera, document.body);

    const instructions = document.getElementById('instructions');
    const gameOverScreen = document.getElementById('game-over');

    instructions.addEventListener('click', function () {
        controls.lock();
    });

    gameOverScreen.addEventListener('click', function () {
        resetGame();
        controls.lock();
    });

    controls.addEventListener('lock', function () {
        instructions.style.display = 'none';
        gameOverScreen.style.display = 'none';
        isGameActive = true;
    });

    controls.addEventListener('unlock', function () {
        if (isGameActive) { // Only show instructions if paused, not dead
            instructions.style.display = 'block';
        }
        isGameActive = false;
    });

    scene.add(controls.getObject());

    // 6. Input Handling
    const onKeyDown = function (event) {
        switch (event.code) {
            case 'ArrowUp':
            case 'KeyW':
                moveForward = true;
                break;
            case 'KeyR':
                reload();
                break;
            case 'ArrowLeft':

            case 'KeyA':
                moveLeft = true;
                break;
            case 'ArrowDown':
            case 'KeyS':
                moveBackward = true;
                break;
            case 'ArrowRight':
            case 'KeyD':
                moveRight = true;
                break;
        }
    };

    const onKeyUp = function (event) {
        switch (event.code) {
            case 'ArrowUp':
            case 'KeyW':
                moveForward = false;
                break;
            case 'ArrowLeft':
            case 'KeyA':
                moveLeft = false;
                break;
            case 'ArrowDown':
            case 'KeyS':
                moveBackward = false;
                break;
            case 'ArrowRight':
            case 'KeyD':
                moveRight = false;
                break;
        }
    };

    document.addEventListener('keydown', onKeyDown);
    document.addEventListener('keyup', onKeyUp);
    document.addEventListener('keydown', onKeyDown);
    document.addEventListener('keyup', onKeyUp);
    document.addEventListener('mousedown', onMouseDown); // Shooting

    // 6. Environment (Minecraft Style)
    createEnvironment();

    // Resize Handler
    window.addEventListener('resize', onWindowResize);
}


// Floor (Green/Grass)
// --- Procedural Texture Generator ---
function createTexture(baseColorHex, noiseAmount = 20) {
    const size = 128;
    const canvas = document.createElement('canvas');
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext('2d');

    // Fill Base Color
    ctx.fillStyle = '#' + new THREE.Color(baseColorHex).getHexString();
    ctx.fillRect(0, 0, size, size);

    // Add Noise
    const imageData = ctx.getImageData(0, 0, size, size);
    const data = imageData.data;
    for (let i = 0; i < data.length; i += 4) {
        const noise = (Math.random() - 0.5) * noiseAmount;
        data[i] = Math.min(255, Math.max(0, data[i] + noise));     // R
        data[i + 1] = Math.min(255, Math.max(0, data[i + 1] + noise)); // G
        data[i + 2] = Math.min(255, Math.max(0, data[i + 2] + noise)); // B
    }
    ctx.putImageData(imageData, 0, 0);

    const texture = new THREE.CanvasTexture(canvas);
    texture.magFilter = THREE.NearestFilter; // Pixelated look
    texture.minFilter = THREE.NearestFilter;
    return texture;
}

// --- Environment Generation ---
function createEnvironment() {
    // 1. Textures
    const stoneTex = createTexture(0x757575, 40); // Grey Stone
    const grassTex = createTexture(0x4caf50, 30); // Green Grass
    const dirtTex = createTexture(0x5d4037, 30);  // Brown Dirt
    const woodTex = createTexture(0x8d6e63, 40);  // Light Brown Wood
    const darkWoodTex = createTexture(0x4e342e, 40); // Dark Wood (Trunks)
    const obsidianTex = createTexture(0x1a1a1a, 20); // Dark Obsidian

    const materialCache = {
        stone: new THREE.MeshStandardMaterial({ map: stoneTex, roughness: 0.8 }),
        grass: new THREE.MeshStandardMaterial({ map: grassTex, roughness: 0.9 }),
        dirt: new THREE.MeshStandardMaterial({ map: dirtTex, roughness: 1.0 }),
        wood: new THREE.MeshStandardMaterial({ map: woodTex, roughness: 0.7 }),
        trunk: new THREE.MeshStandardMaterial({ map: darkWoodTex, roughness: 0.9 }),
        obsidian: new THREE.MeshStandardMaterial({ map: obsidianTex, roughness: 0.2, color: 0x330033 }), // Purple tint
        leaves: new THREE.MeshStandardMaterial({ color: 0x2e7d32 }) // Keep leaves simple for now
    };

    // 2. Floor (Cobblestone Courtyard)
    const floorGeo = new THREE.PlaneGeometry(100, 100);
    floorGeo.rotateX(-Math.PI / 2);
    // Use stone for courtyard floor
    const floor = new THREE.Mesh(floorGeo, materialCache.stone);
    floor.receiveShadow = true;
    scene.add(floor);

    // 3. Castle Walls (With Battlements)
    const wallHeight = 12;
    const wallThick = 4;
    const wallGeo = new THREE.BoxGeometry(100, wallHeight, wallThick);

    // Helper to create a wall segment
    function createWall(x, z, rotY) {
        const wallGroup = new THREE.Group();

        // Main Wall
        const wall = new THREE.Mesh(wallGeo, materialCache.stone);
        wall.position.y = wallHeight / 2;
        wall.castShadow = true;
        wall.receiveShadow = true;
        wallGroup.add(wall);

        // Battlements (Teeth)
        const toothGeo = new THREE.BoxGeometry(4, 2, wallThick);
        for (let i = -48; i < 48; i += 8) {
            const tooth = new THREE.Mesh(toothGeo, materialCache.stone);
            tooth.position.set(i, wallHeight + 1, 0);
            tooth.castShadow = true;
            tooth.receiveShadow = true;
            wallGroup.add(tooth);
        }

        wallGroup.position.set(x, 0, z);
        wallGroup.rotation.y = rotY;
        scene.add(wallGroup);
    }

    createWall(0, -50, 0);          // Back
    createWall(0, 50, 0);           // Front
    createWall(-50, 0, Math.PI / 2);  // Left
    createWall(50, 0, Math.PI / 2);   // Right

    // 4. Corner Towers
    const towerGeo = new THREE.BoxGeometry(10, 18, 10);
    function createTower(x, z) {
        const tower = new THREE.Mesh(towerGeo, materialCache.stone);
        tower.position.set(x, 9, z);
        tower.castShadow = true;
        tower.receiveShadow = true;
        scene.add(tower);
    }
    createTower(-50, -50);
    createTower(50, -50);
    createTower(-50, 50);
    createTower(50, 50);

    // 5. Nether Portal (Updated)
    const portalGroup = new THREE.Group();
    portalGroup.position.set(0, 0, -46); // Slightly forward from wall

    // Frame
    const colGeo = new THREE.BoxGeometry(3, 10, 3);
    const col1 = new THREE.Mesh(colGeo, materialCache.obsidian);
    col1.position.set(-3.5, 5, 0);
    portalGroup.add(col1);

    const col2 = new THREE.Mesh(colGeo, materialCache.obsidian);
    col2.position.set(3.5, 5, 0);
    portalGroup.add(col2);

    const topGeo = new THREE.BoxGeometry(10, 3, 3);
    const top = new THREE.Mesh(topGeo, materialCache.obsidian);
    top.position.set(0, 9.5, 0);
    portalGroup.add(top);

    const bottom = new THREE.Mesh(topGeo, materialCache.obsidian);
    bottom.position.set(0, 0.5, 0);
    portalGroup.add(bottom);

    // Portal Pane
    const portalMat = new THREE.MeshBasicMaterial({ color: 0xaa00aa });
    const portalPane = new THREE.Mesh(new THREE.PlaneGeometry(6, 8), portalMat);
    portalPane.position.set(0, 5, 0);
    portalGroup.add(portalPane);

    // Light
    const portalLight = new THREE.PointLight(0xaa00aa, 2, 40);
    portalLight.position.set(0, 5, 5);
    portalGroup.add(portalLight);

    portalGroup.name = "NetherPortal";
    scene.add(portalGroup);

    // 6. Random Wooden Crates (Cover)
    const crateGeo = new THREE.BoxGeometry(3, 3, 3);
    for (let i = 0; i < 20; i++) {
        const crate = new THREE.Mesh(crateGeo, materialCache.wood);

        // Random Pos
        const x = (Math.random() - 0.5) * 70;
        const z = (Math.random() - 0.5) * 70;

        if (Math.abs(x) < 8 && Math.abs(z) < 8) continue; // Clear spawn

        crate.position.set(x, 1.5, z);
        crate.castShadow = true;
        crate.receiveShadow = true;
        scene.add(crate);

        // Occasional Stacked Crate
        if (Math.random() > 0.7) {
            const crate2 = new THREE.Mesh(crateGeo, materialCache.wood);
            crate2.position.set(x, 4.5, z);
            crate2.castShadow = true;
            crate2.receiveShadow = true;
            scene.add(crate2);
        }
    }

    // 7. Trees (Updated)
    function addTree(x, z) {
        const tree = new THREE.Group();
        // Trunk
        const trunk = new THREE.Mesh(new THREE.BoxGeometry(1.5, 6, 1.5), materialCache.trunk);
        trunk.position.y = 3;
        trunk.castShadow = true;
        tree.add(trunk);
        // Leaves
        const leaves = new THREE.Mesh(new THREE.BoxGeometry(5, 5, 5), materialCache.leaves);
        leaves.position.y = 6;
        leaves.castShadow = true;
        tree.add(leaves);

        tree.position.set(x, 0, z);
        scene.add(tree);
    }

    addTree(-35, -35);
    addTree(35, -35);
    addTree(-35, 30);
    addTree(35, 30);
}



function onWindowResize() {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
}

function onMouseDown(event) {
    if (!controls.isLocked) return;
    if (isReloading) return;

    if (currentAmmo <= 0) {
        // Maybe play a custom click sound?
        // Trigger small shake to indicate stuck
        return;
    }

    currentAmmo--;
    updateAmmoUI();

    // Recoil
    gun.position.z += 0.2; // Kick back

    // Create Bullet
    const bulletGeometry = new THREE.SphereGeometry(0.05, 8, 8); // Smaller bullet
    const bulletMaterial = new THREE.MeshBasicMaterial({ color: 0x00ffff }); // Cyan bullet
    const bullet = new THREE.Mesh(bulletGeometry, bulletMaterial);

    // Position bullet at Gun muzzle
    const gunWorldPos = new THREE.Vector3();
    gun.getWorldPosition(gunWorldPos);

    // Offset slightly forward to not clip
    const dir = new THREE.Vector3();
    camera.getWorldDirection(dir);

    bullet.position.copy(gunWorldPos).add(dir.multiplyScalar(0.5));

    bullet.userData.velocity = dir.normalize().multiplyScalar(BULLET_SPEED);

    // Remove bullet after 2 seconds to save memory
    bullet.userData.life = 2.0;

    scene.add(bullet);
    bullets.push(bullet);
}

function reload() {
    if (isReloading || currentAmmo === MAX_AMMO) return;

    isReloading = true;
    document.getElementById('ammo').innerText = "RLD";

    // Reload animation (dip gun)
    gun.rotation.x = -Math.PI / 4;

    setTimeout(() => {
        currentAmmo = MAX_AMMO;
        isReloading = false;
        updateAmmoUI();
        gun.rotation.x = 0;
    }, RELOAD_TIME);
}

function updateAmmoUI() {
    document.getElementById('ammo').innerText = currentAmmo;
}


// Spawn Enemy Logic (Nether Portal -> Player)
function spawnEnemy() {
    const enemy = new THREE.Group();

    // Load Texture
    const textureLoader = new THREE.TextureLoader();
    const catTexture = textureLoader.load('cat_face.png');

    // Minecraft Style Head (Cube)
    // Map texture to specific faces? For BoxGeometry, map is applied to all faces by default.
    // If we want it only on the front, we need an array of materials.
    // [Right, Left, Top, Bottom, Front, Back]

    const plainMat = new THREE.MeshStandardMaterial({ color: 0xffffff }); // White body
    const faceMat = new THREE.MeshStandardMaterial({ map: catTexture, color: 0xffffff });

    // Front face is usually index 4 or 5 depending on UVs.
    // Let's try applying to all for now to be sure it's visible, or test array.
    // Applying to ALL faces ensures user sees it no matter what rotation initially.
    // The user asked for "Clearer photo", Cube is best for this.

    const headGeo = new THREE.BoxGeometry(2, 2, 2); // 2x2x2 Cube
    const head = new THREE.Mesh(headGeo, faceMat);
    head.position.y = 1; // Center is 0, so raise it
    head.castShadow = true;
    head.receiveShadow = true;
    enemy.add(head);

    // Spawn at Portal
    // Portal is at (0, 0, -48)
    enemy.position.set(0, 0, -45);

    // Add some random offset so they don't stack perfectly
    enemy.position.x += (Math.random() - 0.5) * 4;

    scene.add(enemy);
    enemies.push(enemy);
}


function resetGame() {
    score = 0;
    currentHealth = MAX_HEALTH;
    updateScore(0);
    updateHealth();
    currentAmmo = MAX_AMMO;
    isReloading = false;
    updateAmmoUI();
    if (gun) gun.rotation.x = 0;

    // Remove all enemies
    for (const enemy of enemies) {
        scene.remove(enemy);
    }
    enemies.length = 0;

    // Remove all bullets
    for (const bullet of bullets) {
        scene.remove(bullet);
    }
    bullets.length = 0;

    controls.getObject().position.set(0, 1.6, 0);
    isGameActive = true;

    document.getElementById('game-over').style.display = 'none';
    document.getElementById('ui-container').style.display = 'block';
}

function gameOver() {
    isGameActive = false;
    document.getElementById('final-score').innerText = score;
    document.getElementById('game-over').style.display = 'block';
    controls.unlock();
}

function updateScore(val) {
    score = val;
    document.getElementById('score').innerText = score;
}

function animate() {
    requestAnimationFrame(animate);

    const time = performance.now();
    const delta = (time - prevTime) / 1000;

    if (gun) {
        // Smooth recoil return
        gun.position.lerp(gunRestPosition, 10 * delta);
    }

    if (controls.isLocked) {

        // --- Movement Logic ---
        // Deceleration (friction)
        velocity.x -= velocity.x * 10.0 * delta;
        velocity.z -= velocity.z * 10.0 * delta;

        // Input
        direction.z = Number(moveForward) - Number(moveBackward);
        direction.x = Number(moveRight) - Number(moveLeft);
        direction.normalize(); // Ensure consistent speed in all directions

        if (moveForward || moveBackward) velocity.z -= direction.z * PLAYER_SPEED * delta;
        if (moveLeft || moveRight) velocity.x -= direction.x * PLAYER_SPEED * delta;

        controls.moveRight(-velocity.x * delta);
        controls.moveForward(-velocity.z * delta);

        // --- Game Logic ---

        // 1. Spawning
        if (time - lastEnemySpawn > SPAWN_RATE) {
            spawnEnemy();
            lastEnemySpawn = time;
            // Increase difficulty? Make spawn rate faster over time?
        }

        // 2. Bullets Update
        for (let i = bullets.length - 1; i >= 0; i--) {
            const b = bullets[i];

            // Move bullet
            b.position.addScaledVector(b.userData.velocity, delta);

            // Life check
            b.userData.life -= delta;
            if (b.userData.life <= 0) {
                scene.remove(b);
                bullets.splice(i, 1);
                continue;
            }

            // Collision with enemies
            // Simple distance check (optimization: use bounding sphere)
            for (let j = enemies.length - 1; j >= 0; j--) {
                const e = enemies[j];
                const dist = b.position.distanceTo(e.position);

                if (dist < 1.5) { // Radius(2)/2 + Radius(0.2) ~= 1.2, give some buffer
                    // HIT!
                    scene.remove(e);
                    enemies.splice(j, 1);
                    scene.remove(b);
                    bullets.splice(i, 1);

                    updateScore(score + 10);
                    break; // Bullet destroyed
                }
            }
        }

        // 3. Enemies Update
        const playerPos = controls.getObject().position;
        for (let i = enemies.length - 1; i >= 0; i--) {
            const e = enemies[i];

            // Move towards player
            const dirToPlayer = new THREE.Vector3().subVectors(playerPos, e.position).setY(0).normalize();
            e.position.addScaledVector(dirToPlayer, enemySpeed * delta);
            e.rotation.y += 2 * delta; // spin effect

            // Collision with Player
            const distToPlayer = e.position.distanceTo(playerPos);
            if (distToPlayer < 2.5) { // Cube is size 2, distance 2.5 is decent buffer
                // Damage Player
                currentHealth--;
                updateHealth();

                // Destroy Enemy
                scene.remove(e);
                enemies.splice(i, 1);

                if (currentHealth <= 0) {
                    gameOver();
                }
            }
        }
    }
    prevTime = time;
    renderer.render(scene, camera);
}

function updateHealth() {
    document.getElementById('health').innerText = currentHealth;
}

// Start Game
init();
animate();


