const { app, BrowserWindow, protocol, net } = require('electron');
const path = require('path');
const { pathToFileURL } = require('url');

// Define the custom scheme
const SCHEME = 'app';
const HOST = 'u3-draw';
const BASE_URL = `${SCHEME}://${HOST}`;

// Register privileges for the custom scheme
protocol.registerSchemesAsPrivileged([
    {
        scheme: SCHEME,
        privileges: {
            standard: true,
            secure: true,
            supportFetchAPI: true,
            corsEnabled: true
        }
    }
]);

let mainWindow;

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1280,
        height: 800,
        title: "U3 Draw",
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, 'preload.js') // Optional
        },
        autoHideMenuBar: true
    });

    // Load the app using the custom protocol
    mainWindow.loadURL(`${BASE_URL}/index.html`);

    mainWindow.on('closed', function () {
        mainWindow = null;
    });
}

app.on('ready', () => {
    // Handle requests for the custom protocol
    protocol.handle(SCHEME, (request) => {
        try {
            const url = new URL(request.url);
            let pathname = decodeURIComponent(url.pathname);

            // Handle root path
            if (pathname === '/' || !pathname) {
                pathname = '/index.html';
            }

            // Construct the absolute path to the file
            // __dirname is the app root
            // We expect assets to be in 'app' subfolder since we copied build there
            const absolutePath = path.normalize(path.join(__dirname, 'app', pathname));

            // Ensure the path is still within the app directory
            if (!absolutePath.startsWith(path.join(__dirname, 'app'))) {
                return new Response('Forbidden', { status: 403 });
            }

            return net.fetch(pathToFileURL(absolutePath).toString());
        } catch (error) {
            console.error('Protocol Error:', error);
            return new Response('Internal Server Error', { status: 500 });
        }
    });

    createWindow();
});

app.on('window-all-closed', function () {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('activate', function () {
    if (mainWindow === null) {
        createWindow();
    }
});
