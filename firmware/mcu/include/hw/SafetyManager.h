#pragma once

class SafetyManager {
public:
    void estop()       { estopActive_ = true; }
    void clearEstop()  { estopActive_ = false; }
    bool isEstopActive() const { return estopActive_; }

private:
    bool estopActive_ = false;
};
