import unittest

from app.services.ai_service import AIService


class AIServiceTests(unittest.TestCase):
    def test_ai_service_can_initialize_without_groq_runtime(self):
        service = AIService()
        self.assertIsNotNone(service)


if __name__ == "__main__":
    unittest.main()
