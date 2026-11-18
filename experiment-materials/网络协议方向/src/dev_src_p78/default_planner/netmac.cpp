#include <array>
#include "netmac.h"
#include "pibt.h"
#include "utils.h"
#include "window_control.h"
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <stdexcept>
#include <string>
#include <unistd.h>
#include "nlohmann/json.hpp"
namespace DefaultPlanner { namespace NetMac {
namespace {
bool hdx=false, bo=false; double mp_kappa=0; int hdx_hold=8, hdx_stall=3, hdx_maxlen=1000000, bo_k=2, bo_maxexp=5; long long seed=1;
double param(const char* n,double d,double lo,double hi){const char* r=std::getenv(n);double x=r?std::stod(r):d; if(!(x>=lo&&x<=hi))throw std::runtime_error(std::string("Invalid ")+n); return x;}
// ---- corridor links (maximal chains of degree-2 cells)
struct Link { std::vector<int> cells; int outA=-1, outB=-1; int dir=0; int hold=0; int inside=0; int stall=0; int last_dir=0; int qA=0,qB=0; bool open=false; };
std::vector<Link> links; std::vector<int> link_of, pos_in;   // per cell
std::vector<int> desired, backlog, loc_now, agent_side, stuck, bo_exp, bo_until, last_h;
long long step=0; long long st_denied=0, st_backoffs=0, st_headon=0, st_stall_open=0, st_steps=0;
int degree(SharedEnvironment* env,int v){ if(env->map[v]) return 0; int r=v/env->cols,c=v%env->cols,d=0;
    if(c+1<env->cols&&!env->map[v+1])++d; if(c>0&&!env->map[v-1])++d; if(r+1<env->rows&&!env->map[v+env->cols])++d; if(r>0&&!env->map[v-env->cols])++d; return d; }
std::vector<int> nbrs(SharedEnvironment* env,int v){ std::vector<int> o; int r=v/env->cols,c=v%env->cols;
    if(c+1<env->cols&&!env->map[v+1])o.push_back(v+1); if(r+1<env->rows&&!env->map[v+env->cols])o.push_back(v+env->cols);
    if(c>0&&!env->map[v-1])o.push_back(v-1); if(r>0&&!env->map[v-env->cols])o.push_back(v-env->cols); return o; }
std::uint64_t mix(std::uint64_t h){h^=h>>33;h*=0xff51afd7ed558ccdull;h^=h>>33;h*=0xc4ceb9fe1a85ec53ull;h^=h>>33;return h;}
// entering direction: +1 = entering at A side (A->B), -1 = entering at B side
int entry_dir(const Link& L,int from){ return from==L.outA?1:(from==L.outB?-1:0); }
// ---- v19b/v20: bridge / link MAC. One direction at a time through a single-lane passage, and the apron (cells within
// ROBOT_BMAC_APRON steps of it) on the receiving side is kept clear of robots that want to cross the other way (like RTS/CTS
// clearing the receiver's neighbourhood). Switch when the other side waits and the current side is empty (or has held for
// ROBOT_BMAC_HOLD steps), after the current side's crossers have drained out of the apron.
//  - cut passages ("bridges", RobotWindow): a robot is a crosser if its goal lies in the other part (ROBOT_BMAC=1).
//  - v20 links (ROBOT_LMAC=1): short 1-wide passages (<= ROBOT_LMAC_MAXLEN cells) that are not cuts but whose detour is
//    >= ROBOT_LMAC_DETOUR cells; a robot is a crosser if its guide path enters the passage soon from its side.
bool bm_chainfree=false;   // v27b: a robot inside one passage is not held by the apron rules of another passage
bool bmac=false, bm_evac=false, lmac=false; int bm_apron=2, bm_hold=40, bm_near=8, lm_maxlen=4, lm_detour=20;
// v25e: ROBOT_LMAC_GATE_DETOUR=g -- only cuts and links whose detour is >= g count for passage_count() (the global-cap gate);
// default = ROBOT_LMAC_DETOUR, i.e. every managed passage counts, as before
int lm_gate_detour=-1; int long_passages=0;
struct BM { bool cut=true; int bidx=-1; std::vector<int> cells; int ap=-1; int dir=-1, hold=0; bool drain=false; long long switches=0, denied=0; int owait=0;
            std::vector<int> gate;   // v32: robots waiting on the active side when its turn began (gated service)
            int nav=0; bool nav_used=false;
            int wb=-1, la[2]={0,0}, lch=0; };   // p16: RobotWindow bridge index, last apron counts and passage count   // p01: NAV countdown and whether this turn already used its one RTS window
// v32 (round 45): ROBOT_BMAC_GATED=1 -- gated service from polling theory instead of the fixed hold ROBOT_BMAC_HOLD: when a side gets
// the passage, the robots then waiting on that side are served; once none of them is still waiting, the passage switches as soon as
// the other side waits (same drain rule as before). No time constant: every robot waits at most one cycle of the other side.
bool bm_gated=false;
// v25 (round 36): batch threshold for switching direction (polling with a threshold): the waiting side gets the passage only
// when ROBOT_BMAC_BATCH robots wait there, or one has waited ROBOT_BMAC_MAXWAIT steps. Defaults 1 / 0 = v24 behaviour.
int bm_batch=1, bm_maxwait=0; bool bm_idlechain=false;
// v25 diagnostic (ROBOT_BMAC_WAITLOG=path): why active-direction crossers inside the apron are planned to stay. No effect on behaviour.
std::FILE* wl=nullptr; std::vector<int> wl_best; long long wl_step=0;
struct BE { int b, side, dist; };
// v40 (round 57): ROBOT_BMAC_APRON_AREA=1 -- the apron is set per passage from the map instead of one number for all: a(passage) =
// the smallest a >= amin (ROBOT_BMAC_APRON_MIN, default 3 = ceil(h / tau), h = 9-tick same-direction headway, tau = 3 ticks per action)
// such that on each side the cells within distance a of the passage number at least amin^2 (= the 1 + 3 + 5 cells an open door's
// exit fan has within amin steps). A door next to a wall corner has fewer cells near it, so it gets a larger apron. Capped at R.
bool bm_area=false; int bm_amin=3;
// p01 (protocol round 1, project round 76): ROBOT_BMAC_NAV=D -- 802.11 RTS/CTS + NAV (IEEE 802.11 virtual carrier sense). A crosser
// on the active side that is still on its way (distance in (near, near+D] from the passage, outside the ROBOT_BMAC_NEAR zone the
// switch rule looks at) "sends an RTS": when the active side would be declared empty, the passage sets a NAV = the largest announced
// arrival time (d - near steps) and does not start draining until it expires (or nobody is still coming, like CF-End). One NAV per
// turn, so a turn is extended by at most D steps (no starvation). ROBOT_BMAC_NAVLOG=path writes only counters (no effect on behaviour):
// how often the active side was declared empty while a crosser was on its way within (near, near+D] (D defaults to 2*apron there).
int bm_nav=0; const char* bm_navlog=nullptr; std::vector<std::vector<BE>> far_be;
long long nav_trig=0, nav_trig_far=0, nav_set=0, nav_defer=0;
std::vector<BM> bms; std::vector<std::vector<BE>> cell_be; std::vector<int> chain_of; std::vector<std::vector<int>> bside;
inline int apr(int b){ return bms[b].ap>=0?bms[b].ap:bm_apron; }   // v40: per-passage apron (bm_area), else the global one
std::vector<int> bm_target; std::vector<char> bm_blocked; bool bm_demote=false;
// p12 (protocol round 12, project round 87): ROBOT_ETR=k -- IEEE 802.5 early token release. Once the active side has nobody left to
// send (drain), its apron holds no crosser and its last crosser is inside the passage, the token is released early: crossers of the
// other side may step into their apron, but no closer than k cells to the passage (the cells right at the exit stay free for the
// robots still coming out, like the new frame following the old one round the ring). The switch itself is unchanged. 0 = off.
int bm_etr_k=0; std::vector<char> bm_etr;
// p13 (protocol round 13, project round 88): ROBOT_TAS=S -- IEEE 802.1Qbv time-aware shaper. Every passage follows a fixed gate
// control list: side 0 for S planning steps, then side 1 for S steps, repeating, regardless of demand. A guard band of
// bm_tas_guard steps before the end of a side's window (and after it) drains that side; the passage then switches to the side the
// schedule currently names as soon as the passage and the draining side's apron are empty. 0 = off.
int bm_tas=0, bm_tas_guard=3; long long bm_tas_t=0;
// v24 (round 35): ROBOT_BMAC_LANE=1 -- a passage's mouth cells (the free cells next to its ends) may only be entered from / left to
// the passage itself or the next cell on the passage axis, so robots pass the mouth straight (no turning or side entry there).
bool bm_lane=false; std::vector<int> lane_a, lane_c; long long lane_denied=0;
// p22 (ROBOT_CREDIT=1): hop-by-hop credit flow control (Kung & Morris 1995). A robot may step from outside into a passage
// only if an exit cell on the far side (free cell next to the passage end, dist 1) was free at the start of this step.
bool bm_credit=false; long long credit_denied=0; std::vector<std::array<std::vector<int>,2>> bm_exit; std::vector<char> occ_now;
std::vector<std::vector<std::pair<int,int>>> bm_cross;    // per agent: (bm, side) where the agent is a crosser this step
const BE* be_of(int cell,int b){ if(cell<0) return nullptr; for(const auto& e:cell_be[cell]) if(e.b==b) return &e; return nullptr; }
int cross_side(int agent,int b){ for(const auto& x:bm_cross[agent]) if(x.first==b) return x.second; return -1; }
}
int pipe_idle(int wb, int s){ for(const auto& m:bms) if(m.cut&&m.wb==wb){ if(s<0||s>1) return 0; const int src=1-s; return m.dir==src&&!m.drain&&m.la[src]==0&&m.lch==0; } return 0; }
int door_idle(int wb){ for(const auto& m:bms) if(m.cut&&m.wb==wb) return m.la[0]==0&&m.la[1]==0&&m.lch==0; return 0; }   // p68
// p21 (TCP SACK): cell v is a passage cell of a cut bridge, or within that bridge's apron radius of it
bool door_zone(int v){ if(v<0||v>=int(chain_of.size())) return false; const int c=chain_of[v]; if(c>=0) return bms[c].cut;
    for(const auto& e:cell_be[v]) if(bms[e.b].cut&&e.dist<=apr(e.b)) return true; return false; }
bool any_enabled(){return hdx||bo||mp_kappa>0;}
int passage_count(){return lm_gate_detour<0?int(bms.size()):long_passages;}
int link_count(){int k=0; for(const auto& m:bms) if(!m.cut) ++k; return k;}
bool demote_active(){return (bmac||lmac)&&bm_demote&&!bms.empty();}
namespace { int bm_promote=0, bm_exit_steps=6; std::vector<char> bm_prom; std::vector<long long> bm_last_chain; long long bm_stepc=0; }
bool promote_active(){return (bmac||lmac)&&bm_promote>0&&!bms.empty();}
bool promoted(int a){return a>=0&&a<int(bm_prom.size())&&bm_prom[a];}
namespace { std::vector<int> bm_rank; int bm_efcap=0; std::vector<int> bm_efdoor; }   // p03: RFC 3246 EF share cap per door
int promote_rank(int a){return a>=0&&a<int(bm_rank.size())?bm_rank[a]:-1;}
bool blocked(int a){return a>=0&&a<int(bm_blocked.size())&&bm_blocked[a];}
// p23 (ROBOT_RED=min_th): Random Early Detection (Floyd & Jacobson 1993). A robot standing in a passage whose next guide cell
// (outside the passage) is held by a non-delayed robot that is not crossing this passage, and that has stood still q steps, is put
// first in the PIBT order with probability p(q) = max_p*(q-min_th)/(max_th-min_th) (0 below min_th, 1 from max_th; max_th = 3*min_th,
// max_p = 0.1), so priority inheritance pushes the holder aside. 0 = off. ROBOT_RED_LOG=path: counts every 500 steps.
namespace { int red_min=0; std::vector<int> red_still, red_last; std::vector<char> red_mark; long long red_step=0, red_cand=0, red_hit=0; std::FILE* red_lf=nullptr; }
bool red_active(){return red_min>0&&(bmac||lmac)&&!bms.empty();}
bool red_push(int a){return a>=0&&a<int(red_mark.size())&&red_mark[a];}
// p24 (count only, ROBOT_DEFL_LOG=prefix): who holds robots standing in a door (cut passage) cell. Executor ticks per door:
// G (go / turn), W (planner staged a wait), E (no staged action), B (wants forward, another robot heads the target cell's TPG order),
// Bx (B with the target outside the passage), Bf (B with the front robot in a delay); X = exits (door cell -> outside cell).
// Planner steps: pw (door robot with a goal planned to stay), pb (its best guide cell is outside the passage, held by a non-delayed
// robot that also stays), pd (the holder has a free neighbour: not a passage cell, empty before and after), pdx (pd and the holder is
// not itself crossing this door) -- the cases deflection routing (Baran 1964, Maxemchuk 1987) could use. No effect on behaviour.
// p24b: B split by the front robot's Manhattan distance to the target cell: Bnear (<=3), Bfar (>3), Bfarf (Bfar, front in a delay)
// -- head-of-line blocking in the sense of QUIC (RFC 9000 sec. 2-3).
namespace { std::string dl_pre; bool dl_on=false; long long dl_steps=0, dl_ticks=0, dl_lasttick=-1; std::vector<std::array<long long,34>> dl_c;
    std::vector<int> m_dist, m_door, m_occ; long long m_occtick=-2;   // p30 count only: door mouth (1-3 steps from a door cell)
    std::vector<int> dl_best; std::vector<char> dl_goal, dl_del; SharedEnvironment* dl_env=nullptr; TrajLNS* dl_lns=nullptr;
    bool dl_door(int v){ return v>=0&&v<int(chain_of.size())&&chain_of[v]>=0&&bms[chain_of[v]].cut; }
    void dl_dump(){ if(!dl_on||!dl_env) return; static std::string fn; if(fn.empty()) fn=dl_pre+"_"+std::to_string(int(getpid()))+".txt";
        std::FILE* f=std::fopen(fn.c_str(),"w"); if(!f) return;
        std::fprintf(f,"H %s %d %lld %lld\n",dl_env->map_name.c_str(),dl_env->num_of_agents,dl_steps,dl_ticks);
        for(size_t b=0;b<dl_c.size();++b){ if(!bms[b].cut) continue; std::fprintf(f,"D %zu",b); for(long long x:dl_c[b]) std::fprintf(f," %lld",x); std::fprintf(f,"\n"); }
        std::fclose(f); } }
bool defl_on(){return dl_on;}
// p30 (count only, M-1): robots in a door mouth (not in a door cell, 1-3 steps from the nearest door cell), not delayed, with a goal,
// whose best guide cell is closer to that door, i.e. heading into it. [17] Mt all such ticks; with the wanted cell empty this tick:
// [18] Mrule staged wait while the BMAC door rule blocks it, [19] Mplan staged wait otherwise, [20] Mnone no staged action,
// [21] Mtpg wants forward but another robot heads the target cell's TPG order; [22] Mocc wait/none/held with the wanted cell occupied;
// [23] Mgo go or turn. Which pipeline stage holds a packet at a router port (lookahead routing, Galles 1997; Peh & Dally 2001).
void mouth_exec(SharedEnvironment* env,int agent,char kind,int next_cell){
    if(!dl_lns||agent>=int(dl_best.size())) return; const int N=int(chain_of.size()); const auto& st=env->system_states[agent];
    if(m_dist.empty()){ m_dist.assign(N,1000); m_door.assign(N,-1); std::vector<int> q, nb;
        for(int v=0;v<N;++v) if(dl_door(v)){ m_dist[v]=0; m_door[v]=chain_of[v]; q.push_back(v); }
        for(size_t h=0;h<q.size();++h){ const int v=q[h]; if(m_dist[v]>=3) continue; getNeighborLocs(&(dl_lns->neighbors),nb,v);
            for(int n:nb) if(n>=0&&n<N&&m_dist[n]>m_dist[v]+1&&!dl_door(n)){ m_dist[n]=m_dist[v]+1; m_door[n]=m_door[v]; q.push_back(n); } } }
    if(env->system_timestep!=m_occtick){ m_occtick=env->system_timestep; m_occ.assign(N,-1);
        for(int j=0;j<int(env->system_states.size());++j){ const int u=env->system_states[j].location; if(u>=0&&u<N) m_occ[u]=j; } }
    const int v=st.location; if(v<0||v>=N||st.delay.inDelay||dl_door(v)||m_dist[v]<1||m_dist[v]>3||!dl_goal[agent]) return;
    const int u=dl_best[agent]; if(u<0||u>=N||m_dist[u]>=m_dist[v]) return;
    const int g=m_door[v]; if(g<0||g>=int(dl_c.size())) return; auto& c=dl_c[g]; ++c[17];
    if(kind=='G'){ ++c[23]; return; }
    const int w=(kind=='B')?next_cell:u; const bool empty=w>=0&&w<N&&(m_occ[w]<0||m_occ[w]==agent);
    if(!empty){ ++c[22]; return; }
    // p30b: the default executor never stages W (execute_process_new_plan drops W/NA), so a planner wait shows up as E (no staged action);
    // E is therefore split by the door rule too: [18] door rule blocks it, [20] E otherwise (planner wait or no new plan yet).
    if((kind=='W'||kind=='E')&&blocked(agent)) ++c[18]; else if(kind=='W') ++c[19]; else if(kind=='E') ++c[20]; else if(kind=='B') ++c[21]; }
void defl_exec(SharedEnvironment* env,int agent,char kind,int next_cell,int front){
    if(!dl_on||dl_c.empty()) return; if(env->system_timestep!=dl_lasttick){ dl_lasttick=env->system_timestep; ++dl_ticks; }
    mouth_exec(env,agent,kind,next_cell);
    const auto& st=env->system_states[agent]; if(st.delay.inDelay||!dl_door(st.location)) return; auto& c=dl_c[chain_of[st.location]];
    if(kind=='G') ++c[0]; else if(kind=='W') ++c[1]; else if(kind=='E') ++c[2];
    else if(kind=='B'){ ++c[3]; if(!dl_door(next_cell)) ++c[4]; if(front>=0&&front<int(env->system_states.size())&&env->system_states[front].delay.inDelay) ++c[5];
        if(front>=0&&front<int(env->system_states.size())&&next_cell>=0){ const int fl=env->system_states[front].location, C=env->cols;   // p24b: QUIC head-of-line count
            const int d=fl<0?1000:std::abs(fl/C-next_cell/C)+std::abs(fl%C-next_cell%C);
            if(d<=3) ++c[11]; else { ++c[12]; if(env->system_states[front].delay.inDelay) ++c[13]; } } } }
// p25b (count only): B on a door cell whose front robot f stands on the target cell, is not delayed, and this very tick gets GO with a
// forward move that does not go into the follower's cell -- the one-tick lag wormhole flit pipelining (Dally & Seitz 1987) removes.
// [14] Bfol, [15] Bfol with the same heading (straight follow), [16] Bstay (f on the target cell, not delayed, not leaving this tick).
void defl_follow(SharedEnvironment* env,int agent,int kind){
    if(!dl_on||dl_c.empty()) return; const auto& st=env->system_states[agent]; if(st.delay.inDelay||!dl_door(st.location)) return;
    auto& c=dl_c[chain_of[st.location]]; if(kind==1||kind==2) ++c[14]; if(kind==2) ++c[15]; if(kind==3) ++c[16]; }
void defl_move(int from,int to){ if(!dl_on||dl_c.empty()) return; if(dl_door(from)&&to>=0&&chain_of[to]<0) ++dl_c[chain_of[from]][6]; }
void initialize(SharedEnvironment* env, TrajLNS&){
    const char* h=std::getenv("ROBOT_HDX"); hdx=h&&std::string(h)=="1";
    const char* b=std::getenv("ROBOT_BACKOFF"); bo=b&&std::string(b)=="1";
    mp_kappa=param("ROBOT_MP_KAPPA",0,0,1000); hdx_hold=int(param("ROBOT_HDX_HOLD",8,1,10000)); hdx_stall=int(param("ROBOT_HDX_STALL",3,1,10000)); hdx_maxlen=int(param("ROBOT_HDX_MAXLEN",1000000,1,1000000));
    bo_k=int(param("ROBOT_BACKOFF_K",2,1,1000)); bo_maxexp=int(param("ROBOT_BACKOFF_MAXEXP",5,0,16)); seed=std::llround(param("ROBOT_NETMAC_SEED",1,0,1e9));
    const int N=env->map.size(), A=env->num_of_agents;
    links.clear(); link_of.assign(N,-1); pos_in.assign(N,-1);
    desired.assign(A,-1); backlog.assign(N,0); loc_now.assign(A,-1); agent_side.assign(A,0); stuck.assign(A,0); bo_exp.assign(A,0); bo_until.assign(A,-1); last_h.assign(A,-1);
    step=0; st_denied=st_backoffs=st_headon=st_stall_open=st_steps=0;
    bmac = std::getenv("ROBOT_BMAC") && std::string(std::getenv("ROBOT_BMAC")) == "1";
    lmac = std::getenv("ROBOT_LMAC") && std::string(std::getenv("ROBOT_LMAC")) == "1";
    bm_evac=std::getenv("ROBOT_BMAC_EVAC")&&std::string(std::getenv("ROBOT_BMAC_EVAC"))=="1";
    bm_idlechain=std::getenv("ROBOT_BMAC_IDLECHAIN")&&std::string(std::getenv("ROBOT_BMAC_IDLECHAIN"))=="1";
    bm_chainfree=std::getenv("ROBOT_BMAC_CHAINFREE")&&std::string(std::getenv("ROBOT_BMAC_CHAINFREE"))=="1";
    bm_credit=std::getenv("ROBOT_CREDIT")&&std::string(std::getenv("ROBOT_CREDIT"))=="1"; credit_denied=0; bm_exit.clear();
    bm_batch=int(param("ROBOT_BMAC_BATCH",1,1,1000)); bm_maxwait=int(param("ROBOT_BMAC_MAXWAIT",0,0,1000000));
    bm_area=std::getenv("ROBOT_BMAC_APRON_AREA")&&std::string(std::getenv("ROBOT_BMAC_APRON_AREA"))=="1"; bm_amin=int(param("ROBOT_BMAC_APRON_MIN",3,1,50));
    bm_gated=std::getenv("ROBOT_BMAC_GATED")&&std::string(std::getenv("ROBOT_BMAC_GATED"))=="1"; bm_apron=int(param("ROBOT_BMAC_APRON",2,0,50)); bm_hold=int(param("ROBOT_BMAC_HOLD",40,1,100000)); bm_near=int(param("ROBOT_BMAC_NEAR",8,1,1000));
    lm_maxlen=int(param("ROBOT_LMAC_MAXLEN",4,1,1000)); lm_detour=int(param("ROBOT_LMAC_DETOUR",20,1,1000000));
    lm_gate_detour=std::getenv("ROBOT_LMAC_GATE_DETOUR")?int(param("ROBOT_LMAC_GATE_DETOUR",20,1,1000000)):-1; long_passages=0;
    bms.clear(); bside.clear(); cell_be.assign(N,{}); chain_of.assign(N,-1); bm_target.assign(A,-1); bm_blocked.assign(A,0); bm_cross.assign(A,{});
    bm_etr_k=int(param("ROBOT_ETR",0,0,50)); bm_etr.clear();
    bm_tas=int(param("ROBOT_TAS",0,0,100000)); bm_tas_t=0;
    bm_demote=std::getenv("ROBOT_BMAC_DEMOTE")&&std::string(std::getenv("ROBOT_BMAC_DEMOTE"))=="1";
    { const char* dp=std::getenv("ROBOT_DEFL_LOG"); dl_on=dp&&*dp; if(dl_on) dl_pre=dp; dl_c.assign(bms.size(),{}); dl_steps=dl_ticks=0; dl_lasttick=-1; dl_env=env; }
    red_min=int(param("ROBOT_RED",0,0,1000)); red_still.assign(A,0); red_last.assign(A,-1); red_mark.assign(A,0); red_step=red_cand=red_hit=0;
    { const char* rl=std::getenv("ROBOT_RED_LOG"); if(red_min>0&&rl&&!red_lf){ red_lf=std::fopen(rl,"w"); if(red_lf) std::setvbuf(red_lf,nullptr,_IOLBF,1<<12); } }
    bm_promote=int(param("ROBOT_BMAC_PROMOTE",0,0,7)); bm_exit_steps=int(param("ROBOT_BMAC_EXIT_STEPS",6,0,1000)); bm_prom.assign(A,0); bm_last_chain.assign(A,-1000000); bm_stepc=0; bm_efcap=int(param("ROBOT_BMAC_EFCAP",0,0,1000)); bm_efdoor.assign(A,-1);
    const int R=std::max(bm_apron,bm_near);
    bm_nav=int(param("ROBOT_BMAC_NAV",0,0,1000)); bm_navlog=std::getenv("ROBOT_BMAC_NAVLOG"); far_be.assign(N,{});
    const int nav_r=bm_nav>0?bm_nav:(bm_navlog?2*bm_apron:0); const int RB=std::max(R,bm_near+nav_r);   // RB == R when p01 is off
    if(bmac){
        const int nb=RobotWindow::bridge_count(env);
        for(int b=0;b<nb;++b){
            std::vector<int> sd(N,-1); int parts=0;
            for(int v=0;v<N;++v){ if(env->map[v]) continue; sd[v]=RobotWindow::bridge_side(b,v); parts=std::max(parts,sd[v]+1); }
            if(parts!=2) continue;
            BM m; m.cut=true; m.wb=b; m.bidx=int(bside.size()); m.cells=RobotWindow::bridge_cells(b); const int id=int(bms.size());
            std::vector<int> dist(N,-1); std::vector<int> q=m.cells; for(int c:q){ dist[c]=0; chain_of[c]=id; }
            for(size_t h=0;h<q.size();++h){ const int v=q[h]; if(dist[v]>=RB) continue;
                for(int n:nbrs(env,v)) if(dist[n]<0){ dist[n]=dist[v]+1; q.push_back(n); if(sd[n]>=0) (dist[n]<=R?cell_be:far_be)[n].push_back({id,sd[n],dist[n]}); } }
            bside.push_back(std::move(sd)); bms.push_back(std::move(m)); if(lm_gate_detour>=0) ++long_passages;
        }
    }
    if(lmac){
        // passage cell: exactly two free neighbours, on opposite sides
        auto passage=[&](int v){ if(env->map[v]) return false; auto o=nbrs(env,v); return o.size()==2&&o[0]+o[1]==2*v; };
        std::vector<char> seen(N,0); long long found=0;
        for(int v0=0;v0<N;++v0){ if(seen[v0]||!passage(v0)||chain_of[v0]>=0) continue;
            std::vector<int> ch{v0}; seen[v0]=1;
            for(size_t k=0;k<ch.size();++k) for(int n:nbrs(env,ch[k])) if(!seen[n]&&passage(n)){ seen[n]=1; ch.push_back(n); }
            if(int(ch.size())>lm_maxlen) continue;
            bool overlap=false; for(int c:ch) if(chain_of[c]>=0) overlap=true; if(overlap) continue;
            std::vector<char> inch(N,0); for(int c:ch) inch[c]=1;
            std::vector<int> ends; for(int c:ch) for(int n:nbrs(env,c)) if(!inch[n]) ends.push_back(n);
            if(ends.size()!=2) continue;
            // both ends must open into a 2-D area: some 3x3 block of free cells (not touching the passage) contains the end
            const int C=env->cols, Rr=env->rows;
            auto in_open=[&](int e){ const int er=e/C, ec=e%C;
                for(int r0=er-2;r0<=er;++r0) for(int c0=ec-2;c0<=ec;++c0){ bool ok=r0>=0&&c0>=0&&r0+2<Rr&&c0+2<C;
                    for(int dr=0;ok&&dr<3;++dr) for(int dc=0;ok&&dc<3;++dc){ const int u=(r0+dr)*C+c0+dc; if(env->map[u]||inch[u]) ok=false; }
                    if(ok) return true; }
                return false; };
            bool open=true; for(int e:ends) if(!in_open(e)) open=false; if(!open) continue;
            // detour: shortest path between the two ends that avoids the passage
            std::vector<int> d(N,-1); std::vector<int> q{ends[0]}; d[ends[0]]=0; int det=-1;
            const int dlim=std::max(lm_detour,lm_gate_detour);
            for(size_t h=0;h<q.size()&&det<0;++h){ const int v=q[h]; if(d[v]>=dlim) break;
                for(int n:nbrs(env,v)) if(d[n]<0&&!inch[n]){ d[n]=d[v]+1; if(n==ends[1]){det=d[n];break;} q.push_back(n);} }
            if(det>=0&&det<lm_detour) continue;
            if(lm_gate_detour>=0&&(det<0||det>=lm_gate_detour)) ++long_passages;
            const int id=int(bms.size()); BM m; m.cut=false; m.cells=ch; for(int c:ch) chain_of[c]=id;
            // local sides: multi-source BFS from the two ends, radius R, never through the passage
            std::vector<int> dist(N,-1), sd(N,-1); std::vector<int> qq;
            for(int s=0;s<2;++s){ dist[ends[s]]=1; sd[ends[s]]=s; qq.push_back(ends[s]); }
            for(size_t h=0;h<qq.size();++h){ const int v=qq[h]; if(dist[v]>=RB) continue;
                for(int n:nbrs(env,v)) if(dist[n]<0&&!inch[n]){ dist[n]=dist[v]+1; sd[n]=sd[v]; qq.push_back(n);} }
            for(int v:qq) (dist[v]<=R?cell_be:far_be)[v].push_back({id,sd[v],dist[v]});
            bms.push_back(std::move(m)); ++found;
        }
        if(std::getenv("ROBOT_BMAC_TRACE")) std::fprintf(stderr,"[lmac] links %lld (bridges %zu)\n",found,bside.size());
    }
    if(bm_area){   // v40: per-passage apron from the map (see bm_area)
        std::vector<std::vector<std::vector<int>>> cnt(bms.size(), std::vector<std::vector<int>>(2, std::vector<int>(R+2,0)));
        for(int v=0;v<N;++v) for(const auto& e:cell_be[v]) if(e.side>=0&&e.side<2&&e.dist>=1&&e.dist<=R) cnt[e.b][e.side][e.dist]++;
        for(size_t b=0;b<bms.size();++b){ int a=bm_amin; const int need=bm_amin*bm_amin;
            for(;a<R;++a){ int c0=0,c1=0; for(int d=1;d<=a;++d){ c0+=cnt[b][0][d]; c1+=cnt[b][1][d]; } if(c0>=need&&c1>=need) break; }
            bms[b].ap=a;
            if(std::getenv("ROBOT_BMAC_TRACE")){ const int C=env->cols; std::fprintf(stderr,"[apron] passage %zu %s cell (%d,%d) a=%d\n",b,bms[b].cut?"cut":"link",bms[b].cells[0]/C,bms[b].cells[0]%C,a); } }
    }
    const int lane_mode=std::getenv("ROBOT_BMAC_LANE")?std::atoi(std::getenv("ROBOT_BMAC_LANE")):0; bm_lane=lane_mode>0;
    lane_a.assign(N,-1); lane_c.assign(N,-1); lane_denied=0;
    if(bm_lane) for(size_t b=0;b<bms.size();++b) for(int c:bms[b].cells) for(int m:nbrs(env,c)){
        if(chain_of[m]>=0) continue; const int C=env->cols; const int dr=m/C-c/C, dc=m%C-c%C; const int ar=m/C+dr, ac=m%C+dc;
        if(ar<0||ac<0||ar>=env->rows||ac>=C) continue; const int a=ar*C+ac; if(env->map[a]||chain_of[a]>=0) continue;
        if(lane_c[m]>=0&&lane_c[m]!=c) { lane_c[m]=-2; continue; }   // mouth of two passage cells: leave unconstrained
        lane_c[m]=c; lane_a[m]=a; }
    if(lane_mode==2){   // v24b: same rule, but as removed edges of the movement graph, so guide paths know it too
        for(int m=0;m<N;++m) if(lane_c[m]>=0) for(int s2:nbrs(env,m)) if(s2!=lane_c[m]&&s2!=lane_a[m]){ RobotWindow::forbid_move(s2,m); RobotWindow::forbid_move(m,s2); }
        bm_lane=false;   // the allow_move check of mode 1 is not used
    }
    if(lane_mode>0&&std::getenv("ROBOT_BMAC_TRACE")){ int k=0; for(int v=0;v<N;++v) if(lane_c[v]>=0) ++k; std::fprintf(stderr,"[lane] mouths %d\n",k); }
    if(!hdx) return;
    // build maximal chains of degree-2 cells (corridors / doors). A chain end's outside neighbour is its non-chain neighbour.
    std::vector<char> seen(N,0);
    for(int v=0;v<N;++v){ if(seen[v]||degree(env,v)!=2) continue;
        std::vector<int> comp{v}; seen[v]=1;
        for(size_t k=0;k<comp.size();++k) for(int n:nbrs(env,comp[k])) if(!seen[n]&&degree(env,n)==2){seen[n]=1;comp.push_back(n);}
        auto inner_deg=[&](int c){int d=0; for(int n:nbrs(env,c)) if(degree(env,n)==2&&std::find(comp.begin(),comp.end(),n)!=comp.end()) ++d; return d;};
        int start=-1; for(int c:comp) if(inner_deg(c)<=1){start=c;break;}
        if(start<0) continue; // pure cycle of corridor cells: skip
        std::vector<int> full; int prev=-1,x=start;
        while(x!=-1){ full.push_back(x); int nxt=-1; for(int n:nbrs(env,x)) if(n!=prev&&degree(env,n)==2&&std::find(comp.begin(),comp.end(),n)!=comp.end()&&std::find(full.begin(),full.end(),n)==full.end()){nxt=n;break;} prev=x; x=nxt; }
        if(full.size()!=comp.size()) continue; // branching inside component: not a simple corridor
        if((int)full.size()>hdx_maxlen) continue; // only short shared links (doors / short corridors)
        Link L; L.cells=full;
        auto outs=[&](int c){std::vector<int> o; for(int n:nbrs(env,c)) if(std::find(full.begin(),full.end(),n)==full.end()) o.push_back(n); return o;};
        if(full.size()==1){ auto o=outs(full[0]); if(o.size()!=2) continue; L.outA=o[0]; L.outB=o[1]; }
        else { auto oa=outs(full.front()), ob=outs(full.back()); if(oa.size()!=1||ob.size()!=1) continue; L.outA=oa[0]; L.outB=ob[0]; }
        int id=links.size(); for(size_t i=0;i<full.size();++i){link_of[full[i]]=id;pos_in[full[i]]=i;} links.push_back(L);
    }
}
namespace { void navlog_dump(int tick){   // p01: counters only, rewritten every planning step (the last write is the total)
    long long sw=0; for(const auto& m:bms) sw+=m.switches; std::FILE* nf=std::fopen(bm_navlog,"w"); if(!nf) return;
    std::fprintf(nf,"{\"tick\":%d,\"switches\":%lld,\"emptyTriggers\":%lld,\"emptyTriggersWithFar\":%lld,\"navSet\":%lld,\"navDeferSteps\":%lld,\"navD\":%d}\n",
        tick,sw,nav_trig,nav_trig_far,nav_set,nav_defer,bm_nav); std::fclose(nf); } }
// p35 (PFC deadlock watchdog; IEEE 802.1Qbb + Guo et al. SIGCOMM 2016): ROBOT_PFC_WD=K. A robot with a task that has stood on the
// same cell for >= K ticks and is not delayed right now ignores the door rules in allow_move for this step (PIBT collision checks stay).
// p36 (PFC + ECN/DCQCN division of labour; Zhu et al. SIGCOMM 2015, Guo et al. SIGCOMM 2016 §4.3): ROBOT_PFC_WD_DRAIN=1 adds the
// switch watchdog's second condition: a queue is deadlocked only if it is paused AND has not drained for the detection time. A robot in a
// passage or its apron is released only if nobody has entered each such passage for >= K ticks (a door still passing robots = congestion).
// p73 (PFC watchdog counts only while the queue is paused AND non-empty): ROBOT_PFC_WD_TASKCLK=1 restarts the timer at every step the
// robot has no task, so an idle robot that has just been given a task is not taken for deadlocked.
namespace { int wd_taskclk=0; }
namespace { int wd_k=-1, wd_drain=0; std::vector<int> wd_loc, wd_since, wd_entry; std::vector<char> wd_free; long long wd_hits=0, wd_robot_ticks=0, wd_held=0; const char* wd_log=nullptr; int wd_lastt=-1; }
static void pfc_wd_update(SharedEnvironment* env, const std::vector<State>& prev_states){
    if(wd_k<0){ const char* e=std::getenv("ROBOT_PFC_WD"); wd_k=e?std::atoi(e):0; wd_log=std::getenv("ROBOT_PFC_WD_LOG");
        const char* d=std::getenv("ROBOT_PFC_WD_DRAIN"); wd_drain=d?std::atoi(d):0;
        const char* tc=std::getenv("ROBOT_PFC_WD_TASKCLK"); wd_taskclk=tc?std::atoi(tc):0; }
    if(wd_k<=0) return;
    const int A=int(prev_states.size()), t=env->system_timestep;   // curr_timestep stays 0 under the logical clock
    if(int(wd_loc.size())!=A){ wd_loc.assign(A,-1); wd_since.assign(A,t); wd_free.assign(A,0); }
    const bool drain=wd_drain>0&&!bms.empty();
    if(drain&&wd_entry.size()!=bms.size()) wd_entry.assign(bms.size(),t);
    for(int i=0;i<A;++i){ const int v=prev_states[i].location;
        if(v!=wd_loc[i]){   // p36: an entry into a passage from outside it = the passage drained a robot
            if(drain&&v>=0&&chain_of[v]>=0&&(wd_loc[i]<0||chain_of[wd_loc[i]]!=chain_of[v])) wd_entry[chain_of[v]]=t;
            wd_loc[i]=v; wd_since[i]=t; }
        if(wd_taskclk&&env->goal_locations[i].empty()) wd_since[i]=t; }
    long long held=0;
    for(int i=0;i<A;++i){ const int v=prev_states[i].location;
        const bool del=i<int(env->system_states.size())&&env->system_states[i].delay.inDelay;
        wd_free[i]=v>=0&&!env->goal_locations[i].empty()&&!del&&t-wd_since[i]>=wd_k;
        if(wd_free[i]&&drain){ bool flowing=chain_of[v]>=0&&t-wd_entry[chain_of[v]]<wd_k;
            for(const auto& e:cell_be[v]) if(!flowing&&e.dist<=apr(e.b)&&t-wd_entry[e.b]<wd_k) flowing=true;
            if(flowing){ wd_free[i]=0; ++held; } } }
    if(t!=wd_lastt){ wd_lastt=t; wd_held+=held; for(int i=0;i<A;++i) if(wd_free[i]) ++wd_robot_ticks;
        if(wd_log&&t%500==0){ if(std::FILE* f=std::fopen(wd_log,"w")){ std::fprintf(f,"{\"t\": %d, \"freeRobotTicks\": %lld, \"bypassedChecks\": %lld, \"drainHeld\": %lld}\n",t,wd_robot_ticks,wd_hits,wd_held); std::fclose(f);} } }
}
// p37 (deadlock prevention, Duato 1993 escape channel): ROBOT_ESCAPE=E. Two robots that each want the other's cell (head-on), both
// still for >= E ticks, one of them in a passage or its apron: if the door rules allow the move of one and forbid the other's, the allowed
// one (the escape move) is planned first, so PIBT pushes the other aside. No rule is relaxed.
namespace { int esc_e=-1; std::vector<int> esc_loc, esc_since; std::vector<char> esc_mark; long long esc_pairs=0, esc_marks=0; const char* esc_log=nullptr; int esc_lastt=-1; }
static void esc_update(SharedEnvironment* env, TrajLNS& lns, const std::vector<State>& prev_states){
    if(esc_e<0){ const char* e=std::getenv("ROBOT_ESCAPE"); esc_e=e?std::atoi(e):0; esc_log=std::getenv("ROBOT_ESCAPE_LOG"); }
    if(esc_e<=0||bms.empty()) return;
    const int A=int(prev_states.size()), t=env->system_timestep, N=int(chain_of.size());
    if(int(esc_loc.size())!=A){ esc_loc.assign(A,-1); esc_since.assign(A,t); }
    esc_mark.assign(A,0); std::vector<int> at(N,-1), best(A,-1), nb;
    for(int i=0;i<A;++i){ const int v=prev_states[i].location; if(v!=esc_loc[i]){ esc_loc[i]=v; esc_since[i]=t; } if(v<0||v>=N) continue; at[v]=i;
        if(env->goal_locations[i].empty()) continue;
        int bh=get_gp_h(lns,i,v); getNeighborLocs(&(lns.neighbors),nb,v);
        for(int n:nb){ const int hh=get_gp_h(lns,i,n); if(hh<bh){bh=hh;best[i]=n;} } }
    auto near=[&](int v){ if(chain_of[v]>=0) return true; for(const auto& e:cell_be[v]) if(e.dist<=apr(e.b)) return true; return false; };
    for(int i=0;i<A;++i){ const int v=prev_states[i].location, u=best[i]; if(v<0||v>=N||u<0||u>=N) continue; const int j=at[u];
        if(j<0||j<=i||best[j]!=v||t-esc_since[i]<esc_e||t-esc_since[j]<esc_e||(!near(v)&&!near(u))) continue;
        ++esc_pairs; const bool ai=allow_move(i,v,u), aj=allow_move(j,u,v);
        if(ai&&!aj){ esc_mark[i]=1; ++esc_marks; } else if(aj&&!ai){ esc_mark[j]=1; ++esc_marks; } }
    if(esc_log&&t!=esc_lastt&&t%500==0){ esc_lastt=t; if(std::FILE* f=std::fopen(esc_log,"w")){ std::fprintf(f,"{\"t\": %d, \"headOnPairs\": %lld, \"escapeMarks\": %lld}%c",t,esc_pairs,esc_marks,10); std::fclose(f);} }
}
bool esc_active(){ return esc_e>0&&!bms.empty(); }
bool esc_push(int a){ return a>=0&&a<int(esc_mark.size())&&esc_mark[a]; }
void begin_step(SharedEnvironment* env, TrajLNS& lns, const std::vector<State>& prev_states){
    pfc_wd_update(env, prev_states);
    if(dl_on&&!bms.empty()){ const int A=int(prev_states.size()); dl_env=env; dl_lns=&lns; dl_best.assign(A,-1); dl_goal.assign(A,0); dl_del.assign(A,0); std::vector<int> nb;
        if(dl_c.size()!=bms.size()) dl_c.assign(bms.size(),{});
        for(int i=0;i<A;++i){ const int v=prev_states[i].location; if(v<0) continue; dl_goal[i]=!env->goal_locations[i].empty();
            dl_del[i]=i<int(env->system_states.size())&&env->system_states[i].delay.inDelay;
            int best=-1, bh=get_gp_h(lns,i,v); getNeighborLocs(&(lns.neighbors),nb,v);
            for(int n:nb){ const int hh=get_gp_h(lns,i,n); if(hh<bh){bh=hh;best=n;} } dl_best[i]=best; } }
    if(bm_credit&&!bms.empty()){
        const int N=int(cell_be.size());
        if(bm_exit.size()!=bms.size()){ bm_exit.assign(bms.size(),{}); for(int v=0;v<N;++v) for(const auto& e:cell_be[v]) if(e.dist==1&&chain_of[v]<0&&e.side>=0&&e.side<2) bm_exit[e.b][e.side].push_back(v); }
        occ_now.assign(N,0); for(const auto& st:prev_states) if(st.location>=0&&st.location<N) occ_now[st.location]=1;
    }
    if((bmac||lmac)&&!bms.empty()){
        const int A=env->num_of_agents;
        for(int i=0;i<A;++i){
            bm_target[i]=lns.tasks.at(i); bm_cross[i].clear(); const int v=prev_states[i].location; if(v<0) continue;
            for(const auto& e:cell_be[v]){ if(e.dist>bm_near) continue; const BM& m=bms[e.b];
                if(m.cut){ const int t=bm_target[i]>=0?bside[m.bidx][bm_target[i]]:-1; if(t>=0&&t!=e.side) bm_cross[i].push_back({e.b,e.side}); }
                else {   // guide path enters the passage within the next dist+len+1 cells
                    const auto& tr=lns.trajs[i]; size_t k=0; while(k<tr.size()&&tr[k]!=v) ++k; if(k==tr.size()) continue;
                    const size_t lim=std::min(tr.size(),k+size_t(e.dist)+m.cells.size()+2);
                    for(size_t q=k+1;q<lim;++q) if(chain_of[tr[q]]==e.b){ bm_cross[i].push_back({e.b,e.side}); break; }
                } } }
        std::vector<int> farc0(bms.size(),0), farc1(bms.size(),0), farm0(bms.size(),0), farm1(bms.size(),0);   // p01: crossers on their way
        if(bm_nav>0||bm_navlog) for(int i=0;i<A;++i){ const int v=prev_states[i].location; if(v<0) continue;
            for(const auto& e:far_be[v]){ if(e.dist<=bm_near) continue; const BM& m=bms[e.b]; bool cr=false;
                if(m.cut){ const int t=bm_target[i]>=0?bside[m.bidx][bm_target[i]]:-1; cr=t>=0&&t!=e.side; }
                else { const auto& tr=lns.trajs[i]; size_t k=0; while(k<tr.size()&&tr[k]!=v) ++k;
                    if(k<tr.size()){ const size_t lim=std::min(tr.size(),k+size_t(e.dist)+m.cells.size()+2);
                        for(size_t q=k+1;q<lim;++q) if(chain_of[tr[q]]==e.b){ cr=true; break; } } }
                if(!cr) continue; (e.side==0?farc0:farc1)[e.b]++; int& fm=(e.side==0?farm0:farm1)[e.b]; fm=std::max(fm,e.dist-bm_near); } }
        std::vector<int> in_chain(bms.size(),0), w0(bms.size(),0), w1(bms.size(),0), a0(bms.size(),0), a1(bms.size(),0);
        for(int i=0;i<A;++i){ const int v=prev_states[i].location; if(v<0) continue;
            if(chain_of[v]>=0&&!(bm_idlechain&&env->goal_locations[i].empty())) ++in_chain[chain_of[v]];   // v25h: idle robots parked in a passage do not block the switch
            for(const auto& x:bm_cross[i]){ const BE* e=be_of(v,x.first); if(!e) continue;
                (x.second==0?w0:w1)[x.first]++; if(e->dist<=apr(x.first)) (x.second==0?a0:a1)[x.first]++; } }
        {   // v24t: diagnostic trace only (ROBOT_BMAC_LOG=path); no effect on behaviour
            static const char* lg=std::getenv("ROBOT_BMAC_LOG"); static std::FILE* lf=lg?std::fopen(lg,"w"):nullptr;
            if(lf){ std::vector<int> d0(bms.size(),0), d1(bms.size(),0), dc(bms.size(),0);
                for(int i=0;i<A;++i){ const int v=prev_states[i].location; if(v<0||i>=int(env->system_states.size())||!env->system_states[i].delay.inDelay) continue;
                    if(chain_of[v]>=0) ++dc[chain_of[v]];
                    for(const auto& x:bm_cross[i]){ const BE* e=be_of(v,x.first); if(e&&e->dist<=apr(x.first)) (x.second==0?d0:d1)[x.first]++; } }
                for(size_t b=0;b<bms.size();++b){ const auto& m=bms[b];
                    std::fprintf(lf,"%d %d %zu %d %d %d %d %d %d %d %d %d %d %d %lld\n",env->curr_timestep,env->system_timestep,b,m.dir,int(m.drain),m.hold,w0[b],w1[b],a0[b],a1[b],in_chain[b],d0[b],d1[b],dc[b],m.denied); } }
        }
        if(bm_tas>0) ++bm_tas_t;
        for(size_t b=0;b<bms.size();++b){ auto& m=bms[b]; const int wait[2]={w0[b],w1[b]}, apron[2]={a0[b],a1[b]};
            m.la[0]=a0[b]; m.la[1]=a1[b]; m.lch=in_chain[b];   // p16
            auto open_gate=[&](BM& mm, int side){ mm.gate.clear(); if(!bm_gated||side<0) return;
                for(int i=0;i<A;++i) for(const auto& x:bm_cross[i]) if(x.first==int(b)&&x.second==side){ mm.gate.push_back(i); break; } };
            if(bm_tas>0){   // p13: the gate control list decides the direction; demand is ignored
                const long long ph=bm_tas_t%(2LL*bm_tas); const int g=ph<bm_tas?0:1; const bool guard=(ph%bm_tas)>=bm_tas-bm_tas_guard;
                if(m.dir<0){ if(wait[0]||wait[1]){ m.dir=g; m.hold=0; m.drain=false; ++m.switches; open_gate(m,m.dir); } continue; }
                const int s=m.dir; ++m.hold;
                if(!m.drain&&(g!=s||guard)) m.drain=true;
                if(m.drain&&g!=s&&in_chain[b]==0&&apron[s]==0){ m.dir=g; m.hold=0; m.drain=false; ++m.switches; open_gate(m,m.dir); }
                else if(m.drain&&g==s&&!guard) m.drain=false;   // ran over the whole other window: the schedule names this side again
                continue; }
            if(m.dir<0){ if(wait[0]||wait[1]){ m.dir=wait[0]>=wait[1]?0:1; m.hold=0; m.drain=false; m.nav=0; m.nav_used=false; ++m.switches; open_gate(m,m.dir); } continue; }
            const int s=m.dir, o=1-s; ++m.hold;
            if(wait[o]>0) ++m.owait; else m.owait=0;
            const bool enough = wait[o]>=bm_batch || (bm_maxwait>0&&m.owait>=bm_maxwait) || bm_batch<=1;
            bool served=m.hold>=bm_hold;
            if(bm_gated){ served=true; for(int i:m.gate) if(cross_side(i,int(b))==s){ served=false; break; } }
            const int farc[2]={farc0[b],farc1[b]}, farm[2]={farm0[b],farm1[b]};
            if(m.nav>0){ --m.nav; if(wait[s]==0&&farc[s]==0) m.nav=0; }   // NAV counts down; cancelled when nobody is still coming
            if(wait[o]>0&&enough&&(wait[s]==0||served)&&!m.drain){
                if(wait[s]==0&&!served&&m.nav==0){ ++nav_trig; if(farc[s]>0) ++nav_trig_far; }   // p01 measurement (side declared empty)
                if(bm_nav>0&&wait[s]==0&&!served&&!m.nav_used&&farc[s]>0){ m.nav=farm[s]; m.nav_used=true; ++nav_set; }
                if(m.nav>0) ++nav_defer; else m.drain=true; }
            if(m.drain&&in_chain[b]==0&&apron[s]==0){ m.dir=wait[o]>0?o:(wait[s]>0?s:-1); m.hold=0; m.drain=false; m.owait=0; m.nav=0; m.nav_used=false; ++m.switches; open_gate(m,m.dir); }
        }
        {   // p12 (protocol round 12, item ETR = IEEE 802.5 early token release): ROBOT_ETR_LOG=path writes per planning step and passage
            // "step b dir drain in_chain e0 e1 m0 m1": entries into the passage from side 0/1 since the last step, and the nearest crosser's
            // distance on side 0/1 (-1 = none). Measurement only, no effect on behaviour.
            static const char* elp=std::getenv("ROBOT_ETR_LOG"); static std::FILE* ef=elp?std::fopen(elp,"w"):nullptr; static std::vector<int> el_last; static long long el_step=0;
            if(ef){ ++el_step; if(int(el_last.size())!=A) el_last.assign(A,-1);
                std::vector<int> e0(bms.size(),0), e1(bms.size(),0), m0(bms.size(),-1), m1(bms.size(),-1);
                for(int i=0;i<A;++i){ const int v=prev_states[i].location, u=el_last[i]; el_last[i]=v; if(v<0) continue;
                    if(u>=0&&chain_of[v]>=0&&chain_of[u]!=chain_of[v]){ const BE* e=be_of(u,chain_of[v]); if(e) (e->side==0?e0:e1)[chain_of[v]]++; }
                    for(const auto& x:bm_cross[i]){ const BE* e=be_of(v,x.first); if(!e) continue; int& mm=(x.second==0?m0:m1)[x.first]; if(mm<0||e->dist<mm) mm=e->dist; } }
                for(size_t b=0;b<bms.size();++b) std::fprintf(ef,"%lld %zu %d %d %d %d %d %d %d%c",el_step,b,bms[b].dir,int(bms[b].drain),in_chain[b],e0[b],e1[b],m0[b],m1[b],10);
                std::fflush(ef); } }
        if(bm_etr_k>0){ bm_etr.assign(bms.size(),0);   // p12: token released early (drain, own apron empty, last crosser in the passage)
            for(size_t b=0;b<bms.size();++b){ const auto& m=bms[b]; if(m.dir>=0&&m.drain&&(m.dir==0?a0:a1)[b]==0&&in_chain[b]>0) bm_etr[b]=1; } }
        if(bm_navlog) navlog_dump(env->curr_timestep);
        if(wl||(wl=nullptr,false)){}
        { static const char* wlp=std::getenv("ROBOT_BMAC_WAITLOG"); if(wlp&&!wl) { wl=std::fopen(wlp,"w"); if(wl) std::setvbuf(wl,nullptr,_IOLBF,1<<16); } }   // p08: line-buffered so the log survives exit
        if(wl){ ++wl_step; wl_best.assign(A,-1); std::vector<int> nb;
            for(int i=0;i<A;++i){ const int v=prev_states[i].location; if(v<0) continue;
                for(const auto& x:bm_cross[i]){ const auto& m=bms[x.first]; const BE* e=be_of(v,x.first); if(!e||m.dir!=x.second||e->dist>apr(x.first)) continue;
                    int best=-1, bh=get_gp_h(lns,i,v); getNeighborLocs(&(lns.neighbors),nb,v);
                    for(int n:nb){ const int hh=get_gp_h(lns,i,n); if(hh<bh){bh=hh;best=n;} }
                    wl_best[i]=best; break; } } }
        if(bm_promote>0){ ++bm_stepc; bm_rank.assign(A,-1);
            for(int i=0;i<A;++i){ bm_prom[i]=0; const int v=prev_states[i].location; if(v<0) continue;
                if(chain_of[v]>=0){ bm_prom[i]=1; bm_rank[i]=0; bm_last_chain[i]=bm_stepc; continue; }
                if((bm_promote&2)&&bm_stepc-bm_last_chain[i]<=bm_exit_steps){ bm_prom[i]=1; continue; }   // just left a passage
                if(bm_promote&1) for(const auto& x:bm_cross[i]){ const auto& m=bms[x.first]; const BE* e=be_of(v,x.first);
                    if(m.dir==x.second&&!m.drain&&e&&e->dist<=apr(x.first)){ bm_prom[i]=1; bm_rank[i]=e->dist; if(bm_efcap>0) bm_efdoor[i]=x.first; break; } } }
            if(bm_efcap>0){   // p03: EF is policed to a small share (RFC 3246): per door only the efcap closest approaching crossers keep the promotion
                std::vector<std::pair<std::pair<int,int>,int>> ef; for(int i=0;i<A;++i){ if(bm_prom[i]&&bm_efdoor[i]>=0) ef.push_back({{bm_efdoor[i],bm_rank[i]},i}); bm_efdoor[i]=-1; }
                std::sort(ef.begin(),ef.end()); int last=-1,cnt=0; for(const auto& q:ef){ if(q.first.first!=last){last=q.first.first;cnt=0;} if(++cnt>bm_efcap){ bm_prom[q.second]=0; bm_rank[q.second]=-1; } } } }
        if(bm_demote){   // robots waiting for their side's turn get the lowest PIBT priority (they must not hold cells others need)
            for(int i=0;i<A;++i){ bm_blocked[i]=0; const int v=prev_states[i].location; if(v<0) continue;
                for(const auto& x:bm_cross[i]){ const auto& m=bms[x.first]; const BE* e=be_of(v,x.first);
                    if(m.dir>=0&&e&&(m.dir!=x.second||(m.drain&&e->dist>apr(x.first)))){ bm_blocked[i]=1; break; } } }
        }
        if(red_min>0){ ++red_step; const int N=int(env->map.size());
            std::vector<int> at(N,-1), nxt(A,-1), nb;
            for(int i=0;i<A;++i){ red_mark[i]=0; const int v=prev_states[i].location; if(v<0) continue; at[v]=i;
                if(v==red_last[i]) ++red_still[i]; else { red_still[i]=0; red_last[i]=v; } }
            for(int i=0;i<A;++i){ const int v=prev_states[i].location; if(v<0) continue;
                int best=-1, bh=get_gp_h(lns,i,v); getNeighborLocs(&(lns.neighbors),nb,v);
                for(int n:nb){ const int hh=get_gp_h(lns,i,n); if(hh<bh){bh=hh;best=n;} }
                nxt[i]=best; }
            const int red_max=3*red_min; const double max_p=0.1;
            for(int i=0;i<A;++i){ const int v=prev_states[i].location; if(v<0||chain_of[v]<0||env->goal_locations[i].empty()) continue;
                const int u=nxt[i]; if(u<0||chain_of[u]>=0) continue; const int m=at[u]; if(m<0||m==i) continue;
                if(m<int(env->system_states.size())&&env->system_states[m].delay.inDelay) continue;
                if(nxt[m]>=0&&chain_of[nxt[m]]==chain_of[v]) continue;   // the holder is itself crossing this passage
                const int q=red_still[m]; if(q<red_min) continue;
                ++red_cand; const double pr=q>=red_max?1.0:max_p*double(q-red_min)/double(red_max-red_min);
                const std::uint64_t h=mix(std::uint64_t(seed)*0x9E3779B97F4A7C15ull^std::uint64_t(red_step)<<20^std::uint64_t(i)*2654435761ull^0x524544ull);
                if(double(h>>11)*(1.0/9007199254740992.0)<pr){ red_mark[i]=1; ++red_hit; } }
            if(red_lf&&red_step%500==0){ std::fprintf(red_lf,"%lld %lld %lld%c",red_step,red_cand,red_hit,10); std::fflush(red_lf); } }
    }
    esc_update(env, lns, prev_states);   // p37
    {   // p11b (protocol round 11, item BEB): ROBOT_BACKOFF_COUNT=path only counts wait-v7 head-on standoffs (mutual desire,
        // both >= 2 steps without guide-distance progress) in robot-steps. No effect on behaviour; any_enabled() stays false.
        static const char* bcp=std::getenv("ROBOT_BACKOFF_COUNT");
        if(bcp){ static std::vector<int> cs, ch, cd; static long long rs=0, so=0, pairs=0, calls=0; const int A=env->num_of_agents;
            if(int(cs.size())!=A){ cs.assign(A,0); ch.assign(A,-1); }
            cd.assign(A,-1); std::vector<int> at(env->map.size(),-1), nb;
            for(int i=0;i<A;++i){ const int v=prev_states[i].location; if(v<0) continue; at[v]=i;
                int best=v, bh=get_gp_h(lns,i,v); getNeighborLocs(&(lns.neighbors),nb,v);
                for(int n:nb){ const int hh=get_gp_h(lns,i,n); if(hh<bh){bh=hh;best=n;} }
                cd[i]=best; if(ch[i]>=0&&bh>=ch[i]&&best!=v) ++cs[i]; else if(bh<ch[i]) cs[i]=0; ch[i]=bh; }
            for(int i=0;i<A;++i){ const int d=cd[i]; if(d<0||d==prev_states[i].location) continue; const int j=at[d];
                if(j<0||j<i) continue; if(cd[j]==prev_states[i].location&&cs[i]>=2&&cs[j]>=2){ ++pairs; so+=2; } }
            rs+=A; if(++calls%500==0){ if(std::FILE* f=std::fopen(bcp,"w")){ std::fprintf(f,"{\"robotSteps\": %lld, \"standoffRobotSteps\": %lld, \"pairs\": %lld, \"calls\": %lld}\n",rs,so,pairs,calls); std::fclose(f);} } }
    }
    if(!any_enabled()) return;
    ++step; ++st_steps; const int A=env->num_of_agents;
    std::fill(backlog.begin(),backlog.end(),0);
    std::vector<int> neigh;
    for(int i=0;i<A;++i){
        const int v=prev_states[i].location; loc_now[i]=v;
        // desired next cell = PIBT's first preference (min guide-path heuristic, prefer forward, then stay)
        int best=v; int bh=get_gp_h(lns,i,v);
        getNeighborLocs(&(lns.neighbors),neigh,v);
        for(int n:neigh){int hh=get_gp_h(lns,i,n); if(hh<bh){bh=hh;best=n;}}
        desired[i]=best; if(best!=v) ++backlog[best];
        // progress tracking for backoff
        if(bo){ if(last_h[i]>=0&&bh>=last_h[i]&&best!=v) ++stuck[i]; else if(bh<last_h[i]) {stuck[i]=0; bo_exp[i]=0;} last_h[i]=bh; }
    }
    if(bo){
        std::vector<int> at(env->map.size(),-1); for(int i=0;i<A;++i) at[loc_now[i]]=i;
        for(int i=0;i<A;++i){ int d=desired[i]; if(d==loc_now[i]) continue; int j=at[d]; if(j<0||j<i) continue;
            if(desired[j]==loc_now[i]&&stuck[i]>=bo_k&&stuck[j]>=bo_k&&bo_until[i]<step&&bo_until[j]<step){
                ++st_headon; // head-on "collision": each side backs off with prob 1/2 (at least one)
                std::uint64_t h=mix(std::uint64_t(seed)*0x9E3779B97F4A7C15ull^std::uint64_t(step)<<20^std::uint64_t(i)*1315423911ull^std::uint64_t(j));
                int who = (h&1)? i : j;
                int w = 1 + int((h>>8)%(std::uint64_t(1)<<std::min(bo_exp[who],bo_maxexp)));
                bo_until[who]=step+w; bo_exp[who]=std::min(bo_exp[who]+1,bo_maxexp); ++st_backoffs; } }
    }
    if(hdx){
        for(auto& L:links){ L.inside=0; L.qA=L.qB=0; }
        std::vector<int> moving_dir(links.size(),0);
        for(int i=0;i<A;++i){ const int v=loc_now[i]; const int l=link_of[v];
            if(l<0){ agent_side[i]=0;
                // queue at link ends: agents outside whose desired cell is inside a link
                const int dl=link_of[desired[i]]; if(dl>=0){ int e=entry_dir(links[dl],v); if(e>0)++links[dl].qA; else if(e<0)++links[dl].qB; }
                continue; }
            auto& L=links[l]; ++L.inside;
            int dir=agent_side[i];
            if(desired[i]!=v){ int dl=link_of[desired[i]]; if(dl==l) dir=(pos_in[desired[i]]>pos_in[v])?1:-1; else dir=(desired[i]==L.outB)?1:(desired[i]==L.outA?-1:dir); }
            if(dir!=0) agent_side[i]=dir, moving_dir[l]+=dir;
        }
        for(size_t l=0;l<links.size();++l){ auto& L=links[l];
            int nd = L.inside==0?0:(moving_dir[l]>0?1:(moving_dir[l]<0?-1:L.dir));
            if(nd!=0&&nd==L.dir) ++L.hold; else if(nd!=0){L.hold=1;}
            if(nd!=0) L.last_dir=nd;
            L.dir=nd;
            if(L.inside==0){L.stall=0;L.open=false;}
        }
    }
}
double key_bonus(int agent){
    if(!any_enabled()) return 0;
    double b=0;
    if(mp_kappa>0){ const int v=loc_now[agent], d=desired[agent]; b+=mp_kappa*(double(backlog[v]) - (d!=v?double(backlog[d]-1):0.0)); }
    if(bo&&bo_until[agent]>=step) b-=1e6;
    return b;
}
bool allow_move(int agent,int from,int to){
    if(wd_k>0&&agent>=0&&agent<int(wd_free.size())&&wd_free[agent]&&from!=to){ ++wd_hits; return true; }   // p35 PFC watchdog
    if(bm_lane&&from>=0&&to>=0&&from!=to){
        if(lane_c[to]>=0&&from!=lane_c[to]&&from!=lane_a[to]){ ++lane_denied; return false; }
        if(lane_c[from]>=0&&to!=lane_c[from]&&to!=lane_a[from]){ ++lane_denied; return false; }
    }
    if((bmac||lmac)&&!bms.empty()&&from>=0&&to>=0){
        // same order of checks as v19 (per passage: evacuation of the receiving apron first, then entry, then apron entry)
        for(const auto& e:cell_be[from]){ auto& m=bms[e.b]; if(m.dir<0||chain_of[from]==e.b) continue;
            if(bm_chainfree&&chain_of[from]>=0){ if(from!=to&&chain_of[to]==e.b&&m.dir!=e.side){ ++m.denied; return false; } continue; }
            const int s=e.side; const bool crosser=cross_side(agent,e.b)==s;
            if(bm_evac&&m.dir!=s&&e.dist<=apr(e.b)){
                // receiving side: a robot that wants to cross the other way must leave the apron (no waiting, no step inwards)
                if(crosser){ const BE* et=be_of(to,e.b); bool out=(chain_of[to]!=e.b)&&(!et||(et->side==s&&et->dist>e.dist));
                    if(!out&&bm_etr_k>0&&bm_etr[e.b]) out=(chain_of[to]!=e.b)&&(!et||et->dist>=bm_etr_k);   // p12: early token, may wait/advance to >= k
                    if(!out){ ++m.denied; return false; } }
                continue;
            }
            if(from==to) continue;
            if(chain_of[to]==e.b){ if(m.dir!=s){ ++m.denied; return false; }
                if(bm_credit&&s>=0&&s<2&&!bm_exit[e.b][1-s].empty()){ bool cr=false; for(int x:bm_exit[e.b][1-s]) if(!occ_now[x]) cr=true; if(!cr){ ++credit_denied; return false; } }
                continue; }
            // a crosser may step into its own side's apron only during its side's turn (and not while that turn drains)
            if(crosser&&e.dist>apr(e.b)&&(m.dir!=s||m.drain)){ const BE* et=be_of(to,e.b);
                const bool etr_ok=bm_etr_k>0&&m.dir!=s&&bm_etr[e.b]&&et&&et->dist>=bm_etr_k;   // p12: early token lets the other side in (not too close)
                if(et&&et->side==s&&et->dist<=apr(e.b)&&!etr_ok){ ++m.denied; return false; } }
        }
    }
    if(!hdx||from==to||to<0) return true;
    const int lt=link_of[to]; if(lt<0) return true;
    if(link_of[from]==lt) return true;              // already inside: never block
    auto& L=links[lt]; if(L.open) return true;
    const int e=entry_dir(L,from); if(e==0) return true;
    bool ok=true;
    if(L.inside>0){
        if(L.dir!=0&&L.dir!=e) ok=false;           // carrier sense: never enter against traffic
        else if(L.dir==e&&L.hold>=hdx_hold&&((e>0)?L.qB:L.qA)>0) ok=false; // max hold reached, other side waiting: drain & switch
    } else {
        const int qs=(e>0)?L.qA:L.qB, qo=(e>0)?L.qB:L.qA;
        if(qs>0&&qo>0&&L.last_dir==e) ok=false;     // both sides waiting: round-robin turn to the other side
    }
    if(!ok) ++st_denied;
    return ok;
}
void end_step(const std::vector<State>& prev_states,const std::vector<State>& next_states){
    if(dl_on&&!dl_best.empty()&&dl_lns){ const int A=int(prev_states.size()); const int N=int(chain_of.size()); ++dl_steps;
        std::vector<int> at(N,-1); std::vector<char> busy(N,0); std::vector<int> nb;
        for(int j=0;j<A;++j){ const int u=prev_states[j].location, w=next_states[j].location; if(u>=0){at[u]=j;busy[u]=1;} if(w>=0) busy[w]=1; }
        for(int i=0;i<A;++i){ const int v=prev_states[i].location; if(!dl_door(v)||!dl_goal[i]||dl_del[i]||next_states[i].location!=v) continue;
            auto& c=dl_c[chain_of[v]]; ++c[7]; const int u=dl_best[i]; if(u<0||chain_of[u]>=0) continue; const int m=at[u];
            if(m<0||m==i||dl_del[m]||next_states[m].location!=u) continue; ++c[8];
            bool fr=false; getNeighborLocs(&(dl_lns->neighbors),nb,u); for(int n:nb) if(chain_of[n]<0&&!busy[n]){fr=true;break;}
            if(!fr) continue; ++c[9]; const int bm=dl_best[m]; if(bm<0||chain_of[bm]!=chain_of[v]) ++c[10]; }
        // p30c (count only): planner side of M-1. Mouth robots heading into a door (as in mouth_exec), not delayed, with a goal, whose best
        // guide cell is empty at the start of the step, planned to stay put (same cell): [24] Pw, [25] Ptake (another robot
        // enters that cell this step), [26] Prule (nobody enters, BMAC door rule blocks it), [27] Pdoor (nobody enters, not blocked, the
        // cell is a door cell), [28] Pother (nobody enters, not blocked, not a door cell).
        // p30e: Ptake split by the robot that takes the cell: [29] Tout (it stood in a door cell), [30] Tsame (it is in a mouth heading into a
        // door too), [31] Tcross (anything else: cross traffic) -- only Tcross costs door throughput.
        if(!m_dist.empty()) for(int i=0;i<A;++i){ const int v=prev_states[i].location; if(v<0||v>=N||dl_door(v)||m_dist[v]<1||m_dist[v]>3||!dl_goal[i]||dl_del[i]) continue;
            const int u=dl_best[i]; if(u<0||u>=N||m_dist[u]>=m_dist[v]) continue;
            if(at[u]>=0){   // p31a (M-1c, count only): the best cell is occupied at step start by m -- [32] Pocc (m not delayed), [33] Pvac (m also planned to leave u)
                const int m=at[u]; if(m==i||next_states[i].location!=v||dl_del[m]) continue; const int g=m_door[v]; if(g<0||g>=int(dl_c.size())) continue;
                ++dl_c[g][32]; if(next_states[m].location!=u) ++dl_c[g][33]; continue; }
            if(next_states[i].location!=v) continue;   // p30d: PIBT next states carry no heading (orientation -1), compare the cell only
            const int g=m_door[v]; if(g<0||g>=int(dl_c.size())) continue; auto& c=dl_c[g]; ++c[24];
            int took=-1; for(int j=0;j<A;++j) if(j!=i&&next_states[j].location==u){took=j;break;}
            if(took>=0){ ++c[25];   // p30e (M-1b): who took it -- [29] Tout from a door cell, [30] Tsame also heading into a door here, [31] Tcross
                const int pj=prev_states[took].location, bj=took<int(dl_best.size())?dl_best[took]:-1;
                if(dl_door(pj)) ++c[29]; else if(pj>=0&&pj<N&&bj>=0&&bj<N&&m_dist[pj]<=3&&m_dist[bj]<m_dist[pj]) ++c[30]; else ++c[31]; } else if(blocked(i)) ++c[26]; else if(dl_door(u)) ++c[27]; else ++c[28]; }
        dl_dump(); }
    if(wl&&!wl_best.empty()){ const int A=int(prev_states.size());
        std::vector<int> at(link_of.size()>0?link_of.size():chain_of.size(),-1); for(int j=0;j<A;++j) if(prev_states[j].location>=0) at[prev_states[j].location]=j;
        for(int i=0;i<A;++i){ const int b=wl_best[i]; if(b<0||next_states[i].location!=prev_states[i].location) continue;
            const char* why="free_but_stayed"; const int j=at[b];
            int taker=-1; for(int k=0;k<A;++k) if(k!=i&&next_states[k].location==b&&prev_states[k].location!=b){taker=k;break;}
            if(j>=0&&next_states[j].location==b) why=blocked(j)?"occupant_stays_demoted":(chain_of[b]>=0?"occupant_stays_in_chain":"occupant_stays");
            else if(taker>=0) why="cell_taken_by_other";
            else if(j>=0) why=TcpWin::hitcell(i,b)?"occupant_moved_not_followed_head":"occupant_moved_not_followed";
            else if(!allow_move(i,prev_states[i].location,b)) why="mac_denied";
            std::fprintf(wl,"%lld %d %d %d %s\n",wl_step,i,prev_states[i].location,b,why); }
        for(int i=0;i<A;++i){ const int u=prev_states[i].location, v=next_states[i].location;   // p11: entries into a passage (crossings)
            if(u>=0&&v>=0&&u!=v&&chain_of[v]>=0&&chain_of[u]<0) std::fprintf(wl,"%lld %d C\n",wl_step,i); } }
    if(!hdx) return;
    std::vector<char> moved(links.size(),0), has(links.size(),0);
    for(size_t i=0;i<prev_states.size();++i){ int l=link_of[prev_states[i].location]; if(l<0) continue; has[l]=1; if(next_states[i].location!=prev_states[i].location) moved[l]=1; }
    for(size_t l=0;l<links.size();++l){ auto& L=links[l]; if(has[l]&&!moved[l]){ if(++L.stall>=hdx_stall&&!L.open){L.open=true;++st_stall_open;} } else L.stall=0; }
}
void write_stats(SharedEnvironment* env){
    if(bm_credit&&env->curr_timestep%500==0){ int ne=0; for(const auto& x:bm_exit) ne+=int(x[0].size()+x[1].size()); std::fprintf(stderr,"[credit] t=%d denied %lld exits %d\n",env->curr_timestep,credit_denied,ne); std::fflush(stderr); }
    static int bm_last=-1; if(bmac&&std::getenv("ROBOT_BMAC_TRACE")&&env->curr_timestep/500!=bm_last&&(bm_last=env->curr_timestep/500,true)) for(size_t b=0;b<bms.size();++b) std::fprintf(stderr,"[bmac] t=%d bridge %zu dir %d switches %lld denied %lld\n",env->curr_timestep,b,bms[b].dir,bms[b].switches,bms[b].denied);
    const char* p=std::getenv("ROBOT_NETMAC_TRACE"); if(!p||!any_enabled()) return;
    std::ofstream f(p,std::ios::app);
    size_t cells=0; for(auto& L:links) cells+=L.cells.size();
    f<<nlohmann::json({{"tick",env->curr_timestep},{"links",links.size()},{"linkCells",cells},{"steps",st_steps},{"denied",st_denied},{"headOn",st_headon},{"backoffs",st_backoffs},{"stallOpens",st_stall_open}}).dump()<<"\n";
}
}}
