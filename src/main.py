#!/usr/bin/env python3
"""端侧AI语言学习机 — Line C 开发版入口。

启动方式：
    python src/main.py                  # 默认 MockLLM
    python src/main.py --llm mock       # 使用 Mock（开发调试）
    python src/main.py --llm cloud      # 使用云端 API（需要配置 CLOUD_API_KEY）

环境变量：
    CLOUD_API_KEY   云端 API 密钥
    CLOUD_API_URL   云端 API 地址（默认 DeepSeek）
"""

import os
import sys
import argparse
from pathlib import Path

# 确保 src/ 在 Python 搜索路径中
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from PyQt5.QtWidgets import QApplication

from line_c.config import DATABASE_PATH, CLOUD_API_URL, CLOUD_API_KEY
from line_c.engine.vocabulary_repository import VocabularyRepository
from line_c.engine.conversation_manager import ConversationManager
from line_c.llm.mock_llm import MockLLM
from line_c.llm.cloud_llm import CloudLLM
from line_c.tts.mock_tts import MockTTS
from line_c.ui.main_window import MainWindow


def create_llm(backend: str):
    """根据命令行参数创建对应的 LLM 适配器。"""
    if backend == "cloud":
        api_key = os.environ.get("CLOUD_API_KEY", CLOUD_API_KEY)
        api_url = os.environ.get("CLOUD_API_URL", CLOUD_API_URL)
        if not api_key:
            print("错误：使用 cloud 模式需要设置 CLOUD_API_KEY 环境变量")
            print("  export CLOUD_API_KEY=sk-your-key-here")
            sys.exit(1)
        print(f"使用云端 API: {api_url}")
        return CloudLLM(api_url=api_url, api_key=api_key)

    # 默认 mock
    print("使用 MockLLM（预设回复，无需联网）")
    return MockLLM()


def main():
    parser = argparse.ArgumentParser(description="端侧AI语言学习机 - Line C")
    parser.add_argument(
        "--llm", choices=["mock", "cloud"], default="mock",
        help="LLM 后端选择 (默认: mock)"
    )
    args = parser.parse_args()

    # 1. 初始化数据库
    repo = VocabularyRepository(DATABASE_PATH)
    word_count = repo.word_count()
    print(f"数据库已连接: {DATABASE_PATH} ({word_count} 词)")

    if word_count == 0:
        print("提示：词库为空，请先运行 scripts/import_vocabulary.py 导入词汇数据")
        print("  python scripts/import_vocabulary.py")
        repo.close()
        sys.exit(1)

    # 2. 创建 LLM
    llm = create_llm(args.llm)

    # 3. 创建 TTS（开发阶段用 MockTTS，真机换 PiperTTS）
    tts = MockTTS(verbose=(args.llm == "mock"))

    # 4. 创建对话管理器
    manager = ConversationManager(llm=llm, repository=repo, tts=tts)

    # 5. 启动会话（以日常聊天话题开始）
    manager.start_session(topic="daily life")

    # 6. Qt 应用
    app = QApplication(sys.argv)
    window = MainWindow(manager)
    window.show()

    print(f"话题: {manager.topic}")
    print("界面已启动。聊天中遇到的 CET 词汇会自动出现在面板中。")
    print("关闭窗口退出。")

    exit_code = app.exec_()

    # 清理
    manager.srs  # 确保析构
    repo.close()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
