#!/bin/sh
exec mini --exit-immediately --yolo \
  --task "$HARNESS_PROMPT" \
  --environment-class docker \
  --config mini.yaml \
  --config "environment.image=$HARNESS_IMAGE" \
  --config environment.cwd=/workspace \
  --config "environment.run_args=$HARNESS_DOCKER_RUN_ARGS" \
  --config "agent.wall_time_limit_seconds=$HARNESS_TIMEOUT_SECONDS" \
  --config agent.step_limit=50 \
  --output "$HARNESS_OUTPUT_DIR/trajectory.json"
