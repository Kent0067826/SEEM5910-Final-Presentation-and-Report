#pragma once
// wait-v7: link-layer ("MAC") mechanisms from computer networks applied inside PIBT.
//  HDX: adaptive half-duplex corridors (TDMA-like direction slots with carrier sense and max hold time)
//  MP : max-pressure / backpressure right-of-way (priority bonus = upstream backlog - downstream backlog)
//  BO : CSMA-style randomized binary exponential backoff for persistent head-on conflicts
// All disabled by default => planner behaviour identical to v6.
#include <vector>
#include "Types.h"
#include "TrajLNS.h"
namespace DefaultPlanner { namespace NetMac {
bool any_enabled();
// v21: number of single-lane passages (cut bridges + links) the bridge/link MAC is managing
int passage_count();
// v25i: number of managed single-lane links (not cuts)
int link_count();
// v19d: bridge MAC priority demotion (robots waiting for their turn at a bridge go last in PIBT)
bool demote_active();
bool blocked(int agent);
// v25c (round 36): ROBOT_BMAC_PROMOTE=1 -- robots crossing in the current direction (near the passage), robots inside the passage
// and robots that left it in the last few steps go first in PIBT (in-transit traffic first)
bool promote_active();
bool promoted(int agent);
// v25d: with ROBOT_BMAC_PROMOTE bit 4, promoted robots are ordered by distance to the passage (closest first; -1 if not promoted)
int promote_rank(int agent);
void initialize(SharedEnvironment* env, TrajLNS& lns);
// called once per PIBT step, before priorities are sorted
void begin_step(SharedEnvironment* env, TrajLNS& lns, const std::vector<State>& prev_states);
double key_bonus(int agent);
bool allow_move(int agent, int from, int to);
void end_step(const std::vector<State>& prev_states, const std::vector<State>& next_states);
void write_stats(SharedEnvironment* env);
}}
