// 3D Point Cloud Face Visualization

// --- Configuration ---
const CONFIG = {
    particleSize: 2.0, // Slightly larger to compensate for lower density
    sampleRate: 3,     // Lower density (Every 3rd pixel)
    depthScale: 30,    // Subtle Micro 3D
    mouseSensitivity: 0.8,
};

// --- Global Variables ---
let scene, camera, renderer;
let particles;
let mouse = { x: 0, y: 0 };
let width, height;
let windowHalfX, windowHalfY;

// --- Initialization ---
function init() {
    const container = document.getElementById('visual-container');
    width = container.clientWidth;
    height = container.clientHeight;
    windowHalfX = width / 2;
    windowHalfY = height / 2;

    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(75, width / height, 0.1, 1000);
    camera.position.z = 500;

    renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(window.devicePixelRatio);
    container.appendChild(renderer.domElement);

    loadImageAndCreateParticles();
    window.addEventListener('resize', onWindowResize);
    document.addEventListener('mousemove', onDocumentMouseMove);
    animate();
}

function loadImageAndCreateParticles() {
    const loader = new THREE.TextureLoader();
    loader.load(FACE_DATA_URL, (texture) => {
        const img = texture.image;
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');

        const w = 300;
        const h = w * (img.height / img.width);

        canvas.width = w;
        canvas.height = h;

        ctx.drawImage(img, 0, 0, w, h);
        const imageData = ctx.getImageData(0, 0, w, h).data;

        createPointCloud(imageData, w, h);
    });
}

function createPointCloud(data, width, height) {
    const geometry = new THREE.BufferGeometry();
    const positions = [];
    const colors = [];

    const offsetX = width / 2;
    const offsetY = height / 2;

    // Radius for Elliptical Mask
    const radiusX = width * 0.48;
    const radiusY = height * 0.55;

    for (let y = 0; y < height; y += CONFIG.sampleRate) {
        for (let x = 0; x < width; x += CONFIG.sampleRate) {
            const index = (y * width + x) * 4;
            const r = data[index];
            const g = data[index + 1];
            const b = data[index + 2];
            const alpha = data[index + 3];

            // 1. Mask Check
            const dx = x - offsetX;
            const dy = y - offsetY;
            if ((dx * dx) / (radiusX * radiusX) + (dy * dy) / (radiusY * radiusY) > 1.0) continue;

            // 2. White Background Removal
            if (r > 240 && g > 240 && b > 240) continue;

            // 3. Brightness Filtering
            const brightness = (r + g + b) / 3;
            if (brightness < 12) continue; // Keep hair visible but remove noise

            // 4. Depth
            const normalizedDistSq = ((dx * dx) / (radiusX * radiusX) + (dy * dy) / (radiusY * radiusY));
            const curvature = Math.cos(Math.sqrt(normalizedDistSq) * (Math.PI / 2)) * 15;
            const detail = (brightness / 255) * CONFIG.depthScale;
            const z = curvature + detail;

            const posX = (x - offsetX) * 1.5;
            const posY = -(y - offsetY) * 1.5;
            const posZ = z;

            positions.push(posX, posY, posZ);

            // 5. COLORS - Extra Bright
            let intensity = (brightness / 255);

            // Boost curve: Make skin super white, hair dark but distinct
            // 0.0 -> 0.4 (Dark Grey)
            // 1.0 -> 2.0 (Super White)
            let val = 0.4 + (intensity * 1.6);

            colors.push(val, val, val);
        }
    }

    geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));

    const material = new THREE.PointsMaterial({
        size: CONFIG.particleSize,
        vertexColors: true,
        transparent: true,
        opacity: 1.0,
        sizeAttenuation: true,
        blending: THREE.AdditiveBlending
    });

    particles = new THREE.Points(geometry, material);
    scene.add(particles);
}

// ... (Interaction/Animation same)

function onDocumentMouseMove(event) {
    mouse.x = (event.clientX - window.innerWidth / 2);
    mouse.y = (event.clientY - window.innerHeight / 2);
}

function animate() {
    requestAnimationFrame(animate);

    if (particles) {
        const targetRotY = mouse.x * 0.001 * CONFIG.mouseSensitivity;
        const targetRotX = mouse.y * 0.001 * CONFIG.mouseSensitivity;

        particles.rotation.x += 0.05 * (targetRotX - particles.rotation.x);
        particles.rotation.y += 0.05 * (targetRotY - particles.rotation.y);

        particles.position.z = Math.sin(Date.now() * 0.001) * 3;
    }

    renderer.render(scene, camera);
}

function onWindowResize() {
    const container = document.getElementById('visual-container');
    if (!container) return;
    width = container.clientWidth;
    height = container.clientHeight;
    windowHalfX = width / 2;
    windowHalfY = height / 2;
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height);
}

init();
