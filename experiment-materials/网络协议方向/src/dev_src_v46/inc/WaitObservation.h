#pragma once
#include <cstdint>
#include <deque>
#include <string>
#include <utility>
#include <vector>

// Read-only execution measurements. Collector belongs to the simulation
// thread; planner snapshots contain independent value copies, never aliases.
namespace WaitObservation {

struct Active {
    std::uint64_t episodeSeq = 0;
    int agent = -1, from = -1, to = -1;
    int startTick = 0, snapshotTick = 0;
    int blockTicks = 0, delayTicks = 0, timeoutTicks = 0, observedTicks = 0;
};

struct Sample : Active {
    std::uint64_t seq = 0; // Terminal-event order, including cancelled episodes.
    int endTick = 0;
};

struct Terminal {
    Sample sample;
    bool completed = false;
    std::string reason;
};

class Collector {
    struct Slot {
        bool active = false;
        int lastTick = -1;
        Active value;
    };
    std::vector<Slot> slots;
    std::deque<Sample> pendingCompleted;
    std::vector<Terminal> pendingTrace;
    std::uint64_t nextEpisode = 1, nextTerminal = 1;
    bool traceEnabled = false;

    void close(Slot& slot, int tick, bool completed, const char* reason) {
        Sample sample;
        static_cast<Active&>(sample) = slot.value;
        sample.seq = nextTerminal++;
        sample.endTick = tick;
        sample.snapshotTick = tick;
        if (completed) pendingCompleted.push_back(sample);
        if (traceEnabled) pendingTrace.push_back({sample, completed, reason});
        slot.active = false;
    }

public:
    void configure(int agents, bool keepTrace = false) {
        slots.assign(agents, Slot{});
        pendingCompleted.clear(); pendingTrace.clear();
        nextEpisode = nextTerminal = 1;
        traceEnabled = keepTrace;
    }

    // A new plan can shorten its retained prefix before the next physical
    // tick. Reconcile at a snapshot without opening an episode or counting
    // another tick of waiting.
    void reconcile_front(int tick, int agent, int from, int to, bool forward) {
        auto& slot = slots.at(agent);
        if (slot.active && (!forward || slot.value.from != from || slot.value.to != to))
            close(slot, tick, false, !forward ? "front_action_changed" : "edge_or_position_changed");
    }

    // Called after this tick's external delay update and any timeout ticks.
    // The interval being observed is [tick, tick+1). The caller supplies a
    // geometrically valid directed FW edge, or forward=false otherwise.
    void before_step(int tick, int agent, int from, int to, bool forward,
                     bool stop, bool ownDelay) {
        auto& slot = slots.at(agent);
        if (tick <= slot.lastTick) return; // Defensive same-tick idempotence.
        slot.lastTick = tick;
        reconcile_front(tick, agent, from, to, forward);
        if (!forward) return;
        if (!slot.active) {
            slot.active = true;
            slot.value = Active{};
            slot.value.episodeSeq = nextEpisode++;
            slot.value.agent = agent; slot.value.from = from; slot.value.to = to;
            slot.value.startTick = tick;
        }
        auto& active = slot.value;
        ++active.observedTicks;
        if (ownDelay) ++active.delayTicks;
        else if (stop) ++active.blockTicks;
        active.snapshotTick = tick + 1;
    }

    // Only the action model's actual position can complete a sample.
    void after_step(int tickEnd, int agent, int actualLocation) {
        auto& slot = slots.at(agent);
        if (!slot.active || slot.lastTick + 1 != tickEnd) return;
        if (actualLocation == slot.value.to)
            close(slot, tickEnd, true, "completed");
        else if (actualLocation != slot.value.from)
            close(slot, tickEnd, false, "unexpected_actual_position");
    }

    // Simulator wall-time penalties advance its clock without model->step.
    // Keep them separate: they are neither TPG blocking nor sampled delay.
    void timeout_wait(int steps, int tickEnd) {
        if (steps <= 0) return;
        for (auto& slot : slots) if (slot.active) {
            slot.value.timeoutTicks += steps;
            slot.value.snapshotTick = tickEnd;
        }
    }

    // Consume only terminal samples available by the frozen planner snapshot.
    // Repeating a snapshot cannot deliver a completed sample twice. Active
    // records are cumulative and must be keyed by episodeSeq by consumers.
    void snapshot(int tick, std::vector<Sample>& completed, std::vector<Active>& active) {
        completed.clear();
        while (!pendingCompleted.empty() && pendingCompleted.front().endTick <= tick) {
            completed.push_back(pendingCompleted.front());
            pendingCompleted.pop_front();
        }
        copy_active(tick, active);
    }

    // Used at simulation end to retain right-censored episodes without
    // consuming planner delivery samples or changing any episode state.
    void copy_active(int tick, std::vector<Active>& active) const {
        active.clear();
        for (const auto& slot : slots)
            if (slot.active && slot.value.snapshotTick <= tick) {
                active.push_back(slot.value);
                active.back().snapshotTick = tick;
            }
    }

    std::vector<Terminal> take_trace() {
        std::vector<Terminal> result;
        result.swap(pendingTrace);
        return result;
    }
};
}
