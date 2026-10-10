from pathlib import Path
import pandas as pd,numpy as np,json
R=Path(__file__).resolve().parents[2];O=R/'results/LAB160C_20261010'
s=pd.read_csv(O/'LAB160C_summary.csv');a=pd.read_csv(O/'LAB160C_attribution.csv');y=pd.read_csv(O/'LAB160C_annual.csv');st=pd.read_csv(O/'LAB160C_standalone_new.csv');ci=pd.read_csv(O/'LAB160C_delta_monthly_bootstrap.csv');de=pd.read_csv(O/'LAB160C_portfolio_delta_decomposition.csv')
def md(df):
 return '| '+' | '.join(df.columns)+' |\n| '+' | '.join(['---']*len(df.columns))+' |\n'+'\n'.join('| '+' | '.join(str(v) for v in r)+' |' for r in df.itertuples(index=False,name=None))
def portfolio(cost,names=None):
 q=s[s.cost_bps==cost].set_index('variant')
 if names is not None:q=q.loc[names]
 q=q[['n','trades_month','ev','pf','r_month','mtm_dd_pct']].reset_index()
 for c in q.columns[2:]:q[c]=q[c].map(lambda v:f'{v:.3f}' if c=='ev' else f'{v:.2f}')
 q.columns=['Варіант','N','Угод/міс','EV, R','PF','R/міс','MTM DD, %'];return md(q)
main=['OLD','OLD_PROFILE','R48_RETEST_NEW_ALL','R48_RETEST_PROFILE','R48_OI_NEW_ALL','R48_OI_PROFILE','R48_BOTH_NEW_ALL','R48_BOTH_PROFILE']
aq=['OLD_PROFILE','A_Z075_NEW_ALL','A_Z075_PROFILE','A_OI50_NEW_ALL','A_OI50_PROFILE','A_Z075_OI50_NEW_ALL','A_Z075_OI50_PROFILE']
new=a[(a.cost_bps==7.5)&(a.cohort=='NEW_RAW_ACCEPTED')][['variant','n','ev','pf','total_r']].copy()
for c in ['ev','pf','total_r']:new[c]=new[c].round(3)
stand=[]
for v in ['R48_RETEST','R48_OI','R48_BOTH','A_Z075','A_OI50','A_Z075_OI50']:
 q=st[(st.variant==v)&(st.cost_bps==7.5)]
 for label,qq in [('ALL',q),('b',q[q.profile_shape=='b']),('NOT_b',q[q.profile_shape!='b']),('D',q[q.profile_shape=='D'])]:
  x=qq.net_r;loss=-x[x<0].sum();stand.append(dict(variant=v,shape=label,n=len(x),ev=x.mean(),pf=x[x>0].sum()/loss if loss>0 else np.nan,total_r=x.sum()))
