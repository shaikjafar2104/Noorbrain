from pathlib import Path
import shutil
backup=Path('/home/jshome/Projects/NoorBrain/backups/sprint10-whole-home-20260802-031743')
project=Path.home()/'Projects'/'NoorBrain'
for r in ['main.py','dashboard/index.html','dashboard/mobile/index.html','dashboard/pwa/sw.js']:shutil.copy2(backup/r,project/r)
service=project/'services/whole_home_v10'
if service.exists():shutil.rmtree(service)
if (backup/'service').exists():shutil.copytree(backup/'service',service)
(project/'dashboard/js/sprint10-whole-home.js').unlink(missing_ok=True)
(project/'dashboard/css/sprint10-whole-home.css').unlink(missing_ok=True)
print('SPRINT 10 ROLLBACK COMPLETE')
