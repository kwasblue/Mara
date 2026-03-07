#pragma once
#include <cstdint>
#include <cstddef>
#include <functional>

class ITransport {
public:
    using FrameHandler = std::function<void(const uint8_t* data, size_t len)>;

    virtual ~ITransport() = default;

    virtual void begin() = 0;
    virtual void loop() = 0;
    virtual bool sendBytes(const uint8_t* data, size_t len) = 0;
    //virtual const char* name() const = 0;

    void setFrameHandler(FrameHandler handler) {
        handler_ = std::move(handler);
    }

protected:
    FrameHandler handler_;
};
