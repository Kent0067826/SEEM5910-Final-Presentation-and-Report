// Default scheduler baseline implementation.
//
// Keeps persistent sets of free agents and free tasks across timesteps, then
// greedily matches each free agent to the task with minimum heuristic distance
// makespan. This is intentionally simple and serves as a reference scheduler.

#include "scheduler.h"
#include "window_control.h"
#include "task_congestion.h"
#include "nms_scheduler.h"
#include <algorithm>
#include <cstdlib>
#include <cstring>

namespace DefaultPlanner{

std::mt19937 mt;
std::unordered_set<int> free_agents;
std::unordered_set<int> free_tasks;

void schedule_initialize(int preprocess_time_limit, SharedEnvironment* env)
{
    // cout<<"schedule initialise limit" << preprocess_time_limit<<endl;
    // DefaultPlanner::init_heuristics(env);
    mt.seed(0);
    free_agents.clear();
    free_tasks.clear();
    RobotWindow::initialize(env);
    TaskCongestion::initialize(env);
    NmsScheduler::initialize(env);
    return;
}

void schedule_plan(int time_limit, std::vector<int> & proposed_schedule,  SharedEnvironment* env)
{
    //use at most half of time_limit to compute schedule, -10 for timing error tolerance
    //so that the remainning time are left for path planner
    TimePoint endtime = std::chrono::steady_clock::now() + std::chrono::milliseconds(time_limit);
    RobotWindow::begin_schedule(env);
    const char* work_mode = std::getenv("ROBOT_WORK_MODE");
    const bool fixed_work = work_mode != nullptr && std::strcmp(work_mode, "fixed") == 0;
    if (NmsScheduler::enabled()) {   // v15: LoRR 2024 winning scheduler (re-implementation), optionally with door-line admission
        NmsScheduler::plan(proposed_schedule, env);
        RobotWindow::end_schedule(env);
        return;
    }
    // cout<<"schedule plan limit" << time_limit <<endl;

    // the default scheduler keep track of all the free agents and unassigned (=free) tasks across timesteps
    free_agents.insert(env->new_freeagents.begin(), env->new_freeagents.end());
    free_tasks.insert(env->new_tasks.begin(), env->new_tasks.end());
    TaskCongestion::begin(env,!free_agents.empty()&&!free_tasks.empty());

    int min_task_i, min_task_makespan, dist, c_loc, count;
    clock_t start = clock();

    // iterate over the free agents to decide which task to assign to each of them
    std::unordered_set<int>::iterator it = free_agents.begin();
    while (it != free_agents.end())
    {
        //keep assigning until timeout
        if (!fixed_work && std::chrono::steady_clock::now() > endtime)
        {
            break;
        }
        int i = *it;

        assert(env->curr_task_schedule[i] == -1);
            
        min_task_i = -1;
        min_task_makespan = INT_MAX;
        count = 0;
        std::vector<std::pair<int,int>> task_candidates;

        // iterate over all the unassigned tasks to find the one with the minimum makespan for agent i
        for (int t_id : free_tasks)
        {
            //check for timeout every 10 task evaluations
            if (!fixed_work && count % 10 == 0 && std::chrono::steady_clock::now() > endtime)
            {
                break;
            }
            if (!RobotWindow::allowed(i, t_id, env)) { ++count; continue; }
            dist = 0;
            c_loc = env->curr_states.at(i).location;

            // iterate over the locations (errands) of the task to compute the makespan to finish the task
            // makespan: the time for the agent to complete all the errands of the task t_id in order
            // v13 probe (ROBOT_CROSS_COST=k): every door line a leg has to cross costs k extra cells, on the pickup AND the delivery leg.
            static int cross_cost = -1; if (cross_cost < 0) { const char* e = std::getenv("ROBOT_CROSS_COST"); cross_cost = e ? std::atoi(e) : 0; }
            for (int loc : env->task_pool[t_id].locations){
                dist += DefaultPlanner::get_h(env, c_loc, loc);
                if (cross_cost > 0) dist += cross_cost * RobotWindow::line_crossings(c_loc, loc);
                c_loc = loc;
            }

            // update the new minimum makespan
            if (dist < min_task_makespan){
                min_task_i = t_id;
                min_task_makespan = dist;
            }
            if (TaskCongestion::enabled()) task_candidates.emplace_back(t_id,dist);
            count++;            
        }

        if (TaskCongestion::enabled() && !task_candidates.empty()) {
            // Stable order retains the baseline tie break. Only the shortlist
            // receives the extra forecast cost; no task is hard-rejected.
            std::stable_sort(task_candidates.begin(),task_candidates.end(),
                [](const auto& a,const auto& b){return a.second<b.second;});
            min_task_i=TaskCongestion::choose(i,task_candidates,env);
        }

        // assign the best free task to the agent i (assuming one exists)
        if (min_task_i != -1){
            proposed_schedule[i] = min_task_i;
            RobotWindow::assigned(i, min_task_i, env);
            TaskCongestion::assigned(i, min_task_i, env);
            it = free_agents.erase(it);
            free_tasks.erase(min_task_i);
        }
        // nothing to assign
        else{
            proposed_schedule[i] = -1;
            it++;
        }
    }
    // #ifndef NDEBUG
    // cout << "Time Usage: " <<  ((float)(clock() - start))/CLOCKS_PER_SEC <<endl;
    // cout << "new free agents: " << env->new_freeagents.size() << " new tasks: "<< env->new_tasks.size() <<  endl;
    // cout << "free agents: " << free_agents.size() << " free tasks: " << free_tasks.size() << endl;
    // #endif
    RobotWindow::end_schedule(env);
    TaskCongestion::finish(env);
    return;
}
}
