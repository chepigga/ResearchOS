# LAB160 — PRICE TRAJECTORY × CROWD × OI × PROFILE STATE ATLAS

Статус: розрахунок завершено. Дослідницький атлас; входи, прибуток і придатність для торгівлі не тестувалися.

## Висновок
Послаблення Z дає додаткові історичні стани-кандидати, але загальна гіпотеза «профіль компенсує слабкий gate» не підтвердилася в перевіреній моделі. Додавання shape + location погіршило Brier score в обох напрямках на 2024 і 2025–2026 роках. Це висновок про цю грубу таблицю станів і цей прогноз, а не доказ відсутності будь-якої користі профілю.
У зрізі |Z|<1 десять клітин пройшли discovery/validation screen; сім мали додатний lift проти загального фону у пізнішому періоді, шість — проти відповідного price+crowd+OI стану. Вибірки перекриваються; це кандидати, не підтверджені сигнали.

## Джерела і виправлення попереднього аудиту
OHLCV є у GitHub Releases. Попереднє блокування через нібито відсутність цінової історії було помилковим: перевірка лише main не охоплювала releases і гілки.
- https://github.com/chepigga/ResearchOS/releases/tag/btc
- https://github.com/chepigga/ResearchOS/tree/lab/lab159-profile-shape-incremental-replay-20261010
- LAB159 source commit: 441a2467b285c47946811d785ef16f0f7332a90b.
- btc_5m.zip: SHA256 13188498f1f9eadc98550237590734bf65ec865ebe927458301d038e533858bd
- BTCUSDT_flow_2021-01-2026-08.csv.zip: SHA256 b6c80084751305f394270c4b133abbf89a0264634924891251b13b33afbe5e0d

## Обсяг розрахунку
- 589,794 M5-спостережень; 575,799 мають повний базовий state.
- Час спостережень: 2021-01-01 00:00:00+00:00 — 2026-08-10 21:25:00+00:00.
- OHLCV-архів: 741 737 рядків, 13 631 точний дублікат; суперечливих дублікатів немає. Остання свічка відкривається 10.08.2026 21:20 UTC. На досліджуваній ціновій сітці немає пропущених M5.
- Flow: 635 420 рядків, 40 152 точні дублікати; 153 розриви >5 хв. Пропуски не інтерполювалися. Пізніші flow-рядки без OHLCV не використовуються.
- Кожен горизонт має власну кількість доступних міток; останні 48h не мають повної 48h-мітки.

## Методика
- Кожна закрита M5; reference price = close. Майбутній шлях починається наступною свічкою. Жодного відбору за A/B3/R48.
- Горизонти 1/3/6/12/24/48h: signed terminal displacement, up/down MFE, час екстремумів, перший дотик ±0.5/1/2/3 ATR. MAE для BUY дорівнює down MFE, для SELL — up MFE.
- ATR за останніми 14 повними закритими H1 — проста середня TR, як у LAB158. Це явно замінює Wilder ATR, запропонований у початковому чернетковому аудиті.
- Profile: trailing24h, 40 bins, 70% value area. Обсяг M5 рівномірно розподілено між high/low; це proxy, не native volume-at-price. Shape збігається з LAB158 на контрольних прикладах.
- Z: 72 послідовні M5 значення count_long_short_ratio; OI4h value для сумісності та quantity окремо. Основний запуск передбачає затримку доступності flow 5 хв. Реальний час публікації джерелом не підтверджений.
- Напрям минулої ціни: displacement6h >0.5 ATR = UP, <-0.5 = DOWN, інакше FLAT. Continuation/reversal — лише опис майбутнього відносно цього минулого стану.
- Головна діагностика: за 6h досягти +2 ATR до -1 ATR; дзеркально вниз. Дотики обох бар’єрів в одній M5 позначено ambiguous та виключено з моделі. Час дотику відомий лише з точністю M5.
- Discovery2021–2023; validation2024; retrospective check2025–2026. По 48h перед межами вилучено. Це не pristine OOS: історію вже використовували інші LAB.

