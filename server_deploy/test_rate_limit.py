"""Tests for the demo rate limiter.

Stdlib only (no pytest needed):

    cd server_deploy && python -m unittest test_rate_limit -v
"""

import unittest

from rate_limit import RateLimiter, Rule, describe, format_duration


class FakeClock:
    """Controllable stand-in for time.monotonic()."""

    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def limiter(rules, clock):
    return RateLimiter([Rule(*rule) for rule in rules], clock=clock)


class PerIpLimitTests(unittest.TestCase):
    def test_allows_up_to_the_limit_then_rejects(self):
        clock = FakeClock()
        rl = limiter([(3, 60, "ip", "minute")], clock)

        for _ in range(3):
            self.assertTrue(rl.check("1.1.1.1").allowed)

        decision = rl.check("1.1.1.1")
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.rejection.rule.label, "minute")
        self.assertEqual(decision.rejection.rule.scope, "ip")

    def test_window_slides_so_quota_comes_back(self):
        clock = FakeClock()
        rl = limiter([(3, 60, "ip", "minute")], clock)

        for _ in range(3):
            rl.check("1.1.1.1")
        self.assertFalse(rl.check("1.1.1.1").allowed)

        clock.advance(60)
        self.assertTrue(rl.check("1.1.1.1").allowed)

    def test_visitors_are_independent(self):
        clock = FakeClock()
        rl = limiter([(1, 1, "ip", "second")], clock)

        self.assertTrue(rl.check("1.1.1.1").allowed)
        self.assertFalse(rl.check("1.1.1.1").allowed)
        self.assertTrue(rl.check("2.2.2.2").allowed)

    def test_retry_after_counts_down_with_the_oldest_hit(self):
        clock = FakeClock()
        rl = limiter([(1, 60, "ip", "minute")], clock)

        rl.check("1.1.1.1")
        clock.advance(20)
        decision = rl.check("1.1.1.1")
        self.assertEqual(decision.rejection.retry_after_seconds, 40)

    def test_remaining_is_reported_per_window(self):
        clock = FakeClock()
        rl = limiter([(3, 60, "ip", "minute"), (10, 86_400, "ip", "day")], clock)

        decision = rl.check("1.1.1.1")
        self.assertEqual(decision.remaining, {"minute": 2, "day": 9})


class GlobalLimitTests(unittest.TestCase):
    def test_global_rule_is_shared_across_visitors(self):
        clock = FakeClock()
        rl = limiter([(2, 60, "global", "minute")], clock)

        self.assertTrue(rl.check("1.1.1.1").allowed)
        self.assertTrue(rl.check("2.2.2.2").allowed)

        decision = rl.check("3.3.3.3")
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.rejection.rule.scope, "global")

    def test_rejected_request_does_not_consume_other_windows(self):
        """All-or-nothing: a request blocked by one rule must not burn the rest."""
        clock = FakeClock()
        rl = limiter([(1, 1, "ip", "second"), (10, 86_400, "ip", "day")], clock)

        rl.check("1.1.1.1")  # 1 second-slot + 1 day-slot used
        self.assertFalse(rl.check("1.1.1.1").allowed)  # blocked on "second"
        self.assertFalse(rl.check("1.1.1.1").allowed)

        clock.advance(1)
        # only the one accepted request should have counted against the daily quota
        self.assertEqual(rl.peek_remaining("1.1.1.1")["day"], 9)

    def test_production_ruleset_end_to_end(self):
        """The real demo config: 1/s, 3/min, 10/day per IP; 3/s, 5/min, 100/day global."""
        import config

        clock = FakeClock()
        rl = limiter(config.DEMO_RATE_LIMITS, clock)

        # one visitor: 3 questions a minute, spaced a second apart
        for _ in range(3):
            self.assertTrue(rl.check("1.1.1.1").allowed)
            clock.advance(1)
        self.assertFalse(rl.check("1.1.1.1").allowed)  # per-IP minute limit

        # a second visitor still gets through (limits are per visitor)...
        self.assertTrue(rl.check("2.2.2.2").allowed)
        clock.advance(1)
        self.assertTrue(rl.check("2.2.2.2").allowed)

        # ...until the shared 5/minute ceiling is reached
        clock.advance(1)
        decision = rl.check("3.3.3.3")
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.rejection.rule.scope, "global")


class MessageTests(unittest.TestCase):
    def test_every_rule_produces_a_distinct_code_and_message(self):
        clock = FakeClock()
        seen = set()
        for limit, window, scope, label in [
            (1, 1, "ip", "second"),
            (3, 60, "ip", "minute"),
            (10, 86_400, "ip", "day"),
            (3, 1, "global", "second"),
            (5, 60, "global", "minute"),
            (100, 86_400, "global", "day"),
        ]:
            rl = limiter([(limit, window, scope, label)], clock)
            for _ in range(limit):
                rl.check("1.1.1.1")
            code, message = describe(rl.check("1.1.1.1").rejection)
            self.assertNotIn(code, seen)
            seen.add(code)
            self.assertTrue(message and message[0].isupper())

    def test_duration_formatting(self):
        self.assertEqual(format_duration(1), "1 second")
        self.assertEqual(format_duration(40), "40 seconds")
        self.assertEqual(format_duration(90), "2 minutes")
        self.assertEqual(format_duration(7320), "2h 02m")


if __name__ == "__main__":
    unittest.main()
