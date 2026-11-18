#include <cstdlib>
// Default executor baseline implementation.
//
// The planner returns multi-step intent. This executor stages a window of actions,
// predicts future states for the next planning snapshot, and emits GO/STOP commands
// every execution tick using a Temporal Dependency Graph (TPG).
//
// Reference:
//   Ma, H., Kumar, T. S., & Koenig, S. (2017). Multi-agent path finding with
//   delay probabilities. AAAI Conference on Artificial Intelligence, Vol. 31.

#include "default_executor.h"
#include "window_control.h"

namespace DefaultPlanner{

    std::unordered_map<int, std::list<int>> tpg; //dependency graph for location visiting orders
    std::unordered_map<int, std::list<int>> temp_tpg; //temporary dependency graph for current timestep, used for process new plan

    vector<int> previous_locations; //record the previous locations of agents for tpg update
    vector<State> predicted_states;

    // the default process plan type is to keep a windoed actions to staged actions, window = min_planner_communication_time/simulator_time_limit, which means we will only execute the part of the plan that can be executed within the communication time limit.
    int window_size;
    bool first_execution = true;

void execute_initialize(int preprocess_time_limit, SharedEnvironment* env)
{
    window_size = (int)env->min_planner_communication_time / (env->action_time*env->max_counter) + 1; //calculate the window size based on the communication time limit and action execution time
    { const char* e = std::getenv("ROBOT_PLAN_EXTRA"); if (e) window_size += std::atoi(e); }   // v13 probe: larger action window
    previous_locations.resize(env->num_of_agents, -1);
}

vector<State> execute_process_new_plan(int sync_time_limit, Plan& plan_struct, vector<vector<Action>> & staged_actions, SharedEnvironment* env)
{
    // Default implementation: always append, update the predicted states based on moves
    if (predicted_states.size() != env->num_of_agents)
    {
        predicted_states = env->system_states;
    }

    if (first_execution)
    {
        for (int i = 0; i < env->num_of_agents; i++)
        {
            if (tpg.find(env->curr_states[i].location) == tpg.end())
            {
                tpg[env->curr_states[i].location].push_back(i);
            }
        }
        first_execution = false;
    }


    // v25g (round 36): ROBOT_EXEC_SYNCFIX=1 -- robots that finished a move in the last tick still head the visiting order of
    // the cell they just left (the order is only updated at the next tick). Without the fix, the ordering simulation below
    // treats that cell as still occupied, so every robot planned to enter it gets its new actions cut and waits for the
    // next plan. With the fix, those stale entries are removed first (exactly what the next tick would do).
    static int syncfix = -1; if (syncfix < 0) { const char* e = std::getenv("ROBOT_EXEC_SYNCFIX"); syncfix = e ? std::atoi(e) : 0; }
    for (int i = 0; i < env->num_of_agents; i++)
    {
        if (syncfix > 0) {
            const int prev = previous_locations[i], curr = env->system_states[i].location;
            if (prev >= 0 && prev != curr) { auto it = tpg.find(prev); if (it != tpg.end() && !it->second.empty() && it->second.front() == i) it->second.pop_front(); }
        }
        previous_locations[i] = env->system_states[i].location; //for use of keep track of tpg in move function
    }

    auto curr_states = predicted_states;

    int moves[4] = {1, env->cols, -1, -env->cols};
    std::vector<std::vector<Action>> plan = plan_struct.actions;

    //first apppend all actions and tpg location to window size
    for (int timestep = 0; timestep < plan[0].size() && timestep < window_size; timestep++)
    {
        for (int i = 0; i < plan.size(); i++)
        {
            int new_location = curr_states[i].location;
            int new_orientation = curr_states[i].orientation;

            if (plan[i][timestep] == Action::FW)
            {
                new_location = new_location + moves[curr_states[i].orientation];
                tpg[new_location].push_back(i);
            }
            else if (plan[i][timestep] == Action::CR)
            {
                new_orientation = (curr_states[i].orientation + 1) % 4;
            }
            else if (plan[i][timestep] == Action::CCR)
            {
                new_orientation = (curr_states[i].orientation - 1) % 4;
                if (new_orientation == -1)
                    new_orientation = 3;
            }
            // cout<<"agent "<<i<<" current prediceted state location from last iteration "<<predicted_states[i].location<<" orientation "<<predicted_states[i].orientation<<endl;
            // cout<<"agent "<<i<<" action "<<(plan[i][timestep] == Action::FW ? "FW" : (plan[i][timestep] == Action::CR ? "CR" : (plan[i][timestep] == Action::CCR ? "CCR" : (plan[i][timestep] == Action::NA ? "NA" : "W"))))<<" new prediceted state location "<<new_location<<" orientation "<<new_orientation<<endl;
            curr_states[i].location = new_location;
            curr_states[i].orientation = new_orientation;   
            curr_states[i].timestep+=1;

            if (plan[i][timestep] != Action::NA && plan[i][timestep] != Action::W)
            {
                staged_actions[i].push_back(plan[i][timestep]);
            }
        }
    }

    //now run a mcp simulation assuming no delays for a windowed size, and obtain the actions
    vector<int> action_index(env->num_of_agents,0); //keep track of the next action index for each agent in the staged actions 
    curr_states = env->system_states;
    temp_tpg.clear();

    // v16 (round 26): ROBOT_EXEC_DELAYHOLD=K -- in the ordering simulation, a robot that is in an execution delay right now
    // stays put for the first K simulated actions, so the passing order (TPG) lets the others go first where they can.
    static int delay_hold = -1; if (delay_hold < 0) { const char* e = std::getenv("ROBOT_EXEC_DELAYHOLD"); delay_hold = e ? std::atoi(e) : 0; }
    for (int t = 0; t < window_size; t++)
    {
        auto pre_states = curr_states;
        for (int i = 0; i < env->num_of_agents; i++)
        {
            if (delay_hold > 0 && t < delay_hold && env->system_states[i].delay.inDelay)
            {
                curr_states[i].timestep++;   // held: treated as waiting in the simulation
                continue;
            }

            if (staged_actions[i].size() <= action_index[i])//no action left to proceed
            {
                curr_states[i].timestep++;//treat as wait
                continue;
            }

            //simulate with mcp (no delay)
            Action curr_action = staged_actions[i][action_index[i]];
            int curr_location = curr_states[i].location;
            int curr_orientation = curr_states[i].orientation;
            int new_location = curr_location;
            int new_orientation = curr_orientation;
            // cout<<"agent "<<i<<" current prediceted state location from last iteration "<<predicted_states[i].location<<" orientation "<<predicted_states[i].orientation<<endl;
            // cout<<"agent "<<i<<" action "<<(curr_action == Action::FW ? "FW" : (curr_action == Action::CR ? "CR" : (curr_action == Action::CCR ? "CCR" : (curr_action == Action::NA ? "NA" : "W"))))<<" current state location "<<curr_location<<" orientation "<<curr_orientation<<endl;

            assert(tpg[curr_location].front() == i);

            if (curr_action == Action::FW)
            {
                new_location = curr_location + moves[curr_orientation];
                assert(!tpg[new_location].empty());
                if (tpg[new_location].front() == i)
                {
                    //you can go
                    action_index[i]++;
                }
                else
                {
                    new_location = curr_location; //cannot move because of the dependency, stay at the current location
                }
            }
            else if (curr_action == Action::CR)
            {
                new_orientation = (curr_orientation + 1) % 4;
                //you can go because it's just rotation
                action_index[i]++;
            }
            else if (curr_action == Action::CCR)
            {
                new_orientation = (curr_orientation - 1) % 4;
                if (new_orientation == -1)
                    new_orientation = 3;
                //you can go because it's just rotation
                action_index[i]++;
            }
            curr_states[i].location = new_location;
            curr_states[i].orientation = new_orientation;   
        }
        //clear dependency
        for (int i = 0; i < env->num_of_agents; i++)
        {
            if (t == 0)
            {
                temp_tpg[pre_states[i].location].push_back(i);
                // cout<<"inserting "<<i<<" into tpg loc "<<pre_states[i].location<<endl;
            }

            if (pre_states[i].location != curr_states[i].location) //agent move
            {
                //insert location into temp tpg, and pop the current location from tpg
                assert(tpg[pre_states[i].location].front() == i);
                tpg[pre_states[i].location].pop_front();
                temp_tpg[curr_states[i].location].push_back(i);
                // cout<<"inserting "<<i<<" into tpg loc "<<curr_states[i].location<<endl;
            }
        }
    }
    for (int i = 0; i < env->num_of_agents; i++)
    {
        if (action_index[i] < staged_actions[i].size())
        {
            staged_actions[i].resize(action_index[i]);//remove the actions that are not executed in the windowed simulation
            // cout<<"resizing staged actions for agent "<<i<<" to "<<action_index[i]<<endl;
        }
    }
    predicted_states = curr_states;
    tpg = temp_tpg;
    return predicted_states;
}

void execute_next_command(int exec_time_limit, std::vector<ExecutionCommand> & agent_command, SharedEnvironment* env)
{
    //update the tpg based on the current system states from last tick
    for (int i = 0; i < env->system_states.size(); i++)
    {
        int prev_location = previous_locations[i];
        int curr_location = env->system_states[i].location;
        // cout<<"tpg for agent "<<i<<" prev loc "<< prev_location<<" tpg first "<<tpg[prev_location].front()<<endl;
        assert(tpg[prev_location].front() == i);
        if (prev_location != curr_location && tpg[prev_location].front() == i)
        {
            //remove the agent from the previous location in tpg
            tpg[prev_location].pop_front();
            previous_locations[i] = curr_location;
        }
    }
    for (int i = 0; i < env->system_states.size(); i++)
    {

        mcp(i, agent_command, env);
    }
    RobotWindow::observe(env, agent_command);
    
}

// v46 (round 74, log only): ROBOT_EXEC_STOPLOG=<path> -- one line per robot and tick when the executor stops it or its staged
// action is a wait: "E t agent" (no staged action, STOP), "W t agent" (staged action is a wait), "B t agent cell front frontInDelay"
// (wants to move forward but another robot heads the visiting order of the target cell, STOP). Line-buffered; no effect on behaviour.
static std::FILE* stoplog() { static int init = 0; static std::FILE* f = nullptr;
    if (!init) { init = 1; const char* p = std::getenv("ROBOT_EXEC_STOPLOG"); if (p) { f = std::fopen(p, "w"); if (f) std::setvbuf(f, nullptr, _IOLBF, 0); } }
    return f; }
bool mcp(int agent_id, std::vector<ExecutionCommand> & agent_command, SharedEnvironment* env)
{
    std::FILE* slog = stoplog();
    // cout<<"mcp for "<<agent_id<<endl;
    if (env->staged_actions[agent_id].empty())
    {
        //no action, just stop and wait for the next plan, no tpg order clear
        agent_command[agent_id] = ExecutionCommand::STOP;
        if (slog) std::fprintf(slog, "E %d %d\n", env->system_timestep, agent_id);
        return false;
    }
    else if (env->staged_actions[agent_id].front() != Action::FW) 
    {
        //try to go but still stay at current location because it's not move forward, no tpg order clear
        agent_command[agent_id] = ExecutionCommand::GO;
        if (slog && env->staged_actions[agent_id].front() == Action::W) std::fprintf(slog, "W %d %d\n", env->system_timestep, agent_id);
        return false;
    }
    else
    {
        int moves[4] = {1, env->cols, -1, -env->cols};
        int curr_location = env->system_states[agent_id].location;
        int curr_orientation = env->system_states[agent_id].orientation;
        int next_location = curr_location + moves[curr_orientation];

        if (tpg[next_location].empty() || tpg[next_location].front() == agent_id)
        {
            //try to go and can go, clear the tpg order
            agent_command[agent_id] = ExecutionCommand::GO;

            // cout<<"mcp true, agent "<<agent_id<<" decided to move to "<<next_location<<endl;
            return true;
        }
        else
        {
                //the blocking agent cannot go, so we cannot go
                agent_command[agent_id] = ExecutionCommand::STOP;
                if (slog) { const int fr = tpg[next_location].front();
                    std::fprintf(slog, "B %d %d %d %d %d\n", env->system_timestep, agent_id, next_location, fr,
                                 (fr >= 0 && fr < (int)env->system_states.size() && env->system_states[fr].delay.inDelay) ? 1 : 0); }
                return false;
        }
    }
    
}


}
