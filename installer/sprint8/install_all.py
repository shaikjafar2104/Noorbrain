from pathlib import Path
import subprocess,sys
HERE=Path(__file__).resolve().parent
batches=[HERE/"batch_8A1.py"]+[HERE/f"batch_8B{i}.py" for i in range(1,12)]
for batch in batches:
    if batch.exists():
        print("Running",batch.name)
        subprocess.run([sys.executable,str(batch)],check=True)
print("SPRINT 8 INSTALLER SEQUENCE COMPLETE")
