#include "network/OTAHandler.h"
#include "network/WebServer.h"
#include "utils/Logger.h"

static const char* TAG = "OTA";

// OTA upload page HTML
static const char OTA_PAGE[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
    <title>ESP32-CAM Firmware Update</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #1a1a1a; color: #fff; }
        .container { max-width: 500px; margin: 0 auto; }
        h1 { color: #4CAF50; }
        .upload-form { background: #2d2d2d; padding: 20px; border-radius: 8px; }
        input[type="file"] { margin: 10px 0; }
        button { background: #4CAF50; color: white; padding: 10px 20px; border: none;
                 border-radius: 4px; cursor: pointer; font-size: 16px; }
        button:hover { background: #45a049; }
        button:disabled { background: #666; cursor: not-allowed; }
        .progress { width: 100%; height: 20px; background: #444; border-radius: 10px;
                    margin: 10px 0; overflow: hidden; display: none; }
        .progress-bar { height: 100%; background: #4CAF50; width: 0%;
                        transition: width 0.3s; }
        .status { margin-top: 10px; padding: 10px; border-radius: 4px; display: none; }
        .success { background: #4CAF50; }
        .error { background: #f44336; }
        .warning { background: #ff9800; color: #000; padding: 10px; border-radius: 4px;
                   margin-bottom: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Firmware Update</h1>
        <div class="warning">
            Warning: Do not disconnect power during update!
        </div>
        <div class="upload-form">
            <form id="uploadForm" enctype="multipart/form-data">
                <input type="file" name="firmware" id="firmware" accept=".bin">
                <br><br>
                <button type="submit" id="uploadBtn">Upload Firmware</button>
            </form>
            <div class="progress" id="progress">
                <div class="progress-bar" id="progressBar"></div>
            </div>
            <div class="status" id="status"></div>
        </div>
    </div>
    <script>
        document.getElementById('uploadForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const file = document.getElementById('firmware').files[0];
            if (!file) { alert('Please select a file'); return; }

            const formData = new FormData();
            formData.append('firmware', file);

            document.getElementById('uploadBtn').disabled = true;
            document.getElementById('progress').style.display = 'block';
            document.getElementById('status').style.display = 'none';

            const xhr = new XMLHttpRequest();
            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable) {
                    const pct = Math.round((e.loaded / e.total) * 100);
                    document.getElementById('progressBar').style.width = pct + '%';
                }
            });

            xhr.onload = () => {
                const status = document.getElementById('status');
                status.style.display = 'block';
                if (xhr.status === 200) {
                    status.className = 'status success';
                    status.textContent = 'Update successful! Rebooting...';
                    setTimeout(() => { location.reload(); }, 5000);
                } else {
                    status.className = 'status error';
                    status.textContent = 'Update failed: ' + xhr.responseText;
                    document.getElementById('uploadBtn').disabled = false;
                }
            };

            xhr.onerror = () => {
                const status = document.getElementById('status');
                status.style.display = 'block';
                status.className = 'status error';
                status.textContent = 'Upload failed. Check connection.';
                document.getElementById('uploadBtn').disabled = false;
            };

            xhr.open('POST', '/update');
            xhr.send(formData);
        });
    </script>
</body>
</html>
)rawliteral";

OTAHandler::OTAHandler() {}

void OTAHandler::registerHandlers(AsyncWebServer& server, bool requireAuth) {
    // OTA page
    server.on("/update", HTTP_GET, [this](AsyncWebServerRequest* request) {
        handleUploadPage(request);
    });

    // OTA upload handler
    server.on("/update", HTTP_POST,
        [this](AsyncWebServerRequest* request) {
            handleUploadComplete(request);
        },
        [this](AsyncWebServerRequest* request, const String& filename,
               size_t index, uint8_t* data, size_t len, bool final) {
            handleUpload(request, filename, index, data, len, final);
        }
    );

    LOG_INFO(TAG, "OTA handlers registered");
}

void OTAHandler::handleUploadPage(AsyncWebServerRequest* request) {
    request->send_P(200, "text/html", OTA_PAGE);
}

void OTAHandler::handleUpload(AsyncWebServerRequest* request, const String& filename,
                              size_t index, uint8_t* data, size_t len, bool final) {
    if (index == 0) {
        LOG_INFO(TAG, "Update starting: %s", filename.c_str());
        updating_ = true;
        progress_ = 0;
        error_ = "";
        receivedSize_ = 0;

        // Get content length from header
        if (request->hasHeader("Content-Length")) {
            totalSize_ = request->header("Content-Length").toInt();
        } else {
            totalSize_ = 0;
        }

        if (!Update.begin(UPDATE_SIZE_UNKNOWN)) {
            error_ = "Update.begin failed";
            LOG_ERROR(TAG, "%s", error_.c_str());
            updating_ = false;
            return;
        }
    }

    if (updating_ && len > 0) {
        if (Update.write(data, len) != len) {
            error_ = "Update.write failed";
            LOG_ERROR(TAG, "%s", error_.c_str());
            updating_ = false;
            return;
        }

        receivedSize_ += len;
        if (totalSize_ > 0) {
            progress_ = (receivedSize_ * 100) / totalSize_;
        }
    }

    if (final) {
        if (Update.end(true)) {
            LOG_INFO(TAG, "Update complete, size: %u", receivedSize_);
            progress_ = 100;
        } else {
            error_ = "Update.end failed";
            LOG_ERROR(TAG, "%s", error_.c_str());
        }
        updating_ = false;
    }
}

void OTAHandler::handleUploadComplete(AsyncWebServerRequest* request) {
    if (Update.hasError()) {
        WebServerManager::sendError(request, 500, error_.length() > 0 ? error_ : "Update failed");
    } else {
        WebServerManager::sendSuccess(request, "Update successful, rebooting...");
        delay(500);
        ESP.restart();
    }
}
