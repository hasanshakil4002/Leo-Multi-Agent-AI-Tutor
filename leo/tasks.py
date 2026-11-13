from crewai import Task
from leo.models import RoutingDecision, QuizSet, EvaluationResult
from leo.agents import (
    COORDINATOR_GOAL_TEMPLATE,
    EXPLAINER_GOAL_TEMPLATE,
    QUIZ_MASTER_GOAL_TEMPLATE,
    EVALUATOR_GOAL_TEMPLATE,
)


def build_routing_task(agent, student_name: str, raw_request: str, memory_context: str) -> Task:
    description = COORDINATOR_GOAL_TEMPLATE.format(
        student_name=student_name, raw_request=raw_request, memory_context=memory_context
    )
    return Task(
        description=description,
        expected_output="A RoutingDecision object with topic, subtopic, level, "
        "clarification_needed and clarification_question.",
        agent=agent,
        output_pydantic=RoutingDecision,
    )


def build_explain_task(agent, student_name: str, topic: str, subtopic: str, level: str, memory_context: str) -> Task:
    description = EXPLAINER_GOAL_TEMPLATE.format(
        student_name=student_name,
        topic=topic,
        subtopic=subtopic or "none specified",
        level=level,
        memory_context=memory_context,
    )
    return Task(
        description=description,
        expected_output="A clear lesson (prose) of under 300 words with one worked example.",
        agent=agent,
    )


def build_quiz_task(agent, student_name: str, topic: str, level: str, lesson_text: str, num_questions: int = 4) -> Task:
    description = (
        QUIZ_MASTER_GOAL_TEMPLATE.format(
            student_name=student_name, topic=topic, level=level, num_questions=num_questions
        )
        + f"\n\nHere is the lesson the Explainer just gave — base every question on it:\n---\n{lesson_text}\n---"
    )
    return Task(
        description=description,
        expected_output="A QuizSet object with a list of QuizQuestion items.",
        agent=agent,
        output_pydantic=QuizSet,
    )


def build_evaluate_task(agent, student_name: str, topic: str, quiz_json: str, answers_json: str) -> Task:
    description = (
        EVALUATOR_GOAL_TEMPLATE.format(student_name=student_name, topic=topic)
        + f"\n\nQuiz Master's questions (with correct answers/explanations), as JSON:\n{quiz_json}\n\n"
        f"Student's submitted answers, as JSON (keyed by question id):\n{answers_json}"
    )
    return Task(
        description=description,
        expected_output="An EvaluationResult object with per-question feedback, "
        "score_percent, weak_areas, recommend_reteach, and encouragement.",
        agent=agent,
        output_pydantic=EvaluationResult,
    )
