#pragma once
#include <vector>
#include <memory>
#include "audio/DspNodes.h"

namespace audio {

class DspChain {
public:
    DspChain(int sr, int ch) : sr_(sr), ch_(ch) {}

    void add(std::unique_ptr<DspNode> node) {
        nodes_.push_back(std::move(node));
    }

    void process(float* interleaved, size_t frames) {
        for (auto& n : nodes_) n->process(interleaved, frames, ch_);
    }

    int sr() const { return sr_; }
    int ch() const { return ch_; }

private:
    int sr_;
    int ch_;
    std::vector<std::unique_ptr<DspNode>> nodes_;
}; 

}// namespace audio
