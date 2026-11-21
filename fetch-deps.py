#!/usr/bin/env python3
"""从 Maven 仓库拉取 MediaPipe tasks-vision 及其传递依赖，解出 jars / native 库。

输出布局（build.sh 依赖这个结构）：
    libs/*.jar                        普通 jar 依赖
    libs/x/jars/<artifact>-<ver>.jar  AAR 里的 classes.jar
    libs/x/native/<artifact>-<ver>/<abi>/*.so

用法：python3 fetch-deps.py [--version 0.10.14]
"""
import os
import re
import sys
import urllib.request
import zipfile

# 国内镜像优先；连不上会依次回退到官方源
REPOS = [
    'https://maven.aliyun.com/repository/google',
    'https://maven.aliyun.com/repository/central',
    'https://dl.google.com/dl/android/maven2',
    'https://repo1.maven.org/maven2',
]
ROOT = os.path.dirname(os.path.abspath(__file__))
LIBS = os.path.join(ROOT, 'libs')
VERSION = '0.10.14'
if '--version' in sys.argv:
    VERSION = sys.argv[sys.argv.index('--version') + 1]


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0',
                                               'Accept-Encoding': 'identity'})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read()


def coord(g, a, v):
    return '%s:%s:%s' % (g, a, v)


def pom_path(g, a, v):
    return '%s/%s/%s/%s' % (g.replace('.', '/'), a, v, '%s-%s.pom' % (a, v))


def get_pom(g, a, v):
    for repo in REPOS:
        try:
            return fetch(repo + '/' + pom_path(g, a, v)).decode('utf-8', 'replace'), repo
        except Exception:
            continue
    return None, None


def parse_deps(xml):
    out = []
    for block in re.findall(r'<dependency>([\s\S]*?)</dependency>', xml):
        g = re.search(r'<groupId>([^<]+)</groupId>', block)
        a = re.search(r'<artifactId>([^<]+)</artifactId>', block)
        v = re.search(r'<version>([^<]+)</version>', block)
        scope = re.search(r'<scope>([^<]+)</scope>', block)
        if not (g and a and v):
            continue
        if '<optional>true</optional>' in block:
            continue
        if scope and scope.group(1) in ('test', 'provided', 'system'):
            continue
        if '${' in v.group(1):
            continue
        out.append((g.group(1), a.group(1), v.group(1)))
    return out


def download_artifact(g, a, v, repo):
    base = '%s/%s/%s/%s/%s-%s' % (repo, g.replace('.', '/'), a, v, a, v)
    for ext in ('aar', 'jar'):
        try:
            return fetch(base + '.' + ext), ext
        except Exception:
            continue
    return None, None


def extract(a, v, data, ext):
    name = '%s-%s' % (a, v)
    if ext == 'jar':
        dest = os.path.join(LIBS, name + '.jar')
        os.makedirs(LIBS, exist_ok=True)
        with open(dest, 'wb') as f:
            f.write(data)
        print('  jar  %s' % name)
        return
    import io
    zf = zipfile.ZipFile(io.BytesIO(data))
    os.makedirs(os.path.join(LIBS, 'x', 'jars'), exist_ok=True)
    if 'classes.jar' in zf.namelist():
        with open(os.path.join(LIBS, 'x', 'jars', name + '.jar'), 'wb') as f:
            f.write(zf.read('classes.jar'))
    for entry in zf.namelist():
        if entry.startswith('jni/') and entry.endswith('.so'):
            rel = entry[len('jni/'):]          # e.g. arm64-v8a/libxxx.so
            dest = os.path.join(LIBS, 'x', 'native', name, rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, 'wb') as f:
                f.write(zf.read(entry))
    print('  aar  %s' % name)


def main():
    seen = set()
    queue = [('com.google.mediapipe', 'tasks-vision', VERSION)]
    while queue:
        g, a, v = queue.pop(0)
        key = coord(g, a, v)
        if key in seen:
            continue
        seen.add(key)
        xml, repo = get_pom(g, a, v)
        if xml is None:
            print('  !! 找不到 POM：%s' % key)
            continue
        data, ext = download_artifact(g, a, v, repo)
        if data is None:
            print('  !! 下载失败：%s' % key)
            continue
        extract(a, v, data, ext)
        queue.extend(parse_deps(xml))
    print('依赖完成，共 %d 个' % len(seen))


if __name__ == '__main__':
    main()
