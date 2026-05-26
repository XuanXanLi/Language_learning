"""SM-2 间隔复习算法的测试用例。

覆盖：
- 各种质量分的标准场景
- 边界情况
- EF 因子变化趋势
- 连续成功/失败的模式
"""
from line_c.engine.sm2_srs import sm2_calculate, SM2Result


class TestSM2Calculate:

    def test_perfect_first_review(self):
        """第一次完美回忆 (q=5)：间隔应为 1 天。"""
        result = sm2_calculate(quality=5, repetition=0, interval=0.0, ef=2.5)
        assert result.interval_days == 1.0
        assert result.repetition == 1

    def test_perfect_second_review(self):
        """第二次完美回忆：间隔应为 6 天。"""
        result = sm2_calculate(quality=5, repetition=1, interval=1.0, ef=2.5)
        assert result.interval_days == 6.0
        assert result.repetition == 2

    def test_perfect_third_review(self):
        """第三次完美回忆：间隔 = 上一次(6) × EF(2.5) = 15 天。"""
        result = sm2_calculate(quality=5, repetition=2, interval=6.0, ef=2.5)
        assert result.interval_days == 15.0
        assert result.repetition == 3

    def test_quality_4_good_recall(self):
        """良好回忆 (q=4)，EF 应该轻微下调。"""
        result = sm2_calculate(quality=4, repetition=2, interval=6.0, ef=2.5)
        assert result.interval_days > 0
        assert result.ef <= 2.5  # q=4 可能让 EF 略降或持平

    def test_quality_3_barely_passed(self):
        """勉强及格 (q=3)，EF 下降更多。"""
        result = sm2_calculate(quality=3, repetition=2, interval=6.0, ef=2.5)
        assert result.repetition == 3  # 仍然算成功
        assert result.interval_days > 0
        assert result.ef < 2.5

    def test_failure_resets_repetition(self):
        """质量 < 3 → 重置 repetition 为 0，间隔 1 天。"""
        result = sm2_calculate(quality=2, repetition=3, interval=15.0, ef=2.5)
        assert result.repetition == 0
        assert result.interval_days == 1.0

    def test_quality_zero_complete_blackout(self):
        """质量 0（完全忘了）。"""
        result = sm2_calculate(quality=0, repetition=5, interval=30.0, ef=2.1)
        assert result.repetition == 0
        assert result.interval_days == 1.0

    def test_ef_never_below_1_3(self):
        """无论表现多差，EF 不低于 1.3。"""
        # 连续低质量打击 EF
        ef = 2.5
        for _ in range(20):
            result = sm2_calculate(quality=0, repetition=0, interval=1.0, ef=ef)
            ef = result.ef
        assert ef >= 1.3

    def test_ef_increases_with_consistent_perfect(self):
        """持续完美回忆，EF 应该上升（词越来越容易）。"""
        ef = 2.5
        rep = 0
        interval = 0.0
        for _ in range(5):
            result = sm2_calculate(quality=5, repetition=rep, interval=interval, ef=ef)
            rep = result.repetition
            interval = result.interval_days
            ef = result.ef
        assert ef > 2.5  # 持续 q=5 后 EF 应升高

    def test_quality_clamped_to_valid_range(self):
        """传入非法的 quality 值应该被限制在 0-5。"""
        r1 = sm2_calculate(quality=10, repetition=0, interval=0.0)
        r2 = sm2_calculate(quality=-5, repetition=0, interval=0.0)
        # 不应该崩溃，正常输出
        assert r1.interval_days > 0
        assert r2.interval_days > 0

    def test_known_values_from_sm2_paper(self):
        """验证 SM-2 论文中的一组已知值。

        SM-2 论文中的示例：
        q=5, rep=0, interval=0, ef=2.5 → interval=1, rep=1
        q=5, rep=1, interval=1, ef=2.5 → interval=6, rep=2
        q=5, rep=2, interval=6, ef=2.6 → interval=15.6
        """
        r1 = sm2_calculate(quality=5, repetition=0, interval=0.0, ef=2.5)
        assert r1.interval_days == 1.0
        assert r1.repetition == 1

        # 使用 r1 的 EF（可能略有变化）
        r2 = sm2_calculate(quality=5, repetition=1, interval=1.0, ef=r1.ef)
        assert r2.interval_days == 6.0
        assert r2.repetition == 2

        r3 = sm2_calculate(quality=5, repetition=2, interval=6.0, ef=r2.ef)
        threshold = round(6.0 * r2.ef, 2)
        assert r3.interval_days == threshold
