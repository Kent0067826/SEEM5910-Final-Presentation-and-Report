#pragma once
#include <algorithm>
#include <cmath>
#include <deque>
#include <limits>
#include <string>
#include <unordered_set>
#include <vector>

// A physical-task admission experiment inspired by BBR. This is NOT a TCP
// BBRv3 implementation: there are no packet losses, retransmissions or wire ACKs.
// Time is in execution ticks, rate in confirmed crossings per tick.
namespace RobotWindow {
struct BbrReceipt {
    int sent = 0, delivered_time = 0, first_sent = 0;
    long long delivered = 0, sequence = 0;
    bool app_limited = false;
};

class BbrAdmission {
public:
    void reset(int agents, double initial, int tick_quantum, int now = 0) {
        *this = BbrAdmission();
        max_window_ = agents;
        floor_ = std::min(double(agents), std::max(2.0, initial));
        quantum_ = std::max(1, tick_quantum);
        bootstrap_rtt_ = std::max(24, 2 * quantum_);
        bandwidth_ = floor_ / bootstrap_rtt_;
        window_ = startup_window_ = floor_;
        now_ = last_delivery_ = first_send_ = phase_start_ = round_start_ = now;
        tokens_ = std::min(2.0, floor_);
        set_rates();
    }

    // Called once per newly scheduled first-leg crossing; never from allowed().
    BbrReceipt sent(int now, int inflight_before) {
        if (inflight_before == 0) first_send_ = last_delivery_ = now;
        tokens_ = std::max(0.0, tokens_ - 1.0);
        ++sent_total_;
        return {now, last_delivery_, first_send_, delivered_, sent_total_, app_limited_};
    }

    // Process a physical snapshot as ONE batch. Agent scan order cannot inflate
    // bandwidth by generating several zero-duration samples for simultaneous ACKs.
    void ack_batch(int now, const std::vector<BbrReceipt>& receipts) {
        if (receipts.empty() || now < last_delivery_) return;
        std::vector<BbrReceipt> fresh;
        for (const auto& r : receipts)
            if (r.sequence > 0 && r.sequence <= sent_total_ && now >= r.sent &&
                acked_.insert(r.sequence).second) fresh.push_back(r);
        if (fresh.empty()) return;
        delivered_ += fresh.size();
        round_acks_ += fresh.size();
        const auto newest = std::max_element(fresh.begin(), fresh.end(),
            [](const auto& a, const auto& b) { return a.sequence < b.sequence; });
        for (const auto& r : fresh) {
            const int latency = now - r.sent;
            if (latency > 0) latency_samples_.push_back({now, double(latency)});
        }
        refresh_min_latency(now);
        const int elapsed = std::max({1, now - newest->delivered_time, newest->sent - newest->first_sent});
        const double sample = double(delivered_ - newest->delivered) / elapsed;
        last_sample_ = sample;
        round_nonlimited_ = round_nonlimited_ || !newest->app_limited;
        // No-ACK intervals are never zero-bandwidth measurements. A low sample
        // marked application-limited does not overwrite a capacity estimate.
        if (!newest->app_limited || !have_bandwidth_ || sample >= bandwidth_) {
            rate_samples_.push_back({now, sample});
            have_bandwidth_ = true;
        }
        refresh_bandwidth(now);
        last_delivery_ = now;
        first_send_ = newest->sent;
        if (app_limited_until_ > 0 && delivered_ > app_limited_until_) app_limited_until_ = 0;
        app_limited_ = app_limited_until_ > 0;
        if (phase_ == "STARTUP")
            startup_window_ = std::min(max_window_, startup_window_ + double(fresh.size()));
    }

