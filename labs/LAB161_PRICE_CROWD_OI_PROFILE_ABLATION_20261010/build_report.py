from pathlib import Path
import json
import pandas as pd,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parents[2];O=R/'results/LAB161_20261010'
p=pd.read_csv(O/'LAB161_pooled.csv');w=pd.read_csv(O/'LAB161_wave_metrics.csv');s=pd.read_csv(O/'LAB161_signal_metrics.csv');b=pd.read_csv(O/'LAB161_incremental_brier.csv');ic=pd.read_csv(O/'LAB161_incremental_coverage.csv');iff=pd.read_csv(O/'LAB161_incremental_false.csv');prob=pd.read_csv(O/'LAB161_probability_metrics.csv');data=json.loads((O/'LAB161_data_audit.json').read_text());models=['PRICE','PRICE_CROWD','PRICE_CROWD_OI','PRICE_CROWD_OI_PROFILE'];labels=['Price (OHLCV)','+ Crowd','+ OI','+ Profile'];colors=['#344b68','#197b94','#329d9a','#b08336'];main=p[(p.requested_per_day==1)&p.model.isin(models)].set_index('model').loc[models]
def md(df):
 d=df.copy()
 for col in d:
  if pd.api.types.is_float_dtype(d[col]):d[col]=d[col].map(lambda x:f'{x:.2f}' if pd.notna(x) else '—')
 return '| '+' | '.join(map(str,d.columns))+' |\n| '+' | '.join(['---']*len(d.columns))+' |\n'+'\n'.join('| '+' | '.join(map(str,row))+' |' for row in d.itertuples(index=False,name=None))
fig,ax=plt.subplots(2,2,figsize=(13,9));x=np.arange(4)
ax[0,0].bar(x,main.coverage1_pct,color=colors);ax[0,0].set_xticks(x,labels);ax[0,0].set_ylim(0,18);ax[0,0].set_ylabel('% of 1,309 retrospective waves');ax[0,0].set_title('Wave coverage | >=1 ATR remains',loc='left',fontweight='bold')
for i,v in enumerate(main.coverage1_pct):ax[0,0].text(i,v+.35,f'{v:.1f}%',ha='center')
ax[0,1].bar(x,main.false_pct,color=colors);ax[0,1].errorbar(x,main.false_pct,yerr=[main.false_pct-main.false_ci_low,main.false_ci_high-main.false_pct],fmt='none',ecolor='#293646',capsize=4);ax[0,1].set_xticks(x,labels);ax[0,1].set_ylim(0,85);ax[0,1].set_ylabel('% of emitted signals');ax[0,1].set_title('False signals | weekly bootstrap 95% CI',loc='left',fontweight='bold')
for i,v in enumerate(main.false_pct):ax[0,1].text(i,main.false_ci_high.iloc[i]+2,f'{v:.1f}%',ha='center')
for model,label,col in zip(models,labels,colors):
 q=p[p.model==model].sort_values('requested_per_day');ax[1,0].plot(q.signals_per_day,q.coverage1_pct,'o-',label=label,color=col)
q=p[p.model=='SCHEDULE_MOMENTUM'];ax[1,0].plot(q.signals_per_day,q.coverage1_pct,'--',color='#888',label='Scheduled momentum');ax[1,0].set_xlabel('Actual signals per day');ax[1,0].set_ylabel('Wave coverage, %');ax[1,0].set_title('More signals raise coverage, not necessarily quality',loc='left',fontweight='bold',fontsize=10);ax[1,0].legend(frameon=False,fontsize=8)
for model,label,col in zip(models,labels,colors):
 q=prob[(prob.model==model)&(prob.sampling=='ALL_M5')];ax[1,1].plot(q.year,q.brier,'o-',label=label,color=col)
