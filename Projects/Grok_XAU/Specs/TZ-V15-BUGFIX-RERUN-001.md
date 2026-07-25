# ТЗ-V15-BUGFIX-RERUN-001 — переоцінка AK47-UPD (V15) після виправлення OCO/ticket-select/STOPLEVEL багів
**Дата:** 2026-07-25
**Статус:** ЗАМОРОЖЕНЕ ТЗ (pre-registered). Правки після контакту з даними ЗАБОРОНЕНІ.
**Базується на:** AK47_VARIANTS_001 (2026-07-25, V15 M15 pass-rate 62%, actual нижче permutation p95, hedge fills 1495-1599).

## 1. Що змінилось (і що НІ)
Джерело: `AK47-UPD_V15_1_BUGFIX.mq5` (v15.1). Три виправлення, нуль змін стратегії:

1. **OCO enforcement**: `if(CountPositions()>0 && CountOrders()>0) DeleteAllOrders();` одразу після `ManagePositions()` в `OnTick()`. Прибирає можливість одночасного філу протилежних pending (раніше: hedge fills).
2. **CountOrders()/CountPositions() ticket-select fix**: додано `OrderGetTicket(i)`/`PositionGetTicket(i)` перед читанням властивостей.
3. **STOPLEVEL/FREEZELEVEL guard** перед SL-modify: якщо нова відстань SL порушує ліміт брокера — modify НЕ надсилається.

**НЕ змінено:** SL/TP (1500/3000), padding (2), risk (1.0%, ×0.5 anti-martingale, streak 3), BE/trailing пороги (15/2, старт 8 крок 3), часове вікно (08-18), відсутність candle-фільтра.

## 2. Двигун і дані
- Той самий M5 tester-stream (sha256 `40175d5d...`), 2022-06-01..2026-07-23, $100,000 старт, $5 RT комісія.
- Primary і mirror path-конвенції.
- TF: M15 і H1 окремо.

## 3. Обов'язкові розрізи
1. N, WR, EV actual-risk, EV base-1%, PF, MaxDD.
2. Hedge fill count.
3. `SL_MODIFY_BLOCKED_STOPLEVEL` frequency.
4. Rolling 14-day pass-rate + permutation p95/mean.
5. Early/late half.
6. Помісячно та по роках.

## 4. Пряме порівняння v15.0 vs v15.1
Обов'язкова таблиця до/після на чотирьох конфігураціях.

## 5. Вердикт-правила
- **CONFIRMED:** EV_actual-risk ≥ +0.05R на всіх 4 конфігураціях, N ≥90, hedge fills <20.
- **DEGRADED:** EV_actual-risk <+0.05R хоча б на одній, але лишається >0.
- **NO-GO:** EV_actual-risk ≤0 на більшості конфігурацій.
- Жоден параметр не змінюється цим ТЗ.

## 6. Артефакти
Trade CSV, comparison, slices, explicit verdict and provenance.
