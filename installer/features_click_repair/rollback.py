from pathlib import Path
import shutil

backup = Path('/home/jshome/Projects/NoorBrain/backups/features-click-repair-20260802-051000')
project = Path.home() / 'Projects' / 'NoorBrain'
for relative in [
    'dashboard/index.html',
    'dashboard/mobile/index.html',
    'dashboard/pwa/sw.js',
]:
    shutil.copy2(backup / relative, project / relative)
(project / 'dashboard/js/features-click-repair.js').unlink(missing_ok=True)
(project / 'dashboard/css/features-click-repair.css').unlink(missing_ok=True)
print('FEATURES CLICK REPAIR ROLLBACK COMPLETE')
