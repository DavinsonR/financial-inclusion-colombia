from iif.legacy.ledger import Ledger


def test_ledger_loads_document_values():
    led = Ledger.from_yaml()
    assert led.doc["B2"]["beta"] == 35.5537 and led.doc_otros["Pesaran_CD"] == 66.81


def test_ledger_reproduces_the_25_discrepancies(legacy_results):
    frame = legacy_results.ledger_frame
    assert len(frame) == 40
    assert legacy_results.ledger.n_discrepancias == 25
    assert set(frame["estado"]) <= {"OK", "DISCREPA", "DIAGNÓSTICO", "SIN DATO EN DOC", "NO ESTIMADO"}


def test_every_document_n_is_off_by_one_cross_section(legacy_results):
    led = legacy_results.ledger
    for k in ("A1", "A2", "A3", "B1", "B3", "B4"):
        assert legacy_results.tabla6[k].N - led.doc[k]["N"] == 33
    assert legacy_results.tabla6["B2"].N == led.doc["B2"]["N"]