ax[1,1].set_xticks([2024,2025,2026],['2024','2025','2026 partial']);ax[1,1].set_ylabel('Multiclass Brier score (lower is better)');ax[1,1].set_title('Probability quality is not stable across years',loc='left',fontweight='bold',fontsize=10)
for a in ax.flat:a.spines[['top','right']].set_visible(False);a.grid(axis='y',alpha=.12);a.set_axisbelow(True)
fig.suptitle('LAB161 | Price, Crowd, OI and Profile',x=.07,ha='left',fontsize=19,fontweight='bold');fig.text(.07,.93,'BTCUSDT | temporal test: 2024–09 Aug 2026 | primary threshold calibrated to 1 signal/day',fontsize=10,color='#596577');fig.text(.07,.015,'Signal success: +3 ATR before -1.5 ATR within 24h, using closes. Coverage is not realized profit.',fontsize=9,color='#596577');fig.tight_layout(rect=[0,.03,1,.91]);fig.savefig(O/'LAB161_comparison.png',dpi=140);plt.close(fig)
mt=main.reset_index()[['model','signals','signals_per_day','false_pct','coverage1_pct','coverage2_pct','coverage3_pct','remaining_atr_median']];mt.columns=['Модель','Сигналів','На день','Хибні, %','Покрито ≥1 ATR, %','≥2 ATR, %','≥3 ATR, %','Залишок ATR*']
y=w[(w.definition=='LEG_REV1ATR')&(w.requested_per_day==1)&w.model.isin(models)].merge(s,on=['year','model','requested_per_day']);y=y[['year','model','signals_per_day','false_pct','coverage1_pct','remaining_atr_median']]
sens=p[(p.requested_per_day==2)&p.model.isin(models)][['model','signals_per_day','false_pct','coverage1_pct','clean_coverage1_pct']]
rev=w[(w.definition=='LEG_REV2ATR')&(w.requested_per_day==1)].groupby('model')[['waves','covered1','covered2','covered3']].sum().reset_index();rev['coverage1_pct']=100*rev.covered1/rev.waves
ib=b[b.year=='ALL'];fc=iff[(iff.year=='ALL')&(iff.requested_per_day==1)];cc=ic[(ic.year=='ALL')&(ic.requested_per_day==1)]
legacy=w[(w.year==2024)&(w.definition=='LEG_REV1ATR')&((w.requested_per_day==1)|(w.model=='LEGACY_RAW_PROFILE'))].merge(s,on=['year','model','requested_per_day'])[['model','signals','signals_per_day','false_pct','coverage1_pct']]
report=f'''# LAB161 — PRICE → CROWD → OI → PROFILE

Дата: 2026-10-10. Відтворюване дослідження BTCUSDT, parent LAB160d `dbc99709494b47d38464d7e450fffd880a0debb6`. Production не змінено.

## Висновок

**Просте додавання Crowd, OI і profile до моделі ціни не дало стійкого розширення покриття рухів.** При приблизно одному сигналі на день моделі розпізнають12–13% окремих хвиль; близько67–70% сигналів не виконують зафіксовану цінову умову. Додаткові ознаки не усунули проблему слабкої прогностичної якості в цьому експерименті.

Crowd знижує спостережувану частку хибних сигналів із70,49% до67,31%, але paired weekly95% CI різниці **−7,25…+1,13 п.п.** включає нуль. Покращення не називаємо доведеним. OI додає лише−0,54п.п. хибних; profile змінює показник на+0,06п.п. Обидва інтервали також включають нуль.

Profile не показує підтвердженого приросту покриття чи точності понад PRICE+CROWD+OI. Це не скасовує LAB159: там досліджувався фільтр уже відібраних R48-угод; тут — прогноз широкої вибірки ринку.

![Порівняння](LAB161_comparison.png)

## Основне порівняння

Тести2024,2025 та2026 до9 серпня21:25UTC; **1309 окремих хвиль**, із них1306 мають хоча б одну спільну доступну точку прогнозу в дозволеному інтервалі. Це інший період і суворіша метрика, ніж91,6% у LAB160d. Безпосередньо віднімати ці відсотки один від одного не можна.

Калібрування на попередньому році націлене на1 сигнал/день; фактична частота в тесті показана окремо і не є абсолютно однаковою. Немає вибору порогів за результатом тестового року.

{md(mt)}

*Залишок ATR — **медіана лише серед розпізнаних хвиль**: від close першого відповідного сигналу до ретроспективного піку, у ATR на момент сигналу. Це не середній результат усіх сигналів і не зароблений R. Медіанний час до піку у цих хвилях — приблизно2,8–3,0години. У повної моделі медіанна залишкова частка амплітуди —62,2% серед розпізнаних хвиль.

За суворішої умови, що сигнал також успішний за3-before-1.5, coverage у повної моделі — **9,24%**, проти8,02% у PRICE. Це спільна вимога до хвилі та майбутньої траєкторії сигналу, не торговий P/L.

## Що саме означає хибний сигнал

На закритті M5 модель обирає BUY або SELL. Успіх: протягом наступних24h ціна **закриття** досягла+3 ATR у вибраному напрямку раніше, ніж−1,5 ATR. ATR зафіксований на сигналі; intrabar high/low тут не визначає послідовність. Невиконання цієї умови — хибний сигнал для конкретної дослідницької цілі, не обов'язково збиткова угода за іншими exits.

Для повної моделі на основній частоті:
-33,17%: +3 ATR до зустрічних1,5 ATR;
-9,27%: +3 ATR усе-таки досягнуто, але спочатку була несприятлива траєкторія;
-57,56%: +3 ATR не досягнуто за24h.

Таким чином, слабкість не пояснюється тільки надто раннім стопом у нашому визначенні: **більше половини сигналів повної моделі взагалі не отримують потрібного3ATR руху у свій бік за24h**. Це не доводить непридатності інших горизонтів/амплітуд.

## Стабільність за роками

{md(y)}

2024: повна модель покриває10,69%, ціна9,07%, але повна модель також подає більше сигналів. 2025: Crowd піднімає coverage до19,31%, частково на тлі частоти1,61/день проти1,34у PRICE. 2026: повна модель8,47% проти12,20% у PRICE і також рідше сигналізує. Тому ці різниці не є чистим порівнянням за однакової кількості сигналів. Саме для цього паралельно вимірюється якість імовірностей на всіх спільних M5-рядках.

## Якість прогнозів на всій M5-сітці

Brier — сума квадратів помилки трьох імовірностей NONE/UP/DOWN; менше краще. На відміну від coverage за порогом, цей показник не залежить від кількості відібраних сигналів. Порівняння парне,95% інтервали — bootstrap календарних тижнів,1000перевибірок. Це враховує кластеризацію, але не робить багаторічний ринок стаціонарним і не усуває весь ризик багаторазових порівнянь.

{md(ib[['previous','model','delta_brier','ci_low','ci_high']].assign(delta_brier=lambda x:x.delta_brier.map(lambda v:f'{v:+.6f}'),ci_low=lambda x:x.ci_low.map(lambda v:f'{v:+.6f}'),ci_high=lambda x:x.ci_high.map(lambda v:f'{v:+.6f}')))}

Негативна delta — покращення. **Жоден сукупний приріст не має інтервалу цілком нижче нуля.** Додавання Crowd у2024 покращує Brier на−0,00717 (CI−0,01368…−0,00093), а у2025 погіршує на+0,01750 (CI+0,00542…+0,02985). Поліпшення precision відібраного хвоста і погіршення ймовірностей по всій вибірці можуть співіснувати; це різні метрики. Ймовірності моделі не проходили окремого probability calibration, тому їх не слід показувати на стрілках як доведену ймовірність успіху.

Повні ALL_M5 та DAILY_ANCHOR Brier/logloss/AP/base-rate таблиці — у `LAB161_probability_metrics.csv`.

## Невизначеність додаткової користі

Основна частота, paired weekly bootstrap; хибні оцінюються як різниця часток у двох потоках сигналів на тих самих перевибраних тижнях, coverage — на тих самих хвилях. Пороги незмінні, фактична частота може різнитися.

{md(fc[['previous','model','delta_false_pp','ci_low','ci_high']])}

{md(cc[['previous','model','delta_coverage_pp','ci_low','ci_high']])}

Усі наведені інтервали перетинають нуль. Немає підстав оголосити переможцем повну модель або автоматично включати ці ознаки у production.

## Чи допомагає більша частота

Наперед визначена чутливість: калібрування на2 сигнали/день:

{md(sens)}

Coverage зростає до21–24%, але частка хибних залишається67–71%. Це переважно збільшення кількості спроб, а не продемонстрований якісний стрибок. Повна модель при2,01сигнала/день покриває21,01% хвиль; PRICE при1,94 —23,83%.

Простий контроль за розкладом із напрямком trailing6h momentum при приблизно1/день покриває11,84%, але має76,59% хибних. При2/день він покриває24,52% і має73,99% хибних. Це показує, чому високий coverage без одночасного контролю помилок недостатній. Контроль за розкладом не підібраний за результатом і не є рівночастотним випадковим тестом.

## Чутливість до визначення хвилі

Для ширшого підтвердження розвороту2 ATR —1163 хвилі. Інтервали хвиль стають довшими, тож новому сигналу легше потрапити всередину. Основна частота:

{md(rev)}

Покриття вище, але профіль знову не перевершує PRICE. Не змішуємо ці знаменники з1ATR-сегментацією.

## Порівняння зі старими сигналами в одному періоді

Лише2024, однаковий новий критерій: сигнал усередині хвилі, строго до піку, пік у межах24h, щонайменше1ATRзалишку. Старі raw-події після NOT_b дедупліковані за часом і напрямком; використано лише спільні доступні рядки. Це не зіставлення251 фактичної угоди з новими симульованими угодами.

{md(legacy)}

У старих90raw-сигналів coverage5,04% проти10,69% у повної моделі з307сигналами. Отже, кількість сигналів зросла значно сильніше, ніж покриття. Старий raw success за новим label36,67% має широку невизначеність; це не його історичний win rate/PF.

## Що перевірено і чого висновок не доводить

-PRICE:18ознак OHLCV — минулі зміни ціни, range location/width, EMA distance, ATR%, реалізована мінливість і агрегований volume ratio. Crowd:+6ознак long/short ratio,6hZ та їх зміни. OI:+4зміни кількості контрактів за30m/1h/4h/24h. Profile:+11ознак shape, відстань доPOC/VAL/VAH, щільність, ширина value, міграціяPOC. Повний список уJSON.
-Одна фіксована архітектура gradient boosting, без підбору гіперпараметрів за тестом. Навчання на кожній третій M5-точці (UTC15m), оцінювання всіх доступних M5. Хронологічні train/calibration/test,24hpurge; threshold калібрується лише на попередньому році. Сигнали мають спільний6hcooldown, без фільтра старих setup.
-{data['rows']}рядків, {data['eligible']}спільних повних спостережень у2021–2026; тести мають271671M5-рядок. OHLCV закінчується10серпня2026, хоча flow триває далі: майбутню ціну не домальовано. Покриття даних за роками збережене окремо.
-Profile реконструйований заM5OHLCV,24h/40bins. Це не tick volume-at-price. Flow зсувається на5хв: припущення доступності, не виміряний publication lag у live.
-Нуль future price gaps у price tape; пропущений flow не forward-fill. Ознаки доступні на закритті; causal-prefix тест пройдено. Synthetic label/barrier/cooldown/endpoint tests пройдено. Успадковані3483завершені хвилі двох визначень LAB160d відтворені точно.
-2021–2026 вже використовувалися для спорідненого пошуку. Це часові held-out прогнози в рамках LAB161, **не pristine project OOS**. Довірчі інтервали умовні на цей протокол і не враховують усі попередні спроби.
-Одна модель, один primary horizon і зафіксований набір ознак не доводять, що Crowd/OI/profile завжди марні. Вони показують, що ці конкретні causal summaries не забезпечили стійкого додаткового результату тут.
-Немає виконаних входів, SL/TP, витрат, PF, DD або прогнозу доходу. Close-barrier результат не замінює execution replay.

## Практичний висновок для дослідження

Попередній аудит локалізував вузьке покриття старих setup. LAB161 додав важливу перевірку: **зняти старі setup і просто об'єднати поточні price/Crowd/OI/profile-ознаки недостатньо для сильного загального детектора рухів**. Потрібно досліджувати форму події та розвиток стану у часі, окремо continuation/reversal, і вимагати приросту поза навчальним періодом. Це гіпотеза наступної роботи, не доведена причина і не вже виконане покращення. Поточний production залишено без змін.

## Відтворення

Input ZIP: release `btc` репозиторію chepigga/ResearchOS. SHA256 і версії в `LAB161_data_audit.json` та `LAB161_versions.json`. Файли помістити в сусідній до repo `data/` або встановити `LAB160C_DATA`. Встановлені numpy,pandas,numba,scikit-learn,joblib,matplotlib.

```bash
export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
python3 labs/LAB161_PRICE_CROWD_OI_PROFILE_ABLATION_20261010/prepare.py
python3 labs/LAB161_PRICE_CROWD_OI_PROFILE_ABLATION_20261010/run_models.py
python3 labs/LAB161_PRICE_CROWD_OI_PROFILE_ABLATION_20261010/evaluate.py
python3 labs/LAB161_PRICE_CROWD_OI_PROFILE_ABLATION_20261010/uncertainty.py
python3 labs/LAB161_PRICE_CROWD_OI_PROFILE_ABLATION_20261010/verify.py
python3 labs/LAB161_PRICE_CROWD_OI_PROFILE_ABLATION_20261010/build_report.py
```

Archive містить код, протокол,12навчених моделей, усі emitted signals, поелементне зіставлення з хвилями, підсумки та перевірки. Великі відновлювані `LAB161_dataset.pkl` та повні M5predictionNPZ не включено; вони відновлюються першими двома командами. `evaluate.py` повторно відкидає старі legacy-рядки перед додаванням, тож повторне виконання не дублює їх.
'''
(O/'LAB161_REPORT_UK.md').write_text(report);print('REPORT READY')
