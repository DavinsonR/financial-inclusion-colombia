
## SECCIÓN 0 — Entorno

```text
pandas 1.5.3 · numpy 1.23.5
factor_analyzer disponible: True
Ruta de datos: [ruta local omitida]
✓ Constantes cargadas.
```

## SECCIÓN 2 — Carga de datos

```text
Dimensiones   : (462, 102)
Departamentos : 33
Años          : [2017, 2018, 2019, 2020, 2021]
Columna tiempo: Fecha — 14 valores únicos
Períodos      : [numpy.datetime64('2017-12-01T00:00:00.000000000'), numpy.datetime64('2018-03-01T00:00:00.000000000'), numpy.datetime64('2018-06-01T00:00:00.000000000'), numpy.datetime64('2018-09-01T00:00:00.000000000')] ... [numpy.datetime64('2020-12-01T00:00:00.000000000'), numpy.datetime64('2021-03-01T00:00:00.000000000')]
Variables con NA: 0
```

## DIAGNÓSTICO D1 — Estructura temporal del PIB

```text
pib_percapita          valores distintos por (depto, año): min=1  max=1  media=1.00
pib_crecimiento        valores distintos por (depto, año): min=1  max=1  media=1.00
IPC_pct                valores distintos por (depto, año): min=1  max=1  media=1.00
internet_pct           valores distintos por (depto, año): min=1  max=1  media=1.00
educacion_anios        valores distintos por (depto, año): min=1  max=1  media=1.00
Empleo_Informal        valores distintos por (depto, año): min=1  max=1  media=1.00

Lectura: si max = 1 la variable es ANUAL repetida en los 4 trimestres.
         si max = 4 la variable varía trimestralmente.

pib_percapita — valores distintos por departamento (sobre 14 trimestres):
  min=5  max=5  media=5.00
  (5 ≈ un valor por año; 14 ≈ variación trimestral real)

Fracción de observaciones con crec_pib(t) == crec_pib(t-1): 0.643
  → si ≈ 0.75, el modelo dinámico regresa la variable sobre sí misma en 3 de cada 4 casos.
```

## SECCIÓN 3 — Construcción de variables

```text
Obs totales            : 462
Umbral p75 densidad    : 103.0 hab/km²
Urbanos / Rurales      : 8 / 25
crec_pib     no nulos  : 462
crec_pib_pc  no nulos  : 429
Regiones sin mapear    : 0 obs

Fracción de crec_pib_pc exactamente igual a 0: 0.643
  → si ≈ 0.75, la dependiente per cápita no varía dentro del año.
```

## SECCIÓN 4 — PCA e IIF

```text
[IIF principal] KMO = 0.7189 | Bartlett χ² = 2543.45 (p = 0.0000)
[IIF principal] Componentes retenidos (≥80.0%): 4
   PC1: 46.76%  (acum  46.76%) ◄
   PC2: 17.38%  (acum  64.14%) ◄
   PC3: 13.72%  (acum  77.85%) ◄
   PC4:  6.57%  (acum  84.42%) ◄
   PC5:  6.25%  (acum  90.67%)
   PC6:  3.64%  (acum  94.31%)
   PC7:  2.70%  (acum  97.01%)
   PC8:  1.68%  (acum  98.69%)
   PC9:  1.31%  (acum 100.00%)
[IIF principal] Pesos de los 4 componentes: [0.5539, 0.2058, 0.1625, 0.0778]
[IIF principal] Corr(IIF, cuentas ahorro pc) = 0.8684

Cargas factoriales (componentes retenidos):
                    PC1 (46.8%)  PC2 (17.4%)  PC3 (13.7%)  PC4 (6.6%)
Corresponsales           0.4278      -0.0992       0.1468     -0.1472
Cuentas ahorro           0.3913       0.2576       0.1052      0.1934
Internet (%)             0.3532      -0.0277       0.1355     -0.6643
Pagos digitales          0.4165      -0.0934       0.1446     -0.1993
Transferencias           0.2190      -0.6005      -0.1903      0.3483
Depósitos                0.3567      -0.4085      -0.0832      0.2796
Microcrédito/PIB        -0.0614      -0.1696      -0.7883     -0.4369
Créd. consumo/PIB        0.2717       0.4227      -0.4838      0.2395
Créd. vivienda/PIB       0.3360       0.4234      -0.1718      0.1101
```

