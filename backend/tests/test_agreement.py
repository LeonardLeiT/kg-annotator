from app.services.agreement import agreement_label, fleiss_kappa, fleiss_kappa_binary


def test_fleiss_kappa_is_one_for_mixed_unanimous_items():
    metric = fleiss_kappa_binary([3, 3, 0, 0])
    assert metric["kappa"] == 1.0
    assert metric["observed_agreement"] == 1.0
    assert metric["expected_agreement"] == 0.5


def test_fleiss_kappa_handles_no_candidate_items():
    metric = fleiss_kappa_binary([])
    assert metric["kappa"] is None
    assert metric["items"] == 0
    assert agreement_label(metric["kappa"]) == "无法计算"


def test_multicategory_kappa_represents_unanimous_types():
    metric = fleiss_kappa([{"Material": 3}, {"Property": 3}, {"NONE": 3}])
    assert metric["kappa"] == 1.0
    assert metric["items"] == 3
