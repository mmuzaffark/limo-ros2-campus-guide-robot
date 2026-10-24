#!/bin/bash
# gate2: AMCL-driven test; home faces the bay back wall (yaw pi)
source ~/env.sh
PASSES=${1:-3}
G=("4.25 1.7 0.7071 0.7071" "0.0 0.0 1.0 0.0" "9.5 1.2 0.7071 0.7071" "0.0 0.0 1.0 0.0" "4.75 -1.7 -0.7071 0.7071" "0.0 0.0 1.0 0.0")
for r in $(seq 1 $PASSES); do echo "##### pass $r"
  for g in "${G[@]}"; do set -- $g
    s=$(go $g 2>&1 | grep -o "status: [A-Z]*")
    echo "$(date +%T) goal ($1,$2) $s | $(python3 ~/truth.py $1 $2 | grep -o 'amcl error.*') | $(python3 ~/stale.py)"
  done
done
echo "too old: $(grep -c 'too old' ~/nav2_run.log)"
