from pathlib import Path
import json,hashlib,zipfile,shutil
import pandas as pd,numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parents[2];O=R/'results/LAB165_20261010';OLD=R/'results/LAB161_20261010'
def table(d):
 def fmt(x):return f'{x:.2f}' if isinstance(x,(float,np.floating)) else str(x)
 return '\n'.join(['| '+' | '.join(d.columns)+' |','| '+' | '.join(['---']*len(d.columns))+' |']+['| '+' | '.join(fmt(x) for x in r)+' |' for r in d.itertuples(index=False,name=None)])
def main():
 m=pd.read_csv(O/'metrics.csv');q=m[m.period=='CHECK_2025_26'].copy();same=pd.read_csv(O/'same_wave_comparison.csv');th=pd.read_csv(O/'thresholds.csv');s=pd.read_csv(O/'signals.csv.gz');a=pd.read_csv(O/'wave_matches.csv.gz');default=q[q.policy=='PRICE_CROWD_OI_PROFILE_R4'].iloc[0];old=same[same.policy=='PRICE_CROWD_OI_PROFILE_R4'].iloc[0]
 # Export model files plus selected configuration, not a production deployment.
 md=O/'models';md.mkdir(exist_ok=True)
 for year in [2024,2025,2026]:
  for name in ['PRICE','PRICE_CROWD_OI_PROFILE']:shutil.copy2(OLD/f'models/{year}_{name}.joblib',md/f'{year}_{name}.joblib')
 config=dict(policy='PRICE_CROWD_OI_PROFILE_R4',evaluation_only=True,score='max(P_UP,P_DOWN)',direction='argmax(P_UP,P_DOWN)',cooldown_minutes=60,requires='Causal LAB161 feature construction at closed M5, eligible input rows; persist last signal timestamp across calls/restarts',calibrations=th[th.policy=='PRICE_CROWD_OI_PROFILE_R4'].to_dict('records'),current_live_deployment=False);(O/'detector_config.json').write_text(json.dumps(config,indent=2))
 fig,ax=plt.subplots(1,3,figsize=(15,4.5))
 for family,label in [('PRICE','Price'),('PRICE_CROWD_OI_PROFILE','Price+Crowd+OI+profile'),('CLOCK_1H_MOMENTUM','Scheduled 1h momentum')]:
  ids=[f'{family}_R{rate}' for rate in [2,4,8,12]];v=q.set_index('policy').loc[ids]
  for j,col in enumerate(['coverage_pct','false_pct','median_remaining_atr']):ax[j].plot(v.per_day,v[col],'o-',label=label)
 for j,title in enumerate(['Independent wave coverage, %','False +3/-1.5 ATR labels, %','Remaining ATR (recognized waves)']):ax[j].set_title(title);ax[j].set_xlabel('Actual alerts per day');ax[j].grid(alpha=.2)
 ax[0].legend(fontsize=7);fig.suptitle('LAB165 — CHECK 2025–2026, fixed earlier-year thresholds');fig.tight_layout();fig.savefig(O/'coverage_tradeoff.png',dpi=150);plt.close(fig)
 fields=['policy','per_day','recognized','waves','coverage_pct','false_pct','median_remaining_atr','clean_coverage_pct'];brief=q[fields];annual=m[(m.policy=='PRICE_CROWD_OI_PROFILE_R4')&m.period.isin(['2024','2025','2026'])]
 report=f'''# LAB165 — BROAD COVERAGE DETECTOR

Завершено 2026-10-10. **Охоплення розширено шляхом зміни детектора, без обов'язкового балансу, ретесту чи жорсткого profile/Z gate.** Це дослідницький генератор сигналів, production EA не змінений.

## Конкретний результат

Фіксований до розрахунку основний режим — FULL, орієнтир4 сигнали/добу, глобальна пауза1h. На CHECK2025–2026: **{default.recognized:.0f}/{default.waves:.0f} хвиль = {default.coverage_pct:.2f}%**, фактично {default.per_day:.2f} сигналів/добу. На тому самому наборі хвиль LAB164 розпізнав {old.lab164_recognized:.0f}; новий режим додав {old.additional_vs164:.0f} раніше не розпізнаних, водночас пропустив {old.missed_old:.0f} з тих, що бачив LAB164. Це не об'єднання двох стратегій.

Ціна розширення: **{default.false_pct:.2f}% хибних міток** за критерієм +3ATR раніше за−1.5ATR у24h. Це не відсоток збиткових угод. Медіанний залишок до вершини серед розпізнаних хвиль — {default.median_remaining_atr:.2f} ATR; без ретроспективної вершини він наперед невідомий.

## Що змінено

Використано заморожені причинні моделі LAB161: PRICE та PRICE+Crowd+OI+PROFILE. Кожен доступний M5 оцінюється без вимоги конкретного патерну. Напрямок — більша з оцінок UP/DOWN, якість — її значення. Пауза знижена з6h до1h. Пороги для2/4/8/12 сигналів/добу калібровано **лише на попередньому році за частотою**, без використання результатів наступного року. Порогова частота не є жорстким денним лімітом.

PRICE охоплює різні масштаби до24h та ширші діапазони; тут не додавали структурні ознаки D1/H4 з LAB163, щоб ізолювати зміну політики сигналів. PROFILE — trailing24h legacy D/P/b/DOUBLE з LAB161, не anchored profile LAB164. Розширення не є новим доказом переваги профілю. M1 не використано.

Окремий контроль CLOCK — фіксовані UTC години з напрямком останньої години. Він показує, скільки охоплення можна отримати просто більшою кількістю спроб. Його фактична частота може відрізнятися від каліброваних моделей; це наближене, не точне зрівнювання кількості сигналів.

## Повна таблиця CHECK2025–2026

{table(brief)}

OLD6H_R2 — незмінний старий детектор LAB161. R2/R4/R8/R12 — новий cooldown1h. Усі варіанти наведено, переможця за майбутнім прибутком не обирали.

![Охоплення і помилки](coverage_tradeoff.png)

## Що показав контроль

CLOCK_R4 охопив46.13% хвиль при3.99 сигнала/добу, але74.48% хибних міток. FULL_R4 охопив24.11% при5.22 сигнала/добу та68.18% хибних. Отже, модель знижує частку хибних міток, але концентрує сигнали в меншій кількості хвиль; її перевага для широкого пошуку не встановлена. Це порівняння різної фактичної частоти, без твердження статистичної значущості.

За малих цільових частот скорочення cooldown саме по собі може **зменшити** охоплення: FULL_R2 дає12.67% проти21.89% старого OLD6H_R2, попри більше сигналів. Поріг, відкалібрований під коротшу паузу, допускає скупчення спроб у сильних локальних оцінках. Тому збережено повну криву, а не твердження, що кожне послаблення покращує всі показники.

Режим FULL_R4 зафіксований як дослідницький варіант до результатів, не оголошується найкращим. Для максимально широкого переліку кандидатів CLOCK_R12 покриває78.35%, проте74.72% його міток хибні. Це вже широкий пошук, а не доказ готової торгової стратегії.

## Стабільність основного режиму за роками

{table(annual[['period']+fields[1:]])}

## Порівняння з LAB164 на однакових хвилях

{table(same)}

Сирі 4.2% LAB164 і показники LAB165 не порівнюємо напряму: для цього розрахунку залишено тільки спільне часове вікно та однакові ідентифікатори хвиль. Попередні91.6% стосувалися іншого періоду й фактичних позицій. Також не порівнюємо успішність+2/−1ATR LAB164 з+3/−1.5ATR LAB165.

## Методика й межі

Хвилі — успадковані M5close рухи амплітудою>=3H1ATR, підтверджені відкатом1ATR. Кожну хвилю рахують один раз на політику. Сигнал має бути потрібного напрямку після початку хвилі та до вершини, зі щонайменше1ATR залишку й вершиною в межах24h. Додатково збережено охоплення із залишком2/3ATR, частку хвиль із хоча б одним чистим+3/−1.5 сигналом, повторні сигнали всередині хвилі та хвилі на100 сигналів.

Велике охоплення саме по собі не означає edge: один рух може отримати багато стрілок. Висока частка хибних сигналів потребує окремого дослідження входу/ризику; цей LAB не симулює fills,SL/TP,costs чи portfolio. Залишковий рух обчислено умовно на вже відомих розпізнаних хвилях. Це не гарантований доступний прибуток.

Історія вже використовувалася в попередніх LAB. Хоча моделі навчалися на минулому, цей аналіз не pristine OOS. Моделі не перенавчали й пороги не оптимізували за хвилями CHECK. Оцінки UP/DOWN не оголошуються каліброваними торговими ймовірностями.

## Що готове для повторного використання

`detector.py`: пакетний emit і станний AlertDetector з однаковою логікою. `detector_config.json`: фіксований режим4/добу й пороги кожного року. `models/`: шість заморожених моделей з feature lists. Для запуску потрібен причинний розрахунок ознак LAB161 на закритих M5; часу останнього сигналу потрібно надати збереження між перезапусками. Це не встановлений MT5 індикатор та не зміна активного бота. Пороги2026 не видаються за відкалібровані для майбутнього2027.

Відтворення з кореня ResearchOS: `python3 labs/LAB165_BROAD_COVERAGE_DETECTOR_20261010/run.py`, потім аналогічно `report.py`. Потрібні LAB161_dataset.pkl, його frozen models/predictions/folds/waves та LAB164_wave_matches. Залежності numpy,pandas,scikit-learn,joblib,numba,matplotlib. Вхідні кеші створюються попередніми LAB, не дублюються в архіві.

Перевірки: точна відповідність старих охоплень LAB161; prefix parity пакетного й послідовного detector; cooldown; часовий purge навчання/калібрування. Усю частоту й coverage рахували на однакових eligible M5 та хвилях. Відсутні/неякісні дані й особливості OI/L/S успадковані з LAB161; це не новий аудит джерел.
'''
 (O/'LAB165_REPORT_UK.md').write_text(report)
 files=sorted([p for p in Path(__file__).parent.iterdir() if p.suffix in ['.py','.md']]+[p for p in O.rglob('*') if p.is_file() and p.suffix!='.log' and p.name!='manifest.json']);manifest={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files};(O/'manifest.json').write_text(json.dumps(manifest,indent=2));files.append(O/'manifest.json');dest=R/'artifacts/LAB165_BROAD_COVERAGE_DETECTOR.zip'
 with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for p in files:z.write(p,p.relative_to(R))
 print('ZIP bytes',dest.stat().st_size);print(brief.to_string(index=False));print('DEFAULT COMPARISON',old.to_dict())
if __name__=='__main__':main()
