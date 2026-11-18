#pragma once
#include "SharedEnv.h"
// v30 (round 43): bandwidth-delay credit on every room-to-room link (ROBOT_LINK=1); see link_credit.cpp.
namespace LinkCredit {
void initialize(SharedEnvironment* env);
void begin_schedule(SharedEnvironment* env);
bool allowed(int agent, int task, SharedEnvironment* env);
void assigned(int agent, int task, SharedEnvironment* env);
void release(int agent);
// v31: true where the link credit is active and ROBOT_LINK_ONLY=1 (it then replaces the cut credit)
bool replaces_cuts();
}
