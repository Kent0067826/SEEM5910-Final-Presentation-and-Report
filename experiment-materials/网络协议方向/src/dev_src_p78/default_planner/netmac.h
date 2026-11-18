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
bool red_active();
bool red_push(int agent);
bool esc_active();   // p37 escape channel
bool esc_push(int agent);
bool promoted(int agent);
// v25d: with ROBOT_BMAC_PROMOTE bit 4, promoted robots are ordered by distance to the passage (closest first; -1 if not promoted)
int promote_rank(int agent);
// p16 (HTTP/1.1 pipelining): 1 if the door rule on cut bridge wb (RobotWindow numbering) is serving the direction into side s
// (not draining) and that direction's pipe is empty (no crosser in its apron, nobody in the passage) at the last planning step
int pipe_idle(int wb, int s);
int door_idle(int wb);   // p68: cut passage and both aprons empty
// p21 (TCP SACK): 1 if cell v is a cut-bridge passage cell or lies within that bridge's apron (ROBOT_BMAC_APRON)
bool door_zone(int v);
// p24 (count only): ROBOT_DEFL_LOG -- executor records per tick why a door robot did not move (kind G/W/E/B), and door exits
bool defl_on();
void defl_exec(SharedEnvironment* env,int agent,char kind,int next_cell,int front);
void defl_move(int from,int to);
void defl_follow(SharedEnvironment* env,int agent,int kind);   // p25b count only
void initialize(SharedEnvironment* env, TrajLNS& lns);
// called once per PIBT step, before priorities are sorted
void begin_step(SharedEnvironment* env, TrajLNS& lns, const std::vector<State>& prev_states);
double key_bonus(int agent);
bool allow_move(int agent, int from, int to);
void end_step(const std::vector<State>& prev_states, const std::vector<State>& next_states);
void write_stats(SharedEnvironment* env);
}}