## DIAGNÓSTICO D2 — IIF sin internet

```text
[IIF sin internet] KMO = 0.6776 | Bartlett χ² = 2257.39 (p = 0.0000)
[IIF sin internet] Componentes retenidos (≥80.0%): 3
   PC1: 46.91%  (acum  46.91%) ◄
   PC2: 19.54%  (acum  66.44%) ◄
   PC3: 15.24%  (acum  81.69%) ◄
   PC4:  7.17%  (acum  88.85%)
   PC5:  4.39%  (acum  93.24%)
   PC6:  3.27%  (acum  96.52%)
   PC7:  1.97%  (acum  98.49%)
   PC8:  1.51%  (acum 100.00%)
[IIF sin internet] Pesos de los 3 componentes: [0.5742, 0.2392, 0.1866]
[IIF sin internet] Corr(IIF, cuentas ahorro pc) = 0.8903

Corr(IIF, IIF_sin_net) = 0.9933
```

## DIAGNÓSTICO D3 — PCA out-of-sample (pesos de 2017–2019)

```text
[IIF out-of-sample] KMO = 0.7189 | Bartlett χ² = 2543.45 (p = 0.0000)
[IIF out-of-sample] Componentes retenidos (≥80.0%): 4
   PC1: 44.98%  (acum  44.98%) ◄
   PC2: 18.12%  (acum  63.10%) ◄
   PC3: 12.65%  (acum  75.75%) ◄
   PC4:  8.66%  (acum  84.41%) ◄
   PC5:  7.40%  (acum  91.81%)
   PC6:  3.80%  (acum  95.61%)
   PC7:  2.23%  (acum  97.84%)
   PC8:  1.28%  (acum  99.12%)
   PC9:  0.88%  (acum 100.00%)
[IIF out-of-sample] Pesos de los 4 componentes: [0.5328, 0.2147, 0.1499, 0.1026]
[IIF out-of-sample] Corr(IIF, cuentas ahorro pc) = 0.8774

Corr(IIF, IIF_oos) = 0.9947
  → si la correlación es alta (>0.95) el look-ahead no altera el ordenamiento.
```

## SECCIÓN 5 — Panel econométrico (construcción corregida de rezagos)

```text
Entidades : 33
Períodos  : 14
Obs base  : 462

Trazabilidad de la muestra (todos los rezagos vienen del panel de 462):
  crec_pib + IIF                       :  462 obs
  crec_pib + IIF_lag1 + crec_pib_lag1  :  429 obs
  crec_pib_pc + IIF                    :  429 obs
  crec_pib_pc + IIF_lag1 + lag DV      :  396 obs
  crec_pib_pc + IIF_lag2 + lag DV      :  396 obs
```

## SECCIÓN 7 — TABLA 6 consolidada

```text
BLOQUE A — DV: crecimiento del PIB per cápita
  A1 FE-Est   | IIF                                β= +20.8640*** SE= 5.9913 p=0.0006 N= 429 R²=0.0239
  A2 FE-Dyn   | IIF_lag1                           β= +57.8769*** SE= 7.6273 p=0.0000 N= 396 R²=0.1160
  A3 2way FE  | IIF_lag1  ← REFERENCIA             β=  +0.3579    SE= 6.2724 p=0.9545 N= 396 R²=0.0058
  A4 2way FE  | IIF       ← FALTABA                β=  -8.4388    SE= 6.9623 p=0.2262 N= 429 R²=0.0075

BLOQUE B — DV: crecimiento del PIB agregado
  B1 FE-Est   | IIF                                β=  +3.0349    SE= 4.8141 p=0.5288 N= 462 R²=0.0708
  B2 FE-Dyn   | IIF_lag1                           β= +35.5537*** SE= 5.9553 p=0.0000 N= 429 R²=0.1992
  B3 FE-Dyn   | IIF_PC1_lag1                       β= +25.8399*** SE= 4.9779 p=0.0000 N= 429 R²=0.1955
  B4 2way FE  | IIF_lag1                           β=  -5.7504    SE= 4.2043 p=0.1722 N= 429 R²=0.1907

Comparación entity vs two-way SOBRE LA MISMA MUESTRA:
  Bloque A (per cápita): entity β=+57.8769 (N=396) → two-way β= +0.3579 (N=396)  | ΔR² = -0.1103
  Bloque B (agregado)  : entity β=+35.5537 (N=429) → two-way β= -5.7504 (N=429)  | ΔR² = -0.0085
```

