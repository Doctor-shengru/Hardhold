#!/bin/bash
# 构建俯卧撑计数 APK：aapt(资源) -> javac -> d8(dex) -> 塞 dex/so -> zipalign -> apksigner
set -euo pipefail
cd "$(dirname "$0")"

BT=tools/android-14                 # build-tools 34
ANDROID_JAR=tools/android-34/android.jar
APP=app/src/main
OUT=build/out
PROJ_JARS=$(ls libs/*.jar libs/x/jars/*.jar | grep -v auto-value)
LIB_JARS=$(ls libs/*.jar libs/x/jars/*.jar | grep auto-value || true)
CP="$ANDROID_JAR:$(echo "$PROJ_JARS" | tr '\n' ':'):$(echo "$LIB_JARS" | tr '\n' ':')"

rm -rf "$OUT" build/classes build/dex
mkdir -p "$OUT" build/classes build/dex

echo "[1/6] javac"
if ! javac -encoding UTF-8 -source 8 -target 8 -nowarn -cp "$CP" -d build/classes $(find "$APP/java" -name '*.java') 2> build/javac.log; then
  grep -v "bootstrap class path" build/javac.log | head -30
  exit 1
fi
echo "      classes: $(find build/classes -name '*.class' | wc -l)"

echo "[2/6] aapt package (manifest + assets)"
aapt package -f -M "$APP/AndroidManifest.xml" -S "$APP/res" -A "$APP/assets" -I "$ANDROID_JAR" -F "$OUT/base.apk"

echo "[3/6] d8 (dex)"
LIB_ARGS=("--lib" "$ANDROID_JAR")
for j in $LIB_JARS; do LIB_ARGS+=("--lib" "$j"); done
java -cp "$BT/lib/d8.jar" com.android.tools.r8.D8 \
  --release --min-api 24 "${LIB_ARGS[@]}" \
  --output build/dex $(find build/classes -name '*.class') $PROJ_JARS > build/d8.log 2>&1 || { tail -20 build/d8.log; exit 1; }
ls -lh build/dex/classes.dex

echo "[4/6] 打包 dex + native libs"
python3 package.py "$OUT/base.apk" "$OUT/unaligned.apk" \
  "classes.dex=build/dex/classes.dex" \
  "lib/arm64-v8a/libmediapipe_tasks_vision_jni.so=libs/x/native/tasks-vision-0.10.14/arm64-v8a/libmediapipe_tasks_vision_jni.so" \
  "lib/armeabi-v7a/libmediapipe_tasks_vision_jni.so=libs/x/native/tasks-vision-0.10.14/armeabi-v7a/libmediapipe_tasks_vision_jni.so"

echo "[5/6] zipalign"
zipalign -f -p 4 "$OUT/unaligned.apk" "$OUT/aligned.apk"

echo "[6/6] 签名"
if [ ! -f tools/debug.keystore ]; then
  keytool -genkeypair -keystore tools/debug.keystore -alias pushup \
    -keyalg RSA -keysize 2048 -validity 10000 \
    -storepass android -keypass android \
    -dname "CN=Pushup Counter, OU=DSH, O=DSH, L=Local, ST=Local, C=CN" >/dev/null 2>&1
fi
java -jar "$BT/lib/apksigner.jar" sign \
  --ks tools/debug.keystore --ks-pass pass:android --key-pass pass:android \
  --min-sdk-version 24 --v1-signing-enabled true --v2-signing-enabled true \
  --out pushup-counter.apk "$OUT/aligned.apk"

echo "--- verify ---"
java -jar "$BT/lib/apksigner.jar" verify --print-certs pushup-counter.apk | head -4
ls -lh pushup-counter.apk
