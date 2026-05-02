from datetime import date
import json
from pydantic import ValidationError 
from openai import OpenAI
from schema import PlanResponse, TopicPlan
from services.build_profile import generate_profile
from models import Profile, Course
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import os

load_dotenv()

client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=os.environ["HF_TOKEN"],
    timeout=30.0,
    max_retries=3
)

from datetime import date


def get_course_time(user_id: int, course_id:int, db: Session):
    course = db.query(Course).filter_by(user_id=user_id,course_id=course_id).first()

    if not course:
        raise ValueError("Course not found")
    
    today = date.today()

    start_date = course.start_date.date()
    end_date = course.end_date.date()

    remaining_days = (end_date - today).days
    total_days = (end_date - start_date).days

    progress_ratio = (
        (today - start_date).days / total_days
        if total_days > 0 else 0
)

    return {
        "remaining_days": max(remaining_days, 0),
        "progress_ratio": progress_ratio
    }

def fetch_profile(user_id: int, course_id: int, db: Session):
    profile = db.query(Profile).filter_by(user_id=user_id, course_id=course_id).first()

    if not profile:
        raise ValueError("Profile not found")

    topic_performance = generate_profile(user_id, course_id, db)

    return {
        "overall_average": profile.overall_avg,
        "total_quizzes": profile.total_quiz,
        "topics": topic_performance
    }    

def generate_plan(context: dict, course_time = None) -> PlanResponse:
    if not context["topics"]:
        raise ValueError("No topic performance available for planning")

    context["topics"].sort(key=lambda x: x["average_score"])
    
    remaining_days = course_time.get("remaining_days") if course_time else None
    prompt = f"""
You are an intelligent academic planner.

You are given a user's learning performance and a strict course time constraint.

User Performance:
{json.dumps(context, indent=2)}

Course Constraint:
- The user has LIMITED time to complete the course
- Remaining time: {remaining_days if remaining_days is not None else "unknown"} days

Your job:
- Identify weak topics from the data
- Decide how many topics to include based on available time
- Adjust difficulty dynamically based on:
    - user performance
    - time remaining

Rules:
- If time is low → focus on fewer topics + revision
- If time is sufficient → include more topics
- Prioritize weakest topics first
- Do NOT overload the user
- Be realistic and adaptive

Return ONLY valid JSON in this format:

{{
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "generated_for_topics": [str],
  "recommended_difficulty": "easy" | "medium" | "hard",
  "study_plan": [
    {{
      "topic": str,
      "focus_areas": [str],
      "study_tips": str
    }}
  ],
  "daily_time_commitment": int (optional)
}}
"""

    completion = client.chat.completions.create(
        model=os.environ["MODEL_NAME"],
        temperature=0.3,
        messages=[{"role": "user", "content": prompt}],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "plan_schema",
                "schema": PlanResponse.model_json_schema()
            }
        },
    )

    content = completion.choices[0].message.content.strip()

    if isinstance(content, list):
        content = content[0].get("text", "")

    (content or "").strip()

    try:
        plan_dict = json.loads(content)
        plan = PlanResponse.model_validate(plan_dict)

        # ✅ validate dates
        if plan.end_date < plan.start_date:
            raise ValueError("Invalid plan dates")

        return plan

    except json.JSONDecodeError:
        raise ValueError("LLM did not return valid JSON")

    except ValidationError as e:
        raise ValueError(f"Invalid plan structure: {e}")