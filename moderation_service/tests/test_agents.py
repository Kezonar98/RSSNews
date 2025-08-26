import unittest
from agents import moderate_text

class TestAgents(unittest.TestCase):
    def test_toxic_text(self):
        result = moderate_text("You are stupid!")
        self.assertIn("toxicity", result)

    def test_safe_text(self):
        result = moderate_text("Hello world")
        self.assertTrue(result["safety"]["safe"])

if __name__ == "__main__":
    unittest.main()
