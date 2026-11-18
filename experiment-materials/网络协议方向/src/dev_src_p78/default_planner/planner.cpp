// Default planner baseline implementation.
//
// For each planning episode, this module updates guide paths with a bounded
// traffic-flow phase (Frank-Wolfe optimisation), then runs PIBT to produce
// a multi-step plan. Internal rollout builds future steps; the environment
// snapshot is restored after planning.
//
// References:
//   Chen, Z., Harabor, D., Li, J., & Stuckey, P. J. (2024). Traffic flow
//   optimisation for lifelong multi-agent path finding. AAAI Conference on
//   Artificial Intelligence, Vol. 38, No. 18, pp. 20674-20682.
//   https://ojs.aaai.org/index.php/AAAI/article/view/30054/31856
//
//   Okumura, K., et al. (2022). Priority Inheritance with Backtracking (PIBT)
//   for iterative multi-agent path finding. Artificial Intelligence, Vol. 310.

#include "planner.h"
#include "heuristics.h"
#include "SharedEnv.h"
#include "pibt.h"
#include "netmac.h"
#include "flow.h"
#include "window_control.h"
#include "const.h"
#include <chrono>
#include <iostream>
#include <cstdlib>
#include <cstring>
#include <fstream>


namespace DefaultPlanner{
    static std::vector<int> p49_kprev; static long long p49_gp_ok = 0, p49_gp_fail = 0;   // p49
    static int k_prev_p49(int i) { return i < int(p49_kprev.size()) ? p49_kprev[i] : 0; }
    static void k_set_p49(int i, int k) { if (int(p49_kprev.size()) <= i) p49_kprev.resize(i + 1, 0); p49_kprev[i] = k; }

    static bool fixed_planner_work_mode()
    {
        static const bool enabled = [](){
            const char* value = std::getenv("ROBOT_WORK_MODE");
            return value != nullptr && std::strcmp(value, "fixed") == 0;
        }();
        return enabled;
    }

    static const char* debug_action_to_string(Action action)
    {
        switch (action)
        {
            case Action::FW: return "FW";
            case Action::CR: return "CR";
            case Action::CCR: return "CCR";
            case Action::W: return "W";
            case Action::NA: return "NA";
            default: return "UNKNOWN";
        }
    }

    //default planner data
    std::vector<int> decision; 
    std::vector<int> prev_decision;
    std::vector<double> p;
    std::vector<State> prev_states;
    std::vector<State> next_states;
    std::vector<int> ids;
    std::vector<double> p_copy;
    std::vector<bool> occupied;
    std::vector<DCR> decided;
    std::vector<bool> checked;
    std::vector<bool> require_guide_path;
    std::vector<int> dummy_goals;
    TrajLNS trajLNS;
    std::mt19937 mt1;
    // v16 (round 26): robots that are in an execution delay (fault) when the plan is made are held in place for the first
    // ROBOT_DELAY_FREEZE planned steps, so that other robots plan around them instead of queueing behind them
    // (network analogue: a failed link is reported to the routing layer instead of letting packets queue behind it).
    std::vector<char> v16_frozen; int v16_step = 0;
    extern std::vector<int> v16_block_pen;
    // v16: ROBOT_DELAY_REROUTE=P puts a cost of P cells on every cell occupied by a delayed robot and recomputes the guide path of
    // each robot whose guide path reaches such a cell within ROBOT_DELAY_HORIZON cells (fast reroute around a failed link).
    static int delay_reroute_pen() { static int v = -1; if (v < 0) { const char* e = std::getenv("ROBOT_DELAY_REROUTE"); v = e ? std::atoi(e) : 0; } return v; }
    static int delay_horizon() { static int v = -1; if (v < 0) { const char* e = std::getenv("ROBOT_DELAY_HORIZON"); v = e ? std::atoi(e) : 12; } return v; }
    long long v16_reroutes = 0;
    // v17 (round 27): which agents are being rerouted in this plan (not because their goal changed), and an optional detour bound:
    // ROBOT_REROUTE_DETOUR=B keeps the old guide path when the new one is more than B cells longer than what was left of the old one
    // (bounded-stretch rerouting: in a maze there is usually no short alternative, so nothing changes there).
    std::vector<char> v17_rflag; long long v17_rejected = 0;
    static int reroute_detour() { static int v = -2; if (v == -2) { const char* e = std::getenv("ROBOT_REROUTE_DETOUR"); v = e ? std::atoi(e) : -1; } return v; }
    // p14: ROBOT_FRER=B (IEEE 802.1CB-style standby route): a delayed robot standing on a one-lane cell blocks that whole
    // one-lane stretch (door / corridor); robots whose guide path reaches it within ROBOT_DELAY_HORIZON cells switch to a route
    // that avoids it (another door), kept only if it is at most B cells longer than the rest of the old route. Unset = off.
    static int frer_b() { static int v = -2; if (v == -2) { const char* e = std::getenv("ROBOT_FRER"); v = e ? std::atoi(e) : -1; } return v; }
    long long p14_frer_reroutes = 0;
    static int delay_freeze_steps() { static int v = -1; if (v < 0) { const char* e = std::getenv("ROBOT_DELAY_FREEZE"); v = e ? std::atoi(e) : 0; } return v; }

