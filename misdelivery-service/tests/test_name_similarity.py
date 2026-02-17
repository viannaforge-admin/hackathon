from app.name_similarity import normalized_similarity


def test_similarity_high_for_confusable_names() -> None:
    score = normalized_similarity("Rahul Verma", "Rahul Sharma")
    assert score >= 0.9


def test_similarity_low_for_different_names() -> None:
    score = normalized_similarity("Rahul Verma", "Priya Menon")
    assert score < 0.9
