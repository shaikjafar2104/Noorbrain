from pathlib import Path
import shutil

backup = Path('/home/jshome/Projects/NoorBrain/backups/sprint8e1-ai-dashboard-20260801-130417')
project = Path.home() / 'Projects' / 'NoorBrain'
shutil.copy2(backup / 'main.py', project / 'main.py')
shutil.copy2(backup / 'index.html', project / 'dashboard' / 'index.html')
service = project / 'services' / 'ai_control_center_v8'
if service.exists(): shutil.rmtree(service)
if (backup / 'service').exists(): shutil.copytree(backup / 'service', service)
(project / 'dashboard/js/sprint8e1-ai-dashboard.js').unlink(missing_ok=True)
(project / 'dashboard/css/sprint8e1-ai-dashboard.css').unlink(missing_ok=True)
print('SPRINT 8E.1 ROLLBACK COMPLETE')
