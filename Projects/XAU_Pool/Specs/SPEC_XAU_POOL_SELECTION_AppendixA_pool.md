# XAU_POOL_SELECTION_LAB_001 — ДОДАТОК A
## Склад пулу генераторів (заморожується разом зі специфікацією)

Джерело: `github.com/AlexWan/OsEngine`, `project/OsEngine/Robots/`
Дата витягу: 2026-08-03

---

## Принцип відбору

**Одна механіка = один генератор.** Параметричні клони об'єднані.

Обґрунтування: у каталозі 91 торговий робот, але `PriceChannelTrade`,
`TwoTimeFramesBot`, `PriceChannelTrendAtrFilter`, `FuturesTrendPriceChannel`,
`PriceChannelAdaptiveRsiScreener` — це **один індикатор** `PriceChannel`
із різними обгортками. Включення всіх п'яти створило б штучну згоду
і зробило б фічі співпадіння беззмістовними.

---

## СКЛАД: 18 механік

### Клас TREND (7)

| # | id | Джерело OsEngine | Правило входу |
|---|---|---|---|
| 1 | `T_PRICECHANNEL` | `Trend/PriceChannelTrade.cs` | `high > PriceChannelUp(20)` → BUY; `low < PriceChannelDown(20)` → SELL |
| 2 | `T_ENVELOPE` | `Trend/EnvelopTrend.cs` | `close` вище верхньої стрічки Envelops(20, 0.5%) → BUY; нижче нижньої → SELL |
| 3 | `T_LINREG` | `Trend/BreakLinearRegressionChannel.cs` | пробій межі каналу лінійної регресії(50) |
| 4 | `T_PSAR` | `Trend/ParabolicSarTrade.cs` | `price > SAR(0.02, 0.2)` → BUY; `price < SAR` → SELL |
| 5 | `T_MACD_MOM` | `Trend/MomentumMacd.cs` | `MacdLine(12,26,9)` і `Momentum(10)` узгоджені за напрямком |
| 6 | `T_SMA_STOCH` | `Trend/SmaStochastic.cs` | `close` відносно `Sma(50)` + вихід `Stochastic(14,3,3)` із зони |
| 7 | `T_ALLIGATOR` | `Trend/StrategyBillWilliams.cs` | `Alligator` розкритий + `AO` за напрямком + пробій `Fractal` |

### Клас COUNTERTREND (4)

| # | id | Джерело | Правило |
|---|---|---|---|
| 8 | `C_BOLLINGER` | `CounterTrend/StrategyBollinger.cs` | `close < BB_lower(20,2)` → BUY; `close > BB_upper` → SELL |
| 9 | `C_RSI` | `CounterTrend/RsiContrtrend.cs` | `RSI(14) < 30` і `close > Sma(50)` → BUY; дзеркально SELL |
| 10 | `C_WILLIAMS` | `CounterTrend/WilliamsRangeTrade.cs` | `WilliamsRange(14) < −80` → BUY; `> −20` → SELL |
| 11 | `C_PIVOT` | `Patterns/PivotPointsRobot.cs` | `close > R1` і `open < R1` → BUY; `close < S1` і `open > S1` → SELL |

### Клас PATTERN (4)

| # | id | Джерело | Правило |
|---|---|---|---|
| 12 | `P_PINBAR` | `Patterns/PinBarTrade.cs` | `close ≥ high − (high−low)/3` і `open ≥ high − (high−low)/3` → BUY; дзеркально SELL |
| 13 | `P_3SOLDIER` | `Patterns/ThreeSoldier.cs` | 3 послідовні свічки одного напрямку, тіло > 0.3×ATR(14) |
| 14 | `P_TURNAROUND` | `PositionsMicromanagement/CandlesTurnaroundPattern.cs` | розворотна свічка після серії протилежних |
| 15 | `P_IMPULSE` | `Patterns/CustomCandlesImpulseTrader.cs` | імпульсна свічка з тілом > k×ATR |

### Клас VOLATILITY (3)

