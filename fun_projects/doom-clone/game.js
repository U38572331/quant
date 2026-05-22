
import * as THREE from 'three';
import { PointerLockControls } from 'three/addons/controls/PointerLockControls.js';

// --- Global Variables ---
let camera, scene, renderer, controls;
let raycaster;
let moveForward = false;
let moveBackward = false;
let moveLeft = false;
let moveRight = false;
let canJump = false;

let prevTime = performance.now();
const velocity = new THREE.Vector3();
const direction = new THREE.Vector3();
const vertex = new THREE.Vector3();
const color = new THREE.Color();

// Game State
let bullets = [];
let enemies = [];
const objects = []; // For collision (floor, walls) (simplified)
const wallObjects = [];

// Config
const PLAYER_SPEED = 150.0; // Fast movement like Doom
const PLAYER_HEIGHT = 10;

init();
animate();

function init() {
    // 1. Scene Setup
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x111111); // Dark background
    scene.fog = new THREE.Fog(0x111111, 0, 100);  // Spooky fog

    // 2. Camera
    camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 1, 1000);
    camera.position.y = PLAYER_HEIGHT;

    // 3. Lights
    const hemiLight = new THREE.HemisphereLight(0xffffff, 0x444444, 0.4);
    hemiLight.position.set(0, 200, 0);
    scene.add(hemiLight);

    const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
    dirLight.position.set(0, 200, 100);
    dirLight.castShadow = true;
    scene.add(dirLight);

    // 4. Controls
    controls = new PointerLockControls(camera, document.body);

    const startBtn = document.getElementById('startBtn');
    const message = document.getElementById('message');

    startBtn.addEventListener('click', function () {
        controls.lock();
    });

    controls.addEventListener('lock', function () {
        message.style.display = 'none';
    });

    controls.addEventListener('unlock', function () {
        message.style.display = 'flex';
    });

    scene.add(controls.getObject());

    // 5. Input Handling
    const onKeyDown = function (event) {
        switch (event.code) {
            case 'ArrowUp':
            case 'KeyW': moveForward = true; break;
            case 'ArrowLeft':
            case 'KeyA': moveLeft = true; break;
            case 'ArrowDown':
            case 'KeyS': moveBackward = true; break;
            case 'ArrowRight':
            case 'KeyD': moveRight = true; break;
            case 'Space':
                if (canJump === true) velocity.y += 150;
                canJump = false;
                break;
        }
    };

    const onKeyUp = function (event) {
        switch (event.code) {
            case 'ArrowUp':
            case 'KeyW': moveForward = false; break;
            case 'ArrowLeft':
            case 'KeyA': moveLeft = false; break;
            case 'ArrowDown':
            case 'KeyS': moveBackward = false; break;
            case 'ArrowRight':
            case 'KeyD': moveRight = false; break;
        }
    };

    document.addEventListener('keydown', onKeyDown);
    document.addEventListener('keyup', onKeyUp);
    document.addEventListener('mousedown', onMouseDown);

    // 6. Raycaster
    raycaster = new THREE.Raycaster(new THREE.Vector3(), new THREE.Vector3(0, -1, 0), 0, 10);

    // 7. Gun Model (Simple Box for now)
    const gunGeometry = new THREE.BoxGeometry(1, 1, 3);
    const gunMaterial = new THREE.MeshLambertMaterial({ color: 0x333333 });
    const gun = new THREE.Mesh(gunGeometry, gunMaterial);
    gun.position.set(0.5, -0.5, -1); // Relative to camera
    camera.add(gun); // Attach gun to camera

    // 8. Level Generation
    generateLevel();

    // 9. Renderer
    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.shadowMap.enabled = true;
    document.body.appendChild(renderer.domElement);

    // 10. Start Enemies
    spawnEnemies();

    window.addEventListener('resize', onWindowResize);
}

