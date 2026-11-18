// v41 (round 59): ROBOT_ADMIT_AUTO=1 -- the global admission ratio is computed by the program from the map at start, instead of
// being passed in as ROBOT_ACTIVE_CAP by a Python preprocessing step (r47_common.little / lcap_env):
//   r = beta * lambda * alpha * (T1 + T2) / N   (Little's law on the max-concurrent-flow throughput lambda; round 47)
//   the cap is r when r < 1, otherwise no cap (round 58: this alone reproduces the old hand-set switches on all 39 instances).
// Region network: the same rule as netmodel_r40/regiongraph.py (narrow cells = free cells whose horizontal or vertical free run is
// <= 2; rooms = 4-connected components of the other free cells; a 4-connected group of narrow cells touching exactly two rooms is a
// door, touching one room is a niche merged into it; width = cells across the passing direction). Demand between rooms s != t is
// w_s * w_t (w = room size share; pickups and deliveries uniform over room cells). Door capacity (both directions together):
// width 1 -> c1 = 26/500, wider -> c2 = 32/500 per tick (round 40). lambda by Garg-Koenemann / Fleischer phases (epsilon 0.01; each source routes along its shortest-path tree), scaled down by the
// largest edge congestion so that it is a feasible (lower-bound) value. T2 = mean oriented free-flow time between two free cells
// (a move or a 90-degree turn costs 3 ticks), exact over up to 200 evenly spaced sources and all targets.
#include "Types.h"
#include <vector>
#include <queue>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <algorithm>
#include <climits>
#include <string>
#include <chrono>
namespace AdmitAuto {
static double envd(const char* k, double d) { const char* e = std::getenv(k); return e ? std::atof(e) : d; }
struct Result { bool done = false; double lambda = 0, T2 = 0, r = 1e9, cap = 0; int rooms = 0, doors = 0; };
static Result R;
static bool g_force = false;   // v44 (round 67): solve the flow problem even when the cap would stay off (exact lambda wanted)

static void compute(SharedEnvironment* env) {
    const auto t_start = std::chrono::steady_clock::now();
    auto el = [&]() { return std::chrono::duration<double>(std::chrono::steady_clock::now() - t_start).count(); };
    const bool tr = std::getenv("ROBOT_ADMIT_TRACE") != nullptr;
    const int H = env->rows, W = env->cols, n = H * W;
    auto fr = [&](int y, int x) { return y >= 0 && y < H && x >= 0 && x < W && env->map[y * W + x] == 0; };
    std::vector<int> hr(n, 0), vr(n, 0);
    for (int y = 0; y < H; ++y) for (int x = 0; x < W;) { if (!fr(y, x)) { ++x; continue; } int e = x; while (e < W && fr(y, e)) ++e; for (int k = x; k < e; ++k) hr[y * W + k] = e - x; x = e; }
    for (int x = 0; x < W; ++x) for (int y = 0; y < H;) { if (!fr(y, x)) { ++y; continue; } int e = y; while (e < H && fr(e, x)) ++e; for (int k = y; k < e; ++k) vr[k * W + x] = e - y; y = e; }
    std::vector<char> narrow(n, 0);
    for (int v = 0; v < n; ++v) if (env->map[v] == 0 && (hr[v] <= 2 || vr[v] <= 2)) narrow[v] = 1;
    const int DY[4] = {1, -1, 0, 0}, DX[4] = {0, 0, 1, -1};
    std::vector<int> room(n, -1); int nr = 0;
    for (int v = 0; v < n; ++v) if (env->map[v] == 0 && !narrow[v] && room[v] < 0) {
        std::vector<int> q{v}; room[v] = nr;
        for (size_t h = 0; h < q.size(); ++h) { int y = q[h] / W, x = q[h] % W; for (int d = 0; d < 4; ++d) { int yy = y + DY[d], xx = x + DX[d]; if (!fr(yy, xx)) continue; int u = yy * W + xx; if (!narrow[u] && room[u] < 0) { room[u] = nr; q.push_back(u); } } }
        ++nr; }
    std::vector<long long> size(nr, 0); for (int v = 0; v < n; ++v) if (room[v] >= 0) ++size[room[v]];
    struct Door { int a, b, width; }; std::vector<Door> D;
    std::vector<int> grp(n, -1);
    for (int v = 0; v < n; ++v) if (narrow[v] && grp[v] < 0) {
        std::vector<int> q{v}; grp[v] = 1;
        for (size_t h = 0; h < q.size(); ++h) { int y = q[h] / W, x = q[h] % W; for (int d = 0; d < 4; ++d) { int yy = y + DY[d], xx = x + DX[d]; if (!fr(yy, xx)) continue; int u = yy * W + xx; if (narrow[u] && grp[u] < 0) { grp[u] = 1; q.push_back(u); } } }
        std::vector<int> touch;
        for (int c : q) { int y = c / W, x = c % W; for (int d = 0; d < 4; ++d) { int yy = y + DY[d], xx = x + DX[d]; if (!fr(yy, xx)) continue; int u = yy * W + xx; if (room[u] >= 0 && std::find(touch.begin(), touch.end(), room[u]) == touch.end()) touch.push_back(room[u]); } }
        if (touch.size() == 2) {
            bool up = false, dn = false; int y0 = INT_MAX, y1 = -1, x0 = INT_MAX, x1 = -1;
            for (int c : q) { int y = c / W, x = c % W; y0 = std::min(y0, y); y1 = std::max(y1, y); x0 = std::min(x0, x); x1 = std::max(x1, x);
                if (fr(y - 1, x) && room[(y - 1) * W + x] >= 0) up = true; if (fr(y + 1, x) && room[(y + 1) * W + x] >= 0) dn = true; }
            const bool vert = up && dn; D.push_back({std::min(touch[0], touch[1]), std::max(touch[0], touch[1]), vert ? x1 - x0 + 1 : y1 - y0 + 1});
        } else if (touch.size() == 1) size[touch[0]] += (long long)q.size();   // niche merged into its room
    }
    R.rooms = nr; R.doors = int(D.size());
    if (tr) std::fprintf(stderr, "[admit] region network %.2fs: %d rooms, %zu doors\n", el(), nr, D.size());
    // ---- T2: mean oriented free-flow time between free cells ----
    std::vector<int> cells; for (int v = 0; v < n; ++v) if (env->map[v] == 0) cells.push_back(v);
    const int nsrc = std::min<int>(200, cells.size()); double sum = 0; long long cnt = 0;
    const int DR[4] = {1, W, -1, -W};
    for (int k = 0; k < nsrc; ++k) {
        const int s = cells[(size_t(k) * cells.size()) / nsrc];
        std::vector<int> dd(4 * n, INT_MAX); using Q = std::pair<int,int>; std::priority_queue<Q, std::vector<Q>, std::greater<Q>> pq;
        for (int o = 0; o < 4; ++o) { dd[4 * s + o] = 0; pq.push({0, 4 * s + o}); }
        while (!pq.empty()) { auto [d, st] = pq.top(); pq.pop(); if (d != dd[st]) continue; const int v = st / 4, o = st % 4;
            for (int no : {(o + 1) % 4, (o + 3) % 4}) if (d + 3 < dd[4 * v + no]) { dd[4 * v + no] = d + 3; pq.push({d + 3, 4 * v + no}); }
            const int u = v + DR[o]; const bool ok = u >= 0 && u < n && env->map[u] == 0 && (o == 1 || o == 3 || u / W == v / W);
            if (ok && d + 3 < dd[4 * u + o]) { dd[4 * u + o] = d + 3; pq.push({d + 3, 4 * u + o}); } }
        for (int t : cells) { int b = INT_MAX; for (int o = 0; o < 4; ++o) b = std::min(b, dd[4 * t + o]); if (b < INT_MAX) { sum += b; ++cnt; } }
    }
    R.T2 = cnt ? sum / cnt : 0;
    if (tr) std::fprintf(stderr, "[admit] T2 %.2fs\n", el());
    const double beta = envd("ROBOT_ADMIT_BETA", 1.76), alpha = envd("ROBOT_ADMIT_ALPHA", 2.23), T1 = envd("ROBOT_ADMIT_T1", 25.0);
    const int N = env->num_of_agents;
    // ---- maximum concurrent flow (Garg-Koenemann), undirected door edges, commodities (s, t), s != t, demand w_s w_t ----
    const double c1 = envd("ROBOT_ADMIT_C1", 26.0 / 500), c2 = envd("ROBOT_ADMIT_C2", 32.0 / 500), eps = envd("ROBOT_ADMIT_EPS", 0.01);
    long long A = 0; for (auto s : size) A += s;
    std::vector<double> w(nr); for (int i = 0; i < nr; ++i) w[i] = double(size[i]) / double(A);
    const int m = int(D.size()); std::vector<double> cap(m); for (int e = 0; e < m; ++e) cap[e] = D[e].width <= 1 ? c1 : c2;
    std::vector<std::vector<std::pair<int,int>>> adj(nr); for (int e = 0; e < m; ++e) { adj[D[e].a].push_back({D[e].b, e}); adj[D[e].b].push_back({D[e].a, e}); }
    double lambda = 0;
    if (nr >= 2 && m > 0) {
        // connected? (otherwise lambda = 0)
        std::vector<int> seen(nr, 0); std::vector<int> q{0}; seen[0] = 1; for (size_t h = 0; h < q.size(); ++h) for (auto& pe : adj[q[h]]) if (!seen[pe.first]) { seen[pe.first] = 1; q.push_back(pe.first); }
        if (int(q.size()) == nr) {
            // scale demands with a single-path estimate so that the optimum is about 1 or more
            std::vector<double> len(m), fl(m, 0.0);
            std::vector<int> settled; std::vector<char> done_(nr);
            auto sp = [&](int s, std::vector<double>& dist, std::vector<int>& pe) {   // settled = the order nodes leave the queue (parents first)
                dist.assign(nr, 1e300); pe.assign(nr, -1); dist[s] = 0; settled.clear(); std::fill(done_.begin(), done_.end(), 0);
                using P = std::pair<double,int>; std::priority_queue<P, std::vector<P>, std::greater<P>> pq; pq.push({0, s});
                while (!pq.empty()) { auto [d, v] = pq.top(); pq.pop(); if (done_[v] || d > dist[v]) continue; done_[v] = 1; settled.push_back(v); for (auto& x : adj[v]) { double nd = d + len[x.second]; if (nd < dist[x.first]) { dist[x.first] = nd; pe[x.first] = x.second; pq.push({nd, x.first}); } } } };
            std::vector<double> dist; std::vector<int> pe;
            for (int e = 0; e < m; ++e) len[e] = 1.0;
            std::vector<double> load(m, 0.0);
            for (int s = 0; s < nr; ++s) { sp(s, dist, pe); for (int t = 0; t < nr; ++t) if (t != s) { int v = t; while (v != s) { int e = pe[v]; load[e] += w[s] * w[t]; v = D[e].a == v ? D[e].b : D[e].a; } } }
            double cong0 = 0; for (int e = 0; e < m; ++e) cong0 = std::max(cong0, load[e] / cap[e]);
            // Garg-Koenemann / Fleischer phases with accuracy e on demands * sc; returns the feasible concurrent ratio (lower bound)
            auto gk = [&](double e, double sc, int maxph, int& phases) {
                const double delta = (1 + e) / std::pow((1 + e) * m, 1.0 / e);
                for (int k = 0; k < m; ++k) { len[k] = delta / cap[k]; fl[k] = 0; }
                std::vector<double> routed(nr * nr, 0.0);
                auto Dl = [&]() { double s = 0; for (int k = 0; k < m; ++k) s += cap[k] * len[k]; return s; };
                phases = 0;
                std::vector<double> sub(nr);
                while (Dl() < 1 && phases < maxph) {        // one phase: every source routes all its demands along its shortest-path tree
                    for (int s = 0; s < nr && Dl() < 1; ++s) {
                        sp(s, dist, pe);
                        for (int v = 0; v < nr; ++v) sub[v] = v == s ? 0.0 : w[s] * w[v] * sc;
                        // children before parents: reverse settle order (sorting by distance fails when lengths are tiny and ties appear)
                        for (auto it = settled.rbegin(); it != settled.rend(); ++it) { const int v = *it; if (v == s) continue; const int k = pe[v]; const int par = D[k].a == v ? D[k].b : D[k].a;   // flow on the tree edge = demand of the subtree
                            fl[k] += sub[v]; len[k] *= (1 + e * sub[v] / cap[k]); sub[par] += sub[v]; }
                        for (int t = 0; t < nr; ++t) if (t != s) routed[s * nr + t] += w[s] * w[t] * sc; }
                    ++phases; }
                double cong = 0; for (int k = 0; k < m; ++k) cong = std::max(cong, fl[k] / cap[k]);
                double mn = 1e300; for (int s = 0; s < nr; ++s) for (int t = 0; t < nr; ++t) if (t != s && w[s] * w[t] > 0) mn = std::min(mn, routed[s * nr + t] / (w[s] * w[t] * sc));
                return cong > 0 ? mn / cong * sc : 0.0; };
            int ph1 = 0, ph2 = 0;
            if (tr) std::fprintf(stderr, "[admit] hop routing %.2fs\n", el());
            // routing every demand on a fewest-doors path is itself a feasible flow: lambda >= 1 / cong0. If r computed with that lower
            // bound is already >= 1 the cap stays off, and the flow problem need not be solved (large maps: warehouse, maze, random).
            const double r_hop = N > 0 ? beta * (1.0 / cong0) * alpha * (T1 + R.T2) / N : 1e9;
            if (r_hop >= 1 && !g_force) { lambda = 1.0 / cong0; if (tr) std::fprintf(stderr, "[admit] r with the fewest-doors flow %.3f >= 1: no cap, lambda printed is that lower bound\n", r_hop); }
            else {
            const double lam0 = gk(0.1, 1.0 / cong0, 100000, ph1);
            if (tr) std::fprintf(stderr, "[admit] coarse pass %.2fs (%d phases)\n", el(), ph1);            // coarse pass: a feasible flow, so lam0 <= lambda
            lambda = lam0;
            // the fine pass only matters when the cap could switch on: r computed with the lower bound lam0 is already >= 1 -> no cap
            // lam0 is a feasible flow, so lambda >= lam0 and r >= r0: if r0 >= 1 the cap stays off whatever the fine pass gives
            const double r0 = N > 0 ? beta * lam0 * alpha * (T1 + R.T2) / N : 1e9;
            if (lam0 > 0 && (r0 < 1 || g_force)) lambda = std::max(lam0, gk(eps, lam0, int(envd("ROBOT_ADMIT_MAXPHASE", 200000)), ph2));
            if (std::getenv("ROBOT_ADMIT_TRACE")) std::fprintf(stderr, "[admit] gk phases %d + %d, coarse lambda %.6f\n", ph1, ph2, lam0);
            }
        }
    }
    R.lambda = lambda;
    R.r = N > 0 ? beta * lambda * alpha * (T1 + R.T2) / N : 1e9;
    if (lambda <= 0) R.r = 1e9;                     // no room network -> no cap
    R.cap = R.r < 1 ? R.r : 0;
    R.done = true;
    if (std::getenv("ROBOT_ADMIT_TRACE")) std::fprintf(stderr, "[admit] rooms %d doors %d lambda %.6f T2 %.2f N %d r %.4f cap %.4f\n", R.rooms, R.doors, R.lambda, R.T2, N, R.r, R.cap);
}
bool enabled() { const char* e = std::getenv("ROBOT_ADMIT_AUTO"); return e && std::string(e) == "1"; }
double ratio(SharedEnvironment* env) { if (!R.done) compute(env); return R.cap; }
// v44 (round 67): the maximum-concurrent-flow throughput lambda* (per tick) of the room network, solved in full (the shortcut that
// skips the flow problem when the cap stays off is not taken). Recomputing only raises lambda above the shortcut's lower bound,
// so the admission cap (off when r >= 1) cannot change.
double lambda_star(SharedEnvironment* env) { if (!R.done || !g_force) { g_force = true; R.done = false; compute(env); } return R.lambda; }
}
