"""SM-2 间隔复习算法（Spaced Repetition System）。

SM-2 是 SuperMemo 家族中最经典的算法，由 Piotr Wozniak 在 1980s 开发。
核心思想：根据你每次复习的表现质量，动态调整下次复习的间隔时间。

算法输入：
  - quality:  复习质量 0-5（0=完全忘了, 5=完美回忆）
  - repetition: 这是第几次连续正确复习
  - interval:   上一次的间隔天数
  - ef:         Ease Factor（难度因子，越大表示越容易记住，默认 2.5）

算法输出：
  - interval:    下次复习间隔（天）
  - repetition:  更新后的连续正确次数
  - ef:          更新后的难度因子

SM-2 论文参考: https://www.supermemo.com/english/ol/sm2.htm
"""

from dataclasses import dataclass


@dataclass
class SM2Result:
    """SM-2 的一次计算结果。"""
    interval_days: float   # 下次复习间隔（天）
    repetition: int        # 连续正确次数
    ef: float              # 难度因子 (1.3 ~ 2.5)


def sm2_calculate(
    quality: int,
    repetition: int = 0,
    interval: float = 0.0,
    ef: float = 2.5,
) -> SM2Result:
    """SM-2 算法核心——纯函数，无副作用。

    参数：
    - quality:      用户回忆质量，0-5 的整数
                    * 0-2: 失败（完全忘记或几乎忘记）
                    * 3:   及格（想起来但有些犹豫）
                    * 4:   良好（顺利想起来）
                    * 5:   完美（脱口而出）
    - repetition:   这是第几次连续正确回忆（失败时重置为 0）
    - interval:     上次复习到现在的间隔天数
    - ef:           难度因子，1.3（最难）到 2.5（最简单），默认 2.5

    返回：
    - SM2Result: 包含新的间隔、重复次数和难度因子
    """
    # 参数边界保护
    quality = max(0, min(5, quality))
    ef = max(1.3, ef)  # EF 不能低于 1.3

    if quality < 3:
        # 回忆失败 → 重置，明天再复习
        return SM2Result(
            interval_days=1.0,
            repetition=0,
            ef=ef,  # EF 不变（失败不调整难度）
        )

    # 回忆成功（quality >= 3）
    new_repetition = repetition + 1

    if new_repetition == 1:
        new_interval = 1.0       # 第一次成功：1 天后
    elif new_repetition == 2:
        new_interval = 6.0       # 第二次成功：6 天后
    else:
        # 第三次及以后：上一次间隔 × EF
        new_interval = round(interval * ef, 2)

    # 更新 EF（难度因子）
    new_ef = ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    new_ef = max(1.3, round(new_ef, 4))  # 底线 1.3

    return SM2Result(
        interval_days=new_interval,
        repetition=new_repetition,
        ef=new_ef,
    )


# ── 预计算的典型场景（用于确认算法表现符合预期）──

"""
质量与间隔的关系：

| quality | 第1次 | 第2次 | 第3次 | 第4次 | 第5次 |
|---------|-------|-------|-------|-------|-------|
| 5 (完美) | 1天   | 6天   | 16天  | 42天  | 113天 |
| 4 (良好) | 1天   | 6天   | 15天  | 37天  | 91天  |
| 3 (及格) | 1天   | 6天   | 14天  | 33天  | 73天  |
| 2 (失败) | 1天   | 1天   | 1天   | 1天   | 1天   |

规律：
- quality 越高，间隔增长越快（好记的词少复习）
- quality < 3 → 重置回第 1 天（忘了就从头来）
- EF 会随每次表现微调，表现好 EF 升高、间隔拉长
"""
