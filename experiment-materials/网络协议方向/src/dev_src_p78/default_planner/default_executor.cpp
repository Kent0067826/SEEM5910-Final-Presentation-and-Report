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
#include "netmac.h"
#include <unordered_set>
#include <algorithm>

namespace DefaultPlanner{

    std::unordered_map<int, std::list<int>> tpg; //dependency graph for location visiting orders
    std::unordered_map<int, std::list<int>> temp_tpg; //temporary dependency graph for current timestep, used for process new plan

    vector<int> previous_locations; //record the previous locations of agents for tpg update
    vector<State> predicted_states;

    // the default process plan type is to keep a windoed actions to staged actions, window = min_planner_communication_time/simulator_time_limit, which means we will only execute the part of the plan that can be executed within the communication time limit.
    int window_size;
    long long sack_swaps = 0, sack_plans = 0;   // p21
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

    // p45 (log only): ROBOT_EXEC_PLANLOG=<path> -- per new plan and robot "P tick agent before appended aftercut" (staged action counts).
    static std::FILE* plog = [](){ const char* p = std::getenv("ROBOT_EXEC_PLANLOG"); std::FILE* f = p ? std::fopen(p, "w") : nullptr; if (f) std::setvbuf(f, nullptr, _IOFBF, 1 << 20); return f; }();
    std::vector<int> pl_before, pl_app; if (plog) { pl_before.resize(env->num_of_agents); for (int i = 0; i < env->num_of_agents; i++) pl_before[i] = int(staged_actions[i].size()); }
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

