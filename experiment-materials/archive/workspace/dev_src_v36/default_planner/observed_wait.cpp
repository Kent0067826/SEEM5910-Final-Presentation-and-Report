#include "observed_wait.h"
#include "observed_wait_model.h"
#include "window_control.h"
#include <chrono>
#include <cstdlib>
#include <fstream>
#include <limits>
#include <list>
#include <queue>
#include <string>
#include <tuple>

namespace ObservedWait {
namespace {
bool selected=false, observe=false, limited=false, pricing=false, price_switch=false, price_first_leg=false;
double weight=1, budget_ms=8, half_life=300, prior=4, clip=120;
int topk=8, assignments=0, changed=0, evaluated=0, aborts=0, failures=0;
// wait-v4 switches (all default to exact wait-v3 behaviour)
bool mincost_routes=false; double margin=0, vload=0; long long placebo_seed=-1; int placebo_calls=0;
int gated=0, vload_charges=0;
std::unordered_map<EdgeKey,int> round_load; std::vector<EdgeKey> pending_edges;
std::vector<double> dscores;
// wait-v5 switches (defaults reproduce v4)
enum class TieRule {Iter, Fifo, Random, Align, AntiAlign}; TieRule tie_rule=TieRule::Iter; long long tie_seed=1; int tie_calls=0, tie_reorders=0;
double occ_kappa=0, occ_tau=0.1; std::vector<double> occ_hits; double occ_samples=0; int occ_tick=-1; bool occ_any=false;
double path_weight=0; int max_counter_cached=1;
// wait-v6: flow-consistency ties. Regional EWMA of assigned task directions (block x block cells).
int align_block=8; double align_slack=0; std::vector<double> flow_x, flow_y; int flow_rows=0, flow_cols=0, flow_tick=-1;
int align_front_changes=0; int pending_agent=-1, pending_task=-1;
bool route_cache=false; struct LegCost{double penalty; std::vector<EdgeKey> edges;};
std::unordered_map<EdgeKey,LegCost> leg_cache; int leg_hits=0, leg_misses=0;
long long expansions=0;
double selected_wait=0, spent_ms=0;
WaitingModel model;
std::ofstream trace, price_trace;
std::chrono::steady_clock::time_point started, deadline;
std::vector<std::vector<int>> neighbors;
std::vector<int> scores, parents;
std::vector<unsigned> stamps;
unsigned search_id=0;
struct Route {std::vector<int> nodes;std::list<EdgeKey>::iterator lru;};
std::unordered_map<EdgeKey,Route> routes;
std::list<EdgeKey> lru;
int cache_hits=0, cache_misses=0;
struct BudgetExceeded {};
struct RouteUnavailable {};
double parameter(const char* name,double fallback,double low,double high) {
    const char* raw=std::getenv(name);const double x=raw?std::stod(raw):fallback;
    if(!std::isfinite(x)||x<low||x>high)throw std::runtime_error(std::string("Invalid ")+name);
    return x;
}
void check_budget() {if(limited&&std::chrono::steady_clock::now()>=deadline)throw BudgetExceeded{};}
int manhattan(int a,int b,int cols) {return std::abs(a/cols-b/cols)+std::abs(a%cols-b%cols);}
const std::vector<int>& route(int start,int goal,SharedEnvironment* env) {
    check_budget();
    const auto key=edge_key(start,goal);auto found=routes.find(key);
    if(found!=routes.end()) {++cache_hits;lru.splice(lru.begin(),lru,found->second.lru);return found->second.nodes;}
    ++cache_misses;
    if(start<0||goal<0||start>=int(neighbors.size())||goal>=int(neighbors.size())||env->map[start]||env->map[goal])
        throw std::runtime_error("Invalid waiting route endpoint");
    if(++search_id==0) {std::fill(stamps.begin(),stamps.end(),0);search_id=1;}
    // Independent exact grid A*: the original planner's caches/RNG are untouched.
    // Equal f prefers smaller remaining distance, then insertion order.
    using Item=std::tuple<int,int,int,int>;
    std::priority_queue<Item,std::vector<Item>,std::greater<Item>> open;
    int sequence=0;const int h=manhattan(start,goal,env->cols);
    stamps[start]=search_id;scores[start]=0;parents[start]=-1;open.emplace(h,h,sequence++,start);
    bool reached=false;
    while(!open.empty()) {
        if(expansions%128==0)check_budget();
        const auto [f,heuristic,order,v]=open.top();open.pop();
        if(f!=scores[v]+manhattan(v,goal,env->cols))continue;
        ++expansions;
        if(v==goal) {reached=true;break;}
        for(int n:neighbors[v]) {
            const int g=scores[v]+1;
            if(stamps[n]==search_id&&scores[n]<=g)continue;
            stamps[n]=search_id;scores[n]=g;parents[n]=v;
            const int nh=manhattan(n,goal,env->cols);open.emplace(g+nh,nh,sequence++,n);
        }
    }
    if(!reached) {++failures;throw RouteUnavailable{};}
    std::vector<int> path;
    for(int v=goal;v!=-1;v=parents[v])path.push_back(v);
    std::reverse(path.begin(),path.end());check_budget();
    if(routes.size()>=512) {routes.erase(lru.back());lru.pop_back();}
    lru.push_front(key);
    return routes.emplace(key,Route{std::move(path),lru.begin()}).first->second.nodes;
}
double base_price(int from,int to) {
    double p=model.price(from,to);
    // wait-v5 (D4): ECN-like early signal. EWMA occupancy of the entered cell above threshold tau,
    // mapped to kappa ticks at full occupancy. Needs no observed blocking, so it also works on sparse maps.
    if(occ_kappa>0&&to>=0&&to<int(occ_hits.size())&&occ_samples>0) {
        const double o=occ_hits[to]/occ_samples;
        if(o>occ_tau) p+=occ_kappa*(o-occ_tau)/(1-occ_tau);
    }
    return std::min(p,clip);
}
double edge_price(int from,int to) {
    const double p=base_price(from,to);
    if(vload<=0||p<=0) return p;
    auto it=round_load.find(edge_key(from,to));
    return it==round_load.end()?p:p*(1+vload*it->second);
}
// wait-v4 (A): link-state style least-cost leg. Edge cost = 1 + weight*price/ticksPerMove (grid units),
// Manhattan heuristic stays admissible. Returns detour-aware penalty = cost - hop length of shortest leg.
double mincost_leg_uncached(int start,int goal,SharedEnvironment* env,std::vector<EdgeKey>* edges);
double mincost_leg(int start,int goal,SharedEnvironment* env,std::vector<EdgeKey>* edges) {
    // wait-v5 (D6): prices are frozen inside a scheduling call (until a virtual-load charge),
    // so identical legs reuse the least-cost search. Exact, not approximate.
    if(!route_cache) return mincost_leg_uncached(start,goal,env,edges);
    const auto key=edge_key(start,goal); auto it=leg_cache.find(key);
    if(it!=leg_cache.end()) {++leg_hits; if(edges) edges->insert(edges->end(),it->second.edges.begin(),it->second.edges.end()); return it->second.penalty;}
    ++leg_misses; std::vector<EdgeKey> local;
    const double pen=mincost_leg_uncached(start,goal,env,&local);
    if(edges) edges->insert(edges->end(),local.begin(),local.end());
    leg_cache.emplace(key,LegCost{pen,std::move(local)});
    return pen;
}
double mincost_leg_uncached(int start,int goal,SharedEnvironment* env,std::vector<EdgeKey>* edges) {
    check_budget();
    if(start<0||goal<0||start>=int(neighbors.size())||goal>=int(neighbors.size())||env->map[start]||env->map[goal])
        throw std::runtime_error("Invalid waiting route endpoint");
    if(start==goal) return 0;
    if(++search_id==0) {std::fill(stamps.begin(),stamps.end(),0);search_id=1;}
    using Item=std::tuple<double,int,int,int>;
    std::priority_queue<Item,std::vector<Item>,std::greater<Item>> open;
    int sequence=0; const double scale=weight/std::max(1,env->max_counter);
    stamps[start]=search_id;dscores[start]=0;scores[start]=0;parents[start]=-1;
    open.emplace(manhattan(start,goal,env->cols),manhattan(start,goal,env->cols),sequence++,start);
    bool reached=false;
    while(!open.empty()) {
        if(expansions%128==0)check_budget();
        const auto [f,h,order,v]=open.top();open.pop();
        if(f>dscores[v]+manhattan(v,goal,env->cols)+1e-9)continue;
        ++expansions;
        if(v==goal){reached=true;break;}
        for(int n:neighbors[v]) {
            const double g=dscores[v]+1+scale*edge_price(v,n);
            if(stamps[n]==search_id&&dscores[n]<=g+1e-12)continue;
            stamps[n]=search_id;dscores[n]=g;scores[n]=scores[v]+1;parents[n]=v;
            const int nh=manhattan(n,goal,env->cols);open.emplace(g+nh,nh,sequence++,n);
        }
    }
    if(!reached){++failures;throw RouteUnavailable{};}
    if(edges) for(int v=goal;parents[v]!=-1;v=parents[v]) edges->push_back(edge_key(parents[v],v));
    const auto& shortest=route(start,goal,env); // cached hop-shortest length
    return dscores[goal]-double(shortest.size()-1);
}
double task_wait(int agent,int id,SharedEnvironment* env,std::vector<EdgeKey>* edges=nullptr) {
    int current=env->curr_states[agent].location;double wait=0;
    // Free robot candidates start after the immutable prefix. All currently
    // known task errands are considered; future tasks/delays are never read.
    int leg=0;
    for(int goal:env->task_pool.at(id).locations) {
        // v11 (ROBOT_PRICE_LEGS=first): price only the pickup leg, the only part of the trip the choice can avoid.
        if(price_first_leg&&leg++>0) break;
        if(mincost_routes) {
            // Convert the grid-unit detour penalty back to price ticks so the caller's scaling is unchanged.
            wait+=mincost_leg(current,goal,env,edges)*std::max(1,env->max_counter)/std::max(1e-12,weight);
            current=goal; continue;
        }
        const auto& path=route(current,goal,env);
        for(size_t k=1;k<path.size();++k) {
            if(k%128==0)check_budget();
            wait+=edge_price(path[k-1],path[k]);
            if(edges) edges->push_back(edge_key(path[k-1],path[k]));
        }
        current=goal;
    }
    return wait;
}
}
void initialize(SharedEnvironment* env) {
    const char* p=std::getenv("ROBOT_TASK_POLICY");selected=p&&std::string(p)=="observed_wait";
    const char* o=std::getenv("ROBOT_WAIT_OBSERVE");observe=o&&std::string(o)=="1";
    if(selected&&!observe)throw std::runtime_error("observed_wait requires ROBOT_WAIT_OBSERVE=1");
    if(selected)if(const char* gate=std::getenv("ROBOT_POLICY"))
        if(std::string(gate)!="baseline"&&!std::getenv("ROBOT_COMBINE"))throw std::runtime_error("observed_wait requires ROBOT_POLICY=baseline (set ROBOT_COMBINE=1 to stack with a window policy)");
    weight=parameter("ROBOT_TASK_WEIGHT",1,0,100);topk=int(parameter("ROBOT_TASK_TOPK",8,1,128));
    budget_ms=parameter("ROBOT_TASK_BUDGET_MS",8,0,1000);
    half_life=parameter("ROBOT_WAIT_HALF_LIFE",300,1,100000);
    prior=parameter("ROBOT_WAIT_PRIOR",4,0.001,100000);
    clip=parameter("ROBOT_WAIT_CLIP_TICKS",120,0,100000);
    const char* rm=std::getenv("ROBOT_WAIT_ROUTE");mincost_routes=rm&&std::string(rm)=="mincost";
    if(rm&&std::string(rm)!="mincost"&&std::string(rm)!="shortest")throw std::runtime_error("Invalid ROBOT_WAIT_ROUTE");
    margin=parameter("ROBOT_WAIT_MARGIN",0,0,1000);
    vload=parameter("ROBOT_WAIT_VLOAD",0,0,100);
    // Noise-floor control: ignore prices, pick uniformly among candidates tied with the distance-first task.
    placebo_seed=std::llround(parameter("ROBOT_WAIT_PLACEBO_TIE_SEED",-1,-1,1e9));placebo_calls=0;
    const char* tr=std::getenv("ROBOT_TIE_RULE"); const std::string trs=tr?tr:"iter";
    if(trs=="iter")tie_rule=TieRule::Iter; else if(trs=="fifo")tie_rule=TieRule::Fifo; else if(trs=="random")tie_rule=TieRule::Random;
    else if(trs=="align")tie_rule=TieRule::Align; else if(trs=="antialign")tie_rule=TieRule::AntiAlign;
    else throw std::runtime_error("Invalid ROBOT_TIE_RULE");
    tie_seed=std::llround(parameter("ROBOT_TIE_SEED",1,0,1e9));tie_calls=tie_reorders=0;
    occ_kappa=parameter("ROBOT_OCC_KAPPA",0,0,1000); occ_tau=parameter("ROBOT_OCC_TAU",0.1,0,0.99);
    occ_hits.assign(env->map.size(),0); occ_samples=0; occ_tick=-1; occ_any=false;
    path_weight=parameter("ROBOT_PATH_PRICE_WEIGHT",0,0,100);
    align_block=int(parameter("ROBOT_ALIGN_BLOCK",8,1,1024)); align_slack=parameter("ROBOT_ALIGN_SLACK",0,0,1000);
    flow_rows=(env->rows+align_block-1)/align_block; flow_cols=(env->cols+align_block-1)/align_block;
    flow_x.assign(flow_rows*flow_cols,0); flow_y.assign(flow_rows*flow_cols,0); flow_tick=-1; align_front_changes=0;
    price_switch=std::getenv("ROBOT_PRICE_SWITCH")&&std::string(std::getenv("ROBOT_PRICE_SWITCH"))=="1";
    price_first_leg=std::getenv("ROBOT_PRICE_LEGS")&&std::string(std::getenv("ROBOT_PRICE_LEGS"))=="first";
    const char* rc=std::getenv("ROBOT_ROUTE_CACHE"); route_cache=rc&&std::string(rc)=="1"; leg_cache.clear();
    const char* w=std::getenv("ROBOT_WORK_MODE");limited=!(w&&std::string(w)=="fixed");
    model=WaitingModel(half_life,prior,clip);routes.clear();lru.clear();search_id=0;
    if(trace.is_open())trace.close();if(price_trace.is_open())price_trace.close();
    if(selected)if(const char* path=std::getenv("ROBOT_TASK_TRACE")) {trace.open(path);if(!trace)throw std::runtime_error("Cannot open observed task trace");}
    if(observe)if(const char* path=std::getenv("ROBOT_WAIT_PRICE_TRACE")) {price_trace.open(path);if(!price_trace)throw std::runtime_error("Cannot open waiting price trace");}
    if(!selected||(weight==0&&path_weight==0))return;
    neighbors.assign(env->map.size(),{});scores.resize(env->map.size());dscores.resize(env->map.size());parents.resize(env->map.size());stamps.assign(env->map.size(),0);
    for(int v=0;v<int(env->map.size());++v)if(!env->map[v]) {
        const int r=v/env->cols,c=v%env->cols;
        for(auto rc:{std::pair<int,int>{r,c+1},{r+1,c},{r,c-1},{r-1,c}})
            if(rc.first>=0&&rc.first<env->rows&&rc.second>=0&&rc.second<env->cols) {
                const int n=rc.first*env->cols+rc.second;if(!env->map[n])neighbors[v].push_back(n);
            }
    }
}
int path_penalty(int from,int to) {
    // wait-v5 (D5): same causal price injected into the guide-path A* (flow.cpp/search.cpp), in grid units.
    if(!selected||path_weight<=0) return 0;
    const double p=base_price(from,to);
    return p<=0?0:int(std::lround(path_weight*p/max_counter_cached));
}
bool enabled() {return selected&&(weight>0||placebo_seed>=0||tie_rule!=TieRule::Iter);}
void begin(SharedEnvironment* env) {
    started=std::chrono::steady_clock::now();
    assignments=changed=evaluated=aborts=failures=cache_hits=cache_misses=0;expansions=0;selected_wait=0;
    gated=vload_charges=0;round_load.clear();pending_edges.clear();tie_reorders=align_front_changes=0;
    if(observe) {
        if(!env->wait_observation_enabled||env->wait_observation_snapshot_tick!=env->system_timestep)
            throw std::runtime_error("Missing frozen waiting observation snapshot");
        std::vector<Completed> completed;std::vector<Active> active;
        for(const auto& s:env->wait_completed)completed.push_back({s.seq,s.episodeSeq,s.from,s.to,s.startTick,s.endTick,double(s.blockTicks)});
        for(const auto& s:env->wait_active)active.push_back({s.episodeSeq,s.from,s.to,s.startTick,s.snapshotTick,double(s.blockTicks)});
        model.update(env->system_timestep,completed,active);
    }
    if(selected&&occ_kappa>0) {
        // Decay by elapsed ticks with the same half-life as waiting prices; one sample per scheduling snapshot.
        const double f=occ_tick<0?1:std::exp2(-double(std::max(0,env->system_timestep-occ_tick))/half_life);
        for(auto& h:occ_hits) h*=f; occ_samples=occ_samples*f+1; occ_tick=env->system_timestep;
        for(const auto& st:env->curr_states) if(st.location>=0&&st.location<int(occ_hits.size())) occ_hits[st.location]+=1;
        occ_any=true;
    }
    max_counter_cached=std::max(1,env->max_counter);
    if(selected&&(tie_rule==TieRule::Align||tie_rule==TieRule::AntiAlign)) {
        const double f=flow_tick<0?1:std::exp2(-double(std::max(0,env->system_timestep-flow_tick))/half_life);
        for(auto& v:flow_x) v*=f; for(auto& v:flow_y) v*=f; flow_tick=env->system_timestep;
    }
    leg_cache.clear(); leg_hits=leg_misses=0;
    pricing=selected&&weight>0&&(model.has_prices()||occ_any);
    spent_ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-started).count();
}
namespace {
std::pair<double,double> task_dir(int agent,int id,SharedEnvironment* env) {
    const int a=env->curr_states[agent].location; const auto& t=env->task_pool.at(id);
    if(t.locations.empty()) return {0,0};
    const int g=t.locations.front();
    double dx=g%env->cols-a%env->cols, dy=g/env->cols-a/env->cols; const double n=std::hypot(dx,dy);
    return n>0?std::make_pair(dx/n,dy/n):std::make_pair(0.0,0.0);
}
std::pair<double,double> regional_flow(int agent,SharedEnvironment* env) {
    const int a=env->curr_states[agent].location; const int br=(a/env->cols)/align_block, bc=(a%env->cols)/align_block;
    double x=0,y=0;
    for(int r=std::max(0,br-1);r<=std::min(flow_rows-1,br+1);++r) for(int c=std::max(0,bc-1);c<=std::min(flow_cols-1,bc+1);++c) {
        const double w=(r==br&&c==bc)?1.0:0.5; x+=w*flow_x[r*flow_cols+c]; y+=w*flow_y[r*flow_cols+c];
    }
    return {x,y};
}
}
int choose(int agent,const std::vector<std::pair<int,int>>& input,SharedEnvironment* env) {
    pending_edges.clear();
    if(input.empty())return -1;
    // v11 (ROBOT_PRICE_SWITCH=1): leave door congestion to the windows; use prices only while no door line is congested.
    if(price_switch&&RobotWindow::any_line_active()) return input.front().first;
    // wait-v5 (D2): explicit tie rule among tasks with equal distance (input is stable-sorted by distance,
    // iteration order within ties). fifo = smaller task id (older task) first; random = hashed shuffle.
    std::vector<std::pair<int,int>> reordered;
    const std::vector<std::pair<int,int>>* cand=&input;
    if(tie_rule!=TieRule::Iter) {
        reordered=input; ++tie_calls;
        for(size_t a=0;a<reordered.size();) {
            size_t b=a; while(b<reordered.size()&&reordered[b].second==reordered[a].second) ++b;
            if(tie_rule==TieRule::Align||tie_rule==TieRule::AntiAlign) break;
            if(b-a>1) {
                const int before=reordered[a].first;
                if(tie_rule==TieRule::Fifo) std::sort(reordered.begin()+a,reordered.begin()+b);
                else {
                    auto key=[&](int id){std::uint64_t h=std::uint64_t(tie_seed)*0x9E3779B97F4A7C15ull^(std::uint64_t(env->system_timestep)<<24)^(std::uint64_t(agent)<<44)^std::uint64_t(id);
                        h^=h>>33;h*=0xff51afd7ed558ccdull;h^=h>>33;h*=0xc4ceb9fe1a85ec53ull;h^=h>>33;return h;};
                    std::sort(reordered.begin()+a,reordered.begin()+b,[&](const auto& x,const auto& y){return key(x.first)<key(y.first);});
                }
                if(a==0&&reordered[0].first!=before) ++tie_reorders;
            }
            a=b;
        }
        if((tie_rule==TieRule::Align||tie_rule==TieRule::AntiAlign)&&!reordered.empty()) {
            // wait-v6 (flow aggregation): among tasks within `slack` grid units of the nearest, prefer the one whose
            // direction best agrees (align) / disagrees (antialign control) with the regional recent assignment flow.
            const auto flow=regional_flow(agent,env); const double mag=std::hypot(flow.first,flow.second);
            if(mag>0.5) {
                const int limit=reordered.front().second+int(std::floor(align_slack));
                size_t best=0; double best_score=-1e18;
                for(size_t k=0;k<reordered.size()&&reordered[k].second<=limit&&k<size_t(std::max(topk,1));++k) {
                    const auto d=task_dir(agent,reordered[k].first,env);
                    double cs=(d.first*flow.first+d.second*flow.second)/mag; if(tie_rule==TieRule::AntiAlign) cs=-cs;
                    if(cs>best_score+1e-9){best_score=cs;best=k;}
                }
                if(best!=0){ std::rotate(reordered.begin(),reordered.begin()+best,reordered.begin()+best+1); ++align_front_changes; }
            }
        }
        cand=&reordered;
    }
    const auto& candidates=*cand;
    if(placebo_seed>=0) {
        int ties=0; while(ties<int(candidates.size())&&candidates[ties].second==candidates.front().second) ++ties;
        std::uint64_t h=std::uint64_t(placebo_seed)*0x9E3779B97F4A7C15ull^(std::uint64_t(env->system_timestep)<<20)^std::uint64_t(agent)^(std::uint64_t(++placebo_calls)<<40);
        h^=h>>33; h*=0xff51afd7ed558ccdull; h^=h>>33;
        const int pick=int(h%std::uint64_t(ties)); changed+=pick!=0; return candidates[pick].first;
    }
    if(!pricing)return candidates.front().first;
    const auto decision_start=std::chrono::steady_clock::now();
    // Charge only optional observation/forecast work. Original distance
    // evaluation between calls must not consume this supplementary budget.
    deadline=decision_start+std::chrono::microseconds(static_cast<long long>(std::max(0.0,budget_ms-spent_ms)*1000));
    int best_id=candidates.front().first;double best=std::numeric_limits<double>::infinity(),best_wait=0;
    double front_score=std::numeric_limits<double>::infinity(),front_wait=0;
    const bool want_edges=vload>0;
    std::vector<EdgeKey> edges,best_edges,front_edges;
    try {
        for(int k=0;k<std::min(topk,int(candidates.size()));++k) {
            check_budget();edges.clear();
            const double wait=task_wait(agent,candidates[k].first,env,want_edges?&edges:nullptr);
            const double score=candidates[k].second+weight*wait/std::max(1,env->max_counter);
            ++evaluated;
            if(k==0){front_score=score;front_wait=wait;if(want_edges)front_edges=edges;}
            if(score<best) {best=score;best_id=candidates[k].first;best_wait=wait;if(want_edges)best_edges=edges;}
        }
        check_budget();
    }catch(const BudgetExceeded&) {
        spent_ms+=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-decision_start).count();
        ++aborts;pricing=false;return candidates.front().first;
    }catch(const RouteUnavailable&) {
        spent_ms+=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-decision_start).count();
        return candidates.front().first;
    }
    // wait-v4 (B): hysteresis. Deviate from the distance-first task only when the priced
    // advantage exceeds `margin` grid units (route-flap damping for noisy, sparse prices).
    if(best_id!=candidates.front().first&&front_score-best<margin) {
        ++gated;best_id=candidates.front().first;best_wait=front_wait;best_edges.swap(front_edges);
    }
    if(want_edges) pending_edges.swap(best_edges);
    spent_ms+=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-decision_start).count();
    changed+=best_id!=candidates.front().first;selected_wait+=best_wait;return best_id;
}
void assigned(int agent,int task,SharedEnvironment* env) {
    ++assignments;
    if(selected&&(tie_rule==TieRule::Align||tie_rule==TieRule::AntiAlign)&&task>=0) {
        const auto d=task_dir(agent,task,env); const int a=env->curr_states[agent].location;
        const int idx=((a/env->cols)/align_block)*flow_cols+(a%env->cols)/align_block;
        flow_x[idx]+=d.first; flow_y[idx]+=d.second;
    }
    // wait-v4 (C): in-round virtual load. Robots assigned later in the same scheduling call
    // see congested edges on already-committed nominal routes as more expensive (anti-herding).
    if(vload>0) {
        bool cleared=false;
        for(auto e:pending_edges){ if(base_price(int(e>>32),int(e&0xffffffffu))>0){++round_load[e];++vload_charges;cleared=true;} }
        if(cleared) leg_cache.clear(); // prices changed within the round
    }
    pending_edges.clear();
}
void finish(SharedEnvironment* env) {
    if(price_trace) {
        nlohmann::json prices=nlohmann::json::array();
        for(const auto& s:model.prices())prices.push_back({s.from,s.to,s.ticks,s.completedCount,s.activeCount});
        nlohmann::json row={{"type","snapshot"},{"tick",env->system_timestep},{"latestObservationTick",model.latest_tick()},
            {"lastCompletedSeq",model.last_seq()},{"globalMeanTicks",model.global_mean()},{"prices",prices},
            {"halfLifeTicks",half_life},{"priorCount",prior},{"clipTicks",clip}};
        price_trace<<row.dump()<<'\n';price_trace.flush(); // upstream exits via _exit
    }
    if(trace) {
        const double ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-started).count();
        nlohmann::json row={{"policy","observed_wait"},{"tick",env->system_timestep},{"assignments",assignments},
            {"changedVsDistance",changed},{"candidates",evaluated},{"forecastAgents",0},{"forecastEvents",0},
            {"lateEvents",nullptr},{"routeFailures",failures},{"scorePenaltySum",weight*selected_wait/std::max(1,env->max_counter)},
            {"predictedSelectedWaitTicks",selected_wait},{"schedulerMs",ms},{"weight",weight},{"topk",topk},
            {"forecastBudgetMs",budget_ms},{"budgetLimited",limited},{"forecastBudgetAborts",aborts},{"pricingActiveAtEnd",pricing},
            {"optionalWorkMs",spent_ms},{"routeMode",mincost_routes?"mincost":"shortest"},{"marginGrid",margin},
            {"virtualLoad",vload},{"tieRule",tie_rule==TieRule::Iter?"iter":tie_rule==TieRule::Fifo?"fifo":"random"},{"tieFrontChanges",tie_reorders},{"alignFrontChanges",align_front_changes},
            {"occKappa",occ_kappa},{"pathPriceWeight",path_weight},{"legCacheHits",leg_hits},{"legCacheMisses",leg_misses},{"gatedCandidates",gated},{"virtualLoadCharges",vload_charges},
            {"routeCacheHits",cache_hits},{"routeCacheMisses",cache_misses},{"routeExpansions",expansions},
            {"observedPriceEdges",model.prices().size()},{"latestObservationTick",model.latest_tick()},
            {"halfLifeTicks",half_life},{"priorCount",prior},{"clipTicks",clip}};
        trace<<row.dump()<<'\n';trace.flush();
    }
}
}
