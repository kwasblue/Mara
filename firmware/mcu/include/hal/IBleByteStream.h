// include/hal/IBleByteStream.h
// Extended byte stream interface for BLE-specific features.
#pragma once

#include "IByteStream.h"

namespace hal {

/// Extended byte stream interface for BLE Serial (SPP).
/// Adds BLE-specific features like client connection detection.
class IBleByteStream : public IByteStream {
public:
    /// Check if a BLE client is connected
    virtual bool hasClient() const = 0;
};

} // namespace hal
