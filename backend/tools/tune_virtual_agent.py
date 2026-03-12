"""Simple tuning helper for `virtual_agent.detect_intent_from_text`.

Run this script to print intent detection results for sample inputs and adjust
thresholds/weights in `virtual_agent.py`.
"""
from app.services.virtual_agent import detect_intent_from_text

SAMPLES = [
    "panic attack ngayon", 
    "nakakapagod na ko", 
    "di na ako makatulog", 
    "wala akong gana sa buhay", 
    "gusto ko na mamatay",
    "i'm so stressed and overwhelmed",
    "sobrang anxious ako",
    "pagod na ko sobra",
    "nakakapgod talaga",
]


def run_samples():
    for s in SAMPLES:
        intent, conf = detect_intent_from_text(s)
        print(f"INPUT: {s}\n -> intent={intent}, confidence={conf}\n")


if __name__ == '__main__':
    run_samples()
