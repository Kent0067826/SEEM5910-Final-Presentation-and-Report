#include "Logger.h"
#include <chrono>
#include <ctime>
#include <iomanip>
#include <iostream>
#include <sstream>
// Boost trivial severities: trace0 debug1 info2 warning3 error4 fatal5
Logger::Logger(std::string filename, int severity):min_level(severity){ if(!filename.empty()) out.open(filename); }
void Logger::write(int level,const char* name,const std::string& input){
    if(level<min_level) return; std::lock_guard<std::mutex> g(lock);
    auto t=std::time(nullptr); std::ostringstream s; s<<"["<<std::put_time(std::localtime(&t),"%Y-%m-%d %H:%M:%S")<<"]: *"<<name<<"* "<<input<<"\n";
    if(out.is_open()) out<<s.str(); else std::clog<<s.str();
}
void Logger::flush(){ std::lock_guard<std::mutex> g(lock); if(out.is_open()) out.flush(); }
void Logger::log_info(std::string input){ write(2,"info",input); }
void Logger::log_info(std::string input,int timestep){ log_info("[timetick="+std::to_string(timestep)+"] "+input); }
void Logger::log_fatal(std::string input,int timestep){ log_fatal("[timetick="+std::to_string(timestep)+"] "+input); }
void Logger::log_fatal(std::string input){ write(5,"fatal",input); if(out.is_open()) out.flush(); }
void Logger::log_warning(std::string input){ write(3,"warning",input); }
void Logger::log_warning(std::string input,int timestep){ log_warning("[timetick="+std::to_string(timestep)+"] "+input); }