| # | id | Джерело | Правило |
|---|---|---|---|
| 16 | `V_KELTNER` | `FuturesStart/FuturesStart2Keltner.cs` | пробій межі Keltner(20, 2×ATR) |
| 17 | `V_ATR_EXP` | `VolatilityStageRotationSamples/PriceChannelTrendAtrFilter.cs` | `ATR(14)/ATR(14)[t−10] > 1.20` + напрямок останнього бару |
| 18 | `V_STAGES` | `VolatilityStageRotationSamples/BollingerTrendVolatilityStagesFilter.cs` | зміна стадії волатильності (`VolatilityStagesAW`) + напрямок Bollinger |

---

## ВИКЛЮЧЕНО і чому

| Механіка | Причина |
|---|---|
| `PlateDetectorScreener`, `MarketDepthScreener`, `HighFrequencyTrader` | Потребують повного стакана. На FTMO MT5 роздрібний DOM недоступний |
| `ClusterCountertrend`, `MonitorVolume` | Потребують реального обсягу. На XAU `real_volume`=0, `tick_volume` ненадійний у Strategy Tester |
| `Robots/Grids/*` (8 шт.) | Сітки — необмежений DD, несумісні з FTMO MaxLoss 10% EOD-trailing |
| `UnsafeAveragePosition`, `EnvelopsCountertrend` | Усереднення в збиток |
| `Dividends/*`, `Rebalancers/*`, `Sectors/*`, `Options/*` | Акції/портфелі/опціони — не FX |
| `Funding/*` | Крипто-перпетуали |
| `NewsBots/*` | Потребують стрічки новин |
| `PairArbitrage/*`, `IndexArbitrage/*`, `CurrencyArbitrage/*` (13 шт.) | Потребують ≥2 інструментів. **Відкладено до окремої лабораторії** — не спростовано, лише неперевірено |
| `Lesson*` (18), `TechSamples` (15), `AutoTestBots` (32), `OnScriptIndicators` (15) | Навчальні / демо API / автотести — не стратегії |

### Об'єднані клони (не окремі генератори)

```
T_PRICECHANNEL  <- PriceChannelTrade, TwoTimeFramesBot,
                   PriceChannelTrendAtrFilter, FuturesTrendPriceChannel,
                   PriceChannelAdaptiveRsiScreener, FuturesScreenerLrAdaPc
T_LINREG        <- BreakLinearRegressionChannel, LinearRegressionFastScreener,
                   FuturesScreenerLrSma
T_PSAR          <- ParabolicSarTrade, ParabolicBollinger, ParabolicPriceChannel
C_BOLLINGER     <- StrategyBollinger, FuturesTrendBollinger,
                   FuturesStart1Bollinger, BollingerMomentumScreener
P_PINBAR        <- PinBarTrade, PinBarScreener, PinBarVolatilityScreener
P_3SOLDIER      <- ThreeSoldier, ThreeSoldierVolatilityAdaptive,
                   ThreeSoldierAdaptiveScreener
V_KELTNER       <- FuturesStart2Keltner, SectorsKeltner, SpeculantSetAtrKeltner
```

---

## Параметри

Усі параметри беруться **зі значень за замовчуванням OsEngine**.
Підбір заборонений (§12 специфікації).

Точні значення витягуються з `CreateParameter(...)` кожного файлу
на Кроці 1 і документуються в звіті. Будь-яке відхилення від дефолту
має бути обґрунтоване і зафіксоване **до** прогону.

---

## Очікуваний діапазон фічі співпадіння

```
18 механік × 3 ТФ (M5, M15, H1)
n_bots_active:          0 … 18 на кожному ТФ
n_timeframes:           0 … 3
класів:                 4 (trend / countertrend / pattern / volatility)
```

Виміряно на 5 архетипах (H1): 36.6% активних барів мали ≥2 механіки,
з них 69.9% — конфлікт за напрямком. При 18 механіках розподіл
голосування буде істотно ширшим.

---

## Верифікація Кроку 1

Для кожної з 18 механік перед включенням у пул:

- [ ] Кількість сигналів на 50 місяців — у розумних межах (не 0, не кожен бар)
- [ ] Відсутність look-ahead: усі індикатори на барі `i` використовують дані `≤ i`
- [ ] Обидва напрямки присутні
- [ ] Параметри збігаються з дефолтом OsEngine, зафіксовані письмово
- [ ] Розподіл сигналів по роках — без провалів, що вказують на баг

Механіка, що не пройшла верифікацію, **виключається з пулу з
документуванням причини**, а не виправляється підбором.
