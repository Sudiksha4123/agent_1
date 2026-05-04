from datetime import date
import json
from pydantic import ValidationError 
from openai import OpenAI
from schema import PlanResponse, TopicPlan
from services.build_profile import generate_profile
from models import Profile, Course
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import time
import os
import re

load_dotenv()

client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=os.environ["HF_TOKEN"],
    timeout=30.0,
    max_retries=2
)

MAX_RETRIES = 3


def extract_json(content: str) -> dict:
    content = content.strip()
    match = re.search(r'```(?:json)?\s*([\s\S]*?)```', content)
    if match:
        content = match.group(1).strip()
    start = content.find('{')
    end = content.rfind('}')
    if start != -1 and end != -1:
        content = content[start:end+1]
    return json.loads(content)

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

def generate_plan(context: dict, course_time=None, initial_topics: list = None) -> PlanResponse:
    if not context["topics"]:
        raise ValueError("No topic performance available for planning")

    context["topics"].sort(key=lambda x: x["average_score"])
    remaining_days = course_time.get("remaining_days") if course_time else None

    # figure out which topics have been covered vs not yet started
    assessed_topics = [t["topic"] for t in context["topics"]]
    pending_topics = []
    if initial_topics:
        pending_topics = [t for t in initial_topics if t not in assessed_topics]

    prompt = f"""
You are an intelligent academic planner running a progressive study loop.

The student is working through a course step by step.
Each plan you generate is a SHORT TERM sprint — typically 3 to 14 days long.
Never generate a plan longer than 3 weeks.

Already Assessed Topics (with performance data):
{json.dumps(context["topics"], indent=2)}

Pending Topics Not Yet Covered:
{json.dumps(pending_topics, indent=2)}

Total remaining days in course: {remaining_days if remaining_days is not None else "unknown"}
Today's date: {date.today()}

Your job:
- Pick 1-3 topics maximum for this sprint
- If a topic has low average_score (below 50): include it for revision
- If performance is good (above 75% overall): introduce 1 new pending topic
- Mix at most 1 new topic with 1-2 revision topics per sprint
- Decide a realistic sprint length — between 3 and 14 days based on how many topics you picked
- Set start_date to today
- Set end_date to start_date + sprint duration

Difficulty rules:
- Overall average below 50%: Easy, focus on revision only
- Overall average 50-75%: Medium, mix revision + 1 new topic
- Overall average above 75%: Hard, push new topics

Return ONLY raw JSON. No markdown. Start with {{ end with }}

{{
  "start_date": "{date.today()}",
  "end_date": "YYYY-MM-DD",
  "topics": ["topic1", "topic2"],
  "recommended_difficulty": "Medium",
  "study_plan": [
    {{
      "topic": "topic1",
      "focus_areas": ["area1", "area2"],
      "study_tips": "tip here"
    }}
  ],
  "daily_time_commitment": 60
}}
"""

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"Plan generation attempt {attempt}/{MAX_RETRIES}")
            completion = client.chat.completions.create(
                model=os.environ["MODEL_NAME"],
                temperature=max(0.1, 0.3 - (attempt - 1) * 0.1),
                messages=[{"role": "user", "content": prompt}],
            )

            content = completion.choices[0].message.content
            if isinstance(content, list):
                content = content[0].get("text", "")
            content = (content or "").strip()

            print(f"Plan attempt {attempt} response: {content[:300]}")

            plan_dict = extract_json(content)

            # fix common field name mistake
            if "generated_for_topics" in plan_dict and "topics" not in plan_dict:
                plan_dict["topics"] = plan_dict.pop("generated_for_topics")

            # fix difficulty casing
            diff = plan_dict.get("recommended_difficulty", "Medium")
            diff_map = {"easy": "Easy", "medium": "Medium", "hard": "Hard"}
            plan_dict["recommended_difficulty"] = diff_map.get(diff.lower(), "Medium")

            plan = PlanResponse.model_validate(plan_dict)

            if plan.end_date < plan.start_date:
                raise ValueError("Invalid plan dates")
            if not plan.topics:
                raise ValueError("No topics in plan")

            return plan

        except (json.JSONDecodeError, ValidationError, ValueError) as e:
            last_error = e
            print(f"Plan attempt {attempt} failed: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(2 ** attempt)
            continue

    raise ValueError(f"Plan generation failed after {MAX_RETRIES} attempts: {last_error}")  
    

def generate_initial_plan(course_name: str, start_date, end_date, syllabus_text: str = None) -> PlanResponse:
    from datetime import date as date_type

    # handle both date objects and strings
    if isinstance(start_date, str):
        from datetime import datetime
        start_date = datetime.fromisoformat(start_date).date()
    else:
        start_date = start_date.date() if hasattr(start_date, 'date') else start_date

    if isinstance(end_date, str):
        from datetime import datetime
        end_date = datetime.fromisoformat(end_date).date()
    else:
        end_date = end_date.date() if hasattr(end_date, 'date') else end_date

    total_days = (end_date - start_date).days

    if syllabus_text:
        context_section = f"""
Course Syllabus:
{syllabus_text}

Use the syllabus to extract the key topics for this course.
"""
    else:
        context_section = f"""
No syllabus was provided.
Based on the course name "{course_name}", infer the most likely topics a student would study.
"""

    prompt = f"""
You are an intelligent academic planner helping a student prepare for their course.

Course Information:
- Course Name: {course_name}
- Start Date: {start_date}
- End Date: {end_date}
- Total Duration: {total_days} days

{context_section}

Your job:
- Extract or infer the key topics for this course
- Create a realistic study plan spread across the course duration
- Set an appropriate starting difficulty (easy for long courses, medium/hard for short ones)
- Prioritize foundational topics first, advanced topics later

Rules:
- If duration is more than 60 days → include more topics, easy/medium difficulty
- If duration is 30-60 days → medium difficulty, focused topics
- If duration is less than 30 days → hard difficulty, only core topics
- Be realistic, do not overload the student

Return ONLY valid JSON in this format:
{{
  "start_date": "{start_date}",
  "end_date": "{end_date}",
  "topics": [str],
  "recommended_difficulty": "Easy" | "Medium" | "Hard",
  "study_plan": [
    {{
      "topic": str,
      "focus_areas": [str],
      "study_tips": str
    }}
  ],
  "daily_time_commitment": int (Optional)
}}
"""

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"Initial plan generation attempt {attempt}/{MAX_RETRIES}")
            completion = client.chat.completions.create(
                model=os.environ["MODEL_NAME"],
                temperature=max(0.1, 0.3 - (attempt - 1) * 0.1),
                messages=[{"role": "user", "content": prompt}],
            )

            content = completion.choices[0].message.content
            if isinstance(content, list):
                content = content[0].get("text", "")
            content = (content or "").strip()

            print(f"Plan attempt {attempt} response: {content[:300]}")

            plan_dict = extract_json(content)

            # fix common LLM field name mistake
            if "generated_for_topics" in plan_dict and "topics" not in plan_dict:
                plan_dict["topics"] = plan_dict.pop("generated_for_topics")

            # fix difficulty casing
            diff = plan_dict.get("recommended_difficulty", "Medium")
            diff_map = {"easy": "Easy", "medium": "Medium", "hard": "Hard"}
            plan_dict["recommended_difficulty"] = diff_map.get(diff.lower(), "Medium")   

            plan = PlanResponse.model_validate(plan_dict)

            if plan.end_date < plan.start_date:
                raise ValueError("Invalid plan dates")
            if not plan.topics:
                raise ValueError("No topics in plan")

            return plan

        except (json.JSONDecodeError, ValidationError, ValueError) as e:
            last_error = e
            print(f"Plan attempt {attempt} failed: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(2 ** attempt)
            continue

    raise ValueError(f"Plan generation failed after {MAX_RETRIES} attempts: {last_error}")