#include "seg_route.h"
#include <cstdlib>
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <map>
#include <random>
namespace SegRoute {
struct Seq { double share; std::vector<int> doors; };
static int inited = 0, mode = 0, pen = 0, cur = -1, ndoors = 0;
static std::vector<int> room_of, door_of;
static std::map<std::pair<int,int>, std::vector<Seq>> table;
static std::vector<int> goal_of;                 // goal the robot's sequence was drawn for
static std::vector<std::vector<char>> allowed;   // per robot: door -> on its sequence (empty = no charge)
static std::mt19937_64 rng(61061);
static void init(SharedEnvironment* env) {
    inited = 1;
    mode = std::getenv("ROBOT_SR") ? std::atoi(std::getenv("ROBOT_SR")) : 0;
    if (!mode) return;
    const char* f = std::getenv("ROBOT_SR_FILE");
    const int n = int(env->map.size());
    room_of.assign(n, -1); door_of.assign(n, -1);
    if (!f) { std::fprintf(stderr, "[sr] ROBOT_SR_FILE not set: SR off\n"); mode = 0; return; }
    std::ifstream in(f); std::string line; int nr = 0, nd = 0, np = 0;
    while (std::getline(in, line)) {
        std::istringstream ss(line); char c; ss >> c;
        if (c == 'R') { int cell, r; ss >> cell >> r; if (cell >= 0 && cell < n) { room_of[cell] = r; ++nr; } }
        else if (c == 'D') { int cell, d; ss >> cell >> d; if (cell >= 0 && cell < n) { door_of[cell] = d; ++nd; if (d + 1 > ndoors) ndoors = d + 1; } }
        else if (c == 'P') { int s, t, k; double sh; ss >> s >> t >> sh >> k; Seq q; q.share = sh; q.doors.resize(k);
            for (int j = 0; j < k; ++j) { ss >> q.doors[j]; if (q.doors[j] + 1 > ndoors) ndoors = q.doors[j] + 1; }
            table[{s, t}].push_back(q); ++np; }
    }
    int fr = 0; for (int i = 0; i < n; ++i) if (env->map[i] == 0) ++fr;
    pen = std::getenv("ROBOT_SR_PEN") ? std::atoi(std::getenv("ROBOT_SR_PEN")) : fr;
    if (std::getenv("ROBOT_SR_TRACE")) std::fprintf(stderr, "[sr] %d room cells, %d door cells, %d sequences, penalty %d (%s)\n", nr, nd, np, pen, f);
}
bool on(SharedEnvironment* env) { if (!inited) init(env); return mode != 0; }
void select(SharedEnvironment* env, int agent, int start, int goal) {
    if (!inited) init(env);
    if (!mode) return;
    cur = agent;
    if (agent >= int(goal_of.size())) { goal_of.resize(agent + 1, -1); allowed.resize(agent + 1); }
    if (goal_of[agent] == goal) return;
    goal_of[agent] = goal; allowed[agent].clear();
    if (start < 0 || goal < 0 || start >= int(room_of.size()) || goal >= int(room_of.size())) return;
    const int s = room_of[start], t = room_of[goal];
    if (s < 0 || t < 0 || s == t) return;
    auto it = table.find({s, t}); if (it == table.end() || it->second.empty()) return;
    double u = std::uniform_real_distribution<double>(0.0, 1.0)(rng), acc = 0; const Seq* pick = &it->second.back();
    for (const auto& q : it->second) { acc += q.share; if (u < acc) { pick = &q; break; } }
    allowed[agent].assign(ndoors, 0);
    for (int d : pick->doors) if (d >= 0 && d < ndoors) allowed[agent][d] = 1;
}
int toll(SharedEnvironment* env, int from, int to) {
    if (!inited) init(env);
    if (!mode || cur < 0 || cur >= int(allowed.size()) || allowed[cur].empty()) return 0;
    if (to < 0 || to >= int(door_of.size())) return 0;
    const int d = door_of[to];
    if (d < 0 || d >= int(allowed[cur].size()) || allowed[cur][d]) return 0;
    if (from >= 0 && from < int(door_of.size()) && door_of[from] == d) return 0;   // charge once, on entering the door
    return pen;
}
}
