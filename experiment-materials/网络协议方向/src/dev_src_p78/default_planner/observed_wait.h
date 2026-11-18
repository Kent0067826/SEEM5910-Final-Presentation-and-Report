#pragma once
#include "SharedEnv.h"
#include <utility>
#include <vector>

namespace ObservedWait {
void initialize(SharedEnvironment* env);
bool enabled();
int path_penalty(int from,int to);
void begin(SharedEnvironment* env);
int choose(int agent,const std::vector<std::pair<int,int>>& candidates,SharedEnvironment* env);
void assigned(int agent,int task,SharedEnvironment* env);
void finish(SharedEnvironment* env);
}
