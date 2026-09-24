import subprocess
import shutil
import os

def run(cmd):
    print("Running:", cmd)
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if res.stdout: print(res.stdout)
    if res.stderr: print(res.stderr)
    return res

# 1. Fetch
run("git fetch origin gh-pages")

# 2. Checkout gh-pages
run("git checkout gh-pages")
run("git pull origin gh-pages")

# 3. Checkout dist contents from master
run("git checkout master -- dist/")

# 4. Copy all files from dist/ to current root
dist_dir = "dist"
for item in os.listdir(dist_dir):
    s = os.path.join(dist_dir, item)
    d = os.path.join(".", item)
    if os.path.isdir(s):
        if os.path.exists(d):
            shutil.rmtree(d)
        shutil.copytree(s, d)
    else:
        shutil.copy2(s, d)

# Clean up dist folder from gh-pages branch
shutil.rmtree(dist_dir)

# 5. Commit and push
run("git add -A")
run('git commit -m "Deploy updated HTML with root base href and custom domain algorise-ai.com"')
run("git push origin gh-pages")

# 6. Switch back to master
run("git checkout master")

print("Deployment to gh-pages complete!")
