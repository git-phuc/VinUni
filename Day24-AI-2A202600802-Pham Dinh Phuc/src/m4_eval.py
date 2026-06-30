from __future__ import annotations

"""Module 4: RAGAS Evaluation — 4 metrics + failure analysis."""

import os, sys, json
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TEST_SET_PATH


@dataclass
class EvalResult:
    question: str
    answer: str
    contexts: list[str]
    ground_truth: str
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float


def load_test_set(path: str = TEST_SET_PATH) -> list[dict]:
    """Load test set from JSON. (Đã implement sẵn)"""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _get_llm_and_embeddings():
    """Get LLM and embeddings for RAGAS — dùng Gemini hoặc 9router nếu không có OpenAI."""
    from config import OPENAI_API_KEY, GEMINI_API_KEY, NINEROUTER_API_KEY, NINEROUTER_BASE_URL, NINEROUTER_MODEL

    # Try Gemini first
    if GEMINI_API_KEY:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
            llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                google_api_key=GEMINI_API_KEY,
                temperature=0,
            )
            embeddings = GoogleGenerativeAIEmbeddings(
                model="models/embedding-001",
                google_api_key=GEMINI_API_KEY,
            )
            print("  Using Gemini for RAGAS evaluation")
            return llm, embeddings
        except Exception as e:
            print(f"  Gemini setup failed: {e}")

    # Try 9router (OpenAI-compatible)
    if NINEROUTER_API_KEY:
        try:
            from langchain_openai import ChatOpenAI, OpenAIEmbeddings
            llm = ChatOpenAI(
                model=NINEROUTER_MODEL,
                openai_api_key=NINEROUTER_API_KEY,
                openai_api_base=NINEROUTER_BASE_URL,
                temperature=0,
            )
            # Use local embeddings for 9router since it may not support embeddings
            from langchain_community.embeddings import HuggingFaceEmbeddings
            embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            print("  Using 9router for RAGAS evaluation")
            return llm, embeddings
        except Exception as e:
            print(f"  9router setup failed: {e}")

    # Try OpenAI
    if OPENAI_API_KEY:
        try:
            from langchain_openai import ChatOpenAI, OpenAIEmbeddings
            llm = ChatOpenAI(model="gpt-4o-mini", openai_api_key=OPENAI_API_KEY, temperature=0)
            embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
            print("  Using OpenAI for RAGAS evaluation")
            return llm, embeddings
        except Exception as e:
            print(f"  OpenAI setup failed: {e}")

    return None, None


def evaluate_ragas(questions: list[str], answers: list[str],
                   contexts: list[list[str]], ground_truths: list[str]) -> dict:
    """Run RAGAS evaluation."""
    zeros = {"faithfulness": 0.0, "answer_relevancy": 0.0,
             "context_precision": 0.0, "context_recall": 0.0, "per_question": []}
    try:
        from ragas import evaluate
        from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
        from datasets import Dataset

        # ragas 0.4.x uses new column names: user_input, response, retrieved_contexts, reference
        dataset = Dataset.from_dict({
            "user_input": questions,
            "response": answers,
            "retrieved_contexts": contexts,
            "reference": ground_truths,
        })

        llm, embeddings = _get_llm_and_embeddings()

        col_map = {
            "user_input": "user_input",
            "response": "response",
            "retrieved_contexts": "retrieved_contexts",
            "reference": "reference",
        }

        if llm is not None:
            result = evaluate(
                dataset,
                metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
                llm=llm,
                embeddings=embeddings,
            )
        else:
            print("  ⚠️  No LLM available — running RAGAS with default (may fail)")
            result = evaluate(
                dataset,
                metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
            )

        # ragas 0.4.x: to_pandas() returns EvaluationResult as DataFrame
        try:
            df = result.to_pandas()
        except AttributeError:
            import pandas as pd
            df = pd.DataFrame(result.scores)

        # ragas 0.4.x uses user_input/response/retrieved_contexts/reference; fall back gracefully
        per_question = [
            EvalResult(
                question=str(row.get("user_input", row.get("question", ""))),
                answer=str(row.get("response", row.get("answer", ""))),
                contexts=list(row.get("retrieved_contexts", row.get("contexts", []))),
                ground_truth=str(row.get("reference", row.get("ground_truth", ""))),
                faithfulness=float(row.get("faithfulness", 0.0) or 0.0),
                answer_relevancy=float(row.get("answer_relevancy", 0.0) or 0.0),
                context_precision=float(row.get("context_precision", 0.0) or 0.0),
                context_recall=float(row.get("context_recall", 0.0) or 0.0),
            )
            for _, row in df.iterrows()
        ]

        return {
            "faithfulness": float(df["faithfulness"].mean() if "faithfulness" in df else 0.0),
            "answer_relevancy": float(df["answer_relevancy"].mean() if "answer_relevancy" in df else 0.0),
            "context_precision": float(df["context_precision"].mean() if "context_precision" in df else 0.0),
            "context_recall": float(df["context_recall"].mean() if "context_recall" in df else 0.0),
            "per_question": per_question,
        }

    except Exception as e:
        print(f"  ⚠️  RAGAS evaluation failed: {e}")
        return zeros


def failure_analysis(eval_results: list[EvalResult], bottom_n: int = 10) -> list[dict]:
    """Analyze bottom-N worst questions using Diagnostic Tree."""
    if not eval_results:
        return []

    diagnostic_tree = {
        "faithfulness": ("LLM hallucinating", "Tighten prompt, lower temperature, add source attribution"),
        "context_recall": ("Missing relevant chunks", "Improve chunking or add BM25, lower similarity threshold"),
        "context_precision": ("Too many irrelevant chunks", "Add reranking or metadata filter, stricter top-k"),
        "answer_relevancy": ("Answer doesn't match question", "Improve prompt template, check query reformulation"),
    }

    scored = []
    for r in eval_results:
        metrics = {
            "faithfulness": r.faithfulness,
            "context_recall": r.context_recall,
            "context_precision": r.context_precision,
            "answer_relevancy": r.answer_relevancy,
        }
        avg = sum(metrics.values()) / len(metrics)
        worst_metric = min(metrics, key=lambda k: metrics[k])
        scored.append({
            "question": r.question,
            "avg_score": avg,
            "worst_metric": worst_metric,
            "score": metrics[worst_metric],
            "all_scores": metrics,
            "diagnosis": diagnostic_tree[worst_metric][0],
            "suggested_fix": diagnostic_tree[worst_metric][1],
        })

    scored.sort(key=lambda x: x["avg_score"])
    return scored[:bottom_n]


def save_report(results: dict, failures: list[dict], path: str = "ragas_report.json"):
    """Save evaluation report to JSON. (Đã implement sẵn)"""
    report = {
        "aggregate": {k: v for k, v in results.items() if k != "per_question"},
        "num_questions": len(results.get("per_question", [])),
        "failures": failures,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"Report saved to {path}")


if __name__ == "__main__":
    test_set = load_test_set()
    print(f"Loaded {len(test_set)} test questions")
    print("Run pipeline.py first to generate answers, then call evaluate_ragas().")
