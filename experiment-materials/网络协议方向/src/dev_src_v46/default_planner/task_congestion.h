#pragma once
#include "SharedEnv.h"
#include <utility>
#include <vector>

// Experimental assignment-only congestion prediction. It makes no movement
// reservations and leaves the baseline path planner and executor in charge.
namespace TaskCongestion {
void initialize(SharedEnvironment* env);
bool enabled();
void begin(SharedEnvironment* env, bool need_forecast=true);
int choose(int agent, const std::vector<std::pair<int,int>>& candidates,
           SharedEnvironment* env); // (task id, original distance), best first
void assigned(int agent, int task, SharedEnvironment* env);
void finish(SharedEnvironment* env);
}
