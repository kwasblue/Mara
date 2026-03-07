// src/audio/AudioGraphManager.cpp

#include "audio/AudioGraphManager.h"
#include "audio/DspNodes.h"

#include "core/Debug.h"

// NOTE:
// This implementation assumes AudioGraphManager is in the GLOBAL namespace
// (i.e., NOT wrapped in `namespace audio` in the header).
// DSP types are in `namespace audio`.

void AudioGraphManager::attach(EventBus* bus, CommandRegistry* cmd) {
    bus_ = bus;
    cmd_ = cmd;
}

void AudioGraphManager::begin() {
    // Register commands in your style (adapt to your API)
    //
    // cmd_->registerHandler(AUDIO_CHAIN_SET,
    //   [this](const JsonObjectConst& msg){ handleChainSet(msg); });
    //
    // cmd_->registerHandler(AUDIO_CHAIN_GET,
    //   [this](const JsonObjectConst& msg){ handleChainGet(msg); });

    // Provide a sane default chain
    auto default_chain = std::unique_ptr<audio::DspChain>(new audio::DspChain(44100, 2));
    default_chain->add(std::unique_ptr<audio::DspNode>(new audio::BypassNode()));

    swapChain(std::move(default_chain));

    DBG_PRINTF("[AudioGraph] Default chain loaded\n");
}

bool AudioGraphManager::validateChainMessage(const JsonObjectConst& msg) {
    // Hard limits that protect ESP32
    JsonArrayConst chain = msg["chain"].as<JsonArrayConst>();
    if (!chain) return false;

    const int max_nodes = 8;
    if ((int)chain.size() > max_nodes) return false;

    int sr = msg["sr"] | 44100;
    if (!(sr == 44100 || sr == 48000)) return false;

    int ch = msg["ch"] | 2;
    if (!(ch == 1 || ch == 2)) return false;

    return true;
}

void AudioGraphManager::swapChain(std::unique_ptr<audio::DspChain> new_chain) {
    if (!new_chain) return;

    audio::DspChain* raw = new_chain.release();
    audio::DspChain* old = active_chain_.exchange(raw);

    // MVP-safe cleanup:
    // OK while you are not running a real-time DSP task concurrently.
    // When you add real audio, switch to deferred delete / pool swap.
    if (old) delete old;
}

void AudioGraphManager::handleChainSet(const JsonObjectConst& msg) {
    if (!validateChainMessage(msg)) {
        DBG_PRINTF("[AudioGraph] ChainSet rejected: validation failed\n");
        return;
    }

    auto chain = audio::build_chain_from_json(msg);
    if (!chain) {
        DBG_PRINTF("[AudioGraph] ChainSet rejected: build failed\n");
        return;
    }

    swapChain(std::move(chain));

    DBG_PRINTF("[AudioGraph] Chain swap OK\n");
}

void AudioGraphManager::handleChainGet(const JsonObjectConst& msg) {
    (void)msg;

    // MVP: not implemented
    // Later: store last config JSON and publish it back on 요청.
}
