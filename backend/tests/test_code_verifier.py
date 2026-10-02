from app.services.coding_agent_verifier import verify_generated_output


def test_verifier_rejects_destructive_shell():
    result = verify_generated_output("make a script", "rm -rf /tmp/demo", [])
    assert result["safe"] is False


def test_verifier_checks_required_terms():
    result = verify_generated_output("build API", "FastAPI app", ["FastAPI", "pytest"])
    assert result["constraints_met"] is False
    assert result["missing_terms"] == ["pytest"]


def test_verifier_rejects_gemini_key_exposure():
    result = verify_generated_output(
        "configure Gemini",
        'GEMINI_API_KEY="secret-demo-key"',
        [],
    )
    assert result["safe"] is False
    assert "credential exposure" in result["suspicious_patterns"]
