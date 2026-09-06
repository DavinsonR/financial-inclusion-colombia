# Reproducción del notebook consolidado

## Entorno

- python: `3.11.15`
- pandas: `3.0.5`
- numpy: `2.4.6`
- linearmodels: `7.0`
- sklearn: `1.9.0`
- archivo: `panel_fintech_colombia_trimestral.xlsx`
- sha256: `fb4fba083e2077f33df544662bbc1d3b6a63a662a2b200598ec92d2d944e07df`
- modo: `notebook`

## D1 — Estructura temporal

- pib_percapita: distintos por (depto, año) min=1 max=1 media=1.00
- pib_crecimiento: distintos por (depto, año) min=1 max=1 media=1.00
- IPC_pct: distintos por (depto, año) min=1 max=1 media=1.00
- internet_pct: distintos por (depto, año) min=1 max=1 media=1.00
- educacion_anios: distintos por (depto, año) min=1 max=1 media=1.00
- Empleo_Informal: distintos por (depto, año) min=1 max=1 media=1.00
- pib_percapita distintos por departamento: media=5.00
- fracción crec_pib(t)==crec_pib(t-1): 0.643
- fracción crec_pib_pc == 0: 0.643

## Índice

- KMO = 0.7189 | Bartlett χ² = 2543.45 (p = 0.0000) | componentes = 4 | var. acum. = 84.42%
- pesos de componentes: [0.5539, 0.2058, 0.1625, 0.0778] | corr(IIF, cuentas) = 0.8684
- corr(IIF, IIF sin internet) = 0.9933 | corr(IIF, IIF 2017–2019) = 0.9947

Cargas:

|                    |   PC1 (46.8%) |   PC2 (17.4%) |   PC3 (13.7%) |   PC4 (6.6%) |
|:-------------------|--------------:|--------------:|--------------:|-------------:|
| Corresponsales     |        0.4278 |       -0.0992 |        0.1468 |      -0.1472 |
| Cuentas ahorro     |        0.3913 |        0.2576 |        0.1052 |       0.1934 |
| Internet (%)       |        0.3532 |       -0.0277 |        0.1355 |      -0.6643 |
| Pagos digitales    |        0.4165 |       -0.0934 |        0.1446 |      -0.1993 |
| Transferencias     |        0.219  |       -0.6005 |       -0.1903 |       0.3483 |
| Depósitos          |        0.3567 |       -0.4085 |       -0.0832 |       0.2796 |
| Microcrédito/PIB   |       -0.0614 |       -0.1696 |       -0.7883 |      -0.4369 |
| Créd. consumo/PIB  |        0.2717 |        0.4227 |       -0.4838 |       0.2395 |
| Créd. vivienda/PIB |        0.336  |        0.4234 |       -0.1718 |       0.1101 |

Pesos implícitos por variable (lo que el notebook nunca imprimió):

|                    |   peso_implicito |
|:-------------------|-----------------:|
| Corresponsales     |           0.2289 |
| Cuentas ahorro     |           0.3019 |
| Internet (%)       |           0.1603 |
| Pagos digitales    |           0.2195 |
| Transferencias     |          -0.0061 |
| Depósitos          |           0.1217 |
| Microcrédito/PIB   |          -0.231  |
| Créd. consumo/PIB  |           0.1775 |
| Créd. vivienda/PIB |           0.2539 |

## Tabla 6

