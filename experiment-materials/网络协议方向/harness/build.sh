#!/bin/bash
# 用便携 Cygwin 编译一个源码目录（Linux 版 build_linux.sh 的同样参数，无 Boost / Python）。
# 用法（Git Bash）：bash harness/build.sh src/dev_src_p01 bin/lifelong-p01a.exe
# 编译在同步盘外的英文路径里进行（~/robotnet-lab/build/<目录名>），产物复制到第二个参数。
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"; ROOT="$(dirname "$HERE")"
SRC="$(cd "$1" && pwd)"; OUT="$2"; NAME="$(basename "$SRC")"
TC="${LORR_TOOLCHAIN:-$ROOT/../work/lorr-toolchain/portable}"
B="$HOME/robotnet-lab/build/$NAME"; mkdir -p "$B"
# 只复制源码（不带旧的 build 目录）
( cd "$SRC" && tar cf - --exclude=build-linux --exclude='build-*' . ) | ( cd "$B" && tar xf - )
cat > "$B/_b.sh" <<'EOF'
export PATH=/usr/bin:/bin
cd "$(cygpath -u "$1")"; mkdir -p build-linux/obj
F="-std=c++17 -O3 -DNDEBUG -Ilinux_shim -include linux_shim/port_prelude.h -Iinc -Idefault_planner"
ls src/*.cpp default_planner/*.cpp | while read f; do
  o=build-linux/obj/$(echo $f|tr / _).o
  if [ ! -f $o ] || [ $f -nt $o ] || [ -n "$(find inc default_planner linux_shim -newer $o -name '*.h*' | head -1)" ]; then echo "$f $o"; fi
done > _todo.txt
cat _todo.txt | xargs -P 12 -n 2 sh -c 'g++ '"$F"' -c "$0" -o "$1" || { echo "FAILED $0"; exit 255; }'
g++ build-linux/obj/*.o -o build-linux/lifelong -lpthread
EOF
"$TC/bin/bash.exe" --noprofile --norc "$(cygpath -w "$B/_b.sh")" "$(cygpath -w "$B")" 2>&1 | grep -v "could not find /tmp" | grep -E "error|FAILED|warning: unused" || true
test -f "$B/build-linux/lifelong.exe" || { echo "编译失败"; exit 1; }
[ "$B/build-linux/lifelong.exe" -nt "$B/_todo.txt" ] || { echo "链接没有更新，编译失败"; exit 1; }
mkdir -p "$(dirname "$OUT")"; cp "$B/build-linux/lifelong.exe" "$OUT"
echo "编译完成：$OUT"
