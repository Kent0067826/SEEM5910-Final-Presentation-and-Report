// v30 (round 43): ROBOT_LINK=1 -- a bandwidth-delay credit on EVERY room-to-room link, not only on the cuts.
//
// The map is decomposed exactly like the round-40 region graph (netmodel_r40/regiongraph.py): a free cell is "narrow" when its
// horizontal or vertical run of free cells is at most 2; the connected non-narrow cells are rooms; a connected group of narrow
// cells touching exactly two rooms is a door (touching one room: a niche, merged into that room). All doors between the same
// two rooms form one link (parallel doors share the traffic: the planner's guide paths already balance them, round 42).
//
// Each link and direction gets the same credit formula as the cuts (ROBOT_NET, round 41):
//   K = ceil(alpha * T * C / 2),  C = sum over its doors of the measured effective bandwidth (1-cell 26, 2-cell 32 per 500 ticks)
//   T = leg1 + mean free-flow time from the origin cell to the link's door, over all (origin, destination) cell pairs whose
//       room route crosses the link in that direction (uniform origins and destinations, as in the round-41 flow matrix).
//       For a cut this is the cut formula's T_free (every origin on the other side crosses it).
// Room routes: shortest paths over the door graph with free-flow times (turns included). A robot's in-flight links are the
// links its remaining route (current cell -> next task location -> ... -> last location) crosses, each counted once.
// A task is not assigned while it would push any link/direction over its credit (same rule as the cut credit).
// Gate: like ROBOT_ACTIVE_CAP_GATE=2, the link credit is used only on maps where the door MAC manages a single-lane link.
//
// v31 (round 44): ROBOT_LINK_MEAS=1 -- the delay of every link and direction is MEASURED while running instead of alpha x T_free
// (round 43 showed the map-wide alpha = 2.23 is far too small on some single-door links). Like TCP, which measures the round-trip
// time of every connection, each robot records once per task the time from its assignment to its arrival in the approach area of
// a link on its route (cells within 3 of the door, on the side it comes from; the same area as the round-40 measurement). The
// queue at the door is NOT included (it is what the window must prevent; BBR likewise uses the minimum RTT, not the current one).
// Delay = (model value + sum of samples) / (1 + number of samples): the model value counts as one observation until data arrive.
// ROBOT_LINK_ONLY=1: where the link credit is active it replaces the cut credit (a cut is itself a link), so the credits no longer
// depend on the structural thresholds of the cut detector (5 % parts, door pairs within 12 cells).
// ROBOT_LINK_ROUTE=1 (round 44): the ROUTES are learned instead of assumed. Round 43 counted every robot on the links of its single
// shortest room route; on links where the planner splits traffic between near-equal routes this counted robots on links they never
// use (roomP rooms 8-9: 10 % of the traffic by the model, 5 % in reality). Now every crossing a robot with a task makes (room x ->
// room y while heading for room q) is recorded; the next-hop probabilities for (x, q) are (prior + observed counts) / (1 + total),
// the static shortest-route next hop being the prior with the weight of one observation. A robot counts on a link with the
// probability that it crosses it (propagated room by room through the learned table), so loads are fractional; the credit check
// is load + share <= K. With ROBOT_LINK_ROUTE unset every share is 1 and the behaviour is exactly that of v30.
#include "link_credit.h"
#include "netmac.h"
#include <algorithm>
#include <climits>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <map>
#include <queue>

