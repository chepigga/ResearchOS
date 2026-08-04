# XAU_POOL_SELECTION_LAB_001 — ДОДАТОК C
## Умови входу, витягнуті з коду

Джерело: `github.com/AlexWan/OsEngine`, `master`, `project/OsEngine/Robots/`
Дата: 2026-08-03

Це **фактичні тіла `LogicOpenPosition()`**, не опис за назвою.

---

## TREND

### `T_PRICECHANNEL` — `Trend/PriceChannelTrade.cs`
```
якщо high > PC_up І low < PC_down  ->  СИГНАЛУ НЕМАЄ (обидві межі пробиті)
high > PC_up   ->  BUY   (ліміт close + slippage)
low  < PC_down ->  SELL  (ліміт close − slippage)
PriceChannel: Length up 21, Length down 21
```
Умова взаємовиключення — важлива, я її раніше не фіксував.

### `T_ENVELOPE` — `Trend/EnvelopTrend.cs`
```
BuyAtStop  на рівні Envelop.Upper,  StopActivateType.HigherOrEqual
SellAtStop на рівні Envelop.Lower,  StopActivateType.LowerOrEqual
Envelops: Length 10, Deviation 0.3
```
**⚠ Це СТОП-ОРДЕР**, а не маркет чи ліміт. Тобто геометрія, яку
користувач фальсифікував тричі (adverse selection, AK47_AI_V3 −106R,
AK47_Breakout, теорема EURUSD H1).

### `T_LINREG` — `Trend/BreakLinearRegressionChannel.cs`
```
close > upChannel   ->  BuyAtMarket
close < downChannel ->  SellAtMarket
LinReg: Period 50, Deviation 1
фільтри SMA і нахилу: OFF за замовчуванням
```

### `T_PSAR` — `Trend/ParabolicSarTrade.cs`
```
price > SAR  ->  BUY
price < SAR  ->  SELL
ParabolicSAR: Af 0.02, MaxAf 0.2
```
Сигнал є **на кожному барі**, поки ціна з одного боку SAR. Це не
подія перетину — потрібна дедуплікація, інакше сигнал безперервний.

### `T_MACD_MOM` — `Trend/MomentumMacd.cs`
```
MacdLine > MacdSignal  І  Momentum > 100  ->  BUY
MacdLine < MacdSignal  І  Momentum < 100  ->  SELL
Momentum Period 5 | Macd 12/26/9
```
**Momentum в OsEngine нормований навколо 100**, не навколо 1.

### `T_SMA_STOCH` — `Trend/SmaStochastic.cs`
```
close > Sma + Step  І  Stoch[t−1] <= 30  І  Stoch[t] >= 30   ->  BUY
close < Sma − Step  І  Stoch[t−1] >= 70  І  Stoch[t] <= 70   ->  SELL
Sma Length 14 | Stochastic 5/3/3 | Upline 70 | Downline 30 | Step = 500
```
**⚠ `Step = 500` у пунктах інструменту.** Для XAU це 5.00 USD.
Значення зашите в коді (`Step = 500`), не параметр.

### `T_ALLIGATOR` — `Trend/StrategyBillWilliams.cs`
```
price > AlligatorUp І price > AlligatorMiddle І price > AlligatorDown
І price > FractalUp  ->  BUY
Alligator: Fast 3, Middle 10, Slow 40 | Fractal
```
Робот має додатковий часовий фільтр `Hour >= 11 && Hour <= 18`, але
**лише для довходів**, не для першого входу.

---

## COUNTERTREND

### `C_BOLLINGER` — `CounterTrend/StrategyBollinger.cs`
```
close > BB_upper  ->  SELL
close < BB_lower  ->  BUY
Bollinger: Length 21, Deviation 2
```
Sma(15) створюється, але **в умові входу не використовується**.

### `C_RSI` — `CounterTrend/RsiContrtrend.cs`
```
Sma > close  І  RSI > upline   ->  SELL
Sma < close  І  RSI < downline ->  BUY
Rsi Length 20 | Sma Length 50 | upline 70 | downline 30 (конвенція)
```
Логіка непроста: продаж вимагає `RSI > 70` **і** ціну **нижче** SMA.
Тобто перекупленість при низхідній структурі.

### `C_WILLIAMS` — `CounterTrend/WilliamsRangeTrade.cs`
```
WR < −80  ->  BUY
WR > −20  ->  SELL
WilliamsRange Period 14
```

### `C_PIVOT` — `Patterns/PivotPointsRobot.cs`
```
close > R1  І  open < R1  ->  BUY
close < S1  І  open > S1  ->  SELL
PivotFloor
```
Це **пробій рівня всередині бару**, не контртренд. Класифікацію
треба виправити: механіка належить до TREND.

---

## PATTERN

### `P_PINBAR` — `Patterns/PinBarTrade.cs`
```
close >= high − (high−low)/3  І  open >= high − (high−low)/3
І  Sma < close                                  ->  BUY
дзеркально для SELL
Sma Length 14
```

### `P_3SOLDIER` — `Patterns/ThreeSoldier.cs`
```
|open[t−2] − close[t]| / (close[t]/100)  >=  1.0     сумарна висота %
кожна з трьох свічок: |open − close| / (close/100) >= 0.2
усі три одного напрямку                             ->  BUY / SELL
Height soldiers % = 1.0 | Min height one soldier % = 0.2
```

