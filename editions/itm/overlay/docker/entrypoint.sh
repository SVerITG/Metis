#!/usr/bin/env bash
# First start: create the database and apply the wizard answers of a fictional
# new colleague (docker/sample-answers.json), exactly as install.ps1 does on
# Windows. Then run the dashboard, the smoke test, or the install doctor.
set -euo pipefail
cd /metis
if [ ! -f /data/.initialised ]; then
  mkdir -p /data
  python system/installer/init_db.py
  python system/install/process_wizard_answers.py \
      --answers docker/sample-answers.json --metis-root /metis --quiet
  touch /data/.initialised
fi
case "${1:-dashboard}" in
  dashboard)
    cd system/app-py
    exec python -m uvicorn main:app --host 0.0.0.0 --port 8080 ;;
  test)
    exec python docker/smoke_test.py ;;
  doctor)
    exec python system/install/metis_verify.py ;;
  *)
    exec "$@" ;;
esac
