import subprocess
from pathlib import Path
import sys

# Target GitHub Repository URL
REPO_URL = "https://github.com/emmaarthur191/insurance-risk-calculator.git"
cwd = Path(__file__).parent.resolve()

def run_cmd(args):
    print(f"Running: {' '.join(args)} ...")
    try:
        result = subprocess.run(args, cwd=str(cwd), capture_output=True, text=True)
        if result.returncode == 0:
            print("→ Success!")
            if result.stdout.strip():
                print(result.stdout.strip())
            return True
        else:
            print("→ Error:")
            print(result.stderr.strip())
            return False
    except Exception as e:
        print(f"→ Exception occurred: {e}")
        return False

print("=== STARTING AUTOMATED GIT DEPLOYMENT ===")

# 1. Initialize git if not present
if not (cwd / ".git").exists():
    if not run_cmd(["git", "init"]):
        sys.exit(1)

# 2. Stage all files (respecting the .gitignore we created)
if not run_cmd(["git", "add", "."]):
    sys.exit(1)

# 3. Create initial commit
# Check if there are staged changes first to prevent committing empty state error
run_cmd(["git", "commit", "-m", "Initial commit: Prudential Insurance Risk Decision Support Platform"])

# 4. Set the branch to main
if not run_cmd(["git", "branch", "-M", "main"]):
    sys.exit(1)

# 5. Configure remote origin
print("\nConfiguring remote repository URL...")
# Remove origin if it already exists to avoid conflict
subprocess.run(["git", "remote", "remove", "origin"], cwd=str(cwd), capture_output=True)
if not run_cmd(["git", "remote", "add", "origin", REPO_URL]):
    sys.exit(1)

# 6. Push to GitHub
print("\nPushing to GitHub (main branch)...")
print("Note: If prompted, please enter your GitHub credentials or token in the terminal window.")
run_cmd(["git", "push", "-u", "origin", "main"])

print("\n=== DEPLOYMENT SCRIPT FINISHED ===")
