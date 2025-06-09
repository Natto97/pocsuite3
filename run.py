import os
import re
import shutil
import json
import asyncio
import tempfile
import subprocess
import requests
import time
import hashlib
import logging
from typing import List

# logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

requests.packages.urllib3.disable_warnings()

current_path = os.path.dirname(os.path.abspath(__file__))


def md5(msg, encoding='utf8'):
    return hashlib.md5(msg.encode(encoding)).hexdigest()


def write_json(path, data, encoding="utf8"):
    with open(path, "w", encoding=encoding) as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def read_json(path, default_data={}, encoding="utf8"):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding=encoding) as f:
                return json.load(f)
        except:
            pass
    write_json(path, default_data, encoding)
    return default_data


def github_search(url: str, token: str) -> List[str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "Mozilla/5.0"
    }
    repos = []
    for page in range(1, 6):
        full_url = f"{url}&page={page}&per_page=100"
        response = requests.get(full_url, headers=headers, verify=False)
        if response.status_code != 200:
            logger.warning(f"GitHub API error: {response.status_code}, {response.text}")
            break
        data = response.json()
        items = data.get("items", [])
        if not items:
            break
        for item in items:
            repos.append(item['repository']['html_url'] if 'repository' in item else item['html_url'])
    return list(set(repos))


def is_valid_poc(content: str) -> bool:
    return bool(re.search(r'class\s+\w+\(POCBase\):.*?def\s+_verify\(self\)', content, re.S))


def find_pocs(json_file_path, data, temp_directory, links):
    for link in links:
        link_hash = md5(link)
        for root, _, files in os.walk(os.path.join(temp_directory, link_hash)):
            for file in files:
                if not file.endswith('.py'):
                    continue
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf8') as f:
                        content = f.read()
                except:
                    continue
                if is_valid_poc(content):
                    if file not in data.get(link, {}):
                        data.setdefault(link, {})[file] = time.strftime("%Y-%m-%d %H:%M:%S")
                        shutil.copy2(file_path, os.path.join(current_path, 'poc', file))
        write_json(json_file_path, data)


def commit_push(msg):
    os.chdir(current_path)
    os.system('git add .')
    os.system(f'git commit -m "{msg}"')


async def clone_github_project(link, save_directory):
    if os.path.exists(save_directory):
        return
    os.makedirs(save_directory, exist_ok=True)
    command = f"git clone --depth=1 {link} {save_directory}"
    proc = await asyncio.create_subprocess_shell(command)
    await proc.wait()


async def clone_all(links, temp_directory):
    tasks = [clone_github_project(link, os.path.join(temp_directory, md5(link))) for link in links]
    await asyncio.gather(*tasks)


async def main():
    json_path = os.path.join(current_path, 'data.json')
    poc_dir = os.path.join(current_path, 'poc')
    os.makedirs(poc_dir, exist_ok=True)

    data = read_json(json_path)
    token = os.getenv("GH_TOKEN", "")

    old_links = list(data.keys())
    links_from_code = github_search('https://api.github.com/search/code?q="pocsuite3.api"+language:Python', token)
    links_from_repo = github_search('https://api.github.com/search/repositories?q=pocsuite3', token)
    links = list(set(old_links + links_from_code + links_from_repo))

    # 排除自身项目链接
    blacklist = [
        'https://github.com/20142995/pocsuite3',
        'https://github.com/20142995/pocs',
        'https://github.com/Natto97/pocsuite3'
    ]
    links = [link for link in links if link not in blacklist]

    temp_dir = tempfile.mkdtemp()
    await clone_all(links, temp_dir)

    find_pocs(json_path, data, temp_dir, links)

    readme_path = os.path.join(current_path, 'README.md')
    with open(readme_path, 'w', encoding='utf8') as f:
        f.write(f"## pocsuite3 POC库，共 {len(os.listdir(poc_dir))} 个，更新时间：{time.strftime('%Y-%m-%d %H:%M:%S')}\n")

    commit_push("update pocs")


if __name__ == '__main__':
    asyncio.run(main())
