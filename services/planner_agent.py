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
    if not context["topics"] and not initial_topics:
        raise ValueError("No topic data available for planning")

    remaining_days = course_time.get("remaining_days") if course_time else None
    overall_avg = context.get("overall_average", 0)

    # topics already assessed with performance data
    assessed_topics = {t["topic"]: t for t in context.get("topics", [])}

    # maintain the original course map order
    # split into: weak (need revision), done well, not yet started
    weak_topics = []
    strong_topics = []
    not_started = []

    if initial_topics:
        for topic in initial_topics:
            if topic in assessed_topics:
                perf = assessed_topics[topic]
                if perf["average_score"] < 60:
                    weak_topics.append({
                        "topic": topic,
                        "average_score": perf["average_score"]
                    })
                else:
                    strong_topics.append(topic)
            else:
                not_started.append(topic)

    prompt = f"""
You are an academic sprint planner managing a student's progressive learning through a course.

You have a course map (the full list of topics in the correct learning order).
Your job is to generate the NEXT short study sprint for the student.

--- COURSE MAP (topics in order) ---
{json.dumps(initial_topics, indent=2)}

--- STUDENT PERFORMANCE SO FAR ---
Overall average: {overall_avg}%
Remaining days in course: {remaining_days if remaining_days is not None else "unknown"}
Today: {date.today()}

Weak topics (score below 60%, need revision):
{json.dumps(weak_topics, indent=2)}

Strong topics (score above 60%, covered well):
{json.dumps(strong_topics, indent=2)}

Topics not yet started (next in course map order):
{json.dumps(not_started, indent=2)}

--- SPRINT RULES ---

1. ALWAYS respect the course map order — do not skip ahead
2. Pick the NEXT 1-2 topics that haven't been started yet (in order from course map)
3. If there are weak topics, include at most 1 for revision alongside the new topic
4. If ALL not_started topics are done, focus entirely on revision of weak topics
5. Sprint duration:
   - 1 topic → 3 to 5 days
   - 2 topics → 5 to 7 days
   - 3 topics → 7 to 10 days
6. Difficulty:
   - Overall average below 50% → Easy
   - Overall average 50-75% → Medium  
   - Overall average above 75% → Hard
7. NEVER include more than 3 topics in a sprint
8. NEVER copy the full course map into a sprint

Set start_date to today: {date.today()}
Set end_date based on sprint duration above.

Return ONLY raw JSON. No markdown. Start with {{ end with }}

{{
  "start_date": "{date.today()}",
  "end_date": "YYYY-MM-DD",
  "topics": ["next topic from course map"],
  "recommended_difficulty": "Medium",
  "study_plan": [
    {{
      "topic": "topic name",
      "focus_areas": ["specific area 1", "specific area 2"],
      "study_tips": "actionable tip"
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

            if "generated_for_topics" in plan_dict and "topics" not in plan_dict:
                plan_dict["topics"] = plan_dict.pop("generated_for_topics")

            diff = plan_dict.get("recommended_difficulty", "Medium")
            diff_map = {"easy": "Easy", "medium": "Medium", "hard": "Hard"}
            plan_dict["recommended_difficulty"] = diff_map.get(diff.lower(), "Medium")

            plan = PlanResponse.model_validate(plan_dict)

            if plan.end_date < plan.start_date:
                raise ValueError("Invalid plan dates")
            if not plan.topics:
                raise ValueError("No topics in plan")

            # hard enforce max 3 topics
            if len(plan.topics) > 3:
                plan.topics = plan.topics[:3]
                plan.study_plan = plan.study_plan[:3]

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