## Чи додає профіль інформацію?
Brier score — середня квадратична помилка ймовірності, менше краще. Ті самі спостереження, частотна модель із 100 псевдоспостереженнями; fit лише на discovery. PRICE = минулий напрям; FLOW = PRICE+signed Z bucket+OI bucket; PROFILE = FLOW+shape+value location.

| Напрям / період | Price | +Crowd/OI | +Profile | Δ Profile−Flow, 95% week-bootstrap |
|---|---:|---:|---:|---:|
| UP / VALIDATION | 0.144698 | 0.144278 | 0.144771 | +0.000493 [+0.000045; +0.000942] |
| UP / CHECK | 0.140213 | 0.140593 | 0.140979 | +0.000387 [+0.000067; +0.000707] |
| DOWN / VALIDATION | 0.144070 | 0.143730 | 0.144260 | +0.000530 [+0.000058; +0.001038] |
| DOWN / CHECK | 0.149426 | 0.149407 | 0.149958 | +0.000551 [+0.000259; +0.000921] |

Позитивна Δ означає погіршення. 1000 bootstrap повторів календарних тижнів, seed160; інтервали описові, не виправлені для всього попереднього пошуку гіпотез.

Перехід від OI value до OI quantity не змінив знак висновку: усі чотири порівняння також погіршилися з профілем. У приблизно 16.3% придатних спостережень знак зміни OI value і quantity різний.

## Слабкий Z: додатковий дослідницький зріз
Це supplemental аналіз після основного розрахунку; пороги screen ті самі: discovery N≥500, validation N≥100 і ≥10 тижнів, lift≥3 п.п. в обох періодах. У цьому зрізі наведені ВСІ 10 клітин, включно з невдалими. Не трактувати як незалежну перевірку після вибору.
LOW = |Z|<0.6; MID = 0.6≤|Z|<1. NEG/POS — знак Z. OI HIGH≥0.867%, NEG<0. Верхня/нижня межі value беруться з causal24h profile.
Ймовірності нижче — 6h barrier-event probability, НЕ win rate угод. У N входить багато сусідніх M5 одного руху.

| Напрям | Минула ціна | Crowd | OI | Profile / location | p 2021–23 | p 2024 | p 2025–26 | N пізніше | Δ до parent | ≥48h anchors |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|
| UP | DOWN | NEG_MID | NEG | D / BELOW | 20.0% | 21.3% | 21.7% | 360 | +6.2 п.п. | 83 |
| UP | FLAT | NEG_MID | HIGH | P / INSIDE | 23.5% | 22.0% | 21.7% | 92 | +5.6 п.п. | 31 |
| UP | UP | NEG_MID | HIGH | D / ABOVE | 22.0% | 23.2% | 16.0% | 543 | -2.6 п.п. | 99 |
| UP | UP | NEG_MID | HIGH | b / ABOVE | 24.7% | 22.7% | 20.1% | 289 | +1.4 п.п. | 50 |
| UP | UP | NEG_MID | NEG | D / ABOVE | 19.9% | 29.9% | 20.0% | 416 | +3.1 п.п. | 76 |
| DOWN | DOWN | POS_LOW | NEG | D / BELOW | 21.3% | 21.9% | 20.1% | 796 | +2.7 п.п. | 137 |
| DOWN | DOWN | POS_MID | HIGH | D / INSIDE | 23.6% | 22.1% | 23.7% | 194 | -0.9 п.п. | 50 |
| DOWN | FLAT | NEG_LOW | HIGH | P / INSIDE | 21.4% | 20.6% | 13.9% | 115 | -3.2 п.п. | 30 |
| DOWN | FLAT | NEG_MID | NEG | b / INSIDE | 24.5% | 22.0% | 23.5% | 345 | +6.6 п.п. | 68 |
| DOWN | UP | POS_LOW | NEG | P / INSIDE | 24.2% | 23.6% | 15.5% | 187 | -4.2 п.п. | 48 |