    static State rollout_next_state(const State& state, Action action, const SharedEnvironment* env)
    {
        State next = state;
        next.timestep = state.timestep + 1;

        if (action == Action::CR)
        {
            next.orientation = (state.orientation + 1) % 4;
            return next;
        }
        if (action == Action::CCR)
        {
            next.orientation = (state.orientation + 3) % 4;
            return next;
        }
        if (action != Action::FW)
        {
            return next;
        }

        int delta = 0;
        if (state.orientation == 0) delta = 1;
        if (state.orientation == 1) delta = env->cols;
        if (state.orientation == 2) delta = -1;
        if (state.orientation == 3) delta = -env->cols;

        int next_loc = state.location + delta;
        if (next_loc >= 0 && next_loc < env->map.size() && validateMove(state.location, next_loc, env))
        {
            next.location = next_loc;
        }
        return next;
    }

    static void initialize_dummy_goals_if_needed(SharedEnvironment* env)
    {
        if (env->curr_timestep != 0)
            return;
        dummy_goals.resize(env->num_of_agents);
        for(int i=0; i<env->num_of_agents; i++)
        {
            dummy_goals.at(i) = env->start_states.at(i).location;
        }
    }

    static void setup_multistep_episode_state(SharedEnvironment* env, TimePoint flow_end_time,
                                              std::vector<double>& local_priority)
    {
        prev_decision.clear();
        prev_decision.resize(env->map.size(), -1);
        for(int i=0; i<env->num_of_agents; i++)
        {
            // initialise heuristic tables for goals
            if (fixed_planner_work_mode() || std::chrono::steady_clock::now() < flow_end_time){
                for (int j = 0; j < env->goal_locations[i].size(); j++)
                {
                    int goal_loc = env->goal_locations[i][j].first;
                    if (trajLNS.heuristics.find(goal_loc) == trajLNS.heuristics.end() ||
                        trajLNS.heuristics[goal_loc].empty()){
                        init_heuristic(trajLNS.heuristics[goal_loc], env, goal_loc);
                    }
                }
            }

            // set goals/tasks
            // v20: ROBOT_IDLE_STAY=1 -> a robot without a task stays where it is (as in WPPL's "disabled" agents) instead of
            // walking back to its start cell
            { static int idle_stay = -1; if (idle_stay < 0) { const char* e = std::getenv("ROBOT_IDLE_STAY"); idle_stay = e ? std::atoi(e) : 0; }
              if (idle_stay && env->goal_locations[i].empty()) dummy_goals.at(i) = env->curr_states[i].location; }
            if (env->goal_locations[i].empty()){
                trajLNS.tasks[i] = dummy_goals.at(i);
                local_priority[i] = p_copy[i];
            }
            else{
                trajLNS.tasks[i] = env->goal_locations[i].front().first;
            }
            if (p48_on()) { if (int(p48_adv.size()) != env->num_of_agents) p48_adv.assign(env->num_of_agents, 0); p48_adv[i] = 0; k_set_p49(i, 0); if (int(p49_gp.size()) != env->num_of_agents) p49_gp.assign(env->num_of_agents, 0); p49_gp[i] = 0; }   // p48: new plan, system goals are fresh
            if (p48_on() && std::getenv("ROBOT_ERRAND_DEBUG")) { static long long n1=0,nm=0; if(!env->goal_locations[i].empty()){ ++n1; if(env->goal_locations[i].size()>1) ++nm; } if(i==0) { static int calls=0; if(++calls%50==1) std::fprintf(stderr,"[p48] call=%d t=%d robots-with-goal %lld with>1 errands %lld\n",calls,env->system_timestep,n1,nm); } }

            // detect guide-path mismatch (goal changed or no guide path)
            require_guide_path[i] = false;
            if (trajLNS.trajs[i].empty() || trajLNS.trajs[i].back() != trajLNS.tasks[i])
                require_guide_path[i] = true;

            // update per-agent transient planning state
            assert(env->start_states[i].location >=0);
            prev_states[i] = env->start_states[i];
            next_states[i] = State();
            prev_decision[env->start_states[i].location] = i;
            if (decided[i].loc == -1){
                decided[i].loc = env->start_states[i].location;
                assert(decided[i].state == DONE::DONE);
            }
            if (prev_states[i].location == decided[i].loc){
                decided[i].state = DONE::DONE;
            }
            if (decided[i].state == DONE::NOT_DONE){
                decision.at(decided[i].loc) = i;
                next_states[i] = State(decided[i].loc,-1,-1);
            }

            // cross-episode priority update
            if(require_guide_path[i])
                local_priority[i] = p_copy[i];
            else if (!env->goal_locations[i].empty())
                local_priority[i] = local_priority[i]+1;

            if (!env->goal_locations[i].empty() && trajLNS.neighbors[env->start_states[i].location].size() == 1){
                local_priority[i] = local_priority[i] + 10;
            }
        }
    }