## SECCIÓN 8 — Hausman, Mundlak, descomposición

```text
Hausman: χ²(6) = 292.7736, p = 0.0000, N = 429
Mundlak: β_within = +17.2638 (p=0.0000) | β_mean = +6.7960 (p=0.0615)
Corr between = +0.1201 | Corr within = -0.1532
```

## SECCIÓN 9 — Sesgo de Nickell

```text
PIB agregado : ρ̂ = +0.4279 | sesgo ≈ -0.1098 | ρ corregido ≈ +0.5377 |  25.7% de ρ̂
PIB per cápita: ρ̂ = +0.1314 | sesgo ≈ -0.0870 | ρ corregido ≈ +0.2184 |  66.2% de ρ̂
```

## SECCIÓN 10 — Robustez

```text
[10a] Submuestra pre-pandemia 2017–2019
  Pre-COVID | FE Entity                            β=  -1.0580    SE= 2.0690 p=0.6096 N= 264 R²=0.4733
  Pre-COVID | two-way                              β=  -7.9795    SE= 5.7312 p=0.1652 N= 264 R²=0.4558

[10b] Pesaran CD (dependencia transversal)
CD = 69.1165, p = 0.0000  (N=33, T medio=13.0)

[10c] Driscoll-Kraay
  FE Entity | DK SE                                β= +35.5537    SE=37.0221 p=0.3375 N= 429 R²=0.1992
  SE clustered = 5.9553  →  DK = 37.0221

[10d] Outliers sobre la dependiente
  Trimming 1%                                      β= +30.2266*** SE= 6.0886 p=0.0000 N= 420 R²=0.3048
  Winsorización 5%                                 β= +28.6497*** SE= 5.2424 p=0.0000 N= 429 R²=0.2461

[10e] Autocorrelación serial de los residuos (Wooldridge)
r(e_t, e_t-1) = 0.1279, p = 0.0109

[10f] Especificaciones alternativas del índice y del rezago
  IIF_lag2      | PIB pc                           β= +25.7220**  SE=10.1110 p=0.0114 N= 396 R²=0.0260
  IIF_lag2 2way | PIB pc                           β=  +2.0966    SE= 5.5865 p=0.7077 N= 396 R²=0.0060
  IIF sin internet | PIB pc  (D2)                  β= +57.7779*** SE= 7.1292 p=0.0000 N= 396 R²=0.1262
  IIF sin internet 2way | PIB pc  (D2)             β=  +4.6279    SE= 4.1289 p=0.2631 N= 396 R²=0.0068
  IIF out-of-sample | PIB pc (D3)                  β= +63.4259*** SE= 7.7934 p=0.0000 N= 396 R²=0.1396
  IIF out-of-sample 2way | PIB pc (D3)             β=  +1.6526    SE= 5.6106 p=0.7685 N= 396 R²=0.0059

[10g] Tendencias lineales por departamento (alternativa a TimeEffects)
  FE Entity + tendencia t_idx                      β= +45.4128*** SE= 5.6740 p=0.0000 N= 429 R²=0.2066

[10h] Semi-elasticidad logarítmica
  log(IIF)_lag1 | PIB pc                           β=  +8.1401*** SE= 1.9488 p=0.0000 N= 396 R²=0.0548
  β_log = 8.1401 → +1% IIF = 0.0810 pp | +10% IIF = 0.7758 pp
```

## SECCIÓN 11 — Heterogeneidad regional

```text
  Andina                                           β= +23.2643**  SE= 9.1796 p=0.0125 N= 143 R²=0.1854
  Caribe                                           β= +72.2255*** SE=23.5630 p=0.0029 N= 104 R²=0.2379
  Pacífica                                         β= +58.5644*** SE= 8.3576 p=0.0000 N=  52 R²=0.3711
  Orinoquía                                        β= +16.4008    SE=12.7984 p=0.2071 N=  52 R²=0.5127
  Amazonía                                         β= +50.9128*** SE=13.6983 p=0.0004 N=  78 R²=0.3338

Suma de observaciones regionales : 429
N del modelo principal (B2)      : 429.0
N del modelo de referencia (A3)  : 396.0

   Region    beta      se      p   N  N_dep
   Andina 23.2643  9.1796 0.0125 143     11
   Caribe 72.2255 23.5630 0.0029 104      8
 Pacífica 58.5644  8.3576 0.0000  52      4
Orinoquía 16.4008 12.7984 0.2071  52      4
 Amazonía 50.9128 13.6983 0.0004  78      6
```

