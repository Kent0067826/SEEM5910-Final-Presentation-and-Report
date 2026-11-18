#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <unordered_map>
#include <vector>

namespace TaskCongestion {
struct Exposure {
    std::uint64_t resource;
    int direction;
    double tick;
    double weight;
};
// Piecewise-linear arrival uncertainty over two adjacent bins. Temporal mode
// uses the dot product of these kernels; spatial mode discards bin labels.
// Costs are interaction proxies, NOT measured seconds or an optimality bound.
class DemandModel {
    struct Load {
        std::array<double,2> total{0,0};
        std::unordered_map<int,std::array<double,2>> bins;
    };
    std::unordered_map<std::uint64_t,Load> loads;
    double bin_ticks;
    template<class F> void bins(double tick, F callback) const {
        const double phase = std::max(0.0,tick) / bin_ticks;
        const int k = int(std::floor(phase));
        callback(k, 1.0-(phase-k));
        callback(k+1, phase-k);
    }
public:
    explicit DemandModel(double width=24):bin_ticks(std::max(1.0,width)){}
    void clear() { loads.clear(); }
    void add(const std::vector<Exposure>& events, double scale=1) {
        for(const auto& e:events) {
            auto& l=loads[e.resource];
            l.total[e.direction]+=scale;
            bins(e.tick,[&](int k,double v){l.bins[k][e.direction]+=scale*v;});
        }
    }
    double cost(const std::vector<Exposure>& events, bool temporal) const {
        double result=0;
        for(const auto& e:events) {
            auto it=loads.find(e.resource);
            if(it==loads.end()) continue;
            std::array<double,2> demand{0,0};
            if(!temporal) demand=it->second.total;
            else bins(e.tick,[&](int k,double v){
                auto b=it->second.bins.find(k);
                if(b!=it->second.bins.end()) for(int d=0;d<2;++d) demand[d]+=v*b->second[d];
            });
            result+=e.weight*(0.25*std::max(0.0,demand[e.direction])+std::max(0.0,demand[1-e.direction]));
        }
        return result;
    }
};
}
