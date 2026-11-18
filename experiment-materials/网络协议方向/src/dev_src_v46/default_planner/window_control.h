#pragma once
#include "SharedEnv.h"

// Experimental admission controller. It never changes motion commands.
namespace RobotWindow {
void initialize(SharedEnvironment* env);
void begin_schedule(SharedEnvironment* env);
bool allowed(int agent, int task, SharedEnvironment* env);
void assigned(int agent, int task, SharedEnvironment* env);
// v15: drop the admission bookkeeping of an agent whose (unopened) task is about to be re-matched
void release(int agent);
// v15: number of door lines the pickup leg of (agent, task) crosses, whether or not they are congested (placebo control)
int crossing_count(int agent, int task, SharedEnvironment* env);
// v18b: false when the move from cell `from` to the neighbouring cell `to` goes the wrong way through a one-way door
bool move_allowed(int from, int to);
// v24b (round 35): remove one directed move from the movement graph (used by guide-path search and PIBT through move_allowed)
void forbid_move(int from, int to);
// v18d: room index of a cell (-1 if regions are not in use) and the transit cost of a cell for a path from rstart to rgoal
int region_of(int cell);
// v18f: like move_allowed, plus the room-pause rule (entering a paused room only if the goal is inside it)
bool move_allowed_goal(int from, int to, int goal_cell);
int transit_pen(int cell, int rstart, int rgoal);
// v19: single-lane cuts ("bridges"): number of bridges (detected on first use), part id of a cell (-1 = bridge cell or small part), bridge cells
int bridge_count(SharedEnvironment* env);
int bridge_side(int b, int cell);
std::vector<int> bridge_cells(int b);
// v37 (round 52): true for a free cell within distance 1 of a detected cut's door cells (empty before detection)
bool door_zone(int cell);
void end_schedule(SharedEnvironment* env);
void observe(const SharedEnvironment* env, const std::vector<ExecutionCommand>& commands);
// v11: true while at least one door line is congested (its window is enforced)
bool any_line_active();
// v13 probe: number of (currently active) bottleneck lines separating two cells; 0 when no line model is in use.
int line_crossings(int a, int g);
// v14: smoothed share of forward attempts (all robots, whole map) that the executor had to stop. 0 = free flowing.
double global_blocked();
// v14c: true when the turn cost may be used: after a 100-tick observation period, while the map-wide signal is below `gate`,
// and only on maps where no door line has ever been measured as congested (blocked share >= 0.2).
bool free_flowing(double gate);
}
