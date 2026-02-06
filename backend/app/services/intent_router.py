from app.services.gpt_intent import analyze_with_gpt
from app.services.rule_intent import analyze_with_rules

# Default to rule-based locally to avoid requiring an API key during development.
USE_GPT = False


def analyze_intent(user_input: str):
    if USE_GPT:
        return analyze_with_gpt(user_input)

    return analyze_with_rules(user_input)
