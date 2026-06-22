import time
import os
from dataclasses import dataclass
from typing import Optional, List

from deepeval.test_case import LLMTestCase
from deepeval.metrics import FaithfulnessMetric, AnswerRelevancyMetric, GEval
from deepeval.models.base_model import DeepEvalBaseLLM

from langchain_groq import ChatGroq

from graph.interview_graph import interview_graph

class GroqLLM(DeepEvalBaseLLM):
    def __init__(self, model_name="openai/gpt-oss-120b-", temperature=0.0):
        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise ValueError("GROQ_API_KEY missing")

        self.model_name = model_name

        self.llm = ChatGroq(
            model=model_name,
            api_key=api_key,
            temperature=temperature,
        )

    def load_model(self):
        return self.llm

    def generate(self, prompt: str) -> str:
        return self.llm.invoke(prompt).content

    async def a_generate(self, prompt: str) -> str:
        return (await self.llm.ainvoke(prompt)).content

    def get_model_name(self):
        return self.model_name

@dataclass
class RunResult:
    session_id: str
    question: str
    expected_answer: Optional[str]

    actual_answer: str
    retrieved_context: List[str]

    latency_seconds: float = 0.0

    faithfulness: Optional[float] = None
    relevance: Optional[float] = None
    correctness: Optional[float] = None

    faith_reason: Optional[str] = None
    rel_reason: Optional[str] = None
    corr_reason: Optional[str] = None

PIPELINE_CASES = [
    {
        "session_id": "pipe-001",
        "input": "Design a scalable ML deployment system for churn prediction",
        "simulated_answer": (
            "I would use a microservices architecture on Kubernetes. "
            "For data ingestion I'd use Kafka, store features in a Feature Store like Feast. "
            "Model serving via Seldon or BentoML with A/B testing support. "
            "Handle class imbalance with SMOTE or class weights. "
            "Monitor drift with Evidently AI. Use SHAP for explainability."
        ),
    },
    {
        "session_id": "pipe-002",
        "input": "Design a URL shortener like Bitly",
        "simulated_answer": (
            "Use a distributed system: API gateway → app servers → Redis cache → "
            "Cassandra for URL mappings. Generate short codes with base62 encoding of "
            "an auto-increment ID from Zookeeper to avoid collisions. "
            "CDN for static assets. Rate limiting per IP. "
            "Consistent hashing for horizontal scaling."
        ),
    },
]

OFFLINE_CASES = [
    {
        "session_id": "off-001",
        "question": "Design churn prediction system",
        "expected_answer": "Use XGBoost, SMOTE, monitoring, AUC-ROC",
        "retrieved_context": [
            "ML systems use monitoring",
            "SMOTE handles imbalance",
            "XGBoost performs well"
        ],
    }
]

def run_pipeline_case(case: dict) -> RunResult:
    t0 = time.perf_counter()

    state1 = {
        "session_id": case["session_id"],
        "language": "en",
        "user_input": case["input"],
    }
    result1 = interview_graph.invoke(state1)
    generated_question = result1.get("question") or case["input"]

    simulated_answer = case.get("simulated_answer", "")
    if simulated_answer:
        state2 = {
            **result1,
            "session_id": case["session_id"],
            "language": "en",
            "user_input": simulated_answer,
        }
        result2 = interview_graph.invoke(state2)
    else:
        result2 = result1

    latency = round(time.perf_counter() - t0, 2)

    raw_answer = (
        result2.get("final_report")
        or result2.get("summary")
        or result2.get("answer")
        or result2.get("response")
        or ""
    )
    safe_answer = (raw_answer or "").strip() or "No answer generated"

    candidate_output = simulated_answer.strip() if simulated_answer else safe_answer

    retrieved_context = (
        result2.get("retrieved_context")
        or result2.get("topics")
        or []
    )
    if isinstance(retrieved_context, str):
        import ast
        try:
            retrieved_context = ast.literal_eval(retrieved_context)
        except Exception:
            retrieved_context = [retrieved_context]

    return RunResult(
        session_id=case["session_id"],
        question=generated_question,
        expected_answer=None,
        actual_answer=candidate_output,
        retrieved_context=retrieved_context,
        latency_seconds=latency,
    )

def run_offline_case(case: dict) -> RunResult:
    expected = (case.get("expected_answer") or "").strip() or "No reference answer provided"
    return RunResult(
        session_id=case["session_id"],
        question=case["question"],
        expected_answer=expected,
        actual_answer=expected,
        retrieved_context=case.get("retrieved_context") or [],
    )

def evaluate(runs: List[RunResult]):
    model = GroqLLM("llama-3.3-70b-versatile")

    faith = FaithfulnessMetric(model=model)
    relev = AnswerRelevancyMetric(model=model)

    from deepeval.test_case import LLMTestCaseParams
    correctness = GEval(
        name="Correctness",
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
        ],
        evaluation_steps=[
            "Does the actual_output correctly address the input question?",
            "Is the solution technically valid and realistic?",
            "Is the answer complete with no major gaps?",
        ],
        model=model,
    )

    for i, run in enumerate(runs):

        if not run.actual_answer or not run.actual_answer.strip():
            run.actual_answer = "No answer generated"
        if not run.question or not run.question.strip():
            run.question = "No question provided"

        tc = LLMTestCase(
            input=run.question,
            actual_output=run.actual_answer,
            retrieval_context=run.retrieved_context or [],
        )

        try:
            relev.measure(tc)
            run.relevance = float(relev.score)
            run.rel_reason = relev.reason
        except Exception as e:
            run.rel_reason = f"ERROR: {e}"

        try:
            correctness.measure(tc)
            run.correctness = float(correctness.score)
            run.corr_reason = correctness.reason
        except Exception as e:
            run.corr_reason = f"ERROR: {e}"

        if run.retrieved_context:
            try:
                faith.measure(tc)
                run.faithfulness = float(faith.score)
                run.faith_reason = faith.reason
            except Exception as e:
                run.faith_reason = f"ERROR: {e}"

    return runs

def print_results(runs):
    print("\n" + "=" * 80)

    for r in runs:
        print(f"\n[{r.session_id}]")
        print(f"Q: {r.question}")
        print(f"A: {r.actual_answer}")

        print(f"\nRelevance   : {r.relevance} ({r.rel_reason})")
        print(f"Correctness : {r.correctness} ({r.corr_reason})")
        print(f"Faithfulness: {r.faithfulness} ({r.faith_reason})")

def test_deepeval():
    runs = []

    print("\nPIPELINE")
    for c in PIPELINE_CASES:
        runs.append(run_pipeline_case(c))

    print("\nOFFLINE")
    for c in OFFLINE_CASES:
        runs.append(run_offline_case(c))

    runs = evaluate(runs)
    print_results(runs)

    print("\nDONE")

if __name__ == "__main__":
    test_deepeval()