Parent = той самий past-price/Crowd/OI стан без поділу за profile. Anchors≥48h — груба консервативна оцінка різних спостережень, не кількість угод і не гарантія незалежності.
Приклад для наступного дослідження: UP outcome після DOWN, Z від -1 до -0.6, OI value падає, D-profile, ціна нижче value: 21.7% проти 15.4% у parent у 2025–2026; 360 рядків, лише 83 anchors≥48h. Потребує перевірки входу та ризику, а не негайного вмикання BUY.

## Горизонти: пізніший історичний період

| Горизонт | N | Median up MFE, ATR | Median down MFE, ATR | P(up2 before down1) | P(down2 before up1) |
|---|---:|---:|---:|---:|---:|
| 1h | 168672 | 0.365 | 0.368 | 2.4% | 2.6% |
| 3h | 168648 | 0.650 | 0.661 | 9.0% | 10.1% |
| 6h | 168612 | 0.939 | 0.976 | 16.8% | 18.3% |
| 12h | 168540 | 1.394 | 1.448 | 25.0% | 26.9% |
| 24h | 168396 | 2.077 | 2.129 | 30.0% | 31.9% |
| 48h | 168108 | 2.976 | 3.129 | 32.2% | 33.2% |

У цій загальній таблиці ambiguous лишаються в знаменнику як non-success; у ablation і conditional cells вони виключені. Тому останні десяткові знаки ймовірностей можуть відрізнятись.

## Обмеження та рішення
- Не розраховували PF, прибуток, costs, SL/TP execution або збільшення trades/month. Жоден результат не підтверджує обіцянку подвоїти частоту.
- Поділ на багато клітин створює рідкісні вибірки; негативний ablation може відображати дисперсію та грубу модель. Він не доводить, що профіль безкорисний для окремих режимів.
- Price-only контроль тут лише trend6h, не повноцінна сильна модель усіх цінових факторів. POC migration, density та continuous values збережено, але не включено в цей частотний ablation.
- Для причинності треба підтвердити timestamp semantics та publication lag; для точного профілю потрібен tick/trade volume. Поточний варіант є causal за задекларованою часовою моделлю.
- Глобально послаблювати gate на підставі LAB160 не обґрунтовано. У LAB161 можна дослідити обмежений набір weak-Z станів із калібруванням, контролем price-only та OI quantity; у LAB162 — перевірити execution.

## Відтворення
Python: numpy, pandas, numba, pyarrow. Скрипти не імпортують попередні LAB із побічними запуском бектестів.
```bash
python labs/LAB160_PRICE_TRAJECTORY_STATE_ATLAS_20261010/run_lab160.py --price /path/btc_5m.zip --flow /path/BTCUSDT_flow_2021-01-2026-08.csv.zip --out results/LAB160_20261010
python labs/LAB160_PRICE_TRAJECTORY_STATE_ATLAS_20261010/verify_lab160.py
python labs/LAB160_PRICE_TRAJECTORY_STATE_ATLAS_20261010/diagnostics.py
python labs/LAB160_PRICE_TRAJECTORY_STATE_ATLAS_20261010/build_report.py
```
Перевірки пройдені: profile parity LAB158, prefix invariance, exclusion observation candle, first-touch timing, same-bar ambiguity, missing-path rejection.

## Файли
- LAB160_states.parquet: усі M5 стани, validity і temporal split.
- LAB160_labels_{1,3,6,12,24,48}h.parquet: всі future trajectories та barriers.
- CSV: повна таблиця cells, ablation, candidate monthly, parent comparison, weak-Z supplemental, OI sensitivity та horizon summary.
- LAB160_audit.json: hashes та coverage.
- PROTOCOL.md: правила, зафіксовані до conditional results.
- Source scripts and report; raw source archives не дублюються у delivery bundle.
