#include "window_control.h"
namespace AdmitAuto { double lambda_star(SharedEnvironment* env); }
#include "bbr_admission.h"
#include "link_credit.h"
#include "netmac.h"
#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <mutex>
#include <unordered_map>
#include <map>
#include <cstdio>
#include <queue>
#include <functional>
#include <climits>
#include <unordered_set>

namespace RobotWindow {
namespace {
struct Reservation { int task = -1; int target_side = -1; BbrReceipt receipt; };
std::string policy = "baseline";
double floor_w = 2.0;
// v10 fairness telemetry: reveal time of tasks still in the pool, completed-task latency.
std::unordered_map<int,int> task_seen; long long lat_n = 0; double lat_sum = 0; int lat_max = 0; std::vector<int> lat_hist;
int axis = -1, cut = -1, cols = 0, boundary_edges = 0;
double window = 6, alpha = 0;
int last_update = 0, last_logged = -1, acknowledgements = 0, denied = 0;
int last_observed = -1;
long long opportunities = 0, marks = 0;
long long admitted_total = 0, acked_total = 0, cancelled_total = 0;
double last_fraction = 0;
std::mutex feedback_mutex;
std::vector<Reservation> reservations;
std::ofstream telemetry;
BbrAdmission bbr;
// ---- v10 multicut: one congestion window per bottleneck line ("a router at every door line") ----
struct Line { int axis = 0, cut = 0, edges = 0; double window = 6, alpha = 0; long long opp = 0, marks = 0; int acks = 0, denied = 0, inflight = 0;
              long long admitted = 0; double lastFrac = 0; bool active = true; int infl_dir[2] = {0, 0}; };
std::vector<Line> lines;
struct McRes { int task = -1; std::vector<std::pair<int,int>> pending; }; // (line index, target side)
std::vector<McRes> mcres;
bool mc_adaptive = false; double mc_floor = 2, mc_gate = 0;
// v11 switches: count every leg of the task (pickup AND delivery), per-direction windows, add the single best cut
bool mc_legs_all = false, mc_dir = false, mc_add_single = false;
// v12 (round 23): credit-based admission, borrowed from lossless networks. A pickup crossing of a line toward side s is
// admitted only while the landing zone on side s (cells within mc_zone of the line's crossing edges) still has credit:
// floor(mc_credit * zone cells) - robots standing in the zone - crossings already in flight toward s.  mc_hard: window 0.
double mc_credit = 0; int mc_zone = 2; bool mc_hard = false;
// v15: ROBOT_MC_SCOPE=door gives every door (a run of adjacent crossing edges) of a line its own landing zone and credit;
// the default (line) pools all doors of a line, as in v12-v14.  Keys: door*2 + side; with the line scope door is always 0.
int mc_scope = 0;
// v18 (round 28): region-occupancy admission. The detected door lines cut the map into regions (rooms). A pickup (or delivery)
// in another region is admitted only while that region's load -- robots inside plus robots already heading in -- stays below
// ROBOT_REGION_CAP x its free cells (credit = free buffer space of the destination; prevents rooms from turning into sinks).
double rg_cap = 0; std::vector<int> rg_of, rg_capv, rg_load, rg_counted; long long rg_denied = 0;
// v18b: one-way doors (deadlock avoidance by restricting directions, like one-way streets / turn models in networks-on-chip).
// Within each wall segment (between two perpendicular door lines) that has at least two doors, the doors alternate direction;
// a single door wider than one cell gets half of its lanes in each direction; a single 1-cell door stays two-way.
bool ow_on = false; std::vector<char> ow_forbid; int ow_doors = 0, ow_directed = 0;
// v18d: transit avoidance. When a room's robot density exceeds ROBOT_REGION_AVOID_TH, every cell of that room costs
// ROBOT_REGION_AVOID extra in guide-path search for robots that neither start nor end there (area-level congestion cost, as in
// hierarchical routing); the planner also recomputes guide paths that would pass through such a room.
int ra_pen = 0; double ra_th = 0.15; std::vector<int> ra_of, ra_cells, ra_occ; std::vector<char> ra_hot;
// v18f: room pause, like PFC pause frames in lossless Ethernet (XOFF/XON with hysteresis). When a room's robot density rises above
// ROBOT_ROOM_PAUSE, its doors stop letting robots in (except robots whose current goal is inside that room) and no new task is
// assigned that would send a robot into it; when the density falls below ROBOT_ROOM_RESUME, the room opens again.
double rp_off = 0, rp_on = 0; std::vector<int> rp_of, rp_cells, rp_occ; std::vector<char> rp_paused;
std::vector<int> rp_edge_region;   // per (cell*4+dir): region entered through this door edge, -1 if not a door edge into a room
long long rp_pause_events = 0;
std::vector<std::vector<int>> zone_of;                   // per line: cell -> -1 / key
std::vector<std::vector<int>> zcap, zocc, zinfl;          // per line, per key
std::vector<std::vector<int>> door_of_along;             // per line: along-coordinate -> door index (-1 = no crossing edge)
std::vector<std::vector<double>> door_center;            // per line: mean along-coordinate of each door
// v14: map-wide congestion signal
long long g_opp = 0, g_marks = 0; double g_alpha = 0; int g_last = 0, g_last_obs = -1, g_now = 0; bool g_init = false, g_door_seen = false;

// v19: bridge credit. A bridge is a chain of cut cells (articulation points of the free-cell graph) whose removal leaves
// at least two parts holding >= ROBOT_BRIDGE_FRAC of the free cells each (a single-lane link between two big areas).
// ROBOT_BRIDGE_CREDIT=K: at most K robots may have a remaining route that crosses a bridge into the same part
// (credit-based flow control on a bottleneck link; new crossing assignments wait until credit returns).
int br_K = 0; double br_frac = 0.05; bool br_trace = false;
std::vector<char> dz_mask;   // v37: door zone (see the end of br_detect)
// v26 (round 38): ROBOT_CUT2_CREDIT=K2 -- also find pairs of 1-cell doors whose joint removal splits the map into big parts
// (a two-door wall that is the only connection between two regions) and give them a per-direction credit K2. These pairs get
// credit only; the door rule (NetMac) still sees only single cuts (bridge_count()).
int br_K2 = 0, br_n1 = 0; std::vector<int> br_Kb;
std::vector<std::vector<int>> br_side;                       // per bridge: big-part id of each cell, -1 otherwise
std::vector<int> br_nparts; std::vector<std::vector<int>> br_cells;
std::vector<std::vector<int>> br_load;                       // per bridge, per destination part: robots in flight
std::vector<std::vector<std::pair<int,int>>> br_counted;    // per agent: (bridge, part) entries currently counted
std::vector<std::pair<int,int>> br_tmp; long long br_denied = 0, br_admitted = 0; int br_last_trace = -1;
int br_cols = 0;
// v28 (round 41, network model): ROBOT_NET=1 -- the credit of every cut and every direction comes from the network model
// instead of a hand-set number. Credit = bandwidth x delay (TCP bandwidth-delay product):
//   K[b][s] = ceil(alpha * T_free(b, s) * n_doors(b) * c1 / 2)
//   T_free(b, s): ROBOT_NET_LEG1 + mean, over the cells of the other side(s), of the free-flow time to the cut's door cells
//                 (MAPF_T model: a move or a 90-degree turn takes 3 ticks; reverse Dijkstra over (cell, heading));
//   c1 = ROBOT_NET_C1, measured effective bandwidth of a 1-cell door (crossings per tick, round 40: 26 per 500 ticks);
//   alpha = ROBOT_NET_ALPHA, measured slow-down of the real delay over the free-flow delay (round 40: 2.23 with faults).
// ROBOT_CUT2_SIGFIX=1 (implied by ROBOT_NET): two door pairs are duplicates only if they cut off the same cells (the old
// check compared part sizes only, so two different 225-cell rooms counted as one).
int net_on = 0, c2_sigfix = 0; double net_alpha = 2.23, net_c1 = 26.0 / 500.0, net_leg1 = 25.0;
// v29 (round 42): ROBOT_NET_TA=a, ROBOT_NET_TB=b -- affine delay model T = a + b * T_free instead of alpha * T_free
// (fitted on the round-40 measurement: a = 127, b = 1.49); unset keeps the v28 proportional model.
double net_ta = -1.0, net_tb = 1.0;
std::vector<std::vector<int>> br_Ks;                         // per bridge, per part: model credit (net_on)
std::vector<std::vector<double>> br_Tfree;                   // per bridge, per part: model delay T_free (ticks)
// v33 (round 48): ROBOT_RG_CUTS=1 (with ROBOT_NET) -- the cuts also come from the region graph of round 40 (regiongraph.py; the
// same decomposition as link_credit.cpp): every door whose removal disconnects the room graph, and every pair of doors whose joint
// removal does, whatever the door width and however far apart the two doors are, as long as at least two parts hold
// >= ROBOT_BRIDGE_FRAC of the free cells (the existing definition). The detector above only finds 1-cell doors and pairs of 1-cell
// doors within 12 cells; on 65 of 73 room maps it misses at least one such cut (354 in all, most with a 2-cell door), and those
// cuts get no credit (round 48 diagnosis: roomID_194 without the global cap jams rooms 11-12 behind the uncredited ring 16/22/30/32).
// A region-graph cut that splits the rooms exactly like an existing cut is a duplicate and is skipped. Credit: the same
// bandwidth-delay formula, with the measured effective bandwidth of each door (1-cell c1 = 26, 2-cell c2 = 32 per 500 ticks,
// as link_credit.cpp): K = ceil(alpha * T_free * sum(c) / 2). The new cuts are switched on at the first schedule, and only where
// the door MAC manages a single-lane link (the region graph exists only on room-type maps; the same gate as the global cap).
// Credit only: the door rule still sees the old single cuts (bridge_count()).
// v44 (round 67): ROBOT_RG_CUTS=4 -- only new single-door cuts whose bound cap/D is within 1/0.95 of the network's minimum.
// v43 (round 66): ROBOT_RG_CUTS=3 -- only the new single-door cuts (bridges of the room network, any width; e.g. a 2-cell door
// that is the only way into a part). Round 65: crediting such a bridge helped; round 49 (mode 2) failed mostly on ring cuts.
// v34 (round 49): ROBOT_RG_CUTS=2 -- only the network's bottleneck. Round 48 (mode 1, every missed cut) failed in development:
// on roomT_199 the extra ring cuts are not bottlenecks (load 0.62-0.77 of their bandwidth at the network's maximum throughput)
// and their bandwidth-delay credit, with the real delay about twice the model's there (round 44), throttled traffic that was not
// jamming. On roomID_194 the missed ring cut {16, 30} IS the bottleneck (load 1.0) and its credit helped. Mode 2 therefore keeps
// only the minimum cut(s) of the room network under the uniform demand of round 41 -- the cut(s) with the smallest bandwidth /
// crossing demand, cap_c / D_c, D_c = sum over room pairs (s, t) on different sides of w_s w_t (w = room size share) -- among all
// region-graph cuts with parts >= ROBOT_BRIDGE_FRAC, old ones included; a minimum cut that already has a credit adds nothing.
// This is the cut that the maximum-concurrent-flow bound of round 41 says limits the network; TCP likewise sizes the window
// for the bottleneck link only. Ties: equal within 1e-9 (relative). On 27 of 73 room maps the minimum cut has no credit.
int rg_cuts_on = 0; bool rg_pending = false; double net_c2 = 32.0 / 500.0;
// v35 (round 50, measurement only): ROBOT_RG_DRY=1 -- the region-graph cuts are counted but never deny a task (behaviour identical
// to the run without them). ROBOT_CUT_MEAS=1 -- for every cut and direction, the time-weighted mean in-flight count L (robots whose
// remaining route crosses into that side) and the number X of completed crossings (an in-flight entry that disappears while the robot
// stands in that side); Little's law gives the measured delay T = L * elapsed / X ("assignment to crossing", the interval the
// credit counts), to compare with the model alpha * T_free. Printed cumulatively to stderr every 500 ticks ([cutmeas]).
int rg_dry = 0, rg_first = -1, cm_on = 0, cm_last_t = -1, cm_t0 = -1, cm_last_print = -1;
std::vector<std::vector<double>> cm_lsum; std::vector<std::vector<long long>> cm_x;
// v36 (round 51): ROBOT_RG_BBR=1 (with ROBOT_RG_CUTS=1) -- the region-graph cuts get a BBR-style in-flight cap instead of the
// model credit. Round 50 measured that on these cuts the real delay (assignment -> crossing, Little) is 2.2-2.9 x the model's
// alpha * T_free (1.5 x on the old cuts), so the model credit throttles cuts that are not jammed; but where a cut has collapsed
// (roomZ3, roomGB: a third of the usual crossings) a cap restores it. BBR (Cardwell et al. 2016) measures instead of assuming:
// cap = gain * BtlBw * RTprop, BtlBw = the highest delivery rate seen so far, RTprop = the lowest delay seen so far, both per
// cut and direction over windows of ROBOT_RG_BBR_WIN ticks (500, the unit used throughout); gain = 2 (BBR's cwnd_gain).
// Delivery rate of a window = completed crossings / window length; delay = time-weighted in-flight / crossings (Little).
// No cap until the first window with a crossing. On a cut that is not jammed, in-flight ~ rate x delay < cap; when a queue
// builds, the delay rises and the delivery rate falls, and the cap (fixed by the best values seen) stops the pile-up.
int rg_bbr = 0, bb_win = 500, bb_t0 = -1; double bb_gain = 2.0;
std::vector<std::vector<double>> bb_wl, bb_maxr, bb_mind; std::vector<std::vector<long long>> bb_wx; std::vector<std::vector<int>> bb_cap;
long long bb_denied = 0;
struct RgCut { std::vector<int> side; int nparts; std::vector<int> cells; std::vector<int> K; std::vector<double> T; std::vector<int> doors; double cap = 0; };
// v45 (round 70): ROBOT_RG_CUTS=5 -- the bottleneck bridges of mode 4, but each one's credit is enforced only while its door is losing
// capacity: every 500 ticks J = crossings / (ticks with a robot within 3 cells of the door) * 500 / nominal bandwidth (c1 26, c2 32
// per 500 ticks); two windows in a row with J < 0.9 switch the credit on, two with J >= 1.0 switch it off. Windows with fewer than
// 50 queue ticks leave the state unchanged. Round 68/69: the credit helped where the bridge was losing capacity (roomZ3, J 0.81) and
// hurt where it was not (roomFE, J 1.19).
std::vector<char> g5_on; std::vector<int> g5_lo, g5_hi, g5_cross, g5_last; std::vector<double> g5_q, g5_cap; std::vector<std::vector<char>> g5_apron; int g5_t0 = -1, g5_tl = -1;
std::vector<std::vector<signed char>> g5_side;
std::vector<RgCut> rg_new;
// v27: delay-based AIMD for the two-door cuts (ROBOT_CUT2_AIMD=1). Every c2_win ticks, the robot-ticks spent within
// 3 cells of the two doors per crossing (Little's law) is compared with c2_target: above it, K <- max(kmin, beta K);
// otherwise, if the credit denied a task in the window, K <- min(kmax, K + inc).
int c2_aimd = 0, c2_win = 250, c2_target = 250, c2_kmin = 8, c2_kmax = 48, c2_inc = 2, c2_t0 = -1, c2_samples = 0; double c2_beta = 0.5;
std::vector<double> c2_K; std::vector<std::vector<char>> c2_zone; std::vector<std::vector<signed char>> c2_last;
std::vector<long long> c2_qsum; std::vector<int> c2_x, c2_deny;
static int c2_env(const char* k, int d) { const char* e = std::getenv(k); return e ? std::atoi(e) : d; }
void c2_init(SharedEnvironment* env) {
    c2_aimd = c2_env("ROBOT_CUT2_AIMD", 0); c2_win = c2_env("ROBOT_CUT2_WIN", 250); c2_target = c2_env("ROBOT_CUT2_TARGET", 250);
    c2_kmin = c2_env("ROBOT_CUT2_KMIN", 8); c2_kmax = c2_env("ROBOT_CUT2_KMAX", 48); c2_inc = c2_env("ROBOT_CUT2_INC", 2);
    c2_beta = std::getenv("ROBOT_CUT2_BETA") ? std::stod(std::getenv("ROBOT_CUT2_BETA")) : 0.5;
    c2_K.clear(); c2_zone.clear(); c2_last.clear(); c2_qsum.clear(); c2_x.clear(); c2_deny.clear(); c2_samples = 0; c2_t0 = env->system_timestep;
    if (!c2_aimd || br_K2 <= 0 || int(br_side.size()) <= br_n1) return;
    const int nb = int(br_side.size()) - br_n1, n = int(env->map.size()), C = env->cols;
    c2_K.assign(nb, double(br_K2)); c2_zone.assign(nb, std::vector<char>(n, 0)); c2_last.assign(nb, std::vector<signed char>(env->num_of_agents, -1));
    c2_qsum.assign(nb, 0); c2_x.assign(nb, 0); c2_deny.assign(nb, 0);
    for (int j = 0; j < nb; ++j) for (int v = 0; v < n; ++v) if (!env->map[v])
        for (int c : br_cells[br_n1 + j]) if (std::abs(v / C - c / C) + std::abs(v % C - c % C) <= 3) { c2_zone[j][v] = 1; break; }
}
void c2_step(SharedEnvironment* env) {
    if (c2_K.empty()) return;
    const int nb = int(c2_K.size()), t = env->system_timestep;
    for (int j = 0; j < nb; ++j) { const int b = br_n1 + j; long long q = 0;
        for (int i = 0; i < int(env->system_states.size()) && i < int(c2_last[j].size()); ++i) { const int loc = env->system_states[i].location; if (loc < 0) continue;
            q += c2_zone[j][loc]; const int s = br_side[b][loc];
            if (s >= 0) { if (c2_last[j][i] >= 0 && c2_last[j][i] != s) ++c2_x[j]; c2_last[j][i] = (signed char)s; } }
        c2_qsum[j] += q; }
    ++c2_samples;
    if (t - c2_t0 < c2_win) return;
    const double dt = t - c2_t0;
    for (int j = 0; j < nb; ++j) { const int b = br_n1 + j; const double qavg = double(c2_qsum[j]) / std::max(1, c2_samples);
        const double delay = c2_x[j] > 0 ? qavg * dt / c2_x[j] : (qavg >= 1.0 ? 1e9 : 0.0); const double K0 = c2_K[j];
        if (delay > c2_target) c2_K[j] = std::max(double(c2_kmin), c2_beta * c2_K[j]);
        else if (c2_deny[j] > 0) c2_K[j] = std::min(double(c2_kmax), c2_K[j] + c2_inc);
        br_Kb[b] = int(c2_K[j] + 1e-9);
        if (br_trace) std::fprintf(stderr, "[aimd] t=%d cut2 %d q=%.1f x=%d delay=%.0f deny=%d K %.1f -> %.1f\n", t, j, qavg, c2_x[j], delay > 1e8 ? -1.0 : delay, c2_deny[j], K0, c2_K[j]);
        c2_qsum[j] = 0; c2_x[j] = 0; c2_deny[j] = 0; }
    c2_t0 = t; c2_samples = 0;
}
void br_route(int start, const std::vector<int>& L, int from, std::vector<std::pair<int,int>>& out) {
    out.clear();
    for (int b = 0; b < int(br_side.size()); ++b) {
        int prev = start >= 0 ? br_side[b][start] : -1;
        for (int i = std::max(0, from); i < int(L.size()); ++i) {
            const int s = br_side[b][L[i]]; if (s < 0) continue;
            if (prev >= 0 && s != prev && std::find(out.begin(), out.end(), std::make_pair(b, s)) == out.end()) out.push_back({b, s});
            prev = s;
        }
    }
}
// free-flow delay (ticks) to the cut cells, averaged over the cells of every other side, plus leg 1 (as in the ROBOT_NET block)
std::vector<double> cut_tfree(SharedEnvironment* env, const std::vector<int>& cells, const std::vector<int>& side, int nparts) {
    const int n = int(env->map.size()), C = env->cols; const int DRo[4] = {1, C, -1, -C};
    std::vector<int> dist(4 * n, INT_MAX); using Q = std::pair<int,int>; std::priority_queue<Q, std::vector<Q>, std::greater<Q>> pq;
    for (int c : cells) for (int o = 0; o < 4; ++o) { dist[4 * c + o] = 0; pq.push({0, 4 * c + o}); }
    while (!pq.empty()) { auto [d, st] = pq.top(); pq.pop(); if (d != dist[st]) continue; const int v = st / 4, o = st % 4;
        for (int no : {(o + 1) % 4, (o + 3) % 4}) if (d + 3 < dist[4 * v + no]) { dist[4 * v + no] = d + 3; pq.push({d + 3, 4 * v + no}); }
        const int p = v - DRo[o]; const bool ok = p >= 0 && p < n && !env->map[p] && (o == 1 || o == 3 || p / C == v / C);
        if (ok && d + 3 < dist[4 * p + o]) { dist[4 * p + o] = d + 3; pq.push({d + 3, 4 * p + o}); } }
    std::vector<double> sum(nparts, 0.0); std::vector<long long> cnt(nparts, 0);
    for (int v = 0; v < n; ++v) { const int sv = side[v]; if (sv < 0) continue;
        int m = INT_MAX; for (int o = 0; o < 4; ++o) m = std::min(m, dist[4 * v + o]); if (m == INT_MAX) continue;
        for (int s2 = 0; s2 < nparts; ++s2) if (s2 != sv) { sum[s2] += m; ++cnt[s2]; } }
    std::vector<double> ts(nparts, 0.0); for (int s2 = 0; s2 < nparts; ++s2) ts[s2] = net_leg1 + (cnt[s2] ? sum[s2] / cnt[s2] : 0.0);
    return ts;
}
void rg_detect(SharedEnvironment* env);
void br_detect(SharedEnvironment* env) {
    const int n = int(env->map.size()), C = env->cols; br_cols = C;
    auto nbrs = [&](int v, int* o) { int k = 0;
        if (v % C != C - 1 && !env->map[v + 1]) o[k++] = v + 1; if (v % C != 0 && !env->map[v - 1]) o[k++] = v - 1;
        if (v + C < n && !env->map[v + C]) o[k++] = v + C; if (v - C >= 0 && !env->map[v - C]) o[k++] = v - C; return k; };
    int N = 0; for (int v = 0; v < n; ++v) N += !env->map[v];
    std::vector<int> disc(n, -1), low(n, 0), sub(n, 1), itr(n, 0), par(n, -1), comp(n, 0);
    struct Sep { int v, size, comp; }; std::vector<Sep> seps; int timer = 0;
    for (int root = 0; root < n; ++root) {
        if (env->map[root] || disc[root] >= 0) continue;
        std::vector<int> st{root}, seen{root}; disc[root] = low[root] = timer++; const size_t s0 = seps.size();
        while (!st.empty()) {
            const int v = st.back(); int nb[4]; const int k = nbrs(v, nb);
            if (itr[v] < k) { const int w = nb[itr[v]++];
                if (disc[w] < 0) { disc[w] = low[w] = timer++; par[w] = v; st.push_back(w); seen.push_back(w); }
                else if (w != par[v]) low[v] = std::min(low[v], disc[w]); }
            else { st.pop_back(); const int p = par[v];
                if (p >= 0) { low[p] = std::min(low[p], low[v]); sub[p] += sub[v]; if (low[v] >= disc[p]) seps.push_back({p, sub[v], 0}); } }
        }
        for (size_t i = s0; i < seps.size(); ++i) seps[i].comp = sub[root];
    }
    std::unordered_map<int, std::vector<int>> parts; std::unordered_map<int,int> compsz;
    for (const auto& s : seps) { parts[s.v].push_back(s.size); compsz[s.v] = s.comp; }
    std::vector<char> cut(n, 0); const double thr = br_frac * N;
    for (auto& kv : parts) {
        std::vector<int> ps = kv.second; long long sum = 0; for (int x : ps) sum += x;
        if (par[kv.first] >= 0) ps.push_back(int(compsz[kv.first] - 1 - sum));
        int big = 0; for (int x : ps) big += x >= thr;
        if (big >= 2) cut[kv.first] = 1;
    }
    br_side.clear(); br_nparts.clear(); br_cells.clear();
    std::vector<char> done(n, 0);
    for (int v0 = 0; v0 < n && br_side.size() < 16; ++v0) {
        if (!cut[v0] || done[v0]) continue;
        std::vector<int> chain{v0}; done[v0] = 1;
        for (size_t q = 0; q < chain.size(); ++q) { int nb[4]; const int k = nbrs(chain[q], nb); for (int i = 0; i < k; ++i) if (cut[nb[i]] && !done[nb[i]]) { done[nb[i]] = 1; chain.push_back(nb[i]); } }
        std::vector<int> lab(n, -2); for (int c : chain) lab[c] = -1;
        std::vector<int> sizes; 
        for (int s = 0; s < n; ++s) {
            if (env->map[s] || lab[s] != -2) continue;
            const int id = int(sizes.size()); std::vector<int> q{s}; lab[s] = id;
            for (size_t h = 0; h < q.size(); ++h) { int nb[4]; const int k = nbrs(q[h], nb); for (int i = 0; i < k; ++i) if (lab[nb[i]] == -2) { lab[nb[i]] = id; q.push_back(nb[i]); } }
            sizes.push_back(int(q.size()));
        }
        std::vector<int> remap(sizes.size(), -1); int k = 0;
        for (size_t i = 0; i < sizes.size(); ++i) if (sizes[i] >= thr) remap[i] = k++;
        if (k < 2) continue;
        std::vector<int> side(n, -1); for (int v = 0; v < n; ++v) if (lab[v] >= 0) side[v] = remap[lab[v]];
        br_side.push_back(std::move(side)); br_nparts.push_back(k); br_cells.push_back(chain);
        if (br_trace) { std::fprintf(stderr, "[bridge] %zu cells:", br_side.size() - 1); for (int c : chain) std::fprintf(stderr, " (%d,%d)", c / C, c % C);
            std::fprintf(stderr, " parts:"); for (size_t i = 0; i < sizes.size(); ++i) if (remap[i] >= 0) std::fprintf(stderr, " %d", sizes[i]); std::fprintf(stderr, "\n"); }
    }
    br_n1 = int(br_side.size());
    if (br_K2 > 0) {   // v26: two-door cuts
        auto passage = [&](int v) { if (env->map[v] || cut[v]) return false; int nb[4]; const int k = nbrs(v, nb); return k == 2 && nb[0] + nb[1] == 2 * v; };
        auto open_end = [&](int e, int pv) { const int er = e / C, ec = e % C, R = n / C;
            for (int r0 = er - 2; r0 <= er; ++r0) for (int c0 = ec - 2; c0 <= ec; ++c0) { bool ok = r0 >= 0 && c0 >= 0 && r0 + 2 < R && c0 + 2 < C;
                for (int dr = 0; ok && dr < 3; ++dr) for (int dc = 0; ok && dc < 3; ++dc) { const int u = (r0 + dr) * C + c0 + dc; if (env->map[u] || u == pv) ok = false; }
                if (ok) return true; }
            return false; };
        std::vector<int> cand;
        for (int v = 0; v < n; ++v) if (passage(v)) { int nb[4]; nbrs(v, nb); if (open_end(nb[0], v) && open_end(nb[1], v)) cand.push_back(v); }
        std::vector<std::vector<long long>> sigs;
        if (cand.size() <= 400) for (size_t i = 0; i < cand.size() && br_side.size() < 16; ++i) for (size_t j = i + 1; j < cand.size() && br_side.size() < 16; ++j) {
            const int u = cand[i], w = cand[j]; if (std::abs(u / C - w / C) + std::abs(u % C - w % C) > 12) continue;
            std::vector<int> lab(n, -2); lab[u] = lab[w] = -1; std::vector<int> sizes, firsts;
            for (int s0 = 0; s0 < n; ++s0) { if (env->map[s0] || lab[s0] != -2) continue;
                const int id = int(sizes.size()); std::vector<int> q{s0}; lab[s0] = id; firsts.push_back(s0);
                for (size_t h = 0; h < q.size(); ++h) { int nb[4]; const int k = nbrs(q[h], nb); for (int t = 0; t < k; ++t) if (lab[nb[t]] == -2) { lab[nb[t]] = id; q.push_back(nb[t]); } }
                sizes.push_back(int(q.size())); }
            std::vector<int> remap(sizes.size(), -1); int k = 0; std::vector<long long> sig;
            for (size_t t = 0; t < sizes.size(); ++t) if (sizes[t] >= thr) { remap[t] = k++; sig.push_back(c2_sigfix ? (long long)firsts[t] * (n + 1) + sizes[t] : sizes[t]); }
            if (k < 2) continue;
            std::sort(sig.begin(), sig.end()); bool dup = false; for (auto& g : sigs) if (g == sig) dup = true; if (dup) continue; sigs.push_back(sig);
            std::vector<int> side(n, -1); for (int v = 0; v < n; ++v) if (lab[v] >= 0) side[v] = remap[lab[v]];
            br_side.push_back(std::move(side)); br_nparts.push_back(k); br_cells.push_back({u, w});
            if (br_trace) { std::fprintf(stderr, "[cut2] (%d,%d) (%d,%d) parts:", u / C, u % C, w / C, w % C); for (long long x : sig) std::fprintf(stderr, " %lld", c2_sigfix ? x % (n + 1) : x); std::fprintf(stderr, "\n"); }
        }
    }
    br_Kb.assign(br_side.size(), br_K); for (size_t b = br_n1; b < br_side.size(); ++b) br_Kb[b] = br_K2;
    br_Ks.clear(); br_Tfree.clear();
    if (net_on) {
        const int R = n / C; const int DRo[4] = {1, C, -1, -C};
        for (size_t b = 0; b < br_side.size(); ++b) {
            // reverse Dijkstra from the cut cells over (cell, heading); arrival heading is free
            std::vector<int> dist(4 * n, INT_MAX); using Q = std::pair<int,int>;
            std::priority_queue<Q, std::vector<Q>, std::greater<Q>> pq;
            for (int c : br_cells[b]) for (int o = 0; o < 4; ++o) { dist[4 * c + o] = 0; pq.push({0, 4 * c + o}); }
            while (!pq.empty()) { auto [d, st] = pq.top(); pq.pop(); if (d != dist[st]) continue;
                const int v = st / 4, o = st % 4;
                for (int no : {(o + 1) % 4, (o + 3) % 4}) if (d + 3 < dist[4 * v + no]) { dist[4 * v + no] = d + 3; pq.push({d + 3, 4 * v + no}); }
                const int p = v - DRo[o];      // moving forward with heading o from p arrives at v
                const bool ok = p >= 0 && p < n && !env->map[p] && (o == 1 || o == 3 || p / C == v / C);
                if (ok && d + 3 < dist[4 * p + o]) { dist[4 * p + o] = d + 3; pq.push({d + 3, 4 * p + o}); } }
            (void)R;
            std::vector<double> sum(br_nparts[b], 0.0); std::vector<long long> cnt(br_nparts[b], 0);
            for (int v = 0; v < n; ++v) { const int sv = br_side[b][v]; if (sv < 0) continue;
                int m = INT_MAX; for (int o = 0; o < 4; ++o) m = std::min(m, dist[4 * v + o]); if (m == INT_MAX) continue;
                for (int s2 = 0; s2 < br_nparts[b]; ++s2) if (s2 != sv) { sum[s2] += m; ++cnt[s2]; } }   // a pickup at v feeds every other side
            const int ndoors = int(b) < br_n1 ? 1 : 2;
            std::vector<int> ks(br_nparts[b], 1); std::vector<double> ts(br_nparts[b], 0.0);
            for (int s2 = 0; s2 < br_nparts[b]; ++s2) { ts[s2] = net_leg1 + (cnt[s2] ? sum[s2] / cnt[s2] : 0.0);
                const double teff = net_ta >= 0 ? net_ta + net_tb * ts[s2] : net_alpha * ts[s2];
                ks[s2] = std::max(1, int(std::ceil(teff * ndoors * net_c1 / 2.0))); }
            br_Ks.push_back(ks); br_Tfree.push_back(ts);
            if (br_trace) { std::fprintf(stderr, "[net] cut %zu (%s) doors %d:", b, int(b) < br_n1 ? "bridge" : "pair", ndoors);
                for (int s2 = 0; s2 < br_nparts[b]; ++s2) std::fprintf(stderr, " side%d T_free=%.0f K=%d", s2, ts[s2], ks[s2]); std::fprintf(stderr, "\n"); }
        }
    }
    br_load.assign(br_side.size(), {}); for (size_t b = 0; b < br_side.size(); ++b) br_load[b].assign(br_nparts[b], 0);
    br_counted.assign(env->num_of_agents, {});
    rg_new.clear(); rg_pending = false;
    if (rg_cuts_on && net_on) rg_detect(env);
    // v37 (round 52): door zone = free cells within Manhattan distance 1 of a cut's door cells (bridge chains and door pairs found
    // above). The guide-path search charges a turn made inside it (ROBOT_DOOR_TURN), so robots line up with the door before it.
    dz_mask.assign(n, 0);
    for (const auto& ch : br_cells) for (int c : ch) { const int cy = c / C, cx = c % C;
        for (int dy = -1; dy <= 1; ++dy) for (int dx = -1; dx <= 1; ++dx) { if (std::abs(dy) + std::abs(dx) > 1) continue;
            const int y = cy + dy, x = cx + dx; if (y < 0 || y >= n / C || x < 0 || x >= C) continue; if (!env->map[y * C + x]) dz_mask[y * C + x] = 1; } }
    if (br_trace) { int k = 0; for (char z : dz_mask) k += z; std::fprintf(stderr, "[doorzone] %d cells in %zu cuts\n", k, br_cells.size()); }
}
// v33: region-graph cuts (see the comment at rg_cuts_on)
void rg_detect(SharedEnvironment* env) {
    const int n = int(env->map.size()), C = env->cols, H = n / C;
    auto isfree = [&](int r, int c) { return r >= 0 && r < H && c >= 0 && c < C && !env->map[r * C + c]; };
    std::vector<int> hr(n, 0), vr(n, 0);
    for (int r = 0; r < H; ++r) for (int c = 0; c < C; ) { if (!isfree(r, c)) { ++c; continue; } int e = c; while (e < C && isfree(r, e)) ++e; for (int k = c; k < e; ++k) hr[r * C + k] = e - c; c = e; }
    for (int c = 0; c < C; ++c) for (int r = 0; r < H; ) { if (!isfree(r, c)) { ++r; continue; } int e = r; while (e < H && isfree(e, c)) ++e; for (int k = r; k < e; ++k) vr[k * C + c] = e - r; r = e; }
    std::vector<char> narrow(n, 0); for (int v = 0; v < n; ++v) if (!env->map[v]) narrow[v] = hr[v] <= 2 || vr[v] <= 2;
    auto nb = [&](int v, int k) -> int { const int r = v / C, c = v % C;
        if (k == 0) return r > 0 ? v - C : -1; if (k == 1) return r + 1 < H ? v + C : -1; if (k == 2) return c > 0 ? v - 1 : -1; return c + 1 < C ? v + 1 : -1; };
    std::vector<int> room_of(n, -1); int R = 0;
    for (int s0 = 0; s0 < n; ++s0) { if (env->map[s0] || narrow[s0] || room_of[s0] >= 0) continue;
        std::vector<int> q{s0}; room_of[s0] = R;
        for (size_t h = 0; h < q.size(); ++h) for (int k = 0; k < 4; ++k) { const int w = nb(q[h], k); if (w >= 0 && !env->map[w] && !narrow[w] && room_of[w] < 0) { room_of[w] = R; q.push_back(w); } }
        ++R; }
    struct D { std::vector<int> cells; int a, b; double c; }; std::vector<D> doors;
    std::vector<char> seen(n, 0);
    for (int s0 = 0; s0 < n; ++s0) { if (!narrow[s0] || seen[s0]) continue;
        std::vector<int> g{s0}; seen[s0] = 1;
        for (size_t h = 0; h < g.size(); ++h) for (int k = 0; k < 4; ++k) { const int w = nb(g[h], k); if (w >= 0 && narrow[w] && !seen[w]) { seen[w] = 1; g.push_back(w); } }
        std::vector<int> touch;
        for (int v : g) for (int k = 0; k < 4; ++k) { const int w = nb(v, k); if (w >= 0 && room_of[w] >= 0 && std::find(touch.begin(), touch.end(), room_of[w]) == touch.end()) touch.push_back(room_of[w]); }
        if (touch.size() == 1) { for (int v : g) room_of[v] = touch[0]; continue; }    // niche -> part of the room
        if (touch.size() != 2) continue;
        bool up = false, down = false; int y0 = INT_MAX, y1 = -1, x0 = INT_MAX, x1 = -1;
        for (int v : g) { const int y = v / C, x = v % C; y0 = std::min(y0, y); y1 = std::max(y1, y); x0 = std::min(x0, x); x1 = std::max(x1, x);
            if (y > 0 && room_of[v - C] >= 0) up = true; if (y + 1 < H && room_of[v + C] >= 0) down = true; }
        const int width = (up && down) ? (x1 - x0 + 1) : (y1 - y0 + 1);
        doors.push_back({g, std::min(touch[0], touch[1]), std::max(touch[0], touch[1]), width <= 1 ? net_c1 : net_c2}); }
    const int ND = int(doors.size()); if (R < 2 || ND == 0) return;
    auto connected = [&](int x, int y) {      // room graph without doors x, y (y may be -1)
        std::vector<int> par(R); for (int r = 0; r < R; ++r) par[r] = r;
        std::function<int(int)> f = [&](int u) { while (par[u] != u) u = par[u] = par[par[u]]; return u; };
        int comps = R; for (int i = 0; i < ND; ++i) { if (i == x || i == y) continue; const int u = f(doors[i].a), w = f(doors[i].b); if (u != w) { par[u] = w; --comps; } }
        return comps == 1; };
    // room-level signature of a cut: for each part, the sorted rooms whose cells lie in it (a door cell is never inside a room)
    std::vector<int> rep(R, -1); for (int v = 0; v < n; ++v) if (room_of[v] >= 0 && rep[room_of[v]] < 0 && !narrow[v]) rep[room_of[v]] = v;
    // v34: each room goes to the part holding most of its cells (an old cut's cells may lie inside a room; round 48 counted
    // room200's door 6 twice because a room's first cell was one of them)
    auto room_sig = [&](const std::vector<int>& side, int np) { std::vector<std::vector<int>> g(np); std::vector<std::vector<int>> cnt(R, std::vector<int>(np, 0));
        for (int v = 0; v < n; ++v) if (room_of[v] >= 0 && side[v] >= 0) ++cnt[room_of[v]][side[v]];
        for (int r = 0; r < R; ++r) { int b = -1, bc = 0; for (int q = 0; q < np; ++q) if (cnt[r][q] > bc) { bc = cnt[r][q]; b = q; } if (b >= 0) g[b].push_back(r); }
        std::sort(g.begin(), g.end()); return g; };
    std::vector<std::vector<std::vector<int>>> sigs; for (size_t b = 0; b < br_side.size(); ++b) sigs.push_back(room_sig(br_side[b], br_nparts[b]));
    int Nfree = 0; for (int v = 0; v < n; ++v) Nfree += !env->map[v]; const double thr = br_frac * Nfree;
    std::vector<std::vector<int>> cand;
    for (int i = 0; i < ND; ++i) if (!connected(i, -1)) cand.push_back({i});
    std::vector<char> isbr(ND, 0); for (auto& c : cand) isbr[c[0]] = 1;
    if (ND <= 120) for (int i = 0; i < ND; ++i) for (int j = i + 1; j < ND; ++j) if (!isbr[i] && !isbr[j] && !connected(i, j)) cand.push_back({i, j});
    std::vector<double> rsize(R, 0.0); double Atot = 0; for (int v = 0; v < n; ++v) if (room_of[v] >= 0) { rsize[room_of[v]] += 1; Atot += 1; }
    double best_ratio = 1e300; std::vector<double> new_ratio;
    // uniform demand crossing the cut: share of (origin room, destination room) pairs, s != t, whose rooms lie in different
    // connected parts once the cut's doors are removed (lab = part id of every cell; small parts count as parts too)
    auto demand = [&](const std::vector<int>& lab) {
        std::map<int,double> m; double tot = 0; for (int r = 0; r < R; ++r) { if (rep[r] < 0) continue; const double x = rsize[r] / Atot; m[lab[rep[r]]] += x; tot += x; }
        double same = 0; for (auto& kv : m) same += kv.second * kv.second;
        return tot * tot - same; };
    for (const auto& cd : cand) {
        std::vector<char> rm(n, 0); std::vector<int> cells; double cap = 0;
        for (int d : cd) { cap += doors[d].c; for (int v : doors[d].cells) { rm[v] = 1; cells.push_back(v); } }
        std::vector<int> lab(n, -2); std::vector<int> sizes;
        for (int s0 = 0; s0 < n; ++s0) { if (env->map[s0] || rm[s0] || lab[s0] != -2) continue;
            const int id = int(sizes.size()); std::vector<int> q{s0}; lab[s0] = id;
            for (size_t h = 0; h < q.size(); ++h) for (int k = 0; k < 4; ++k) { const int w = nb(q[h], k); if (w >= 0 && !env->map[w] && !rm[w] && lab[w] == -2) { lab[w] = id; q.push_back(w); } }
            sizes.push_back(int(q.size())); }
        std::vector<int> remap(sizes.size(), -1); int k = 0; for (size_t t = 0; t < sizes.size(); ++t) if (sizes[t] >= thr) remap[t] = k++;
        if (k < 2) continue;
        std::vector<int> side(n, -1); for (int v = 0; v < n; ++v) if (lab[v] >= 0) side[v] = remap[lab[v]];
        { const double D = demand(lab); if (D > 0) best_ratio = std::min(best_ratio, cap / D); }
        auto sg = room_sig(side, k); bool dup = false; for (auto& g : sigs) if (g == sg) dup = true; if (dup) continue; sigs.push_back(sg);
        { const double D = demand(lab); new_ratio.push_back(D > 0 ? cap / D : 1e300); }
        RgCut rc; rc.T = cut_tfree(env, cells, side, k); rc.K.assign(k, 1);
        for (int s2 = 0; s2 < k; ++s2) { const double teff = net_ta >= 0 ? net_ta + net_tb * rc.T[s2] : net_alpha * rc.T[s2];
            rc.K[s2] = std::max(1, int(std::ceil(teff * cap / 2.0))); }
        rc.side = std::move(side); rc.nparts = k; rc.cells = cells; rc.doors = cd; rc.cap = cap;
        if (br_trace) { std::fprintf(stderr, "[rgcut] doors"); for (int d : cd) std::fprintf(stderr, " %d(w%s)", d, doors[d].c > net_c1 ? "2" : "1");
            std::fprintf(stderr, " parts:"); for (size_t t = 0; t < sizes.size(); ++t) if (remap[t] >= 0) std::fprintf(stderr, " %d", sizes[t]);
            std::fprintf(stderr, " K:"); for (int s2 = 0; s2 < k; ++s2) std::fprintf(stderr, " %d", rc.K[s2]); std::fprintf(stderr, "\n"); }
        rg_new.push_back(std::move(rc));
    }
    if (rg_cuts_on == 2) {      // v34: keep only the network's minimum cut(s)
        std::vector<RgCut> keep;
        for (size_t i = 0; i < rg_new.size(); ++i) if (new_ratio[i] <= best_ratio * (1.0 + 1e-9)) keep.push_back(std::move(rg_new[i]));
        if (br_trace) std::fprintf(stderr, "[rgcut] mode 2: minimum cap/D = %.5f per tick; %zu of %zu new cuts are minimum cuts\n", best_ratio, keep.size(), rg_new.size());
        rg_new = std::move(keep);
    }
    if (rg_cuts_on == 4 || rg_cuts_on == 5) {      // v44 (round 67): new single-door cuts that are (nearly) the network bottleneck:
        // rho_C = lambda* / (cap_C / D_C) >= 0.95, lambda* = the maximum concurrent flow solved in full (AdmitAuto::lambda_star;
        // the smallest cap / D over 1- and 2-door cuts is only an upper bound: on roomHE_189 it is 0.479 against lambda* 0.319). Round 66: crediting bridges that are not
        // the bottleneck did nothing or hurt (roomHE_189 -4.5 %); the bottleneck bridges gained (roomZ3 +20 %, roomGB +9 %).
        std::vector<RgCut> keep;
        bool any1 = false; for (auto& rc : rg_new) any1 = any1 || rc.doors.size() == 1;
        const double lam = (any1 && R <= 400) ? AdmitAuto::lambda_star(env) : 0.0;   // exact max concurrent flow (admit_auto.cpp)
        if (br_trace) std::fprintf(stderr, "[rgcut] mode 4: lambda* = %.5f per tick (min cut bound %.5f)\n", lam, best_ratio);
        for (size_t i = 0; i < rg_new.size(); ++i) if (lam > 0 && rg_new[i].doors.size() == 1 && lam / new_ratio[i] >= 0.95) keep.push_back(std::move(rg_new[i]));
        if (br_trace) std::fprintf(stderr, "[rgcut] mode 4: min cap/D = %.5f per tick; %zu of %zu new cuts are bottleneck bridges\n", best_ratio, keep.size(), rg_new.size());
        rg_new = std::move(keep);
    }
    if (rg_cuts_on == 3) {      // v43 (round 66): keep only new single-door cuts (bridges of the room network, any door width)
        std::vector<RgCut> keep;
        for (auto& rc : rg_new) if (rc.doors.size() == 1) keep.push_back(std::move(rc));
        if (br_trace) std::fprintf(stderr, "[rgcut] mode 3: %zu of %zu new cuts are single-door cuts (bridges)\n", keep.size(), rg_new.size());
        rg_new = std::move(keep);
    }
    rg_pending = !rg_new.empty();
}
// v33: switch the region-graph cuts on (first schedule, room-type maps only); begin_schedule recounts the loads right after
void rg_activate() {
    rg_pending = false;
    if (DefaultPlanner::NetMac::link_count() == 0) { if (br_trace) std::fprintf(stderr, "[rgcut] gate closed (no single-lane link): %zu cuts not used\n", rg_new.size()); rg_new.clear(); return; }
    rg_first = int(br_side.size());
    if (rg_cuts_on == 5) { const int n = int(rg_new.empty() ? 0 : rg_new[0].side.size());
        for (auto& rc : rg_new) { std::vector<char> m(n, 0); std::vector<char> isd(n, 0); for (int v : rc.cells) isd[v] = 1;
            for (int v : rc.cells) { const int r = v / cols, c = v % cols; for (int dr = -3; dr <= 3; ++dr) for (int dc = -3; dc <= 3; ++dc) { if (std::abs(dr) + std::abs(dc) > 3) continue;
                const int rr = r + dr, cc = c + dc; if (rr < 0 || cc < 0 || cc >= cols || rr * cols + cc >= n) continue; const int w = rr * cols + cc; if (!isd[w]) m[w] = 1; } }
            g5_apron.push_back(std::move(m)); g5_cap.push_back(rc.cap); }
        const size_t nj = rg_new.size(); g5_on.assign(nj, 0); g5_lo.assign(nj, 0); g5_hi.assign(nj, 0); g5_cross.assign(nj, 0); g5_q.assign(nj, 0.0); }
    for (auto& rc : rg_new) { br_side.push_back(std::move(rc.side)); br_nparts.push_back(rc.nparts); br_cells.push_back(rc.cells);
        br_Kb.push_back(br_K2); br_Ks.push_back(rc.K); br_Tfree.push_back(rc.T); br_load.push_back(std::vector<int>(rc.nparts, 0)); }
    if (br_trace) std::fprintf(stderr, "[rgcut] %zu region-graph cuts switched on (total cuts %zu)\n", rg_new.size(), br_side.size());
    rg_new.clear();
}
void br_uncount(int agent) { if (agent < 0 || agent >= int(br_counted.size())) return; for (auto& bs : br_counted[agent]) --br_load[bs.first][bs.second]; br_counted[agent].clear(); }
void br_count(int agent) { for (auto& bs : br_tmp) ++br_load[bs.first][bs.second]; br_counted[agent] = br_tmp; }
bool multicut() { return policy == "multicut" || policy == "multicut_adaptive"; }
int lside(const Line& L, int loc) { return (L.axis == 0 ? loc % cols : loc / cols) >= L.cut; }
int lalong(const Line& L, int loc) { return L.axis == 0 ? loc / cols : loc % cols; }
int pick_door(int li, int a, int g) {      // the door with the smallest along-line detour between a and g
    if (mc_scope == 0 || li >= int(door_center.size()) || door_center[li].size() <= 1) return 0;
    const Line& L = lines[li]; const double xa = lalong(L, a), xg = lalong(L, g); int best = 0; double bd = 1e18;
    for (size_t d = 0; d < door_center[li].size(); ++d) { const double c = door_center[li][d], v = std::abs(xa - c) + std::abs(xg - c); if (v < bd) { bd = v; best = int(d); } }
    return best;
}
void mc_crossings(int agent, int task, SharedEnvironment* env, std::vector<std::pair<int,int>>& out) {
    out.clear(); const auto& t = env->task_pool.at(task); if (t.locations.empty()) return;
    int a = env->system_states.at(agent).location;
    const int legs = mc_legs_all ? int(t.locations.size()) : 1;
    for (int k = 0; k < legs; ++k) {           // leg k goes from a to the k-th errand
        const int g = t.locations[k];
        for (int i = 0; i < int(lines.size()); ++i) if (lside(lines[i], a) != lside(lines[i], g)) out.push_back({i, pick_door(i, a, g) * 2 + lside(lines[i], g)});
        a = g;
    }
}
std::vector<std::pair<int,int>> mc_tmp;
void mc_count(const std::pair<int,int>& pl, int d) { lines[pl.first].inflight += d; lines[pl.first].infl_dir[pl.second & 1] += d; if (pl.first < int(zinfl.size())) zinfl[pl.first][pl.second] += d; }
bool mc_full(const std::pair<int,int>& pl) {
    const Line& L = lines[pl.first];
    if (!L.active) return false;
    if (mc_hard) return true;
    if (mc_credit > 0) return int(std::floor(mc_credit * zcap[pl.first][pl.second])) - zocc[pl.first][pl.second] - zinfl[pl.first][pl.second] <= 0;
    const int used = mc_dir ? L.infl_dir[pl.second & 1] : L.inflight;   // per-direction window or one shared window
    return used >= int(std::floor(L.window));
}
bool cross_candidate_seen = false;
long long pacing_denied_total = 0;
int side(int loc) { return (axis == 0 ? loc % cols : loc / cols) >= cut; }
int inflight() {
    int n = 0;
    for (const auto& r : reservations) n += r.task >= 0;
    return n;
}
bool crosses(int agent, int task, SharedEnvironment* env) {
    const auto& t = env->task_pool.at(task);
    return axis >= 0 && !t.locations.empty() &&
        side(env->system_states.at(agent).location) != side(t.locations.front());
}
}

void initialize(SharedEnvironment* env) {
    std::lock_guard<std::mutex> lock(feedback_mutex);
    const char* p = std::getenv("ROBOT_POLICY");
    policy = p ? p : "baseline";
    if (policy != "baseline" && policy != "static" && policy != "adaptive" && policy != "bbr" && policy != "multicut" && policy != "multicut_adaptive")
        throw std::runtime_error("ROBOT_POLICY must be baseline, static, adaptive, bbr, multicut or multicut_adaptive");
    cols = env->cols;
    g_opp = g_marks = 0; g_alpha = 0; g_last = 0; g_last_obs = -1; g_init = false; g_now = 0; g_door_seen = false;
    axis = -1; cut = -1; boundary_edges = 0;
    reservations.assign(env->num_of_agents, {});
    window = 6;
    if (const char* w = std::getenv("ROBOT_WINDOW")) window = std::stod(w);
    // v10: ROBOT_WINDOW_FLOOR lets the static window go below 2 (1 = at most one crossing in flight).
    floor_w = 2.0; if (const char* f = std::getenv("ROBOT_WINDOW_FLOOR")) floor_w = std::max(1.0, std::stod(f));
    window = std::max(floor_w, std::min(window, double(env->num_of_agents)));
    task_seen.clear(); lat_n = 0; lat_sum = 0; lat_max = 0; lat_hist.clear();
    alpha = 0; last_update = 0; last_logged = -1; last_observed = -1;
    acknowledgements = denied = 0; opportunities = marks = 0;
    admitted_total = acked_total = cancelled_total = 0; last_fraction = 0;
    cross_candidate_seen = false; pacing_denied_total = 0;
    if (policy == "bbr") bbr.reset(env->num_of_agents, window,
        std::max(1, env->min_planner_communication_time / env->action_time));
    // A complete axis-aligned cutset is unavoidable between its two sides.
    // Rank cuts by free crossing edges / smaller side area. Keep both sides
    // at least 20% of free space to avoid treating a tiny alcove as a gate.
    int total = 0;
    for (int blocked : env->map) total += !blocked;
    double best = 1e100;
    for (int a = 0; a < 2; ++a) {
        int size = a == 0 ? env->cols : env->rows;
        for (int k = 1; k < size; ++k) {
            int left = 0, edges = 0;
            for (int v = 0; v < int(env->map.size()); ++v) {
                if (env->map[v]) continue;
                int coord = a == 0 ? v % cols : v / cols;
                left += coord < k;
                if (coord != k - 1) continue;
                int next = v + (a == 0 ? 1 : cols);
                if (next < int(env->map.size()) && !env->map[next]) ++edges;
            }
            int small = std::min(left, total - left);
            if (edges == 0 || small < total * .2) continue;
            double score = double(edges) / small;
            if (score < best) { best = score; axis = a; cut = k; boundary_edges = edges; }
        }
    }
    lines.clear(); mcres.assign(env->num_of_agents, {});
    if (multicut()) {
        // Bottleneck lines: axis-aligned lines whose free crossing edges are few relative to the line length.
        // Consecutive qualifying lines (a thick wall) are merged, keeping the one with fewest edges.
        const double ratio = std::getenv("ROBOT_MC_RATIO") ? std::stod(std::getenv("ROBOT_MC_RATIO")) : 0.15;
        mc_adaptive = policy == "multicut_adaptive";
        // Congestion gate (ECN-like): a line's window is enforced only while its measured blocked fraction (EWMA) >= gate.
        mc_gate = std::getenv("ROBOT_MC_GATE") ? std::stod(std::getenv("ROBOT_MC_GATE")) : 0.0;
        mc_legs_all = std::getenv("ROBOT_MC_LEGS") && std::string(std::getenv("ROBOT_MC_LEGS")) == "all";
        mc_dir = std::getenv("ROBOT_MC_DIR") && std::string(std::getenv("ROBOT_MC_DIR")) == "1";
        mc_add_single = std::getenv("ROBOT_MC_ADD_SINGLE") && std::string(std::getenv("ROBOT_MC_ADD_SINGLE")) == "1";
        mc_floor = std::getenv("ROBOT_WINDOW_FLOOR") ? std::max(1.0, std::stod(std::getenv("ROBOT_WINDOW_FLOOR"))) : 2.0;
        for (int a = 0; a < 2; ++a) {
            const int size = a == 0 ? env->cols : env->rows, span = a == 0 ? env->rows : env->cols;
            Line prev; bool open_run = false;
            for (int k = 1; k < size; ++k) {
                int left = 0, edges = 0;
                for (int v = 0; v < int(env->map.size()); ++v) {
                    if (env->map[v]) continue;
                    const int coord = a == 0 ? v % cols : v / cols;
                    left += coord < k;
                    if (coord != k - 1) continue;
                    const int next = v + (a == 0 ? 1 : cols);
                    if (next < int(env->map.size()) && !env->map[next]) ++edges;
                }
                const bool q = edges > 0 && edges <= std::max(2.0, ratio * span) && std::min(left, total - left) >= total * .05;
                if (q) {
                    Line L; L.axis = a; L.cut = k; L.edges = edges;
                    // Window sizing: ROBOT_MC_PER_EDGE=c gives each line a capacity-proportional window c*edges
                    // (like a bandwidth-delay product); otherwise every line uses ROBOT_WINDOW.
                    const double w0 = std::getenv("ROBOT_MC_PER_EDGE") ? std::ceil(std::stod(std::getenv("ROBOT_MC_PER_EDGE")) * edges) : window;
                    L.window = std::max(mc_floor, std::min(w0, double(env->num_of_agents)));
                    L.active = mc_gate <= 0;
                    if (!open_run) { prev = L; open_run = true; } else if (L.edges < prev.edges) prev = L;
                } else if (open_run) { lines.push_back(prev); open_run = false; }
            }
            if (open_run) lines.push_back(prev);
        }
    }
    if (multicut() && mc_add_single && axis >= 0) {
        bool dup = false;
        for (const auto& L : lines) dup = dup || (L.axis == axis && std::abs(L.cut - cut) <= 1);
        if (!dup) {
            Line L; L.axis = axis; L.cut = cut; L.edges = boundary_edges;
            const double w0 = std::getenv("ROBOT_MC_PER_EDGE") ? std::ceil(std::stod(std::getenv("ROBOT_MC_PER_EDGE")) * boundary_edges) : window;
            L.window = std::max(mc_floor, std::min(w0, double(env->num_of_agents))); L.active = mc_gate <= 0;
            lines.push_back(L);
        }
    }
    mc_credit = std::getenv("ROBOT_MC_CREDIT") ? std::stod(std::getenv("ROBOT_MC_CREDIT")) : 0.0;
    mc_zone = std::getenv("ROBOT_MC_ZONE") ? std::atoi(std::getenv("ROBOT_MC_ZONE")) : 2;
    mc_hard = std::getenv("ROBOT_MC_HARD") && std::string(std::getenv("ROBOT_MC_HARD")) == "1";
    mc_scope = std::getenv("ROBOT_MC_SCOPE") && std::string(std::getenv("ROBOT_MC_SCOPE")) == "door" ? 1 : 0;
    zone_of.clear(); zcap.clear(); zocc.clear(); zinfl.clear(); door_of_along.clear(); door_center.clear();
    if (multicut()) {   // doors of every line: runs of adjacent crossing edges (one pooled "door" with the line scope)
        for (const auto& L : lines) {
            const int span = L.axis == 0 ? int(env->map.size()) / cols : cols;
            std::vector<char> has(span, 0);
            for (int v = 0; v < int(env->map.size()); ++v) {
                if (env->map[v]) continue;
                const int coord = L.axis == 0 ? v % cols : v / cols; if (coord != L.cut - 1) continue;
                const int next = v + (L.axis == 0 ? 1 : cols); if (next >= int(env->map.size()) || env->map[next]) continue;
                has[L.axis == 0 ? v / cols : v % cols] = 1;
            }
            std::vector<int> dof(span, -1); std::vector<double> centers; std::vector<int> cnt;
            for (int x = 0; x < span; ++x) {
                if (!has[x]) continue;
                const int d = mc_scope == 0 ? 0 : ((x > 0 && has[x - 1]) ? int(centers.size()) - 1 : int(centers.size()));
                if (d >= int(centers.size())) { centers.push_back(0); cnt.push_back(0); }
                dof[x] = d; centers[d] += x; ++cnt[d];
            }
            for (size_t d = 0; d < centers.size(); ++d) centers[d] /= std::max(1, cnt[d]);
            if (centers.empty()) centers.push_back(0);
            door_of_along.push_back(dof); door_center.push_back(centers);
            zinfl.push_back(std::vector<int>(2 * centers.size(), 0));
        }
    }
    if (multicut() && mc_credit > 0) {
        const int R = mc_zone, rows = int(env->map.size()) / cols;
        for (size_t li = 0; li < lines.size(); ++li) {
            const auto& L = lines[li];
            std::vector<int> z(env->map.size(), -1); std::vector<int> cap(2 * door_center[li].size(), 0);
            for (int v = 0; v < int(env->map.size()); ++v) {
                if (env->map[v]) continue;
                const int coord = L.axis == 0 ? v % cols : v / cols; if (coord != L.cut - 1) continue;
                const int next = v + (L.axis == 0 ? 1 : cols); if (next >= int(env->map.size()) || env->map[next]) continue;
                const int along = L.axis == 0 ? v / cols : v % cols;       // position of this crossing edge along the line
                const int door = door_of_along[li][along] < 0 ? 0 : door_of_along[li][along];
                for (int c = L.cut - R; c <= L.cut + R - 1; ++c) for (int a = along - R; a <= along + R; ++a) {
                    const int r_ = L.axis == 0 ? a : c, c_ = L.axis == 0 ? c : a;
                    if (r_ < 0 || c_ < 0 || r_ >= rows || c_ >= cols) continue;
                    const int u = r_ * cols + c_; if (env->map[u] || z[u] >= 0) continue;
                    z[u] = door * 2 + (c >= L.cut); ++cap[z[u]];
                }
            }
            zocc.push_back(std::vector<int>(cap.size(), 0)); zone_of.push_back(std::move(z)); zcap.push_back(cap);
        }
    }
    // v10 control: force a specific cut, e.g. one that is NOT a bottleneck (ROBOT_CUT_AXIS=x|y, ROBOT_CUT_COORD=k).
    if (const char* ca = std::getenv("ROBOT_CUT_AXIS")) {
        axis = std::string(ca) == "x" ? 0 : 1;
        cut = std::getenv("ROBOT_CUT_COORD") ? std::atoi(std::getenv("ROBOT_CUT_COORD")) : cut;
        boundary_edges = 0;
        for (int v = 0; v < int(env->map.size()); ++v) {
            if (env->map[v]) continue;
            int coord = axis == 0 ? v % cols : v / cols;
            if (coord != cut - 1) continue;
            int next = v + (axis == 0 ? 1 : cols);
            if (next < int(env->map.size()) && !env->map[next]) ++boundary_edges;
        }
    }
    if (telemetry.is_open()) telemetry.close();
    telemetry.clear();
    br_K = std::getenv("ROBOT_BRIDGE_CREDIT") ? std::atoi(std::getenv("ROBOT_BRIDGE_CREDIT")) : 0;
    br_K2 = std::getenv("ROBOT_CUT2_CREDIT") ? std::atoi(std::getenv("ROBOT_CUT2_CREDIT")) : 0; br_n1 = 0; br_Kb.clear();
    br_frac = std::getenv("ROBOT_BRIDGE_FRAC") ? std::stod(std::getenv("ROBOT_BRIDGE_FRAC")) : 0.05;
    br_trace = std::getenv("ROBOT_BRIDGE_TRACE") != nullptr; br_denied = br_admitted = 0; br_last_trace = -1;
    net_on = std::getenv("ROBOT_NET") ? std::atoi(std::getenv("ROBOT_NET")) : 0;
    c2_sigfix = net_on || (std::getenv("ROBOT_CUT2_SIGFIX") && std::atoi(std::getenv("ROBOT_CUT2_SIGFIX")));
    if (const char* e = std::getenv("ROBOT_NET_ALPHA")) net_alpha = std::stod(e);
    if (const char* e = std::getenv("ROBOT_NET_C1")) net_c1 = std::stod(e);
    if (const char* e = std::getenv("ROBOT_NET_LEG1")) net_leg1 = std::stod(e);
    net_ta = std::getenv("ROBOT_NET_TA") ? std::stod(std::getenv("ROBOT_NET_TA")) : -1.0;
    net_tb = std::getenv("ROBOT_NET_TB") ? std::stod(std::getenv("ROBOT_NET_TB")) : 1.0;
    rg_cuts_on = std::getenv("ROBOT_RG_CUTS") ? std::atoi(std::getenv("ROBOT_RG_CUTS")) : 0;
    rg_dry = std::getenv("ROBOT_RG_DRY") ? std::atoi(std::getenv("ROBOT_RG_DRY")) : 0; rg_first = -1;
    rg_bbr = std::getenv("ROBOT_RG_BBR") ? std::atoi(std::getenv("ROBOT_RG_BBR")) : 0;
    bb_win = std::getenv("ROBOT_RG_BBR_WIN") ? std::atoi(std::getenv("ROBOT_RG_BBR_WIN")) : 500; bb_gain = std::getenv("ROBOT_RG_BBR_GAIN") ? std::stod(std::getenv("ROBOT_RG_BBR_GAIN")) : 2.0;
    bb_wl.clear(); bb_wx.clear(); bb_maxr.clear(); bb_mind.clear(); bb_cap.clear(); bb_t0 = -1; bb_denied = 0;
    cm_on = std::getenv("ROBOT_CUT_MEAS") ? std::atoi(std::getenv("ROBOT_CUT_MEAS")) : 0; cm_last_t = cm_t0 = cm_last_print = -1; cm_lsum.clear(); cm_x.clear();
    if (const char* e = std::getenv("ROBOT_NET_C2")) net_c2 = std::stod(e);
    rg_new.clear(); rg_pending = false;
    br_side.clear(); br_load.clear(); br_counted.clear();
    if (br_K > 0 || br_K2 > 0 || br_trace || std::getenv("ROBOT_BMAC")) br_detect(env);
    c2_init(env);
    LinkCredit::initialize(env);
    rg_cap = std::getenv("ROBOT_REGION_CAP") ? std::stod(std::getenv("ROBOT_REGION_CAP")) : 0.0;
    rg_of.clear(); rg_capv.clear(); rg_load.clear(); rg_counted.assign(env->num_of_agents, -1); rg_denied = 0;
    if (multicut() && rg_cap > 0) {
        std::unordered_map<long long,int> idx; std::vector<int> cells;
        rg_of.assign(env->map.size(), -1);
        for (int v = 0; v < int(env->map.size()); ++v) {
            if (env->map[v]) continue;
            long long key = 0; for (size_t li = 0; li < lines.size() && li < 62; ++li) key |= (long long)lside(lines[li], v) << li;
            auto it = idx.find(key); int r;
            if (it == idx.end()) { r = int(cells.size()); idx[key] = r; cells.push_back(0); } else r = it->second;
            rg_of[v] = r; ++cells[r];
        }
        for (int c : cells) rg_capv.push_back(std::max(1, int(std::floor(rg_cap * c))));
        rg_load.assign(cells.size(), 0);
    }
    ra_pen = std::getenv("ROBOT_REGION_AVOID") ? std::atoi(std::getenv("ROBOT_REGION_AVOID")) : 0;
    ra_th = std::getenv("ROBOT_REGION_AVOID_TH") ? std::stod(std::getenv("ROBOT_REGION_AVOID_TH")) : 0.15;
    ra_of.clear(); ra_cells.clear(); ra_occ.clear(); ra_hot.clear();
    if (multicut() && ra_pen > 0 && !lines.empty()) {
        std::unordered_map<long long,int> idx; ra_of.assign(env->map.size(), -1);
        for (int v = 0; v < int(env->map.size()); ++v) {
            if (env->map[v]) continue;
            long long key = 0; for (size_t li = 0; li < lines.size() && li < 62; ++li) key |= (long long)lside(lines[li], v) << li;
            auto it = idx.find(key); int r;
            if (it == idx.end()) { r = int(ra_cells.size()); idx[key] = r; ra_cells.push_back(0); } else r = it->second;
            ra_of[v] = r; ++ra_cells[r];
        }
        ra_occ.assign(ra_cells.size(), 0); ra_hot.assign(ra_cells.size(), 0);
        if (ra_cells.size() < 4) { ra_of.clear(); ra_pen = 0; }   // not a room-like layout
    }
    const int ow_mode = std::getenv("ROBOT_ONEWAY_DOORS") ? std::atoi(std::getenv("ROBOT_ONEWAY_DOORS")) : 0;
    ow_on = ow_mode == 1;
    ow_forbid.assign(env->map.size() * 4, 0); ow_doors = ow_directed = 0;
    if (multicut() && ow_on) {
        const int rows = int(env->map.size()) / cols, n = int(env->map.size());
        std::vector<int> cuts_axis[2]; for (const auto& L : lines) cuts_axis[L.axis].push_back(L.cut);
        for (const auto& L : lines) {
            const int span = L.axis == 0 ? rows : cols;
            auto cell = [&](int along) { return L.axis == 0 ? along * cols + (L.cut - 1) : (L.cut - 1) * cols + along; };
            std::vector<int> pos;
            for (int along = 0; along < span; ++along) {
                const int v = cell(along), nx = v + (L.axis == 0 ? 1 : cols);
                if (v >= 0 && nx < n && !env->map[v] && !env->map[nx]) pos.push_back(along);
            }
            std::vector<std::pair<int,int>> doors;   // [first, last] along positions of each run
            for (size_t k = 0; k < pos.size(); ++k) { if (k > 0 && pos[k] == pos[k - 1] + 1) doors.back().second = pos[k]; else doors.push_back({pos[k], pos[k]}); }
            std::map<int, std::vector<std::pair<int,int>>> seg;
            for (const auto& d : doors) { int sgi = 0; for (int c : cuts_axis[1 - L.axis]) sgi += c <= d.first; seg[sgi].push_back(d); }
            auto set_dir = [&](int along, int dir) {   // dir +1: only from side 0 to side 1; -1: only from side 1 to side 0
                const int v = cell(along), nx = v + (L.axis == 0 ? 1 : cols);
                const int fwd = L.axis == 0 ? 0 : 1, back = L.axis == 0 ? 2 : 3;
                if (dir > 0) ow_forbid[size_t(nx) * 4 + back] = 1; else ow_forbid[size_t(v) * 4 + fwd] = 1;
            };
            for (auto& kv : seg) {
                auto& g = kv.second; ow_doors += int(g.size());
                if (g.size() >= 2) {
                    for (size_t i = 0; i < g.size(); ++i) { for (int a = g[i].first; a <= g[i].second; ++a) set_dir(a, i % 2 == 0 ? 1 : -1); ++ow_directed; }
                } else {
                    const int w = g[0].second - g[0].first + 1;
                    if (w >= 2) { for (int a = g[0].first; a <= g[0].second; ++a) set_dir(a, a - g[0].first < w / 2 ? 1 : -1); ++ow_directed; }
                }
            }
        }
    }
    if (multicut() && ow_mode == 2) {
        // v18c: every door may become one-way. Regions = cells grouped by their side of every door line (rooms). Doors are runs of
        // adjacent crossing edges of a line. Doors are visited in order; each one is made one-way (from the room with fewer exits
        // to the room with fewer entrances; a door wider than one cell gets half of its lanes each way instead) as long as the room
        // graph stays strongly connected, otherwise it stays two-way.
        ow_on = true;
        const int n = int(env->map.size()), rows = n / cols;
        std::unordered_map<long long,int> ridx; std::vector<int> reg(n, -1);
        for (int v = 0; v < n; ++v) { if (env->map[v]) continue; long long key = 0; for (size_t li = 0; li < lines.size() && li < 62; ++li) key |= (long long)lside(lines[li], v) << li;
            auto it = ridx.find(key); if (it == ridx.end()) { const int r = int(ridx.size()); ridx[key] = r; reg[v] = r; } else reg[v] = it->second; }
        const int R = int(ridx.size());
        struct Door { int li; int a0, a1; int ra, rb; };   // ra = region on side 0, rb = region on side 1
        std::vector<Door> drs;
        for (size_t li = 0; li < lines.size(); ++li) {
            const auto& L = lines[li]; const int span = L.axis == 0 ? rows : cols;
            auto cell = [&](int along) { return L.axis == 0 ? along * cols + (L.cut - 1) : (L.cut - 1) * cols + along; };
            int start = -1;
            for (int along = 0; along <= span; ++along) {
                bool e = false;
                if (along < span) { const int v = cell(along), nx = v + (L.axis == 0 ? 1 : cols); e = v >= 0 && nx < n && !env->map[v] && !env->map[nx] && reg[v] != reg[nx]; }
                if (e && start < 0) start = along;
                if ((!e || (start >= 0 && along < span && reg[cell(along)] != reg[cell(start)])) && start >= 0) {
                    const int v = cell(start), nx = v + (L.axis == 0 ? 1 : cols);
                    drs.push_back({int(li), start, along - 1, reg[v], reg[nx]}); start = e ? along : -1;
                }
            }
        }
        // adjacency counts: cnt[a][b] = number of usable directed passages a->b
        std::vector<std::vector<int>> cnt(R, std::vector<int>(R, 0));
        std::vector<int> dirv(drs.size(), 0);   // 0 two-way, +1 side0->side1 only, -1 side1->side0 only, 2 split lanes
        for (const auto& d : drs) { ++cnt[d.ra][d.rb]; ++cnt[d.rb][d.ra]; }
        auto strongly = [&]() {
            for (int pass = 0; pass < 2; ++pass) {
                std::vector<char> seen(R, 0); std::vector<int> st = {0}; seen[0] = 1;
                while (!st.empty()) { const int x = st.back(); st.pop_back(); for (int y = 0; y < R; ++y) { const int c = pass == 0 ? cnt[x][y] : cnt[y][x]; if (c > 0 && !seen[y]) { seen[y] = 1; st.push_back(y); } } }
                for (int y = 0; y < R; ++y) if (!seen[y]) return false;
            }
            return true;
        };
        std::vector<int> outs(R, 0), ins(R, 0);
        for (size_t k = 0; k < drs.size(); ++k) {
            const auto& d = drs[k];
            if (d.a1 > d.a0) { dirv[k] = 2; continue; }   // wide door: split lanes, both directions remain
            const int dir = (outs[d.ra] - ins[d.ra]) <= (outs[d.rb] - ins[d.rb]) ? 1 : -1;
            const int from = dir > 0 ? d.ra : d.rb, to = dir > 0 ? d.rb : d.ra;
            --cnt[to][from];
            if (strongly()) { dirv[k] = dir; ++outs[from]; ++ins[to]; } else ++cnt[to][from];
        }
        for (size_t k = 0; k < drs.size(); ++k) {
            const auto& d = drs[k]; const auto& L = lines[d.li];
            auto cell = [&](int along) { return L.axis == 0 ? along * cols + (L.cut - 1) : (L.cut - 1) * cols + along; };
            const int fwd = L.axis == 0 ? 0 : 1, back = L.axis == 0 ? 2 : 3, w = d.a1 - d.a0 + 1;
            ++ow_doors;
            for (int a = d.a0; a <= d.a1; ++a) {
                const int v = cell(a), nx = v + (L.axis == 0 ? 1 : cols);
                const int dir = dirv[k] == 2 ? (a - d.a0 < w / 2 ? 1 : -1) : dirv[k];
                if (dir > 0) ow_forbid[size_t(nx) * 4 + back] = 1; else if (dir < 0) ow_forbid[size_t(v) * 4 + fwd] = 1;
            }
            if (dirv[k] != 0) ++ow_directed;
        }
        if (std::getenv("ROBOT_ONEWAY_TRACE")) std::fprintf(stderr, "oneway: regions %d doors %d directed %d\n", R, ow_doors, ow_directed);
    }
    rp_off = std::getenv("ROBOT_ROOM_PAUSE") ? std::stod(std::getenv("ROBOT_ROOM_PAUSE")) : 0.0;
    rp_on = std::getenv("ROBOT_ROOM_RESUME") ? std::stod(std::getenv("ROBOT_ROOM_RESUME")) : rp_off * 0.6;
    rp_of.clear(); rp_cells.clear(); rp_occ.clear(); rp_paused.clear(); rp_edge_region.clear(); rp_pause_events = 0;
    if (multicut() && rp_off > 0 && !lines.empty()) {
        const int n = int(env->map.size());
        std::unordered_map<long long,int> idx; rp_of.assign(n, -1);
        for (int v = 0; v < n; ++v) {
            if (env->map[v]) continue;
            long long key = 0; for (size_t li = 0; li < lines.size() && li < 62; ++li) key |= (long long)lside(lines[li], v) << li;
            auto it = idx.find(key); int r;
            if (it == idx.end()) { r = int(rp_cells.size()); idx[key] = r; rp_cells.push_back(0); } else r = it->second;
            rp_of[v] = r; ++rp_cells[r];
        }
        if (rp_cells.size() < 4) { rp_off = 0; rp_of.clear(); }
        else {
            rp_occ.assign(rp_cells.size(), 0); rp_paused.assign(rp_cells.size(), 0); rp_edge_region.assign(size_t(n) * 4, -1);
            const int dv[4] = {1, cols, -1, -cols};
            for (int v = 0; v < n; ++v) {
                if (env->map[v]) continue;
                for (int d = 0; d < 4; ++d) {
                    const int u = v + dv[d];
                    if (u < 0 || u >= n || env->map[u]) continue;
                    if ((d == 0 && u % cols == 0) || (d == 2 && v % cols == 0)) continue;
                    if (rp_of[u] != rp_of[v]) rp_edge_region[size_t(v) * 4 + d] = rp_of[u];   // moving v->u enters region of u
                }
            }
        }
    }
    if (const char* path = std::getenv("ROBOT_TELEMETRY")) {
        telemetry.open(path, std::ios::trunc);
        if (!telemetry) throw std::runtime_error("Cannot open ROBOT_TELEMETRY");
    }
}

double global_blocked() { std::lock_guard<std::mutex> lock(feedback_mutex); return g_alpha; }
bool free_flowing(double gate) {
    std::lock_guard<std::mutex> lock(feedback_mutex);
    // v14c: observe for the first 100 ticks; a map on which a door line was ever measured as congested never uses the turn cost
    return g_init && g_now >= 100 && !g_door_seen && g_alpha < gate;
}


// v19b: bridge geometry for the planner-side bridge MAC (copied by NetMac at its initialisation)
int bridge_count(SharedEnvironment* env) { if (br_side.empty() && br_cells.empty() && env) br_detect(env); return br_n1; }
int bridge_side(int b, int cell) { return (b < 0 || b >= int(br_side.size()) || cell < 0) ? -1 : br_side[b][cell]; }
bool door_zone(int cell) { return cell >= 0 && cell < int(dz_mask.size()) && dz_mask[cell]; }
std::vector<int> bridge_cells(int b) { return (b < 0 || b >= int(br_cells.size())) ? std::vector<int>() : br_cells[b]; }
int region_of(int cell) { return ra_of.empty() || cell < 0 ? -1 : ra_of[cell]; }
bool move_allowed_goal(int from, int to, int goal_cell) {
    if (!move_allowed(from, to)) return false;
    if (rp_off <= 0 || rp_edge_region.empty() || from < 0) return true;
    const int d = to - from; int dir;
    if (d == 1) dir = 0; else if (d == cols) dir = 1; else if (d == -1) dir = 2; else if (d == -cols) dir = 3; else return true;
    const int r = rp_edge_region[size_t(from) * 4 + dir];
    if (r < 0 || !rp_paused[r]) return true;
    return goal_cell >= 0 && rp_of[goal_cell] == r;   // only robots whose goal is inside may still enter a paused room
}
int transit_pen(int cell, int rstart, int rgoal) {
    if (ra_pen <= 0 || ra_of.empty() || cell < 0) return 0;
    const int r = ra_of[cell];
    return (r >= 0 && ra_hot[r] && r != rstart && r != rgoal) ? ra_pen : 0;
}

void forbid_move(int from, int to) {
    if (from < 0 || to < 0 || ow_forbid.empty()) return;
    const int d = to - from; int dir;
    if (d == 1) dir = 0; else if (d == cols) dir = 1; else if (d == -1) dir = 2; else if (d == -cols) dir = 3; else return;
    ow_forbid[size_t(from) * 4 + dir] = 1; ow_on = true;
}
bool move_allowed(int from, int to) {
    if (!ow_on || ow_forbid.empty() || from < 0) return true;
    const int d = to - from; int dir;
    if (d == 1) dir = 0; else if (d == cols) dir = 1; else if (d == -1) dir = 2; else if (d == -cols) dir = 3; else return true;
    return !ow_forbid[size_t(from) * 4 + dir];
}

int line_crossings(int a, int g) {
    if (!multicut()) return 0;
    int n = 0; for (const auto& L : lines) if (L.active && lside(L, a) != lside(L, g)) ++n;
    return n;
}

bool any_line_active() {
    if (!multicut()) return false;
    for (const auto& L : lines) if (L.active) return true;
    return false;
}

void begin_schedule(SharedEnvironment* env) {
    LinkCredit::begin_schedule(env);
    if (rg_pending) rg_activate();
    if (rg_cuts_on == 5 && rg_first >= 0 && !g5_on.empty()) {   // v45: measure J of each gated bridge
        const int tnow = env->system_timestep, na = int(env->system_states.size()), nj = int(g5_on.size());
        if (g5_t0 < 0) { g5_t0 = tnow; g5_tl = tnow; g5_side.assign(nj, std::vector<signed char>(na, -1)); }
        const int dt = std::max(0, tnow - g5_tl); g5_tl = tnow;
        for (int j = 0; j < nj; ++j) { const auto& sd = br_side[rg_first + j]; bool q = false;
            for (int i = 0; i < na; ++i) { const int loc = env->system_states[i].location; if (loc < 0) continue;
                if (!q && g5_apron[j][loc]) q = true;
                const int s2 = sd[loc]; if (s2 >= 0) { if (g5_side[j][i] >= 0 && g5_side[j][i] != s2) ++g5_cross[j]; g5_side[j][i] = (signed char)s2; } }
            if (q) g5_q[j] += dt; }
        if (tnow - g5_t0 >= 500) {
            for (int j = 0; j < nj; ++j) { double J = -1;
                if (g5_q[j] >= 50 && g5_cap[j] > 0) { J = g5_cross[j] / g5_q[j] / g5_cap[j];
                    if (J < 0.9) { ++g5_lo[j]; g5_hi[j] = 0; } else if (J >= 1.0) { ++g5_hi[j]; g5_lo[j] = 0; } else { g5_lo[j] = g5_hi[j] = 0; }
                    if (!g5_on[j] && g5_lo[j] >= 2) g5_on[j] = 1; else if (g5_on[j] && g5_hi[j] >= 2) g5_on[j] = 0; }
                if (br_trace) std::fprintf(stderr, "[rg5] t=%d cut %d queue %.0f crossings %d J %.3f credit %s\n", tnow, rg_first + j, g5_q[j], g5_cross[j], J, g5_on[j] ? "on" : "off");
                g5_cross[j] = 0; g5_q[j] = 0; }
            g5_t0 = tnow; }
    }
    if ((br_K > 0 || br_K2 > 0) && !br_side.empty() && !LinkCredit::replaces_cuts()) {   // v19: recount bridge credit from the current assignments
        const int tnow = env->system_timestep;
        if (rg_bbr && rg_first >= 0) {   // v36: per-window accumulators of the region-graph cuts
            const int nb = int(br_load.size()) - rg_first;
            if (int(bb_wl.size()) != nb) { bb_wl.assign(nb, {}); bb_wx.assign(nb, {}); bb_maxr.assign(nb, {}); bb_mind.assign(nb, {}); bb_cap.assign(nb, {});
                for (int j = 0; j < nb; ++j) { const size_t k = br_load[rg_first + j].size(); bb_wl[j].assign(k, 0.0); bb_wx[j].assign(k, 0); bb_maxr[j].assign(k, -1.0); bb_mind[j].assign(k, -1.0); bb_cap[j].assign(k, 0); }
                bb_t0 = tnow; }
            static int bb_last = -1; if (bb_t0 == tnow) bb_last = tnow;
            if (bb_last >= 0 && tnow > bb_last) { const double dt = tnow - bb_last; for (int j = 0; j < nb; ++j) for (size_t q = 0; q < bb_wl[j].size(); ++q) bb_wl[j][q] += dt * br_load[rg_first + j][q]; }
            bb_last = tnow;
        }
        if (cm_on) {   // v35: time-weighted in-flight since the last schedule, using the loads as they were
            if (cm_lsum.size() != br_load.size()) { cm_lsum.resize(br_load.size()); cm_x.resize(br_load.size());
                for (size_t b = 0; b < br_load.size(); ++b) { cm_lsum[b].resize(br_load[b].size(), 0.0); cm_x[b].resize(br_load[b].size(), 0); } }
            if (cm_t0 < 0) cm_t0 = tnow;
            if (cm_last_t >= 0) { const double dt = tnow - cm_last_t; for (size_t b = 0; b < br_load.size(); ++b) for (size_t q = 0; q < br_load[b].size(); ++q) cm_lsum[b][q] += dt * br_load[b][q]; }
            cm_last_t = tnow;
        }
        std::vector<std::vector<std::pair<int,int>>> cm_prev; if (cm_on || (rg_bbr && rg_first >= 0)) cm_prev = br_counted;
        for (auto& v : br_load) std::fill(v.begin(), v.end(), 0);
        for (int i = 0; i < int(env->system_states.size()) && i < int(br_counted.size()); ++i) {
            br_counted[i].clear();
            auto it = env->task_pool.find(env->curr_task_schedule[i]);
            if (it == env->task_pool.end()) continue;
            br_route(env->system_states[i].location, it->second.locations, it->second.idx_next_loc, br_tmp); br_count(i);
        }
        if (rg_bbr && rg_first >= 0 && !bb_wx.empty()) {   // v36: completed crossings of the region-graph cuts; close a window every bb_win ticks
            for (int i = 0; i < int(cm_prev.size()) && i < int(br_counted.size()); ++i) { const int loc = env->system_states[i].location; if (loc < 0) continue;
                for (auto& bs : cm_prev[i]) if (bs.first >= rg_first && std::find(br_counted[i].begin(), br_counted[i].end(), bs) == br_counted[i].end() && br_side[bs.first][loc] == bs.second) ++bb_wx[bs.first - rg_first][bs.second]; }
            if (tnow - bb_t0 >= bb_win) { const double W = tnow - bb_t0;
                for (size_t j = 0; j < bb_wx.size(); ++j) for (size_t q = 0; q < bb_wx[j].size(); ++q) { const long long X = bb_wx[j][q];
                    if (X > 0) { const double r = X / W, d = bb_wl[j][q] / X; bb_maxr[j][q] = std::max(bb_maxr[j][q], r); bb_mind[j][q] = bb_mind[j][q] < 0 ? d : std::min(bb_mind[j][q], d); }
                    if (bb_maxr[j][q] > 0 && bb_mind[j][q] > 0) bb_cap[j][q] = std::max(1, int(std::ceil(bb_gain * bb_maxr[j][q] * bb_mind[j][q])));
                    bb_wl[j][q] = 0; bb_wx[j][q] = 0; }
                if (br_trace) { std::fprintf(stderr, "[rgbbr] t=%d denied=%lld caps:", tnow, bb_denied); for (size_t j = 0; j < bb_cap.size(); ++j) { std::fprintf(stderr, " |"); for (size_t q = 0; q < bb_cap[j].size(); ++q) std::fprintf(stderr, " %d(L%d)", bb_cap[j][q], br_load[rg_first + j][q]); } std::fprintf(stderr, "\n"); }
                bb_t0 = tnow; }
        }
        if (cm_on) {   // v35: completed crossings = entries that disappeared while the robot is on the destination side
            for (int i = 0; i < int(cm_prev.size()) && i < int(br_counted.size()); ++i) { const int loc = env->system_states[i].location; if (loc < 0) continue;
                for (auto& bs : cm_prev[i]) if (std::find(br_counted[i].begin(), br_counted[i].end(), bs) == br_counted[i].end() && br_side[bs.first][loc] == bs.second) ++cm_x[bs.first][bs.second]; }
            if (tnow / 500 != cm_last_print) { cm_last_print = tnow / 500; const double el = std::max(1, tnow - cm_t0);
                for (size_t b = 0; b < br_load.size() && b < cm_lsum.size(); ++b) { std::fprintf(stderr, "[cutmeas] t=%d cut %zu %s", tnow, b, (rg_first >= 0 && int(b) >= rg_first) ? "rg" : "old");
                    for (size_t q = 0; q < br_load[b].size(); ++q) { const double L = cm_lsum[b][q] / el; const long long X = cm_x[b][q];
                        const int K = b < br_Ks.size() && q < br_Ks[b].size() ? br_Ks[b][q] : -1; const double Tf = b < br_Tfree.size() && q < br_Tfree[b].size() ? br_Tfree[b][q] : -1;
                        std::fprintf(stderr, " | side%zu K=%d Tfree=%.0f L=%.2f X=%lld T=%.0f", q, K, Tf, L, X, X > 0 ? L * el / X : -1.0); }
                    std::fprintf(stderr, "\n"); } }
        }
        c2_step(env);
        if (br_trace && env->system_timestep / 500 != br_last_trace) { br_last_trace = env->system_timestep / 500;
            std::fprintf(stderr, "[bridge] t=%d denied=%lld admitted=%lld load:", env->system_timestep, br_denied, br_admitted);
            for (auto& v : br_load) { std::fprintf(stderr, " |"); for (int x : v) std::fprintf(stderr, " %d", x); } std::fprintf(stderr, "\n"); }
    }
    {   // v14: map-wide congestion signal, same sampling period and smoothing as the per-line signal
        std::lock_guard<std::mutex> lock(feedback_mutex);
        g_now = env->system_timestep;
        if (env->system_timestep - g_last >= std::max(12, 8 * env->max_counter)) {
            if (g_opp > 0) { const double f = double(g_marks) / g_opp; g_alpha = g_init ? .875 * g_alpha + .125 * f : f; g_init = true; }
            g_opp = g_marks = 0; g_last = env->system_timestep;
        }
    }
    std::vector<BbrReceipt> receipts;
    cross_candidate_seen = false;
    {   // v10: a task that left the pool since the last call has been completed now.
        std::unordered_set<int> live;
        for (const auto& kv : env->task_pool) { live.insert(kv.first); task_seen.emplace(kv.first, kv.second.t_revealed); }
        for (auto it = task_seen.begin(); it != task_seen.end();) {
            if (!live.count(it->first)) { const int l = env->system_timestep - it->second; ++lat_n; lat_sum += l; lat_max = std::max(lat_max, l); lat_hist.push_back(l); it = task_seen.erase(it); }
            else ++it;
        }
    }
    // This is the planner's stable physical snapshot, NOT predicted curr_states.
    // Each reservation can be ACKed once, after its actual region transition.
    for (int i = 0; i < int(reservations.size()); ++i) {
        auto& r = reservations[i];
        if (r.task < 0) continue;
        if (side(env->system_states[i].location) == r.target_side) {
            ++acknowledgements;
            ++acked_total;
            if (policy == "bbr") receipts.push_back(r.receipt);
            r = {};
        } else if (env->curr_task_schedule[i] != r.task) {
            // Completed/rejected assignment: cancel the outstanding commitment.
            ++cancelled_total;
            r = {};
        }
    }
    if (multicut()) {
        for (int i = 0; i < int(mcres.size()); ++i) {
            auto& r = mcres[i]; if (r.task < 0) continue;
            if (env->curr_task_schedule[i] != r.task) { for (auto& pl : r.pending) mc_count(pl, -1); r = {}; continue; }
            // Entries are in travel order. An entry is ACKed when the robot reaches its target side, but only
            // after every earlier entry on the same line has been ACKed (a delivery leg may cross a line back).
            std::vector<char> waiting(lines.size(), 0);
            for (size_t k = 0; k < r.pending.size();) {
                const int li = r.pending[k].first; auto& L = lines[li];
                if (!waiting[li] && lside(L, env->system_states[i].location) == (r.pending[k].second & 1)) { mc_count(r.pending[k], -1); ++L.acks; r.pending.erase(r.pending.begin() + k); }
                else { waiting[li] = 1; ++k; }
            }
            if (r.pending.empty()) r = {};
        }
        if (rp_off > 0 && !rp_of.empty()) {
            std::fill(rp_occ.begin(), rp_occ.end(), 0);
            for (const auto& st : env->system_states) { const int r = rp_of[st.location]; if (r >= 0) ++rp_occ[r]; }
            for (size_t r = 0; r < rp_occ.size(); ++r) {
                const double dens = double(rp_occ[r]) / std::max(1, rp_cells[r]);
                if (!rp_paused[r] && dens > rp_off) { rp_paused[r] = 1; ++rp_pause_events; }
                else if (rp_paused[r] && dens < rp_on) rp_paused[r] = 0;
            }
        }
        if (ra_pen > 0 && !ra_of.empty()) {
            std::fill(ra_occ.begin(), ra_occ.end(), 0);
            for (const auto& st : env->system_states) { const int r = ra_of[st.location]; if (r >= 0) ++ra_occ[r]; }
            for (size_t r = 0; r < ra_occ.size(); ++r) ra_hot[r] = ra_occ[r] > ra_th * ra_cells[r];
        }
        if (rg_cap > 0 && !rg_capv.empty()) {
            std::fill(rg_load.begin(), rg_load.end(), 0);
            for (int i = 0; i < int(env->system_states.size()); ++i) {
                const int loc = env->system_states[i].location; const int ri = rg_of[loc]; rg_counted[i] = -1;
                if (ri >= 0) ++rg_load[ri];
                auto it = env->task_pool.find(env->curr_task_schedule[i]);
                if (it == env->task_pool.end() || it->second.locations.empty()) continue;
                const auto& L = it->second.locations; const int g = L[std::min<int>(it->second.idx_next_loc, int(L.size()) - 1)];
                const int rgi = rg_of[g];
                if (rgi >= 0 && rgi != ri) { ++rg_load[rgi]; rg_counted[i] = rgi; }
            }
        }
        if (mc_credit > 0) for (size_t li = 0; li < lines.size(); ++li) {
            std::fill(zocc[li].begin(), zocc[li].end(), 0);
            for (const auto& st : env->system_states) { const int z = zone_of[li][st.location]; if (z >= 0) ++zocc[li][z]; }
        }
        const int per = std::max(12, 8 * env->max_counter);
        if (env->system_timestep - last_update >= per) {
            std::lock_guard<std::mutex> lock(feedback_mutex);
            for (auto& L : lines) {
                const double f = L.opp > 0 ? double(L.marks) / L.opp : 0; L.lastFrac = f;
                if (L.opp > 0 && f >= 0.2) g_door_seen = true;
                if (L.opp > 0) L.alpha = .875 * L.alpha + .125 * f;
                if (mc_gate > 0) L.active = L.alpha >= mc_gate;
                if (mc_adaptive) {
                    if (L.opp > 0 && f > .10) L.window = std::max(mc_floor, L.window * (1.0 - L.alpha / 2.0));
                    else if (L.acks > 0 && L.denied > 0) L.window = std::min(double(env->num_of_agents), L.window + 1.0);
                }
                L.opp = L.marks = 0; L.acks = L.denied = 0;
            }
            last_update = env->system_timestep;
        }
        return;
    }
    if (policy == "bbr") {
        bbr.ack_batch(env->system_timestep, receipts);
        bbr.advance(env->system_timestep, inflight(), denied > 0);
        window = bbr.window();
    }
    int period = std::max(12, 8 * env->max_counter);
    if (env->system_timestep - last_update < period) return;
    long long samples, blocked;
    {
        std::lock_guard<std::mutex> lock(feedback_mutex);
        samples = opportunities; blocked = marks;
        opportunities = marks = 0;
    }
    double fraction = samples > 0 ? double(blocked) / samples : 0;
    last_fraction = fraction;
    if (samples > 0) alpha = .875 * alpha + .125 * fraction;
    if (policy == "adaptive") {
        // DCTCP-inspired sampled feedback; NOT DCTCP's networking guarantees.
        if (samples > 0 && fraction > .10)
            window = std::max(floor_w, window * (1.0 - alpha / 2.0));
        else if (acknowledgements > 0 && denied > 0)
            window = std::min(double(env->num_of_agents), window + 1.0);
    }
    last_update = env->system_timestep;
    acknowledgements = denied = 0;
}

bool allowed(int agent, int task, SharedEnvironment* env) {
    if (!LinkCredit::allowed(agent, task, env)) { ++denied; return false; }
    if ((br_K > 0 || br_K2 > 0) && !br_side.empty() && !LinkCredit::replaces_cuts()) {
        const auto& T = env->task_pool.at(task);
        br_route(env->system_states.at(agent).location, T.locations, T.idx_next_loc, br_tmp);
        for (auto& bs : br_tmp) { if (rg_dry && rg_first >= 0 && bs.first >= rg_first) continue;
            if (rg_cuts_on == 5 && rg_first >= 0 && bs.first >= rg_first && (bs.first - rg_first >= int(g5_on.size()) || !g5_on[bs.first - rg_first])) continue;   // v45: gate off
            if (rg_bbr && rg_first >= 0 && bs.first >= rg_first) {   // v36: BBR cap on the region-graph cuts
                const int j = bs.first - rg_first;
                if (j < int(bb_cap.size()) && bb_cap[j][bs.second] > 0 && br_load[bs.first][bs.second] + 1 > bb_cap[j][bs.second]) { ++bb_denied; ++br_denied; ++denied; return false; }
                continue; }
            const int K = (net_on && bs.first < int(br_Ks.size())) ? br_Ks[bs.first][bs.second] : (bs.first < int(br_Kb.size()) ? br_Kb[bs.first] : br_K); if (K > 0 && br_load[bs.first][bs.second] + 1 > K) { ++br_denied; ++denied; if (!c2_K.empty() && bs.first >= br_n1) ++c2_deny[bs.first - br_n1]; return false; } }
    }
    if (multicut() && rp_off > 0 && !rp_of.empty()) {
        const auto& L = env->task_pool.at(task).locations;
        if (!L.empty()) {
            const int rr = rp_of[env->system_states.at(agent).location], rpk = rp_of[L.front()], rd = rp_of[L.back()];
            if (rpk >= 0 && rpk != rr && rp_paused[rpk]) { ++denied; return false; }
            if (rd >= 0 && rd != rpk && rd != rr && rp_paused[rd]) { ++denied; return false; }
        }
    }
    if (multicut()) {
        if (rg_cap > 0 && !rg_capv.empty()) {
            const auto& L = env->task_pool.at(task).locations;
            if (!L.empty()) {
                const int rr = rg_of[env->system_states.at(agent).location], rp = rg_of[L.front()], rd = rg_of[L.back()];
                if (rp >= 0 && rp != rr && rg_load[rp] + 1 > rg_capv[rp]) { ++rg_denied; ++denied; return false; }
                if (rd >= 0 && rd != rp && rd != rr && rg_load[rd] + 1 > rg_capv[rd]) { ++rg_denied; ++denied; return false; }
            }
        }
        mc_crossings(agent, task, env, mc_tmp);
        for (auto& pl : mc_tmp) if (mc_full(pl)) { ++lines[pl.first].denied; ++denied; return false; }
        return true;
    }
    if (policy == "baseline" || !crosses(agent, task, env)) return true;
    cross_candidate_seen = true;
    if (policy == "bbr") {
        bbr.demand_observed();
        if (bbr.can_send(inflight())) return true;
        ++denied;
        if (bbr.tokens() < 1.0 - 1e-9) ++pacing_denied_total;
        return false;
    }
    if (inflight() < int(std::floor(window))) return true;
    ++denied;
    return false;
}

int crossing_count(int agent, int task, SharedEnvironment* env) {
    if (!multicut()) return 0;
    mc_crossings(agent, task, env, mc_tmp); return int(mc_tmp.size());
}

void release(int agent) {
    LinkCredit::release(agent);
    if ((br_K > 0 || br_K2 > 0) && !br_side.empty() && !LinkCredit::replaces_cuts()) br_uncount(agent);
    if (rg_cap > 0 && agent < int(rg_counted.size()) && rg_counted[agent] >= 0) { --rg_load[rg_counted[agent]]; rg_counted[agent] = -1; }
    if (multicut()) { auto& r = mcres[agent]; for (auto& pl : r.pending) mc_count(pl, -1); r = {}; return; }
    if (agent < int(reservations.size()) && reservations[agent].task >= 0) { ++cancelled_total; reservations[agent] = {}; }
}

void assigned(int agent, int task, SharedEnvironment* env) {
    LinkCredit::assigned(agent, task, env);
    if ((br_K > 0 || br_K2 > 0) && !br_side.empty() && !LinkCredit::replaces_cuts()) {
        br_uncount(agent); const auto& T = env->task_pool.at(task);
        br_route(env->system_states.at(agent).location, T.locations, T.idx_next_loc, br_tmp);
        if (!br_tmp.empty()) ++br_admitted; br_count(agent);
    }
    if (multicut() && rg_cap > 0 && !rg_capv.empty()) {
        if (rg_counted[agent] >= 0) { --rg_load[rg_counted[agent]]; rg_counted[agent] = -1; }
        const auto& L = env->task_pool.at(task).locations;
        if (!L.empty()) {
            const int rr = rg_of[env->system_states.at(agent).location], rp = rg_of[L.front()];
            if (rp >= 0 && rp != rr) { ++rg_load[rp]; rg_counted[agent] = rp; }
        }
    }
    if (multicut()) {
        auto& r = mcres[agent]; for (auto& pl : r.pending) mc_count(pl, -1); r = {};
        mc_crossings(agent, task, env, mc_tmp);
        if (!mc_tmp.empty()) { r.task = task; r.pending = mc_tmp; for (auto& pl : mc_tmp) { mc_count(pl, +1); ++lines[pl.first].admitted; } ++admitted_total; }
        return;
    }
    // Measure baseline commitments too, but do not constrain its assignments.
    if (crosses(agent, task, env)) {
        BbrReceipt receipt;
        if (policy == "bbr") receipt = bbr.sent(env->system_timestep, inflight());
        if (reservations[agent].task >= 0) ++cancelled_total;
        reservations[agent] = {task, side(env->task_pool.at(task).locations.front()), receipt};
        ++admitted_total;
    }
}

void end_schedule(SharedEnvironment* env) {
    if (policy == "bbr") bbr.end_schedule(cross_candidate_seen, inflight());
    if (!telemetry || env->system_timestep == last_logged) return;
    last_logged = env->system_timestep;
    nlohmann::json j;
    j["t"] = env->system_timestep;
    j["policy"] = policy;
    j["globalBlocked"] = g_alpha;
    j["gate"] = {{"axis", axis == 0 ? "x" : "y"}, {"coordinate", cut}, {"edges", boundary_edges}};
    j["windows"] = nlohmann::json::array({{
        {"id", "region-cut"}, {"value", policy == "baseline" ? double(env->num_of_agents) : window},
        {"inFlight", inflight()}, {"alpha", alpha}, {"deniedEvaluations", denied},
        {"admittedTotal", admitted_total}, {"ackedTotal", acked_total}, {"cancelledTotal", cancelled_total},
        {"markFraction", last_fraction}
    }});
    {   // v10 fairness: unassigned tasks waiting in the pool and completed-task latency
        int unassigned = 0, max_age = 0; double sum_age = 0; int side_count[2] = {0, 0};
        for (const auto& kv : env->task_pool) {
            if (kv.second.agent_assigned >= 0) continue;
            ++unassigned; const int age = env->system_timestep - kv.second.t_revealed;
            max_age = std::max(max_age, age); sum_age += age;
            if (axis >= 0 && !kv.second.locations.empty()) ++side_count[side(kv.second.locations.front())];
        }
        std::vector<int> h = lat_hist; int p95 = 0;
        if (!h.empty()) { std::nth_element(h.begin(), h.begin() + (h.size() * 95) / 100, h.end()); p95 = h[(h.size() * 95) / 100]; }
        j["fair"] = {{"pool", int(env->task_pool.size())}, {"unassigned", unassigned}, {"maxAge", max_age},
                     {"meanAge", unassigned ? sum_age / unassigned : 0.0}, {"unassignedSide0", side_count[0]}, {"unassignedSide1", side_count[1]},
                     {"doneCount", lat_n}, {"latMean", lat_n ? lat_sum / lat_n : 0.0}, {"latP95", p95}, {"latMax", lat_max}};
    }
    if (multicut()) {
        nlohmann::json ls = nlohmann::json::array(); double wsum = 0;
        for (const auto& L : lines) { ls.push_back({{"axis", L.axis == 0 ? "x" : "y"}, {"cut", L.cut}, {"edges", L.edges}, {"window", L.window}, {"inflight", L.inflight}, {"admitted", L.admitted}, {"markFraction", L.lastFrac}, {"alpha", L.alpha}, {"active", L.active}}); wsum += L.window; }
        j["lines"] = ls; j["windows"][0]["value"] = lines.empty() ? 0.0 : wsum / lines.size(); j["windows"][0]["deniedEvaluations"] = denied;
    }
    if (policy == "bbr") {
        auto& w = j["windows"][0];
        w["bandwidth"] = bbr.bandwidth(); w["minRtt"] = bbr.min_latency();
        w["pacingRate"] = bbr.pacing_rate(); w["phase"] = bbr.phase();
        w["tokens"] = bbr.tokens(); w["lastRateSample"] = bbr.last_sample();
        w["deliveredTotal"] = bbr.delivered(); w["appLimited"] = bbr.app_limited();
        w["pacingDeniedTotal"] = pacing_denied_total;
    }
    telemetry << j.dump() << '\n';
    telemetry.flush();
}

void observe(const SharedEnvironment* env, const std::vector<ExecutionCommand>& commands) {
    std::lock_guard<std::mutex> lock(feedback_mutex);
    if (env->system_timestep > g_last_obs) {
        g_last_obs = env->system_timestep;
        for (int i = 0; i < int(env->system_states.size()); ++i) {
            const auto& s = env->system_states[i];
            if (s.delay.inDelay || s.counter.count != 0 || env->staged_actions[i].empty() || env->staged_actions[i].front() != Action::FW) continue;
            ++g_opp; g_marks += commands[i] == ExecutionCommand::STOP;
        }
    }
    if (multicut() && env->system_timestep > last_observed) {
        for (int i = 0; i < int(env->system_states.size()); ++i) {
            const auto& s = env->system_states[i];
            if (s.delay.inDelay || s.counter.count != 0 || env->staged_actions[i].empty() || env->staged_actions[i].front() != Action::FW) continue;
            for (auto& L : lines) {
                const int coord = L.axis == 0 ? s.location % cols : s.location / cols;
                if (std::abs(coord - L.cut) > 2) continue;
                ++L.opp; L.marks += commands[i] == ExecutionCommand::STOP;
            }
        }
    }
    if (axis < 0 || env->system_timestep <= last_observed) return;
    last_observed = env->system_timestep;
    // Mark only forward intentions close to the cut that the unchanged TPG
    // executor stops. Exclude own delay and partially executing actions.
    for (int i = 0; i < int(env->system_states.size()); ++i) {
        const auto& s = env->system_states[i];
        int coord = axis == 0 ? s.location % cols : s.location / cols;
        if (std::abs(coord - cut) > 2 || s.delay.inDelay || s.counter.count != 0 ||
            env->staged_actions[i].empty() || env->staged_actions[i].front() != Action::FW) continue;
        ++opportunities;
        marks += commands[i] == ExecutionCommand::STOP;
    }
}
}
