#!/bin/sh
exec mini --exit-immediately --yolo \
  --task "$HARNESS_PROMPT" \
  --environment-class docker \
  --config mini.yaml \
  --config "environment.image=$HARNESS_IMAGE" \
  --config environment.cwd=/workspace \
  --config "environment.run_args=[
    \"--rm\", \"--label\", \"$HARNESS_CONTAINER_LABEL\",
    \"-v\", \"$HARNESS_WORKSPACE:/workspace\",
    \"--network\", \"none\", \"--cap-drop\", \"ALL\", \"--security-opt\", \"no-new-privileges\",
    \"--memory\", \"2g\", \"--cpus\", \"1\", \"--pids-limit\", \"256\"
  ]" \
  --config "agent.wall_time_limit_seconds=$HARNESS_TIMEOUT_SECONDS" \
  --config agent.step_limit=50 \
  --output "$HARNESS_OUTPUT_DIR/trajectory.json"
