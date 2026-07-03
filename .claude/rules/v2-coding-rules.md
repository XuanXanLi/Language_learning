# VocaLand v2 编码规范

> 每次修改代码前必须读此文件。违反规则就是制造 bug。

---

## 规则 1：UI 组件选择

- **显示文本 → QLabel**。QLabel 在布局中尺寸天然正确，不需要手动 setFixedSize。
- **多行可点击文本 → QTextBrowser**。比 QTextEdit 更适合只读展示（内部使用 QTextDocument，布局更好）。
- **绝不在 QTextEdit 上手动 setFixedSize + contentsChanged 回调**。这个组合在嵌套布局中不可靠。
- **点击取词**：用 QLabel 显示文字 + mousePressEvent 中 QFontMetrics 手动计算点击位置对应的单词。不需要 QTextEdit.cursorForPosition()。

## 规则 2：布局清理

- 清理布局用 `while layout.count(): item = layout.takeAt(0)` 模式，不要用 for+range。
- 必须同时处理 `item.widget()` 和 `item.layout()` 两种情况（递归清理嵌套布局）。
- 聊天区的气泡用 `addLayout(QHBoxLayout)` 包裹的，清理时必须递归进入子布局删除 widget。

## 规则 3：修改代码前

- **先确认崩溃点**：跑 `PYTHONPATH=src python3 -m pytest tests/ -q`
- **只读定位**：用 Read/Grep 确认要改的代码行的确切上下文
- **单次小改动**：每次 Edit 只改一个语义单元，改完立刻跑测试
- **修改后验证**：跑全量测试确认 168 passed

## 规则 4：UI 交互行为

- **同话题恢复**：ChatPage.start_chat() 检测 topic 是否相同 → 同话题保留消息，不同话题清空
- **气泡自适应**：用 QLabel + setWordWrap(True) + setMaximumWidth(400)，自动适应文字长短
- **取词弹窗**：点击 QLabel 气泡 → 解析点击位置 → 提取英文单词 → 弹出 WordPopup

## 规则 5：禁止事项

- ❌ 禁止在 QTextEdit 上组合使用 setFixedSize + contentsChanged 信号
- ❌ 禁止在 __init__ 中调用需要布局完成才能正确返回的方法（如 idealWidth）
- ❌ 禁止用 sleep/wait 等待布局完成
- ❌ 禁止修改旧 engine 模块的公开接口（保持 117 个旧测试通过）
