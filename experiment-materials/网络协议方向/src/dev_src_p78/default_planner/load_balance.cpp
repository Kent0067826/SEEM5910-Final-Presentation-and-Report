#include "load_balance.h"
#include "netmac.h"
#include <cstdlib>
#include <cstdio>
#include <fstream>
#include <vector>
#include <cmath>
namespace LoadBalance {
static int inited = 0, cap_mode = 0, toll_mode = 0;
static std::vector<int> door_of;
static std::vector<double> factor;
static std::vector<int> toll_of;     // per cell (the door's toll, rounded to whole moves)
static void init(SharedEnvironment* env) {
    inited = 1;
    cap_mode = std::getenv("ROBOT_LB_CAP") ? std::atoi(std::getenv("ROBOT_LB_CAP")) : 0;
    toll_mode = std::getenv("ROBOT_LB_TOLL") ? std::atoi(std::getenv("ROBOT_LB_TOLL")) : 0;
    if (!cap_mode && !toll_mode) return;
    const char* f = std::getenv("ROBOT_LB_FILE");
    const int n = int(env->map.size());
    door_of.assign(n, -1); factor.assign(n, 1.0); toll_of.assign(n, 0);
    if (!f) { std::fprintf(stderr, "[lb] ROBOT_LB_FILE not set: load balancing off\n"); cap_mode = toll_mode = 0; return; }
    std::ifstream in(f); int cell, door; double fac, tl; int cnt = 0;
    while (in >> cell >> door >> fac >> tl) { if (cell < 0 || cell >= n) continue; door_of[cell] = door; factor[cell] = fac; toll_of[cell] = int(std::lround(tl)); ++cnt; }
    if (std::getenv("ROBOT_LB_TRACE")) std::fprintf(stderr, "[lb] %d door cells read from %s (cap %d, toll %d)\n", cnt, f, cap_mode, toll_mode);
}
bool cap_on(SharedEnvironment* env) { if (!inited) init(env); return cap_mode != 0 && DefaultPlanner::NetMac::link_count() > 0; }
double cap_factor(SharedEnvironment* env, int cell) {
    if (!inited) init(env);
    if (!cap_mode || cell < 0 || cell >= int(factor.size()) || DefaultPlanner::NetMac::link_count() == 0) return 1.0;
    return factor[cell];
}
int toll(SharedEnvironment* env, int from, int to) {
    if (!inited) init(env);
    if (!toll_mode || to < 0 || to >= int(door_of.size()) || DefaultPlanner::NetMac::link_count() == 0) return 0;
    const int d = door_of[to];
    if (d < 0 || (from >= 0 && from < int(door_of.size()) && door_of[from] == d)) return 0;   // charge once, on entering the door
    return toll_of[to];
}
}