```text
  A1 FE-Est   | IIF                                β= +20.8640*** SE= 5.9913 p=0.0006 N= 429 R²=0.0239
  A2 FE-Dyn   | IIF_lag1                           β= +57.8769*** SE= 7.6273 p=0.0000 N= 396 R²=0.1160
  A3 2way FE  | IIF_lag1  ← REFERENCIA             β=  +0.3579    SE= 6.2724 p=0.9545 N= 396 R²=0.0058
  A4 2way FE  | IIF       ← FALTABA                β=  -8.4388    SE= 6.9623 p=0.2262 N= 429 R²=0.0075
  B1 FE-Est   | IIF                                β=  +3.0349    SE= 4.8141 p=0.5288 N= 462 R²=0.0708
  B2 FE-Dyn   | IIF_lag1                           β= +35.5537*** SE= 5.9553 p=0.0000 N= 429 R²=0.1992
  B3 FE-Dyn   | IIF_PC1_lag1                       β= +25.8399*** SE= 4.9779 p=0.0000 N= 429 R²=0.1955
  B4 2way FE  | IIF_lag1                           β=  -5.7504    SE= 4.2043 p=0.1722 N= 429 R²=0.1907
```

## Hausman, Mundlak, correlaciones

- Hausman (NO válido con cov clusterizada): χ²(6) = 292.7736, p = 0.0000
- Mundlak: β_within = +17.2638 (p=0.0000) | β_mean = +6.7960 (p=0.0615)
- Corr between = +0.1201 | Corr within = -0.1532

## Nickell

- PIB agregado: ρ̂ = +0.4279 | sesgo ≈ -0.1098 | ρ corregido ≈ +0.5377 | 25.7% de ρ̂
- PIB per cápita: ρ̂ = +0.1314 | sesgo ≈ -0.0870 | ρ corregido ≈ +0.2184 | 66.2% de ρ̂

## Robustez

```text
  Pre-COVID | FE Entity                            β=  -1.0580    SE= 2.0690 p=0.6096 N= 264 R²=0.4733
  Pre-COVID | two-way                              β=  -7.9795    SE= 5.7312 p=0.1652 N= 264 R²=0.4558
  FE Entity | DK SE                                β= +35.5537    SE=37.0221 p=0.3375 N= 429 R²=0.1992
  Trimming 1%                                      β= +30.2266*** SE= 6.0886 p=0.0000 N= 420 R²=0.3048
  Winsorización 5%                                 β= +28.6497*** SE= 5.2424 p=0.0000 N= 429 R²=0.2461
  IIF_lag2      | PIB pc                           β= +25.7220**  SE=10.1110 p=0.0114 N= 396 R²=0.0260
  IIF_lag2 2way | PIB pc                           β=  +2.0966    SE= 5.5865 p=0.7077 N= 396 R²=0.0060
  IIF sin internet | PIB pc  (D2)                  β= +57.7779*** SE= 7.1292 p=0.0000 N= 396 R²=0.1262
  IIF sin internet 2way | PIB pc  (D2)             β=  +4.6279    SE= 4.1289 p=0.2631 N= 396 R²=0.0068
  IIF out-of-sample | PIB pc (D3)                  β= +63.4259*** SE= 7.7934 p=0.0000 N= 396 R²=0.1396
  IIF out-of-sample 2way | PIB pc (D3)             β=  +1.6526    SE= 5.6106 p=0.7685 N= 396 R²=0.0059
  FE Entity + tendencia t_idx                      β= +45.4128*** SE= 5.6740 p=0.0000 N= 429 R²=0.2066
  log(IIF)_lag1 | PIB pc                           β=  +8.1401*** SE= 1.9488 p=0.0000 N= 396 R²=0.0548
```
- Pesaran CD = 69.1165, p = 0.0000 (N=33, T medio=13.0)
- SE clustered = 5.9553 → Driscoll-Kraay = 37.0221
- r(e_t, e_t-1) = 0.1279, p = 0.0109

## Heterogeneidad regional

| Region    |    beta |      se |      p |   N |   N_dep |
|:----------|--------:|--------:|-------:|----:|--------:|
| Andina    | 23.2643 |  9.1796 | 0.0125 | 143 |      11 |
| Caribe    | 72.2255 | 23.563  | 0.0029 | 104 |       8 |
| Pacífica  | 58.5644 |  8.3576 | 0      |  52 |       4 |
| Orinoquía | 16.4008 | 12.7984 | 0.2071 |  52 |       4 |
| Amazonía  | 50.9128 | 13.6983 | 0.0004 |  78 |       6 |

