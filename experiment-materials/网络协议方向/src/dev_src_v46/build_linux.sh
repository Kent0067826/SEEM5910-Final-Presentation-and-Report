#!/bin/bash
# Linux port build (no Boost / pybind11). Python bridge excluded.
set -e; cd "$(dirname "$0")"; mkdir -p build-linux/obj
FLAGS="-std=c++17 -O3 -DNDEBUG -Wuninitialized -Wmaybe-uninitialized -Werror=uninitialized -Werror=maybe-uninitialized -Ilinux_shim -include linux_shim/port_prelude.h -Iinc -Idefault_planner"
for f in src/*.cpp default_planner/*.cpp; do o=build-linux/obj/$(echo $f|tr / _).o
  if [ ! -f $o ] || [ $f -nt $o ] || [ -n "$(find inc default_planner linux_shim -newer $o -name '*.h*' | head -1)" ]; then echo "g++ $FLAGS -c $f -o $o"; fi; done | xargs -P 2 -I{} sh -c "{}"
g++ build-linux/obj/*.o -o build-linux/lifelong -lpthread