    // p21 (TCP SACK, RFC 2018): ROBOT_SACK=1 -- in a cut door's zone (passage cells + apron, NetMac::door_zone), when the robot next in
    // a cell's visiting order is in an execution delay and the one right behind it is not, and the second comes from the side (their
    // routes up to the cell share no cell and neither stands on the other's route before it), the second goes first. Every later cell
    // both robots pass gets the same swap, and only if the two are adjacent there too, so the order stays consistent. At most one swap
    // per cell and plan. ROBOT_SACK_LOG=<path>: number of swaps at exit (log only).
    static int sack = -1; if (sack < 0) { const char* e = std::getenv("ROBOT_SACK"); sack = e ? std::atoi(e) : 0;
        if (sack > 0 && std::getenv("ROBOT_SACK_LOG")) std::atexit([]{ if (std::FILE* f = std::fopen(std::getenv("ROBOT_SACK_LOG"), "w")) { std::fprintf(f, "swaps %lld plans %lld\n", sack_swaps, sack_plans); std::fclose(f); } }); }
    if (sack > 0)
    {
        ++sack_plans;
        const int A = env->num_of_agents;
        vector<vector<int>> route(A);   // cells entered from the current location along the staged actions
        vector<char> simple(A, 1);
        for (int i = 0; i < A; i++)
        {
            int loc = env->system_states[i].location, ori = env->system_states[i].orientation;
            std::unordered_set<int> seen{loc};
            for (Action ac : staged_actions[i])
            {
                if (ac == Action::FW) { loc += moves[ori]; route[i].push_back(loc); if (!seen.insert(loc).second) simple[i] = 0; }
                else if (ac == Action::CR) ori = (ori + 1) % 4;
                else if (ac == Action::CCR) ori = (ori + 3) % 4;
            }
        }
        std::unordered_set<int> touched;
        for (auto& kv : tpg)
        {
            const int X = kv.first; auto& L = kv.second;
            if (L.size() < 2 || touched.count(X) || !NetMac::door_zone(X)) continue;
            for (auto it = L.begin(); std::next(it) != L.end(); ++it)
            {
                const int a = *it, b = *std::next(it);
                if (a < 0 || b < 0 || a >= A || b >= A || a == b || !simple[a] || !simple[b]) continue;
                if (!env->system_states[a].delay.inDelay || env->system_states[b].delay.inDelay) continue;
                if (env->system_states[a].location == X || env->system_states[b].location == X) continue;
                auto ia = std::find(route[a].begin(), route[a].end(), X), ib = std::find(route[b].begin(), route[b].end(), X);
                if (ia == route[a].end() || ib == route[b].end()) continue;
                // position of each cell on the two routes (current location = -1, i.e. before X)
                std::unordered_map<int,int> pa{{env->system_states[a].location, -1}}, pb{{env->system_states[b].location, -1}};
                for (int k = 0; k < (int)route[a].size(); k++) pa[route[a][k]] = k;
                for (int k = 0; k < (int)route[b].size(); k++) pb[route[b][k]] = k;
                const int xa = int(ia - route[a].begin()), xb = int(ib - route[b].begin());
                bool ok = true; vector<int> shared;
                for (const auto& q : pb)
                {
                    auto f = pa.find(q.first); if (f == pa.end()) continue;
                    if (q.second < xb || f->second < xa) { ok = false; break; }   // shared before X: b would have to pass a
                    shared.push_back(q.first);
                }
                if (!ok) continue;
                for (int c : shared)
                {
                    if (touched.count(c)) { ok = false; break; }
                    auto t = tpg.find(c); if (t == tpg.end()) { ok = false; break; }
                    auto ja = std::find(t->second.begin(), t->second.end(), a);
                    if (ja == t->second.end() || std::next(ja) == t->second.end() || *std::next(ja) != b) { ok = false; break; }
                    if (t->second.front() == a && env->system_states[a].location == c) { ok = false; break; }
                }
                if (!ok) continue;
                for (int c : shared)
                {
                    auto& Lc = tpg[c]; auto ja = std::find(Lc.begin(), Lc.end(), a);
                    std::iter_swap(ja, std::next(ja)); touched.insert(c);
                }
                ++sack_swaps;
                break;
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
    if (plog) { pl_app.resize(env->num_of_agents); for (int i = 0; i < env->num_of_agents; i++) pl_app[i] = int(staged_actions[i].size()); }
    for (int i = 0; i < env->num_of_agents; i++)
    {
        if (action_index[i] < staged_actions[i].size())
        {
            staged_actions[i].resize(action_index[i]);//remove the actions that are not executed in the windowed simulation
            // cout<<"resizing staged actions for agent "<<i<<" to "<<action_index[i]<<endl;
        }
    }
    if (plog) { for (int i = 0; i < env->num_of_agents; i++) std::fprintf(plog, "P %d %d %d %d %d%c", env->system_timestep, i, pl_before[i], pl_app[i], int(staged_actions[i].size()), 10); std::fflush(plog); }
    predicted_states = curr_states;
    tpg = temp_tpg;
    return predicted_states;
}

static std::vector<int> defl_front;   // p25b count only: TPG front robot for agents held (B) this tick
namespace Rfd { void observe(SharedEnvironment* env); }   // p56, search.cpp
void execute_next_command(int exec_time_limit, std::vector<ExecutionCommand> & agent_command, SharedEnvironment* env)
{
    RobotWindow::cd_tick(env);   // p06
    Rfd::observe(env);   // p56: route flap damping figure of merit
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
            if (NetMac::defl_on()) NetMac::defl_move(prev_location, curr_location);   // p24 count only
            previous_locations[i] = curr_location;
        }
    }
    if (NetMac::defl_on()) defl_front.assign(env->system_states.size(), -1);   // p25b count only
    for (int i = 0; i < env->system_states.size(); i++)
    {

        mcp(i, agent_command, env);
    }
    if (NetMac::defl_on())   // p25b count only: was the front robot leaving the target cell in this same tick?
    {
        const int moves[4] = {1, env->cols, -1, -env->cols}; const int A = env->system_states.size();
        for (int i = 0; i < A; i++)
        {
            const int f = defl_front[i]; if (f < 0 || f >= A) continue;
            const auto& si = env->system_states[i]; const auto& sf = env->system_states[f];
            const int X = si.location + moves[si.orientation];
            if (sf.delay.inDelay || sf.location != X) continue;
            const bool leaving = agent_command[f] == ExecutionCommand::GO && !env->staged_actions[f].empty()
                                 && env->staged_actions[f].front() == Action::FW && X + moves[sf.orientation] != si.location;
            NetMac::defl_follow(env, i, leaving ? (sf.orientation == si.orientation ? 2 : 1) : 3);
        }
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
        if (NetMac::defl_on()) NetMac::defl_exec(env, agent_id, 'E', -1, -1);   // p24 count only
        return false;
    }
    else if (env->staged_actions[agent_id].front() != Action::FW) 
    {
        //try to go but still stay at current location because it's not move forward, no tpg order clear
        agent_command[agent_id] = ExecutionCommand::GO;
        if (slog && env->staged_actions[agent_id].front() == Action::W) std::fprintf(slog, "W %d %d\n", env->system_timestep, agent_id);
        if (NetMac::defl_on()) NetMac::defl_exec(env, agent_id, env->staged_actions[agent_id].front() == Action::W ? 'W' : 'G', -1, -1);
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
            if (NetMac::defl_on()) NetMac::defl_exec(env, agent_id, 'G', next_location, -1);

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
                if (NetMac::defl_on()) NetMac::defl_exec(env, agent_id, 'B', next_location, tpg[next_location].front());
                if (NetMac::defl_on() && agent_id < (int)defl_front.size()) defl_front[agent_id] = tpg[next_location].front();
                return false;
        }
    }
    
}


}
