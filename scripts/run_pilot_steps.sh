#!/bin/bash
#
# Run the fine-tuning pilot in stages to avoid CLI timeouts.
# Each stage completes in < 5 minutes.
#
# Usage:
#   bash scripts/run_pilot_step1_setup.sh
#   bash scripts/run_pilot_step2_data.sh
#   bash scripts/run_pilot_step3_run.sh coil2000
#   bash scripts/run_pilot_step3_run.sh uslapseagent
#   bash scripts/run_pilot_step3_run.sh eudirectlapse
#   bash scripts/run_pilot_step3_run.sh spanish_motor_lapse
#   bash scripts/run_pilot_step4_aggregate.sh
#

STAGE=$1

case $STAGE in
  setup)
    # Step 1: Clone repo + install deps (~2 min)
    echo "=== STEP 1: Setup ==="
    echo "
import subprocess, os, sys
if not os.path.exists('/content/tfm'):
    subprocess.run(['git', 'clone', '--branch', 'finetune-v2', 'https://github.com/IFoA-ADSWP/tabular-foundation-model.git', '/content/tfm'])
os.chdir('/content/tfm')
subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '-r', 'requirements.txt'])
print('Setup complete.')
" | colab exec
    ;;

  data)
    # Step 2: Download data (~30s)
    echo "=== STEP 2: Download data ==="
    echo "
import sys; sys.path.insert(0, '/content/tfm')
from scripts.run_pilot import check_data, download_file, DATA_DIR, DATASETS
DATA_DIR.mkdir(parents=True, exist_ok=True)
for name, info in DATASETS.items():
    download_file(info['file'])
print('Data ready.')
" | colab exec
    ;;

  run)
    # Step 3: Run one dataset (~5 min each)
    DATASET=$2
    if [ -z "$DATASET" ]; then
      echo "Usage: $0 run <dataset_name>"
      exit 1
    fi
    echo "=== STEP 3: Running $DATASET ==="
    echo "
import sys; sys.path.insert(0, '/content/tfm')
from scripts.run_pilot import run_single_dataset
run_single_dataset('$DATASET')
print(f'$DATASET complete.')
" | colab exec --timeout 600
    ;;

  aggregate)
    # Step 4: Aggregate results
    echo "=== STEP 4: Aggregate ==="
    echo "
import sys; sys.path.insert(0, '/content/tfm')
from scripts.run_pilot import aggregate_results
aggregate_results()
print('Aggregation complete.')
" | colab exec
    ;;

  *)
    echo "Usage: $0 {setup|data|run <dataset>|aggregate}"
    exit 1
    ;;
esac
