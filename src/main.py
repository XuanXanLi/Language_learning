#!/usr/bin/env python3
"""端侧AI语言学习机 — Line C v2 入口。

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
from line_c.engine.user_repository import UserRepository
from line_c.engine.chat_session_repository import ChatSessionRepository
from line_c.engine.user_vocabulary_repository import UserVocabularyRepository
from line_c.engine.topic_generator import TopicGenerator
from line_c.engine.rss_feed_fetcher import RSSFeedFetcher
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
    parser = argparse.ArgumentParser(description="端侧AI语言学习机 - Line C v2")
    parser.add_argument(
        "--llm", choices=["mock", "cloud"], default="mock",
        help="LLM 后端选择 (默认: mock)"
    )
    args = parser.parse_args()

    # ── 初始化数据库 ──
    db_path = DATABASE_PATH
    vocab_repo = VocabularyRepository(db_path)
    user_repo = UserRepository(db_path)
    chat_session_repo = ChatSessionRepository(db_path)
    user_vocab_repo = UserVocabularyRepository(db_path)

    word_count = vocab_repo.word_count()
    print(f"数据库已连接: {db_path} ({word_count} 词)")
    print(f"角色数: {user_repo.count()}")

    if word_count == 0:
        print("提示：词库为空，请先运行 scripts/import_vocabulary.py 导入词汇数据")
        # 不退出，允许创建角色和浏览界面

    # ── 创建 LLM ──
    llm = create_llm(args.llm)

    # ── 创建 TTS ──
    tts = MockTTS(verbose=(args.llm == "mock"))

    # ── 创建 RSS 抓取器 + 话题生成器 ──
    rss_fetcher = RSSFeedFetcher()
    # RSS 优先，LLM 为备选
    topic_gen = TopicGenerator(
        llm=llm if args.llm == "cloud" else None,
        rss_fetcher=rss_fetcher,
    )

    # ── Qt 应用 ──
    app = QApplication(sys.argv)

    # ── 主窗口 ──
    window = MainWindow(
        user_repo=user_repo,
        chat_session_repo=chat_session_repo,
        user_vocab_repo=user_vocab_repo,
        vocab_repo=vocab_repo,
        llm=llm,
        tts=tts,
    )
    # 注入话题生成器
    window.topic_feed_page.set_topic_generator(topic_gen)
    window.show()

    print("VocaLand v2 界面已启动。")
    print("  首页：选择或创建角色")
    print("  话题页：选择话题开始聊天")
    print("  聊天页：点击不认识的单词查释义")
    print("  复习页：闪卡式生词复习")
    print("关闭窗口退出。")

    exit_code = app.exec_()

    # 清理
    vocab_repo.close()
    user_repo.close()
    chat_session_repo.close()
    user_vocab_repo.close()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
