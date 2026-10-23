#!/bin/sh
python /benchmark/prepare.py "$1" --workspace /workspace >&2
exec python /benchmark/grade.py "$1" --workspace /workspace
