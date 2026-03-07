#pragma once
#include <Arduino.h>
#include <memory>
#include <string.h>

#include <ArduinoJson.h>

#include "audio/DspChain.h"
#include "audio/DspNodes.h"
#include "audio/BiquadDesign.h"

namespace audio {

static inline bool str_eq(const char* a, const char* b) {
    return a && b && strcmp(a, b) == 0;
}

static inline std::unique_ptr<DspNode>
make_node(const JsonObjectConst& obj, int sr, int ch) {
    const char* t = obj["type"] | "";

    if (str_eq(t, "gain")) {
        float db = obj["db"] | 0.0f;
        return std::unique_ptr<DspNode>(new GainNode(db));
    }

    if (str_eq(t, "hp")) {
        float freq = obj["freq"] | 70.0f;
        float Q    = obj["q"]    | 0.707f;
        auto c = designHighPass((float)sr, freq, Q);
        return std::unique_ptr<DspNode>(new BiquadNode(c, ch));
    }

    if (str_eq(t, "low_shelf")) {
        float freq = obj["freq"] | 120.0f;
        float db   = obj["db"]   | 0.0f;
        float Q    = obj["q"]    | 0.7f;
        auto c = designLowShelf((float)sr, freq, Q, db);
        return std::unique_ptr<DspNode>(new BiquadNode(c, ch));
    }

    if (str_eq(t, "peaking")) {
        float freq = obj["freq"] | 1200.0f;
        float db   = obj["db"]   | 0.0f;
        float Q    = obj["q"]    | 1.0f;
        auto c = designPeaking((float)sr, freq, Q, db);
        return std::unique_ptr<DspNode>(new BiquadNode(c, ch));
    }

    if (str_eq(t, "high_shelf")) {
        float freq = obj["freq"] | 8000.0f;
        float db   = obj["db"]   | 0.0f;
        float Q    = obj["q"]    | 0.7f;
        auto c = designHighShelf((float)sr, freq, Q, db);
        return std::unique_ptr<DspNode>(new BiquadNode(c, ch));
    }

    if (str_eq(t, "limiter")) {
        float thr = obj["threshold_db"] | -3.0f;
        float att = obj["attack_ms"]    | 1.0f;
        float rel = obj["release_ms"]   | 120.0f;
        return std::unique_ptr<DspNode>(new PeakLimiterNode(thr, att, rel, sr, ch));
    }

    if (str_eq(t, "bypass")) {
        return std::unique_ptr<DspNode>(new BypassNode());
    }

    return nullptr;
}

static inline std::unique_ptr<DspChain>
build_chain_from_json(const JsonObjectConst& root) {
    int sr = root["sr"] | 44100;
    int ch = root["ch"] | 2;

    if (!(sr == 44100 || sr == 48000)) return nullptr;
    if (!(ch == 1 || ch == 2)) return nullptr;

    JsonArrayConst arr = root["chain"].as<JsonArrayConst>();
    if (!arr) return nullptr;

    const int max_nodes = 8;
    if ((int)arr.size() > max_nodes) return nullptr;

    auto chain = std::unique_ptr<DspChain>(new DspChain(sr, ch));

    for (JsonObjectConst n : arr) {
        auto node = make_node(n, sr, ch);
        if (!node) return nullptr;
        chain->add(std::move(node));
    }

    return chain;
};
}// namespace audio
