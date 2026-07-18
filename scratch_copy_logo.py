import shutil
from pathlib import Path

source = Path(r"C:\Users\snype\.gemini\antigravity-ide\brain\8bb506a0-6824-436d-87c4-355a6c8da02b\media__1784371172821.png")
target = Path(r"c:\Users\snype\Downloads\insurance_app\landing\logo.png")

if source.exists():
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    print("SUCCESS: Logo copied to landing/logo.png")
else:
    print(f"ERROR: Source file {source} does not exist")
