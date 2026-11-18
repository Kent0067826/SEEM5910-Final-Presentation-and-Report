#include "task_congestion.h"
#include "task_congestion_model.h"
#include "observed_wait.h"
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <limits>
#include <list>
#include <queue>
#include <stdexcept>
#include <string>
#include <unordered_map>

namespace TaskCongestion {
namespace {
std::string policy="baseline";
double weight=4, age_weight=0, bin_ticks=24, horizon=600;
int topk=8;
bool has_scheduled=false, initial_schedule=true;
bool budget_limited=false, pricing_active=false;
double forecast_budget_ms=8;
int budget_aborts=0, truncated_forecasts=0, cache_hits=0, cache_misses=0;
std::chrono::steady_clock::time_point forecast_deadline;
struct ForecastBudgetExceeded {};
DemandModel demand;
std::vector<std::vector<int>> neighbors;
std::vector<std::array<double,2>> edge_weights;
// Separate from planner heuristic tables: forecasting must not alter baseline
// search caches or RNG state. LRU bounds the memory cost on large public maps.
struct DistanceCache { std::vector<int> distances; std::list<int>::iterator lru; };
std::unordered_map<int,DistanceCache> distances;
std::list<int> lru;
std::vector<std::vector<Exposure>> free_prefixes;
std::ofstream trace;
std::chrono::steady_clock::time_point started;
int assignments=0, changed=0, evaluated=0, forecast_agents=0;
long long events_count=0, late_count=0, route_failures=0;
double penalty_sum=0;

void check_budget() {
    if(budget_limited && std::chrono::steady_clock::now()>=forecast_deadline)
        throw ForecastBudgetExceeded{};
}
void abandon_forecast() {
    pricing_active=false;demand.clear();++budget_aborts;
}

double parameter(const char* name,double fallback,double low,double high) {
    const char* value=std::getenv(name);
    const double v=value?std::stod(value):fallback;
    if(!std::isfinite(v)||v<low||v>high) throw std::runtime_error(std::string("Invalid ")+name);
    return v;
}
int direction(int from,int to,int cols) {
    if(to==from+1) return 0;
    if(to==from+cols) return 1;
    if(to==from-1) return 2;
    return 3;
}
bool free_cell(int row,int col,SharedEnvironment* env) {
    return row>=0&&row<env->rows&&col>=0&&col<env->cols&&!env->map[row*env->cols+col];
}
int local_width(int loc,int axis,SharedEnvironment* env) {
    const int row=loc/env->cols,col=loc%env->cols;
    int width=1;
    for(int sign:{-1,1}) for(int d=1;d<=4;++d) {
        const int r=row+(axis==0?sign*d:0),c=col+(axis==1?sign*d:0);
        if(!free_cell(r,c,env)) break;
        ++width;
    }
    return width;
}
const std::vector<int>& distance_to(int target,SharedEnvironment* env) {
    check_budget();
    auto it=distances.find(target);
    if(it!=distances.end()) {
        ++cache_hits;
        lru.splice(lru.begin(),lru,it->second.lru);
        return it->second.distances;
    }
    ++cache_misses;
    if(distances.size()>=128) {distances.erase(lru.back());lru.pop_back();}
    std::vector<int> ds(env->map.size(),-1),open;
    open.reserve(env->map.size());
    ds[target]=0;open.push_back(target);
    for(size_t head=0;head<open.size();++head) {
        if(head%1024==0) check_budget();
        const int v=open[head];
        for(int next:neighbors[v]) if(ds[next]<0) {ds[next]=ds[v]+1;open.push_back(next);}
    }
    lru.push_front(target);
    return distances.emplace(target,DistanceCache{std::move(ds),lru.begin()}).first->second.distances;
}
void expose(int from,int to,double tick,SharedEnvironment* env,std::vector<Exposure>& out) {
    if(tick>horizon) {++late_count;return;}
    const int low=std::min(from,to),axis=std::abs(from-to)==1?0:1;
    const double w=edge_weights[low][axis];
    if(w<=0) return;
    out.push_back({std::uint64_t(low)*2+axis,from<to?0:1,tick,w});
}

std::vector<Exposure> forecast(int agent,const Task& task,bool new_task,SharedEnvironment* env) {
    check_budget();
    std::vector<Exposure> out;
    int loc=env->system_states[agent].location;
    int ori=env->system_states[agent].orientation;
    int phase=task.idx_next_loc;
    double time=0;
    const int action_ticks=std::max(1,env->max_counter);
    // The executor has already committed this prefix. Its endpoint is the
    // scheduler's curr_states. Replay it before predicting the remaining task.
    if(agent<int(env->staged_actions.size())) {
        bool first=true;
        for(Action a:env->staged_actions[agent]) {
            int duration=action_ticks;
            if(first) duration=std::max(1,action_ticks-env->system_states[agent].counter.count);
            first=false;
            // TaskManager checks the current cell every physical tick, even
            // while an action is incomplete. Advance each errand at most once
            // per tick, including a goal at the prefix's starting cell.
            if(!new_task) for(int dt=1;dt<duration;++dt)
                if(phase<int(task.locations.size())&&loc==task.locations[phase]) ++phase;
            time+=duration;
            if(a==Action::CR) ori=(ori+1)%4;
            else if(a==Action::CCR) ori=(ori+3)%4;
            else if(a==Action::FW) {
                const int deltas[4]={1,env->cols,-1,-env->cols};
                const int next=loc+deltas[(ori+4)%4];
                if(std::find(neighbors[loc].begin(),neighbors[loc].end(),next)!=neighbors[loc].end()) {
                    // Prefix traffic belongs in the committed demand once,
                    // not in each candidate's marginal demand.
                    if(!new_task) expose(loc,next,time,env,out);
                    loc=next;
                }
            }
            if(!new_task && phase<int(task.locations.size())&&loc==task.locations[phase]) ++phase;
        }
    }
    // The official predicted endpoint remains authoritative if a prefix's
    // executor-specific details differ from our nominal replay.
    loc=env->curr_states[agent].location;
    ori=env->curr_states[agent].orientation;
    if(new_task && !initial_schedule) time=std::max(time,double(env->min_planner_communication_time)/std::max(1,env->action_time));
    for(;phase<int(task.locations.size());++phase) {
        check_budget();
        if(time>horizon) {++truncated_forecasts;return out;}
        const int goal=task.locations[phase];
        if(goal<0||goal>=int(neighbors.size())||env->map[goal]) {++route_failures;break;}
        const auto& ds=distance_to(goal,env);
        if(ds[loc]<0) {++route_failures;break;}
        // Consecutive identical errands still require separate task updates.
        if(loc==goal) time+=1;
        while(loc!=goal) {
            if(ds[loc]%64==0) check_budget();
            int next=-1,best_turns=5;
            for(int n:neighbors[loc]) if(ds[n]==ds[loc]-1) {
                const int d=direction(loc,n,env->cols);
                const int delta=(d-ori+4)%4;
                const int turns=std::min(delta,4-delta);
                if(turns<best_turns) {next=n;best_turns=turns;}
            }
            if(next<0) {++route_failures;return out;}
            time+=action_ticks*(1+best_turns);
            // Time only increases: no later edge can re-enter the finite
            // forecast horizon. Avoid BFS/route work that cannot affect cost.
            if(time>horizon) {++truncated_forecasts;return out;}
            expose(loc,next,time,env,out);
            ori=direction(loc,next,env->cols);loc=next;
        }
    }
    return out;
}
}

void initialize(SharedEnvironment* env) {
    policy=std::getenv("ROBOT_TASK_POLICY")?std::getenv("ROBOT_TASK_POLICY"):"baseline";
    if(trace.is_open()) trace.close();
    ObservedWait::initialize(env);
    if(policy=="observed_wait") return;
    if(policy!="baseline"&&policy!="spatial"&&policy!="temporal") throw std::runtime_error("Unknown ROBOT_TASK_POLICY");
    weight=parameter("ROBOT_TASK_WEIGHT",4,0,100);
    topk=int(parameter("ROBOT_TASK_TOPK",8,1,128));
    bin_ticks=parameter("ROBOT_TASK_BIN_TICKS",24,1,10000);
    horizon=parameter("ROBOT_TASK_HORIZON",600,1,100000);
    age_weight=parameter("ROBOT_TASK_AGE",0,0,10);
    forecast_budget_ms=parameter("ROBOT_TASK_BUDGET_MS",8,0,1000);
    const char* work_mode=std::getenv("ROBOT_WORK_MODE");
    budget_limited=!(work_mode && std::string(work_mode)=="fixed");
    has_scheduled=false;
    if(enabled()) {
        const char* gate=std::getenv("ROBOT_POLICY");
        if(gate && std::string(gate)!="baseline" && !std::getenv("ROBOT_COMBINE")) throw std::runtime_error("Task congestion comparison requires ROBOT_POLICY=baseline");
    }
    demand=DemandModel(bin_ticks);
    distances.clear();lru.clear();
    if(trace.is_open()) trace.close();
    if(const char* path=std::getenv("ROBOT_TASK_TRACE")) {
        trace.open(path);if(!trace) throw std::runtime_error("Cannot open ROBOT_TASK_TRACE");
    }
    if(!enabled()) return;
    neighbors.assign(env->map.size(),{});
    edge_weights.assign(env->map.size(),{0,0});
    for(int v=0;v<int(env->map.size());++v) if(!env->map[v]) {
        const int r=v/env->cols,c=v%env->cols;
        for(auto rc:{std::pair<int,int>{r,c+1},{r+1,c},{r,c-1},{r-1,c}})
            if(free_cell(rc.first,rc.second,env)) neighbors[v].push_back(rc.first*env->cols+rc.second);
        for(int axis=0;axis<2;++axis) {
            const int next=v+(axis==0?1:env->cols);
            if(std::find(neighbors[v].begin(),neighbors[v].end(),next)==neighbors[v].end()) continue;
            const int width=std::max(local_width(v,axis,env),local_width(next,axis,env));
            // Price edges in passages up to four cells wide. This is a local
            // geometry proxy, not a certified bottleneck or measured capacity.
            if(width<=4) edge_weights[v][axis]=1.0/width;
        }
    }
}
bool enabled() {return policy=="observed_wait"?ObservedWait::enabled():policy!="baseline"&&weight>0;}
void begin(SharedEnvironment* env,bool need_forecast) {
    started=std::chrono::steady_clock::now();
    ObservedWait::begin(env);
    if(policy=="observed_wait") return;
    forecast_deadline=started+std::chrono::microseconds(static_cast<long long>(forecast_budget_ms*1000));
    budget_aborts=truncated_forecasts=cache_hits=cache_misses=0;
    pricing_active=enabled();
    assignments=changed=evaluated=forecast_agents=0;
    events_count=late_count=route_failures=0;penalty_sum=0;
    initial_schedule=!has_scheduled;has_scheduled=true;
    if(!enabled()||!need_forecast) return;
    demand.clear();
    free_prefixes.assign(env->num_of_agents,{});
    try { for(int a=0;a<env->num_of_agents;++a) {
        check_budget();
        const auto task=env->task_pool.find(env->curr_task_schedule[a]);
        if(task==env->task_pool.end()) {
            Task empty;
            free_prefixes[a]=forecast(a,empty,false,env);
            demand.add(free_prefixes[a]);events_count+=free_prefixes[a].size();
            continue;
        }
        auto events=forecast(a,task->second,false,env);
        demand.add(events);events_count+=events.size();++forecast_agents;
    }
    check_budget();
    } catch(const ForecastBudgetExceeded&) {abandon_forecast();}
}
int choose(int agent,const std::vector<std::pair<int,int>>& candidates,SharedEnvironment* env) {
    if(policy=="observed_wait") return ObservedWait::choose(agent,candidates,env);
    if(candidates.empty()) return -1;
    if(!enabled()||!pricing_active) return candidates.front().first;
    // Other free robots' irrevocable prefixes matter; a candidate must not
    // pay for its own prefix. Restore it afterwards for subsequent robots.
    demand.add(free_prefixes[agent],-1);
    int chosen=candidates.front().first;
    double best=std::numeric_limits<double>::infinity(),selected_penalty=0;
    try { for(int k=0;k<std::min(topk,int(candidates.size()));++k) {
        check_budget();
        const int id=candidates[k].first;
        const auto& task=env->task_pool.at(id);
        auto events=forecast(agent,task,true,env);
        const double raw=demand.cost(events,policy=="temporal");
        const double penalty=weight*raw;
        const double age=std::max(0,env->system_timestep-task.t_revealed);
        const double score=candidates[k].second+penalty-age_weight*age;
        ++evaluated;
        if(score<best) {best=score;chosen=id;selected_penalty=penalty;}
    }
    check_budget();
    } catch(const ForecastBudgetExceeded&) {
        // Never use a partial background or partially evaluated shortlist.
        abandon_forecast();return candidates.front().first;
    }
    changed+=chosen!=candidates.front().first;penalty_sum+=selected_penalty;
    demand.add(free_prefixes[agent]);
    return chosen;
}
void assigned(int agent,int task,SharedEnvironment* env) {
    if(policy=="observed_wait") {ObservedWait::assigned(agent,task,env);return;}
    ++assignments;
    if(!enabled()||!pricing_active) return;
    try {
        auto events=forecast(agent,env->task_pool.at(task),true,env);
        check_budget();
        demand.add(events);events_count+=events.size();
    } catch(const ForecastBudgetExceeded&) {abandon_forecast();}
}
void finish(SharedEnvironment* env) {
    ObservedWait::finish(env);
    if(policy=="observed_wait") return;
    if(!trace) return;
    const double ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-started).count();
    nlohmann::json row={{"policy",policy},{"tick",env->system_timestep},{"assignments",assignments},
        {"changedVsDistance",changed},{"candidates",evaluated},{"forecastAgents",forecast_agents},
        {"forecastEvents",events_count},{"lateEvents",nullptr},{"truncatedForecasts",truncated_forecasts},{"routeFailures",route_failures},
        {"scorePenaltySum",penalty_sum},{"schedulerMs",ms},{"weight",weight},{"topk",topk},
        {"binTicks",bin_ticks},{"horizonTicks",horizon},{"ageWeight",age_weight},
        {"forecastBudgetMs",forecast_budget_ms},{"budgetLimited",budget_limited},
        {"forecastBudgetAborts",budget_aborts},{"pricingActiveAtEnd",pricing_active},
        {"forecastCacheHits",cache_hits},{"forecastCacheMisses",cache_misses}};
    trace<<row.dump()<<'\n';trace.flush();
}
}
