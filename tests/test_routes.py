import unittest

from app import create_app


class RouteTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()

    def test_test_clunk_alias_returns_success(self):
        response = self.client.get("/test-clunk")
        self.assertNotEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
