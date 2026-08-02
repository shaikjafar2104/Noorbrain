from pathlib import Path
import shutil
backup=Path('/home/jshome/Projects/NoorBrain/backups/sprint11-family-vision-20260802-033438')
project=Path.home()/'Projects'/'NoorBrain'
for r in ['main.py','dashboard/index.html','dashboard/mobile/index.html','dashboard/pwa/sw.js']:shutil.copy2(backup/r,project/r)
service=project/'services/family_intelligence_v11'
if service.exists():shutil.rmtree(service)
if (backup/'service').exists():shutil.copytree(backup/'service',service)
(project/'dashboard/js/sprint11-family-vision.js').unlink(missing_ok=True)
(project/'dashboard/css/sprint11-family-vision.css').unlink(missing_ok=True)
print('SPRINT 11 ROLLBACK COMPLETE')