    void advance(int now, int inflight, bool recent_denial) {
        if (now < now_) return;
        // Credits use elapsed PHYSICAL ticks, so repeated scheduler calls at the
        // same snapshot cannot generate credits. Bound burst for coarse sampling.
        tokens_ += (now - now_) * pacing_rate_;
        now_ = now;
        round_demand_ = round_demand_ || recent_denial;
        const int epoch = epoch_length();
        if (phase_ == "STARTUP" && now - round_start_ >= epoch && round_acks_ > 0) {
            if (round_demand_ && round_nonlimited_) {
                if (bandwidth_ >= full_bandwidth_ * 1.25) { full_bandwidth_ = bandwidth_; plateau_ = 0; }
                else ++plateau_;
            } else plateau_ = 0;
            // Without supplied demand a plateau says little about true capacity.
            if (plateau_ >= 3 || now - phase_start_ >= 8 * epoch) enter("DRAIN", now);
            round_start_ = now; round_acks_ = 0;
            round_demand_ = round_nonlimited_ = false;
        }
        if (phase_ == "DRAIN" && (inflight <= std::max(2.0, bdp()) || now - phase_start_ >= 2 * epoch)) {
            enter("PROBE_BW", now); probe_index_ = 0;
        }
        if (phase_ == "PROBE_BW" && now - phase_start_ >= epoch) {
            probe_index_ = (probe_index_ + 1) % 6;
            phase_start_ = now;
        }
        // ProbeRTT is deliberately omitted in this short, heterogeneous-trip
        // prototype. A rolling physical latency minimum is reported instead.
        window_ = phase_ == "STARTUP" ? startup_window_ : std::max(floor_, std::ceil(2.0 * bdp()));
        window_ = std::min(max_window_, window_);
        set_rates();
        const double burst = std::min(window_, std::max(2.0, std::ceil(pacing_rate_ * quantum_)));
        tokens_ = std::min(tokens_, burst);
    }

    bool can_send(int inflight) const { return inflight < int(std::floor(window_)) && tokens_ >= 1.0 - 1e-9; }
    void demand_observed() {} // Preserve an application-limited flight's watermark.
    void end_schedule(bool any_cross_candidate, int inflight) {
        // Candidate availability is only a proxy for application demand; local
        // greedy selection can still prefer another task. Never classify our own
        // pacing/window denial as application-limited.
        if (!any_cross_candidate && inflight < int(std::floor(window_)))
            app_limited_until_ = std::max(1LL, delivered_ + inflight);
        app_limited_ = app_limited_until_ > 0;
    }
    double window() const { return window_; }
    double bandwidth() const { return bandwidth_; }
    double min_latency() const { return min_rtt_; }
    double pacing_rate() const { return pacing_rate_; }
    double tokens() const { return tokens_; }
    double last_sample() const { return last_sample_; }
    long long delivered() const { return delivered_; }
    bool app_limited() const { return app_limited_; }
    const std::string& phase() const { return phase_; }

private:
    struct Sample { int t; double value; };
    double max_window_ = 40, floor_ = 6, window_ = 6, startup_window_ = 6;
    double bandwidth_ = .2, min_rtt_ = 0, pacing_rate_ = .554, tokens_ = 2;
    double full_bandwidth_ = 0, last_sample_ = 0;
    int quantum_ = 15, bootstrap_rtt_ = 30, now_ = 0, last_delivery_ = 0, first_send_ = 0;
    int phase_start_ = 0, round_start_ = 0, plateau_ = 0, probe_index_ = 0, round_acks_ = 0;
    long long delivered_ = 0, sent_total_ = 0, app_limited_until_ = 0;
    bool have_bandwidth_ = false, app_limited_ = false;
    bool round_demand_ = false, round_nonlimited_ = false;
    std::string phase_ = "STARTUP";
    std::deque<Sample> rate_samples_, latency_samples_;
    std::unordered_set<long long> acked_;
    int epoch_length() const { return std::max(2 * quantum_, int(std::ceil(min_rtt_ > 0 ? min_rtt_ : bootstrap_rtt_))); }
    double bdp() const { return bandwidth_ * (min_rtt_ > 0 ? min_rtt_ : bootstrap_rtt_); }
    void enter(const std::string& state, int now) { phase_ = state; phase_start_ = now; }
    void refresh_min_latency(int now) {
        const int age = 10 * epoch_length();
        while (!latency_samples_.empty() && now - latency_samples_.front().t > age) latency_samples_.pop_front();
        min_rtt_ = std::numeric_limits<double>::infinity();
        for (const auto& s : latency_samples_) min_rtt_ = std::min(min_rtt_, s.value);
        if (!std::isfinite(min_rtt_)) min_rtt_ = 0;
    }
    void refresh_bandwidth(int now) {
        while (!rate_samples_.empty() && now - rate_samples_.front().t > 10 * epoch_length()) rate_samples_.pop_front();
        if (rate_samples_.empty()) return; // retain last estimate through idle gaps
        bandwidth_ = 0;
        for (const auto& s : rate_samples_) bandwidth_ = std::max(bandwidth_, s.value);
    }
    void set_rates() {
        static const double gains[] = {1.25, .9, 1, 1, 1, 1};
        double gain = phase_ == "STARTUP" ? 2.77 : phase_ == "DRAIN" ? .5 : gains[probe_index_];
        // Maintain a bounded probe trickle after long no-delivery periods.
        pacing_rate_ = std::max(1.0 / (8 * bootstrap_rtt_), gain * bandwidth_);
    }
};
}
