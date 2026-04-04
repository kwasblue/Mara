// include/hal/IByteStream.h
// Abstract byte stream interface for serial-like communication.
// Used by transports to abstract away HardwareSerial, BluetoothSerial, etc.
#pragma once

#include <cstddef>
#include <cstdint>

namespace hal {

/// Abstract byte stream interface.
/// Covers serial ports, BLE SPP, and other byte-oriented streams.
///
/// Usage:
///   IByteStream* stream = ...;
///   stream->begin(115200);
///   while (stream->available() > 0) {
///       uint8_t b = stream->read();
///   }
///   stream->write(data, len);
class IByteStream {
public:
    virtual ~IByteStream() = default;

    /// Initialize the stream with the given baud rate (where applicable)
    virtual void begin(uint32_t baud = 0) = 0;

    /// Number of bytes available to read
    virtual int available() = 0;

    /// Read a single byte. Returns -1 if no data available.
    virtual int read() = 0;

    /// Write bytes to the stream
    /// @return Number of bytes written
    virtual size_t write(const uint8_t* data, size_t len) = 0;

    /// Flush output buffer (where applicable)
    virtual void flush() {}

    /// Close/end the stream
    virtual void end() {}
};

} // namespace hal
