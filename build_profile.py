from schema import TopicPerformance, ProfileResponse

profiles = {}

def update_profile(user_id: str, evaluation):
    if user_id not in profiles:
     profiles[user_id] = {
        "total_quizzes": 0,
        "scores": [],
        "topics": {}
    }
    
    profile = profiles[user_id]

    percentage = (evaluation.overall_score / evaluation.overall_total) * 100

    profile["total_quizzes"] += 1
    profile["scores"].append(percentage)

    for topic_data in evaluation.topic_scores:

        topic = topic_data.topic
        score = topic_data.score
        total = topic_data.total
        understanding = topic_data.topic_understanding_score

        topic_percentage = (score / total) * 100

        if topic not in profile["topics"]:
            profile["topics"][topic] = {
                "scores": [],
                "quizzes_attempted": 0,
                "understanding_score": understanding
            }

        data = profile["topics"][topic]

        data["scores"].append(topic_percentage)
        data["quizzes_attempted"] += 1
        data["understanding_score"] = understanding

    return profile


def generate_profile(user_id: str):

    profile = profiles[user_id]

    topic_performance = []

    for topic, data in profile["topics"].items():

        avg_score = sum(data["scores"]) / len(data["scores"])

        topic_performance.append(
            TopicPerformance(
                topic=topic,
                average_score=avg_score,
                quizzes_attempted=data["quizzes_attempted"],
                understanding_score=data["understanding_score"]
            )
        )

    overall_avg = sum(profile["scores"]) / len(profile["scores"])

    return ProfileResponse(
        user_id=user_id,
        total_quizzes=profile["total_quizzes"],
        overall_average=overall_avg,
        topic_performance=topic_performance,
        last_quiz_score=profile["scores"][-1]
    )