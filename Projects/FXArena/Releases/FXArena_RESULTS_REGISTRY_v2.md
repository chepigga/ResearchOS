# FXArena RESULTS REGISTRY v2
# 2026-07-23 | Замінює FXArena_RESULTS_REGISTRY.md (v1 — видалити/ігнорувати)
# Правило: сесія отримує цей файл зі спекою; бейзлайни цитуються ТІЛЬКИ
# звідси; зайняте ім'я = тільки цей об'єкт; новий об'єкт = нове ім'я + рядок.

=====================================================================
1. КАНОН / LIVE
=====================================================================
[C2] — канонічна модель ContPrimary
  Universe: 291 659 outcomes (EURUSD M5 touch, 2023-01→2026-07-17,
  state!=0, right_censored==0) | TP1.0 / TO120 / MICRO30
  42 monthly-WF × 48 фіч, економ-лейбл y=(net_R>0), top-4%
  Loop-еталон 2026-07-20: N=3716 | EV +0.337 | PF ~2.3 | DD 15.1R |
  0/42 | найгірший +5.1R
  Статус: CANON. Задеплоєно = FXArena_ContPrimary v1.20, demo-форвард
  з 2026-07-20, NON-CANON до серпневого E-екзамену v005.

[C2-MINSTOP30] деплой-бенчмарк EA: EV +0.348 | DD 14.5R (не контроль)
[C2-REGEN] регенерація v009-сесії: N=3715 (±1, tie-boundary н/л),
  EV +0.3334 | +1238.6R | PF 2.29 | DD 14.99 | 0/42 | parity max 1.43e-6
  Статус: PASS як research-контроль, НЕ біт-еталон.
[C2-OLDREF] старий референс: +0.281 | PF 2.07 | DD 15.0 (історія)

=====================================================================
2. ВАЛІДОВАНІ КАНДИДАТИ
=====================================================================
[GEO*] — v009 GeoSweep (2026-07-22): C2-universe + та сама селекція,
  MICRO30 / TP2.0 / TO120, модель перенавчена під лейбл.
  N=3544 | +1856.4R | EV +0.524 | PF 2.85 | DD 14.42R | 1/42 (-0.22R)
  GS1-GS6 PASS (rev-chrono 3.2%; permutation-200 всі null негативні)
  Множина угод: trades_MICRO30_TP2_TO120.csv.gz (v009)
  Статус: validated candidate v1.30 ПІСЛЯ серпневого екзамену.
  Execution caveat: cost/stop median 0.078R, p95 0.233R; 49% виходів
  по timeout. Ім'я GEO* — тільки цей об'єкт.
[GEO*-CONS] — MICRO30/TP1.5/TO120: +1582.0R | EV +0.442 | DD 14.14

=====================================================================
3. TB-ЛІНІЯ (= дослідження EXIT-менеджменту на GEO*-входах)
=====================================================================
[TB-UNIVERSE] = 3544 канонічні GEO*-угоди (TB v002 Universe Fixed).
  Перекриття з GEO*/ContPrimary у live: 100% (ті самі входи).
  Історичне: TB v001 "2939" = OS-OOS підмножина GEO* (пропуск
  місяців train_n<500) — ім'я [TB-2939-DEPRECATED], не цитувати.
[TB-TP8-BASE] TP8/24h/MICRO30 на 3544: EV +0.425 | +1506.8R |
  DD 94.2R | hit 9.5%. TP5: +0.344/DD 72.2. TP12: +0.440/DD 123.7.
  ВИСНОВОК: повне домінування GEO* (EV, total, DD) — flat TP8/12
  замість TP2 = FALSIFIED (F7). Живе тільки умовна гілка:
