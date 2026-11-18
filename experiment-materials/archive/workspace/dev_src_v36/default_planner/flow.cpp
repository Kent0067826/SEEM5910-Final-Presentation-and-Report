

#include "flow.h"


#include <random>
#include <unordered_set>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <string>
#include <algorithm>

namespace DefaultPlanner{

std::mt19937 g(0);

// Optional mechanism ablation: fix the optimisation work rather than the wall
// clock allocation. The simulator still enforces its official outer deadline.
static bool fixed_flow_work_mode(){
    static const bool enabled = [](){
        const char* value = std::getenv("ROBOT_WORK_MODE");
        return value != nullptr && std::strcmp(value, "fixed") == 0;
    }();
    return enabled;
}

static int fixed_flow_attempts(){
    static const int attempts = [](){
        const char* value = std::getenv("ROBOT_FLOW_ITERS");
        if (value == nullptr || *value == '\0') return 64;
        char* end = nullptr;
        const long parsed = std::strtol(value, &end, 10);
        if (*end != '\0' || parsed < 0 || parsed > 1000000) return 64;
        return static_cast<int>(parsed);
    }();
    return attempts;
}


//remove flow for each location's outgoing edge according to the traj
void remove_traj(TrajLNS& lns, int agent){
    lns.soc -= lns.trajs[agent].size() - 1;
    if (lns.trajs[agent].size() <= 1){
        return;
    }
    int loc, prev_loc, diff, d, to;

    to = lns.trajs[agent].size();

    for (int j = 1; j < to; j++){
        loc = lns.trajs[agent][j];
        prev_loc = lns.trajs[agent][j-1];
        diff = loc - prev_loc;
        d = get_d(diff, lns.env);


        lns.flow[prev_loc].d[d] -= 1;

    }
}

void add_traj(TrajLNS& lns, int agent){

    //update last replan time for agent
    lns.fw_metrics[agent].last_replan_t = lns.env->curr_timestep;

    lns.soc += lns.trajs[agent].size() - 1;
    if (lns.trajs[agent].size() <= 1){
        return;
    }
    int loc, prev_loc, diff, d;
    for (int j = 1; j < lns.trajs[agent].size(); j++){
        loc = lns.trajs[agent][j];
        prev_loc = lns.trajs[agent][j-1];
        diff = loc - prev_loc;
        d = get_d(diff, lns.env);

        lns.flow[prev_loc].d[d] += 1;

    }
}


void get_deviation(TrajLNS& lns){
    lns.deviation_agents.clear();
    for  (int i=0; i< lns.env->num_of_agents;i++){
        if (lns.traj_dists[i].empty() || lns.trajs[i].empty())
            continue;

        std::pair<int,int> dists =  get_source_2_path(lns.traj_dists[i], lns.env, lns.env->curr_states[i].location, &(lns.neighbors));

        if (dists.first > 0){
            lns.deviation_agents.emplace_back(dists.first, i);
        }
    }

    std::sort(lns.deviation_agents.begin(), lns.deviation_agents.end(),
        [](std::pair<int,int>& a, std::pair<int,int>& b)
		{
            return a.first > b.first;
        });
    return;
}

void update_fw_metrics(TrajLNS& lns){
    for  (int i=0; i< lns.env->num_of_agents;i++){
        lns.fw_metrics[i].id = i;
        lns.fw_metrics[i].rand = rand();
        lns.fw_metrics[i].deviation = 0;
        if (lns.traj_dists[i].empty() || lns.trajs[i].empty())
            continue;
        std::pair<int,int> dists =  get_source_2_path(lns.traj_dists[i], lns.env, lns.env->curr_states[i].location, &(lns.neighbors));
        assert(dists.first >= 0 );
        lns.fw_metrics[i].deviation = dists.first;
    }
    return;
}



// ---- wait-v8: traffic-engineering style selection of which guide paths to re-route under a fixed budget.
// ROBOT_FW_ORDER = dev (upstream: largest deviation first) | cong | devcong | wait | devwait | congwait
//   cong : current congestion cost of the agent's guide path (same contra-flow + vertex-flow terms as the A*),
//          i.e. re-route the flows sitting on the most congested links first (like MPLS-TE / OSPF-TE re-optimisation)
//   wait : ticks the agent is currently blocked on its front edge (retransmission-timeout-like signal)
//   dev* : agents that left their guide path keep absolute precedence (they must be repaired anyway)
// ROBOT_FW_RESORT = K > 0: recompute congestion order after every K re-routes (iterative TE); 0 = static order.
static const std::string& fw_order(){ static const std::string o=[](){const char* v=std::getenv("ROBOT_FW_ORDER"); return std::string(v?v:"dev");}(); return o; }
static int fw_resort(){ static const int k=[](){const char* v=std::getenv("ROBOT_FW_RESORT"); return v?std::max(0,atoi(v)):0;}(); return k; }
static double path_congestion(TrajLNS& lns,int a){
    const auto& t=lns.trajs[a]; double c=0;
    for(size_t j=1;j<t.size();++j){ int prev=t[j-1], loc=t[j]; int d=get_d(loc-prev,lns.env);
        const auto& fn=lns.flow[loc].d; int vsum=fn[0]+fn[1]+fn[2]+fn[3];
        c += double(lns.flow[prev].d[d]) * double(fn[(d+2)%4]) + double(std::max(0,vsum-1))/2.0; }
    return c;
}
static void score_agents(TrajLNS& lns, std::vector<FW_Metric>& order){
    const std::string& o=fw_order(); if(o=="dev") return;
    std::vector<double> waitv;
    if(o.find("wait")!=std::string::npos){ waitv.assign(lns.env->num_of_agents,0.0);
        for(const auto& s:lns.env->wait_active) if(s.agent>=0&&s.agent<(int)waitv.size()) waitv[s.agent]=std::max(waitv[s.agent],double(s.blockTicks)); }
    for(auto& m:order){ double sc=0; int a=m.id;
        if(o.find("cong")!=std::string::npos && !lns.trajs[a].empty()) sc+=path_congestion(lns,a);
        if(!waitv.empty()) sc+= (o=="congwait"?100.0:1.0)*waitv[a];
        m.score=sc; }
}
static bool fw_less(const FW_Metric& a,const FW_Metric& b){
    const std::string& o=fw_order();
    if(o!="dev"){
        const bool dev_first=o.rfind("dev",0)==0;
        if(dev_first){ const bool da=a.deviation>0, db=b.deviation>0; if(da!=db) return da; }
        if(a.score!=b.score) return a.score>b.score;
    }
    if (a.deviation > b.deviation) return true; else if (a.deviation < b.deviation) return false;
    if (a.last_replan_t < b.last_replan_t) return true; else if (a.last_replan_t > b.last_replan_t) return false;
    return a.rand > b.rand;
}

void frank_wolfe(TrajLNS& lns,std::unordered_set<int>& updated, TimePoint timelimit){
    const bool fixed_work = fixed_flow_work_mode();
    const auto work_start = std::chrono::steady_clock::now();
    update_fw_metrics(lns);
    std::vector<FW_Metric> replan_order = lns.fw_metrics;
    assert(replan_order.size() == lns.env->num_of_agents);

    if (fw_order()=="dev") {
    std::sort(replan_order.begin(), replan_order.end(),
    [](FW_Metric& a, FW_Metric& b)
    {
        if (a.deviation > b.deviation)
            return true;
        else if ( a.deviation < b.deviation)
            return false;
        
        if (a.last_replan_t < b.last_replan_t)
            return true;
        else if (a.last_replan_t > b.last_replan_t)
            return false;

        return a.rand > b.rand;
    });
    } else {
        score_agents(lns, replan_order);
        std::stable_sort(replan_order.begin(), replan_order.end(), fw_less);
    }
    std::vector<char> done_in_round(lns.env->num_of_agents, 0);

    int count=0;
    int replanned=0;
    int failed=0;
    int a, index;
    while (fixed_work ? count < fixed_flow_attempts() : std::chrono::steady_clock::now() < timelimit){
        index = count%lns.env->num_of_agents;
        if (fw_order()!="dev" && fw_resort()>0 && count>0 && count%fw_resort()==0 && count<lns.env->num_of_agents) {
            // iterative traffic engineering: re-score the not-yet-rerouted agents on the updated flow
            std::vector<FW_Metric> rest; for (int k=index;k<lns.env->num_of_agents;++k) rest.push_back(replan_order[k]);
            for (auto& m: rest) { m.deviation = lns.fw_metrics[m.id].deviation; }
            score_agents(lns, rest); std::stable_sort(rest.begin(), rest.end(), fw_less);
            for (size_t k=0;k<rest.size();++k) replan_order[index+k]=rest[k];
        }
        a = replan_order[index].id;
        count++;
        if (lns.traj_dists[a].empty() || lns.trajs[a].empty()){
            continue;
        }
        std::vector<int> old_traj = lns.trajs[a];
        remove_traj(lns,a);
        if (!update_traj(lns,a, fixed_work ? nullptr : &timelimit)){
            lns.trajs[a] = old_traj;
            add_traj(lns,a);
            failed++;
            break;
        }
        replanned++;
        
    }
    if (const char* trace_path = std::getenv("ROBOT_WORK_TRACE")){
        std::ofstream trace(trace_path, std::ios::app);
        trace << "{\"kind\":\"flow\",\"mode\":\"" << (fixed_work ? "fixed" : "timed")
              << "\",\"planner_timestep\":" << lns.env->curr_timestep
              << ",\"requested_attempts\":" << (fixed_work ? fixed_flow_attempts() : -1)
              << ",\"attempts\":" << count << ",\"replanned\":" << replanned
              << ",\"failed_searches\":" << failed
              << ",\"elapsed_us\":" << std::chrono::duration_cast<std::chrono::microseconds>(
                    std::chrono::steady_clock::now() - work_start).count() << "}\n";
    }
    return;

}




void update_dist_2_path(TrajLNS& lns, int i){
    init_dist_2_path(lns.traj_dists[i], lns.env, lns.trajs[i]);
}

//compute distance table for each traj
void init_dist_table(TrajLNS& lns, int amount){

    int count = 0;
    for (int i=0 ; i <lns.env->num_of_agents; i++){
                // std::cout<<i<<";";
        if (count >= amount){
            break;
        }
        if(!lns.trajs[i].empty() && lns.trajs[i].size() == get_heuristic(lns.heuristics[lns.trajs[i].back()], lns.env,lns.trajs[i].front(),&(lns.neighbors)))
            continue;
        if(!lns.trajs[i].empty() && lns.traj_dists[i].empty()){
            init_dist_2_path(lns.traj_dists[i], lns.env, lns.trajs[i]);
            count++;
            lns.dist2path_inited++;
        }

    }
}

//update traj and distance table for agent i
bool update_traj(TrajLNS& lns, int i, const TimePoint* deadline){
    int start = lns.env->curr_states[i].location;
    int goal = lns.tasks[i];
    s_node goal_node = astar(lns.env,lns.flow, lns.heuristics[goal],lns.trajs[i],lns.mem,start,goal, &(lns.neighbors), deadline);
    if (goal_node.id == -1){
        return false;
    }
    lns.goal_nodes[i] = goal_node;
    add_traj(lns,i);
    update_dist_2_path(lns,i);
    return true;
}

}
