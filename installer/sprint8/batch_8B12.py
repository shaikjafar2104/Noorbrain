from pathlib import Path
import subprocess,sys
P=Path.home()/"Projects"/"NoorBrain"; test=P/"tests/sprint8b_smoke_test.py"
if not test.exists():raise SystemExit(f"Missing: {test}")
subprocess.run([sys.executable,str(test)],check=True)
print("SPRINT 8B.12 FINAL TEST PASS")
