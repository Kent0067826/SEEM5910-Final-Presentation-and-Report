#pragma once
#include "SharedEnv.h"
#include <vector>

// v15: re-implementation of the task scheduler of team "No Man's Sky", winner of all categories of the
// League of Robot Runners 2024 edition (MIT licence; original code: MAPF-Competition/Code-Archive,
// "2024 Competition/Team_No_Man's_Sky", scheduler-track commit ed9fbfc6b9ca407616e98f8f020e987b0f8cfe44,
// files Solution/Scheduler/scheduler_solver.cpp and scheduler.cpp).  What is reproduced, with the settings of that commit:
//  * free robots = robots without a task, plus (task change enabled) robots whose task has not been opened yet;
//    free tasks  = tasks without a robot, plus tasks that have not been opened yet;
//  * cost(r, t) = W * d(robot state -> first errand) + sum of the errand-chain distances of t, with orientation-aware
//    distances (the original uses W = 5 on every competition map it tuned);
//  * one global greedy matching: repeatedly take the cheapest (robot, task) pair among the robots' sorted lists.
// Not reproduced (disabled or tied to their own planner in that commit): annealing (SCHEDULER_LNS_TIME = 0),
// phantom agents (not defined), and the "scheduler trick" that inserts waypoints from their own planner.
// Optional (v15): door-line admission (method E) as a filter inside the greedy matching (ROBOT_POLICY=multicut ...).
namespace NmsScheduler {
bool enabled();
void initialize(SharedEnvironment* env);
void plan(std::vector<int>& proposed_schedule, SharedEnvironment* env);
// orientation-aware distance (actions) from (loc, orientation) to a target cell, any final orientation
int odist(SharedEnvironment* env, int loc, int orient, int target);
}