## Descriptivas

|                    |   N |      mean |      std |      min |       25% |       50% |       75% |       max |
|:-------------------|----:|----------:|---------:|---------:|----------:|----------:|----------:|----------:|
| crec_pib           | 462 |   -0.0534 |   6.1492 | -23.5692 |   -5.1428 |    1.9773 |    3.0811 |   28.0755 |
| crec_pib_pc        | 429 |    0.7655 |   6.6442 | -32.8543 |    0      |    0      |    0      |   47.2285 |
| log_fintech_pc     | 462 |    7.7952 |   0.6841 |   4.7084 |    7.4652 |    7.8297 |    8.2795 |    9.2246 |
| d_acc_corresp      | 462 |   39.6841 |  21.1131 |   5.6216 |   24.008  |   36.7208 |   50.6484 |  111.956  |
| d_acc_cta_ah       | 462 | 1976.64   | 955.135  | 496.664  | 1285.61   | 1787.12   | 2503.06   | 5079.64   |
| d_acc_internet     | 462 |   34.6916 |  22.004  |   0      |   17      |   36.05   |   54      |   81.5249 |
| d_uso_pagos_pc     | 462 | 1289.55   | 957.925  |  48.9249 |  567.488  | 1006.04   | 1957.62   | 4414.27   |
| d_uso_transf_pc    | 462 |   50.3143 |  41.1467 |   0.7834 |   22.7488 |   37.6182 |   63.9801 |  225.106  |
| d_uso_depositos_pc | 462 |  796.431  | 450.825  |  44.4973 |  486.509  |  693.205  |  976.737  | 3177.15   |
| d_pro_micro        | 462 |    0.0059 |   0.0042 |   0.0005 |    0.0031 |    0.0044 |    0.0072 |    0.0212 |
| d_pro_cred_cons    | 462 |    0.0411 |   0.0213 |   0.0011 |    0.0249 |    0.0394 |    0.0557 |    0.1098 |
| d_pro_cred_viv     | 462 |    0.0058 |   0.0045 |   0      |    0.002  |    0.005  |    0.0086 |    0.0224 |
| educacion          | 462 |    7.326  |   1.1088 |   4.8451 |    6.545  |    7.2295 |    8.0781 |   10.6092 |
| densidad           | 462 |  247.949  | 749.166  |   0.6402 |   11.8419 |   56.3597 |  104.531  | 4405.03   |
| informalidad       | 462 |   59.7833 |  12.146  |  35.7974 |   52.7742 |   57.5944 |   66.9388 |   83.3333 |
| IIF                | 462 |    0.3368 |   0.1863 |   0.0001 |    0.1894 |    0.327  |    0.4593 |    1.0001 |
| log_IIF            | 462 |   -1.305  |   0.808  |  -9.2103 |   -1.6637 |   -1.1178 |   -0.778  |    0.0001 |


|   anio |   N |   IIF_prom |   crec_pib |   crec_pib_pc |   log_IIF |
|-------:|----:|-----------:|-----------:|--------------:|----------:|
|   2017 |  33 |     0.2634 |     0.6963 |      nan      |   -1.7508 |
|   2018 | 132 |     0.2799 |     1.7406 |        0.8636 |   -1.5093 |
|   2019 | 132 |     0.3371 |     2.9067 |        0.4264 |   -1.2788 |
|   2020 | 132 |     0.3856 |    -7.6505 |       -3.0168 |   -1.1039 |
|   2021 |  33 |     0.4405 |    10.5685 |       16.8591 |   -0.9515 |

## Verificación contra el documento

