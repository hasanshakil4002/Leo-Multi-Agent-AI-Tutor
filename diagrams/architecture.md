# Leo — Architecture Diagram

```mermaid
flowchart TD
    S[Student request] --> C[🧭 Coordinator]
    C -- "clear request" --> R[RoutingDecision\ntopic / subtopic / level]
    C -- "ambiguous request" --> CL[Ask clarification question]
    CL --> C

    R --> E[📘 Explainer]
    E -- "reads" --> M[(Student Memory\nJSON per student)]
    E -- "lesson text" --> Q[📝 Quiz Master]

    Q -- "QuizSet (structured)" --> H[🧑 Student answers\nhuman-in-the-loop]
    H -- "answers" --> V[✅ Evaluator]
    Q -- "correct answers + explanations" --> V

    V -- "EvaluationResult" --> M
    V -- "weak_areas + recommend_reteach" --> C2{Score >= 70%?}
    C2 -- "No" --> E2[📘 Explainer\nre-teach weak areas]
    E2 --> Q2[📝 Quiz Master\nshort re-quiz]
    Q2 --> H
    C2 -- "Yes" --> Done[Session complete]

    style C fill:#4f46e5,color:#fff
    style E fill:#0891b2,color:#fff
    style Q fill:#ca8a04,color:#fff
    style V fill:#16a34a,color:#fff
    style M fill:#6b7280,color:#fff
```

## Orchestration pattern

**Coordinator-led sequential pipeline with explicit typed hand-offs.**

- The four agents never run inside one giant automatic `Process.hierarchical`
  crew, because the pipeline must **pause for a real human** (the student
  answering the quiz) between the Quiz Master and the Evaluator stages.
- Instead, `leo/orchestrator.py`'s `LeoOrchestrator` runs each stage as its
  own single-task CrewAI `Crew` (`Process.sequential`) and passes each
  agent's **typed Pydantic output** as input context to the next stage:
  - Coordinator → `RoutingDecision` → Explainer
  - Explainer → lesson text → Quiz Master
  - Quiz Master → `QuizSet` → (student answers) → Evaluator
  - Evaluator → `EvaluationResult` → Student Memory
- The Coordinator still does real agentic work (parses free-text requests,
  decides topic/level, detects and resolves ambiguity) and the orchestrator
  plays the "manager" role for control flow — sequencing stages, retrying a
  stalled agent (`MAX_RETRIES` in `orchestrator.py`), and running the
  feedback loop back to the Explainer when the Evaluator recommends a
  re-teach.