## SECCIÓN 12 — Descriptivas

```text
Tabla 1 — descriptivas del panel
                      N      mean      std      min       25%       50%       75%       max
crec_pib            462   -0.0534   6.1492 -23.5692   -5.1428    1.9773    3.0811   28.0755
crec_pib_pc         429    0.7655   6.6442 -32.8543    0.0000    0.0000    0.0000   47.2285
log_fintech_pc      462    7.7952   0.6841   4.7084    7.4652    7.8297    8.2795    9.2246
d_acc_corresp       462   39.6841  21.1131   5.6216   24.0080   36.7208   50.6484  111.9558
d_acc_cta_ah        462 1976.6375 955.1350 496.6644 1285.6097 1787.1230 2503.0593 5079.6418
d_acc_internet      462   34.6916  22.0040   0.0000   17.0000   36.0500   54.0000   81.5249
d_uso_pagos_pc      462 1289.5529 957.9251  48.9249  567.4883 1006.0355 1957.6247 4414.2741
d_uso_transf_pc     462   50.3143  41.1467   0.7834   22.7488   37.6182   63.9801  225.1057
d_uso_depositos_pc  462  796.4310 450.8251  44.4973  486.5092  693.2047  976.7366 3177.1484
d_pro_micro         462    0.0059   0.0042   0.0005    0.0031    0.0044    0.0072    0.0212
d_pro_cred_cons     462    0.0411   0.0213   0.0011    0.0249    0.0394    0.0557    0.1098
d_pro_cred_viv      462    0.0058   0.0045   0.0000    0.0020    0.0050    0.0086    0.0224
educacion           462    7.3260   1.1088   4.8451    6.5450    7.2295    8.0781   10.6092
densidad            462  247.9491 749.1658   0.6402   11.8419   56.3597  104.5306 4405.0304
informalidad        462   59.7833  12.1460  35.7974   52.7742   57.5944   66.9388   83.3333
IIF                 462    0.3368   0.1863   0.0001    0.1894    0.3270    0.4593    1.0001
log_IIF             462   -1.3050   0.8080  -9.2103   -1.6637   -1.1178   -0.7780    0.0001

Tabla 2 — evolución anual
        N  IIF_prom  crec_pib  crec_pib_pc  log_IIF
anio                                               
2017   33    0.2634    0.6963          NaN  -1.7508
2018  132    0.2799    1.7406       0.8636  -1.5093
2019  132    0.3371    2.9067       0.4264  -1.2788
2020  132    0.3856   -7.6505      -3.0168  -1.1039
2021   33    0.4405   10.5685      16.8591  -0.9515
```

## SECCIÓN 13 — Verificación contra el documento

