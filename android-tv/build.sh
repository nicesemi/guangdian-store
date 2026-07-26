#!/bin/bash
# deepedu TV APK 构建脚本
# 前置条件：安装 Android SDK 并设置 ANDROID_HOME 环境变量

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
APK_OUT="$PROJECT_DIR/app/build/outputs/apk/release/app-release-unsigned.apk"

# 检查 ANDROID_HOME
if [ -z "$ANDROID_HOME" ]; then
    echo "请设置 ANDROID_HOME 环境变量"
    echo "例如: export ANDROID_HOME=~/Library/Android/sdk"
    exit 1
fi

# 下载 gradle wrapper（如果不存在）
if [ ! -f "$PROJECT_DIR/gradlew" ]; then
    echo "下载 Gradle Wrapper..."
    GRADLE_VERSION="8.5"
    GRADLE_ZIP="$PROJECT_DIR/gradle/wrapper/gradle-wrapper.zip"
    curl -sL "https://services.gradle.org/distributions/gradle-${GRADLE_VERSION}-bin.zip" -o "$GRADLE_ZIP"
    # 创建简易 gradlew
    cat > "$PROJECT_DIR/gradlew" << 'GRADLEW'
#!/bin/sh
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec java -cp "$PROJECT_DIR/gradle/wrapper/gradle-wrapper.jar" org.gradle.wrapper.GradleWrapperMain "$@"
GRADLEW
    chmod +x "$PROJECT_DIR/gradlew"
fi

echo "构建 deepedu TV APK..."
cd "$PROJECT_DIR"

# 构建 release APK
./gradlew assembleRelease 2>&1 || {
    echo ""
    echo "=== Gradle 构建失败，尝试使用 Android Studio ==="
    echo "请用 Android Studio 打开本项目目录: $PROJECT_DIR"
    exit 1
}

if [ -f "$APK_OUT" ]; then
    echo ""
    echo "构建成功: $APK_OUT"
    echo "安装到 TV: adb install $APK_OUT"
else
    echo "APK 未生成，请检查错误日志"
    exit 1
fi
