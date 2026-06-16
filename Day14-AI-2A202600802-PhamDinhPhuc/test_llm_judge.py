import os
import json
import re
from dotenv import load_dotenv
from openai import OpenAI
from template import LLMJudge

# Load env variables from .env file
load_dotenv()

# Initialize OpenAI client
api_key = os.getenv("OPENAI_API_KEY")
if not api_key or api_key == "your_api_key_here" or api_key.strip() == "":
    print("Please paste your OpenAI API Key into the .env file first!")
    exit(1)

client = OpenAI(api_key=api_key)

def gpt_4o_mini_judge_fn(prompt: str) -> str:
    """Callback function that sends the prompt to gpt-4o-mini and returns the response string."""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a precise AI Judge. You must output evaluations strictly in JSON format as requested."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            response_format={"type": "json_object"} # Force JSON output from gpt-4o-mini
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return "{}"

def main():
    print("Initializing LLM Judge with gpt-4o-mini...")
    judge = LLMJudge(judge_llm_fn=gpt_4o_mini_judge_fn)

    question = "How does a student qualify for the Dean's List at VinUniversity?"
    actual_answer = "To qualify for the Dean's List, you must achieve a semester GPA of 3.60 or higher."
    
    rubric = {
        "correctness": "Is the information factually correct?",
        "completeness": "Does the answer cover both the GPA requirement (>=3.6) and the minimum credit load requirement (at least 15 credits without failing)?",
    }

    print("\n--- Running score_response ---")
    print(f"Question: {question}")
    print(f"Actual Answer: {actual_answer}")
    print("Rubric:")
    for k, v in rubric.items():
        print(f"  - {k}: {v}")

    result = judge.score_response(question, actual_answer, rubric)
    print("\n=== Evaluation Results ===")
    print(json.dumps(result, indent=2))

    # Demonstrate detect_bias with a batch of scores
    print("\n--- Running detect_bias ---")
    scores_batch = [
        result,
        {
            "scores": {"correctness": 0.9, "completeness": 0.8},
            "reasoning": "Good answer."
        },
        {
            "scores": {"correctness": 0.85, "completeness": 0.85},
            "reasoning": "Very consistent."
        }
    ]
    bias = judge.detect_bias(scores_batch)
    print("Detected Bias:")
    print(json.dumps(bias, indent=2))

if __name__ == "__main__":
    main()
