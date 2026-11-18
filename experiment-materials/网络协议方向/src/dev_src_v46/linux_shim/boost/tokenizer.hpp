#pragma once
// Minimal std-only replacement for the subset of boost::tokenizer used by the start kit (Linux port, no Boost available).
#include <memory>
#include <string>
#include <vector>
namespace boost {
template<class Char> class char_separator {
public:
    explicit char_separator(const Char* d=" "):delims(d){}
    std::vector<std::basic_string<Char>> split(const std::basic_string<Char>& s) const {
        std::vector<std::basic_string<Char>> out; std::basic_string<Char> cur;
        for(Char c:s){ if(delims.find(c)!=std::basic_string<Char>::npos){ if(!cur.empty()){out.push_back(cur);cur.clear();} } else cur.push_back(c);} 
        if(!cur.empty())out.push_back(cur); return out;
    }
private: std::basic_string<Char> delims;
};
template<class Sep, class It=void, class Tok=std::string> class tokenizer {
    std::shared_ptr<std::vector<std::string>> toks;
public:
    tokenizer(const std::string& s, const Sep& sep):toks(std::make_shared<std::vector<std::string>>(sep.split(s))){}
    class iterator {
        std::shared_ptr<std::vector<std::string>> v; size_t i=0;
    public:
        iterator()=default; iterator(std::shared_ptr<std::vector<std::string>> v_,size_t i_):v(v_),i(i_){}
        const std::string& operator*() const {return (*v)[i];}
        const std::string* operator->() const {return &(*v)[i];}
        iterator& operator++(){++i;return *this;} iterator operator++(int){auto t=*this;++i;return t;}
        bool operator==(const iterator& o) const {return i==o.i;} bool operator!=(const iterator& o) const {return i!=o.i;}
    };
    iterator begin() const {return iterator(toks,0);} iterator end() const {return iterator(toks,toks->size());}
};
}
