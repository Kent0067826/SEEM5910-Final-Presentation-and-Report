
#ifndef pibt_hpp
#define pibt_hpp

#include <vector>
#include <list>
#include <unordered_set>
#include <tuple>
#include <cstdint>
#include "Types.h"
#include "utils.h"
#include "heuristics.h"
#include "TrajLNS.h"
#include "utils.h"





namespace DefaultPlanner{
extern int p46_step;   // p46 (log only)
extern std::vector<int> p48_adv;
extern std::vector<int> p49_gp;   // p49   // p48 ROBOT_ERRAND_ADVANCE
int p48_on();
// Global counters for heuristic calls within PIBT (defined in pibt.cpp)
extern std::uint64_t PIBT_CNT_get_dist_2_path;
extern std::uint64_t PIBT_CNT_get_heuristic;
extern std::uint64_t PIBT_CNT_manhattan;
int get_gp_h(TrajLNS& lns, int ai, int target);

// p04 (protocol round 4): BFD (RFC 5880) + loop-free alternate fast reroute (RFC 5286), see pibt.cpp
namespace Bfd {
void begin_plan(SharedEnvironment* env);   // once per plan(): which robots are "down" (in a fault for >= DetectMult ticks)
void set_step(int step);                   // planned step inside the current plan (counters use step 0 only)
void write_stats(SharedEnvironment* env);
}

// p11 (protocol round 11): TCP sliding window (RFC 793 sec. 3.7 / RFC 7323): a robot choosing its own move may enter the cell
// its leader (a chain head that already decided to move on) is vacating in the same step, instead of waiting one step for the
// "ack" (ROBOT_TCP_WIN=1, default off). hitcell: in this step the agent was refused that cell only by the head rule.
namespace TcpWin {
bool hitcell(int agent, int cell);
void write_stats();
}


bool causalPIBT(int curr_id, int higher_id,std::vector<State>& prev_states,
	 std::vector<State>& next_states,
      std::vector<int>& prev_decision, std::vector<int>& decision, 
	  std::vector<bool>& occupied,TrajLNS& lns
	  );


Action getAction(State& prev, State& next);

Action getAction(State& prev, int next_loc, SharedEnvironment* env);

bool moveCheck(int id, std::vector<bool>& checked,
		std::vector<DCR>& decided, std::vector<Action>& actions, std::vector<int>& prev_decision);
}
#endif