#!/bin/sh
exec python3 - "$(dirname "$0")/../dataset.json" <<'EOF'
import json, sys

tasks = json.load(open(sys.argv[1]))
print(json.dumps([{"id": t["task_id"], "prompt": t["problem_statement"]} for t in tasks]))
EOF
