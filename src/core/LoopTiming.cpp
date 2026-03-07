#include "core/LoopTiming.h"

namespace mara {

static LoopTiming g_loopTiming;

LoopTiming& getLoopTiming() {
    return g_loopTiming;
}

} // namespace mara
