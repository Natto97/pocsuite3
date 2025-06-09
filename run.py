import os
import subprocess
import shutil
import hashlib
from github import Github

# GitHub token (为了能够使用GitHub API，你需要设置你的token)
GITHUB_TOKEN = os.getenv("GH_TOKEN", "")

# 本地目录设置
DATA_DIR = "poc"
POC_DIR = "poc"

# 初始化GitHub API
g = Github(GITHUB_TOKEN)

# 搜索包含"pocsuite3.api"的Python项目
search_query = 'pocsuite3.api language:Python'
repos = g.search_repositories(search_query)
print(repos)

# 用来保存已经处理的文件的MD5哈希值，防止重复
processed_files_md5 = set()

# 计算文件的MD5值
def calculate_md5(file_path):
    md5_hash = hashlib.md5()
    with open(file_path, "rb") as f:
        # 读取文件并更新md5
        for byte_block in iter(lambda: f.read(4096), b""):
            md5_hash.update(byte_block)
    return md5_hash.hexdigest()

# 克隆项目并查找符合条件的文件
for repo in repos:
    repo_name = repo.full_name
    clone_url = repo.clone_url
    repo_dir = os.path.join(DATA_DIR, repo_name.split("/")[-1])
    
    # 克隆项目
    print(f"Cloning repo: {repo_name}")
    subprocess.run(["git", "clone", clone_url, repo_dir])
    
    # 遍历项目中的所有文件，查找包含"pocsuite3.api"的文件
    for root, dirs, files in os.walk(repo_dir):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                # 计算当前文件的MD5
                file_md5 = calculate_md5(file_path)
                
                # 如果文件的MD5已处理过，则跳过此文件
                if file_md5 in processed_files_md5:
                    print(f"Skipping duplicate file: {file_path}")
                    continue
                
                # 将文件的MD5添加到已处理集合中
                processed_files_md5.add(file_md5)
                
                # 打开文件并检查是否包含"pocsuite3.api"
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if "pocsuite3.api" in content:
                        # 移动文件到poc目录
                        target_path = os.path.join(POC_DIR, file)
                        
                        print(f"Moving file {file_path} to {target_path}")
                        shutil.move(file_path, target_path)
            except Exception as e:
                print(f"Error processing file {file_path}: {e}")
