from pathlib import Path
import shutil

backup = Path('/home/jshome/Projects/NoorBrain/backups/sprint8c2-startup-silence-20260801-125411')
project = Path.home() / 'Projects' / 'NoorBrain'
for relative in [
    'dashboard/js/sprint8c-voice-repeat-guard.js',
    'dashboard/mobile/index.html',
    'dashboard/index.html',
    'dashboard/pwa/sw.js',
]:
    source = backup / relative
    target = project / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
print('SPRINT 8C.2 ROLLBACK COMPLETE')
