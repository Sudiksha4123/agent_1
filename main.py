import json
import os
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import get_db
from services.assess_agent import get_latest_plan, generate_quiz, generate_eval
from services.workflow import run_quiz_pipeline
from services.planner_agent import generate_initial_plan
from schema import QuizRequest, QuizSet, MCQ, SubjectiveQuestion, QuizSubmission, EvaluationResponse, ProfileResponse, TopicPerformance, PlanResponse
from models import User, Course, Syllabus, Evaluation, TopicScoreDB, Quiz, Plan, Profile
from auth.dependencies import get_current_user
from auth.routes import router as auth_router

app = FastAPI()

origins = os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, include_in_schema=True)

@app.get("/")
def home():
    return {"message": "Quiz AI backend running"}

# =======================
# courses
@app.get("/courses")
def get_courses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    courses = db.query(Course).filter(Course.user_id == current_user.user_id).all()
    return [
        {
            "course_id": c.course_id,
            "name": c.name,
            "start_date": c.start_date,
            "end_date": c.end_date,
            "created_at": c.created_at
        }
        for c in courses
    ]

@app.post("/courses")
def create_course(
    course: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    new_course = Course(
        user_id=current_user.user_id,
        name=course["name"],
        start_date=datetime.fromisoformat(course["start_date"]) if course.get("start_date") else None,
        end_date=datetime.fromisoformat(course["end_date"]) if course.get("end_date") else None,
    )
    db.add(new_course)
    db.flush()
    

    new_profile = Profile(
        user_id=current_user.user_id,
        course_id=new_course.course_id
    )

    db.add(new_profile)
    db.commit()
    db.refresh(new_course)
    
    return {
        "course_id": new_course.course_id,
        "name": new_course.name,
        "start_date": new_course.start_date,
        "end_date": new_course.end_date
    }

# =================
# use syllabus to generate initial plan
@app.post("/syllabus")
def create_syllabus(
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    # 1. Save syllabus
    new_syllabus = Syllabus(
        user_id=current_user.user_id,
        course_id=data["course_id"],
        course_name=data["course_name"],
        handout=data["handout"]
    )
    db.add(new_syllabus)
    db.flush()

    # 2. Get course dates
    course = db.query(Course).filter(
        Course.course_id == data["course_id"],
        Course.user_id == current_user.user_id
    ).first()

    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # 3. Generate initial plan from syllabus
    try:
        plan = generate_initial_plan(
            course_name=data["course_name"],
            start_date=course.start_date,
            end_date=course.end_date,
            syllabus_text=data["handout"]
        )

        db.add(Plan(
            user_id=current_user.user_id,
            course_id=data["course_id"],
            syllabus_id=new_syllabus.syllabus_id,
            start_date=plan.start_date,
            end_date=plan.end_date,
            topics=plan.topics,
            recommended_difficulty=plan.recommended_difficulty,
            study_plan=[tp.model_dump() for tp in plan.study_plan],
            is_initial=True
        ))
    except Exception as e:
        print(f"Plan generation failed: {e}")
        # don't block course creation if plan fails

    db.commit()
    db.refresh(new_syllabus)
    return {
        "message": "Syllabus saved and plan generated",
        "syllabus_id": new_syllabus.syllabus_id
    }

# =====================
# skip entering syllabus
@app.post("/courses/{course_id}/generate-plan")
def generate_plan_without_syllabus(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from services.planner_agent import generate_initial_plan

    course = db.query(Course).filter(
        Course.course_id == course_id,
        Course.user_id == current_user.user_id
    ).first()

    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    try:
        plan = generate_initial_plan(
            course_name=course.name,
            start_date=course.start_date,
            end_date=course.end_date,
            syllabus_text=None
        )

        db_plan = Plan(
            user_id=current_user.user_id,
            course_id=course_id,
            syllabus_id=None,
            start_date=plan.start_date,
            end_date=plan.end_date,
            topics=plan.topics,
            recommended_difficulty=plan.recommended_difficulty,
            study_plan=[tp.model_dump() for tp in plan.study_plan],
            is_initial=True
        )
        db.add(db_plan)
        db.commit()
        return {"message": "Plan generated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Plan generation failed: {str(e)}")

# ======================
# to generate sprint plans
@app.post("/courses/{course_id}/start-learning")
def start_learning(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from services.planner_agent import generate_plan, get_course_time

    # check sprint doesn't already exist
    existing_sprint = db.query(Plan).filter(
        Plan.user_id == current_user.user_id,
        Plan.course_id == course_id,
        Plan.is_initial == False
    ).first()

    if existing_sprint:
        return {"message": "Sprint already exists"}

    # get initial plan (course map) for context
    initial_plan = db.query(Plan).filter(
        Plan.user_id == current_user.user_id,
        Plan.course_id == course_id,
        Plan.is_initial == True
    ).first()

    if not initial_plan:
        raise HTTPException(status_code=404, detail="No course plan found. Please set up your course first.")

    try:
        context = {"topics": [], "overall_average": 0, "total_quizzes": 0}
        course_time = get_course_time(current_user.user_id, course_id, db)
        plan = generate_plan(context, course_time, initial_plan.topics)

        db.add(Plan(
            user_id=current_user.user_id,
            course_id=course_id,
            is_initial=False,
            start_date=plan.start_date,
            end_date=plan.end_date,
            topics=plan.topics,
            recommended_difficulty=plan.recommended_difficulty,
            study_plan=[tp.model_dump() for tp in plan.study_plan]
        ))
        db.commit()
        return {"message": "Sprint generated successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sprint generation failed: {str(e)}")
    

# ── Profile ───────────────────────────────────────────────

@app.get("/profile/{course_id}", response_model=ProfileResponse)
def get_profile(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from services.build_profile import generate_profile

    profile = db.query(Profile).filter(
        Profile.user_id == current_user.user_id,
        Profile.course_id == course_id
    ).first()

    topic_performance = generate_profile(current_user.user_id, course_id, db)

    if not profile:
        return {
            "total_quiz": 0,
            "overall_avg": 0.0,
            "overall_max": profile.overall_max or 0.0,   
            "topic_performance": topic_performance
        }

    return {
        "total_quiz": profile.total_quiz,
        "overall_avg": profile.overall_avg,
        "overall_max": profile.overall_max or 0.0,
        "topic_performance": topic_performance
    }

# ── Plan ──────────────────────────────────────────────────
@app.get("/plan/{course_id}/initial")
def get_initial_plan(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    plan = db.query(Plan).filter(
        Plan.user_id == current_user.user_id,
        Plan.course_id == course_id,
        Plan.is_initial == True
    ).first()

    if not plan:
        raise HTTPException(status_code=404, detail="No course map found")

    return {
        "plan_id": plan.plan_id,
        "topics": plan.topics,
        "recommended_difficulty": plan.recommended_difficulty,
        "study_plan": plan.study_plan,
        "start_date": plan.start_date,
        "end_date": plan.end_date
    }

@app.get("/plan/{course_id}")
def get_plan(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # first try to get latest sprint plan
    plan = db.query(Plan).filter(
        Plan.user_id == current_user.user_id,
        Plan.course_id == course_id,
        Plan.is_initial == False
    ).order_by(Plan.created_at.desc()).first()

    # fall back to initial plan if no sprint exists yet
    if not plan:
        plan = db.query(Plan).filter(
            Plan.user_id == current_user.user_id,
            Plan.course_id == course_id
        ).order_by(Plan.created_at.desc()).first()

    if not plan:
        raise HTTPException(status_code=404, detail="No plan found for this course")

    return {
        "plan_id": plan.plan_id,
        "topics": plan.topics,
        "recommended_difficulty": plan.recommended_difficulty,
        "study_plan": plan.study_plan,
        "start_date": plan.start_date,
        "end_date": plan.end_date,
        "is_initial": plan.is_initial
    }

@app.get("/quiz/status/{course_id}")
def get_quiz_status(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sprint_plan_exists = db.query(Plan).filter(
        Plan.user_id == current_user.user_id,
        Plan.course_id == course_id,
        Plan.is_initial == False
    ).first() is not None

    quiz_count = db.query(Quiz).join(Plan).filter(
        Plan.user_id == current_user.user_id,
        Plan.course_id == course_id
    ).count()

    return {
        "sprint_ready": sprint_plan_exists,
        "quizzes_taken": quiz_count
    }

@app.post("/quiz/generate", response_model=QuizSet)
def generate_quiz_endpoint(
    request: QuizRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # check a sprint plan exists (not just the initial course map)
    sprint_plan = db.query(Plan).filter(
        Plan.user_id == current_user.user_id,
        Plan.course_id == request.course_id,
        Plan.is_initial == False
    ).first()

    if not sprint_plan:
        raise HTTPException(
            status_code=400,
            detail="no_sprint_plan"
        )

    try:
        plan = get_latest_plan(current_user.user_id, request.course_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    print("PLAN.TOPICS RAW:", repr(plan.topics))
    print("TYPE:", type(plan.topics))

    topics = plan.topics
    difficulty = plan.recommended_difficulty

    quiz = generate_quiz(topics, difficulty)

    db_quiz = Quiz(
        plan_id=plan.plan_id,  
        topics=topics,
        difficulty=difficulty,
        mcqs=json.dumps([mcq.model_dump() for mcq in quiz.mcqs]),
        subjective=json.dumps([q.model_dump() for q in quiz.subjective]),
        is_attempted=False
    )

    db.add(db_quiz)
    db.commit()
    db.refresh(db_quiz)

    return QuizSet(
        quiz_id=db_quiz.quiz_id,
        topics=topics,
        difficulty=difficulty,
        mcqs=[
            MCQ(**mcq.model_dump(), question_id=i + 1)
            for i, mcq in enumerate(quiz.mcqs)
        ],
        subjective=[
            SubjectiveQuestion(**q.model_dump(), question_id=i + 1)
            for i, q in enumerate(quiz.subjective)
        ],
    )

@app.post("/quiz/submit")
def submit_quiz(
    request: QuizSubmission,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return run_quiz_pipeline(request, db, current_user)

    # except Exception as e:
    #     db.rollback()
    #     raise HTTPException(status_code=500, detail=str(e))