### `P_TURNAROUND` — `PositionsMicromanagement/CandlesTurnaroundPattern.cs`
```
body[t] > 0.3 × ATR(25)  І  body[t−1] > 0.3 × ATR(25)
І  свічка[t] бичача  І  свічка[t−1] ведмежа        ->  BUY
```
**Тільки BUY.** У коді немає дзеркальної SELL-гілки.

### `P_IMPULSE` — `Patterns/CustomCandlesImpulseTrader.cs`
```
2 свічки поспіль одного напрямку
І  (TimeStart[t] − TimeStart[t−2]) <= 120 секунд     ->  BUY / SELL
Candles count 2 | Seconds 120
```
**Працює тільки на M1** (2 бари M1 = рівно 120 с). Додано M1 до ТФ
цієї механіки за рішенням користувача.
Застереження: вартість виконання на M1 = 18% від R (виміряно).

---

## VOLATILITY — ⚠ КЛАС РОЗСИПАВСЯ

### `V_ATR_EXP` — `PriceChannelTrendAtrFilter.cs`
```
price > PriceChannel_up(50)
І  ATR[t] / (ATR[t−20]/100) − 100  >=  3.0        ->  BuyAtMarket
PriceChannel 50 | Atr length 25 | grow 3% | lookback 20
```

### `V_STAGES` — `BollingerTrendVolatilityStagesFilter.cs`
```
price > lastPcUp                     ← PriceChannel, НЕ Bollinger
І  VolatilityStages[t−1] == заданій стадії        ->  BuyAtMarket
```
**Назва файлу вводить в оману** — у коді використовується
`PriceChannel`, а не Bollinger.

### `V_KELTNER` — `FuturesStart/FuturesStart2Keltner.cs`
```
futuresLastPrice > Keltner.Upper
І  contango stage == заданій                       ->  BuyAtIcebergMarket
```
**Непридатне.** Робот працює з ф'ючерсною кривою (контанго),
джерелом `futuresSource` і айсберг-ордерами. На спот-XAU не переноситься.

---

# ТРИ ПРОБЛЕМИ ДО ВИРІШЕННЯ

## Проблема 1 — клас VOLATILITY не існує

Усі три механіки — це **пробій PriceChannel із різними фільтрами**:

```
T_PRICECHANNEL  PriceChannel(21), без фільтра
V_ATR_EXP       PriceChannel(50) + фільтр розширення ATR
V_STAGES        PriceChannel + фільтр стадії волатильності
V_KELTNER       непридатне (ф'ючерси)
```

Це порушує принцип Додатку A: не включати параметричні клони.

**Варіанти:**

**(A)** Виключити V_ATR_EXP і V_STAGES як клони, V_KELTNER як непридатне.
Клас VOLATILITY зникає. Залишається **15 механік**.

**(B)** Залишити V_ATR_EXP і V_STAGES. Аргумент: фільтр змінює **коли**
механіка спрацьовує, і фіча співпадіння «PC спрацював сам» vs
«PC спрацював при розширенні ATR» інформативна. Але вони будуть
сильно корельовані з T_PRICECHANNEL.

**(C)** Замінити V_KELTNER на самостійний пробій Keltner(20, 2×ATR)
без ф'ючерсної обв'язки. Це буде **моя конструкція**, не з каталогу.

## Проблема 2 — `T_ENVELOPE` на стоп-ордерах

Єдина механіка пулу зі стоп-входом. Це геометрія, фальсифікована
користувачем тричі, з підтвердженим механізмом adverse selection.

**Варіанти:**
**(A)** Залишити як є — пул має відображати каталог, а шар відбору
        сам вирішить, брати її чи ні. Її провал буде інформативним.
**(B)** Виключити як заздалегідь відому фальсифіковану.

Рекомендація: **(A)**. Мета лабораторії — перевірити шар відбору,
а не окремі механіки. Якщо відбір працює, він має навчитись
відкидати T_ENVELOPE самостійно. Це фактично вбудований контроль.

## Проблема 3 — `P_TURNAROUND` тільки BUY

У коді немає SELL-гілки. Пул отримає механіку з однобічним сигналом.

**Варіанти:**
**(A)** Залишити однобічною — точно за кодом.
**(B)** Додзеркалити SELL — моя добудова, не з каталогу.

Рекомендація: **(A)**, за кодом. Асиметрія буде видима у фічах.

---

# ІНШІ ВИЯВЛЕНІ ДЕТАЛІ

```
C_PIVOT      класифікація помилкова: це пробій рівня -> клас TREND
T_PSAR       сигнал безперервний, потрібна дедуплікація по зміні стану
T_MACD_MOM   Momentum нормований навколо 100
T_SMA_STOCH  Step = 500 пунктів зашито в код (для XAU = 5.00 USD)
C_BOLLINGER  Sma(15) створюється, але в умові входу не бере участі
V_STAGES     назва файлу не відповідає коду (PriceChannel, не Bollinger)
```

---

# ЗВЕДЕННЯ

```
підтверджено і готово до реалізації:   12 механік
потребує рішення користувача:           4  (V_ATR_EXP, V_STAGES,
                                            V_KELTNER, T_ENVELOPE)
уточнено класифікацію:                  1  (C_PIVOT -> TREND)
однобічна:                              1  (P_TURNAROUND, тільки BUY)
тільки M1:                              1  (P_IMPULSE)
```

Без рішень по Проблемі 1 склад пулу не визначений, і Крок 1
не може бути виконаний.
