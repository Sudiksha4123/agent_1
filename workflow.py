import json
from services.assess_agent import generate_quiz, generate_eval
from services.build_profile import update_profile, generate_profile
from services.planner_agent import get_course_time, fetch_profile, generate_plan
from models import Evaluation, TopicScoreDB, Quiz, Plan, Response
from schema import QuizSubmission
#######
######
######
######
#  Ye chodbangra faltu me kiya. every model has its primary key, one entry cant be same as others anyway but querying ke liye course id lagegi but agar primary key pata hai to ghanta kisi aur id ki zarurat nhi hai 
def run_quiz_pipeline(request:QuizSubmission, db):
    db_quiz = db.query(Quiz).filter(
        Quiz.quiz_id == request.quiz_id
    ).first()

    if not db_quiz:
        raise ValueError("Quiz not found")

    quiz_data = {
        "topics": db_quiz.topics,
        "mcqs": json.loads(db_quiz.mcqs),
        "subjective": json.loads(db_quiz.subjective)
    }

    # 1. Store response
    response = Response(
        user_id=request.user_id,
        quiz_id=request.quiz_id,
        answers=json.dumps({
            "mcq_answers": [a.model_dump() for a in request.mcq_answers],
            "subjective_answers": [a.model_dump() for a in request.subjective_answers]
        })
    )
    db.add(response)
    db.flush()
    
    print("Response stored!!")
    # 2. Generate evaluation
    evaluation_result = generate_eval(
        quiz=quiz_data,
        mcq_answers=request.mcq_answers,
        subjective_answers=request.subjective_answers
    )

    print("Evaluation generated successfully!!")

    if not evaluation_result:
        raise ValueError("Evaluation failed")

    # 3. Store evaluation
    evaluation = Evaluation(
        response_id=response.response_id,
        user_id=request.user_id,
        overall_score=evaluation_result.overall_score,
        overall_total=evaluation_result.overall_total,
        final_feedback=evaluation_result.final_feedback
    )
    db.add(evaluation)
    db.flush()

    # 4. Store topic scores
    for ts in evaluation_result.topic_scores:
        db.add(TopicScoreDB(
            evaluation_id=evaluation.evaluation_id,
            topic=ts.topic,
            score=ts.score,
            total=ts.total,
            understanding_score=ts.topic_understanding_score,
            feedback=ts.feedback
        ))

    print("Evaluation stored!!")

    # 5. Update profile
    update_profile(request.user_id, request.course_id, db)

    # 6. Fetch profile context
    context = fetch_profile(request.user_id, request.course_id, db)

    course_time=get_course_time(request.user_id, request.course_id,db)
    # 7. Generate plan (respect time constraint)
    plan = generate_plan(context, course_time)

    print("Plan generated successfully!!")

    if not plan:
        raise ValueError("Plan generation failed")
    
    print(type(plan.topics))        # should be list
    print(type(plan.study_plan))         # should be list
    print(type(plan.study_plan[0]))      # should be dict
    # 8. Store plan
    db.add(Plan(
    user_id=request.user_id,
    course_id=request.course_id,
    # syllabus_id=request.syllabus_id,  # if applicable

    start_date=plan.start_date,
    end_date=plan.end_date,
    topics = plan.topics,
    recommended_difficulty=plan.recommended_difficulty,
    study_plan=[tp.model_dump() for tp in plan.study_plan]
))
    
    print("Plan stored!!")
    db.commit()

    return {
        "evaluation": evaluation_result,
        "plan": plan
    }