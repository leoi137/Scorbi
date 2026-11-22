#!/bin/bash
# One recorded run on the GPU: train, then evaluate every saved checkpoint, the noise batch, the do-nothing control and the shove ladder.
#   run_recorded.sh NAME TASK SEED ITERATIONS 'META JSON' [DETAIL_AT]
# Writes /workspace/logs/NAME.*.log and, when everything is done, <run>/scorbi/eval_done.json.
set -u
# A queued run is cancelled by creating /workspace/skip/NAME before it starts.
if [ -e "/workspace/skip/$1" ]; then echo "$(date -u +%FT%TZ) skipped $1" >> /workspace/logs/skipped.log; exit 0; fi
NAME=$1; TASK=$2; SEED=$3; ITERS=$4; META=$5; DETAIL=${6:-0,5,20,50,100,200,300,400,last}
# SCORBI_CODE names another checkout to run from (default /workspace/Scorbi), so new code can run beside a queue that uses the old.
CODE=${SCORBI_CODE:-/workspace/Scorbi}; T=$CODE/training/tools; L=/workspace/logs
export PYTHONPATH=$CODE/training${PYTHONPATH:+:$PYTHONPATH}
cd /workspace/isaaclab
SCORBI_RUN_META="$META" uv run python $T/train.py --task "$TASK" --seed "$SEED" --max_iterations "$ITERS" --run_name "$NAME" > $L/$NAME.train.log 2>&1
echo "EXIT $?" >> $L/$NAME.train.log
D=$(ls -d logs/rsl_rl/scorbi_flat/*_"$NAME" | tail -1)
uv run python $T/evaluate.py --run "$D" --iterations all --detail_at "$DETAIL" --skip_done > $L/$NAME.eval.log 2>&1; A=$?
uv run python $T/evaluate.py --run "$D" --iterations 0,last --noise_std 1.0 --seeds 8 --detail_at none > $L/$NAME.noise.log 2>&1; B=$?
uv run python $T/evaluate.py --run "$D" --do_nothing --detail_at none > $L/$NAME.nothing.log 2>&1; C=$?
# The shove ladder: the two shoved commands at 0.5 to 2 m/s. Scorbi shrugs off anything under about 1 m/s (research 0006).
uv run python $T/evaluate.py --run "$D" --iterations 0,50,100,200,last --shove_speeds 0.5,1.0,1.5,2.0 --detail_at last > $L/$NAME.shove.log 2>&1; S=$?
echo "{\"run\": \"$(basename "$D")\", \"eval_exit\": $A, \"noise_exit\": $B, \"do_nothing_exit\": $C, \"shove_exit\": $S, \"finished_at\": \"$(date -u +%FT%TZ)\"}" > "$D/scorbi/eval_done.json"