    static void update_guide_paths_once_for_multistep(SharedEnvironment* env, TimePoint flow_end_time)
    {
        // one-time guide-path update for goal-changed agents
        for (int i = 0; i < env->num_of_agents; i++)
        {
            if (!fixed_planner_work_mode() && std::chrono::steady_clock::now() > flow_end_time)
                break;
            if (require_guide_path[i]){
                std::vector<int> old_traj = trajLNS.trajs[i];
                const s_node old_goal = trajLNS.goal_nodes[i];
                if (!trajLNS.trajs[i].empty())
                    remove_traj(trajLNS, i);
                // p14: the FRER penalty only shapes the reroute of robots switched by FRER, not robots that got a new goal
                std::vector<int> p14_saved; const bool p14_hide = frer_b() >= 0 && !(i < int(v17_rflag.size()) && v17_rflag[i]);
                if (p14_hide) p14_saved.swap(v16_block_pen);
                const bool p14_ok = update_traj(trajLNS, i, fixed_planner_work_mode() ? nullptr : &flow_end_time);
                if (p14_hide) p14_saved.swap(v16_block_pen);
                if (!p14_ok){
                    trajLNS.trajs[i] = old_traj;
                    if (!old_traj.empty()){
                        add_traj(trajLNS, i);
                    }
                    break;
                }
                const int detour_b = frer_b() >= 0 ? frer_b() : reroute_detour();
                if (detour_b >= 0 && i < int(v17_rflag.size()) && v17_rflag[i] && !old_traj.empty()) {
                    const int here = env->curr_states[i].location; size_t k = 0;
                    while (k < old_traj.size() && old_traj[k] != here) ++k;
                    if (k == old_traj.size()) k = 0;
                    const long long old_rem = (long long)old_traj.size() - 1 - (long long)k, new_len = (long long)trajLNS.trajs[i].size() - 1;
                    if (new_len > old_rem + detour_b) {
                        remove_traj(trajLNS, i);
                        trajLNS.trajs[i] = old_traj; trajLNS.goal_nodes[i] = old_goal;
                        add_traj(trajLNS, i); update_dist_2_path(trajLNS, i);
                        ++v17_rejected;
                    }
                }
            }
        }

        // one-time FW optimization in the flow allocation phase
        std::unordered_set<int> updated;
        {   // p14: Frank-Wolfe re-optimises every robot's flow; the FRER penalty must not leak into it
            std::vector<int> p14_saved; if (frer_b() >= 0) p14_saved.swap(v16_block_pen);
            frank_wolfe(trajLNS, updated, flow_end_time);
            if (frer_b() >= 0) p14_saved.swap(v16_block_pen);
        }
    }

    static int v13_prio_mode() { static int m = -1; if (m < 0) { const char* e = std::getenv("ROBOT_PRIO"); std::string s = e ? e : "";
        m = s == "srpt" ? 1 : s == "mix" ? 2 : s == "far" ? 3 : 0; } return m; }
    static double v13_prio_scale() { static double v = -1; if (v < 0) { const char* e = std::getenv("ROBOT_PRIO_SCALE"); v = e ? std::stod(e) : 10.0; } return v; }
    static double v13_door_bonus() { static double v = -1; if (v < 0) { const char* e = std::getenv("ROBOT_DOOR_PRIO"); v = e ? std::stod(e) : 0.0; } return v; }

    static long long p48_adv_steps = 0;   // p48 debug count
    static void refresh_multistep_step_state(SharedEnvironment* env, std::vector<double>& local_priority)
    {
        prev_decision.clear();
        prev_decision.resize(env->map.size(), -1);
        for(int i=0; i<env->num_of_agents; i++)
        {
            if (env->goal_locations[i].empty()){
                trajLNS.tasks[i] = dummy_goals.at(i);
                local_priority[i] = p_copy[i];
            }
            else{
                trajLNS.tasks[i] = env->goal_locations[i].front().first;
                local_priority[i] = local_priority[i] + 1;
            }
            // p48 (TCP delayed ACK -> immediate ACK, ROBOT_ERRAND_ADVANCE=1): inside the plan's rollout, a robot standing on its current
            // errand is treated as having finished it and heads for the task's next errand for the remaining steps (the system does the same
            // when the plan is executed; the last errand is left alone because the next task is not known yet).
            if (p48_on() && !env->goal_locations[i].empty() && i < int(p48_adv.size())) {
                // the system only reveals the current errand in goal_locations; the remaining ones come from the task pool
                std::vector<int> rem; const int tid = i < int(env->curr_task_schedule.size()) ? env->curr_task_schedule[i] : -1;
                auto it = env->task_pool.find(tid);
                if (it != env->task_pool.end()) for (size_t q = it->second.idx_next_loc; q < it->second.locations.size(); ++q) rem.push_back(it->second.locations[q]);
                if (rem.empty() || rem[0] != env->goal_locations[i].front().first) rem.assign(1, env->goal_locations[i].front().first);
                int& k = p48_adv[i]; const int sz = int(rem.size());
                while (k + 1 < sz && env->start_states[i].location == rem[k]) ++k;
                const int k_before = k_prev_p49(i);
                if (k > 0) { const int g = rem[k]; trajLNS.tasks[i] = g; ++p48_adv_steps;
                    if (trajLNS.heuristics[g].empty()) init_heuristic(trajLNS.heuristics[g], env, g);
                    // p49 (ROBOT_ERRAND_ADVANCE=2): on the step the target changes, re-plan this robot's guide path to the new errand with the
                    // same flow-aware A* as at step 0 (old path taken out of the flow table first); fall back to plain distance if none found.
                    if (p48_on() == 2 && k != k_before) {
                        remove_traj(trajLNS, i);
                        s_node gn = astar(env, trajLNS.flow, trajLNS.heuristics[g], trajLNS.trajs[i], trajLNS.mem, env->start_states[i].location, g, &(trajLNS.neighbors), nullptr);
                        if (gn.id != -1) { trajLNS.goal_nodes[i] = gn; add_traj(trajLNS, i); update_dist_2_path(trajLNS, i); p49_gp[i] = 1; ++p49_gp_ok; }
                        else { p49_gp[i] = 0; ++p49_gp_fail; }
                    }
                }
                k_set_p49(i, k);
                if (std::getenv("ROBOT_ERRAND_DEBUG") && i == 0) { static int c2 = 0; if (++c2 % 50 == 1) std::fprintf(stderr, "[p48b] t=%d advanced-robot-steps %lld guide-ok %lld fail %lld%c", env->system_timestep, p48_adv_steps, p49_gp_ok, p49_gp_fail, 10); }
            }

            assert(env->start_states[i].location >=0);
            prev_states[i] = env->start_states[i];
            next_states[i] = State();
            prev_decision[env->start_states[i].location] = i;

            if (prev_states[i].location == decided[i].loc){
                decided[i].state = DONE::DONE;
            }
            if (decided[i].state == DONE::NOT_DONE){
                decision.at(decided[i].loc) = i;
                next_states[i] = State(decided[i].loc,-1,-1);
            }

            if (!env->goal_locations[i].empty() && trajLNS.neighbors[env->start_states[i].location].size() == 1){
                local_priority[i] = local_priority[i] + 10;
            }
        }
    }

