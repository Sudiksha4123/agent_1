import json
import threading
from services.assess_agent import generate_eval
from services.build_profile import update_profile, generate_profile
from services.planner_agent import get_course_time, fetch_profile, generate_plan
from models import Evaluation, TopicScoreDB, Quiz, Plan, Response
from schema import QuizSubmission
from sqlalchemy.orm import Session
from database import SessionLocal  # import your session factory


def generate_plan_background(user_id: int, course_id: int):
    db = SessionLocal()
    try:
        # get the course map (initial plan)
        initial_plan = db.query(Plan).filter(
            Plan.user_id == user_id,
            Plan.course_id == course_id,
            Plan.is_initial == True
        ).first()

        initial_topics = initial_plan.topics if initial_plan else None

        # update profile with latest quiz performance
        update_profile(user_id, course_id, db)
        print("Profile updated!!")

        # get performance context
        try:
            context = fetch_profile(user_id, course_id, db)
        except ValueError:
            # no profile yet — first sprint, no performance data
            context = {"topics": [], "overall_average": 0, "total_quizzes": 0}

        course_time = get_course_time(user_id, course_id, db)

        plan = generate_plan(context, course_time, initial_topics)
        if not plan:
            print("Plan generation returned None, skipping")
            return

        db.add(Plan(
            user_id=user_id,
            course_id=course_id,
            is_initial=False,
            start_date=plan.start_date,
            end_date=plan.end_date,
            topics=plan.topics,
            recommended_difficulty=plan.recommended_difficulty,
            study_plan=[tp.model_dump() for tp in plan.study_plan]
        ))
        db.commit()
        print("Sprint plan stored!!")

    except Exception as e:
        print(f"Background plan generation failed (non-critical): {e}")
        db.rollback()
    finally:
        db.close()


def run_quiz_pipeline(request: QuizSubmission, db: Session, current_user):
    user_id = current_user.user_id

    
    db_quiz = db.query(Quiz).filter(Quiz.quiz_id == request.quiz_id).first()
    if not db_quiz:
        raise ValueError("Quiz not found")

    quiz_data = {
        "topics": db_quiz.topics,
        "mcqs": json.loads(db_quiz.mcqs),
        "subjective": json.loads(db_quiz.subjective)
    }

    
    response = Response(
        user_id=user_id,
        quiz_id=request.quiz_id,
        answers=json.dumps({
            "mcq_answers": [a.model_dump() for a in request.mcq_answers],
            "subjective_answers": [a.model_dump() for a in request.subjective_answers]
        })
    )
    db.add(response)
    db.flush()
    print("Response stored!!")

    db_quiz.is_attempted=True
    db.add(db_quiz)
    db.flush()

    
    try:
        evaluation_result = generate_eval(
            quiz=quiz_data,
            mcq_answers=request.mcq_answers,
            subjective_answers=request.subjective_answers
        )
        print("Evaluation generated successfully!!")
    except Exception as e:
        db.rollback()
        raise ValueError(f"Evaluation failed: {e}")

    
    evaluation = Evaluation(
        response_id=response.response_id,
        user_id=user_id,
        overall_score=evaluation_result.overall_score,
        overall_total=evaluation_result.overall_total,
        final_feedback=evaluation_result.final_feedback
    )
    db.add(evaluation)
    db.flush()

    for ts in evaluation_result.topic_scores:
        db.add(TopicScoreDB(
            evaluation_id=evaluation.evaluation_id,
            topic=ts.topic,
            score=ts.score,
            total=ts.total,
            understanding_score=ts.topic_understanding_score,
            feedback=ts.feedback
        ))

    db.commit()
    print("Evaluation stored!!")

    # fire background plan generation 
    thread = threading.Thread(
        target=generate_plan_background,
        args=(user_id, request.course_id),
        daemon=True
    )
    thread.start()

    return {
        "topic_scores": [
            {
                "topic": ts.topic,
                "score": ts.score,
                "total": ts.total,
                "topic_understanding_score": ts.topic_understanding_score,
                "feedback": ts.feedback
            }
            for ts in evaluation_result.topic_scores
        ],
        "overall_score": evaluation_result.overall_score,
        "overall_total": evaluation_result.overall_total,
        "final_feedback": evaluation_result.final_feedback
    }