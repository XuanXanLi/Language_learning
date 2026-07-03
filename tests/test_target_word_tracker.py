"""目标词追踪器测试。"""

from line_c.engine.target_word_tracker import TargetWordTracker


class TestTargetWordTracker:

    def test_ingest_uses_only_lead_sentence(self):
        tracker = TargetWordTracker()
        targets = tracker.ingest_assistant_response(
            "You can say persist here. Later we can also explore and discover new things."
        )
        assert "persist" in targets
        assert "explore" not in targets

    def test_reset_clears_targets(self):
        tracker = TargetWordTracker()
        tracker.ingest_assistant_response("You can say persist.")
        assert tracker.has_active_targets()
        tracker.reset()
        assert tracker.get_active_targets() == []
        assert tracker.get_all_targets() == []

    def test_focus_can_be_updated(self):
        tracker = TargetWordTracker()
        tracker.set_focus(["坚持", "学习"])
        assert tracker._current_focus == ["坚持", "学习"]
