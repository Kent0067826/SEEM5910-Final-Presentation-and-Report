#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <stdexcept>
#include <unordered_map>
#include <unordered_set>
#include <vector>

namespace ObservedWait {
using EdgeKey = std::uint64_t;
inline EdgeKey edge_key(int from, int to) {
    return (EdgeKey(std::uint32_t(from)) << 32) | std::uint32_t(to);
}
struct Completed {
    std::uint64_t seq, episode;
    int from, to, start, end;
    double blocked;
};
struct Active {
    std::uint64_t episode;
    int from, to, start, snapshot;
    double blocked;
};
struct Price {
    int from=0, to=0;
    double completedCount=0, completedBlocked=0, activeCount=0, activeBlocked=0;
    double ticks=0;
};
// Causal, discounted empirical waiting estimate. Pending episodes contribute
// only waiting already observed, a censored lower bound, not a completed label.
// The zero-wait prior and clipping deliberately limit sparse-data penalties.
class WaitingModel {
    double half_life, prior, clip;
    int tick=-1, latest_observation=-1;
    std::uint64_t last_sequence=0;
    std::unordered_map<EdgeKey,Price> stats;
    std::unordered_set<std::uint64_t> finished_episodes;
    double decay(int dt) const {return std::exp2(-double(std::max(0,dt))/half_life);}
public:
    WaitingModel(double halfLife=300, double priorCount=4, double clipTicks=120):
        half_life(halfLife), prior(priorCount), clip(clipTicks) {
        if(!(std::isfinite(half_life)&&std::isfinite(prior)&&std::isfinite(clip)&&half_life>0&&prior>0&&clip>=0))
            throw std::runtime_error("Invalid waiting estimator parameters");
    }
    void update(int now, const std::vector<Completed>& completed, const std::vector<Active>& active) {
        if(now<tick) throw std::runtime_error("Waiting snapshot moved backwards");
        std::uint64_t input_sequence=0;
        std::unordered_set<std::uint64_t> new_episodes, episodes;
        // Validate the whole snapshot before mutating sufficient statistics.
        for(const auto& e:completed) {
            if(e.seq==0 || e.seq<=input_sequence || e.from<0 || e.to<0 || e.from==e.to || e.start<0 || e.end<=e.start || e.end>now || !std::isfinite(e.blocked) || e.blocked<0 || e.blocked>e.end-e.start)
                throw std::runtime_error("Invalid, unordered or future completed waiting sample");
            input_sequence=e.seq;
            if(e.seq>last_sequence && (finished_episodes.count(e.episode)||!new_episodes.insert(e.episode).second))
                throw std::runtime_error("Repeated completed waiting episode");
        }
        for(const auto& e:active) {
            if(e.from<0 || e.to<0 || e.from==e.to || e.start<0 || e.snapshot>now || e.snapshot<e.start || !std::isfinite(e.blocked) || e.blocked<0 || e.blocked>e.snapshot-e.start)
                throw std::runtime_error("Invalid or future active waiting sample");
            if(finished_episodes.count(e.episode)||new_episodes.count(e.episode)||!episodes.insert(e.episode).second)
                throw std::runtime_error("Duplicate or completed active waiting episode");
        }
        const double factor=tick<0?1:decay(now-tick);
        for(auto& item:stats) {
            auto& s=item.second;s.completedCount*=factor;s.completedBlocked*=factor;
            s.activeCount=s.activeBlocked=0;
        }
        for(const auto& e:completed) {
            if(e.seq<=last_sequence) continue; // Duplicate snapshots cannot relearn labels.
            last_sequence=e.seq;
            finished_episodes.insert(e.episode);
            auto& s=stats[edge_key(e.from,e.to)];s.from=e.from;s.to=e.to;
            const double f=decay(now-e.end);
            s.completedCount+=f;s.completedBlocked+=f*e.blocked;
            latest_observation=std::max(latest_observation,e.end);
        }
        for(const auto& e:active) {
            auto& s=stats[edge_key(e.from,e.to)];s.from=e.from;s.to=e.to;
            s.activeCount+=1;s.activeBlocked+=e.blocked;
            latest_observation=std::max(latest_observation,e.snapshot);
        }
        for(auto& item:stats) {
            auto& s=item.second;
            s.ticks=std::clamp((s.completedBlocked+s.activeBlocked)/(s.completedCount+s.activeCount+prior),0.0,clip);
        }
        tick=now;
    }
    double price(int from,int to) const {
        auto it=stats.find(edge_key(from,to));return it==stats.end()?0:it->second.ticks;
    }
    bool has_prices() const {
        for(const auto& item:stats)if(item.second.ticks>1e-9)return true;
        return false;
    }
    std::vector<Price> prices() const {
        std::vector<Price> result;
        for(const auto& item:stats) if(item.second.ticks>1e-9) result.push_back(item.second);
        std::sort(result.begin(),result.end(),[](const Price& a,const Price& b){return edge_key(a.from,a.to)<edge_key(b.from,b.to);});
        return result;
    }
    double global_mean() const {
        double sum=0,count=prior;
        for(const auto& item:stats) {const auto& s=item.second;sum+=s.completedBlocked+s.activeBlocked;count+=s.completedCount+s.activeCount;}
        return std::clamp(sum/count,0.0,clip);
    }
    int latest_tick() const {return latest_observation;}
    int snapshot_tick() const {return tick;}
    std::uint64_t last_seq() const {return last_sequence;}
};
}
