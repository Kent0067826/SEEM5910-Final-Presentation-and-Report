#include <cstdlib>



#include "search.h"
#include "observed_wait.h"
#include "window_control.h"
#include <string>


namespace DefaultPlanner{
std::chrono::nanoseconds t;
// v16 (round 26): temporary vertex cost on cells occupied by robots that are in an execution delay (set by the planner)
std::vector<int> v16_block_pen;
static bool v18_ignore_pause = false;
//a astar minimized the opposide traffic flow with existing traffic flow

s_node astar(SharedEnvironment* env, std::vector<Int4>& flow,
    HeuristicTable& ht, Traj& traj,
    MemoryPool& mem, int start, int goal, Neighbors* ns, const TimePoint* deadline)
{
    mem.reset();
    // v14: a turn costs a full action in execution, so charge it in the guide path (ROBOT_TURN_PEN=k), but only while the map is
    // free flowing (ROBOT_TURN_GATE=g: map-wide blocked share below g). In congested maps avoiding opposing flow matters more.
    static int turn_pen = -1; static double turn_gate = -2;
    if (turn_pen < 0) { const char* e = std::getenv("ROBOT_TURN_PEN"); turn_pen = e ? std::atoi(e) : 0; const char* g = std::getenv("ROBOT_TURN_GATE"); turn_gate = g ? std::stod(g) : -1; }
    const int turn_pen_now = turn_pen > 0 && (turn_gate < 0 || RobotWindow::free_flowing(turn_gate)) ? turn_pen : 0;
    const int rstart_v18 = RobotWindow::region_of(start), rgoal_v18 = RobotWindow::region_of(goal);

    int expanded=0;
    int generated=0;
    int h;

    if (is_large_map(env)){
        h = manhattanDistance(start,goal,env);
    }
    else{
        if(ht.empty())
            h = manhattanDistance(start,goal,env);
        else
            h = get_heuristic(ht,env, start, ns);
    }
    

    
    s_node* root = mem.generate_node(start,0, h,0,0,0);

    if (start == goal){
        traj.clear();
        traj.push_back(start);
        return *root;
    }

    pqueue_min_of open;
    re_of re;

    open.push(root);

    int  diff, d, cost, op_flow, total_cross, all_vertex_flow,vertex_flow, depth,p_diff, p_d;
    int next_d1, next_d2, next_d1_loc, next_d2_loc;
    int temp_op, temp_vertex;
    // wait-v4 fix: upstream left this uninitialised; the root expansion (no parent) read stack garbage,
    // making guide paths depend on unrelated code/stack layout. Root children get no turn preference.
    double tie_breaker = 0, decay_factor = 0;

    s_node* goal_node = nullptr;
    int neighbors[4];
    int next_neighbors[4];



    while (open.size() > 0){
        if (deadline != nullptr && std::chrono::steady_clock::now() >= *deadline){
            return s_node();
        }
        s_node* curr = open.pop();
        curr->close();

        if (curr->id == goal){
            goal_node = curr;
            break;
        }
        expanded++;
        getNeighborLocs(ns,neighbors,curr->id);
        
        for (int i=0; i<4; i++){
            int next = neighbors[i];
            if (next == -1){
                continue;
            }
            if (!(v18_ignore_pause ? RobotWindow::move_allowed(curr->id, next) : RobotWindow::move_allowed_goal(curr->id, next, goal))) continue;   // v18b/f: one-way doors, room pause

            cost = curr->g+1;

            assert(next >= 0 && next < env->map.size());
            depth = curr->depth + 1;

            //moving direction
            //flow
            op_flow = 0;
            all_vertex_flow = 0;

            if(is_large_map(env)){
                h = manhattanDistance(next,goal,env);
            }
            else{
                if(ht.empty())
                    h = manhattanDistance(next,goal,env);
                else
                    h = get_heuristic(ht,env, next, ns);
            }

            diff = next - curr->id;
            d = get_d(diff,env);
            if (curr->parent != nullptr){
                p_diff = curr->id - curr->parent->id;
                p_d = get_d(p_diff,env);
                if (p_d!=d)
                    tie_breaker = 0.1;
                else
                    tie_breaker = 0;
                //tie breaking on prefering moving forward
            }


            temp_op = ( (flow[curr->id].d[d]+1) * flow[next].d[(d+2)%4]);///( ( (flow[curr->id].d[d]+1) + flow[next].d[(d+2)%4]));

            //all vertex flow
            //the sum of all out going edge flow is the same as the total number of vertex visiting.
            temp_vertex = 1;
            for (int j=0; j<4; j++){
                temp_vertex += flow[next].d[j];                
            }

            op_flow += temp_op;
        
            all_vertex_flow+= (temp_vertex-1) /2;
            all_vertex_flow+= ObservedWait::path_penalty(curr->id,next); // wait-v5 (D5), 0 unless enabled
            if (turn_pen_now > 0 && curr->parent != nullptr && get_d(curr->id - curr->parent->id, env) != d) all_vertex_flow += turn_pen_now;   // v14: gated turn cost
            if (!v16_block_pen.empty()) all_vertex_flow += v16_block_pen[next];   // v16: avoid robots stuck in a delay
            all_vertex_flow += RobotWindow::transit_pen(next, rstart_v18, rgoal_v18);   // v18d: avoid crowded rooms in transit

            p_diff = 0;
            if (curr->parent != nullptr){
                p_diff = curr->id - curr->parent->id;
            }

            op_flow += curr->op_flow; //op_flow is contra flow
            all_vertex_flow += curr->all_vertex_flow;

            s_node temp_node(next,cost,h,op_flow, depth);
            temp_node.tie_breaker = tie_breaker;
            temp_node.set_all_flow(op_flow,  all_vertex_flow);

            if (!mem.has_node(next)){
                s_node* next_node = mem.generate_node(next,cost,h,op_flow, depth,all_vertex_flow);
                next_node->parent = curr;
                next_node->tie_breaker = tie_breaker;
                open.push(next_node);
                generated++;
            }
            else{ 
                s_node* existing = mem.get_node(next);

                if (!existing->is_closed()){
                    if (re(temp_node,*existing)){
                        existing->g = cost;
                        existing->parent = curr;
                        existing->depth = depth;
                        existing->tie_breaker = tie_breaker;
                        existing->set_all_flow(op_flow,  all_vertex_flow);
                        open.decrease_key(existing);
                    }
                }
                else{

                    if (re(temp_node,*existing)){ 
                        std::cout << "error in astar: re-expansion" << std::endl;
                        assert(false);
                        exit(1);
                    }

                } 
            }
        }
            

          
    }


    if (goal_node == nullptr && !v18_ignore_pause){
        // v18f: the room-pause rule can cut a robot off its goal; search again without it
        v18_ignore_pause = true; s_node r = astar(env, flow, ht, traj, mem, start, goal, ns, deadline); v18_ignore_pause = false; return r;
    }
    if (goal_node == nullptr){
        std::cout << "error in astar: no path found "<< start<<","<<goal << std::endl;
        assert(false);
        exit(1);
    }

    traj.resize(goal_node->depth+1);
    s_node* curr = goal_node;
    for (int i=goal_node->depth; i>=0; i--){
        traj[i] = curr->id;
        curr = curr->parent;
    }

    return *goal_node;
}
}