| item                                   |   obtenido |   documento | estado          | nota                                        |
|:---------------------------------------|-----------:|------------:|:----------------|:--------------------------------------------|
| D1 pib_percapita distintos por depto   |     5      |             | DIAGNÓSTICO     | 5≈anual repetido / 14≈trimestral            |
| D1 fracción crec_pib(t)==crec_pib(t-1) |     0.6429 |             | DIAGNÓSTICO     | 0.75 ⇒ dependiente sin variación trimestral |
| D1 fracción crec_pib_pc == 0           |     0.6429 |             | DIAGNÓSTICO     | 0.75 ⇒ log-diff nulo dentro del año         |
| KMO                                    |     0.7189 |      0.7189 | OK              |                                             |
| Bartlett chi2                          |  2543.45   |   2543.45   | OK              |                                             |
| Varianza acumulada 4 PC                |    84.4219 |     84.4    | OK              |                                             |
| Corr orientación IIF~cuentas           |     0.8684 |      0.8684 | OK              |                                             |
| Tabla6 A1 β                            |    20.864  |     31.1133 | DISCREPA        |                                             |
| Tabla6 A1 SE                           |     5.9913 |      6.6263 | DISCREPA        |                                             |
| Tabla6 A1 N                            |   429      |    396      | DISCREPA        |                                             |
| Tabla6 A2 β                            |    57.8769 |     62.4924 | DISCREPA        |                                             |
| Tabla6 A2 SE                           |     7.6273 |      8.3614 | DISCREPA        |                                             |
| Tabla6 A2 N                            |   396      |    363      | DISCREPA        |                                             |
| Tabla6 A3 β                            |     0.3579 |     -0.147  | DISCREPA        |                                             |
| Tabla6 A3 SE                           |     6.2724 |      7.2027 | DISCREPA        |                                             |
| Tabla6 A3 N                            |   396      |    363      | DISCREPA        |                                             |
| Tabla6 A4 β                            |    -8.4388 |             | SIN DATO EN DOC |                                             |
| Tabla6 A4 SE                           |     6.9623 |             | SIN DATO EN DOC |                                             |
| Tabla6 A4 N                            |   429      |             | SIN DATO EN DOC |                                             |
| Tabla6 B1 β                            |     3.0349 |      5.7043 | DISCREPA        |                                             |
| Tabla6 B1 SE                           |     4.8141 |      5.5871 | DISCREPA        |                                             |
| Tabla6 B1 N                            |   462      |    429      | DISCREPA        |                                             |
| Tabla6 B2 β                            |    35.5537 |     35.5537 | OK              |                                             |
| Tabla6 B2 SE                           |     5.9553 |      9.5553 | DISCREPA        |                                             |
| Tabla6 B2 N                            |   429      |    429      | OK              |                                             |
| Tabla6 B3 β                            |    25.8399 |     28.5079 | DISCREPA        |                                             |
| Tabla6 B3 SE                           |     4.9779 |      4.8183 | DISCREPA        |                                             |
| Tabla6 B3 N                            |   429      |    396      | DISCREPA        |                                             |
| Tabla6 B4 β                            |    -5.7504 |     -4.9256 | DISCREPA        |                                             |
| Tabla6 B4 SE                           |     4.2043 |      4.358  | DISCREPA        |                                             |
| Tabla6 B4 N                            |   429      |    396      | DISCREPA        |                                             |
| Hausman chi2                           |   292.774  |     33.93   | DISCREPA        |                                             |
| Mundlak IIF_mean                       |     6.796  |      4.11   | DISCREPA        | doc=4.11 | inicial=1.85 | correcciones=6.77 |
| Corr between                           |     0.1201 |      0.094  | DISCREPA        |                                             |
| Corr within                            |    -0.1532 |     -0.164  | OK              |                                             |
| rho Nickell (agregado)                 |     0.4279 |      0.4279 | OK              | el documento usa el ρ del modelo AGREGADO   |
| Pre-COVID β                            |    -1.058  |      0.12   | DISCREPA        |                                             |
| Pre-COVID R²                           |     0.4733 |      0.576  | DISCREPA        |                                             |
| Pesaran CD                             |    69.1165 |     66.81   | OK              |                                             |
| β semi-elasticidad log                 |     8.1401 |      5.344  | DISCREPA        |                                             |

**TOTAL DISCREPANCIAS: 25**

