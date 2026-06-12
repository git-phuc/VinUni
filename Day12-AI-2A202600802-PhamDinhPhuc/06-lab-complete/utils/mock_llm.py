"""Mock LLM used for local and CI-safe Day 12 deployment tests."""
import random
import time


MOCK_RESPONSES = {
    "default": [
        "This is a mock AI response. In production this can call OpenAI or another LLM.",
        "The production agent is running and received your question.",
        "Mock agent response generated successfully.",
    ],
    "docker": [
        "Docker packages the app and dependencies into a reproducible container.",
    ],
    "deploy": [
        "Deployment publishes the service to a server or cloud platform for real users.",
    ],
    "health": [
        "Health checks let the platform restart or stop routing to unhealthy instances.",
    ],
}


def ask(question: str, delay: float = 0.05) -> str:
    time.sleep(delay + random.uniform(0, 0.02))
    question_lower = question.lower()
    for keyword, responses in MOCK_RESPONSES.items():
        if keyword in question_lower:
            return random.choice(responses)
    return random.choice(MOCK_RESPONSES["default"])
