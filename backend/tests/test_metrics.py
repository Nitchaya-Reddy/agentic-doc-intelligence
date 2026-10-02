from app.evaluation.metrics import citation_accuracy, citation_coverage, evaluate


def test_citation_accuracy():
    assert citation_accuracy("Vacation is 20 days [S1].", {"S1"}) == 1.0
    assert citation_accuracy("Vacation is 20 days [S9].", {"S1"}) == 0.0


def test_evaluate_has_all_metrics():
    metrics = evaluate(
        "How many vacation days?",
        "Employees receive 20 vacation days [S1].",
        ["S1"],
        ["Full-time employees receive 20 days of paid vacation."],
    )
    assert set(metrics) == {
        "retrieval_relevance", "faithfulness", "citation_accuracy", "citation_coverage", "hallucination_rate"
    }
    assert metrics["citation_accuracy"] == 1.0
    assert 0 <= metrics["hallucination_rate"] <= 1


def test_citation_coverage():
    assert citation_coverage("The policy allows remote work [S1].") == 1.0
