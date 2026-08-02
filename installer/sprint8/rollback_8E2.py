from pathlib import Path
import shutil

backup = Path('/home/jshome/Projects/NoorBrain/backups/sprint8e2-mobile-ai-20260801-131122')
project = Path.home() / 'Projects' / 'NoorBrain'
shutil.copy2(backup / 'index.html', project / 'dashboard/mobile/index.html')
shutil.copy2(backup / 'sw.js', project / 'dashboard/pwa/sw.js')
(project / 'dashboard/js/sprint8e2-mobile-ai.js').unlink(missing_ok=True)
(project / 'dashboard/css/sprint8e2-mobile-ai.css').unlink(missing_ok=True)
print('SPRINT 8E.2 ROLLBACK COMPLETE')
