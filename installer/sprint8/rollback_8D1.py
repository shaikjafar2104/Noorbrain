from pathlib import Path
import shutil

backup = Path('/home/jshome/Projects/NoorBrain/backups/sprint8d1-conversation-memory-20260801-125817')
project = Path.home() / 'Projects' / 'NoorBrain'
shutil.copy2(backup / 'main.py', project / 'main.py')
service = project / 'services' / 'halo_conversation_memory_v8'
if service.exists(): shutil.rmtree(service)
if (backup / 'service').exists():
    shutil.copytree(backup / 'service', service)
print('SPRINT 8D.1 ROLLBACK COMPLETE')
