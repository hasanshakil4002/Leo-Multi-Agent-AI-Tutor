import json
import logging
from typing import Dict, Optional, Tuple

from crewai import Crew, Process

from leo.agents import build_agents
from leo.memory import StudentMemory
from leo.models import EvaluationResult, QuizSet, RoutingDecision
from leo.tasks import (
    build_evaluate_task,
    build_explain_task,
    build_quiz_task,
    build_routing_task,
)

logger = logging.getLogger("leo")

MAX_RETRIES = 2  


class LeoOrchestrator:
    """Drives the four agents through a full tutoring session for one student."""

    def __init__(self, student_name: str):
        self.student_name = student_name
        self.memory = StudentMemory(student_name)
        self.agents = build_agents()
        self.log: list[dict] = []  # UI-facing trace of "which agent did what"

    def _trace(self, agent: str, action: str, detail: str = "") -> None:
        entry = {"agent": agent, "action": action, "detail": detail}
        self.log.append(entry)
        logger.info("[%s] %s %s", agent, action, detail[:200])

    def _run_single_task_crew(self, task, agent_label: str):
   
        last_error: Optional[Exception] = None
        for attempt in range(1, MAX_RETRIES + 2):
            try:
                crew = Crew(agents=[task.agent], tasks=[task], process=Process.sequential, verbose=False)
                result = crew.kickoff()
                return result
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                self._trace(agent_label, "retry", f"attempt {attempt} failed: {exc}")
        # All retries exhausted — bubble up as a clear, catchable error.
        raise RuntimeError(
            f"{agent_label} could not complete its task after {MAX_RETRIES + 1} attempts: {last_error}"
        )


    def route(self, raw_request: str) -> RoutingDecision:
        self._trace("Coordinator", "received request", raw_request)
        # We need a topic guess before we can look up memory context; use a
        # light heuristic first, then let the Coordinator refine it.
        provisional_topic_context = "no topic known yet"
        task = build_routing_task(
            self.agents["coordinator"], self.student_name, raw_request, provisional_topic_context
        )
        result = self._run_single_task_crew(task, "Coordinator")
        decision: RoutingDecision = result.pydantic
        if decision.clarification_needed:
            self._trace("Coordinator", "needs clarification", decision.clarification_question or "")
        else:
            self._trace(
                "Coordinator",
                "routed to Explainer",
                f"topic={decision.topic}, subtopic={decision.subtopic}, level={decision.level}",
            )
        return decision

    def reroute_with_clarification(self, raw_request: str, clarification_answer: str) -> RoutingDecision:
        combined = f"{raw_request}\n\nStudent's clarification: {clarification_answer}"
        return self.route(combined)

    def explain(self, topic: str, subtopic: Optional[str], level: str) -> str:
        memory_context = self.memory.context_snippet(topic)
        self._trace("Explainer", "teaching", f"topic={topic}, using memory: {memory_context}")
        task = build_explain_task(
            self.agents["explainer"], self.student_name, topic, subtopic or "", level, memory_context
        )
        result = self._run_single_task_crew(task, "Explainer")
        lesson_text = str(result)
        self._trace("Explainer", "handoff to Quiz Master", "lesson complete")
        return lesson_text


    def make_quiz(self, topic: str, level: str, lesson_text: str, num_questions: int = 4) -> QuizSet:
        self._trace("Quiz Master", "writing questions", f"based on lesson ({len(lesson_text)} chars)")
        task = build_quiz_task(
            self.agents["quiz_master"], self.student_name, topic, level, lesson_text, num_questions
        )
        result = self._run_single_task_crew(task, "Quiz Master")
        quiz: QuizSet = result.pydantic
        self._trace("Quiz Master", "handoff to student", f"{len(quiz.questions)} questions ready")
        return quiz


    def evaluate(self, topic: str, quiz: QuizSet, answers: Dict[int, str]) -> EvaluationResult:
        self._trace("Evaluator", "grading answers", f"{len(answers)} answers received from student")
        quiz_json = quiz.model_dump_json()
        answers_json = json.dumps(answers)
        task = build_evaluate_task(self.agents["evaluator"], self.student_name, topic, quiz_json, answers_json)
        result = self._run_single_task_crew(task, "Evaluator")
        evaluation: EvaluationResult = result.pydantic
        self._trace(
            "Evaluator",
            "handoff to memory",
            f"score={evaluation.score_percent}%, weak_areas={evaluation.weak_areas}, "
            f"recommend_reteach={evaluation.recommend_reteach}",
        )
        self.memory.record_session(topic, evaluation.score_percent, evaluation.weak_areas)
        return evaluation

    def reteach_on_weak_areas(self, topic: str, level: str, weak_areas: list) -> str:
        focus = ", ".join(weak_areas) if weak_areas else topic
        self._trace("Coordinator", "feedback loop triggered", f"re-teaching: {focus}")
        memory_context = (
            f"Re-teach ONLY these weak areas the student missed: {focus}. "
            + self.memory.context_snippet(topic)
        )
        task = build_explain_task(
            self.agents["explainer"], self.student_name, topic, focus, level, memory_context
        )
        result = self._run_single_task_crew(task, "Explainer")
        self._trace("Explainer", "re-teach complete", "handing back to Quiz Master for a short re-quiz")
        return str(result)
