"""Unit tests for the guardrails. Run: python -m unittest discover tests"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from copilot import OpsCopilot  # noqa: E402
from copilot.retriever import tokenize  # noqa: E402


class GuardrailTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bot = OpsCopilot(use_llm=False)

    def test_hostnames_stay_whole_and_split(self):
        tokens = tokenize("patch pg-prod-01")
        self.assertIn("pg-prod-01", tokens)
        self.assertIn("prod", tokens)

    def test_every_answer_has_a_citation(self):
        for q in ["What breaks if pg-prod-01 goes down?", "How do I patch the kafka brokers?"]:
            a = self.bot.ask(q)
            self.assertFalse(a.refused)
            self.assertIn("[source:", a.text)

    def test_unknown_system_is_refused_not_guessed(self):
        a = self.bot.ask("What breaks if db-legacy-09 goes down?")
        self.assertTrue(a.refused)
        self.assertEqual(a.impacted, [])

    def test_off_topic_question_is_refused(self):
        self.assertTrue(self.bot.ask("What is the vacation policy?").refused)

    def test_ticket_is_always_a_draft(self):
        a = self.bot.ask("Draft a change ticket to patch pg-uat-01")
        self.assertIn("DRAFT - requires human approval", a.text)
        self.assertNotIn("APPROVED", a.text.upper().replace("REQUIRES HUMAN APPROVAL", ""))

    def test_blackout_window_is_flagged(self):
        a = self.bot.ask("Draft a change ticket to patch pg-prod-01 at 02:00")
        self.assertEqual(a.risk, "High")
        self.assertIn("CONFLICT", a.text)

    def test_daytime_window_has_no_blackout(self):
        a = self.bot.ask("Draft a change ticket to patch pg-prod-01 at 14:00")
        self.assertIn("Blackout check: OK", a.text)

    def test_transitive_impact(self):
        # kafka -> fraud-scoring -> payments-api -> online-banking
        self.assertIn("online-banking", self.bot.ask("What breaks if kafka-prod-01 goes down?").impacted)


if __name__ == "__main__":
    unittest.main()
