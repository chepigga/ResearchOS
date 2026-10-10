from pathlib import Path
from prepare import R,O
import json,hashlib,zipfile,platform
import pandas as pd,numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt

def table(d):
 def fmt(x):return f'{x:.3f}' if isinstance(x,(float,np.floating)) else str(x)
 return '\n'.join(['| '+' | '.join(d.columns)+' |','| '+' | '.join(['---']*len(d.columns))+' |']+['| '+' | '.join(fmt(x) for x in row)+' |' for row in d.itertuples(index=False,name=None)])

def main():
 f=pd.read_csv(O/'filter_metrics.csv');ab=pd.read_csv(O/'ablation_metrics.csv');e=pd.read_csv(O/'execution_summary.csv');comp=pd.read_csv(O/'feature_comparison.csv');states=pd.read_csv(O/'state_success_rates.csv');cov=pd.read_csv(O/'wave_coverage.csv');cost=pd.read_csv(O/'cost_decomposition.csv');signals=pd.read_csv(O/'scored_signals.csv.gz',parse_dates=['time']);checks=json.loads((O/'prepare_validation.json').read_text());primary=f[(f.model=='OBSTACLES')&(f.retention==.5)&(f.period=='CHECK')].iloc[0]
 p=e[(e.selection=='OBSTACLES_50')&(e.period=='CHECK_2025_26')&(e.replay=='PORTFOLIO2')&(e.cost_bps==7.5)].set_index('mode');base=e[(e.selection=='ALL')&(e.period=='CHECK_2025_26')&(e.replay=='PORTFOLIO2')&(e.cost_bps==7.5)].set_index('mode');market=p.loc['MARKET'];gross=cost[(cost.selection=='OBSTACLES_50')&(cost['mode']=='MARKET')].iloc[0]
 headline=pd.DataFrame([dict(variant='BASE_ALL',trades=int(base.loc['MARKET','n']),EV=base.loc['MARKET','EV'],PF=base.loc['MARKET','PF'],R_month=base.loc['MARKET','R_month'],trades_month=base.loc['MARKET','trades_month'],MTM_DD_pct=base.loc['MARKET','mtm_dd_pct'])]+[dict(variant='FILTER_'+mode,trades=int(r.n),EV=r.EV,PF=r.PF,R_month=r.R_month,trades_month=r.trades_month,MTM_DD_pct=r.mtm_dd_pct) for mode,r in p.iterrows()]);headline.to_csv(O/'headline.csv',index=False)
 selectedfeatures=['atr_pct','range_288','ratio_change_6h','oi_change_48','value_width','valley_ratio','nearest_room_atr','H4_alignment','H1_alignment'];cmp=comp[(comp.feature.isin(selectedfeatures))&(comp.split=='CHECK')][['feature','success_n','failure_n','success_median','failure_median','standardized_difference']]
 # Top10 ranking on FIT only, all variables retained in detailed report tables.
 fitrank=comp[comp.split=='FIT'].copy();fitrank['abs_smd']=fitrank.standardized_difference.abs();top=fitrank.nlargest(10,'abs_smd').feature;rank=comp[comp.feature.isin(top)&comp.split.isin(['FIT','VALIDATION','CHECK'])].pivot(index='feature',columns='split',values='standardized_difference').reset_index();rank.to_csv(O/'fit_ranked_feature_stability.csv',index=False)
 covsummary=[]
 for selection,q in cov[cov.year>=2025].groupby('selection'):covsummary.append(dict(selection=selection,waves=int(q.waves.sum()),recognized=int(q.recognized.sum()),coverage_pct=100*q.recognized.sum()/q.waves.sum(),clean_coverage_pct=100*q.clean_recognized.sum()/q.waves.sum(),signals=int(q.signals.sum())))
 covsummary=pd.DataFrame(covsummary);covsummary.to_csv(O/'check_wave_summary.csv',index=False);cs=covsummary.set_index('selection');primary_threshold=float(primary.threshold)
 config=dict(primary='OBSTACLES_50',threshold=primary_threshold,fit_years=[2021,2022],threshold_calibration_year=2023,score_target='closed-price +3ATR before -1.5ATR in24h',context=['D1','H4','H1','M15','M5'],entry_options=['MARKET','DELAY30','LIMIT025'],SL_signal_ATR=1.5,TP_signal_ATR=3,horizon_hours=24,max_positions_including_pending=2,risk_pct_initial_equity=.25,deployed=False,conclusion='small gross edge; net fails7.5bps in combined2025-2026; no live promotion');(O/'candidate_config.json').write_text(json.dumps(config,indent=2))
 fig,axs=plt.subplots(1,3,figsize=(15,4.5));labels=['Price+TF','+Crowd','+OI','+Profile','+Obstacles'];v=f[(f.period=='CHECK')&(f.retention==.5)].set_index('model').loc[['PRICE_TREND','CROWD','OI','PROFILE','OBSTACLES']]
 axs[0].bar(np.arange(5),v.selected_success_pct,color='#297da6');axs[0].axhline(primary.base_success_pct,color='gray',ls='--',label='All candidates');axs[0].set_xticks(np.arange(5),labels,rotation=25);axs[0].set_ylabel('+3 ATR before -1.5 ATR, %');axs[0].set_ylim(0,35);axs[0].legend(fontsize=8);axs[0].set_title('Retain nominal50%, thresholds from2023')
 for selection,label in [('ALL','All'),('OBSTACLES_50','Filtered')]:
  q=e[(e.selection==selection)&(e.period=='CHECK_2025_26')&(e.replay=='PORTFOLIO2')&(e['mode']=='MARKET')];axs[1].plot(q.cost_bps,q.PF,'o-',label=label)
 axs[1].axhline(1,color='gray',ls='--');axs[1].set_xlabel('Assumed roundtrip bps');axs[1].set_ylabel('Portfolio PF');axs[1].set_title('Market entries; max2 positions');axs[1].legend(fontsize=8)
 axs[2].bar(['Gross','Cost','Net'],[gross.gross_EV,-gross.mean_cost_R,gross.net_EV],color=['#277b53','#b34343','#b34343']);axs[2].axhline(0,color='gray',lw=.8);axs[2].set_ylabel('R per trade');axs[2].set_title('Primary market filter,7.5bps');fig.suptitle('LAB166 — CHECK2025–2026');fig.tight_layout();fig.savefig(O/'comparison_execution.png',dpi=150);plt.close(fig)
 # Annotated pre-signal trajectories: pair chosen for similar prior1h progress (illustration only).
 price=pd.read_pickle(O/'price_runtime.pkl');q=signals[signals.split=='CHECK'];good=q[q.success==1].copy();center=good.return_12.median();g=good.iloc[np.abs(good.return_12-center).argmin()];bad=q[q.success==0];b=bad.iloc[np.abs(bad.return_12-g.return_12).argmin()];fig,axs=plt.subplots(2,1,figsize=(12,7))
 examples=[]
 for r,ax,name in [(g,axs[0],'SUCCESS'),(b,axs[1],'FAILED')]:
  i=int(r.i);start=max(0,i-72);end=min(len(price)-1,i+288);t=price.index[start:end+1];ax.plot(t,r.side*(price.close.iloc[start:end+1]-r.close)/r.atr,color='#2d5674');ax.axvline(r.time,color='purple',ls=':');ax.axhline(3,color='green',ls='--');ax.axhline(-1.5,color='red',ls='--');ax.axvspan(t[0],r.time,color='gray',alpha=.1);ax.set_title(f'{name}: {r.time}, {"BUY" if r.side==1 else "SELL"}, shape{r["shape"]}, OI4h{r.oi_change_48:.2f}%, alignedCrowdZ{r.crowd_z:.2f}, room{r.nearest_room_atr:.2f}ATR');ax.set_ylabel('Directional price, signalATR');ax.tick_params(axis='x',rotation=15);examples.append(dict(time=str(r.time),side=int(r.side),label=name,rule='Success nearest median1h progress, failure closest1h progress to selectedsuccess. Labels used only for illustration; not candidate selection.'))
 fig.tight_layout();fig.savefig(O/'successful_failed_examples.png',dpi=150);plt.close(fig);(O/'example_selection.json').write_text(json.dumps(examples,indent=2))
 report=f'''# LAB166 — ВДАЛІ ТА НЕВДАЛІ ПОЧАТКИ × ENTRY × COSTS

Завершено2026-10-10. **Відбір до входу покращив якість сигналів, але перевага не витримала7.5bps витрат у сукупному CHECK2025–2026.** Production не змінений.

## Результат, який відповідає на поставлене питання

Базові початки мають {primary.base_success_pct:.2f}% виконань +3ATR раніше за−1.5ATR у24h. Причинний відбір за ціною, трендом, Crowd, OI, профілем та відомими рівнями має **{primary.selected_success_pct:.2f}%**, залишаючи {primary.selected_n:.0f}/{primary.n:.0f} сигналів. Приріст **{primary.uplift_pp:.2f}п.п.**, тижневий bootstrap95%CI [{primary.uplift_ci_low:.2f};{primary.uplift_ci_high:.2f}]. Він повторюється за знаком у2024,2025,2026. Інтервал умовний на вже навчену модель, не враховує невизначеність навчання або весь попередній пошук LAB.

Market next-open у портфелі максимум2 позиції: до витрат **EV{gross.gross_EV:+.3f}R, PF{gross.gross_PF:.2f}**. Середня вартість7.5bps — **{gross.mean_cost_R:.3f}R/угоду**. Після витрат **EV{market.EV:+.3f}R, PF{market.PF:.2f}, {market.R_month:+.2f}R/місяць**, {market.trades_month:.1f} угоди/місяць. Отже, ознаки несуть невелику корисну інформацію, але перевірений торговий перенос залишається недостатнім.

![Порівняння та виконання](comparison_execution.png)

## Дані, сигнали та перевірка часу

Основний потік широкий: на закритті M5 у00/06/12/18UTC напрямок за останньою годиною. Без майбутніх екстремумів, вимоги балансу/ретесту або profile gate. У тестових роках сигнали й мітки точно збігаються з LAB165 CLOCK_1H_MOMENTUM_R4. Повна кількість{checks['rows']}; розподіл: {checks['split_counts']}.

Ознаки причинні на момент сигналу: підтверджена структура D1/H4/H1/M15/M5, ціна5m–24h/прискорення/ефективність/обсяг/тіло/тіні; OI quantity1h/4h/24h і прискорення; countL/S та crowdZ/зміни; trailing24h P/B/b/D,POC,VAH/VAL,HVN2,LVN, міграція; відстань до відомих H1/H4 swing і профільних рівнів попереду. Рівні — можливі перешкоди, не гарантовані точки зупинки. Відстані менше0.1ATR не враховуються; відсутність рівня позначена окремо, відстань обмежено10ATR.

OI<=0 масковано; в сирому джерелі473 такі рядки. L/S — співвідношення кількості акаунтів, не розмірів позицій. Flow delay5min — успадковане припущення, не виміряна liveзатримка. Профіль реконструйований з M5high-low40bins, не tickfootprint. B — дві розділені вершини зі структурним valley, не legacyDOUBLE.

Кеш LAB162_tape був обрізаний, тому цей LAB відновив вузли профілю та OI з неушкодженого LAB161pricecache й оригінального flowZIP, не використовував пошкоджений файл. Список missing predictors є уfeature_missingness.csv; модель допускає пропуски, вони не заповнюються майбутнім.

## Як саме відрізняються добрі й погані початки

Усі порівняння збережено, наведені нижче ознаки не обиралися за прибутком CHECK. SMD — різниця середніх good-minus-bad у одиницях pooledSD; це асоціація, не причинне пояснення.

{table(cmp)}

atr_pct — ATR/ціна; ratio_change_6h — часткова зміна, множення на100 дає відсотки. Зміни OI тут уже у%. Всі directional ознаки узгоджені з BUY/SELL кандидата.

Найпомітніша стабільна одинична різниця — **нижчий ATR/ціна** у вдалих міток. Вужчі добові діапазони/VA дають сильніший поділ уFIT, слабший уCHECK. Позитивна змінаOI4h має невелику різницю у тому самому напрямку. Ефект перекосуCrowdZ значно слабшає позаFIT. Однозначного правила «вільна дорога>=1ATR означає хороший сигнал» тут немає.

Нижчий ATR/ціна також підвищує costR для незмінних bps — риса, що допомагає price-label, може погіршувати економіку входу. Це показує, чому однієї класифікації рухів недостатньо.

Стабільність10 ознак із найбільшим|SMD| **саме наFIT**:

{table(rank)}

Форма профілю сама по собі вCHECK:

{table(states[(states.grouping=='shape')&(states.split=='CHECK')][['shape','n','success_pct']])}

P/B/b/D не дає універсального сильного поділу в цьому широкому потоці. Це не спростовує LAB159 для конкретної підвибіркиR48 — там інші сигнали й сценарій.

## Відбір, визначений до CHECK

Модель фіксована HGB80iter,7leaves,minleaf50,L2=10; FIT2021–2022, CAL2023 лише для порогів, VALIDATION2024, CHECK2025–2026. Пороги25/50/75%CAL незмінні; первинний режим — всі ознаки й номінальний відбір50%, визначений уPROTOCOL до результатів. НаCHECK не підбирали переможця.

{table(f[(f.retention==.5)&f.period.isin(['VALIDATION','CHECK','CHECK_2025','CHECK_2026'])][['model','period','selected_n','selected_success_pct','uplift_pp','uplift_ci_low','uplift_ci_high']])}

Ablation на однакових сигналах:

{table(ab[ab.split=='CHECK'])}

Crowd/OI допомагають цьому відбору, але всі AUC залишаються невисокими. Додавання профілю доOI погіршує CHECK Brier; obstacleознаки не дають переконливого окремого Brierприросту. У повної моделі Brier навіть трохи гірший за сталу частотуFIT: rankingкорисність не означає добре калібровані ймовірності. Не видаємо scoreза точну ймовірність прибуткової угоди.

## Охоплення після відсікання

{table(covsummary)}

Основний відбір знижує rawwaveохоплення з{cs.loc['ALL','coverage_pct']:.2f}% до{cs.loc['OBSTACLES_50','coverage_pct']:.2f}%. Тобто помилки зменшуються, але частина вдалих хвиль теж відсікається. Це не вирішення всієї задачі охоплення. Мітки хвиль ретроспективні: M5close,>=3ATR, відкат1ATR. Зараховується сигнал доpeak із>=1ATRзалишку таpeakв24h; залишок умовний на знайдених хвилях, не гарантований прибуток.

![Ілюстрації початків](successful_failed_examples.png)

Ілюстрації вибрано за labelлише для пояснення: successбіля медіанного годинного прогресу й найближчий за цим прогресом failure. Це два приклади, не статистичний доказ або навчальне правило.

## Перевірка входів та виконання

MARKET — openнаступногоM5, DELAY30 — openчерез30min, LIMIT025 — ліміт на0.25signalATR проти напряму з очікуванням1h. SL1.5signalATR/TP3signalATR від фактичногоfill; закриття не пізнішеsignal+24h. Не оптимізували SL/TP/hold/runner післяCHECK.

SL/TP перевірено поhigh-low: заодночасного торкання SLперший; stopgapзаopen, TPgapзаlimit; intrabarlimitfill не отримує оптимістичного TP на тому самому барі. Це консервативний OHLCreplay, не tickexact чи parityзliveMT5.

Спочатку незалежні події, потім причинний портфельmax2, включно зpendinglimit та зарезервованимиDELAY. Зайнятість перевіряється на сигналі; unfilledіblockedзбережені. Same-sideoverlaps дозволені. Ризик0.25% від **початкового**equity, безcompound. MTMDD за закриттямиM5, не intrabarworstcase.

Основне порівняння, CHECK2025–2026,7.5bps:

{table(headline)}

Ліміти виконуються лише на частині кандидатів, тому їхню EVне можна порівнювати як результат одних і тих самих угод. Повна таблиця execution_summary містить всі моделі50%, остаточні25/75%, всі3входи,3витрати, незалежні таportfolioрезультати. Не вибрано прибутковийCHECKваріант дляpromotion.

## Витрати та роки

bps — **задане сукупне roundtripприпущення** проfee/spread/slippage, не фактична специфікація брокера. ФормулаcostR = bps*0.0001*(entry+exit)/2/(1.5signalATR). Ціниfillне зсуваються додатково, витрати віднімаються агреговано; тому це не replayреального bid/ask.

{table(e[(e.selection=='OBSTACLES_50')&(e.period=='CHECK_2025_26')&(e.replay=='PORTFOLIO2')][['mode','cost_bps','n','EV','PF','R_month','mtm_dd_pct']])}

Marketbreak-evenдля всьогоCHECKблизько{gross.break_even_bps:.2f}bps, обчислено описово з уже отриманогоgrossR; не прогноз майбутньої допустимої вартості. При5bpsPFблизько1.02, що дає дуже малий запас.

{table(e[(e.selection=='OBSTACLES_50')&(e.replay=='PORTFOLIO2')&(e.cost_bps==7.5)&e.period.isin(['VALIDATION_2024','CHECK_2025','CHECK_2026'])][['period','mode','n','EV','PF','R_month','mtm_dd_pct']])}

2026 окремо позитивний,2024/2025 негативні. Змішаний результат не підтверджує стійкого торговогоedgeпісля7.5bps.

## Практичний висновок

Ми справді знайшли **невеликий відбір до входу**, а не лише більше стрілок. Однак за перевірених простих входів валова перевага приблизно0.08R, витрати приблизно0.10R. Наступна задача має стосуватися збільшення валовогоEV/ефективнішого виконання або іншого типу початку; ще одне додаванняshapegateсамо по собі тут не обґрунтовано. Не змінюємо productionбот на основі цих результатів.

Це повторно використана developmentісторія, не pristineOOS. Відсутній незалежний liveперіод, реальний brokerbid/ask і виміряний latency. Результат конкретної формалізації не доводить неможливості торгувати рухи взагалі.

## Відтворення й перевірки

Запуск зкореняResearchOS: `prepare.py`, `model.py`, `execution.py`, `verify_and_coverage.py`, `report.py` уlabs/LAB166_SUCCESS_FAILURE_ENTRY_EXECUTION_20261010. Потрібні непошкодженийLAB161dataset,LAB163context,LAB165signals/metrics,LAB161waves,profilekernelLAB162 та оригінальнийflowZIP. Залежностіnumpy,pandas,numba,scikit-learn,joblib,matplotlib. Великіruntimeкеші не включено, відновлюютьсяprepare.

Перевірки пройдено: exactLAB165signal/label/waveparity; featureprefixinvariance; sampledlabelrecompute; навчання/калібруванняpurge; modelreloadpredictionsparity; gap/double-touch/unfilledlimitfixtures; next-openpricing; horizon; max2pending+positions; PF/EV/costformulaповторно. В архіві всі події,відсіви,пороги,моделі,код,графіки,версії,sourcehashesіmanifest. Usergoal — більшепридатнихугод; його ще не досягнуто стійко післявитрат.
'''
 # Improve mixed-script spacing without altering code identifiers/numbers or numeric ranges.
 import re
 report=re.sub(r'([А-Яа-яІіЇїЄєҐґ])([A-Za-z0-9])',r'\1 \2',report);report=re.sub(r'([A-Za-z0-9])([А-Яа-яІіЇїЄєҐґ])',r'\1 \2',report)
 (O/'LAB166_REPORT_UK.md').write_text(report)
 import sklearn,numba,joblib
 (O/'versions.json').write_text(json.dumps(dict(python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__,sklearn=sklearn.__version__,numba=numba.__version__,joblib=joblib.__version__),indent=2));lineage=json.loads((R/'results/LAB161_20261010/LAB161_data_audit.json').read_text());(O/'lineage.json').write_text(json.dumps(lineage,indent=2))
 files=sorted([p for p in Path(__file__).parent.iterdir() if p.suffix in ['.py','.md']]+[p for p in O.rglob('*') if p.is_file() and p.suffix not in ['.log','.pkl'] and p.name!='manifest.json']);manifest={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files};(O/'manifest.json').write_text(json.dumps(manifest,indent=2));files.append(O/'manifest.json');dest=R/'artifacts/LAB166_SUCCESS_FAILURE_ENTRY_EXECUTION.zip'
 with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for p in files:z.write(p,p.relative_to(R))
 with zipfile.ZipFile(dest) as z:assert z.testzip() is None
 print('ARCHIVE',dest.stat().st_size,'bytes',flush=True);print(headline.to_string(index=False),flush=True);print(covsummary.to_string(index=False),flush=True)
if __name__=='__main__':main()
