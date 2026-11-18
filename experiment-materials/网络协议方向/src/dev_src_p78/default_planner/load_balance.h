#pragma once
#include "SharedEnv.h"
// v38 (round 53, load balancing): door-aware guide-path costs, read from a per-map file written by netmodel_r53/lbfiles.py.
//   ROBOT_LB_FILE=<file>   lines "cell door factor toll" for every door cell (cell = row * cols + col)
//   ROBOT_LB_CAP=1         LBC: the vertex-flow term of the guide-path search on a door cell is multiplied by `factor`
//                          = capacity of an ordinary cell / capacity of one lane of the door (volume / capacity, as in the
//                          link performance functions of traffic assignment); ordinary cells keep factor 1.
//   ROBOT_LB_TOLL=1        LBS: entering a door from outside costs `toll` extra moves (dual price of the door's capacity in the
//                          min-cost multicommodity flow at the network's sustainable throughput; system-optimal pricing).
// Both act only on maps with a single-lane link (the same structural switch as the global admission). Both unset -> identical to v37a.
namespace LoadBalance {
bool cap_on(SharedEnvironment* env);
double cap_factor(SharedEnvironment* env, int cell);
int toll(SharedEnvironment* env, int from, int to);
}
