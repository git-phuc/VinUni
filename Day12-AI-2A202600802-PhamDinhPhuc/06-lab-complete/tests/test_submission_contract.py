from pathlib import Path
import unittest


BASE = Path(__file__).resolve().parents[1]


def read(relative_path: str) -> str:
    return (BASE / relative_path).read_text(encoding="utf-8")


class SubmissionContractTests(unittest.TestCase):
    def test_required_final_project_files_are_present(self):
        required_files = [
            "app/main.py",
            "app/config.py",
            "app/auth.py",
            "app/rate_limiter.py",
            "app/cost_guard.py",
            "utils/mock_llm.py",
            "Dockerfile",
            "docker-compose.yml",
            ".env.example",
        ]

        missing = [path for path in required_files if not (BASE / path).exists()]

        self.assertEqual(missing, [])

    def test_main_uses_redis_backed_stateless_helpers(self):
        main_py = read("app/main.py")

        self.assertIn("from app.auth import verify_api_key", main_py)
        self.assertIn("from app.rate_limiter import check_rate_limit", main_py)
        self.assertIn("from app.cost_guard import check_budget", main_py)
        self.assertIn("redis", main_py.lower())
        self.assertIn("history", main_py.lower())
        self.assertNotIn("_rate_windows", main_py)
        self.assertNotIn("_daily_cost", main_py)
        self.assertNotIn("defaultdict", main_py)

    def test_compose_uses_checked_in_example_env_for_local_run(self):
        compose = read("docker-compose.yml")

        self.assertIn(".env.example", compose)
        self.assertNotIn(".env.local", compose)

    def test_middleware_uses_starlette_header_api(self):
        main_py = read("app/main.py")

        self.assertNotIn(".headers.pop(", main_py)
        self.assertIn('del response.headers["server"]', main_py)


if __name__ == "__main__":
    unittest.main()
