import os
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

from leo.orchestrator import LeoOrchestrator  

st.set_page_config(page_title="Leo — Multi-Agent AI Tutor", page_icon="🦉", layout="centered")

AGENT_EMOJI = {
    "Coordinator": "🧭",
    "Explainer": "📘",
    "Quiz Master": "📝",
    "Evaluator": "✅",
}


def agent_badge(agent: str) -> str:
    return f"{AGENT_EMOJI.get(agent, '🤖')} **{agent}**"


def render_trace(log):
    with st.expander("🔎 Agent activity log (who did what)", expanded=False):
        for entry in log:
            st.markdown(f"- {agent_badge(entry['agent'])} — {entry['action']}: {entry['detail']}")



if "stage" not in st.session_state:
    st.session_state.stage = "intro"  # intro -> clarify -> explain -> quiz -> answers -> evaluate -> reteach -> done
if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = None

st.title("🦉 Leo — Multi-Agent AI Tutor")
st.caption("Coordinator → Explainer → Quiz Master → Evaluator, working together on your topic.")

if not (os.environ.get("OPENROUTER_API_KEY")):
    st.warning(
        "No API key found. Copy `.env.example` to `.env` and set `OPENROUTER_API_KEY` "
        
    )


if st.session_state.stage == "intro":
    with st.form("intro_form"):
        name = st.text_input("Your name", value=st.session_state.get("student_name", ""))
        request = st.text_area(
            "What do you want to study today?",
            placeholder="e.g. 'Explain recursion in Python' or 'help me with photosynthesis'",
        )
        submitted = st.form_submit_button("Start session")
    if submitted:
        if not name.strip() or not request.strip():
            st.error("Please enter both your name and a topic/request.")
        else:
            st.session_state.student_name = name.strip()
            st.session_state.raw_request = request.strip()
            st.session_state.orchestrator = LeoOrchestrator(name.strip())
            st.session_state.stage = "route"
            st.rerun()

elif st.session_state.stage == "route":
    orch: LeoOrchestrator = st.session_state.orchestrator
    st.markdown(agent_badge("Coordinator") + " is reviewing your request…")
    try:
        with st.spinner("Coordinator is routing your request..."):
            decision = orch.route(st.session_state.raw_request)
        st.session_state.decision = decision
        render_trace(orch.log)
        if decision.clarification_needed:
            st.session_state.stage = "clarify"
        else:
            st.session_state.stage = "explain"
        st.rerun()
    except Exception as exc:  # noqa: BLE001
        st.error(f"Coordinator couldn't process this request: {exc}")
        if st.button("Try again"):
            st.session_state.stage = "intro"
            st.rerun()


elif st.session_state.stage == "clarify":
    orch: LeoOrchestrator = st.session_state.orchestrator
    decision = st.session_state.decision
    st.markdown(agent_badge("Coordinator") + " needs a bit more detail:")
    st.info(decision.clarification_question)
    clarification = st.text_input("Your answer")
    if st.button("Send") and clarification.strip():
        with st.spinner("Coordinator is re-routing..."):
            new_decision = orch.reroute_with_clarification(st.session_state.raw_request, clarification.strip())
        st.session_state.decision = new_decision
        render_trace(orch.log)
        st.session_state.stage = "clarify" if new_decision.clarification_needed else "explain"
        st.rerun()


elif st.session_state.stage == "explain":
    orch: LeoOrchestrator = st.session_state.orchestrator
    decision = st.session_state.decision
    st.success(f"**Topic:** {decision.topic}  |  **Level:** {decision.level}")
    st.markdown(agent_badge("Explainer") + " is preparing your lesson…")
    try:
        with st.spinner("Explainer is teaching..."):
            lesson = orch.explain(decision.topic, decision.subtopic, decision.level)
        st.session_state.lesson = lesson
        st.session_state.stage = "quiz"
        st.rerun()
    except Exception as exc:  # noqa: BLE001
        st.error(f"Explainer stalled: {exc}")
        if st.button("Retry lesson"):
            st.rerun()


