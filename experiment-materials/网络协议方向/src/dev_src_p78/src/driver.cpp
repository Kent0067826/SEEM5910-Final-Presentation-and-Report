#include "CompetitionSystem.h"
#include "Evaluation.h"
#include <filesystem>
#include <map>
#include "nlohmann/json.hpp"
#include <signal.h>
#include <climits>
#include <memory>
#include <stdexcept>



using json = nlohmann::json;
// Linux port: tiny option parser replacing boost::program_options (same flags/defaults). Python components unsupported.
struct OptValue { std::string v; template<class T> T as() const; };
template<> inline std::string OptValue::as<std::string>() const { return v; }
template<> inline bool OptValue::as<bool>() const { return v=="1"||v=="true"; }
template<> inline int OptValue::as<int>() const { return std::stoi(v); }
struct OptMap { std::map<std::string,OptValue> m; const OptValue& operator[](const std::string& k) const { return m.at(k); } size_t count(const std::string& k) const { return m.count(k); } };
OptMap vm;
static void parse_options(int argc, char** argv) {
    const std::map<std::string,std::pair<std::string,std::string>> defs = { // long -> (short, default)
        {"actionMoveTimeLimit",{"a","100"}},{"outputScreen",{"c","1"}},{"logDetailLevel",{"d","1"}},{"fileStoragePath",{"f",""}},
        {"inputFile",{"i","\x01"}},{"logFile",{"l",""}},{"initialPlanTimeLimit",{"n","1000"}},{"output",{"o","./output.json"}},
        {"prettyPrintJson",{"","0"}},{"preprocessTimeLimit",{"p","30000"}},{"disableStagedActionValidation",{"","0"}},
        {"simulationTime",{"s","5000"}},{"taskTrendFile",{"",""}},{"taskTrendInterval",{"","100"}},{"planCommTimeLimit",{"t","1000"}},
        {"outputActionWindow",{"w","1000"}},{"executorProcessPlanTimeLimit",{"x","100"}}};
    for (auto& d: defs) vm.m[d.first].v = d.second.second;
    for (int k=1;k<argc;++k) { std::string a=argv[k], name;
        if (a=="--help") { vm.m["help"].v="1"; continue; }
        if (a.rfind("--",0)==0) name=a.substr(2);
        else if (a.size()==2 && a[0]=='-') { for (auto& d: defs) if (d.second.first==a.substr(1)) name=d.first; }
        if (!defs.count(name)) throw std::invalid_argument("Unsupported option (Linux port): "+a);
        if (name=="prettyPrintJson"||name=="disableStagedActionValidation") { vm.m[name].v="1"; continue; }
        if (k+1>=argc) throw std::invalid_argument("Missing value for "+a);
        vm.m[name].v=argv[++k]; }
    if (vm.m["inputFile"].v=="\x01") throw std::invalid_argument("--inputFile is required");
}
std::unique_ptr<BaseSystem> system_ptr;

void sigint_handler(int a)
{
    fprintf(stdout, "stop the simulation...\n");
    system_ptr->saveResults(
        vm["output"].as<std::string>(),
        vm["outputScreen"].as<int>(),
        vm["prettyPrintJson"].as<bool>());
    _exit(0);
}


