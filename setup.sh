#!/bin/bash
# 一键准备构建环境：Android build-tools 34 + platform 34 + MediaPipe 依赖 + 姿态模型
# 用法：./setup.sh            （默认腾讯云镜像，海外可用 MIRROR=https://dl.google.com/dl/android 之类）
set -euo pipefail
cd "$(dirname "$0")"

MIRROR=${MIRROR:-https://mirrors.cloud.tencent.com/AndroidSDK}
BT=build-tools_r34-linux.zip
PLATFORM=platform-34-ext7_r03.zip
MODEL_URL=https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task

dl() {  # dl <url> <dest>
  python3 - "$1" "$2" <<'PY'
import sys, urllib.request
url, dest = sys.argv[1], sys.argv[2]
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, timeout=120) as r, open(dest, 'wb') as f:
    f.write(r.read())
print('  %s' % dest)
PY
}

echo "[1/4] 检查工具"
for t in java javac keytool python3 aapt zipalign; do
  command -v "$t" >/dev/null || echo "  !! 缺少 $t（Debian/Ubuntu: apt install openjdk-17-jdk-headless aapt zipalign unzip）"
done

echo "[2/4] Android build-tools + platform"
mkdir -p tools
if [ ! -f tools/android-34/android.jar ]; then
  [ -f tools/$BT ] || dl "$MIRROR/$BT" "tools/$BT"
  [ -f tools/$PLATFORM ] || dl "$MIRROR/$PLATFORM" "tools/$PLATFORM"
  unzip -q -o "tools/$BT" -d tools
  unzip -q -o "tools/$PLATFORM" -d tools
else
  echo "  已存在，跳过"
fi

echo "[3/4] MediaPipe 依赖（约 120MB）"
if [ ! -d libs/x/jars ]; then
  python3 fetch-deps.py
else
  echo "  已存在，跳过"
fi

echo "[4/4] 姿态模型"
if [ ! -f app/src/main/assets/pose_landmarker_lite.task ]; then
  dl "$MODEL_URL" app/src/main/assets/pose_landmarker_lite.task
else
  echo "  已存在，跳过"
fi

echo
echo "准备完成，接着执行：./build.sh"
