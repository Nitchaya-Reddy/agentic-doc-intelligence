import re
from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from app.config import get_settings
from app.evaluation.metrics import evaluate
from app.prompts import GENERATION_PROMPT, VERIFIER_PROMPT
from app.schemas import MetadataFilter, VerificationResult
from app.services.llm import get_chat_model
from app.services.retriever import RetrievedChunk, retrieve_documents


settings = get_settings()


class AgentState(TypedDict, total=False):
    question: str
    metadata_filter: MetadataFilter
    top_k: int

    classification: str
    rewritten_query: str

    sources: list[RetrievedChunk]

    answer: str

    verification: VerificationResult

    metrics: dict[str, float]

    confidence: float

    retry_count: int

    route: str

    warnings: list[str]


def _render_sources(
    sources: list[RetrievedChunk],
) -> str:

    return "\n\n".join(
        (
            f"[{s.source_id}] "
            f"file={s.filename} "
            f"chunk={s.chunk_index} "
            f"score={s.score:.3f}\n"
            f"{s.content}"
        )
        for s in sources
    )


# ---------------------------------------------------------
# FAST LOCAL CLASSIFICATION
# ---------------------------------------------------------

def _local_classify(
    question: str,
) -> tuple[str, str]:

    q = " ".join(
        question.strip().split()
    )

    lower = q.lower()

    if re.search(
        r"\b("
        r"summarize|"
        r"summary|"
        r"overview|"
        r"key points|"
        r"main points|"
        r"tl;?dr"
        r")\b",
        lower,
    ):

        intent = "summary"

    elif re.search(
        r"\b("
        r"compare|"
        r"comparison|"
        r"difference|"
        r"differences|"
        r"versus|"
        r"vs\.?|"
        r"contrast"
        r")\b",
        lower,
    ):

        intent = "comparison"

    else:

        intent = "document_qa"

    return intent, q


def classify_node(
    state: AgentState,
) -> AgentState:

    intent, rewritten = _local_classify(
        state["question"]
    )

    return {

        "classification": intent,

        "rewritten_query": rewritten,

        "retry_count": state.get(
            "retry_count",
            0,
        ),
    }


# ---------------------------------------------------------
# RETRIEVAL
# ---------------------------------------------------------

def retrieve_node(
    state: AgentState,
    *,
    db: Session,
) -> AgentState:

    sources = retrieve_documents(

        db,

        query=(
            state.get("rewritten_query")
            or state["question"]
        ),

        top_k=state.get(
            "top_k",
            4,
        ),

        metadata_filter=state.get(
            "metadata_filter",
            MetadataFilter(),
        ),
    )

    return {
        "sources": sources
    }


# ---------------------------------------------------------
# ANSWER GENERATION
# ---------------------------------------------------------

def generate_node(
    state: AgentState,
) -> AgentState:

    if not state.get("sources"):

        return {
            "answer":
                "I could not find relevant evidence "
                "in the uploaded documents."
        }

    prompt = GENERATION_PROMPT.format(

        question=state["question"],

        sources=_render_sources(
            state["sources"]
        ),
    )

    response = get_chat_model().invoke(prompt)

    content = response.content

    if isinstance(content, str):
        answer = content

    elif isinstance(content, list):
        text_parts = []

        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text_parts.append(item.get("text", ""))
            elif isinstance(item, str):
                text_parts.append(item)

        answer = "\n".join(text_parts).strip()

    else:
        answer = str(content)

    return {
        "answer": answer
    }


# ---------------------------------------------------------
# LOCAL CONFIDENCE
# ---------------------------------------------------------

def _metric_confidence(
    metrics: dict[str, float],
) -> float:

    return round(

        metrics["retrieval_relevance"]
        * 0.30

        + metrics["faithfulness"]
        * 0.25

        + metrics["citation_accuracy"]
        * 0.25

        + metrics["citation_coverage"]
        * 0.20,

        4,
    )


# ---------------------------------------------------------
# VERIFY ANSWER
# ---------------------------------------------------------

