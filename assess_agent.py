import json
from pydantic import ValidationError 
from openai import OpenAI
from schema import Quiz, EvaluationResponse
from dotenv import load_dotenv
import os

load_dotenv()

client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=os.environ["HF_TOKEN"],
)
def generate_quiz(topic: str, difficulty: str):

    prompt = f"""
You are an expert assessment designer.

Generate questions:
- MCQs
- subjective questions

Generate 10 questions in a way that the topic is properly assessed.
Both MCQs and Subjective Questions and REQUIRED. The quiz should be a proper mix of MCQs and Subjective Questions for all round assessment.

Topic: {topic}
Difficulty: {difficulty}

Rules:
- Each MCQ must have 4 options
- Include correct answer
- Include explanation
- Each subjective question must include evaluation points (bullet list)

Return STRICT JSON matching this format:

{{
  "topic": "",
  "difficulty": "",
  "mcqs": [
    {{
      "question": "",
      "options": ["", "", "", ""],
      "correct_answer": "",
      "explanation": ""
    }}
  ],
  "subjective": [
    {{
      "question": "",
      "evaluation_points": ["", ""]
    }}
  ]
}}

Both MCQs and the Subjective questions MUST be present.
Do not omit any fields.
Do not return text outside JSON.
"""

    completion = client.chat.completions.create(
    model="openai/gpt-oss-20b:groq",
    temperature=0.3,
    max_tokens=2000,
    messages=[{"role": "user", "content": prompt}],
    # response_format={
    #     "type": "json_schema",
    #     "json_schema": {
    #         "name": "quiz_schema",
    #         "schema": Quiz.model_json_schema()
    #     }
    # },
)

    content = completion.choices[0].message.content
    
    print("\n===== LLM RESPONSE =====")
    print(content)
    print("========================\n")
    
    #Prints json
    quiz_dict = json.loads(content)

    quiz = Quiz(**quiz_dict)

    return quiz

def generate_eval(quiz: dict, user_sub: dict) -> EvaluationResponse:

    prompt = f"""
You are an expert evaluator.

Given the quiz and user answers below:

QUIZ:
{json.dumps(quiz, indent=2)}

USER ANSWERS:
{json.dumps(user_sub, indent=2)}

Instructions:
- Evaluate answers topic-wise.
- Calculate score and total per topic.
- Assign a topic understanding score from 0 to 100 based on conceptual understanding.
- The understanding score should consider correctness and depth of explanation.
- Calculate overall score and total.
- Provide constructive feedback per topic.
- Provide final overall feedback.

Return ONLY valid JSON.

Required JSON format:

{{
  "topic_scores": [
    {{
      "topic": "string",
      "score": 0,
      "total": 0,
      "topic_understanding_score": 0,
      "feedback": "string"
    }}
  ],
  "overall_score": 0,
  "overall_total": 0,
  "final_feedback": "string"
}}
"""
  

    completion = client.chat.completions.create(
    model="openai/gpt-oss-20b:groq",
    temperature=0.5,
    messages=[{"role": "user", "content": prompt}],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "evaluation_schema",
            "schema": EvaluationResponse.model_json_schema()
        }
    },
)

    content = completion.choices[0].message.content.strip()
    
    try:
        evaluation_dict = json.loads(content)
        evaluation = EvaluationResponse.model_validate(evaluation_dict)
        return evaluation

    except json.JSONDecodeError:
        raise ValueError("LLM did not return valid JSON")

    except ValidationError as e:
        raise ValueError(f"Invalid evaluation structure: {e}")