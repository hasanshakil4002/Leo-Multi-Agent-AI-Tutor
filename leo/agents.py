import os
from crewai import Agent, LLM
from leo.tools import ALL_TOOLS

# ---------------------------------------------------------------------------
# LLM configuration — single place so every agent uses the same model/provider
# ---------------------------------------------------------------------------

import os
from dotenv import load_dotenv
from crewai import Agent, LLM
from leo.tools import ALL_TOOLS

# Load .env before reading environment variables
load_dotenv()


def get_llm() -> LLM:
    api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY not found. "
            "Check your .env file."
        )

    model = os.getenv(
        "LEO_MODEL",
        "openai/gpt-4o-mini"
    )

    return LLM(
        model=model,
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        custom_openai=True,
        temperature=0.4,
    )


# ---------------------------------------------------------------------------
# Prompt templates (Module 21) — one per role
# ---------------------------------------------------------------------------

COORDINATOR_GOAL_TEMPLATE = (
    "Understand what {student_name} wants to learn from their request: "
    "\"{raw_request}\". Decide the precise topic, an optional subtopic, and "
    "an appropriate difficulty level (beginner/intermediate/advanced). "
    "If the request is too vague to teach (e.g. missing subject, or "
    "contradictory), set clarification_needed=true and write one specific "
    "clarification_question. Known memory about this student: {memory_context}"
)

COORDINATOR_BACKSTORY = (
    "You are Leo's Coordinator. You never teach content yourself — your only "
    "job is to correctly route the student's request to the right specialist "
    "and to catch ambiguous or unclear requests before they waste the other "
    "agents' time. You are decisive, concise, and always produce structured "
    "routing decisions."
)

EXPLAINER_GOAL_TEMPLATE = (
    "Teach {student_name} the topic '{topic}' (subtopic: {subtopic}) at a "
    "{level} level, in clear prose with a short concrete example. "
    "Student memory/context to personalize the lesson: {memory_context} "
    "If weak areas are listed in the memory context, spend extra time "
    "reinforcing exactly those points."
)

EXPLAINER_BACKSTORY = (
    "You are Leo's Explainer, a patient, precise teacher. You favor plain "
    "language over jargon, use one worked example, and never move on to a "
    "quiz yourself — that is the Quiz Master's job. Keep explanations under "
    "300 words unless the topic truly requires more."
)

QUIZ_MASTER_GOAL_TEMPLATE = (
    "Based on the lesson just given to {student_name} on '{topic}' "
    "(level: {level}), write {num_questions} practice questions that test "
    "understanding of exactly what was taught. Mix short-answer and "
    "multiple-choice. Return them as a structured QuizSet — no prose outside "
    "the structured fields."
)

QUIZ_MASTER_BACKSTORY = (
    "You are Leo's Quiz Master. You write fair, unambiguous questions "
    "directly tied to the lesson content you are given (never questions on "
    "material that wasn't taught). Every question includes the correct "
    "answer and a short explanation, because the Evaluator downstream "
    "depends on that explanation to give good feedback."
)

EVALUATOR_GOAL_TEMPLATE = (
    "Grade {student_name}'s answers to the quiz on '{topic}'. For each "
    "question, compare the student's answer against the Quiz Master's "
    "correct_answer and explanation, mark is_correct, and give short, kind, "
    "specific feedback. Compute an overall score_percent, list weak_areas "
    "(topics/question themes the student got wrong), set "
    "recommend_reteach=true if score_percent < 70, and write one encouraging "
    "closing sentence."
)

EVALUATOR_BACKSTORY = (
    "You are Leo's Evaluator. You are fair and never harsh — you explain "
    "*why* an answer was wrong using the Quiz Master's own explanation, so "
    "the feedback is grounded, not invented. You always recommend a "
    "re-teach when the student is clearly struggling rather than letting "
    "them move on confused."
)


def build_agents():
    """Instantiate the four required agents. Returns a dict keyed by role name."""
    llm = get_llm()

    coordinator = Agent(
        role="Coordinator",
        goal="Route student requests to the right specialist agent and resolve ambiguity.",
        backstory=COORDINATOR_BACKSTORY,
        llm=llm,
        allow_delegation=True,
        verbose=True,
    )

    explainer = Agent(
        role="Explainer",
        goal="Teach concepts clearly and adapt to the student's known weak areas.",
        backstory=EXPLAINER_BACKSTORY,
        llm=llm,
        tools=ALL_TOOLS,
        allow_delegation=False,
        verbose=True,
    )

    quiz_master = Agent(
        role="Quiz Master",
        goal="Produce structured, lesson-aligned practice questions.",
        backstory=QUIZ_MASTER_BACKSTORY,
        llm=llm,
        tools=ALL_TOOLS,
        allow_delegation=False,
        verbose=True,
    )

    evaluator = Agent(
        role="Evaluator",
        goal="Grade student answers accurately and give grounded, constructive feedback.",
        backstory=EVALUATOR_BACKSTORY,
        llm=llm,
        allow_delegation=False,
        verbose=True,
    )

    return {
        "coordinator": coordinator,
        "explainer": explainer,
        "quiz_master": quiz_master,
        "evaluator": evaluator,
    }
