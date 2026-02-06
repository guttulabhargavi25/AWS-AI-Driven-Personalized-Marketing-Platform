# ai_engine.py

def calculate_engagement_score(clicks, opens):
    """
    Simple AI logic (rule-based ML style)
    """
    score = (clicks * 10) + (opens * 5)

    if score >= 50:
        return "High", score
    elif score >= 25:
        return "Medium", score
    else:
        return "Low", score


def recommend_channel(engagement_level):
    """
    AI-based recommendation
    """
    if engagement_level == "High":
        return "Email"
    elif engagement_level == "Medium":
        return "SMS"
    else:
        return "Social"
