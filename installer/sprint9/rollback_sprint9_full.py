from pathlib import Path
import shutil
backup=Path('/home/jshome/Projects/NoorBrain/backups/sprint9-full-20260801-134633')
project=Path.home()/'Projects'/'NoorBrain'
for r in ['main.py','dashboard/index.html','dashboard/mobile/index.html','dashboard/pwa/sw.js']: shutil.copy2(backup/r,project/r)
service=project/'services/voice_platform_v9'
if service.exists(): shutil.rmtree(service)
if (backup/'service').exists(): shutil.copytree(backup/'service',service)
(project/'dashboard/js/sprint9-voice-platform.js').unlink(missing_ok=True)
(project/'dashboard/css/sprint9-voice-platform.css').unlink(missing_ok=True)
print('SPRINT 9 FULL ROLLBACK COMPLETE')
