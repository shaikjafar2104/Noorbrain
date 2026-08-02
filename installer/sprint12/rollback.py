from pathlib import Path
import shutil
b=Path('/home/jshome/Projects/NoorBrain/backups/sprint12-20260802-034847')
p=Path.home()/'Projects/NoorBrain'
for r in ['main.py','dashboard/index.html','dashboard/mobile/index.html','dashboard/pwa/sw.js']:shutil.copy2(b/r,p/r)
shutil.rmtree(p/'services/islamic_intelligence_v12',ignore_errors=True)
print('SPRINT 12 ROLLBACK COMPLETE')
