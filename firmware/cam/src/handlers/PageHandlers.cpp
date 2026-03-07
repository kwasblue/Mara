#include "handlers/PageHandlers.h"
#include "utils/Logger.h"

static const char* TAG = "Pages";

// Main dashboard page
const char INDEX_HTML[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
    <title>ESP32-CAM</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: Arial, sans-serif; background: #1a1a1a; color: #fff; }
        .header { background: #2d2d2d; padding: 15px; text-align: center; }
        .header h1 { color: #4CAF50; margin-bottom: 5px; }
        .container { max-width: 800px; margin: 0 auto; padding: 20px; }
        .stream-container { background: #000; border-radius: 8px; overflow: hidden;
                           margin-bottom: 20px; text-align: center; }
        .stream-container img { max-width: 100%; height: auto; }
        .controls { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                    gap: 10px; margin-bottom: 20px; }
        .btn { background: #4CAF50; color: white; padding: 12px 20px; border: none;
               border-radius: 4px; cursor: pointer; font-size: 14px; text-decoration: none;
               text-align: center; display: block; }
        .btn:hover { background: #45a049; }
        .btn-secondary { background: #555; }
        .btn-secondary:hover { background: #666; }
        .btn-danger { background: #f44336; }
        .btn-danger:hover { background: #d32f2f; }
        .status { background: #2d2d2d; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        .status-row { display: flex; justify-content: space-between; padding: 5px 0;
                      border-bottom: 1px solid #444; }
        .status-row:last-child { border-bottom: none; }
        .status-label { color: #888; }
        .stream-mode { margin-bottom: 10px; }
        .stream-mode button { margin: 0 5px; }
        .active { background: #4CAF50 !important; }
    </style>
</head>
<body>
    <div class="header">
        <h1>ESP32-CAM</h1>
        <p id="hostname">Loading...</p>
    </div>
    <div class="container">
        <div class="stream-mode">
            <button class="btn btn-secondary" id="btnSnapshot" onclick="showSnapshot()">Snapshot</button>
            <button class="btn active" id="btnStream" onclick="showStream()">Live Stream</button>
        </div>
        <div class="stream-container">
            <img id="stream" src="/stream" alt="Camera Stream">
        </div>
        <div class="controls">
            <button class="btn" id="flashBtn" onclick="toggleFlash()">Toggle Flash</button>
            <a href="/config" class="btn btn-secondary">Settings</a>
            <a href="/update" class="btn btn-secondary">Firmware Update</a>
            <a href="/jpg" class="btn btn-secondary" download="capture.jpg">Download Snapshot</a>
        </div>
        <div class="status" id="status">
            <div class="status-row"><span class="status-label">IP Address</span><span id="ip">-</span></div>
            <div class="status-row"><span class="status-label">WiFi Signal</span><span id="rssi">-</span></div>
            <div class="status-row"><span class="status-label">Free Heap</span><span id="heap">-</span></div>
            <div class="status-row"><span class="status-label">Uptime</span><span id="uptime">-</span></div>
        </div>
    </div>
    <script>
        let isStreaming = true;
        const img = document.getElementById('stream');

        function showSnapshot() {
            isStreaming = false;
            img.src = '/jpg?' + new Date().getTime();
            document.getElementById('btnSnapshot').classList.add('active');
            document.getElementById('btnStream').classList.remove('active');
        }

        function showStream() {
            isStreaming = true;
            img.src = '/stream';
            document.getElementById('btnStream').classList.add('active');
            document.getElementById('btnSnapshot').classList.remove('active');
        }

        function toggleFlash() {
            fetch('/flash', { method: 'POST' })
                .then(r => r.json())
                .then(d => console.log('Flash:', d.flash));
        }

        function updateStatus() {
            fetch('/api/status')
                .then(r => r.json())
                .then(d => {
                    document.getElementById('hostname').textContent = d.hostname + '.local';
                    document.getElementById('ip').textContent = d.ip;
                    document.getElementById('rssi').textContent = d.rssi + ' dBm';
                    document.getElementById('heap').textContent = Math.round(d.freeHeap / 1024) + ' KB';
                    document.getElementById('uptime').textContent = formatUptime(d.uptime);
                })
                .catch(e => console.error('Status update failed:', e));
        }

        function formatUptime(seconds) {
            const h = Math.floor(seconds / 3600);
            const m = Math.floor((seconds % 3600) / 60);
            const s = seconds % 60;
            return h + 'h ' + m + 'm ' + s + 's';
        }

        updateStatus();
        setInterval(updateStatus, 5000);
    </script>
</body>
</html>
)rawliteral";

// Configuration page
const char CONFIG_HTML[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
    <title>ESP32-CAM Settings</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { box-sizing: border-box; }
        body { font-family: Arial, sans-serif; background: #1a1a1a; color: #fff; margin: 0; padding: 20px; }
        .container { max-width: 600px; margin: 0 auto; }
        h1 { color: #4CAF50; margin-bottom: 20px; }
        .section { background: #2d2d2d; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .section h2 { margin-bottom: 15px; font-size: 18px; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; color: #888; }
        select, input[type="text"], input[type="password"], input[type="number"] {
            width: 100%; padding: 10px; background: #444; border: 1px solid #555;
            border-radius: 4px; color: #fff; font-size: 14px;
        }
        input[type="range"] { width: 100%; }
        .range-value { text-align: right; color: #4CAF50; }
        .btn { background: #4CAF50; color: white; padding: 12px 20px; border: none;
               border-radius: 4px; cursor: pointer; font-size: 14px; margin-right: 10px; }
        .btn:hover { background: #45a049; }
        .btn-secondary { background: #555; }
        .btn-danger { background: #f44336; }
        .checkbox-group { display: flex; align-items: center; }
        .checkbox-group input { width: auto; margin-right: 10px; }
        a { color: #4CAF50; }
        .actions { margin-top: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h1><a href="/">&#8592;</a> Camera Settings</h1>

        <div class="section">
            <h2>Image Settings</h2>
            <div class="form-group">
                <label>Resolution</label>
                <select id="frameSize" onchange="updateSetting('frameSize', this.value)">
                    <option value="0">96x96</option>
                    <option value="1">QQVGA (160x120)</option>
                    <option value="2">128x128</option>
                    <option value="3">QCIF (176x144)</option>
                    <option value="4">HQVGA (240x176)</option>
                    <option value="5">240x240</option>
                    <option value="6">QVGA (320x240)</option>
                    <option value="7">CIF (400x296)</option>
                    <option value="8">HVGA (480x320)</option>
                    <option value="9">VGA (640x480)</option>
                    <option value="10">SVGA (800x600)</option>
                    <option value="11">XGA (1024x768)</option>
                    <option value="12">HD (1280x720)</option>
                    <option value="13">SXGA (1280x1024)</option>
                    <option value="14">UXGA (1600x1200)</option>
                </select>
            </div>
            <div class="form-group">
                <label>Quality (0=best, 63=worst)</label>
                <input type="range" id="quality" min="0" max="63" value="12" oninput="updateRange(this)">
                <div class="range-value" id="quality-val">12</div>
            </div>
            <div class="form-group">
                <label>Brightness</label>
                <input type="range" id="brightness" min="-2" max="2" value="0" oninput="updateRange(this)">
                <div class="range-value" id="brightness-val">0</div>
            </div>
            <div class="form-group">
                <label>Contrast</label>
                <input type="range" id="contrast" min="-2" max="2" value="0" oninput="updateRange(this)">
                <div class="range-value" id="contrast-val">0</div>
            </div>
            <div class="form-group">
                <label>Saturation</label>
                <input type="range" id="saturation" min="-2" max="2" value="0" oninput="updateRange(this)">
                <div class="range-value" id="saturation-val">0</div>
            </div>
            <div class="form-group checkbox-group">
                <input type="checkbox" id="hmirror" onchange="updateSetting('hmirror', this.checked)">
                <label for="hmirror">Horizontal Mirror</label>
            </div>
            <div class="form-group checkbox-group">
                <input type="checkbox" id="vflip" onchange="updateSetting('vflip', this.checked)">
                <label for="vflip">Vertical Flip</label>
            </div>
        </div>

        <div class="section">
            <h2>Motion Detection</h2>
            <div class="form-group checkbox-group">
                <input type="checkbox" id="motionEnabled" onchange="updateMotion()">
                <label for="motionEnabled">Enable Motion Detection</label>
            </div>
            <div class="form-group">
                <label>Sensitivity (0-100)</label>
                <input type="range" id="motionSensitivity" min="0" max="100" value="30" oninput="updateRange(this)">
                <div class="range-value" id="motionSensitivity-val">30</div>
            </div>
        </div>

        <div class="actions">
            <button class="btn" onclick="saveAll()">Save All</button>
            <button class="btn btn-secondary" onclick="loadSettings()">Reload</button>
            <button class="btn btn-danger" onclick="factoryReset()">Factory Reset</button>
        </div>
    </div>
    <script>
        function updateRange(el) {
            document.getElementById(el.id + '-val').textContent = el.value;
            updateSetting(el.id, parseInt(el.value));
        }

        function updateSetting(key, value) {
            fetch('/api/camera/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ [key]: value })
            });
        }

        function updateMotion() {
            fetch('/api/motion/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    enabled: document.getElementById('motionEnabled').checked,
                    sensitivity: parseInt(document.getElementById('motionSensitivity').value)
                })
            });
        }

        function loadSettings() {
            fetch('/api/camera/config')
                .then(r => r.json())
                .then(d => {
                    document.getElementById('frameSize').value = d.frameSize;
                    document.getElementById('quality').value = d.quality;
                    document.getElementById('quality-val').textContent = d.quality;
                    document.getElementById('brightness').value = d.brightness;
                    document.getElementById('brightness-val').textContent = d.brightness;
                    document.getElementById('contrast').value = d.contrast;
                    document.getElementById('contrast-val').textContent = d.contrast;
                    document.getElementById('saturation').value = d.saturation;
                    document.getElementById('saturation-val').textContent = d.saturation;
                    document.getElementById('hmirror').checked = d.hmirror;
                    document.getElementById('vflip').checked = d.vflip;
                });

            fetch('/api/motion/config')
                .then(r => r.json())
                .then(d => {
                    document.getElementById('motionEnabled').checked = d.enabled;
                    document.getElementById('motionSensitivity').value = d.sensitivity;
                    document.getElementById('motionSensitivity-val').textContent = d.sensitivity;
                });
        }

        function saveAll() {
            alert('Settings auto-save on change. Settings will persist across reboots.');
        }

        function factoryReset() {
            if (confirm('Reset all settings to defaults? Device will reboot.')) {
                fetch('/api/factory-reset', { method: 'POST' })
                    .then(() => { alert('Resetting...'); location.href = '/'; });
            }
        }

        loadSettings();
    </script>
</body>
</html>
)rawliteral";

PageHandlers::PageHandlers(CameraManager& camera, WiFiManager& wifi)
    : camera_(camera), wifi_(wifi) {}

void PageHandlers::registerHandlers(AsyncWebServer& server) {
    server.on("/", HTTP_GET, [this](AsyncWebServerRequest* request) {
        handleRoot(request);
    });

    server.on("/config", HTTP_GET, [this](AsyncWebServerRequest* request) {
        handleConfig(request);
    });

    LOG_INFO(TAG, "Page handlers registered");
}

void PageHandlers::handleRoot(AsyncWebServerRequest* request) {
    request->send_P(200, "text/html", INDEX_HTML);
}

void PageHandlers::handleConfig(AsyncWebServerRequest* request) {
    request->send_P(200, "text/html", CONFIG_HTML);
}
