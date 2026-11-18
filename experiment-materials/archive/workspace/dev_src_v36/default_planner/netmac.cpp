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
struct BM { bool cut=true; int bidx=-1; std::vector<int> cells; int dir=-1, hold=0; bool drain=false; long long switches=0, denied=0; int owait=0;
            std::vector<int> gate; };   // v32: robots waiting on the active side when its turn began (gated service)
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
std::vector<BM> bms; std::vector<std::vector<BE>> cell_be; std::vector<int> chain_of; std::vector<std::vector<int>> bside;
std::vector<int> bm_target; std::vector<char> bm_blocked; bool bm_demote=false;
// v24 (round 35): ROBOT_BMAC_LANE=1 -- a passage's mouth cells (the free cells next to its ends) may only be entered from / left to
// the passage itself or the next cell on the passage axis, so robots pass the mouth straight (no turning or side entry there).
bool bm_lane=false; std::vector<int> lane_a, lane_c; long long lane_denied=0;
std::vector<std::vector<std::pair<int,int>>> bm_cross;    // per agent: (bm, side) where the agent is a crosser this step
const BE* be_of(int cell,int b){ if(cell<0) return nullptr; for(const auto& e:cell_be[cell]) if(e.b==b) return &e; return nullptr; }
int cross_side(int agent,int b){ for(const auto& x:bm_cross[agent]) if(x.first==b) return x.second; return -1; }
}
bool any_enabled(){return hdx||bo||mp_kappa>0;}
int passage_count(){return lm_gate_detour<0?int(bms.size()):long_passages;}
int link_count(){int k=0; for(const auto& m:bms) if(!m.cut) ++k; return k;}
bool demote_active(){return (bmac||lmac)&&bm_demote&&!bms.empty();}
namespace { int bm_promote=0, bm_exit_steps=6; std::vector<char> bm_prom; std::vector<long long> bm_last_chain; long long bm_stepc=0; }
bool promote_active(){return (bmac||lmac)&&bm_promote>0&&!bms.empty();}
bool promoted(int a){return a>=0&&a<int(bm_prom.size())&&bm_prom[a];}
namespace { std::vector<int> bm_rank; }
int promote_rank(int a){return a>=0&&a<int(bm_rank.size())?bm_rank[a]:-1;}
bool blocked(int a){return a>=0&&a<int(bm_blocked.size())&&bm_blocked[a];}
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
    bm_batch=int(param("ROBOT_BMAC_BATCH",1,1,1000)); bm_maxwait=int(param("ROBOT_BMAC_MAXWAIT",0,0,1000000));
    bm_gated=std::getenv("ROBOT_BMAC_GATED")&&std::string(std::getenv("ROBOT_BMAC_GATED"))=="1"; bm_apron=int(param("ROBOT_BMAC_APRON",2,0,50)); bm_hold=int(param("ROBOT_BMAC_HOLD",40,1,100000)); bm_near=int(param("ROBOT_BMAC_NEAR",8,1,1000));
    lm_maxlen=int(param("ROBOT_LMAC_MAXLEN",4,1,1000)); lm_detour=int(param("ROBOT_LMAC_DETOUR",20,1,1000000));
    lm_gate_detour=std::getenv("ROBOT_LMAC_GATE_DETOUR")?int(param("ROBOT_LMAC_GATE_DETOUR",20,1,1000000)):-1; long_passages=0;
    bms.clear(); bside.clear(); cell_be.assign(N,{}); chain_of.assign(N,-1); bm_target.assign(A,-1); bm_blocked.assign(A,0); bm_cross.assign(A,{});
    bm_demote=std::getenv("ROBOT_BMAC_DEMOTE")&&std::string(std::getenv("ROBOT_BMAC_DEMOTE"))=="1";
    bm_promote=int(param("ROBOT_BMAC_PROMOTE",0,0,7)); bm_exit_steps=int(param("ROBOT_BMAC_EXIT_STEPS",6,0,1000)); bm_prom.assign(A,0); bm_last_chain.assign(A,-1000000); bm_stepc=0;
    const int R=std::max(bm_apron,bm_near);
    if(bmac){
        const int nb=RobotWindow::bridge_count(env);
        for(int b=0;b<nb;++b){
            std::vector<int> sd(N,-1); int parts=0;
            for(int v=0;v<N;++v){ if(env->map[v]) continue; sd[v]=RobotWindow::bridge_side(b,v); parts=std::max(parts,sd[v]+1); }
            if(parts!=2) continue;
            BM m; m.cut=true; m.bidx=int(bside.size()); m.cells=RobotWindow::bridge_cells(b); const int id=int(bms.size());
            std::vector<int> dist(N,-1); std::vector<int> q=m.cells; for(int c:q){ dist[c]=0; chain_of[c]=id; }
            for(size_t h=0;h<q.size();++h){ const int v=q[h]; if(dist[v]>=R) continue;
                for(int n:nbrs(env,v)) if(dist[n]<0){ dist[n]=dist[v]+1; q.push_back(n); if(sd[n]>=0) cell_be[n].push_back({id,sd[n],dist[n]}); } }
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
            for(size_t h=0;h<qq.size();++h){ const int v=qq[h]; if(dist[v]>=R) continue;
                for(int n:nbrs(env,v)) if(dist[n]<0&&!inch[n]){ dist[n]=dist[v]+1; sd[n]=sd[v]; qq.push_back(n);} }
            for(int v:qq) cell_be[v].push_back({id,sd[v],dist[v]});
            bms.push_back(std::move(m)); ++found;
        }
        if(std::getenv("ROBOT_BMAC_TRACE")) std::fprintf(stderr,"[lmac] links %lld (bridges %zu)\n",found,bside.size());
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
void begin_step(SharedEnvironment* env, TrajLNS& lns, const std::vector<State>& prev_states){
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
        std::vector<int> in_chain(bms.size(),0), w0(bms.size(),0), w1(bms.size(),0), a0(bms.size(),0), a1(bms.size(),0);
        for(int i=0;i<A;++i){ const int v=prev_states[i].location; if(v<0) continue;
            if(chain_of[v]>=0&&!(bm_idlechain&&env->goal_locations[i].empty())) ++in_chain[chain_of[v]];   // v25h: idle robots parked in a passage do not block the switch
            for(const auto& x:bm_cross[i]){ const BE* e=be_of(v,x.first); if(!e) continue;
                (x.second==0?w0:w1)[x.first]++; if(e->dist<=bm_apron) (x.second==0?a0:a1)[x.first]++; } }
        {   // v24t: diagnostic trace only (ROBOT_BMAC_LOG=path); no effect on behaviour
            static const char* lg=std::getenv("ROBOT_BMAC_LOG"); static std::FILE* lf=lg?std::fopen(lg,"w"):nullptr;
            if(lf){ std::vector<int> d0(bms.size(),0), d1(bms.size(),0), dc(bms.size(),0);
                for(int i=0;i<A;++i){ const int v=prev_states[i].location; if(v<0||i>=int(env->system_states.size())||!env->system_states[i].delay.inDelay) continue;
                    if(chain_of[v]>=0) ++dc[chain_of[v]];
                    for(const auto& x:bm_cross[i]){ const BE* e=be_of(v,x.first); if(e&&e->dist<=bm_apron) (x.second==0?d0:d1)[x.first]++; } }
                for(size_t b=0;b<bms.size();++b){ const auto& m=bms[b];
                    std::fprintf(lf,"%d %d %zu %d %d %d %d %d %d %d %d %d %d %d %lld\n",env->curr_timestep,env->system_timestep,b,m.dir,int(m.drain),m.hold,w0[b],w1[b],a0[b],a1[b],in_chain[b],d0[b],d1[b],dc[b],m.denied); } }
        }
        for(size_t b=0;b<bms.size();++b){ auto& m=bms[b]; const int wait[2]={w0[b],w1[b]}, apron[2]={a0[b],a1[b]};
            auto open_gate=[&](BM& mm, int side){ mm.gate.clear(); if(!bm_gated||side<0) return;
                for(int i=0;i<A;++i) for(const auto& x:bm_cross[i]) if(x.first==int(b)&&x.second==side){ mm.gate.push_back(i); break; } };
            if(m.dir<0){ if(wait[0]||wait[1]){ m.dir=wait[0]>=wait[1]?0:1; m.hold=0; m.drain=false; ++m.switches; open_gate(m,m.dir); } continue; }
            const int s=m.dir, o=1-s; ++m.hold;
            if(wait[o]>0) ++m.owait; else m.owait=0;
            const bool enough = wait[o]>=bm_batch || (bm_maxwait>0&&m.owait>=bm_maxwait) || bm_batch<=1;
            bool served=m.hold>=bm_hold;
            if(bm_gated){ served=true; for(int i:m.gate) if(cross_side(i,int(b))==s){ served=false; break; } }
            if(wait[o]>0&&enough&&(wait[s]==0||served)) m.drain=true;
            if(m.drain&&in_chain[b]==0&&apron[s]==0){ m.dir=wait[o]>0?o:(wait[s]>0?s:-1); m.hold=0; m.drain=false; m.owait=0; ++m.switches; open_gate(m,m.dir); }
        }
        if(wl||(wl=nullptr,false)){}
        { static const char* wlp=std::getenv("ROBOT_BMAC_WAITLOG"); if(wlp&&!wl) wl=std::fopen(wlp,"w"); }
        if(wl){ ++wl_step; wl_best.assign(A,-1); std::vector<int> nb;
            for(int i=0;i<A;++i){ const int v=prev_states[i].location; if(v<0) continue;
                for(const auto& x:bm_cross[i]){ const auto& m=bms[x.first]; const BE* e=be_of(v,x.first); if(!e||m.dir!=x.second||e->dist>bm_apron) continue;
                    int best=-1, bh=get_gp_h(lns,i,v); getNeighborLocs(&(lns.neighbors),nb,v);
                    for(int n:nb){ const int hh=get_gp_h(lns,i,n); if(hh<bh){bh=hh;best=n;} }
                    wl_best[i]=best; break; } } }
        if(bm_promote>0){ ++bm_stepc; bm_rank.assign(A,-1);
            for(int i=0;i<A;++i){ bm_prom[i]=0; const int v=prev_states[i].location; if(v<0) continue;
                if(chain_of[v]>=0){ bm_prom[i]=1; bm_rank[i]=0; bm_last_chain[i]=bm_stepc; continue; }
                if((bm_promote&2)&&bm_stepc-bm_last_chain[i]<=bm_exit_steps){ bm_prom[i]=1; continue; }   // just left a passage
                if(bm_promote&1) for(const auto& x:bm_cross[i]){ const auto& m=bms[x.first]; const BE* e=be_of(v,x.first);
                    if(m.dir==x.second&&!m.drain&&e&&e->dist<=bm_apron){ bm_prom[i]=1; bm_rank[i]=e->dist; break; } } } }
        if(bm_demote){   // robots waiting for their side's turn get the lowest PIBT priority (they must not hold cells others need)
            for(int i=0;i<A;++i){ bm_blocked[i]=0; const int v=prev_states[i].location; if(v<0) continue;
                for(const auto& x:bm_cross[i]){ const auto& m=bms[x.first]; const BE* e=be_of(v,x.first);
                    if(m.dir>=0&&e&&(m.dir!=x.second||(m.drain&&e->dist>bm_apron))){ bm_blocked[i]=1; break; } } }
        }
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
    if(bm_lane&&from>=0&&to>=0&&from!=to){
        if(lane_c[to]>=0&&from!=lane_c[to]&&from!=lane_a[to]){ ++lane_denied; return false; }
        if(lane_c[from]>=0&&to!=lane_c[from]&&to!=lane_a[from]){ ++lane_denied; return false; }
    }
    if((bmac||lmac)&&!bms.empty()&&from>=0&&to>=0){
        // same order of checks as v19 (per passage: evacuation of the receiving apron first, then entry, then apron entry)
        for(const auto& e:cell_be[from]){ auto& m=bms[e.b]; if(m.dir<0||chain_of[from]==e.b) continue;
            if(bm_chainfree&&chain_of[from]>=0){ if(from!=to&&chain_of[to]==e.b&&m.dir!=e.side){ ++m.denied; return false; } continue; }
            const int s=e.side; const bool crosser=cross_side(agent,e.b)==s;
            if(bm_evac&&m.dir!=s&&e.dist<=bm_apron){
                // receiving side: a robot that wants to cross the other way must leave the apron (no waiting, no step inwards)
                if(crosser){ const BE* et=be_of(to,e.b); const bool out=(chain_of[to]!=e.b)&&(!et||(et->side==s&&et->dist>e.dist)); if(!out){ ++m.denied; return false; } }
                continue;
            }
            if(from==to) continue;
            if(chain_of[to]==e.b){ if(m.dir!=s){ ++m.denied; return false; } continue; }
            // a crosser may step into its own side's apron only during its side's turn (and not while that turn drains)
            if(crosser&&e.dist>bm_apron&&(m.dir!=s||m.drain)){ const BE* et=be_of(to,e.b); if(et&&et->side==s&&et->dist<=bm_apron){ ++m.denied; return false; } }
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
    if(wl&&!wl_best.empty()){ const int A=int(prev_states.size());
        std::vector<int> at(link_of.size()>0?link_of.size():chain_of.size(),-1); for(int j=0;j<A;++j) if(prev_states[j].location>=0) at[prev_states[j].location]=j;
        for(int i=0;i<A;++i){ const int b=wl_best[i]; if(b<0||next_states[i].location!=prev_states[i].location) continue;
            const char* why="free_but_stayed"; const int j=at[b];
            int taker=-1; for(int k=0;k<A;++k) if(k!=i&&next_states[k].location==b&&prev_states[k].location!=b){taker=k;break;}
            if(j>=0&&next_states[j].location==b) why=blocked(j)?"occupant_stays_demoted":(chain_of[b]>=0?"occupant_stays_in_chain":"occupant_stays");
            else if(taker>=0) why="cell_taken_by_other";
            else if(j>=0) why="occupant_moved_not_followed";
            else if(!allow_move(i,prev_states[i].location,b)) why="mac_denied";
            std::fprintf(wl,"%lld %d %d %d %s\n",wl_step,i,prev_states[i].location,b,why); } }
    if(!hdx) return;
    std::vector<char> moved(links.size(),0), has(links.size(),0);
    for(size_t i=0;i<prev_states.size();++i){ int l=link_of[prev_states[i].location]; if(l<0) continue; has[l]=1; if(next_states[i].location!=prev_states[i].location) moved[l]=1; }
    for(size_t l=0;l<links.size();++l){ auto& L=links[l]; if(has[l]&&!moved[l]){ if(++L.stall>=hdx_stall&&!L.open){L.open=true;++st_stall_open;} } else L.stall=0; }
}
void write_stats(SharedEnvironment* env){
    static int bm_last=-1; if(bmac&&std::getenv("ROBOT_BMAC_TRACE")&&env->curr_timestep/500!=bm_last&&(bm_last=env->curr_timestep/500,true)) for(size_t b=0;b<bms.size();++b) std::fprintf(stderr,"[bmac] t=%d bridge %zu dir %d switches %lld denied %lld\n",env->curr_timestep,b,bms[b].dir,bms[b].switches,bms[b].denied);
    const char* p=std::getenv("ROBOT_NETMAC_TRACE"); if(!p||!any_enabled()) return;
    std::ofstream f(p,std::ios::app);
    size_t cells=0; for(auto& L:links) cells+=L.cells.size();
    f<<nlohmann::json({{"tick",env->curr_timestep},{"links",links.size()},{"linkCells",cells},{"steps",st_steps},{"denied",st_denied},{"headOn",st_headon},{"backoffs",st_backoffs},{"stallOpens",st_stall_open}}).dump()<<"\n";
}
}}
