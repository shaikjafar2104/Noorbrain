# NoorBrain Installer Architecture

## Sprint 8

cd ~/Projects/NoorBrain
source venv/bin/activate
python installer/sprint8/install_all.py
python tests/sprint8_smoke_test.py

## Rollback

cd ~/Projects/NoorBrain
source venv/bin/activate
python installer/rollback.py

## Storage Report

python tools/storage_report.py

## Remove Old Downloaded Sprint Packages

python tools/cleanup_old_packages.py