def verify_node(
    state: AgentState,
) -> AgentState:

    sources = state.get(
        "sources",
        [],
    )

    source_ids = [
        s.source_id
        for s in sources
    ]

    source_texts = [
        s.content
        for s in sources
    ]

    metrics = evaluate(

        state["question"],

        state.get(
            "answer",
            "",
        ),

        source_ids,

        source_texts,
    )


    metric_conf = (
        _metric_confidence(
            metrics
        )
    )


    # -------------------------------------------------
    # FAST PATH
    #
    # If citations and retrieval look good,
    # DO NOT CALL GEMINI AGAIN.
    # -------------------------------------------------

    fast_grounded = bool(

        sources

        and metrics[
            "retrieval_relevance"
        ] >= 0.40

        and metrics[
            "citation_accuracy"
        ] >= 0.99

        and metrics[
            "citation_coverage"
        ] >= 0.75
    )


    if fast_grounded:

        confidence = max(

            metric_conf,

            settings.confidence_threshold,
        )

        result = VerificationResult(

            grounded=True,

            confidence=confidence,

            issues=[],
        )

        return {

            "verification": result,

            "metrics": metrics,

            "confidence": confidence,
        }


    # -------------------------------------------------
    # SLOW PATH
    #
    # Only use Gemini verifier when necessary.
    # -------------------------------------------------

    llm_result = VerificationResult(

        grounded=False,

        confidence=0.0,

        issues=[
            "No sources retrieved"
        ],
    )


    if sources:

        verifier = (
            get_chat_model()
            .with_structured_output(
                VerificationResult
            )
        )


        llm_result = verifier.invoke(

            VERIFIER_PROMPT.format(

                question=(
                    state["question"]
                ),

                answer=state.get(
                    "answer",
                    "",
                ),

                sources=(
                    _render_sources(
                        sources
                    )
                ),
            )
        )


    confidence = round(

        0.65
        * llm_result.confidence

        + 0.35
        * metric_conf,

        4,
    )


    return {

        "verification":
            llm_result,

        "metrics":
            metrics,

        "confidence":
            confidence,
    }


# ---------------------------------------------------------
# ROUTING
# ---------------------------------------------------------

def route_after_verify(
    state: AgentState,
) -> str:

    verified = state.get(
        "verification"
    )


    if (

        verified

        and verified.grounded

        and state.get(
            "confidence",
            0.0,
        )
        >= settings.confidence_threshold

    ):

        return "finalize"


    if (
        state.get(
            "retry_count",
            0,
        )
        < settings.max_retries
    ):

        return "retry"


    return "human_review"


# ---------------------------------------------------------
# RETRY
# ---------------------------------------------------------

def retry_node(
    state: AgentState,
) -> AgentState:

    current_top_k = state.get(
        "top_k",
        4,
    )


    return {

        "retry_count":
            state.get(
                "retry_count",
                0,
            )
            + 1,


        "top_k":
            min(
                10,

                max(

                    current_top_k + 2,

                    current_top_k * 2,
                ),
            ),


        "rewritten_query":

            (
                f'{state.get(
                    "rewritten_query",
                    state["question"]
                )} supporting evidence details'
            ),


        "route":
            "retry",
    }


def finalize_node(
    state: AgentState,
) -> AgentState:

    return {
        "route":
            "finalize"
    }


def human_review_node(
    state: AgentState,
) -> AgentState:

    issues = (

        state.get(
            "verification"
        ).issues

        if state.get(
            "verification"
        )

        else []
    )


    warning = (

        "Low-confidence answer: "
        "human review recommended "
        "before relying on this response."
    )


    answer = state.get(
        "answer",
        "",
    )


    if not answer:

        answer = (

            "The available documents "
            "do not provide enough "
            "verified evidence "
            "to answer confidently."
        )


    return {

        "answer":
            answer,

        "route":
            "human_review",

        "warnings":
            [
                warning,
                *issues,
            ],
    }


# ---------------------------------------------------------
# LANGGRAPH
# ---------------------------------------------------------

def build_graph(
    db: Session,
):

    graph = StateGraph(
        AgentState
    )


    graph.add_node(
        "classify",
        classify_node,
    )


    graph.add_node(
        "retrieve",
        lambda state:
            retrieve_node(
                state,
                db=db,
            ),
    )


    graph.add_node(
        "generate",
        generate_node,
    )


    graph.add_node(
        "verify",
        verify_node,
    )


    graph.add_node(
        "retry",
        retry_node,
    )


    graph.add_node(
        "finalize",
        finalize_node,
    )


    graph.add_node(
        "human_review",
        human_review_node,
    )


    graph.add_edge(
        START,
        "classify",
    )


    graph.add_edge(
        "classify",
        "retrieve",
    )


    graph.add_edge(
        "retrieve",
        "generate",
    )


    graph.add_edge(
        "generate",
        "verify",
    )


    graph.add_conditional_edges(

        "verify",

        route_after_verify,

        {

            "finalize":
                "finalize",

            "retry":
                "retry",

            "human_review":
                "human_review",
        },
    )


    graph.add_edge(
        "retry",
        "retrieve",
    )


    graph.add_edge(
        "finalize",
        END,
    )


    graph.add_edge(
        "human_review",
        END,
    )


    return graph.compile()