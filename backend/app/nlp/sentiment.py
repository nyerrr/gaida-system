from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

analyzer = SentimentIntensityAnalyzer()

def get_sentiment(text: str):
    score = analyzer.polarity_scores(text)
    return score["compound"]
