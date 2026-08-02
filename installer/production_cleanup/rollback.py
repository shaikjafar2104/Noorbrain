from pathlib import Path
import shutil

backup = Path('/home/jshome/Projects/NoorBrain/backups/production-ui-cleanup-20260802-042228')
project = Path.home() / 'Projects' / 'NoorBrain'
for relative in [
    'dashboard/index.html',
    'dashboard/mobile/index.html',
    'dashboard/pwa/sw.js',
]:
    shutil.copy2(backup / relative, project / relative)
(project / 'dashboard/js/production-ui-cleanup.js').unlink(missing_ok=True)
(project / 'dashboard/css/production-ui-cleanup.css').unlink(missing_ok=True)
print('PRODUCTION UI CLEANUP ROLLBACK COMPLETE')
