#include <cmath>
// v15: re-implementation of the LoRR 2024 winning task scheduler (team "No Man's Sky"); see nms_scheduler.h.
#include "nms_scheduler.h"
#include "netmac.h"
#include <cstdio>
#include "window_control.h"
namespace AdmitAuto { bool enabled(); double ratio(SharedEnvironment* env); }
#include <algorithm>
#include <cstdlib>
#include <cstring>
#include <deque>
#include <queue>
#include <tuple>
#include <unordered_map>
#include <limits>

namespace NmsScheduler {
namespace {
int mode = -1;            // -1 unread, 0 off, 1 on
long long weight = 5;     // ROBOT_NMS_W
bool change_task = true;  // ROBOT_NMS_REASSIGN (1 = robots may swap tasks they have not opened yet, as in the original)
// placebo control (ROBOT_NMS_PLACEBO=q): a candidate pair whose pickup leg crosses a door line is refused with probability q,
// without looking at congestion or downstream space (same targets as method E, no information)
double placebo_q = 0; unsigned long long placebo_seed = 1;
// v15c exploration: soft door pricing inside the matching cost. Every congested (active) door line crossed costs xcost cells,
// on the pickup leg; with xcost_all also on every leg of the task (pickup -> ... -> last errand).
long long xcost = 0; bool xcost_all = false;
// v16 (round 26): ROBOT_NMS_OPT=1 replaces the greedy matching by an optimal assignment (Hungarian algorithm, minimum total
// cost) on exactly the same costs; door-line admission is not applied in this mode.
bool opt = false;
// v16: ROBOT_NMS_DELAYCOST=D adds W*D to every pair of a robot that is currently in an execution delay, so unopened tasks
// move to robots that can actually go (a node reported down is avoided), and a stuck robot keeps a task only if nobody is better.
long long delaycost = 0;
// p26 (TE, SWAN/B4 strict priority classes): ROBOT_TE_PRIO=W -- a pair whose robot, pickup and delivery all lie on one side of
// every single-lane cut (the task never uses the bottleneck) and whose task was revealed >= W ticks ago is matched before every
// other pair; inside the class the original cost order is kept. ROBOT_TE_PRIO_LOG=<file> writes how many such pairs were matched.
int te_w = 0; const char* te_log = nullptr; long long te_matched = 0, te_pairs = 0, te_plans = 0;
const long long TE_BIG = 1000000000000LL;
int te_nb = -1;   // p26b: number of single-lane cuts, read once (bridge_count re-runs detection on every call when a map has none)
bool te_local(SharedEnvironment* env, int loc, const std::vector<int>& L, int from) {
    if (te_nb < 0) te_nb = RobotWindow::bridge_count(env);
    const int nb = te_nb;
    if (nb <= 0) return false;
    for (int b = 0; b < nb; ++b) {
        const int s0 = RobotWindow::bridge_side(b, loc);
        if (s0 < 0) return false;
        for (size_t i = size_t(from); i < L.size(); ++i) if (RobotWindow::bridge_side(b, L[i]) != s0) return false;
    }
    return true;
}

// rectangular assignment, n rows <= m columns, minimise sum of a[i][ans[i]] (e-maxx Hungarian with potentials), 1-based
std::vector<int> hungarian(const std::vector<std::vector<long long>>& a, int n, int m) {
    const long long INF = std::numeric_limits<long long>::max() / 4;
    std::vector<long long> u(n + 1), v(m + 1); std::vector<int> p(m + 1), way(m + 1);
    for (int i = 1; i <= n; ++i) {
        p[0] = i; int j0 = 0; std::vector<long long> minv(m + 1, INF); std::vector<char> used(m + 1, 0);
        do {
            used[j0] = 1; int i0 = p[j0], j1 = 0; long long delta = INF;
            for (int j = 1; j <= m; ++j) if (!used[j]) {
                const long long cur = a[i0 - 1][j - 1] - u[i0] - v[j];
                if (cur < minv[j]) { minv[j] = cur; way[j] = j0; }
                if (minv[j] < delta) { delta = minv[j]; j1 = j; }
            }
            for (int j = 0; j <= m; ++j) if (used[j]) { u[p[j]] += delta; v[j] -= delta; } else minv[j] -= delta;
            j0 = j1;
        } while (p[j0] != 0);
        do { const int j1 = way[j0]; p[j0] = p[j1]; j0 = j1; } while (j0);
    }
    std::vector<int> ans(n, -1);
    for (int j = 1; j <= m; ++j) if (p[j] > 0) ans[p[j] - 1] = j - 1;
    return ans;
}
std::unordered_map<int, std::vector<unsigned short>> cache;   // target cell -> distance from every (cell, orientation)
const unsigned short UNREACH = 65535;

double active_cap = 0;   // v20 ROBOT_ACTIVE_CAP: at most this fraction of the robots hold a task (WPPL-style global admission)
// v21: ROBOT_ACTIVE_CAP_GATE=1 -> the fixed cap only applies on maps where the bridge/link MAC found a single-lane passage.
// ROBOT_ACTIVE_AIMD=tau -> adaptive cap (AIMD on the number of robots allowed to hold a task), driven by the map-wide share of
// forward moves the executor had to stop (RobotWindow::global_blocked, a congestion "mark" rate): every ROBOT_AIMD_PERIOD ticks,
// share > tau -> cap *= (1 - ROBOT_AIMD_B); else cap += ROBOT_AIMD_A (fractions of the team), within [ROBOT_AIMD_MIN, 1].
double cap_sig = 0;   // v22 ROBOT_ACTIVE_CAP_SIG=tau: the fixed cap applies only while the map-wide blocked share exceeds tau
// v23: ROBOT_ACTIVE_CAP_SIG_OFF=tau_off (< tau): hysteresis; the cap switches on when the share exceeds tau and off only when it
// falls below tau_off (default tau_off = tau, i.e. the v22 behaviour)
double cap_sig_off = -1; bool cap_on = false; long long cap_switches = 0;
int cap_gate = 0; double aimd_tau = 0, aimd_a = 0.02, aimd_b = 0.1, aimd_min = 0.2; int aimd_period = 50;
double aimd_cap = 1.0; int aimd_last = -1000000; long long aimd_dec = 0, aimd_inc = 0;
// p62 ROBOT_CAP_TIGHT_W=W: MPLS-TE auto-bandwidth style -- sample completions per admitted robot over the first W ticks; if the
// rate (per 1000 ticks) is below ROBOT_CAP_TIGHT_TH, scale the cap by ROBOT_CAP_TIGHT_F (SWAN scratch capacity) for the rest of the run
int tight_w = 0; double tight_th = 0, tight_f = 0.90; int tight_id0 = -1, tight_maxid = -1; int tight_state = 0;   // 0 undecided, 1 tight, 2 keep
void read_env() {
    if (mode >= 0) return;
    if (const char* a = std::getenv("ROBOT_ACTIVE_CAP")) active_cap = std::atof(a);
    if (const char* g = std::getenv("ROBOT_ACTIVE_CAP_GATE")) cap_gate = std::atoi(g);
    if (const char* g = std::getenv("ROBOT_ACTIVE_CAP_SIG")) cap_sig = std::atof(g);
    if (const char* g = std::getenv("ROBOT_ACTIVE_CAP_SIG_OFF")) cap_sig_off = std::atof(g);
    if (const char* g = std::getenv("ROBOT_ACTIVE_AIMD")) aimd_tau = std::atof(g);
    if (const char* g = std::getenv("ROBOT_AIMD_A")) aimd_a = std::atof(g);
    if (const char* g = std::getenv("ROBOT_AIMD_B")) aimd_b = std::atof(g);
    if (const char* g = std::getenv("ROBOT_AIMD_MIN")) aimd_min = std::atof(g);
    if (const char* g = std::getenv("ROBOT_AIMD_PERIOD")) aimd_period = std::atoi(g);
    if (const char* g = std::getenv("ROBOT_CAP_TIGHT_W")) tight_w = std::atoi(g);
    if (const char* g = std::getenv("ROBOT_CAP_TIGHT_TH")) tight_th = std::atof(g);
    if (const char* g = std::getenv("ROBOT_CAP_TIGHT_F")) tight_f = std::atof(g);
    const char* s = std::getenv("ROBOT_SCHED");
    mode = (s && std::strcmp(s, "nms") == 0) ? 1 : 0;
    if (const char* w = std::getenv("ROBOT_NMS_W")) weight = std::atoll(w);
    if (const char* r = std::getenv("ROBOT_NMS_REASSIGN")) change_task = std::atoi(r) != 0;
    if (const char* q = std::getenv("ROBOT_NMS_PLACEBO")) placebo_q = std::atof(q);
    if (const char* q = std::getenv("ROBOT_NMS_PLACEBO_SEED")) placebo_seed = std::strtoull(q, nullptr, 10);
    if (const char* q = std::getenv("ROBOT_NMS_XCOST")) xcost = std::atoll(q);
    if (const char* q = std::getenv("ROBOT_NMS_XCOST_ALL")) xcost_all = std::atoi(q) != 0;
    if (const char* q = std::getenv("ROBOT_NMS_OPT")) opt = std::atoi(q) != 0;
    if (const char* q = std::getenv("ROBOT_NMS_DELAYCOST")) delaycost = std::atoll(q);
    if (const char* q = std::getenv("ROBOT_TE_PRIO")) te_w = std::atoi(q);
    te_log = std::getenv("ROBOT_TE_PRIO_LOG");
}

const std::vector<unsigned short>& table(SharedEnvironment* env, int target) {
    auto it = cache.find(target);
    if (it != cache.end()) return it->second;
    const int n = int(env->map.size()), cols = env->cols;
    std::vector<unsigned short> d(size_t(n) * 4, UNREACH);
    std::deque<int> q;
    for (int o = 0; o < 4; ++o) { d[size_t(target) * 4 + o] = 0; q.push_back(target * 4 + o); }
    while (!q.empty()) {
        const int s = q.front(); q.pop_front();
        const int v = s / 4, o = s % 4; const unsigned short nd = d[s] + 1;
        // predecessor by a forward move in orientation o: u + delta(o) = v
        int u = -1;
        if (o == 0 && v % cols != 0) u = v - 1;
        else if (o == 1 && v - cols >= 0) u = v - cols;
        else if (o == 2 && v % cols != cols - 1) u = v + 1;
        else if (o == 3 && v + cols < n) u = v + cols;
        if (u >= 0 && !env->map[u] && d[size_t(u) * 4 + o] == UNREACH) { d[size_t(u) * 4 + o] = nd; q.push_back(u * 4 + o); }
        // predecessors by a rotation: clockwise from (o+3)%4, counter-clockwise from (o+1)%4
        for (int p : {(o + 3) % 4, (o + 1) % 4})
            if (d[size_t(v) * 4 + p] == UNREACH) { d[size_t(v) * 4 + p] = nd; q.push_back(v * 4 + p); }
    }
    return cache.emplace(target, std::move(d)).first->second;
}
}

bool enabled() { read_env(); return mode == 1; }

void initialize(SharedEnvironment* env) { read_env(); cache.clear(); (void)env; }

int odist(SharedEnvironment* env, int loc, int orient, int target) {
    const unsigned short v = table(env, target)[size_t(loc) * 4 + orient];
    return v == UNREACH ? 1000000 : int(v);
}

void plan(std::vector<int>& proposed_schedule, SharedEnvironment* env) {
    read_env();
    const int na = env->num_of_agents;
    std::vector<int> free_tasks, free_robots; std::vector<int> held(na, -1);
    for (auto& kv : env->task_pool) {
        Task& t = kv.second;
        if (t.agent_assigned == -1 || (change_task && t.idx_next_loc == 0)) free_tasks.push_back(kv.first);
    }
    std::sort(free_tasks.begin(), free_tasks.end());
    for (int r = 0; r < na; ++r) {
        const int t = env->curr_task_schedule[r];
        auto it = env->task_pool.find(t);
        if (it != env->task_pool.end() && it->second.idx_next_loc != 0) continue;           // opened: cannot change
        if (it == env->task_pool.end() || (change_task && it->second.idx_next_loc == 0)) {
            free_robots.push_back(r);
            if (it != env->task_pool.end()) held[r] = t;
        }
    }
    if (free_robots.empty()) return;
    // task metric: errand-chain length, each leg measured from orientation 0 at the previous errand (as in the original)
    std::unordered_map<int, long long> metric; metric.reserve(free_tasks.size() * 2);
    for (int t : free_tasks) {
        const auto& L = env->task_pool.at(t).locations; long long m = 0;
        for (size_t i = 0; i + 1 < L.size(); ++i) {
            m += odist(env, L[i], 0, L[i + 1]);
            if (xcost > 0 && xcost_all) m += xcost * RobotWindow::line_crossings(L[i], L[i + 1]);
        }
        metric[t] = m;
    }
    // per free robot: all free tasks sorted by cost
    std::vector<std::vector<std::pair<long long,int>>> dp(free_robots.size());
    for (size_t k = 0; k < free_robots.size(); ++k) {
        const int r = free_robots[k]; const auto& st = env->curr_states[r];
        const long long extra = (delaycost > 0 && r < int(env->system_states.size()) && env->system_states[r].delay.inDelay) ? weight * delaycost : 0;
        auto& v = dp[k]; v.reserve(free_tasks.size());
        for (int t : free_tasks) {
            const int g = env->task_pool.at(t).locations[0];
            long long c = weight * odist(env, st.location, st.orientation, g) + metric[t];
            if (xcost > 0) c += weight * xcost * RobotWindow::line_crossings(st.location, g);
            if (te_w > 0) { const Task& T = env->task_pool.at(t);
                if (env->system_timestep - T.t_revealed >= te_w && te_local(env, st.location, T.locations, T.idx_next_loc)) { c -= TE_BIG; ++te_pairs; } }
            v.emplace_back(c + extra, t);
        }
        std::sort(v.begin(), v.end());
    }
    // release the free robots' current (unopened) tasks; admission bookkeeping of method E is released too
    for (int r : free_robots) { proposed_schedule[r] = -1; if (held[r] >= 0) RobotWindow::release(r); }
    if (opt && !free_tasks.empty()) {
        const int n = int(free_robots.size()), m = int(free_tasks.size());
        std::unordered_map<int,int> col; for (int j = 0; j < m; ++j) col[free_tasks[j]] = j;
        const long long BIG = 1000000000LL;
        // rows = robots; if there are more robots than tasks, dummy columns (cost BIG) leave robots unassigned
        const int cols_ = std::max(n, m);
        std::vector<std::vector<long long>> a(n, std::vector<long long>(cols_, BIG));
        for (int k = 0; k < n; ++k) for (const auto& ct : dp[k]) a[k][col[ct.second]] = ct.first;
        const auto ans = hungarian(a, n, cols_);
        for (int k = 0; k < n; ++k) {
            const int j = ans[k]; if (j < 0 || j >= m) continue;
            const int r = free_robots[k], t = free_tasks[j];
            proposed_schedule[r] = t; RobotWindow::assigned(r, t, env);
        }
        return;
    }
    std::unordered_map<int,char> used; used.reserve(free_tasks.size() * 2);
    using E = std::tuple<long long,int,int>;   // (cost, robot index k, list index)
    std::priority_queue<E, std::vector<E>, std::greater<E>> heap;
    for (size_t k = 0; k < free_robots.size(); ++k) if (!dp[k].empty()) heap.push({dp[k][0].first, int(k), 0});
    double capf = active_cap;
    const bool admit_auto = AdmitAuto::enabled();   // v41: ratio computed from the map (admit_auto.cpp); the old switches are ignored
    if (admit_auto) capf = AdmitAuto::ratio(env);
    if (!admit_auto && capf > 0 && cap_gate == 1 && DefaultPlanner::NetMac::passage_count() == 0) capf = 0;
    // v25i (round 36): ROBOT_ACTIVE_CAP_GATE=2 -- the global cap only where the map has single-lane links (doors with a long
    // detour); a map whose only bottleneck is a cut is handled by the cut's credit and MAC alone
    if (!admit_auto && capf > 0 && cap_gate == 2 && DefaultPlanner::NetMac::link_count() == 0) capf = 0;
    if (capf > 0 && cap_sig > 0) {
        const double g = RobotWindow::global_blocked();
        if (cap_sig_off < 0) cap_on = g >= cap_sig;                       // v22: no hysteresis
        else if (!cap_on && g > cap_sig) { cap_on = true; ++cap_switches; }
        else if (cap_on && g < cap_sig_off) { cap_on = false; ++cap_switches; }
        if (!cap_on) capf = 0;
    }
    if (aimd_tau > 0) {
        if (env->system_timestep - aimd_last >= aimd_period) {
            aimd_last = env->system_timestep;
            const double g = RobotWindow::global_blocked();
            if (g > aimd_tau) { aimd_cap = std::max(aimd_min, aimd_cap * (1.0 - aimd_b)); ++aimd_dec; }
            else { aimd_cap = std::min(1.0, aimd_cap + aimd_a); ++aimd_inc; }
            if (std::getenv("ROBOT_AIMD_TRACE") && env->system_timestep % 500 < aimd_period) std::fprintf(stderr, "[aimd] t=%d g=%.3f cap=%.3f\n", env->system_timestep, g, aimd_cap);
        }
        capf = capf > 0 ? std::min(capf, aimd_cap) : aimd_cap;
    }
    if (tight_w > 0 && capf > 0) {
        for (const auto& kv : env->task_pool) tight_maxid = std::max(tight_maxid, kv.first);
        if (tight_id0 < 0) tight_id0 = tight_maxid;
        if (tight_state == 0 && env->system_timestep >= tight_w) {
            const double rate = double(tight_maxid - tight_id0) / (na * capf) / env->system_timestep * 1000.0;
            tight_state = rate < tight_th ? 1 : 2;
            std::fprintf(stderr, "[cap_tight] t=%d done=%d rate=%.3f th=%.3f -> %s\n", env->system_timestep, tight_maxid - tight_id0, rate, tight_th, tight_state == 1 ? "tight" : "keep");
        }
        if (tight_state == 1) capf *= tight_f;
    }
    int budget = capf > 0 && capf < 1.0 ? int(std::floor(capf * na)) - (na - int(free_robots.size())) : na;
    while (!heap.empty()) {
        if (budget <= 0) break;
        auto [c, k, idx] = heap.top(); heap.pop(); (void)c;
        const int r = free_robots[k], t = dp[k][idx].second;
        // a task this robot already holds stays admitted; anything else must pass the door-line admission check
        bool ok = !used.count(t) && (t == held[r] || RobotWindow::allowed(r, t, env));
        if (ok && placebo_q > 0 && t != held[r] && RobotWindow::crossing_count(r, t, env) > 0) {
            unsigned long long h = placebo_seed * 0x9E3779B97F4A7C15ull ^ (unsigned long long)(env->system_timestep) << 20 ^ (unsigned long long)r << 40 ^ (unsigned long long)t;
            h ^= h >> 33; h *= 0xff51afd7ed558ccdull; h ^= h >> 33; h *= 0xc4ceb9fe1a85ec53ull; h ^= h >> 33;
            if (double(h >> 11) / double(1ull << 53) < placebo_q) ok = false;
        }
        if (!ok) { if (idx + 1 < int(dp[k].size())) heap.push({dp[k][idx + 1].first, k, idx + 1}); continue; }
        used[t] = 1; proposed_schedule[r] = t; RobotWindow::assigned(r, t, env); --budget;
        if (c < 0 && t != held[r]) ++te_matched;
    }
    if (te_log && ++te_plans % 50 == 0) if (std::FILE* f = std::fopen(te_log, "w")) {
        std::fprintf(f, "{\"t\": %d, \"w\": %d, \"plans\": %lld, \"prio_pairs\": %lld, \"prio_matched\": %lld}\n", env->system_timestep, te_w, te_plans, te_pairs, te_matched);
        std::fclose(f); }
}
}
