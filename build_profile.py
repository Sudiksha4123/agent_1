from schema import TopicPerformance, ProfileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from models import Profile, Evaluation, TopicScoreDB

def update_profile(user_id: int, new_score: float, db: Session):
    profile = db.query(Profile).filter_by(user_id=user_id).first()
    
    if not profile:
        raise ValueError(f"Profile not found for user_id={user_id}")

    total = profile.total_quiz + 1

    new_avg = (
        (profile.overall_avg * profile.total_quiz) + new_score
    ) / total

    profile.total_quiz = total
    profile.overall_avg = new_avg

    db.commit()
    db.refresh(profile)

    return profile

def generate_profile(user_id: int, db: Session):
    evaluations = db.query(Evaluation).filter_by(user_id=user_id).all()

    topic_map = {}
# needs to be optimized. 
    for eval in evaluations:
        for ts in eval.topic_scores:
            if ts.topic not in topic_map:
                topic_map[ts.topic] = {
                    "total_score": 0,
                    "count": 0,
                    "understanding": 0
                }
# all three are not computed properly
            topic_map[ts.topic]["total_score"] += ts.score
            topic_map[ts.topic]["count"] += 1
            topic_map[ts.topic]["understanding"] += ts.understanding_score

    topic_performance = []

    for topic, data in topic_map.items():
        topic_performance.append({
            "topic": topic,
            "average_score": data["total_score"] / data["count"],
            "quizzes_attempted": data["count"],
            "understanding_score": data["understanding"] // data["count"]
        })

    return topic_performance