    static void run_multistep_pibt_once(SharedEnvironment* env, std::vector<double>& local_priority,
                                        std::vector<Action>& one_step_actions)
    {
        const auto start_time = std::chrono::steady_clock::now();
        NetMac::begin_step(env, trajLNS, prev_states);
        if (NetMac::any_enabled()) {
            // wait-v7: transient sort key = persistent PIBT priority + link-layer bonus (max-pressure / backoff)
            std::vector<double> key(env->num_of_agents);
            for (int a = 0; a < env->num_of_agents; ++a) key[a] = local_priority.at(a) + NetMac::key_bonus(a);
            std::stable_sort(ids.begin(), ids.end(), [&](int a, int b) { return key[a] > key[b]; });
        } else if (v13_prio_mode() != 0 || v13_door_bonus() > 0) {
            // v13: "who goes first" key. srpt: robots closest to their current goal first (like SRPT / pFabric);
            // mix: age minus distance/scale; door bonus: robots standing in a 1-wide passage are drained first (in-transit priority).
            std::vector<double> key(env->num_of_agents);
            const int mode = v13_prio_mode(); const double scale = v13_prio_scale(), door = v13_door_bonus();
            for (int a = 0; a < env->num_of_agents; ++a) {
                double k = local_priority.at(a);
                const int loc = prev_states[a].location;
                if (!env->goal_locations[a].empty() && mode != 0) {
                    const double d = get_h(env, loc, trajLNS.tasks[a]);
                    if (mode == 1) k = 1e6 - d + 1e-3 * local_priority.at(a);          // pure SRPT, age only breaks ties
                    else if (mode == 2) k = local_priority.at(a) - d / scale;           // age minus scaled distance
                    else if (mode == 3) k = -1e6 + d + 1e-3 * local_priority.at(a);    // control: farthest first
                }
                if (door > 0 && !env->goal_locations[a].empty()) {
                    const auto& nb = trajLNS.neighbors[loc];
                    if (nb.size() == 2 && nb[0] + nb[1] == 2 * loc) k += door;        // two opposite free neighbours: 1-wide passage
                }
                key[a] = k;
            }
            std::stable_sort(ids.begin(), ids.end(), [&](int a, int b) { return key[a] > key[b]; });
        } else
        std::sort(ids.begin(), ids.end(), [&](int a, int b) {
                return local_priority.at(a) > local_priority.at(b);
            }
        );
        if (NetMac::demote_active()) std::stable_partition(ids.begin(), ids.end(), [](int a) { return !NetMac::blocked(a); });
        if (NetMac::promote_active()) {
            auto mid = std::stable_partition(ids.begin(), ids.end(), [](int a) { return NetMac::promoted(a); });
            static int pm = -1; if (pm < 0) { const char* e = std::getenv("ROBOT_BMAC_PROMOTE"); pm = e ? std::atoi(e) : 0; }
            if (pm & 4) std::stable_sort(ids.begin(), mid, [](int a, int b) { return NetMac::promote_rank(a) < NetMac::promote_rank(b); });
        }
        if (NetMac::red_active()) std::stable_partition(ids.begin(), ids.end(), [](int a) { return NetMac::red_push(a); });   // p23 RED
        if (NetMac::esc_active()) std::stable_partition(ids.begin(), ids.end(), [](int a) { return NetMac::esc_push(a); });   // p37 escape channel
        //clear reset occupied
        std::fill(occupied.begin(), occupied.end(), false);
        if (delay_freeze_steps() > 0 && v16_step < delay_freeze_steps() && v16_frozen.size() == size_t(env->num_of_agents)) {
            for (int i = 0; i < env->num_of_agents; ++i) {
                if (!v16_frozen[i]) continue;
                const int loc = prev_states[i].location;
                if (decided[i].state == DONE::NOT_DONE && decided[i].loc >= 0 && decision.at(decided[i].loc) == i) decision.at(decided[i].loc) = -1;
                if (decision.at(loc) != -1 && decision.at(loc) != i) continue;   // cell already claimed (should not happen)
                decided[i] = DCR({loc, DONE::DONE});
                next_states[i] = State(loc, -1, -1);
                decision.at(loc) = i;
            }
        }

        for (int i : ids){
            if (decided[i].state == DONE::NOT_DONE){
                continue;
            }
            if (next_states[i].location==-1){
                assert(prev_states[i].location >=0 && prev_states[i].location < env->map.size());
                causalPIBT(i,-1,prev_states,next_states,
                    prev_decision,decision,
                    occupied, trajLNS);
            }
        }
        NetMac::end_step(prev_states, next_states);

        one_step_actions.resize(env->num_of_agents);
        for (int id : ids){
            if (next_states.at(id).location!= -1)
                decision.at(next_states.at(id).location) = -1;
            if (next_states.at(id).location >=0){
                decided.at(id) = DCR({next_states.at(id).location,DONE::NOT_DONE});
            }
            one_step_actions.at(id) = getAction(prev_states.at(id),decided.at(id).loc, env);
            checked.at(id) = false;
        }
        // v13 probe (ROBOT_PRETURN=1): a robot told to wait turns toward the neighbour it wants next instead of idling.
        // Rotating in place never conflicts; network analogue: look-ahead routing (prepare the next hop while blocked).
        {
            static int preturn = -1; if (preturn < 0) { const char* e = std::getenv("ROBOT_PRETURN"); preturn = e ? std::atoi(e) : 0; }
            if (preturn > 0) for (int id = 0; id < env->num_of_agents; ++id) {
                if (one_step_actions[id] != Action::W || env->goal_locations[id].empty()) continue;
                const int loc = prev_states[id].location, ori = prev_states[id].orientation;
                if (ori < 0 || decided[id].loc != loc) continue;
                const int step4[4] = {1, env->cols, -1, -env->cols};
                int best_h = get_gp_h(trajLNS, id, loc), best_d = -1;
                for (int d = 0; d < 4; ++d) {
                    const int nb = loc + step4[d];
                    bool ok = false; for (int x : trajLNS.neighbors[loc]) ok = ok || x == nb;
                    if (!ok) continue;
                    const int h = get_gp_h(trajLNS, id, nb);
                    if (h < best_h || (h == best_h && best_d != -1 && d == ori)) { best_h = h; best_d = d; }
                }
                if (best_d < 0 || best_d == ori) continue;
                const int delta = (best_d - ori + 4) % 4;
                one_step_actions[id] = delta == 3 ? Action::CCR : Action::CR;
            }
        }

        for (int id=0;id < env->num_of_agents ; id++){
            if (!checked.at(id) && one_step_actions.at(id) == Action::FW){
                moveCheck(id,checked,decided,one_step_actions,prev_decision);
            }
        }

        prev_states = next_states;

        const auto elapsed_us = std::chrono::duration_cast<std::chrono::microseconds>(
            std::chrono::steady_clock::now() - start_time).count();
    }

