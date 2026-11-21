# 硬撑 · Hardhold

用前置摄像头实时数俯卧撑的 Android App。姿态识别用 MediaPipe Pose Landmarker（lite，5.5 MB），
**完全在手机上推理，不联网、不上传画面**。

> 名字的由来：既是俯卧撑，也是撑住的那口气。

- 包名：`com.pushup.counter`
- 版本：1.2（versionCode 3）
- 安装包：`hardhold.apk`（约 16 MB，见 [Releases](../../releases)）
- 最低系统：Android 7.0（API 24），目标 API 34
- 架构：arm64-v8a、armeabi-v7a
- 技术栈：Camera2 + MediaPipe Tasks Vision + 纯 Java 计数状态机（无 AndroidX、无 Gradle）

## 安装

1. 下载 `hardhold.apk` 保存到手机。
2. 点开安装，若提示"未知来源应用"，允许当前文件管理器安装。
3. 打开「硬撑」，同意摄像头权限。

> 换版本重装若报"签名冲突"，先卸载旧版。APK 使用本地自签证书，不是应用商店版本。

## 使用

- 手机放稳（侧面或正面 1.5–2.5 米），**整个人和两只胳膊都要在画面里**，光线尽量充足。
- 画面上出现绿色骨架后开始做动作：撑起时肘角接近 180°，下去时小臂贴地。
- 顶部大数字是次数，下面是状态（撑起 / 下落 / 动作中）和实时肘角；右下角「重置」清零。
- 计数规则：必须完整走完「撑起 → 下落 → 撑起」，只做半程不计数；手抖、抬手机不会误计数。

### 微调阈值

点右下角「微调」打开面板：

- **撑起 ≥** / **下落 ≤** 两条滑杆直接调角度，面板里实时显示当前肘角。
- **取撑起**：撑到最高点时点一下，把当前肘角设为撑起阈值。
- **取下落**：降到最低点时点一下，把当前肘角设为下落阈值。
- **默认**：恢复 158° / 95°。
- **完成**：保存到本机，下次打开仍然生效。

两条阈值至少要差 15°，否则面板会提示且不保存。计数偏少就把撑起阈值调低；
没撑直也被算就把撑起阈值调高；下到底没数就把下落阈值调高。

## 从源码构建

前置：JDK 17、`aapt`、`zipalign`、`unzip`、`python3`（Debian/Ubuntu：`apt install openjdk-17-jdk-headless aapt zipalign unzip`）。

```bash
./setup.sh     # 下载 build-tools 34、platform 34、MediaPipe 依赖、姿态模型（约 500MB）
./build.sh     # 产物：hardhold.apk
```

`setup.sh` 默认用腾讯云镜像，海外可指定 `MIRROR=` 换源。完整构建约 1 分钟。

没有用 Gradle：`build.sh` 直接调 aapt（资源）→ javac → d8（dex）→ 塞入 dex 与 .so → zipalign → apksigner，
依赖只有仓库里的 `fetch-deps.py` 和系统里的 JDK/Android 工具。

单测（不需要 Android 设备）：

```bash
javac -encoding UTF-8 -d build/test \
  app/src/main/java/com/pushup/counter/PushupCounter.java \
  app/src/main/java/com/pushup/counter/AngleMath.java \
  test/PushupCounterTest.java
java -cp build/test PushupCounterTest
```

## 自动发版（GitHub Actions）

推一个 tag 就会自动编译、签名并创建 GitHub Release：

```bash
git tag v1.3
git push origin v1.3
```

工作流在 `.github/workflows/release.yml`，用 runners 预装的 build-tools 34 + platform 34，
不额外下载 SDK；也可以在 Actions 页手动触发（填了 tag 才建 Release，否则只产出 artifact）。
versionCode 取自 `github.run_number`，versionName 取自 tag。

### 签名密钥（可选但建议）

在 Settings → Secrets and variables → Actions 里加：

| Secret | 内容 |
|---|---|
| `KEYSTORE_BASE64` | `base64 -w0 release.keystore` 的输出 |
| `KEYSTORE_PASSWORD` | keystore 密码 |
| `KEY_ALIAS` | 密钥别名 |
| `KEY_PASSWORD` | key 密码（可与 KEYSTORE_PASSWORD 相同） |

