"""End-to-end tests for /api/ask rate limiting, with the model stubbed out.

No Ollama and no model download needed — generation is replaced by a fake stream,
so this exercises routing, validation, limits and the 429 payload only.

    cd server_deploy && python -m unittest test_api -v
"""

import unittest

import app as app_module
from fastapi.testclient import TestClient
from rate_limit import RateLimiter, Rule


class AskEndpointTests(unittest.TestCase):
    def setUp(self):
        # deterministic, generous limits unless a test overrides them
        self._install_limits([(2, 60, "ip", "minute"), (3, 60, "global", "minute")])
        app_module.stream_answer_query = lambda question: iter(["stub answer"])
        self.client = TestClient(app_module.app)

    def _install_limits(self, rules):
        app_module.demo_limiter = RateLimiter([Rule(*rule) for rule in rules])

    def _ask(self, question="What is Vera-Finance?", ip="1.1.1.1"):
        return self.client.post(
            "/api/ask",
            json={"question": question},
            headers={"X-Forwarded-For": ip},
        )

    def test_answer_streams_back_with_quota_header(self):
        response = self._ask()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "stub answer")
        self.assertEqual(response.headers["X-Demo-Quota-Remaining-Minute"], "1")

    def test_per_visitor_limit_returns_429_with_a_message(self):
        self._ask()
        self._ask()
        response = self._ask()

        self.assertEqual(response.status_code, 429)
        error = response.json()["error"]
        self.assertEqual(error["scope"], "ip")
        self.assertEqual(error["window"], "minute")
        self.assertEqual(error["limit"], 2)
        self.assertGreaterEqual(error["retry_after"], 1)
        self.assertIn("2 questions per minute", error["message"])
        self.assertEqual(response.headers["Retry-After"], str(error["retry_after"]))

    def test_forwarded_for_separates_visitors(self):
        self._ask(ip="1.1.1.1")
        self._ask(ip="1.1.1.1")
        self.assertEqual(self._ask(ip="1.1.1.1").status_code, 429)
        self.assertEqual(self._ask(ip="2.2.2.2").status_code, 200)

    def test_global_ceiling_blocks_even_fresh_visitors(self):
        self._install_limits([(5, 60, "ip", "minute"), (2, 60, "global", "minute")])
        self.assertEqual(self._ask(ip="1.1.1.1").status_code, 200)
        self.assertEqual(self._ask(ip="2.2.2.2").status_code, 200)

        response = self._ask(ip="3.3.3.3")
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json()["error"]["scope"], "global")
        self.assertIn("busy", response.json()["error"]["message"])

    def test_empty_and_oversized_questions_are_rejected_before_the_model(self):
        self.assertEqual(self._ask(question="").status_code, 422)
        self.assertEqual(self._ask(question="x" * 501).status_code, 422)

    def test_limits_endpoint_reports_config_and_remaining(self):
        payload = self.client.get("/api/limits", headers={"X-Forwarded-For": "9.9.9.9"}).json()
        self.assertEqual(payload["limits"]["ip"], {"minute": 2})
        self.assertEqual(payload["limits"]["global"], {"minute": 3})
        self.assertEqual(payload["remaining"], {"minute": 2})


if __name__ == "__main__":
    unittest.main()
