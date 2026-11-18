#pragma once
// Linux port: std-only logger replacing Boost.Log, same public interface and message text.
#include <fstream>
#include <mutex>
#include <string>
class Logger
{
public:
    Logger(std::string filename, int severity=2);
    ~Logger(){ if(out.is_open()) out.close(); };
    void log_info(std::string input);
    void log_info(std::string input, int timestep);
    void log_fatal(std::string input);
    void log_fatal(std::string input, int timestep);
    void log_warning(std::string input);
    void log_warning(std::string input, int timestep);
    void flush();
private:
    void write(int level, const char* name, const std::string& input);
    std::ofstream out; int min_level; std::mutex lock;
};