pd.DataFrame(stand).to_csv(O/'LAB160C_new_raw_shape_attribution.csv',index=False)
rawtable=pd.DataFrame(stand).round(3)
yy=y[(y.cost_bps==7.5)&y.variant.isin(main[:2]+['R48_RETEST_NEW_ALL','R48_OI_NEW_ALL','R48_OI_PROFILE'])][['variant','year','n','pf','total_r']].round(3)
cc=ci[(ci.cost_bps==7.5)&ci.variant.isin(main[2:])&(ci.baseline=='OLD_PROFILE')][['variant','delta_rmo','ci_low','ci_high','positive_months']].round(3)
dd=de[(de.cost_bps==7.5)&(de.baseline=='OLD_PROFILE')&de.variant.isin(['R48_RETEST_NEW_ALL','R48_OI_NEW_ALL','R48_OI_PROFILE','A_Z075_NEW_ALL','A_OI50_NEW_ALL'])].drop(columns=['cost_bps','baseline']).round(3)
report=f'''# LAB160c — GATE RELAXATION × PROFILE INCREMENTAL REPLAY

Порівняння виконано 2026-10-10. **20 варіантів × 2 рівні витрат**, BTCUSDT, 2021–2024, спільний знаменник 48 місяців. Це продовження LAB159 для перевірки додаткових сигналів, а не нова direction model LAB161.

## Відповідь

**Частоту збільшити можна, але у перевірених варіантах профіль не компенсував погіршення якості додаткових сигналів.** Сильний результат R48_NOT_b на старому HIGH-гейті відтворився. Перенесення NOT_b на нові, слабші R48-сигнали погіршило їхній результат. Послаблення Z у A теж не дало поліпшення.

Найм'якше розширення — допустити ретест у R48, зберігши сильні acceptance/OI та NOT_b лише для старого HIGH-сегмента: **5,23 → 5,71 угоди/міс; +3,636 → +3,795R/міс; PF2,268 → 2,187; DD2,473% → 2,543%**. Це невеликий development-кандидат, не підтверджений приріст: 95% описовий місячний bootstrap інтервал ΔR/міс **−0,283…+0,637**, а 2023 рік погіршився.

Сильніше розширення — прибрати OI-гейт R48: **8,71 угоди/міс і +4,59R/міс**, але PF знижується до **1,84**, DD зростає до **5,12%**. Додаткове NOT_b на цих нових сигналах дає **+4,06R/міс і DD6,59%**, тобто не покращує цей варіант.

## Що саме послаблено

- `OLD`: оригінальні A+B3_HIGH+R48_HIGH+EARLY_EPISODE.
- `OLD_PROFILE`: LAB159 R48_NOT_b — не брати старий R48_HIGH на b-profile.
- `R48_RETEST`: прибрано заборону ретесту; margin≥0,689091 H1 ATR і OI change≥0,349516% залишено.
- `R48_OI`: прибрано OI-гейт; no-retest і margin≥0,689091 залишено.
- `R48_BOTH`: прибрано OI-гейт та заборону ретесту; margin залишено.
- У всіх R48 збережено пробій попереднього 48h діапазону, ≥4 із наступних6 close поза межею, вхід на відкритті сьомої свічки. Це не довільні M5 угоди.
- `A_Z075`: додано A-тригери перетину |Z|0,75 замість1,0; інші умови A збережено.
- `A_OI50`: OI4h q70 **+0,866696% → q50 +0,083239%**; Z1,0 залишено.
- `A_Z075_OI50`: обидва послаблення A. EXT80=1,529405 ATR, H4 CONT/REACCEL та SWING3 збережено.

Для A нові перетини об'єднані зі старими сигналами, бо перетин нижчого Z-порогу не містить автоматично старі перетини. Це нова додаткова trigger-гілка, а не буквальна заміна1,0 на0,75 у старому боті. Дедуплікація застосована лише до нових source/time/side; оригінальна кратність старих сигналів збережена.

`*_NEW_ALL` = **OLD_PROFILE + усі нові сигнали** відповідного послаблення. `*_PROFILE` = той самий старий OLD_PROFILE, але нові R48 пропускаються лише з NOT_b, нові A — лише з D-profile. Existing A/B3/EARLY не фільтруються. D-only для нових A — дослідницька гіпотеза LAB158, не доведене правило LAB159.

## R48: порівняння за однакової старої бази

Stress7,5bps, risk0,25%. У всіх NEW_ALL/PROFILE однаковий OLD_PROFILE; різниця лише у нових подіях.

{portfolio(7.5,main)}

Найбільше R/міс серед цих варіантів має R48_BOTH_NEW_ALL, але його якість нижча, а DD вищий за OLD_PROFILE. Це компроміс частота/ризик, не безкоштовне поліпшення. Вибирати його лише за максимальним історичним R/міс було б новим підбором на вже дослідженій історії.

## Engine A: слабший Z та OI

{portfolio(7.5,aq)}

Усі шість A-варіантів за однакової OLD_PROFILE бази мають нижчий stress R/міс за OLD_PROFILE. Для A_Z075_NEW_ALL **32 фактично прийняті нові угоди: EV−0,235R, PF0,669**. D-profile залишає20 нових прийнятих угод, але вони також від'ємні: **EV−0,197R, PF0,719**. Тут профіль не врятував послаблення Z.

## Чому старий висновок про b-profile не переноситься автоматично

Серед **192 нових raw R48** після зняття OI-гейта, при ізольованому виконанні зі старими виходами:

- b-profile: **N32, EV+0,739R, PF2,248**;
- NOT_b: **N160, EV+0,153R, PF1,201**.

На старому R48_HIGH b-profile був слабким. На новому сегменті зі слабшим OI він виявився сильнішим у цій історії. Отже, profile shape взаємодіє з умовами setup: твердження «b завжди поганий» даними не підтримується. N32 мале, тому це **не підстава перевертати фільтр і торгувати лише b**.

Повна ізольована атрибуція нових raw-подій:

{md(rawtable)}

Ці події можуть перекриватися; standalone суми не є портфельним P/L. Виходи ті самі HALF_TP3_LOCK2, але без portfolio add-on stop transfer. Signal-anchor ATR збережено окремо для кожного варіанта: різні тригери можуть вести до однакового entry time з різним ATR.

## Нові угоди, які портфель фактично прийняв

{md(new)}

Це результат нових raw-подій після concurrency, пріоритетів та stop transfer. `NEW_RAW_ACCEPTED` відрізняється від «виконано додатково щодо baseline»: старий raw-сигнал, який раніше блокувався, також може почати виконуватися. Повна декомпозиція Δportfolio:

**результат додатково виконаних − результат витіснених + зміна результату спільних угод**.

{md(dd)}

Наприклад, A_OI50 може мати прибуткові нові прийняті угоди, але не покращувати загальний портфель через витіснення та зміну менеджменту старих позицій. Тому додавання standalone R до baseline було б неправильним.

## Роки та невизначеність

{md(yy)}

Для R48_RETEST_NEW_ALL 2023 total R знизився **16,455 → 11,878**, PF **1,655 → 1,400**. Невелике загальне покращення не є рівномірним за роками.

Парний bootstrap місячних realized-R різниць проти OLD_PROFILE, 2000 вибірок48 місяців, 95% інтервали:

{md(cc)}

Жоден наведений R48 приріст не має нижньої межі вище нуля. Це описова невизначеність на історії; незалежне resampling місяців не повністю моделює серійну залежність, поправки за множинні перевірки немає. 2021–2024 вже використовувалися для розробки, **це не OOS**.

## Повні результати всіх20 варіантів

Безсуфіксні послаблені варіанти нижче залишають старий OLD без профілю. Вони потрібні для первинного тристороннього порівняння. NEW_ALL дають чистіший контроль користі профілю саме на нових подіях.

### Stress7,5bps

{portfolio(7.5)}

### Витрати2,81bps

{portfolio(2.81)}

На нижчих витратах розширення також збільшує частоту, але профіль на нових R48 не відновлює якість старого HIGH-сегмента. Наприклад, R48_OI_NEW_ALL: R/міс5,143, PF1,994, DD4,248%; для OLD_PROFILE: R/міс3,926, PF2,433, DD2,369%.

## Контроль відтворення та межі

- Stress OLD відтворено: **N300, EV0,563843, PF1,951644, R/міс3,524022, DD3,9193%** в межах точності опублікованого LAB159. OLD_PROFILE: **N251, EV0,695302, PF2,2676, R/міс3,6359, DD2,4733%**. Повна точність у CSV; baseline check не використовує нові результати для налаштування.
- Оригінальні506 raw-записів містять40 повторних source/time/side ключів. Кратність збережено у всіх гілках; occurrence ID дає однозначну атрибуцію. Цей lab не виправляє стару семантику повторних сигналів.
- Відновлений R48 universe1015, HIGH134; його ключі точно збігаються зі збереженими HIGH-сигналами. Entry indices усіх старих подій збігаються з оригінальною tape.
- Використано незмінені функції LAB155 execution та LAB159 profile, витягнуті з відповідних джерел без запуску сторонніх старих sweeps. Оригінальна LAB124 підготовка даних збережена. Усі40 результатів, часи, ідентифікатори, ATR standalone, суми та декомпозиції перевірені скриптом.
- Дані: release `btc`, `btc_5m.zip` і `BTCUSDT_flow_2021-01-2026-08.csv.zip`; SHA256 збігаються з LAB160b. Список у meta JSON. Нові2025–2026 дані не використано як доказ цієї перевірки.
- Виконання: SL1ATR, half TP3R + runner LOCK2, max48h за старою індексною tape, max2 односпрямовані позиції, перша MTM≥0 для add-on, LOCK025 transfer, пріоритет A>B3>R48>EARLY, 0,25% початкового капіталу за1R, без компаунду. DD = close-M5 MTM, не intrabar tick DD.
- Успадковано припущення старих lab щодо доступності flow timestamp, пропущених свічок та OHLC stop fills/transfer. Це точне порівняння старого дослідницького execution, **не нова перевірка live-causality або брокерських fills**. Зокрема, старий R48 OI використовує значення з timestamp entry; його реальну доступність на open слід окремо підтвердити перед forward.
- Profile — trailing24h,40bins, M5 volume рівномірно по high–low, без поточної entry-свічки; не tick footprint. Пороги розподілів визначені на development2021–2024.
- Перші14 варіантів зафіксовано до підрахунку; ще6 NEW_ALL додано як контроль змішаного ефекту старого і нового profile-фільтра. Вони не оголошуються заздалегідь зареєстрованим OOS тестом. Жодного порогу не підганяли після результатів.

## Рішення

**Зберегти R48_NOT_b як старий development-кандидат. Послаблення Z у A не підтримане. Універсальний NOT_b для нових R48 не підтриманий.** Допуск ретесту зі збереженим сильним OI — вузький кандидат для подальшої перевірки, але приріст невеликий та непереконливий. Повне зняття OI дає більше угод і R/міс ціною гіршої якості та більшої просадки. Production не змінено.

## Відтворення

Клонувати ResearchOS на гілці цього lab. Зберегти два source ZIP у `data/` поруч із репозиторієм або вказати `LAB160C_DATA` з абсолютним шляхом. З кореня репозиторію виконати:

```bash
python3 labs/LAB160C_GATE_RELAXATION_PROFILE_REPLAY_20261010/run_lab160c.py
python3 labs/LAB160C_GATE_RELAXATION_PROFILE_REPLAY_20261010/matched_controls.py
python3 labs/LAB160C_GATE_RELAXATION_PROFILE_REPLAY_20261010/verify_lab160c.py
python3 labs/LAB160C_GATE_RELAXATION_PROFILE_REPLAY_20261010/build_report.py
```

Dependencies: Python3, numpy, pandas. Пакет містить протокол, код, усі raw-набори,40 portfolio summaries, усі виконані угоди, annuals, standalone нових подій, cohort attribution, bootstrap і validation. Старі скрипти та raw baseline доступні у батьківському repo commit `2fc655be226af63035457d73b82a09893c27f377`.
'''
# Avoid hard-coded excess precision in baseline narrative; authoritative summary table is above.
report=report.replace('**N300, EV0,563843, PF1,951644, R/міс3,524022, DD3,9193%**','**N300, EV0,564, PF1,952, R/міс3,524, DD3,919%**').replace('**N251, EV0,695302, PF2,2676, R/міс3,6359, DD2,4733%**','**N251, EV0,695, PF2,268, R/міс3,636, DD2,473%**')
(O/'LAB160C_REPORT_UK.md').write_text(report);print('report ready')
