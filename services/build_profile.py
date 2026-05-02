from schema import TopicPerformance, ProfileResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from models import Profile, Evaluation, TopicScoreDB, Response, Quiz, Plan

def update_profile(user_id: int, course_id: int, db: Session):
    profile = db.query(Profile).filter_by(user_id=user_id, course_id=course_id).first()

    if not profile:
        raise ValueError(f"Profile not found for user_id={user_id}")

    # 🔹 Get latest evaluation
    latest_eval = (
    db.query(Evaluation)
    .join(Evaluation.response)
    .join(Response.quiz)
    .join(Quiz.plan)
    .filter(
        Evaluation.user_id == user_id,
        Plan.course_id == course_id
    )
    .order_by(Evaluation.generated_at.desc())
    .first()
)

    if not latest_eval:
        return profile  # nothing to update

    new_score = latest_eval.overall_score

    # 🔹 Incremental update
    total = profile.total_quiz + 1

    new_avg = (
        (profile.overall_avg * profile.total_quiz) + new_score
    ) / total

    profile.total_quiz = total
    profile.overall_avg = new_avg

    db.commit()
    db.refresh(profile)

    return profile

def generate_profile(user_id: int, course_id:int, db: Session):
    evaluations = (
    db.query(Evaluation)
    .join(Evaluation.response)
    .join(Response.quiz)
    .join(Quiz.plan)
    .filter(
        Response.user_id == user_id,
        Plan.course_id == course_id
    )
    .options(joinedload(Evaluation.topic_scores))
    .all()
)

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
            if ts.total > 0:
                normalized_score = ts.score / ts.total
            else:
                normalized_score = 0

            topic_map[ts.topic]["total_score"] += normalized_score
            topic_map[ts.topic]["count"] += 1
            topic_map[ts.topic]["understanding"] += float(ts.understanding_score)

    topic_performance = []

    for topic, data in topic_map.items():
        if data["count"] == 0:
            continue
        topic_performance.append({
            "topic": topic,
            "average_score": data["total_score"] / data["count"],
            "quizzes_attempted": data["count"],
            "understanding_score": data["understanding"] / data["count"]
        })

    topic_performance = sorted(
        topic_performance,
        key=lambda x: x["average_score"]
    )

    return topic_performance