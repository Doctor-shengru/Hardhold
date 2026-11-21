#!/bin/bash
# 构建「硬撑」APK：aapt(资源) -> javac -> d8(dex) -> 塞 dex/so -> zipalign -> apksigner
#
# 可用环境变量覆盖（CI 用）：
#   BUILD_TOOLS   build-tools 目录（含 aapt / zipalign / lib/d8.jar / lib/apksigner.jar）
#   ANDROID_JAR   platform 的 android.jar
#   AAPT / ZIPALIGN  单独指定可执行文件（默认优先用 BUILD_TOOLS 里的原生二进制）
#   VERSION_CODE / VERSION_NAME  覆盖清单里的版本号
#   KEYSTORE / KS_PASS / KEY_ALIAS / KEY_PASS  签名材料（默认 tools/debug.keystore，密码 android）
set -euo pipefail
cd "$(dirname "$0")"

BT=${BUILD_TOOLS:-tools/android-14}
ANDROID_JAR=${ANDROID_JAR:-tools/android-34/android.jar}
APP=app/src/main
OUT=build/out
JARS_LIST=$(ls libs/*.jar libs/x/jars/*.jar)
# auto-value 只在编译期当注解处理器，不进 dex；其余 jar 需要作为程序输入打进 dex
PROJ_JARS=$(echo "$JARS_LIST" | grep -v auto-value || true)
LIB_JARS=$(echo "$JARS_LIST" | grep auto-value || true)
CP="$ANDROID_JAR:$(echo "$JARS_LIST" | tr '\n' ':')"

# build-tools 里的二进制在 x86 主机上可直接跑；在 arm64 上跑不了就退回系统自带的
if [ -z "${AAPT:-}" ]; then
  AAPT=aapt
  if [ -x "$BT/aapt" ] && "$BT/aapt" version >/dev/null 2>&1; then AAPT="$BT/aapt"; fi
fi
if [ -z "${ZIPALIGN:-}" ]; then
  ZIPALIGN=zipalign
  # zipalign 无参运行会打印用法并返回非 0，配合 set -o pipefail 必须 || true 兜住
  if [ -x "$BT/zipalign" ] && { "$BT/zipalign" 2>&1 || true; } | grep -q "Zip alignment"; then
    ZIPALIGN="$BT/zipalign"
  fi
fi

# 本地签名材料（.signing/env，不进仓库）：存在则自动加载
if [ -f .signing/env ]; then set -a; . .signing/env; set +a; fi

KEYSTORE=${KEYSTORE:-tools/debug.keystore}
KS_PASS=${KS_PASS:-android}
KEY_ALIAS=${KEY_ALIAS:-pushup}
KEY_PASS=${KEY_PASS:-android}

rm -rf "$OUT" build/classes build/dex
mkdir -p "$OUT" build/classes build/dex

MANIFEST="$APP/AndroidManifest.xml"
if [ -n "${VERSION_CODE:-}" ] || [ -n "${VERSION_NAME:-}" ]; then
  MANIFEST=build/AndroidManifest.xml
  sed -e "s/android:versionCode=\"[0-9]*\"/android:versionCode=\"${VERSION_CODE:-1}\"/" \
      -e "s/android:versionName=\"[^\"]*\"/android:versionName=\"${VERSION_NAME:-1.0}\"/" \
      "$APP/AndroidManifest.xml" > "$MANIFEST"
  echo "      版本覆盖：versionCode=${VERSION_CODE:-1} versionName=${VERSION_NAME:-1.0}"
fi

echo "[1/6] javac"
if ! javac -encoding UTF-8 -source 8 -target 8 -nowarn -cp "$CP" -d build/classes $(find "$APP/java" -name '*.java') 2> build/javac.log; then
  grep -v "bootstrap class path" build/javac.log | head -30
  exit 1
fi
echo "      classes: $(find build/classes -name '*.class' | wc -l)"

echo "[2/6] aapt package ($AAPT)"
"$AAPT" package -f -M "$MANIFEST" -S "$APP/res" -A "$APP/assets" -I "$ANDROID_JAR" -F "$OUT/base.apk"

echo "[3/6] d8 (dex)"
LIB_ARGS=("--lib" "$ANDROID_JAR")
for j in $LIB_JARS; do LIB_ARGS+=("--lib" "$j"); done
java -cp "$BT/lib/d8.jar" com.android.tools.r8.D8 \
  --release --min-api 24 "${LIB_ARGS[@]}" \
  --output build/dex $(find build/classes -name '*.class') $PROJ_JARS > build/d8.log 2>&1 || { tail -20 build/d8.log; exit 1; }
ls -lh build/dex/classes.dex
DEX_SIZE=$(stat -c%s build/dex/classes.dex)
if [ "$DEX_SIZE" -lt 1048576 ]; then
  echo "错误：classes.dex 只有 $DEX_SIZE 字节，依赖 jar 可能没作为程序输入传进 d8" >&2
  exit 1
fi

echo "[4/6] 打包 dex + native libs"
python3 package.py "$OUT/base.apk" "$OUT/unaligned.apk" \
  "classes.dex=build/dex/classes.dex" \
  "lib/arm64-v8a/libmediapipe_tasks_vision_jni.so=libs/x/native/tasks-vision-0.10.14/arm64-v8a/libmediapipe_tasks_vision_jni.so" \
  "lib/armeabi-v7a/libmediapipe_tasks_vision_jni.so=libs/x/native/tasks-vision-0.10.14/armeabi-v7a/libmediapipe_tasks_vision_jni.so"

echo "[5/6] zipalign ($ZIPALIGN)"
"$ZIPALIGN" -f -p 4 "$OUT/unaligned.apk" "$OUT/aligned.apk"

echo "[6/6] 签名"
if [ ! -f "$KEYSTORE" ]; then
  mkdir -p "$(dirname "$KEYSTORE")"
  echo "      未找到密钥，生成临时密钥：$KEYSTORE"
  keytool -genkeypair -keystore "$KEYSTORE" -alias "$KEY_ALIAS" \
    -keyalg RSA -keysize 2048 -validity 10000 \
    -storepass "$KS_PASS" -keypass "$KEY_PASS" \
    -dname "CN=Hardhold, OU=DSH, O=DSH, L=Local, ST=Local, C=CN" >/dev/null 2>&1
fi
java -jar "$BT/lib/apksigner.jar" sign \
  --ks "$KEYSTORE" --ks-pass "pass:$KS_PASS" --ks-key-alias "$KEY_ALIAS" --key-pass "pass:$KEY_PASS" \
  --min-sdk-version 24 --v1-signing-enabled true --v2-signing-enabled true \
  --out hardhold.apk "$OUT/aligned.apk"

echo "--- verify ---"
java -jar "$BT/lib/apksigner.jar" verify --print-certs hardhold.apk | head -4
"$AAPT" dump badging hardhold.apk | head -2
ls -lh hardhold.apk
