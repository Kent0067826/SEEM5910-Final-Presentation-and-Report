


#include "pibt.h"
#include "netmac.h"
#include "window_control.h"

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <algorithm>





namespace DefaultPlanner{
// p04 (protocol round 4): BFD + LFA fast reroute around a robot in a fault.
// Network original: BFD (RFC 5880) declares a neighbour Down when its control packets stop for DetectMult intervals; IP fast
// reroute with loop-free alternates (RFC 5286) then switches traffic at once to a precomputed backup next hop N of the router S
// for destination D, accepted only if it is loop-free, dist(N,D) < dist(N,S) + dist(S,D), and node-protecting for the failed
// next hop E, dist(N,D) < dist(N,E) + dist(E,D). Without such an alternate the traffic waits for the repair (no reroute).
// Here: a robot in an execution delay for >= ROBOT_BFD_LFA ticks (DetectMult; the simulator's delay flag plays the role of the
// missing BFD packets) makes its cell a down node E. A robot S choosing its own move (not pushed by PIBT) whose first choice is E
// tries an alternate neighbour N first when N is empty, unclaimed, and passes both tests with the true distance to its goal
// (one move = 1, so dist(N,S) = 1 and dist(N,E) >= 2 on the grid: h(N) <= h(S) and h(N) <= h(E) + 1). Otherwise nothing changes.
// The robot in the fault, the other robots and the executor are untouched (unlike ROBOT_DELAY_FREEZE / ROBOT_DELAY_REROUTE).
// ROBOT_BFD_LFA_MEAS=1 counts the situations without changing anything; ROBOT_BFD_LFA_LOG=path writes the counters.
namespace Bfd {
namespace {
int mult = -1; bool meas = false; int step = 0;
std::vector<int> down_of, fault_t0;                    // per cell: down robot standing there (-1); per robot: first tick seen in a fault
std::vector<int> down_cells;
long long n_self = 0, n_primary_down = 0, n_lfa = 0, n_taken = 0, n_plans = 0, n_down_sum = 0;
void init_env() { if (mult >= 0) return; const char* e = std::getenv("ROBOT_BFD_LFA"); mult = e ? std::max(0, std::atoi(e)) : 0;
    meas = std::getenv("ROBOT_BFD_LFA_MEAS") != nullptr; }
}
bool on() { init_env(); return mult > 0 || meas; }
void begin_plan(SharedEnvironment* env) {
    if (!on()) return;
    const int n = int(env->map.size()), na = int(env->system_states.size()), now = env->system_timestep;
    if (int(down_of.size()) != n) down_of.assign(n, -1);
    if (int(fault_t0.size()) != na) fault_t0.assign(na, -1);
    for (int c : down_cells) down_of[c] = -1; down_cells.clear();
    const int m = std::max(1, mult);
    for (int i = 0; i < na; ++i) {
        if (!env->system_states[i].delay.inDelay) { fault_t0[i] = -1; continue; }
        if (fault_t0[i] < 0) fault_t0[i] = now;
        const int loc = env->system_states[i].location;
        if (now - fault_t0[i] + 1 >= m && loc >= 0 && loc < n) { down_of[loc] = i; down_cells.push_back(loc); }
    }
    ++n_plans; n_down_sum += down_cells.size();
}
void set_step(int s) { step = s; }
void write_stats(SharedEnvironment* env) {
    static const char* lp = std::getenv("ROBOT_BFD_LFA_LOG"); if (!lp || !on()) return;
    if (std::FILE* f = std::fopen(lp, "w")) { std::fprintf(f, "{\"t\":%d,\"mult\":%d,\"meas\":%d,\"plans\":%lld,\"meanDown\":%.3f,\"selfChoices\":%lld,\"primaryDown\":%lld,\"lfaAvailable\":%lld,\"lfaTaken\":%lld}\n",
        env->system_timestep, mult, int(meas), n_plans, n_plans ? double(n_down_sum) / n_plans : 0.0, n_self, n_primary_down, n_lfa, n_taken); std::fclose(f); }
}
// returns the index in succ of the loop-free, node-protecting alternate to try first, or -1
template <class S> int pick_lfa(int curr_id, int prev_loc, int target, S& succ, std::vector<int>& prev_decision,
                                 std::vector<int>& decision, std::vector<bool>& occupied, TrajLNS& lns) {
    if (!on() || down_of.empty()) return -1;
    if (step == 0) ++n_self;
    if (succ.empty() || succ[0].location == prev_loc) return -1;
    const int E = succ[0].location;
    if (E < 0 || E >= int(down_of.size()) || down_of[E] < 0 || down_of[E] == curr_id) return -1;
    if (down_of[prev_loc] == curr_id) return -1;                       // S itself is down
    auto& ht = lns.heuristics[target]; if (ht.empty()) return -1;
    if (step == 0) ++n_primary_down;
    const int hS = get_heuristic(ht, lns.env, prev_loc, &(lns.neighbors)), hE = get_heuristic(ht, lns.env, E, &(lns.neighbors));
    for (int k = 1; k < int(succ.size()); ++k) {
        const int N = succ[k].location;
        if (N == prev_loc || N == E || N < 0 || down_of[N] >= 0) continue;
        const int hN = get_heuristic(ht, lns.env, N, &(lns.neighbors));
        if (hN > hS || hN > hE + 1) continue;                          // loop-free and node-protecting (RFC 5286)
        if (occupied[N] || decision[N] != -1 || prev_decision[N] != -1) continue;   // empty and unclaimed now
        if (!NetMac::allow_move(curr_id, prev_loc, N)) continue;
        if (step == 0) { ++n_lfa; if (!meas) ++n_taken; }
        return meas ? -1 : k;
    }
    return -1;
}
}

std::vector<int> p49_gp;   // p49: 1 = guide path re-planned to the advanced errand (use it, not plain distance)
std::vector<int> p48_adv;   // p48: per robot, how many errands the planner has advanced past inside the current plan
int p48_on(){ static int v = -1; if (v < 0) { const char* e = std::getenv("ROBOT_ERRAND_ADVANCE"); v = e ? std::atoi(e) : 0; } return v; }
int get_gp_h(TrajLNS& lns, int ai, int target){
    int min_heuristic;
	// p48 (TCP delayed ACK -> immediate ACK): a robot whose target was advanced inside this plan heads for the new errand by plain distance
	if (ai < int(p48_adv.size()) && p48_adv[ai] > 0 && !(ai < int(p49_gp.size()) && p49_gp[ai]) && !lns.heuristics[lns.tasks.at(ai)].empty()) return get_heuristic(lns.heuristics[lns.tasks.at(ai)], lns.env, target, &(lns.neighbors));
	// v18e diagnosis: ROBOT_NO_GUIDE=1 ignores the guide paths and uses the plain distance to the goal
	static int noguide = -1; if (noguide < 0) { const char* e = std::getenv("ROBOT_NO_GUIDE"); noguide = e ? std::atoi(e) : 0; }
	if (noguide && !lns.heuristics[lns.tasks.at(ai)].empty()) return get_heuristic(lns.heuristics[lns.tasks.at(ai)], lns.env, target, &(lns.neighbors));

	if (is_large_map(lns.env)){
		if (!lns.traj_dists.empty() && !lns.traj_dists[ai].empty())
		{
			min_heuristic = get_dist_2_path(lns.traj_dists[ai], lns.env, target, &(lns.neighbors)); 
		}
		else
		{
			min_heuristic = manhattanDistance(target,lns.tasks.at(ai),lns.env);
		}
		return min_heuristic;
	}
	else{
		if (!lns.traj_dists.empty() && !lns.traj_dists[ai].empty())
		{
			min_heuristic = get_dist_2_path(lns.traj_dists[ai], lns.env, target, &(lns.neighbors)); 
		}
		else if (!lns.heuristics[lns.tasks.at(ai)].empty())
		{
			min_heuristic = get_heuristic(lns.heuristics[lns.tasks.at(ai)], lns.env, target, &(lns.neighbors));
		}
		else
		{
			min_heuristic = manhattanDistance(target,lns.tasks.at(ai),lns.env);
		}
		return min_heuristic;
	}
}

namespace TcpWin {
namespace { std::vector<int> hit; int mode = -1; long long used = 0, seen = 0; }
static bool on() { if (mode < 0) { const char* e = std::getenv("ROBOT_TCP_WIN"); mode = e ? std::atoi(e) : 0; } return mode > 0; }
bool hitcell(int agent, int cell) { return agent >= 0 && agent < int(hit.size()) && hit[agent] == cell; }
void write_stats() { static const char* p = std::getenv("ROBOT_TCP_WIN_LOG"); if (!p) return;
    if (std::FILE* f = std::fopen(p, "w")) { std::fprintf(f, "{\"seen\": %lld, \"used\": %lld}\n", seen, used); std::fclose(f); } }
}

int p46_step = 0;   // p46 (log only): multistep PIBT step index, set by the planner
bool causalPIBT(int curr_id, int higher_id,std::vector<State>& prev_states,
	  std::vector<State>& next_states,
      std::vector<int>& prev_decision, std::vector<int>& decision, 
	  std::vector<bool>& occupied, TrajLNS& lns
	  ){
	// The PIBT works like a causal PIBT when using MAPF-T model. But a normal PIBT when using MAPF model.
	
	assert(next_states[curr_id].location == -1);
    int prev_loc = prev_states[curr_id].location;
	int prev_orientation = prev_states[curr_id].orientation;
	int next[4] = { prev_loc + 1,prev_loc + lns.env->cols, prev_loc - 1, prev_loc - lns.env->cols};
	int orien_next_v = next[prev_orientation];

	assert(prev_loc >= 0 && prev_loc < lns.env->map.size());

	int target = lns.tasks.at(curr_id);
	if (TcpWin::hit.size() < prev_states.size()) TcpWin::hit.assign(prev_states.size(), -1);
	TcpWin::hit[curr_id] = -1;

	if (higher_id == -1){
		//fist agent in the chain, disallow cyclic movments by preventing other agents moving to first agent's previous location
		occupied[prev_loc] = true;
	}

	// for each neighbor of (prev_loc,prev_direction), and a wait copy of current location, generate a successor
	std::vector<int> neighbors;
	std::vector<PIBT_C> successors;
	getNeighborLocs(&(lns.neighbors),neighbors,prev_loc);
	// v16 (round 26): ROBOT_PIBT_ROT=k makes the successor order turn-aware: score = 2*h + k*(quarter turns needed to face
	// the neighbour); k=2 counts a quarter turn as one action, like a move (turn-cost routing, as in NoC turn models).
	static int rotk = -1; if (rotk < 0) { const char* e = std::getenv("ROBOT_PIBT_ROT"); rotk = e ? std::atoi(e) : 0; }
	for (auto& neighbor: neighbors){

		assert(validateMove(prev_loc, neighbor, lns.env));
		if (!RobotWindow::move_allowed_goal(prev_loc, neighbor, lns.tasks.at(curr_id))) continue;   // v18b/f: one-way doors, room pause

		int min_heuristic = get_gp_h(lns, curr_id, neighbor);
		if (rotk > 0) {
			int dir = 0; for (int k = 0; k < 4; ++k) if (next[k] == neighbor) dir = k;
			const int dd = std::abs(dir - prev_orientation), rot = prev_orientation < 0 ? 0 : std::min(dd, 4 - dd);
			min_heuristic = 2 * min_heuristic + rotk * rot;
		}

		successors.emplace_back(neighbor,min_heuristic,-1,rand());
	}

	int wait_heuristic = get_gp_h(lns, curr_id, prev_loc);
	if (rotk > 0) wait_heuristic *= 2;

	successors.emplace_back(prev_loc, wait_heuristic,-1,rand());


	std::sort(successors.begin(), successors.end(), 
		[&](PIBT_C& a, PIBT_C& b)
		{
			int diff[4] = {1,lns.env->cols,-1,-lns.env->cols};
			if (a.heuristic == b.heuristic){
					//tie break on prefer moving forward
					if (a.location==orien_next_v && b.location!=orien_next_v)
						return true;
					if (a.location!=orien_next_v && b.location==orien_next_v)
						return false;
					// random tie break
					return a.tie_breaker < b.tie_breaker;
			}
			return a.heuristic < b.heuristic;
		});

	if (higher_id == -1) {   // p04: BFD + LFA, only for a robot choosing its own move
		const int k = Bfd::pick_lfa(curr_id, prev_loc, target, successors, prev_decision, decision, occupied, lns);
		if (k > 0) std::rotate(successors.begin(), successors.begin() + k, successors.begin() + k + 1);
	}

    // p46 (log only): ROBOT_PIBT_STAYLOG=<path> -- when a robot with a task ends up staying, why its best improving cell was not taken.
    static std::FILE* stf = [](){ const char* p = std::getenv("ROBOT_PIBT_STAYLOG"); std::FILE* f = p ? std::fopen(p, "w") : nullptr; if (f) { std::setvbuf(f, nullptr, _IOFBF, 1 << 20); static std::FILE* ff = f; std::atexit([]{ std::fflush(ff); }); } return f; }();
    int st_best = -1; char st_rej = 'G';
    if (stf) for (auto& sc: successors) if (sc.location != prev_loc && sc.heuristic < wait_heuristic) { st_best = sc.location; break; }
    auto st_log = [&](){ if (stf && target >= 0) std::fprintf(stf, "S %d %d %d %c %d %d%c", lns.env->system_timestep, p46_step, curr_id, st_best < 0 ? 'G' : st_rej, higher_id == -1 ? 0 : 1, int(prev_loc == target), 10); if (stf && lns.env->system_timestep % 300 == 0) std::fflush(stf); };
    for (auto& next: successors){
		if(occupied[next.location] && !(higher_id == -1 && prev_loc == next.location)){
			// p11: occupied only because the leader standing there is a chain head that already decided to leave
			const int j = prev_decision[next.location];
			if (!(j >= 0 && j != curr_id && next_states[j].location != -1 && next_states[j].location != next.location)) { if (next.location == st_best) st_rej = 'O'; continue; }
			if (TcpWin::hit[curr_id] < 0) TcpWin::hit[curr_id] = next.location;
			// follow only as a chain head nobody is entering behind (cannot close a cycle back to the leader)
			if (!(TcpWin::on() && higher_id == -1 && decision[prev_loc] == -1)) { if (next.location == st_best) st_rej = 'O'; continue; }
			++TcpWin::seen;
		}
		if(!NetMac::allow_move(curr_id, prev_loc, next.location)) // wait-v7 half-duplex corridor admission
			{ if (next.location == st_best) st_rej = 'M'; continue; }
		assert(validateMove(prev_loc, next.location, lns.env));
		
		if (next.location == -1)
			continue;
		if (decision[next.location] != -1){
			if (next.location == st_best) st_rej = 'D'; continue;
		}
		if (higher_id != -1 && prev_decision[next.location] == higher_id){
			continue;
		}
		next_states.at(curr_id) = State(next.location, -1, -1);
		decision.at(next.location) = curr_id;
		if (next.location == prev_loc) st_log();
		if (occupied[next.location] && next.location != prev_loc) ++TcpWin::used;

        if (prev_decision.at(next.location) != -1 && 
			next_states.at(prev_decision.at(next.location)).location == -1){
            int lower_id = prev_decision.at(next.location);
            if (!causalPIBT(lower_id,curr_id,prev_states,next_states, prev_decision,decision, occupied,lns)){
				if (next.location == st_best) st_rej = 'C'; continue;
            }
        }

        return true;
    }

    st_log();
    next_states.at(curr_id) = State(prev_loc,-1 ,-1);;
    decision.at(prev_loc) = curr_id;     
    return false;
}

Action getAction(State& prev, State& next){
	if (prev.location == next.location && prev.orientation == next.orientation){
		return Action::W;
	}
	if (prev.location != next.location && prev.orientation == next.orientation){
		return Action::FW;
	}
	if (next.orientation  == (prev.orientation+1)%4){
		return Action::CR;
	}
	if (next.orientation  == (prev.orientation+3)%4){
		return Action::CCR;
	}
	assert(false);
	return Action::W;
}

Action getAction(State& prev, int next_loc, SharedEnvironment* env){
	if (prev.location == next_loc){
		return Action::W;
	}
	int diff = next_loc -prev.location;
	int orientation;
	if (diff == 1){
		orientation = 0;
	}
	if (diff == -1){
		orientation = 2;
	}
	if (diff == env->cols){
		orientation = 1;
	}
	if (diff == -env->cols){
		orientation = 3;
	}
	if (orientation == prev.orientation){
		return Action::FW;
	}
	if (orientation  == (prev.orientation+1)%4){
		return Action::CR;
	}
	if (orientation  == (prev.orientation+3)%4){
		return Action::CCR;
	}
	if (orientation  == (prev.orientation+2)%4){
		return Action::CR;
	}
	assert(false);

}

bool moveCheck(int id, std::vector<bool>& checked,
		std::vector<DCR>& decided, std::vector<Action>& actions, std::vector<int>& prev_decision){
	if (checked.at(id) && actions.at(id) == Action::FW)
		return true;
	checked.at(id) = true;

	if (actions.at(id) != Action::FW)
		return false;

	//move forward
	int target = decided.at(id).loc;
	assert(target != -1);

	int na = prev_decision[target];
	if (na == -1)
		return true;

	if (moveCheck(na,checked,decided,actions,prev_decision))
		return true;
	actions.at(id) = Action::W;
	return false;
	

	

	
	
}

}