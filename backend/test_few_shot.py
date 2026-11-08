"""Manual smoke test for retrieved few-shot examples and GAIDA replies."""

from app.services import gpt_agent
from few_shot import get_examples


SAMPLE_MESSAGES = [
    "I'm nervous about my exams and keep thinking I will fail.",
    "I feel alone even when I'm around my friends.",
    "I can't stop worrying about what will happen after graduation.",
]


def main() -> None:
    for user_message in SAMPLE_MESSAGES:
        print(f"\nStudent: {user_message}")
        examples = get_examples(user_message, k=4)
        print("Retrieved examples:")
        for example in examples:
            print(f"  {example['role']}: {example['content']}")

        result = gpt_agent.generate_response_with_gpt(user_message)
        print("GAIDA:", result.get("response") or "[No API reply returned]")


if __name__ == "__main__":
    main()
