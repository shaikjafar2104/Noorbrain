from pathlib import Path
import shutil
b=Path('/home/jshome/Projects/NoorBrain/backups/sprint13-20260802-034848')
p=Path.home()/'Projects'/'NoorBrain'
for r in ['main.py','dashboard/index.html','dashboard/mobile/index.html','dashboard/pwa/sw.js']:shutil.copy2(b/r,p/r)
shutil.rmtree(p/'services/plugin_platform_v13',ignore_errors=True)
print('SPRINT 13 ROLLBACK COMPLETE')