[TB-FILTERS] топ (best-of-40, winner's curse до pre-reg валідації):
  EFFICIENCY_5 N=1021 EV +0.783 lift +0.358 PF 2.08 4/4
  BB_EXPANSION N=570 +0.739 | RANGE_EXPANSION_15 N=451 +0.727
  FRACTAL_BREAK N=903 +0.602 | DONCHIAN20 N=628 +0.538
  Slippage-стрес: edge живий при 2pt. Per-filter DD: НЕ звітований.
  Paired TP8-vs-TP2 на підмножинах: ВІДСУТНІЙ (ключова дірка).
[TB-NO-GO] standalone ADX (lift -0.09..-0.30) / Holy Grail (-0.194) /
  MACD-zero / SMA-tunnel як TB-детектори — локально для TB-universe.
[MG-v001] MarketGeometry: geometry-score бакети монотонні
  (ALL_OOS 2626 EV +0.449; TOP_10 +1.375 N=232), leakage PASS
  (60m excluded). Статус: PoC, без risk-шару.
[OS-PROTO] шарова pre-entry архітектура на [TB-2939-DEPRECATED]-
  бейзлайні (там названо "GEO*" — помилка імені): os_score AUC 0.621
  (p_htf 0.612, базовий p 0.511); дельта +75.7R / EV +0.026 /
  DD +0.57R — significance не міряна. Статус: architecture-PoC.

=====================================================================
4. ЦІЛЬОВА АРХІТЕКТУРА (FXArena OS) І МАПІНГ
=====================================================================
Feature Layer -> Statistical Model -> Entry -> Execution -> Risk
  Feature Layer: 48 фіч C2 (+tk1-tk8 у v010; +geometry/expansion TB)
  Statistical Model: WF p_win (розширення: Expected Move/MAE/MFE —
    RegressionHeads Lab, черга)
  Entry: ContPrimary D3+60s (альтернативи — ExecutionEntry Lab, черга)
  Execution: ExecutionCore v001 (v1.1 після форвард-місяця),
    ExecutionReplay v002 (тіковий, у черзі)
  Risk: frozen risk-шар v1.00 (0.25%, day-cap 6, cooldown 2->12h)
Принцип (TB-вердикт): класика = сенсори контексту / фічі,
  НЕ голосуючі entry-модулі. "Етап 3" подкаст-плану (Holy Grail/Kumo/
  TDI ансамбль) — ЗАМІНЕНО TB-вердиктом, не реанімувати.

=====================================================================
5. FALSIFIED (глобальний каталог)
=====================================================================
F1 state-label для cont-відбору (S2R#1: AUC 0.856 -> EV -0.098)
F2 sequential online-детекція резолюції як entry (v008)
F3 AUC як критерій успіху battle-моделі
F4 M15-скальпінг EURUSD (кости)
F5 H1-структурний стоп у DD-межах (v009)
F6 timeout >= 360 хв та "без timeout" на C2-universe (v009)
F7 flat TP8/TP12 замість TP2 на GEO*-множині (TB v002: DD 94-124R)

=====================================================================
6. ЧЕРГА (пріоритет зверху вниз)
=====================================================================
0. Форвард-нагляд ContPrimary v1.20 (щоденно; THR 0.61-0.67,
   opens 3-6/д, slip_pts для E4; INIT_OK підтвердити) — верхній суддя
1. v009b TimeoutSweep — FROZEN, НЕ ЗАПУЩЕНО. Блокує геометрію для
   v010 / HybridExit / v1.30. Запустити першим (6 клітинок, години).
2. GitHub реліз v1.1 — БОРГ: C2-артефакти + v009 (звіт, таблиця,
   ваги GEO*, trades) + TB v002 outputs. Без залежностей.
3. Після вердикту v009b (GEO*/GEO**) — вибір одного:
   a) v010 TickFeatures/C3 (ТЗ заморожене; paired sub-period
      2025-01+ через тікове покриття)
   b) RegressionHeads Lab (Expected Move/MAE/MFE -> адаптивний стоп
      + вибір exit-політики per-епізод; ПОГЛИНАЄ HybridExitLab;
      pre-reg фільтри EFFICIENCY_5/BB_EXP/RANGE_EXP_15 як контроль)
   спека b) — не написана.
4. ExecutionEntry Lab (market vs limit vs retracement на GEO*-
   множині) — спека не написана.
5. EurCore-режимна гілка (окрема, не блокується): компіляція
   v4.01R -> тестер 2025-03→2026-07 -> join з battle-індексом
   (CleanRate/TwoSidedRate з interactions v007) vs ADX-бейзлайн.
6. OS-крок-2 (permutation дельти + ваги шарів) — після 3.
7. ExecutionReplay v002 (тіковий, для серпневого екзамену) — за
   планом беклогу v7.
Research-пауза S2R-типу знята фактом v009; дисципліна frozen
one-run — чинна для всього.
