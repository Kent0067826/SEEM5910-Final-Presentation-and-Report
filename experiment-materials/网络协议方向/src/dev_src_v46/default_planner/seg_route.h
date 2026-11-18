#pragma once
#include "SharedEnv.h"
// v42 (round 61, segment routing SR): each robot follows a door sequence drawn from the min-cost multicommodity flow at the
// network's maximum concurrent throughput (netmodel_r61/srsplit.py, written per map).
//   ROBOT_SR=1, ROBOT_SR_FILE=<file>  lines "R cell room", "D cell door", "P s t share k d1 ... dk".
// When the current goal of robot i changes, the robot draws one sequence from (room it stands in) to (room of the goal) with the
// listed shares (fixed seed). The guide-path search then charges P extra moves for entering a door that is not on the robot's
// sequence; P = number of free cells (longer than any detour). No sequence (robot not in a room, same room, no entry) -> no charge.
// Unset -> identical to v41a.
namespace SegRoute {
bool on(SharedEnvironment* env);
void select(SharedEnvironment* env, int agent, int start, int goal);   // sets the robot the next search is for
int toll(SharedEnvironment* env, int from, int to);                    // extra moves for the move from -> to
}
