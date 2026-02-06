def generate_response(intent_data: dict):
    intent = intent_data.get("intent") if isinstance(intent_data, dict) else None

    if intent == "anxiety":
        return "I understand that you're feeling anxious. Let's take this one step at a time."

    if intent == "sadness":
        return "I'm here to listen. Would you like to talk more about what's making you feel this way?"

    if intent == "stress":
        return "It sounds like you're under a lot of pressure. Taking short breaks can sometimes help."

    return "I'm here with you. Please tell me more."
