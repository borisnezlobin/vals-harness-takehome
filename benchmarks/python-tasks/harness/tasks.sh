#!/bin/sh
exec python3 - "$(dirname "$0")/../dataset.json" <<'EOF'
import json, sys

tasks = json.load(open(sys.argv[1]))
print(json.dumps([
    {"id": t["id"], "prompt": f"{t['prompt']}\n\nWrite your solution in {t['solution_file']}."}
    for t in tasks
]))
EOF
