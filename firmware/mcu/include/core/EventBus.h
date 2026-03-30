#pragma once
#include <cstdint>
#include "core/Event.h"

// -----------------------------------------------------------------------------
// EventBus: Enhanced event bus with bounded queue, typed filtering, and stats
//
// Features:
//   - Bounded ring buffer for ISR-safe event queueing
//   - Optional event type filtering per subscriber
//   - Statistics tracking (published, delivered, dropped)
//   - drain() method to process queued events in main loop
//
// Usage:
//   EventBus bus;
//   bus.subscribe(myHandler);                    // All events
//   bus.subscribe(myHandler, EventType::PING);  // Only PING events
//   bus.publishQueued(evt);                      // ISR-safe, queues event
//   bus.publish(evt);                            // Immediate dispatch (non-ISR)
//   bus.drain();                                 // Process queued events
// -----------------------------------------------------------------------------

class EventBus {
public:
    using Handler = void (*)(const Event&);

    // Event type mask for filtering (up to 32 event types)
    using EventMask = uint32_t;
    static constexpr EventMask ALL_EVENTS = 0xFFFFFFFF;

    static constexpr uint8_t MAX_HANDLERS = 16;
    static constexpr uint8_t QUEUE_SIZE = 32;  // Power of 2 for efficient wrapping

    struct Subscription {
        Handler   handler = nullptr;
        EventMask mask    = ALL_EVENTS;  // Which event types to receive
        bool      active  = true;        // Mark-and-sweep: false = pending removal
    };

    struct Stats {
        uint32_t published  = 0;  // Total events published
        uint32_t delivered  = 0;  // Total handler invocations
        uint32_t dropped    = 0;  // Events dropped due to full queue
        uint32_t queuePeak  = 0;  // Peak queue depth observed
    };

    // Subscribe to all events
    void subscribe(Handler h) {
        subscribe(h, ALL_EVENTS);
    }

    // Subscribe to specific event type
    void subscribe(Handler h, EventType type) {
        subscribe(h, eventMask(type));
    }

    // Subscribe with custom mask (multiple event types)
    void subscribe(Handler h, EventMask mask) {
        if (handlerCount_ < MAX_HANDLERS && h != nullptr) {
            subs_[handlerCount_].handler = h;
            subs_[handlerCount_].mask = mask;
            subs_[handlerCount_].active = true;
            ++handlerCount_;
        }
    }

    // Unsubscribe a handler from all events
    // Uses mark-and-sweep: marks inactive, compacts later (safe during dispatch)
    void unsubscribe(Handler h) {
        for (uint8_t i = 0; i < handlerCount_; ++i) {
            if (subs_[i].handler == h) {
                subs_[i].active = false;
                needsCompact_ = true;
            }
        }
    }

    // Unsubscribe a handler from a specific event type
    void unsubscribe(Handler h, EventType type) {
        unsubscribe(h, eventMask(type));
    }

    // Unsubscribe a handler with specific mask
    void unsubscribe(Handler h, EventMask mask) {
        for (uint8_t i = 0; i < handlerCount_; ++i) {
            if (subs_[i].handler == h && subs_[i].mask == mask) {
                subs_[i].active = false;
                needsCompact_ = true;
            }
        }
    }

    // Immediate dispatch (NOT ISR-safe, use from main loop only)
    void publish(const Event& evt) {
        ++stats_.published;
        dispatchEvent(evt);
    }

    // Queue event for later processing (ISR-safe)
    // Returns false if queue is full
    bool publishQueued(const Event& evt) {
        // Calculate next write position
        uint8_t nextHead = (queueHead_ + 1) & (QUEUE_SIZE - 1);

        if (nextHead == queueTail_) {
            // Queue full
            ++stats_.dropped;
            return false;
        }

        queue_[queueHead_] = evt;
        queueHead_ = nextHead;
        ++stats_.published;

        // Track peak queue depth
        uint8_t depth = queueDepth();
        if (depth > stats_.queuePeak) {
            stats_.queuePeak = depth;
        }

        return true;
    }

    // Process all queued events (call from main loop)
    void drain() {
        while (queueTail_ != queueHead_) {
            const Event& evt = queue_[queueTail_];
            queueTail_ = (queueTail_ + 1) & (QUEUE_SIZE - 1);
            dispatchEvent(evt);
        }
    }

    // Get current queue depth
    uint8_t queueDepth() const {
        return (queueHead_ - queueTail_) & (QUEUE_SIZE - 1);
    }

    // Check if queue is empty
    bool queueEmpty() const {
        return queueHead_ == queueTail_;
    }

    // Get statistics
    const Stats& stats() const { return stats_; }

    // Reset statistics
    void resetStats() { stats_ = Stats{}; }

    // Get handler count (for diagnostics)
    uint8_t handlerCount() const { return handlerCount_; }

private:
    // Convert EventType to bit mask
    static EventMask eventMask(EventType type) {
        return static_cast<EventMask>(1) << static_cast<uint8_t>(type);
    }

    // Dispatch event to matching subscribers (only active handlers)
    void dispatchEvent(const Event& evt) {
        EventMask evtMask = eventMask(evt.type);

        for (uint8_t i = 0; i < handlerCount_; ++i) {
            const Subscription& sub = subs_[i];
            if (sub.active && sub.handler && (sub.mask & evtMask)) {
                sub.handler(evt);
                ++stats_.delivered;
            }
        }

        // Compact after dispatch if needed (safe: not iterating anymore)
        if (needsCompact_) {
            compact();
        }
    }

    // Remove inactive subscriptions (called automatically after dispatch)
    void compact() {
        uint8_t writeIdx = 0;
        for (uint8_t readIdx = 0; readIdx < handlerCount_; ++readIdx) {
            if (subs_[readIdx].active) {
                if (writeIdx != readIdx) {
                    subs_[writeIdx] = subs_[readIdx];
                }
                ++writeIdx;
            }
        }
        // Clear remaining slots
        for (uint8_t i = writeIdx; i < handlerCount_; ++i) {
            subs_[i] = Subscription{};
        }
        handlerCount_ = writeIdx;
        needsCompact_ = false;
    }

    // Subscriptions with type filtering
    Subscription subs_[MAX_HANDLERS]{};
    uint8_t      handlerCount_ = 0;
    bool         needsCompact_ = false;  // Mark-and-sweep: pending cleanup

    // Ring buffer queue for ISR-safe publishing
    Event   queue_[QUEUE_SIZE]{};
    uint8_t queueHead_ = 0;  // Next write position
    uint8_t queueTail_ = 0;  // Next read position

    // Statistics
    Stats stats_{};
};
