from pathlib import Path
import shutil

backup = Path('/home/jshome/Projects/NoorBrain/backups/sprint8f-production-final-20260801-133420')
project = Path.home() / 'Projects' / 'NoorBrain'
shutil.copy2(backup / 'main.py', project / 'main.py')
service = project / 'services' / 'sprint8_release'
if service.exists(): shutil.rmtree(service)
if (backup / 'service').exists(): shutil.copytree(backup / 'service', service)
release = project / 'data' / 'sprint8_release.json'
if (backup / 'sprint8_release.json').exists():
    shutil.copy2(backup / 'sprint8_release.json', release)
else:
    release.unlink(missing_ok=True)
print('SPRINT 8F ROLLBACK COMPLETE')