    static void append_actions_and_rollout_states(SharedEnvironment* env,
                                                   std::vector<std::vector<Action>> & actions,
                                                   const std::vector<Action>& one_step_actions)
    {
        for (int aid = 0; aid < env->num_of_agents; aid++){
            actions[aid].push_back(one_step_actions[aid]);
        }

        std::vector<State> rolled_states(env->num_of_agents);
        for (int aid = 0; aid < env->num_of_agents; aid++){
            rolled_states[aid] = rollout_next_state(env->start_states[aid], one_step_actions[aid], env);
        }
        env->start_states = rolled_states;
        env->curr_timestep += 1;
    }

    /**
     * @brief Default planner initialization
     * 
     * @param preprocess_time_limit time limit for preprocessing in milliseconds
     * @param env shared environment object
     * 
     * The initialization function initializes the default planner data structures and heuristics tables.
     */
    void initialize(int preprocess_time_limit, SharedEnvironment* env){
            //initialise all required data structures
            assert(env->num_of_agents != 0);
            p.resize(env->num_of_agents);
            decision.resize(env->map.size(), -1);
            prev_states.resize(env->num_of_agents);
            next_states.resize(env->num_of_agents);
            decided.resize(env->num_of_agents,DCR({-1,DONE::DONE}));
            occupied.resize(env->map.size(),false);
            checked.resize(env->num_of_agents,false);
            ids.resize(env->num_of_agents);
            require_guide_path.resize(env->num_of_agents,false);
            for (int i = 0; i < ids.size();i++){
                ids[i] = i;
            }

            // initialise the heuristics tables containers
            init_heuristics(env);
            // wait-v9: planner-internal random seed (initial PIBT priorities + rand() tie-breaks).
            // Default 0 reproduces all earlier versions bit-for-bit.
            { const char* ps=std::getenv("ROBOT_PLANNER_SEED"); unsigned sd= ps? (unsigned)std::strtoul(ps,nullptr,10):0u;
              mt1.seed(sd); srand(sd); }

            new (&trajLNS) TrajLNS(env, global_heuristictable, global_neighbors);
            trajLNS.init_mem();

            //assign intial priority to each agent
            std::shuffle(ids.begin(), ids.end(), mt1);
            for (int i = 0; i < ids.size();i++){
                p[ids[i]] = ((double)(ids.size() - i))/((double)(ids.size()+1));
            }
            p_copy = p;
            NetMac::initialize(env, trajLNS);
            return;
    };

