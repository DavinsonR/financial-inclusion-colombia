import pandas as pd

from iif import config


def test_dictionary_classifies_all_columns():
    dic = pd.read_csv(config.DATA_LEGACY / "diccionario_panel_legacy.csv")
    assert len(dic) == 102
    counts = dic["frecuencia_real"].value_counts()
    assert counts.get("trimestral", 0) == 76, counts.to_dict()
    assert counts.get("muerta (1 valor)", 0) == 2
    assert int(dic["usada_por_notebook"].sum()) == 21
    assert int((~dic["usada_por_notebook"]).sum()) == 81