function generateLevel() {
    // Floor
    const floorGeometry = new THREE.PlaneGeometry(2000, 2000, 100, 100);
    floorGeometry.rotateX(-Math.PI / 2);

    const floorMaterial = new THREE.MeshStandardMaterial({
        color: 0x331111, // Dark Red Floor
        roughness: 0.8
    });
    const floor = new THREE.Mesh(floorGeometry, floorMaterial);
    scene.add(floor);

    // Walls
    const wallGeo = new THREE.BoxGeometry(40, 60, 40);
    const wallMat = new THREE.MeshStandardMaterial({ color: 0x555555 });

    // Random pillars
    for (let i = 0; i < 50; i++) {
        const wall = new THREE.Mesh(wallGeo, wallMat);
        wall.position.x = Math.floor(Math.random() * 20 - 10) * 40;
        wall.position.y = 30; // Half height
        wall.position.z = Math.floor(Math.random() * 20 - 10) * 40;

        // Don't spawn on player
        if (Math.abs(wall.position.x) < 20 && Math.abs(wall.position.z) < 20) continue;

        wall.castShadow = true;
        wall.receiveShadow = true;
        scene.add(wall);
        wallObjects.push(wall);
    }
}

function spawnEnemies() {
    const geometry = new THREE.BoxGeometry(10, 20, 10);
    const material = new THREE.MeshStandardMaterial({ color: 0xff0000 }); // Red enemies

    for (let i = 0; i < 10; i++) {
        const enemy = new THREE.Mesh(geometry, material);
        enemy.position.x = Math.floor(Math.random() * 20 - 10) * 40;
        enemy.position.y = 10;
        enemy.position.z = Math.floor(Math.random() * 20 - 10) * 40;

        // Health property
        enemy.userData = { health: 100, id: i };

        scene.add(enemy);
        enemies.push(enemy);
    }
}

function onMouseDown() {
    if (!controls.isLocked) return;

    // Shoot
    shoot();
}

function shoot() {
    // Flash effect
    const flash = new THREE.PointLight(0xffaa00, 1, 30);
    flash.position.set(0.5, -0.5, -2);
    camera.add(flash);
    setTimeout(() => camera.remove(flash), 50);

    // Raycast from camera center
    const raycaster = new THREE.Raycaster();
    raycaster.setFromCamera(new THREE.Vector2(0, 0), camera);

    const intersects = raycaster.intersectObjects(enemies);

    if (intersects.length > 0) {
        const hit = intersects[0];
        const enemy = hit.object;

        // Damage
        enemy.material.color.setHex(0xffffff); // Flash white
        setTimeout(() => enemy.material.color.setHex(0xff0000), 100);

        enemy.userData.health -= 34;
        if (enemy.userData.health <= 0) {
            scene.remove(enemy);
            enemies = enemies.filter(e => e !== enemy);
        }
    }
}

function onWindowResize() {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
}

function animate() {
    requestAnimationFrame(animate);

    const time = performance.now();

    if (controls.isLocked === true) {
        const delta = (time - prevTime) / 1000;

        // Friction
        velocity.x -= velocity.x * 10.0 * delta;
        velocity.z -= velocity.z * 10.0 * delta;
        velocity.y -= 9.8 * 100.0 * delta; // Gravity

        direction.z = Number(moveForward) - Number(moveBackward);
        direction.x = Number(moveRight) - Number(moveLeft);
        direction.normalize(); // Ensure consistent speed in all directions

        if (moveForward || moveBackward) velocity.z -= direction.z * PLAYER_SPEED * delta;
        if (moveLeft || moveRight) velocity.x -= direction.x * PLAYER_SPEED * delta;

        controls.moveRight(-velocity.x * delta);
        controls.moveForward(-velocity.z * delta);

        // Simple Collision (Keep 'y' above floor)
        if (controls.getObject().position.y < PLAYER_HEIGHT) {
            velocity.y = 0;
            controls.getObject().position.y = PLAYER_HEIGHT;
            canJump = true;
        }

        // Enemy AI (Follow player)
        enemies.forEach(enemy => {
            const lookAtVec = new THREE.Vector3(camera.position.x, 10, camera.position.z);
            enemy.lookAt(lookAtVec);
            enemy.translateZ(10 * delta); // Move towards player
        });

    }

    prevTime = time;

    renderer.render(scene, camera);
}
