from pathlib import Path
import shutil

backup = Path('/home/jshome/Projects/NoorBrain/backups/unified-product-ui-20260802-042926')
project = Path.home() / 'Projects' / 'NoorBrain'
for relative in [
    'dashboard/index.html',
    'dashboard/mobile/index.html',
    'dashboard/pwa/sw.js',
]:
    shutil.copy2(backup / relative, project / relative)
voice_backup = backup / 'data/voice_platform_v9.json'
if voice_backup.is_file():
    shutil.copy2(voice_backup, project / 'data/voice_platform_v9.json')
(project / 'dashboard/js/unified-product-ui.js').unlink(missing_ok=True)
(project / 'dashboard/css/unified-product-ui.css').unlink(missing_ok=True)
print('UNIFIED PRODUCT UI ROLLBACK COMPLETE')
