from pathlib import Path
import shutil
backup=Path('/home/jshome/Projects/NoorBrain/backups/sprint14-production-20260802-040006')
project=Path.home()/'Projects'/'NoorBrain'
for relative in ['main.py','dashboard/index.html','dashboard/mobile/index.html','dashboard/pwa/sw.js']:
    shutil.copy2(backup/relative,project/relative)
service=project/'services/platform_release_v14'
if service.exists():shutil.rmtree(service)
if (backup/'service').exists():shutil.copytree(backup/'service',service)
print('SPRINT 14 ROLLBACK COMPLETE')