int main(int argc, char **argv)
{
    clock_t start_time = clock();
    parse_options(argc, argv);
    if (vm.count("help")) { std::cout << "See 程序启动检查.txt for options" << std::endl; return 1; }

    std::filesystem::path p(vm["inputFile"].as<std::string>());
    std::filesystem::path dir = p.parent_path();
    std::string base_folder = dir.string();
    if (base_folder.size() > 0 && base_folder.back() != '/')
    {
        base_folder += "/";
    }

    int log_level = vm["logDetailLevel"].as<int>();
    if (log_level <= 1)
        log_level = 2; //info
    else if (log_level == 2)
        log_level = 3; //warning
    else
        log_level = 5; //fatal

    Logger *logger = new Logger(vm["logFile"].as<std::string>(),log_level);

    std::filesystem::path filepath(vm["output"].as<std::string>());
    if (filepath.parent_path().string().size() > 0 && !std::filesystem::is_directory(filepath.parent_path()))
    {
        logger->log_fatal("output directory does not exist",0);
        _exit(1);
    }


    Entry *planner = nullptr;
    Executor *executor = nullptr;

    planner = new Entry();
    executor = new Executor();

    auto input_json_file = vm["inputFile"].as<std::string>();
    json data;
    std::ifstream f(input_json_file);
    try
    {
        data = json::parse(f);
    }
    catch (json::parse_error error)
    {
        std::cerr << "Failed to load " << input_json_file << std::endl;
        std::cerr << "Message: " << error.what() << std::endl;
        exit(1);
    }

    auto map_path = read_param_json<std::string>(data, "mapFile");
    Grid grid(base_folder + map_path);

    planner->env->map_name = map_path.substr(map_path.find_last_of("/") + 1);
    executor->env->map_name = planner->env->map_name;


    string file_storage_path = vm["fileStoragePath"].as<std::string>();
    if (file_storage_path==""){
      char const* tmp = getenv("LORR_LARGE_FILE_STORAGE_PATH");
      if ( tmp != nullptr ) {
        file_storage_path = string(tmp);
      }
    }

    // check if the path exists;
    if (file_storage_path!="" &&!std::filesystem::exists(file_storage_path))
    {
      std::ostringstream stringStream;
      stringStream << "fileStoragePath (" << file_storage_path << ") is not valid";
      logger->log_warning(stringStream.str());
    }

    planner->env->file_storage_path = file_storage_path;
    executor->env->file_storage_path = file_storage_path;

    float agent_size = read_param_json<float>(data, "agentSize", 1.0f);
    if (agent_size <= 0.0f)
    {
        throw std::invalid_argument("agentSize should be a positive number");
    }

    ActionModelWithRotate *model = new ActionModelWithRotate(grid, agent_size);
    model->set_logger(logger);

    int team_size = read_param_json<int>(data, "teamSize");
    DelayConfig delay_config;
    try
    {
        delay_config = parse_delay_config(data);
    }
    catch (const std::invalid_argument& error)
    {
        logger->log_fatal(error.what(), 0);
        _exit(1);
    }

    const std::string delay_event_distribution =
        delay_config.eventModel == DelayConfig::EventModel::Bernoulli ? "bernoulli" : "poisson";
    const std::string delay_time_distribution =
        delay_config.durationModel == DelayConfig::DurationModel::Uniform ? "uniform" : "gaussian";

    planner->env->delay_event_distribution = delay_event_distribution;
    planner->env->delay_time_distribution = delay_time_distribution;
    executor->env->delay_event_distribution = delay_event_distribution;
    executor->env->delay_time_distribution = delay_time_distribution;

    std::vector<int> agents = read_int_vec(base_folder + read_param_json<std::string>(data, "agentFile"), team_size);
    std::vector<list<int>> tasks = read_int_vec(base_folder + read_param_json<std::string>(data, "taskFile"));
    if (agents.size() > tasks.size())
        logger->log_warning("Not enough tasks for robots (number of tasks < team size)");

    system_ptr = std::make_unique<BaseSystem>(grid, planner, executor, agents, tasks, model, read_param_json<int>(data, "agentCounter", 10));

    system_ptr->set_logger(logger);
    const int task_trend_interval = vm["taskTrendInterval"].as<int>();
    if (task_trend_interval <= 0)
    {
        logger->log_fatal("taskTrendInterval must be a positive integer", 0);
        _exit(1);
    }
    system_ptr->set_task_trend_output(vm["taskTrendFile"].as<std::string>(), task_trend_interval);

    system_ptr->set_logger(logger);
    system_ptr->set_plan_time_limit(vm["initialPlanTimeLimit"].as<int>(),vm["planCommTimeLimit"].as<int>(),vm["actionMoveTimeLimit"].as<int>(),vm["executorProcessPlanTimeLimit"].as<int>());
    system_ptr->set_preprocess_time_limit(vm["preprocessTimeLimit"].as<int>());
    system_ptr->set_staged_action_validation_enabled(!vm["disableStagedActionValidation"].as<bool>());

    system_ptr->set_num_tasks_reveal(read_param_json<float>(data, "numTasksReveal", 1));

    try
    {
        system_ptr->set_delay_generator(std::make_unique<DelayGenerator>(delay_config, team_size));
    }
    catch (const std::invalid_argument& error)
    {
        logger->log_fatal(error.what(), 0);
        _exit(1);
    }

    signal(SIGINT, sigint_handler);

    // Release GIL so worker threads in simulate() can acquire it for Python calls
    system_ptr->simulate(vm["simulationTime"].as<int>(),100);

    system_ptr->saveResults(
        vm["output"].as<std::string>(),
        vm["outputScreen"].as<int>(),
        vm["prettyPrintJson"].as<bool>());

    delete model;
    delete logger;
    _exit(0);
}