elif st.session_state.stage == "quiz":
    orch: LeoOrchestrator = st.session_state.orchestrator
    decision = st.session_state.decision
    st.markdown(agent_badge("Explainer"))
    st.write(st.session_state.lesson)
    if "quiz" not in st.session_state:
        st.markdown(agent_badge("Quiz Master") + " is writing practice questions…")
        try:
            with st.spinner("Quiz Master is working..."):
                quiz = orch.make_quiz(decision.topic, decision.level, st.session_state.lesson)
            st.session_state.quiz = quiz
            st.rerun()
        except Exception as exc:  # noqa: BLE001
            st.error(f"Quiz Master stalled: {exc}")
            if st.button("Retry quiz generation"):
                st.rerun()
    else:
        quiz = st.session_state.quiz
        st.markdown(agent_badge("Quiz Master") + f" — {len(quiz.questions)} questions for you:")
        render_trace(orch.log)
        with st.form("answers_form"):
            answers = {}
            for q in quiz.questions:
                st.markdown(f"**Q{q.id}. {q.question}**")
                if q.choices:
                    answers[q.id] = st.radio(f"Answer to Q{q.id}", q.choices, key=f"q_{q.id}", index=None)
                else:
                    answers[q.id] = st.text_input(f"Answer to Q{q.id}", key=f"q_{q.id}")
            submit_answers = st.form_submit_button("Submit answers to Evaluator")
        if submit_answers:
            st.session_state.answers = {qid: (a or "") for qid, a in answers.items()}
            st.session_state.stage = "evaluate"
            st.rerun()


elif st.session_state.stage == "evaluate":
    orch: LeoOrchestrator = st.session_state.orchestrator
    decision = st.session_state.decision
    quiz = st.session_state.quiz
    st.markdown(agent_badge("Evaluator") + " is grading your answers…")
    try:
        with st.spinner("Evaluator is working..."):
            evaluation = orch.evaluate(decision.topic, quiz, st.session_state.answers)
        st.session_state.evaluation = evaluation
        st.session_state.stage = "results"
        st.rerun()
    except Exception as exc:  # noqa: BLE001
        st.error(f"Evaluator stalled: {exc}")
        if st.button("Retry grading"):
            st.rerun()


elif st.session_state.stage == "results":
    orch: LeoOrchestrator = st.session_state.orchestrator
    decision = st.session_state.decision
    evaluation = st.session_state.evaluation
    st.markdown(agent_badge("Evaluator") + f" — Score: **{evaluation.score_percent}%**")
    for item in evaluation.feedback_items:
        icon = "✅" if item.is_correct else "❌"
        st.markdown(f"{icon} **Q{item.question_id}**: {item.feedback}")
    if evaluation.weak_areas:
        st.warning("Weak areas: " + ", ".join(evaluation.weak_areas))
    st.info(evaluation.encouragement)
    render_trace(orch.log)

    if evaluation.recommend_reteach and not st.session_state.get("reteach_done"):
        st.markdown("---")
        st.markdown(
            agent_badge("Evaluator") + " → " + agent_badge("Coordinator")
            + ": recommending a re-teach on the weak areas above."
        )
        if st.button("🔁 Let Leo re-teach the weak areas"):
            with st.spinner("Explainer is re-teaching the weak areas..."):
                reteach_text = orch.reteach_on_weak_areas(decision.topic, decision.level, evaluation.weak_areas)
            st.session_state.reteach_text = reteach_text
            st.session_state.reteach_done = True
            st.rerun()
    if st.session_state.get("reteach_done"):
        st.markdown(agent_badge("Explainer") + " (re-teach):")
        st.write(st.session_state.reteach_text)

    st.markdown("---")
    if st.button("Start a new topic"):
        for key in list(st.session_state.keys()):
            if key not in ("student_name",):
                del st.session_state[key]
        st.session_state.stage = "intro"
        st.rerun() 
