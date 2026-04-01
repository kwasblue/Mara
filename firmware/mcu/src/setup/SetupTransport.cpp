#include <Arduino.h>

#include "setup/ISetupModule.h"
#include "core/ServiceContext.h"
#include "core/IModule.h"
#include "command/MessageRouter.h"
#include "command/CommandRegistry.h"
#include "core/MCUHost.h"

namespace {

class SetupTransportModule : public mara::ISetupModule {
public:
    const char* name() const override { return "Transport"; }
    bool isCritical() const override { return true; }  // No transport = no commands = unsafe

    mara::Result<void> setup(mara::ServiceContext& ctx) override {
        if (!ctx.commands || !ctx.router || !ctx.host) {
            return mara::Result<void>::err(mara::ErrorCode::NotInitialized);
        }

        // Note: Handlers are already registered in ServiceStorage.initCommands()

        ctx.commands->setup();
        ctx.router->setup();

        // Set up router loop callback
        ctx.host->setRouterLoop([ctx]() {
            if (ctx.router) {
                ctx.router->loop();
            }
        });

        // Add modules to host (legacy pattern - these modules take constructor deps)
        if (ctx.heartbeat) ctx.host->addModule(ctx.heartbeat);
        if (ctx.logger)    ctx.host->addModule(ctx.logger);
        if (ctx.identity)  ctx.host->addModule(ctx.identity);
        if (ctx.benchmark) ctx.host->addModule(ctx.benchmark);

        // Setup host with ServiceContext for self-registered modules
        ctx.host->setup(&ctx);

        Serial.println("[TRANSPORT] Router and host configured");

        return mara::Result<void>::ok();
    }
};

SetupTransportModule g_setupTransport;

} // anonymous namespace

mara::ISetupModule* getSetupTransportModule() {
    return &g_setupTransport;
}