    /**
     * @brief Default planner plan function
     * 
     * @param time_limit time limit for planning in milliseconds
     * @param actions vector of actions to be populated by the planner
     * @param env shared environment object
     * @param num_steps number of steps to plan
     * 
     * The plan function is the main function of the default planner. 
     * It computes the actions for the agents based on the current state of the environment.
     * The function first checks assignments/goal location changes and perform the necessary updates.
     * It then computes and optimises traffic flow optimised guide paths for the agents.
     * Finally, it computes the actions for the agents using PIBT that follows the guide path heuristics and returns the actions.
     * Note that the default planner ignores the turning action costs, and post-processes turning actions as additional delays on top of original plan.
     */
    void plan(int time_limit, std::vector<std::vector<Action>> & actions,
                         SharedEnvironment* env, int num_steps){
        actions.clear();
        //cout<<"num of steps to plan "<<num_steps<<endl;
        if (env == nullptr || env->num_of_agents <= 0){
            return;
        }

        actions.resize(env->num_of_agents);
        if (num_steps <= 0){
            return;
        }

        const auto episode_start = std::chrono::steady_clock::now();
        const TimePoint episode_deadline = episode_start + std::chrono::milliseconds(std::max(0, time_limit));
        int pibt_time = PIBT_RUNTIME_PER_100_AGENTS * env->num_of_agents/100;
        if (pibt_time <= 0){
            pibt_time = 1;
        }
        const int flow_budget_ms = std::max(0, time_limit - std::max(MIN_PIBT_TIME, pibt_time * num_steps) - TRAFFIC_FLOW_ASSIGNMENT_END_TIME_TOLERANCE);
        TimePoint flow_end_time = episode_start + std::chrono::milliseconds(flow_budget_ms);

        std::vector<double> local_priority = p;

        const std::vector<State> original_states = env->start_states;
        const int original_timestep = env->curr_timestep;
        const std::vector<DCR> original_decided = decided;

        // Fresh execution tracking for each multi-step planning episode:
        // no ongoing orientation-compensation actions are carried across episodes.
        decided.assign(env->num_of_agents, DCR({-1, DONE::DONE}));

        // --- One-time setup for this planning episode ---
        initialize_dummy_goals_if_needed(env);
        setup_multistep_episode_state(env, flow_end_time, local_priority);
        v17_rflag.assign(env->num_of_agents, 0);
        {   // v18d: reroute robots whose guide path (next ROBOT_REGION_AVOID_H cells) passes through a crowded room that is neither
            // where they are nor where they go
            static int rah = -1; if (rah < 0) { const char* e = std::getenv("ROBOT_REGION_AVOID_H"); rah = e ? std::atoi(e) : 40; }
            for (int i = 0; i < env->num_of_agents; ++i) {
                if (require_guide_path[i] || env->goal_locations[i].empty()) continue;
                const auto& tr = trajLNS.trajs[i]; if (tr.empty()) continue;
                const int here = env->curr_states[i].location, rs = RobotWindow::region_of(here), rgl = RobotWindow::region_of(tr.back());
                if (rs < 0) break;
                size_t k = 0; while (k < tr.size() && tr[k] != here) ++k; if (k == tr.size()) k = 0;
                for (size_t q = k + 1; q < tr.size() && q <= k + size_t(rah); ++q)
                    if (RobotWindow::transit_pen(tr[q], rs, rgl) > 0) { require_guide_path[i] = true; break; }
            }
        }
        if (delay_reroute_pen() > 0) {
            v16_block_pen.assign(env->map.size(), 0);
            std::vector<char> dl(env->num_of_agents, 0); bool any = false;
            static int placebo = -1; if (placebo < 0) { const char* e = std::getenv("ROBOT_DELAY_REROUTE_PLACEBO"); placebo = e ? std::atoi(e) : 0; }
            // v16h exploration: ROBOT_REROUTE_MODE=stalled -> cells of robots that did not change cell since the previous plan
            // (delayed or blocked; "queue occupancy"); =all -> cells of every robot; =refresh -> no cost, the same number of
            // randomly chosen robots simply get their guide path recomputed.
            static int rmode = -1; if (rmode < 0) { const char* e = std::getenv("ROBOT_REROUTE_MODE"); std::string m = e ? e : "";
                rmode = m == "stalled" ? 1 : m == "all" ? 2 : m == "refresh" ? 3 : m == "randcells" ? 4 : m == "randall" ? 5 : m == "refreshall" ? 6 : 0; }
            static std::vector<int> last_loc;
            if (rmode == 1 || rmode == 2) {
                if (last_loc.size() != size_t(env->num_of_agents)) last_loc.assign(env->num_of_agents, -1);
                for (int i = 0; i < env->num_of_agents; ++i) {
                    const int loc = env->system_states[i].location;
                    if (rmode == 2 || loc == last_loc[i] || env->system_states[i].delay.inDelay) { v16_block_pen[loc] = delay_reroute_pen(); any = true; dl[i] = rmode == 1; }
                    last_loc[i] = loc;
                }
            } else if (rmode == 6) {
                for (int i = 0; i < env->num_of_agents; ++i) if (!require_guide_path[i] && !env->goal_locations[i].empty()) { require_guide_path[i] = true; v17_rflag[i] = 1; }
            } else if (rmode == 5) {
                // v17b placebo for the "all" mode: as many cells as there are robots, chosen at random among all free cells
                static std::vector<int> freec5; if (freec5.empty()) for (int v = 0; v < int(env->map.size()); ++v) if (!env->map[v]) freec5.push_back(v);
                std::mt19937 rg(1000003u * unsigned(env->curr_timestep + 1) + 17u);
                for (int k = 0; k < env->num_of_agents; ++k) { v16_block_pen[freec5[rg() % freec5.size()]] = delay_reroute_pen(); any = true; }
            } else if (rmode == 4) {
                // v17 placebo for the stalled mode: as many cells as there are stalled robots, but chosen at random among all free cells
                static std::vector<int> freec; if (freec.empty()) for (int v = 0; v < int(env->map.size()); ++v) if (!env->map[v]) freec.push_back(v);
                if (last_loc.size() != size_t(env->num_of_agents)) last_loc.assign(env->num_of_agents, -1);
                int c = 0;
                for (int i = 0; i < env->num_of_agents; ++i) { const int loc = env->system_states[i].location; if (loc == last_loc[i] || env->system_states[i].delay.inDelay) ++c; last_loc[i] = loc; }
                std::mt19937 rg(1000003u * unsigned(env->curr_timestep + 1) + 13u);
                for (int k = 0; k < c; ++k) { v16_block_pen[freec[rg() % freec.size()]] = delay_reroute_pen(); any = true; }
            } else if (rmode == 3) {
                int c = 0; std::vector<int> pool;
                for (int i = 0; i < env->num_of_agents; ++i) { if (env->system_states[i].delay.inDelay) ++c; if (!require_guide_path[i] && !env->goal_locations[i].empty() && !trajLNS.trajs[i].empty()) pool.push_back(i); }
                std::mt19937 rg(1000003u * unsigned(env->curr_timestep + 1) + 11u); std::shuffle(pool.begin(), pool.end(), rg);
                for (int k = 0; k < c && k < int(pool.size()); ++k) { require_guide_path[pool[k]] = true; v17_rflag[pool[k]] = 1; ++v16_reroutes; }
            } else if (!placebo) {
                for (int i = 0; i < env->num_of_agents && i < int(env->system_states.size()); ++i)
                    if (env->system_states[i].delay.inDelay) { dl[i] = 1; any = true; v16_block_pen[env->system_states[i].location] = delay_reroute_pen(); }
            } else {
                // placebo control: the same number of robots, chosen at random among those NOT in a delay, are treated as stuck
                std::vector<int> pool; int c = 0;
                for (int i = 0; i < env->num_of_agents && i < int(env->system_states.size()); ++i) { if (env->system_states[i].delay.inDelay) ++c; else pool.push_back(i); }
                std::mt19937 rg(1000003u * unsigned(env->curr_timestep + 1) + 7u);
                std::shuffle(pool.begin(), pool.end(), rg);
                for (int k = 0; k < c && k < int(pool.size()); ++k) { const int i = pool[k]; dl[i] = 1; any = true; v16_block_pen[env->system_states[i].location] = delay_reroute_pen(); }
            }
            if (any) for (int i = 0; i < env->num_of_agents; ++i) {
                if (dl[i] || require_guide_path[i] || env->goal_locations[i].empty()) continue;
                const auto& tr = trajLNS.trajs[i]; if (tr.empty()) continue;
                const int here = env->curr_states[i].location; size_t k = 0;
                while (k < tr.size() && tr[k] != here) ++k;
                if (k == tr.size()) k = 0;
                for (size_t q = k + 1; q < tr.size() && q <= k + size_t(delay_horizon()); ++q)
                    if (v16_block_pen[tr[q]] > 0) { require_guide_path[i] = true; v17_rflag[i] = 1; ++v16_reroutes; break; }
            }
        }
        if (frer_b() >= 0 && delay_reroute_pen() <= 0) {   // p14: FRER standby route (see frer_b)
            static std::vector<int> lane_comp; static std::vector<std::vector<int>> comps;
            if (lane_comp.empty()) {
                const int R_ = env->rows, C_ = env->cols, N_ = R_ * C_;
                auto fr = [&](int r, int c) { return r >= 0 && r < R_ && c >= 0 && c < C_ && !env->map[r * C_ + c]; };
                std::vector<char> one(N_, 0);
                for (int r = 0; r < R_; ++r) for (int c = 0; c < C_; ++c) if (fr(r, c)) {
                    const bool h1 = !fr(r, c - 1) && !fr(r, c + 1), v1 = !fr(r - 1, c) && !fr(r + 1, c);
                    one[r * C_ + c] = h1 || v1;
                }
                lane_comp.assign(N_, -1);
                for (int v = 0; v < N_; ++v) if (one[v] && lane_comp[v] < 0) {
                    comps.emplace_back(); std::vector<int> st{v}; lane_comp[v] = int(comps.size()) - 1;
                    while (!st.empty()) { const int u = st.back(); st.pop_back(); comps.back().push_back(u);
                        const int r = u / C_, c = u % C_; const int nb[4][2] = {{r + 1, c}, {r - 1, c}, {r, c + 1}, {r, c - 1}};
                        for (auto& q : nb) if (fr(q[0], q[1]) && one[q[0] * C_ + q[1]] && lane_comp[q[0] * C_ + q[1]] < 0) { lane_comp[q[0] * C_ + q[1]] = lane_comp[u]; st.push_back(q[0] * C_ + q[1]); } }
                }
            }
            v16_block_pen.assign(env->map.size(), 0);
            std::vector<char> dl(env->num_of_agents, 0); bool any = false;
            for (int i = 0; i < env->num_of_agents && i < int(env->system_states.size()); ++i) {
                if (!env->system_states[i].delay.inDelay) continue;
                const int loc = env->system_states[i].location; dl[i] = 1;
                if (loc < 0 || loc >= int(lane_comp.size()) || lane_comp[loc] < 0) continue;
                for (int c : comps[lane_comp[loc]]) v16_block_pen[c] = 1000;
                any = true;
            }
            if (any) for (int i = 0; i < env->num_of_agents; ++i) {
                if (dl[i] || require_guide_path[i] || env->goal_locations[i].empty()) continue;
                const auto& tr = trajLNS.trajs[i]; if (tr.empty()) continue;
                const int here = env->curr_states[i].location; size_t k = 0;
                while (k < tr.size() && tr[k] != here) ++k;
                if (k == tr.size()) k = 0;
                if (v16_block_pen[here] > 0) continue;   // already inside the blocked stretch: nothing to switch to
                for (size_t q = k + 1; q < tr.size() && q <= k + size_t(delay_horizon()); ++q)
                    if (v16_block_pen[tr[q]] > 0) { require_guide_path[i] = true; v17_rflag[i] = 1; ++p14_frer_reroutes; break; }
            }
        }
        update_guide_paths_once_for_multistep(env, flow_end_time);
        if (delay_reroute_pen() > 0 || frer_b() >= 0) v16_block_pen.assign(env->map.size(), 0);   // the penalty only shapes the reroutes made now

        const auto after_setup = std::chrono::steady_clock::now();
        const auto setup_elapsed_ms = std::chrono::duration_cast<std::chrono::milliseconds>(after_setup - episode_start).count();
        // commit only cross-episode priority update (internal rollout keeps using local_priority only)
        p = local_priority;

        v16_frozen.assign(env->num_of_agents, 0);
        if (delay_freeze_steps() > 0)
            for (int i = 0; i < env->num_of_agents && i < int(env->system_states.size()); ++i) v16_frozen[i] = env->system_states[i].delay.inDelay;
        teft_observe(env);   // p28 TE-6 (no effect unless ROBOT_TE_FT)
        Bfd::begin_plan(env);   // p04: BFD down set for this plan (no effect unless ROBOT_BFD_LFA / ROBOT_BFD_LFA_MEAS)
        for (int step = 0; step < num_steps; step++){
            v16_step = step; Bfd::set_step(step); p46_step = step;
            if (!fixed_planner_work_mode() && std::chrono::steady_clock::now() >= episode_deadline){
                break;
            }
            std::vector<Action> one_step_actions;
            // After step 0, only run PIBT + rollout (no guide path recompute and no FW)
            if (step > 0){
                refresh_multistep_step_state(env, local_priority);
            }
            run_multistep_pibt_once(env, local_priority, one_step_actions);
            append_actions_and_rollout_states(env, actions, one_step_actions);
        }

        {   // v25 diagnostic: ROBOT_PLAN_LOG=path writes each plan (start state + actions) for every agent. No effect on behaviour.
            static const char* pl=std::getenv("ROBOT_PLAN_LOG"); static std::FILE* pf=pl?std::fopen(pl,"w"):nullptr; static int ep=0;
            if(pf){ ++ep; for(int i=0;i<env->num_of_agents;++i){ std::fprintf(pf,"%d %d %d %d %d",ep,i,original_states[i].location,original_states[i].orientation,(int)env->goal_locations[i].size());
                    for(auto a:actions[i]) std::fprintf(pf," %d",(int)a); std::fprintf(pf,"\n"); } }
        }
        // restore env state after internal rollout simulation
        env->start_states = original_states;
        env->curr_timestep = original_timestep;
        NetMac::write_stats(env);
        Bfd::write_stats(env);
        TcpWin::write_stats();
        decided = original_decided;

        // This is optional diagnostic output, separate from controller telemetry.
        // Equal iteration limits do not imply equal CPU time: states can differ.
        if (const char* trace_path = std::getenv("ROBOT_WORK_TRACE")){
            std::ofstream trace(trace_path, std::ios::app);
            trace << "{\"kind\":\"plan\",\"mode\":\"" << (fixed_planner_work_mode() ? "fixed" : "timed")
                  << "\",\"planner_timestep\":" << original_timestep
                  << ",\"requested_steps\":" << num_steps
                  << ",\"produced_steps\":" << actions.front().size()
                  << ",\"remaining_budget_ms\":" << time_limit
                  << ",\"elapsed_us\":" << std::chrono::duration_cast<std::chrono::microseconds>(
                        std::chrono::steady_clock::now() - episode_start).count() << "}\n";
        }
    }
}
