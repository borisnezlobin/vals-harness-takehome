#!/bin/sh
exec python3 /benchmark/evaluate.py --workspace-dir /workspace --task "$1"