```text
                                  item   obtenido  documento          estado                                        nota
  D1 pib_percapita distintos por depto     5.0000                DIAGNÓSTICO            5≈anual repetido / 14≈trimestral
D1 fracción crec_pib(t)==crec_pib(t-1)     0.6429                DIAGNÓSTICO 0.75 ⇒ dependiente sin variación trimestral
          D1 fracción crec_pib_pc == 0     0.6429                DIAGNÓSTICO         0.75 ⇒ log-diff nulo dentro del año
                                   KMO     0.7189     0.7189              OK                                            
                         Bartlett chi2 2,543.4502 2,543.4500              OK                                            
               Varianza acumulada 4 PC    84.4219    84.4000              OK                                            
          Corr orientación IIF~cuentas     0.8684     0.8684              OK                                            
                           Tabla6 A1 β    20.8640    31.1133        DISCREPA                                            
                          Tabla6 A1 SE     5.9913     6.6263        DISCREPA                                            
                           Tabla6 A1 N   429.0000   396.0000        DISCREPA                                            
                           Tabla6 A2 β    57.8769    62.4924        DISCREPA                                            
                          Tabla6 A2 SE     7.6273     8.3614        DISCREPA                                            
                           Tabla6 A2 N   396.0000   363.0000        DISCREPA                                            
                           Tabla6 A3 β     0.3579    -0.1470        DISCREPA                                            
                          Tabla6 A3 SE     6.2724     7.2027        DISCREPA                                            
                           Tabla6 A3 N   396.0000   363.0000        DISCREPA                                            
                           Tabla6 A4 β    -8.4388            SIN DATO EN DOC                                            
                          Tabla6 A4 SE     6.9623            SIN DATO EN DOC                                            
                           Tabla6 A4 N   429.0000            SIN DATO EN DOC                                            
                           Tabla6 B1 β     3.0349     5.7043        DISCREPA                                            
                          Tabla6 B1 SE     4.8141     5.5871        DISCREPA                                            
                           Tabla6 B1 N   462.0000   429.0000        DISCREPA                                            
                           Tabla6 B2 β    35.5537    35.5537              OK                                            
                          Tabla6 B2 SE     5.9553     9.5553        DISCREPA                                            
                           Tabla6 B2 N   429.0000   429.0000              OK                                            
                           Tabla6 B3 β    25.8399    28.5079        DISCREPA                                            
                          Tabla6 B3 SE     4.9779     4.8183        DISCREPA                                            
                           Tabla6 B3 N   429.0000   396.0000        DISCREPA                                            
                           Tabla6 B4 β    -5.7504    -4.9256        DISCREPA                                            
                          Tabla6 B4 SE     4.2043     4.3580        DISCREPA                                            
                           Tabla6 B4 N   429.0000   396.0000        DISCREPA                                            
                          Hausman chi2   292.7736    33.9300        DISCREPA                                            
                      Mundlak IIF_mean     6.7960     4.1100        DISCREPA doc=4.11 | inicial=1.85 | correcciones=6.77
                          Corr between     0.1201     0.0940        DISCREPA                                            
                           Corr within    -0.1532    -0.1640              OK                                            
                rho Nickell (agregado)     0.4279     0.4279              OK   el documento usa el ρ del modelo AGREGADO
                           Pre-COVID β    -1.0580     0.1200        DISCREPA                                            
                          Pre-COVID R²     0.4733     0.5760        DISCREPA                                            
                            Pesaran CD    69.1165    66.8100              OK                                            
                β semi-elasticidad log     8.1401     5.3440        DISCREPA                                            

TOTAL DISCREPANCIAS: 25

                  item obtenido documento                                        nota
           Tabla6 A1 β  20.8640   31.1133                                            
          Tabla6 A1 SE   5.9913    6.6263                                            
           Tabla6 A1 N 429.0000  396.0000                                            
           Tabla6 A2 β  57.8769   62.4924                                            
          Tabla6 A2 SE   7.6273    8.3614                                            
           Tabla6 A2 N 396.0000  363.0000                                            
           Tabla6 A3 β   0.3579   -0.1470                                            
          Tabla6 A3 SE   6.2724    7.2027                                            
           Tabla6 A3 N 396.0000  363.0000                                            
           Tabla6 B1 β   3.0349    5.7043                                            
          Tabla6 B1 SE   4.8141    5.5871                                            
           Tabla6 B1 N 462.0000  429.0000                                            
          Tabla6 B2 SE   5.9553    9.5553                                            
           Tabla6 B3 β  25.8399   28.5079                                            
          Tabla6 B3 SE   4.9779    4.8183                                            
           Tabla6 B3 N 429.0000  396.0000                                            
           Tabla6 B4 β  -5.7504   -4.9256                                            
          Tabla6 B4 SE   4.2043    4.3580                                            
           Tabla6 B4 N 429.0000  396.0000                                            
          Hausman chi2 292.7736   33.9300                                            
      Mundlak IIF_mean   6.7960    4.1100 doc=4.11 | inicial=1.85 | correcciones=6.77
          Corr between   0.1201    0.0940                                            
           Pre-COVID β  -1.0580    0.1200                                            
          Pre-COVID R²   0.4733    0.5760                                            
β semi-elasticidad log   8.1401    5.3440                                            
```

## SECCIÓN 14 — Exportación

```text
Filas de verificación: 40
```