namespace LinkCredit {
namespace {
int on = 0, meas = 0, only = 0; bool built = false, trace = false, dry = false;   // dry: count and trace only, never deny (diagnostic)
std::vector<long long> over_ticks, samples_n; std::vector<double> load_sum;
double alpha = 2.23, c1 = 26.0 / 500.0, c2 = 32.0 / 500.0, leg1 = 25.0, ta = -1.0, tb = 1.0;
SharedEnvironment* env0 = nullptr;
int n = 0, C = 0, R = 0;
std::vector<int> room_of, door_of;
struct Door { std::vector<int> cells; int a = -1, b = -1, width = 1, link = -1; };
struct Link { int a, b; double cap = 0; int K[2] = {1, 1}; double T[2] = {0, 0}; double load[2] = {0, 0}; long long denied = 0;
               double prior[2] = {0, 0}, sumT[2] = {0, 0}; long long nT[2] = {0, 0}; };
std::vector<Door> doors; std::vector<Link> links;
std::vector<std::vector<int>> field;            // per door: free-flow ticks from a cell to the door (INT_MAX = unreachable)
std::vector<std::vector<std::pair<int,int>>> route;   // per (room r, room q): (link, dir) in order
std::vector<std::vector<std::pair<int,int>>> counted; std::vector<std::pair<int,int>> tmp;
std::vector<std::vector<double>> countedf; std::vector<double> tmpf;   // fractional shares (all 1 without ROBOT_LINK_ROUTE)
int lroute = 0; long long n_cross = 0;
struct Hop { int L, d, y; };
std::vector<std::vector<Hop>> adj;                      // per room: outgoing hops (link, direction, next room)
std::vector<std::vector<double>> hopcnt;                // per (x * R + q): observed counts per hop of adj[x]
std::vector<std::vector<std::pair<int,double>>> usage;  // per (r * R + q): (link * 2 + dir, probability of crossing)
std::vector<char> dirty; std::vector<int> last_room;
void build_routes();
long long n_denied = 0, n_admitted = 0, n_samples = 0;
std::vector<std::vector<std::pair<int,int>>> apron;   // per cell: (link, dir) whose door is within 3 cells, approached from this side
std::vector<int> ag_task, ag_t0; std::vector<std::vector<std::pair<int,int>>> ag_rec;
void setK(Link& L, int d) { const double T = meas ? (L.prior[d] + L.sumT[d]) / (1.0 + L.nT[d]) : L.prior[d]; L.K[d] = std::max(1, int(std::ceil(T * L.cap / 2.0))); }

double envd(const char* k, double d) { const char* e = std::getenv(k); return e ? std::atof(e) : d; }

void build(SharedEnvironment* env) {
    built = true; n = int(env->map.size()); C = env->cols; const int H = n / C;
    auto isfree = [&](int r, int c) { return r >= 0 && r < H && c >= 0 && c < C && !env->map[r * C + c]; };
    std::vector<int> hr(n, 0), vr(n, 0);
    for (int r = 0; r < H; ++r) for (int c = 0; c < C; ) { if (!isfree(r, c)) { ++c; continue; } int e = c; while (e < C && isfree(r, e)) ++e; for (int k = c; k < e; ++k) hr[r * C + k] = e - c; c = e; }
    for (int c = 0; c < C; ++c) for (int r = 0; r < H; ) { if (!isfree(r, c)) { ++r; continue; } int e = r; while (e < H && isfree(e, c)) ++e; for (int k = r; k < e; ++k) vr[k * C + c] = e - r; r = e; }
    std::vector<char> narrow(n, 0); for (int v = 0; v < n; ++v) if (!env->map[v]) narrow[v] = hr[v] <= 2 || vr[v] <= 2;
    const int DR[4] = {-C, C, -1, 1};
    auto nb = [&](int v, int k) -> int { const int r = v / C, c = v % C;
        if (k == 0) return r > 0 ? v - C : -1; if (k == 1) return r + 1 < H ? v + C : -1; if (k == 2) return c > 0 ? v - 1 : -1; return c + 1 < C ? v + 1 : -1; };
    (void)DR;
    room_of.assign(n, -1); door_of.assign(n, -1); R = 0;
    for (int s = 0; s < n; ++s) { if (env->map[s] || narrow[s] || room_of[s] >= 0) continue;
        std::vector<int> q{s}; room_of[s] = R;
        for (size_t h = 0; h < q.size(); ++h) for (int k = 0; k < 4; ++k) { const int w = nb(q[h], k); if (w >= 0 && !env->map[w] && !narrow[w] && room_of[w] < 0) { room_of[w] = R; q.push_back(w); } }
        ++R; }
    std::vector<char> seen(n, 0);
    for (int s = 0; s < n; ++s) { if (!narrow[s] || seen[s]) continue;
        std::vector<int> g{s}; seen[s] = 1;
        for (size_t h = 0; h < g.size(); ++h) for (int k = 0; k < 4; ++k) { const int w = nb(g[h], k); if (w >= 0 && narrow[w] && !seen[w]) { seen[w] = 1; g.push_back(w); } }
        std::vector<int> touch;
        for (int v : g) for (int k = 0; k < 4; ++k) { const int w = nb(v, k); if (w >= 0 && room_of[w] >= 0 && std::find(touch.begin(), touch.end(), room_of[w]) == touch.end()) touch.push_back(room_of[w]); }
        if (touch.size() == 1) { for (int v : g) room_of[v] = touch[0]; continue; }      // niche -> part of the room
        if (touch.size() != 2) continue;                                                // odd group: ignored
        Door d; d.cells = g; d.a = std::min(touch[0], touch[1]); d.b = std::max(touch[0], touch[1]);
        bool up = false, down = false; int y0 = INT_MAX, y1 = -1, x0 = INT_MAX, x1 = -1;
        for (int v : g) { const int y = v / C, x = v % C; y0 = std::min(y0, y); y1 = std::max(y1, y); x0 = std::min(x0, x); x1 = std::max(x1, x);
            if (y > 0 && room_of[v - C] >= 0) up = true; if (y + 1 < H && room_of[v + C] >= 0) down = true; }
        d.width = (up && down) ? (x1 - x0 + 1) : (y1 - y0 + 1);
        for (int v : g) door_of[v] = int(doors.size());
        doors.push_back(d); }
    std::map<std::pair<int,int>, int> lidx;
    for (size_t i = 0; i < doors.size(); ++i) { auto key = std::make_pair(doors[i].a, doors[i].b); auto it = lidx.find(key);
        if (it == lidx.end()) { lidx[key] = int(links.size()); Link L; L.a = key.first; L.b = key.second; links.push_back(L); it = lidx.find(key); }
        doors[i].link = it->second; links[it->second].cap += doors[i].width <= 1 ? c1 : c2; }
    // free-flow time fields: reverse Dijkstra over (cell, heading) from the door cells; a move or a 90-degree turn takes 3 ticks
    const int DRo[4] = {1, C, -1, -C};
    field.assign(doors.size(), std::vector<int>());
    for (size_t i = 0; i < doors.size(); ++i) {
        std::vector<int> dist(4 * n, INT_MAX); using Q = std::pair<int,int>; std::priority_queue<Q, std::vector<Q>, std::greater<Q>> pq;
        for (int c : doors[i].cells) for (int o = 0; o < 4; ++o) { dist[4 * c + o] = 0; pq.push({0, 4 * c + o}); }
        while (!pq.empty()) { auto [d, st] = pq.top(); pq.pop(); if (d != dist[st]) continue; const int v = st / 4, o = st % 4;
            for (int no : {(o + 1) % 4, (o + 3) % 4}) if (d + 3 < dist[4 * v + no]) { dist[4 * v + no] = d + 3; pq.push({d + 3, 4 * v + no}); }
            const int p = v - DRo[o]; const bool ok = p >= 0 && p < n && !env->map[p] && (o == 1 || o == 3 || p / C == v / C);
            if (ok && d + 3 < dist[4 * p + o]) { dist[4 * p + o] = d + 3; pq.push({d + 3, 4 * p + o}); } }
        auto& f = field[i]; f.assign(n, INT_MAX);
        for (int v = 0; v < n; ++v) for (int o = 0; o < 4; ++o) f[v] = std::min(f[v], dist[4 * v + o]); }
    // per room: cells, adjacent doors, mean free-flow time from its cells to each door
    std::vector<std::vector<int>> rcells(R); for (int v = 0; v < n; ++v) if (room_of[v] >= 0) rcells[room_of[v]].push_back(v);
    std::vector<std::vector<int>> rdoors(R); for (size_t i = 0; i < doors.size(); ++i) { rdoors[doors[i].a].push_back(int(i)); rdoors[doors[i].b].push_back(int(i)); }
    std::vector<std::vector<double>> mean(R, std::vector<double>(doors.size(), 1e18));
    for (int r = 0; r < R; ++r) for (int i : rdoors[r]) { double s = 0; long long k = 0; for (int v : rcells[r]) if (field[i][v] < INT_MAX) { s += field[i][v]; ++k; } if (k) mean[r][i] = s / k; }
    // door-to-door free-flow time (door i's first cell to door j)
    const int ND = int(doors.size());
    auto other = [&](int i, int r) { return doors[i].a == r ? doors[i].b : doors[i].a; };
    route.assign(size_t(R) * R, {});
    std::vector<double> Tsum(2 * links.size(), 0.0), Wsum(2 * links.size(), 0.0);
    for (int r = 0; r < R; ++r) {
        // Dijkstra over states (door i, room entered after crossing it)
        std::vector<double> dist(ND, 1e18); std::vector<int> prev(ND, -1);
        using Q = std::pair<double,int>; std::priority_queue<Q, std::vector<Q>, std::greater<Q>> pq;
        for (int i : rdoors[r]) if (mean[r][i] < 1e17) { dist[i] = mean[r][i]; pq.push({dist[i], i}); }
        // state i means "crossed door i away from the room we came from"; we track the entered room per state
        std::vector<int> entered(ND, -1); for (int i : rdoors[r]) entered[i] = other(i, r);
        while (!pq.empty()) { auto [d, i] = pq.top(); pq.pop(); if (d != dist[i]) continue; const int s = entered[i];
            for (int j : rdoors[s]) { if (j == i) continue; const int fv = field[j][doors[i].cells[0]]; if (fv == INT_MAX) continue;
                const double nd = d + fv; if (nd < dist[j]) { dist[j] = nd; prev[j] = i; entered[j] = other(j, s); pq.push({nd, j}); } } }
        for (int q = 0; q < R; ++q) { if (q == r) continue;
            int best = -1; double bd = 1e18;
            for (int i : rdoors[q]) if (dist[i] < 1e17 && entered[i] == q && mean[q][i] < 1e17 && dist[i] + mean[q][i] < bd) { bd = dist[i] + mean[q][i]; best = i; }
            if (best < 0) continue;
            std::vector<int> seq; for (int i = best; i >= 0; i = prev[i]) seq.push_back(i); std::reverse(seq.begin(), seq.end());
            auto& rt = route[size_t(r) * R + q]; int cur = r; const double w = double(rcells[r].size()) * rcells[q].size();
            for (int i : seq) { const int L = doors[i].link, dir = (cur == links[L].a) ? 0 : 1; rt.push_back({L, dir});
                Tsum[2 * L + dir] += w * dist[i]; Wsum[2 * L + dir] += w; cur = other(i, cur); } } }
    for (size_t L = 0; L < links.size(); ++L) for (int dir = 0; dir < 2; ++dir) {
        const double T = leg1 + (Wsum[2 * L + dir] > 0 ? Tsum[2 * L + dir] / Wsum[2 * L + dir] : 0.0);
        links[L].T[dir] = T; const double teff = ta >= 0 ? ta + tb * T : alpha * T;   // v30b: affine delay model (ROBOT_NET_TA/TB, round 42 fit)
        links[L].prior[dir] = teff; setK(links[L], dir); }
    apron.assign(n, {});
    for (size_t i = 0; i < doors.size(); ++i) for (int c : doors[i].cells) { const int cy = c / C, cx = c % C;
        for (int dy = -3; dy <= 3; ++dy) for (int dx = -3; dx <= 3; ++dx) { if (std::abs(dy) + std::abs(dx) > 3) continue; const int y = cy + dy, x = cx + dx;
            if (y < 0 || y >= H || x < 0 || x >= C) continue; const int v = y * C + x; const int r = room_of[v]; if (r < 0) continue;
            const int L = doors[i].link; std::pair<int,int> e(L, r == links[L].a ? 0 : r == links[L].b ? 1 : -1); if (e.second < 0) continue;
            if (std::find(apron[v].begin(), apron[v].end(), e) == apron[v].end()) apron[v].push_back(e); } }
    ag_task.assign(env->num_of_agents, -1); ag_t0.assign(env->num_of_agents, 0); ag_rec.assign(env->num_of_agents, {});
    counted.assign(env->num_of_agents, {}); countedf.assign(env->num_of_agents, {});
    if (lroute) build_routes();
    if (trace) { std::fprintf(stderr, "[link] rooms %d doors %zu links %zu\n", R, doors.size(), links.size());
        for (size_t L = 0; L < links.size(); ++L) { int nd = 0, w2 = 0; for (auto& d : doors) if (d.link == int(L)) { ++nd; w2 += d.width == 2; }
            std::fprintf(stderr, "[link] %zu rooms %d-%d doors %d (2-cell %d) T %.0f/%.0f K %d/%d\n", L, links[L].a, links[L].b, nd, w2, links[L].T[0], links[L].T[1], links[L].K[0], links[L].K[1]); } }
}

int room_at(int v, int target_room) {
    if (v < 0 || v >= n) return -1;
    if (room_of[v] >= 0) return room_of[v];
    const int d = door_of[v]; if (d < 0) return -1;
    const int a = doors[d].a, b = doors[d].b;            // standing in a door: take the side with the shorter route onward
    if (target_room < 0) return a;
    if (a == target_room || b == target_room) return target_room;
    return route[size_t(a) * R + target_room].size() <= route[size_t(b) * R + target_room].size() ? a : b;
}

void route_of_static(int start, const std::vector<int>& L, int from, std::vector<std::pair<int,int>>& out);
void build_routes() {
    adj.assign(R, {}); for (size_t L = 0; L < links.size(); ++L) { adj[links[L].a].push_back({int(L), 0, links[L].b}); adj[links[L].b].push_back({int(L), 1, links[L].a}); }
    hopcnt.assign(size_t(R) * R, {}); for (int x = 0; x < R; ++x) for (int q = 0; q < R; ++q) hopcnt[size_t(x) * R + q].assign(adj[x].size(), 0.0);
    usage.assign(size_t(R) * R, {}); dirty.assign(R, 1); last_room.assign(counted.size(), -1);
}
void refresh(int q) {      // probabilities of crossing each link for every origin r and target q (absorbing chain at q)
    std::vector<std::vector<double>> P(R);
    for (int x = 0; x < R; ++x) { if (x == q) continue; const auto& c = hopcnt[size_t(x) * R + q]; const auto& rt = route[size_t(x) * R + q];
        std::vector<double> pr(adj[x].size(), 0.0); double tot = 1.0;
        for (size_t k = 0; k < adj[x].size(); ++k) { if (!rt.empty() && adj[x][k].L == rt[0].first && adj[x][k].d == rt[0].second) pr[k] += 1.0; pr[k] += c[k]; tot += c[k]; }
        if (rt.empty()) { tot -= 1.0; if (tot <= 0) { P[x].assign(adj[x].size(), 0.0); continue; } }
        for (auto& v : pr) v /= tot; P[x] = pr; }
    for (int r = 0; r < R; ++r) { auto& U = usage[size_t(r) * R + q]; U.clear(); if (r == q) continue;
        std::vector<double> m(R, 0.0), use(2 * links.size(), 0.0); m[r] = 1.0;
        for (int it = 0; it < 4 * R; ++it) { std::vector<double> nm(R, 0.0); double left = 0;
            for (int x = 0; x < R; ++x) { if (x == q || m[x] < 1e-9) continue;
                for (size_t k = 0; k < adj[x].size(); ++k) { const double f = m[x] * P[x][k]; if (f <= 0) continue; use[2 * adj[x][k].L + adj[x][k].d] += f; nm[adj[x][k].y] += f; } }
            for (int x = 0; x < R; ++x) if (x != q) left += nm[x];
            m.swap(nm); if (left < 1e-6) break; }
        for (size_t j = 0; j < use.size(); ++j) if (use[j] > 1e-6) U.push_back({int(j), std::min(1.0, use[j])}); }
    dirty[q] = 0;
}
void route_of(int start, const std::vector<int>& L, int from, std::vector<std::pair<int,int>>& out) {
    if (lroute) {           // learned routes: fractional shares, each link at most once (shares of the legs added, capped at 1)
        out.clear(); tmpf.clear(); int prev = -1, prevcell = start;
        for (int i = std::max(0, from); i < int(L.size()); ++i) {
            const int tgt = room_at(L[i], -1); if (tgt < 0) { prevcell = L[i]; continue; }
            const int src = prev >= 0 ? prev : room_at(prevcell, tgt);
            if (src >= 0 && src != tgt) { if (dirty[tgt]) refresh(tgt);
                for (auto& u : usage[size_t(src) * R + tgt]) { const std::pair<int,int> e(u.first / 2, u.first % 2); auto f = std::find(out.begin(), out.end(), e);
                    if (f == out.end()) { out.push_back(e); tmpf.push_back(u.second); } else { double& s0 = tmpf[f - out.begin()]; s0 = std::min(1.0, s0 + u.second); } } }
            prev = tgt; prevcell = L[i]; }
        return; }
    route_of_static(start, L, from, out); tmpf.assign(out.size(), 1.0);
}
void route_of_static(int start, const std::vector<int>& L, int from, std::vector<std::pair<int,int>>& out) {
    out.clear(); int prev = -1, prevcell = start;
    for (int i = std::max(0, from); i < int(L.size()); ++i) {
        const int tgt = room_at(L[i], -1); if (tgt < 0) { prevcell = L[i]; continue; }
        const int src = prev >= 0 ? prev : room_at(prevcell, tgt);
        if (src >= 0 && src != tgt) for (auto& e : route[size_t(src) * R + tgt]) if (std::find(out.begin(), out.end(), e) == out.end()) out.push_back(e);
        prev = tgt; prevcell = L[i]; }
}
bool active() {
    if (!on || DefaultPlanner::NetMac::link_count() <= 0) return false;
    if (!built && env0) build(env0);
    return built; }
void uncount(int agent) { if (agent < 0 || agent >= int(counted.size())) return;
    for (size_t j = 0; j < counted[agent].size(); ++j) links[counted[agent][j].first].load[counted[agent][j].second] -= countedf[agent][j];
    counted[agent].clear(); countedf[agent].clear(); }
void count(int agent) { for (size_t j = 0; j < tmp.size(); ++j) links[tmp[j].first].load[tmp[j].second] += tmpf[j]; counted[agent] = tmp; countedf[agent] = tmpf; }
}

bool replaces_cuts() { return only && active(); }
void initialize(SharedEnvironment* env) {
    on = std::getenv("ROBOT_LINK") ? std::atoi(std::getenv("ROBOT_LINK")) : 0;
    meas = std::getenv("ROBOT_LINK_MEAS") ? std::atoi(std::getenv("ROBOT_LINK_MEAS")) : 0; only = std::getenv("ROBOT_LINK_ONLY") ? std::atoi(std::getenv("ROBOT_LINK_ONLY")) : 0;
    lroute = std::getenv("ROBOT_LINK_ROUTE") ? std::atoi(std::getenv("ROBOT_LINK_ROUTE")) : 0; n_cross = 0; dry = std::getenv("ROBOT_LINK_DRY") != nullptr; trace = std::getenv("ROBOT_LINK_TRACE") != nullptr;
    alpha = envd("ROBOT_NET_ALPHA", 2.23); c1 = envd("ROBOT_NET_C1", 26.0 / 500.0); c2 = envd("ROBOT_NET_C2", 32.0 / 500.0); leg1 = envd("ROBOT_NET_LEG1", 25.0);
    ta = std::getenv("ROBOT_NET_TA") ? std::atof(std::getenv("ROBOT_NET_TA")) : -1.0; tb = envd("ROBOT_NET_TB", 1.0);
    built = false; doors.clear(); links.clear(); field.clear(); route.clear(); counted.clear(); n_denied = n_admitted = 0; env0 = env;
}
void begin_schedule(SharedEnvironment* env) {
    if (!active()) return;
    for (auto& L : links) L.load[0] = L.load[1] = 0;
    const int now = env->system_timestep;
    for (int i = 0; i < int(env->system_states.size()) && i < int(counted.size()); ++i) { const auto prev = counted[i]; counted[i].clear();
        const int tk = env->curr_task_schedule[i];
        if (lroute) { const int l0 = env->system_states[i].location, cur = (l0 >= 0 && l0 < n) ? room_of[l0] : -1;
            if (cur >= 0) { const int last = last_room[i];
                auto itq = env->task_pool.find(tk);
                if (last >= 0 && cur != last && itq != env->task_pool.end()) {
                    const auto& TL = itq->second.locations; const int ix = std::max(0, itq->second.idx_next_loc);
                    const int q = ix < int(TL.size()) ? room_at(TL[ix], -1) : -1;
                    if (q >= 0 && q != last) for (size_t k = 0; k < adj[last].size(); ++k) if (adj[last][k].y == cur) {
                        hopcnt[size_t(last) * R + q][k] += 1.0; dirty[q] = 1; ++n_cross; break; } }
                last_room[i] = cur; } }
        if (tk != ag_task[i]) { ag_task[i] = tk; ag_t0[i] = now; ag_rec[i].clear(); }
        auto it = env->task_pool.find(tk); if (it == env->task_pool.end()) continue;
        const int loc = env->system_states[i].location;
        route_of(loc, it->second.locations, it->second.idx_next_loc, tmp); count(i);
        std::vector<std::pair<int,int>> here;
        if (meas == 2 && loc >= 0 && loc < n && door_of[loc] >= 0) { const int L0 = doors[door_of[loc]].link;
            for (int d = 0; d < 2; ++d) here.push_back({L0, d}); }
        if (meas && loc >= 0 && loc < n) for (auto& e : (meas == 2 ? here : apron[loc])) {        // v31: delay sample on arrival in a link's approach area
            const auto& R0 = meas == 2 ? prev : tmp;   // in a door cell the remaining route may already start past the door
            if (std::find(R0.begin(), R0.end(), e) == R0.end() || std::find(ag_rec[i].begin(), ag_rec[i].end(), e) != ag_rec[i].end()) continue;
            auto& L = links[e.first]; L.sumT[e.second] += now - ag_t0[i]; ++L.nT[e.second]; ++n_samples; setK(L, e.second); ag_rec[i].push_back(e); } }
    if (trace) { if (over_ticks.empty()) { over_ticks.assign(2 * links.size(), 0); samples_n.assign(2 * links.size(), 0); load_sum.assign(2 * links.size(), 0); }
        for (size_t L = 0; L < links.size(); ++L) for (int d = 0; d < 2; ++d) { ++samples_n[2 * L + d]; load_sum[2 * L + d] += links[L].load[d]; if (links[L].load[d] > links[L].K[d]) ++over_ticks[2 * L + d]; }
        if (env->system_timestep >= 4980 && env->system_timestep < 4995) for (size_t L = 0; L < links.size(); ++L) for (int d = 0; d < 2; ++d)
            std::fprintf(stderr, "[linkstat] %zu %d K=%d meanload=%.2f over=%.3f prior=%.0f measured=%.0f n=%lld\n", L, d, links[L].K[d], load_sum[2 * L + d] / std::max(1LL, samples_n[2 * L + d]), double(over_ticks[2 * L + d]) / std::max(1LL, samples_n[2 * L + d]), links[L].prior[d], links[L].nT[d] ? links[L].sumT[d] / links[L].nT[d] : -1.0, links[L].nT[d]); }
    if (trace && env->system_timestep % 500 == 0) { std::fprintf(stderr, "[link] t=%d denied=%lld admitted=%lld crossings=%lld load/K:", env->system_timestep, n_denied, n_admitted, n_cross);
        for (auto& L : links) std::fprintf(stderr, " %.1f/%d,%.1f/%d[%lld]", L.load[0], L.K[0], L.load[1], L.K[1], L.denied); std::fprintf(stderr, "\n"); }
}
bool allowed(int agent, int task, SharedEnvironment* env) {
    if (!active()) return true;
    const auto& T = env->task_pool.at(task);
    route_of(env->system_states.at(agent).location, T.locations, T.idx_next_loc, tmp);
    for (size_t j = 0; j < tmp.size(); ++j) { const auto& e = tmp[j];
        if (links[e.first].load[e.second] + tmpf[j] > links[e.first].K[e.second] + 1e-9) { ++n_denied; ++links[e.first].denied; if (!dry) return false; } }
    return true;
}
void assigned(int agent, int task, SharedEnvironment* env) {
    if (!active()) return;
    uncount(agent); const auto& T = env->task_pool.at(task);
    route_of(env->system_states.at(agent).location, T.locations, T.idx_next_loc, tmp); if (!tmp.empty()) ++n_admitted; count(agent);
}
void release(int agent) { if (active()) uncount(agent); }
}
