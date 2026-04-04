#include "config/FeatureFlags.h"

#if HAS_WIFI

#include "command/IStringHandler.h"
#include "command/CommandContext.h"
#include "command/HandlerMacros.h"
#include "core/Clock.h"

// TODO: Migrate to hal::IWifiManager for full platform portability
// Currently uses ESP32 WiFi APIs directly (guarded by HAS_WIFI)
#include <WiFi.h>

namespace {

const char* wifiStatusToString(wl_status_t status) {
    switch (status) {
    case WL_IDLE_STATUS: return "idle";
    case WL_NO_SSID_AVAIL: return "no_ssid";
    case WL_SCAN_COMPLETED: return "scan_completed";
    case WL_CONNECTED: return "connected";
    case WL_CONNECT_FAILED: return "connect_failed";
    case WL_CONNECTION_LOST: return "connection_lost";
    case WL_DISCONNECTED: return "disconnected";
    default: return "unknown";
    }
}

class WifiCommandHandler : public IStringHandler {
public:
    static constexpr const char* CMDS[] = {
        "CMD_WIFI_STATUS",
        "CMD_WIFI_JOIN",
        "CMD_WIFI_DISCONNECT",
        nullptr,
    };

    const char* const* commands() const override { return CMDS; }
    const char* name() const override { return "WifiCommandHandler"; }
    uint32_t requiredCaps() const override { return HandlerCap::WIFI; }

    void handle(const char* cmd, JsonVariantConst payload, CommandContext& ctx) override {
        if (strcmp(cmd, "CMD_WIFI_STATUS") == 0) {
            handleStatus(ctx);
            return;
        }
        if (strcmp(cmd, "CMD_WIFI_JOIN") == 0) {
            handleJoin(payload, ctx);
            return;
        }
        if (strcmp(cmd, "CMD_WIFI_DISCONNECT") == 0) {
            handleDisconnect(ctx);
            return;
        }
        ctx.sendError(cmd, "unknown_command");
    }

private:
    void handleStatus(CommandContext& ctx) {
        JsonDocument resp;
        resp["sta_status"] = wifiStatusToString(WiFi.status());
        resp["sta_connected"] = (WiFi.status() == WL_CONNECTED);
        resp["sta_ip"] = WiFi.localIP().toString();
        resp["ap_active"] = WiFi.softAPgetStationNum() >= 0;
        resp["ap_ip"] = WiFi.softAPIP().toString();
        resp["ap_ssid"] = WiFi.softAPSSID();
        resp["mode"] = wifiModeString();
        ctx.sendAck("CMD_WIFI_STATUS", true, resp);
    }

    // WARNING: If wait_for_connect=true and timeout_ms is large (e.g., 10s),
    // this handler BLOCKS the command task. During this time:
    //   - No other JSON commands are processed
    //   - Host heartbeat responses won't be sent
    //   - Host may fire E-stop due to connection timeout
    // Recommendation: Use wait_for_connect=false and poll WiFi status separately,
    // or use a short timeout (< host heartbeat timeout).
    static constexpr int MAX_SAFE_TIMEOUT_MS = 2000;  // Avoid triggering host timeout

    void handleJoin(JsonVariantConst payload, CommandContext& ctx) {
        const char* ssid = payload["ssid"] | "";
        // Note: password is NOT logged to avoid exposing credentials
        const char* password = payload["password"] | "";
        bool wait_for_connect = payload["wait_for_connect"].isNull() ? true : payload["wait_for_connect"].as<bool>();
        int timeout_ms = payload["timeout_ms"].isNull() ? 10000 : payload["timeout_ms"].as<int>();

        if (!ssid || ssid[0] == '\0') {
            ctx.sendError("CMD_WIFI_JOIN", "missing_ssid");
            return;
        }
        if (timeout_ms < 0) timeout_ms = 0;

        // Warn if timeout exceeds safe limit (may cause host E-stop)
        bool timeout_capped = false;
        if (wait_for_connect && timeout_ms > MAX_SAFE_TIMEOUT_MS) {
            timeout_ms = MAX_SAFE_TIMEOUT_MS;
            timeout_capped = true;
        }

        WiFi.mode(WIFI_AP_STA);
        WiFi.setAutoReconnect(false);
        WiFi.setAutoConnect(false);
        WiFi.begin(ssid, password);

        bool connected = (WiFi.status() == WL_CONNECTED);
        if (wait_for_connect) {
            uint32_t start = mara::getSystemClock().millis();
            while (WiFi.status() != WL_CONNECTED && (mara::getSystemClock().millis() - start) < static_cast<uint32_t>(timeout_ms)) {
                mara::getSystemClock().delay(100);
            }
            connected = (WiFi.status() == WL_CONNECTED);
        }

        JsonDocument resp;
        resp["ssid"] = ssid;
        resp["sta_status"] = wifiStatusToString(WiFi.status());
        resp["sta_connected"] = connected;
        resp["sta_ip"] = WiFi.localIP().toString();
        resp["ap_ip"] = WiFi.softAPIP().toString();
        resp["mode"] = wifiModeString();
        resp["wait_for_connect"] = wait_for_connect;
        resp["timeout_ms"] = timeout_ms;
        if (timeout_capped) {
            resp["timeout_capped"] = true;
            resp["warning"] = "timeout_ms capped to avoid host E-stop";
        }

        ctx.sendAck("CMD_WIFI_JOIN", connected, resp);
    }

    void handleDisconnect(CommandContext& ctx) {
        WiFi.mode(WIFI_AP_STA);
        bool ok = WiFi.disconnect(false, true);

        JsonDocument resp;
        resp["sta_connected"] = (WiFi.status() == WL_CONNECTED);
        resp["sta_status"] = wifiStatusToString(WiFi.status());
        resp["sta_ip"] = WiFi.localIP().toString();
        resp["ap_ip"] = WiFi.softAPIP().toString();
        resp["mode"] = wifiModeString();

        ctx.sendAck("CMD_WIFI_DISCONNECT", ok, resp);
    }

    const char* wifiModeString() const {
        wifi_mode_t mode = WiFi.getMode();
        switch (mode) {
        case WIFI_OFF: return "off";
        case WIFI_STA: return "sta";
        case WIFI_AP: return "ap";
        case WIFI_AP_STA: return "ap_sta";
        default: return "unknown";
        }
    }
};

constexpr const char* WifiCommandHandler::CMDS[];
REGISTER_HANDLER(WifiCommandHandler);

} // namespace

#endif // HAS_WIFI