### 生成正式密钥（只在本地做一次，密钥本身不要提交）

```bash
keytool -genkeypair -keystore release.keystore -alias hardhold \
  -keyalg RSA -keysize 2048 -validity 10000 \
  -dname "CN=Hardhold" -storepass '你的密码' -keypass '你的密码'
base64 -w0 release.keystore      # 复制输出填进 KEYSTORE_BASE64
```

本地构建也用同一把密钥：

```bash
KEYSTORE=release.keystore KS_PASS='你的密码' KEY_ALIAS=hardhold \
  KEY_PASS='你的密码' ./build.sh
```

不配置密钥也能跑，工作流会用临时密钥并在 Release 说明里标注「临时签名」——
能装，但每次发版签名都不同，装过旧版的手机会冲突，需要卸载重装。

## 目录结构

```
apk/
├── app/src/main/
│   ├── AndroidManifest.xml
│   ├── assets/pose_landmarker_lite.task      # 姿态模型（Apache-2.0）
│   ├── res/                                  # 图标、应用名
│   └── java/com/pushup/counter/
│       ├── MainActivity.java                 # Camera2 + MediaPipe 调度、权限、生命周期
│       ├── PreviewView.java                  # 画面 + 骨架 + 计数叠加层
│       ├── TunePanel.java                    # 阈值微调面板
│       ├── PushupCounter.java                # 计数状态机（纯 Java，可单测）
│       ├── AngleMath.java                    # 关键点夹角
│       └── YuvConverter.java                 # YUV_420_888 → Bitmap
├── test/PushupCounterTest.java               # 12 个计数逻辑单测
├── build.sh                                  # 一键打包 + 签名
├── setup.sh                                  # 下载工具链与依赖
├── fetch-deps.py                             # 从 Maven 拉 MediaPipe 依赖
├── package.py                                # 把 dex/so 塞进 APK
├── .github/workflows/release.yml             # 打 tag 自动构建并发 Release
├── LICENSE                                   # Apache-2.0
└── NOTICE                                    # 第三方组件署名
```

`tools/`（SDK）、`libs/`（依赖）、`build/`、`*.apk`、`*.keystore` 都不进仓库，见 `.gitignore`。

## 计数参数

在 `PushupCounter.java`：

- `DEFAULT_UP_ANGLE = 158°`：大于等于算"撑起"
- `DEFAULT_DOWN_ANGLE = 95°`：小于等于算"下落"
- 阈值之间是滞回区，防抖动误计数；状态切换需连续 2 帧确认且间隔 ≥100ms
- 无姿态 1.5 秒自动清空当前动作状态

App 内改阈值无需重编译（见「微调阈值」），改动会存到 SharedPreferences。

## 许可证

本项目以 **Apache License 2.0** 发布，见 [LICENSE](LICENSE)。

选择它的原因：依赖（MediaPipe、Guava、protobuf 等）本来就是 Apache-2.0 / BSD，
Apache-2.0 含专利授权条款，对视觉类项目更稳妥。

## 第三方组件

| 组件 | 许可证 |
|---|---|
| [MediaPipe Tasks Vision](https://github.com/google-ai-edge/mediapipe) 0.10.14 | Apache-2.0 |
| Pose Landmarker Lite 模型 | Apache-2.0 |
| Guava、Flogger、AutoValue、Firebase Encoders、DataTransport、AndroidX Annotation | Apache-2.0 |
| javax.inject (JSR-330) | Apache-2.0 |
| Protocol Buffers (javalite) | BSD-3-Clause |

完整署名见 [NOTICE](NOTICE)。重新分发 APK 时需要保留 LICENSE 与 NOTICE。

## 隐私

- 摄像头画面只在本机内存中解码、逐帧推理，不写盘、不上传。
- App 不申请网络权限，也没有任何统计/广告 SDK。
- 唯一写入本机的是微调后的阈值（SharedPreferences）。

## 已知限制

- 必须双肘可见；只露半身或侧身遮挡时角度不可靠。
- 距离太近、逆光、宽大衣服会影响关键点精度。
- 手机放地上仰拍时人容易出画，建议侧面平放。
- 目前只在单台设备上验证过画面方向与帧率，不同机型可能需要在 `MainActivity` 里调整旋转角。
