from pathlib import Path
import shutil

backup = Path('/home/jshome/Projects/NoorBrain/backups/sprint9a1-universal-voice-20260801-133840')
project = Path.home() / 'Projects' / 'NoorBrain'
for relative in ['main.py','dashboard/index.html','dashboard/mobile/index.html','dashboard/pwa/sw.js']:
    shutil.copy2(backup / relative, project / relative)
service = project / 'services/universal_voice_gateway_v9'
if service.exists(): shutil.rmtree(service)
if (backup / 'service').exists(): shutil.copytree(backup / 'service', service)
(project / 'dashboard/js/sprint9a1-universal-voice.js').unlink(missing_ok=True)
print('SPRINT 9A.1 ROLLBACK COMPLETE')
