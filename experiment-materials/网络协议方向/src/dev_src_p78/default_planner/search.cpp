#include <cmath>
#include <cstdlib>
#include <cstdio>
#include <algorithm>
#include <vector>



#include "search.h"
#include "seg_route.h"
#include "observed_wait.h"
#include "window_control.h"
#include "load_balance.h"
#include "netmac.h"
#include <string>


namespace DefaultPlanner{
std::chrono::nanoseconds t;
// v16 (round 26): temporary vertex cost on cells occupied by robots that are in an execution delay (set by the planner)
std::vector<int> v16_block_pen;
// p28 (TE-6, Fortz & Thorup INFOCOM 2000): ROBOT_TE_FT=1|2 -- every plan call, a robot with a task, not delayed, on the same cell as
// at the previous call and outside a cut door's zone counts one wait on its cell. Every 100 calls each cell's utilisation u = calls
// with a waiting robot / 100, and the guide-path A* charges (slope of the Fortz-Thorup piecewise-linear cost at u) - 1 extra moves
// on entering it: slopes 1, 3, 10, 70 for u < 1/3, < 2/3, < 9/10, >= 9/10 (=2: slope capped at 10). 0 = off.
std::vector<int> teft_pen;
void teft_observe(SharedEnvironment* env)
{
    static int mode = -1; if (mode < 0) { const char* e = std::getenv("ROBOT_TE_FT"); mode = e ? std::atoi(e) : 0; }
    if (mode <= 0) return;
    static std::vector<int> last, cnt; static int calls = 0;
    const int A = env->num_of_agents, N = env->map.size();
    if ((int)last.size() != A) last.assign(A, -1);
    if ((int)cnt.size() != N) { cnt.assign(N, 0); teft_pen.assign(N, 0); }
    std::vector<char> seen(N, 0);
    for (int a = 0; a < A && a < (int)env->system_states.size(); a++)
    {
        const int v = env->system_states[a].location;
        const bool task = a < (int)env->curr_task_schedule.size() && env->curr_task_schedule[a] >= 0;
        if (task && v == last[a] && !env->system_states[a].delay.inDelay && !NetMac::door_zone(v) && !seen[v]) { seen[v] = 1; ++cnt[v]; }
        last[a] = v;
    }
    if (++calls < 100) return;
    calls = 0;
    for (int v = 0; v < N; v++)
    {
        const double u = cnt[v] / 100.0; int slope = u < 1.0 / 3 ? 1 : u < 2.0 / 3 ? 3 : u < 0.9 ? 10 : 70;
        if (mode == 2 && slope > 10) slope = 10;
        teft_pen[v] = slope - 1; cnt[v] = 0;
    }
}
static bool v18_ignore_pause = false;
// p55: CSPF with a path-length constraint (RSVP-TE RFC 3209 / PCE RFC 4655; SMORE NSDI 2018 bounds path stretch). ROBOT_CSPF=r
// (percent, 0 = off): the guide path may be at most S = max(2, r*D0/100) cells longer than the start heuristic D0; nodes with
// g + h > D0 + S are pruned. If nothing fits (one-way doors, room pause), search again without the constraint.
static bool p55_unconstrained = false;
static int p55_r() { static int r = -1; if (r < 0) { const char* e = std::getenv("ROBOT_CSPF"); r = e ? std::atoi(e) : 0; } return r; }

// p56: BGP route flap damping (RFC 2439). One map-wide figure of merit P = exponentially weighted share of robot-ticks spent on
// wasted in-place turns (turn, then turn back before moving; same definition as round 50). P > S (ROBOT_RFD=S, 1/10000) turns the
// HN-SPF damping below on; P < 0.375*S (RFC 2439 default reuse/suppress = 750/2000) turns it off. Half-life ROBOT_RFD_HALF ticks.
namespace Rfd {
namespace { int S = -1; double decay = 1, P = 0, norm = 0; bool act = false; int warm = 0; long long ticks_on = 0; int last_t = -1;
    std::vector<int> loc, ori, turns, net, waste; }
static bool enabled() { if (S < 0) { const char* e = std::getenv("ROBOT_RFD"); S = e ? std::atoi(e) : 0; const char* h = std::getenv("ROBOT_RFD_HALF");
    warm = h ? std::atoi(h) : 1500; decay = std::pow(0.5, 1.0 / std::max(1, warm)); } return S > 0; }
bool active() { return enabled() && act; }
void observe(SharedEnvironment* env) {
    if (!enabled() || env->system_timestep == last_t) return;
    last_t = env->system_timestep;
    const int N = int(env->system_states.size());
    if (int(loc.size()) != N) { loc.assign(N, -1); ori.assign(N, 0); turns.assign(N, 0); net.assign(N, 0); waste.assign(N, 0); }
    int flaps = 0;
    for (int i = 0; i < N; i++) {
        const auto& s = env->system_states[i];
        if (s.location != loc[i]) { loc[i] = s.location; ori[i] = s.orientation; turns[i] = net[i] = waste[i] = 0; continue; }
        if (s.orientation == ori[i]) continue;
        ++turns[i]; net[i] += ((s.orientation - ori[i] + 4) % 4 == 1) ? 1 : -1; ori[i] = s.orientation;
        const int n = ((net[i] % 4) + 4) % 4, w = turns[i] - std::min(n, 4 - n);
        if (w > waste[i]) { flaps += w - waste[i]; waste[i] = w; }
    }
    P = P * decay + (N > 0 ? 3.0 * flaps / N : 0.0); norm = norm * decay + 1.0;
    const double share = P / norm * 10000.0;
    if (last_t >= warm) { if (!act && share > S) act = true; else if (act && share < 0.375 * S) act = false; }
    if (act) ++ticks_on;
    static const char* lp = std::getenv("ROBOT_RFD_LOG");
    if (lp && last_t % 500 == 0) if (std::FILE* f = std::fopen(lp, "w")) { std::fprintf(f, "{\"t\": %d, \"ticks_on\": %lld, \"share_bp\": %.2f}\n", last_t, ticks_on, share); std::fclose(f); }
}
}

// p53: HN-SPF (Khanna & Zinky, SIGCOMM 1989). ARPANET's 1980 SPF used measured delay as link cost and oscillated; HN-SPF caps a
// link's cost (ROBOT_HNSPF=M: at most M extra steps per cell) and limits how fast the reported cost moves (ROBOT_HNSPF_STEP=s:
// frozen within a timestep, then at most s per elapsed timestep toward the raw flow cost), so all robots do not re-route together.
namespace Hnspf {
namespace { int cap = -1, step = 0; std::vector<int> rep, stamp; }
static bool vonly = false;   // p54: ROBOT_HNSPF_VONLY=1
static bool on() { if (cap < 0) { const char* e = std::getenv("ROBOT_HNSPF"); cap = e ? std::atoi(e) : 0; const char* t = std::getenv("ROBOT_HNSPF_STEP"); step = t ? std::atoi(t) : 0;
    const char* v = std::getenv("ROBOT_HNSPF_VONLY"); vonly = v && std::atoi(v) > 0; } return cap > 0 && (!Rfd::enabled() || Rfd::active()); }
// p54 (log only): ROBOT_HNSPF_LOG=<path> -- histogram of the contra-flow and same-cell terms seen by A* (0,1,2,3-5,6-10,>10).
static long long hist[2][6];
static void dump() { static const char* p = std::getenv("ROBOT_HNSPF_LOG"); if (!p) return;
    if (std::FILE* f = std::fopen(p, "w")) { std::fprintf(f, "{\"op\": [%lld,%lld,%lld,%lld,%lld,%lld], \"vertex\": [%lld,%lld,%lld,%lld,%lld,%lld]}\n",
        hist[0][0],hist[0][1],hist[0][2],hist[0][3],hist[0][4],hist[0][5],hist[1][0],hist[1][1],hist[1][2],hist[1][3],hist[1][4],hist[1][5]); std::fclose(f); } }
static void log(int op, int v) { static const bool lg = [](){ bool b = std::getenv("ROBOT_HNSPF_LOG") != nullptr; if (b) std::atexit(dump); return b; }(); if (!lg) return;
    auto bin = [](int x){ return x <= 2 ? x : x <= 5 ? 3 : x <= 10 ? 4 : 5; }; ++hist[0][bin(op)]; ++hist[1][bin(v)];
    static long long n = 0; if ((++n & ((1LL << 20) - 1)) == 0) dump(); }   // the program may exit without atexit handlers
static int cost(SharedEnvironment* env, int cell, int d, int raw) {
    raw = std::min(raw, cap);
    if (step <= 0) return raw;
    const size_t k = size_t(cell) * 4 + size_t(d);
    if (rep.size() < env->map.size() * 4) { rep.assign(env->map.size() * 4, -1); stamp.assign(env->map.size() * 4, -1); }
    const int t = env->system_timestep;
    if (rep[k] < 0) { rep[k] = raw; stamp[k] = t; }
    else if (stamp[k] != t) {
        const int lim = step * std::max(1, t - stamp[k]);
        rep[k] = std::max(rep[k] - lim, std::min(rep[k] + lim, raw)); stamp[k] = t;
    }
    return rep[k];
}
}

// p77 (D-2): look-ahead routing (Galles, SGI Spider, Hot Interconnects 1996/97): the next hop is computed one router early, so
// a packet does not stall at the router to decide. Here: a robot should be facing the door before it reaches the door, so it does
// not stop in the door mouth to turn. ROBOT_PRETURN=k charges ROBOT_PRETURN_PEN (default 1: a quarter turn is one action, like a
// step) for a guide-path turn made on a cell within k steps (BFS over free cells) of a real room door; the door cells come from
// ROBOT_PRETURN_FILE ("row col" per line; round-76 rule: both sides are rooms of >= 25 cells). 0 = off.
namespace Preturn {
namespace { int k = -1, pen = 1; std::vector<char> zone; }
static bool on(SharedEnvironment* env) {
    if (k < 0) {
        const char* e = std::getenv("ROBOT_PRETURN"); k = e ? std::atoi(e) : 0;
        const char* p = std::getenv("ROBOT_PRETURN_PEN"); if (p) pen = std::atoi(p);
        if (k > 0) {
            const int n = int(env->map.size()), C = env->cols; std::vector<int> dist(n, -1); std::vector<int> q;
            const char* f = std::getenv("ROBOT_PRETURN_FILE");
            if (std::FILE* fp = f ? std::fopen(f, "r") : nullptr) { int r, c; while (std::fscanf(fp, "%d %d", &r, &c) == 2) { const int v = r * C + c; if (v >= 0 && v < n && !env->map[v] && dist[v] < 0) { dist[v] = 0; q.push_back(v); } } std::fclose(fp); }
            for (size_t i = 0; i < q.size(); i++) { const int v = q[i]; if (dist[v] >= k) continue;
                const int nb[4] = { v % C + 1 < C ? v + 1 : -1, v + C < n ? v + C : -1, v % C > 0 ? v - 1 : -1, v - C >= 0 ? v - C : -1 };
                for (int u : nb) if (u >= 0 && !env->map[u] && dist[u] < 0) { dist[u] = dist[v] + 1; q.push_back(u); } }
            zone.assign(n, 0); int z = 0; for (int v = 0; v < n; v++) if (dist[v] >= 0) { zone[v] = 1; ++z; }
            std::fprintf(stderr, "[preturn] k %d pen %d zone cells %d (file %s)\n", k, pen, z, f ? f : "none");
        }
    }
    return k > 0 && !zone.empty();
}
static bool in_zone(int v) { return v >= 0 && v < int(zone.size()) && zone[v]; }
}

// p78 (D-1): virtual output queues (McKeown et al., IEEE Trans. Commun. 1999): an input port queues per output, so a packet for a
// busy output does not block packets behind it. Robots have no buffer, so keep waiting cells and through cells apart instead: on the
// few doors picked from measured head-of-line blocking (ROBOT_VOQ_FILE, "row col dist" per line, door cells 0, apron 1-2),
// ROBOT_VOQ=p charges p for a guide-path step that runs along the apron (same distance) or dips into it and leaves without crossing.
// A robot that crosses moves 3-2-1-0-1-2-3 and pays nothing. 0 = off.
namespace Voq {
namespace { int pen = -1; std::vector<signed char> dist; }
static bool on(SharedEnvironment* env) {
    if (pen < 0) {
        const char* e = std::getenv("ROBOT_VOQ"); pen = e ? std::atoi(e) : 0;
        if (pen > 0) {
            const int n = int(env->map.size()), C = env->cols; int z = 0;
            const char* f = std::getenv("ROBOT_VOQ_FILE");
            if (std::FILE* fp = f ? std::fopen(f, "r") : nullptr) { int r, c, d; while (std::fscanf(fp, "%d %d %d", &r, &c, &d) == 3) { const int v = r * C + c; if (v >= 0 && v < n) { if (dist.empty()) dist.assign(n, 3); dist[v] = (signed char)d; ++z; } } std::fclose(fp); }
            std::fprintf(stderr, "[voq] pen %d zone cells %d (file %s)\n", pen, z, f ? f : "none");
        }
    }
    return pen > 0 && !dist.empty();
}
static int D(int v) { return v >= 0 && v < int(dist.size()) ? dist[v] : 3; }
static int cost(int parent, int curr, int next) {
    const int dc = D(curr), dn = D(next);
    if (dc == 0 || dc == 3) return 0;
    if (dn == dc) return pen;   // runs along the door mouth
    if (parent >= 0 && D(parent) > dc && dn > dc) return pen;   // dipped in and left without crossing
    return 0;
}
}

//a astar minimized the opposide traffic flow with existing traffic flow

s_node astar(SharedEnvironment* env, std::vector<Int4>& flow,
    HeuristicTable& ht, Traj& traj,
    MemoryPool& mem, int start, int goal, Neighbors* ns, const TimePoint* deadline)
{
    mem.reset();
    // v14: a turn costs a full action in execution, so charge it in the guide path (ROBOT_TURN_PEN=k), but only while the map is
    // free flowing (ROBOT_TURN_GATE=g: map-wide blocked share below g). In congested maps avoiding opposing flow matters more.
    static int turn_pen = -1; static double turn_gate = -2;
    if (turn_pen < 0) { const char* e = std::getenv("ROBOT_TURN_PEN"); turn_pen = e ? std::atoi(e) : 0; const char* g = std::getenv("ROBOT_TURN_GATE"); turn_gate = g ? std::stod(g) : -1; }
    const int turn_pen_now = turn_pen > 0 && (turn_gate < 0 || RobotWindow::free_flowing(turn_gate)) ? turn_pen : 0;
    // v37 (round 52): ROBOT_DOOR_TURN=k charges k for a turn made on a door-zone cell (RobotWindow::door_zone). A turn costs one
    // action, the same as a step, so k = 1. Reason (round 52 replay): a robot that turns on the cell in front of a 1-cell door holds
    // that cell for 3 actions instead of 2, which sets the same-direction headway to 9 ticks instead of 6.
    static int door_turn = -1; if (door_turn < 0) { const char* e = std::getenv("ROBOT_DOOR_TURN"); door_turn = e ? std::atoi(e) : 0; }
    const int rstart_v18 = RobotWindow::region_of(start), rgoal_v18 = RobotWindow::region_of(goal);
    const bool preturn_on = Preturn::on(env);   // p77
    const bool voq_on = Voq::on(env);   // p78

    int expanded=0;
    int generated=0;
    int h;

    if (is_large_map(env)){
        h = manhattanDistance(start,goal,env);
    }
    else{
        if(ht.empty())
            h = manhattanDistance(start,goal,env);
        else
            h = get_heuristic(ht,env, start, ns);
    }
    

    
    const int p55_lim = (p55_r() > 0 && !p55_unconstrained) ? h + std::max(2, p55_r() * h / 100) : -1;   // p55 CSPF
    s_node* root = mem.generate_node(start,0, h,0,0,0);

    if (start == goal){
        traj.clear();
        traj.push_back(start);
        return *root;
    }

    pqueue_min_of open;
    re_of re;

    open.push(root);

    int  diff, d, cost, op_flow, total_cross, all_vertex_flow,vertex_flow, depth,p_diff, p_d;
    int next_d1, next_d2, next_d1_loc, next_d2_loc;
    int temp_op, temp_vertex;
    // wait-v4 fix: upstream left this uninitialised; the root expansion (no parent) read stack garbage,
    // making guide paths depend on unrelated code/stack layout. Root children get no turn preference.
    double tie_breaker = 0, decay_factor = 0;

    s_node* goal_node = nullptr;
    int neighbors[4];
    int next_neighbors[4];



    while (open.size() > 0){
        if (deadline != nullptr && std::chrono::steady_clock::now() >= *deadline){
            return s_node();
        }
        s_node* curr = open.pop();
        curr->close();

        if (curr->id == goal){
            goal_node = curr;
            break;
        }
        expanded++;
        getNeighborLocs(ns,neighbors,curr->id);
        
        for (int i=0; i<4; i++){
            int next = neighbors[i];
            if (next == -1){
                continue;
            }
            if (!(v18_ignore_pause ? RobotWindow::move_allowed(curr->id, next) : RobotWindow::move_allowed_goal(curr->id, next, goal))) continue;   // v18b/f: one-way doors, room pause

            cost = curr->g+1;

            assert(next >= 0 && next < env->map.size());
            depth = curr->depth + 1;

            //moving direction
            //flow
            op_flow = 0;
            all_vertex_flow = 0;

            if(is_large_map(env)){
                h = manhattanDistance(next,goal,env);
            }
            else{
                if(ht.empty())
                    h = manhattanDistance(next,goal,env);
                else
                    h = get_heuristic(ht,env, next, ns);
            }

            if (p55_lim >= 0 && cost + h > p55_lim) continue;   // p55 CSPF: too long

            diff = next - curr->id;
            d = get_d(diff,env);
            if (curr->parent != nullptr){
                p_diff = curr->id - curr->parent->id;
                p_d = get_d(p_diff,env);
                if (p_d!=d)
                    tie_breaker = 0.1;
                else
                    tie_breaker = 0;
                //tie breaking on prefering moving forward
            }


            temp_op = ( (flow[curr->id].d[d]+1) * flow[next].d[(d+2)%4]);///( ( (flow[curr->id].d[d]+1) + flow[next].d[(d+2)%4]));

            //all vertex flow
            //the sum of all out going edge flow is the same as the total number of vertex visiting.
            temp_vertex = 1;
            for (int j=0; j<4; j++){
                temp_vertex += flow[next].d[j];                
            }

            Hnspf::log(temp_op, (temp_vertex-1)/2);
            if (Hnspf::on() && Hnspf::vonly) {   // p54: HN-SPF on the queueing (same-cell) term only; contra-flow term unchanged
                op_flow += temp_op;
                all_vertex_flow += Hnspf::cost(env, next, d, (temp_vertex-1)/2);
            } else if (Hnspf::on()) {   // p53: HN-SPF -- report a bounded, rate-limited flow cost instead of the raw one
                op_flow += Hnspf::cost(env, next, d, temp_op + (temp_vertex-1)/2);
            } else {
            op_flow += temp_op;
        
            if (LoadBalance::cap_on(env)) {   // v38 LBC: volume / capacity on door cells
                const double fac = LoadBalance::cap_factor(env, next);
                all_vertex_flow += fac == 1.0 ? (temp_vertex-1) /2 : int(std::lround(fac * double(temp_vertex-1) / 2.0));
            } else all_vertex_flow+= (temp_vertex-1) /2;
            }
            all_vertex_flow += LoadBalance::toll(env, curr->id, next);   // v38 LBS: system-optimal door toll (0 unless enabled)
            all_vertex_flow += SegRoute::toll(env, curr->id, next);   // v42 SR: door outside the robot's sequence (0 unless enabled)
            all_vertex_flow+= ObservedWait::path_penalty(curr->id,next); // wait-v5 (D5), 0 unless enabled
            if (turn_pen_now > 0 && curr->parent != nullptr && get_d(curr->id - curr->parent->id, env) != d) all_vertex_flow += turn_pen_now;   // v14: gated turn cost
            if (door_turn > 0 && curr->parent != nullptr && get_d(curr->id - curr->parent->id, env) != d && RobotWindow::door_zone(curr->id)) all_vertex_flow += door_turn;   // v37
            if (preturn_on && curr->parent != nullptr && get_d(curr->id - curr->parent->id, env) != d && Preturn::in_zone(curr->id)) all_vertex_flow += Preturn::pen;   // p77
            if (voq_on) all_vertex_flow += Voq::cost(curr->parent != nullptr ? curr->parent->id : -1, curr->id, next);   // p78
            if (!v16_block_pen.empty()) all_vertex_flow += v16_block_pen[next];   // v16: avoid robots stuck in a delay
            if (!teft_pen.empty()) all_vertex_flow += teft_pen[next];   // p28: Fortz-Thorup cell weight (0 unless ROBOT_TE_FT)
            all_vertex_flow += RobotWindow::transit_pen(next, rstart_v18, rgoal_v18);   // v18d: avoid crowded rooms in transit

            p_diff = 0;
            if (curr->parent != nullptr){
                p_diff = curr->id - curr->parent->id;
            }

            op_flow += curr->op_flow; //op_flow is contra flow
            all_vertex_flow += curr->all_vertex_flow;

            s_node temp_node(next,cost,h,op_flow, depth);
            temp_node.tie_breaker = tie_breaker;
            temp_node.set_all_flow(op_flow,  all_vertex_flow);

            if (!mem.has_node(next)){
                s_node* next_node = mem.generate_node(next,cost,h,op_flow, depth,all_vertex_flow);
                next_node->parent = curr;
                next_node->tie_breaker = tie_breaker;
                open.push(next_node);
                generated++;
            }
            else{ 
                s_node* existing = mem.get_node(next);

                if (!existing->is_closed()){
                    if (re(temp_node,*existing)){
                        existing->g = cost;
                        existing->parent = curr;
                        existing->depth = depth;
                        existing->tie_breaker = tie_breaker;
                        existing->set_all_flow(op_flow,  all_vertex_flow);
                        open.decrease_key(existing);
                    }
                }
                else{

                    if (re(temp_node,*existing)){ 
                        std::cout << "error in astar: re-expansion" << std::endl;
                        assert(false);
                        exit(1);
                    }

                } 
            }
        }
            

          
    }


    if (goal_node == nullptr && p55_lim >= 0){
        // p55: nothing within the length bound; search again unconstrained
        p55_unconstrained = true; s_node r = astar(env, flow, ht, traj, mem, start, goal, ns, deadline); p55_unconstrained = false; return r;
    }
    if (goal_node == nullptr && !v18_ignore_pause){
        // v18f: the room-pause rule can cut a robot off its goal; search again without it
        v18_ignore_pause = true; s_node r = astar(env, flow, ht, traj, mem, start, goal, ns, deadline); v18_ignore_pause = false; return r;
    }
    if (goal_node == nullptr){
        std::cout << "error in astar: no path found "<< start<<","<<goal << std::endl;
        assert(false);
        exit(1);
    }

    traj.resize(goal_node->depth+1);
    s_node* curr = goal_node;
    for (int i=goal_node->depth; i>=0; i--){
        traj[i] = curr->id;
        curr = curr->parent;
    }

    return *goal_node;
}
}
