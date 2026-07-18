import subprocess
from pathlib import Path

cwd = Path(r"c:\Users\snype\Downloads\insurance_app")

def run_git(args):
    result = subprocess.run(["git"] + args, cwd=str(cwd), capture_output=True, text=True)
    print(f"Running: git {' '.join(args)}")
    if result.returncode == 0:
        print("Success:")
        print(result.stdout)
    else:
        print("Error:")
        print(result.stderr)
    return result.returncode == 0

# 1. Initialize repository
print("Initializing Git repository...")
run_git(["init"])

# 2. Add files
print("Adding files...")
run_git(["add", "."])

# 3. Initial commit
print("Creating initial commit...")
run_git(["commit", "-m", "Initial commit: Prudential Insurance Risk Decision Support Platform"])
