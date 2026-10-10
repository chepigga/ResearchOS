from pathlib import Path
import pandas as pd,numpy as np,json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parents[2];O=R/'results/LAB160D_20261010'
a=pd.read_csv(O/'LAB160D_move_audit.csv',parse_dates=['start','peak','cutoff','end']);s=pd.read_csv(O/'LAB160D_summary.csv');c=pd.read_csv(O/'LAB160D_categories.csv');e=pd.read_csv(O/'LAB160D_examples.csv',parse_dates=['start','peak','cutoff','end']);t=pd.read_csv(O/'LAB160D_execution_trades.csv',parse_dates=['entry_time','exit_observed_time']);p=pd.read_pickle(O/'LAB160D_price_tape.pkl');g=pd.read_csv(O/'LAB160D_gate_flags.csv');sg=pd.read_csv(O/'LAB160D_single_gate_summary.csv')
def md(d):return '| '+' | '.join(d.columns)+' |\n| '+' | '.join(['---']*len(d.columns))+' |\n'+'\n'.join('| '+' | '.join(str(v) for v in row)+' |' for row in d.itertuples(index=False,name=None))
names={'POSITION_THROUGH_PEAK':'Позиція залишалася відкритою до піку','POSITION_EXITED_EARLY':'Позиція була, але закрилася до піку','EXIT_ON_PEAK_BAR':'Вихід на свічці піку, порядок невідомий','PORTFOLIO_BLOCKED':'Вчасний сигнал заблокований портфелем','PROFILE_FILTERED':'Вчасний raw-сигнал відсіяний профілем','LATE_CONFIRMATION':'Setup підтвердився після піку','NO_TIMELY_RAW_SIGNAL':'Немає вчасного raw-сигналу'}
# Deterministic median-shape examples; show actual observed close and same/opposite positions.
fig,axes=plt.subplots(3,2,figsize=(13,12))
for ax,row in zip(axes.flat,e.itertuples()):
 st=row.start;en=row.end;view=p.loc[st-pd.Timedelta(hours=2):en+pd.Timedelta(hours=2)];scale=p.loc[st,'atr'];xx=(view.index-st).total_seconds()/3600;yy=(view.close-row.start_price)/scale
 ax.plot(xx,yy,color='#243b60',lw=1.3);ax.axvline(0,color='#888',lw=.8,ls='--');peakx=(row.peak-st).total_seconds()/3600;ax.scatter([0,peakx],[0,row.side*row.amplitude_atr],color='#e99c25',s=30,zorder=5)
 trades=t[(t.entry_time<=view.index.max())&(t.exit_observed_time>=view.index.min())]
 for r in trades.itertuples():
  left=max((r.entry_time-st).total_seconds()/3600,xx.min());right=min((r.exit_observed_time-st).total_seconds()/3600,xx.max());ax.axvspan(left,right,color='#39a487' if r.side==row.side else '#d06169',alpha=.15)
 ax.set_title(row.category.replace('_',' '),fontsize=10,fontweight='bold',loc='left');ax.text(.02,.97,f'{row.move_id} · {st:%Y-%m-%d %H:%M} UTC\n{row.amplitude_atr:.2f} ATR · {row.duration_h:.1f}h',transform=ax.transAxes,va='top',fontsize=8,color='#576778');ax.set_xlabel('Hours from retrospective starting pivot');ax.set_ylabel('Close change / starting H1 ATR');ax.spines[['top','right']].set_visible(False);ax.margins(y=.25)
fig.suptitle('LAB160d | Why price moves had no matching position',x=.055,ha='left',fontsize=18,fontweight='bold');fig.text(.055,.955,'Orange: hindsight start / peak. Green shade: same-side position. Red shade: opposite-side position.',fontsize=10,color='#576778');fig.tight_layout(rect=[0,0,1,.94]);fig.savefig(O/'LAB160D_examples.png',dpi=130);plt.close(fig)
q=a[a.definition=='LEG_REV1ATR'];miss=q[q.positions_overlap==0]
ct=c[c.definition=='LEG_REV1ATR'].copy();ct['category']=ct.category.map(names);ct=ct[['category','n','pct']];ct.pct=ct.pct.round(2);ct.columns=['Причина / стан','Хвиль','% усіх хвиль']
summary=s[['definition','n','raw_coverage_pct','position_overlap_pct','positive_contribution_pct','no_position_pct']].round(2);summary.columns=['Визначення руху','N','Новий raw-сигнал, %','Позиція в напрямку, %','Позитивний внесок у напрямку, %','Без позиції в напрямку, %']
ex=e[['move_id','start','peak','side','amplitude_atr','category','best_single_trade_gross_capture_pct']].copy();ex['category']=ex.category.map(names);ex.amplitude_atr=ex.amplitude_atr.round(2);ex.best_single_trade_gross_capture_pct=ex.best_single_trade_gross_capture_pct.round(1)
y=q.groupby(q.start.dt.year).agg(n=('move_id','size'),position=('positions_overlap',lambda x:sum(x>0)));y['miss_pct']=(1-y.position/y.n)*100;y=y.round(2).reset_index();y.columns=['Рік','Хвиль','Із позицією в напрямку','Без позиції, %']
fg=g[g.definition=='LEG_REV1ATR'].sort_values('moves',ascending=False).head(14)[['gate','moves','denominator_without_position']]
sg=sg.sort_values('moves',ascending=False)
report=f'''# LAB160d — MISSED PRICE MOVE AUDIT

Виконано 2026-10-10. BTCUSDT, **2021–2024**, baseline **LAB159 R48_NOT_b / OLD_PROFILE**, stress7,5bps, risk0,25%, оригінальні execution та пріоритети LAB155. Вхідні дані та правила не змінено для покращення результату.

## Відповідь: скільки рухів залишається поза ботом

У базовому визначенні окремої хвилі **≥3 H1 ATR**, із підтвердженням розвороту1 ATR, знайдено **1863 хвилі**. Це приблизно38,8 на місяць, але вони визначені ретроспективно і не є готовими торговими можливостями.

- **1706 / 1863 = 91,6%** не мали відкритої позиції в напрямку руху протягом хвилі.
- **157 / 1863 = 8,4%** мали таку позицію; у65 хвилях була позиція, відкрита раніше початку хвилі.
- **149 / 1863 = 8,0%** мали позитивний net-R внесок однойменних позицій на момент піку;8 хвиль мали позицію, але цей внесок був непозитивним.
- **138** хвиль — позиція залишалася відкритою до піку; **19** — закрилася раніше.
- Серед157 хвиль із позицією медіана найкращого single-trade gross захоплення ціни — **50%**. Це опис ціни з урахуванням partial TP, не50% усіх прибутків і не частка доходу рахунку.
- На хвилі без однойменної позиції припадає **90,4% сумарної ATR-нормованої амплітуди** цієї вибірки. Це вага цінових рухів, не втрачений P/L.

Основна прогалина цього бота — **утворення своєчасного сигналу для інших класів руху**. Скасування ліміту позицій або зміна виходів не усуває відсутність сигналів у більшості хвиль.

## Чому це не ті самі87,6%, що раніше

Старе число87,6% означало «немає нового raw-сигналу в добовому вікні до піку». Воно не враховувало вже відкриту позицію. Для тих самих539 добових вікон:

-67 мали новий raw-сигнал після shape-фільтра;
-87 мали позицію у напрямку руху, включно з відкритою раніше;
-**452 / 539 = 83,9%** залишилися без такої позиції;
-69 мали позитивний directional net-R внесок до консервативної межі вимірювання.

Для годинних вікон і окремих хвиль різні знаменники; їх не складаємо і не називаємо одним універсальним відсотком.

{md(summary)}

`LEG_REV2ATR` — заздалегідь визначена чутливість до ширшого розвороту. Частка без позиції **90,9%** проти91,6% у базовій сегментації. Отже, великий розрив покриття не зникає після цієї зміни визначення.

## Операційні причини для1863 окремих хвиль

Категорії взаємовиключні: спочатку перевіряється фактична позиція, потім своєчасний eligible/raw-сигнал, потім запізніле підтвердження. Відсотки — від усіх1863 хвиль.

{md(ct)}

**1635 / 1706 = 95,8% хвиль без позиції** не мали вчасного raw-сигналу й не належать до окремо виділених profile/portfolio/late-confirmation випадків. «Немає raw-сигналу» не означає відсутність будь-яких змін Crowd/OI: базова подія могла бути, але повний набір умов setup не склався.

`PROFILE_FILTERED` означає, що у вікні був raw R48, який відсіяв NOT_b, але не було іншої однойменної позиції. Це **не доказ помилковості фільтра**: майбутній великий рух може виникнути після збиткового входу/стопа. LAB159 вимірює результати угод, а ця категорія — перетин із майбутнім рухом.

`LATE_CONFIRMATION` означає знайдений setup із початком до піку та підтвердженим входом після нього в заданому часовому контексті. Це не доказ, що можна безпечно торгувати до підтвердження.

## Які гейти не складалися

Відновлено **266895 оцінок кандидатів**, із них506 завершених raw-подій. Це не266895 незалежних setup: active-Z перевіряється повторно по свічках. Перед кожною хвилею без позиції перевірено кандидатів того самого напрямку від12h до старту й до піку; використовуються лише оцінки, вже відомі до межі піку.

Найчастіші **супутні** невиконані умови:

{md(fg)}

Ці числа **перекриваються**. Наприклад, біля одного руху могли бути різні кандидати з недостатнім extension, OI та невідповідною фазою. Не можна сказати, що зняття extension-гейта автоматично поверне1599 хвиль: інші умови й подальше підтвердження можуть залишитися невиконаними.

Окремо виділено випадки, коли у конкретної оцінки був лише один невиконаний поточний gate; це ближче до setup, але наступне SWING3/reclaim ще не гарантоване:

{md(sg)}

У72 хвилях без позиції взагалі не знайдено однойменного primitive-кандидата в цьому12h-контексті. Для решти наявність хоча б одного кандидата також не доводить прогностичного зв'язку з хвилею. Цей аудит локалізує обмеження механізму; він не вимірює причинний ефект скасування кожного гейта.

## Реальні приклади

Приклад для кожної категорії обрано механічно — найближчий до її медіанної амплітуди й тривалості, без відбору за прибутком.

![Цінові хвилі та позиції](LAB160D_examples.png)

{md(ex)}

У таблиці `side=1` BUY, `side=-1` SELL. Нуль захоплення для хвиль без позиції означає відсутність експозиції в напрямку, а не розрахований збиток від відмови торгувати. Червоне тло на графіку показує позицію проти напрямку хвилі, зелене — у напрямку.

## Стабільність за роками

{md(y)}

Жоден із чотирьох років не має широкого покриття цих цінових хвиль. Одна угода може перетинати кілька хвиль, тому157 хвиль із позиціями не дорівнюють157 окремим угодам.

## Як визначено рух і захоплення

**Clock:** ті самі UTC-якорі6/24/48h, максимум U/D≥3 ATR, terminal утримує≥50% домінантного відхилення. Reference — поточний закритий M5 close, ATR — останній закритий H1 SMA14 TR. Для high/low піку порядок усередині M5 невідомий, тому cutoff для сигналів і P/L — відкриття свічки піку. Позиція, що виходить на свічці піку, мала б окрему ambiguous-категорію; у наведеній вибірці таких випадків немає.

**Leg:** чергування close-півотів; новий розворот підтверджується відхиленням≥1 ATR від поточного екстремуму. ATR для підтвердження береться в екстремумі, для нормування амплітуди — у стартовому півоті. Початковий стан сіється першою валідною close-точкою періоду; наступні півоти визначаються розворотами. Враховуються завершені хвилі≥3 ATR; остання непідтверджена відкинута. Внутрішні часові інтервали не перекриваються. Півоти відомі тільки ретроспективно, **вхід у півот не симулюється**. Вхід точно на close піку вважається запізнілим.

**Захоплення:** для кожної фактичної однойменної угоди виміряна зміна її MTM від старту хвилі до cutoff, включно з partial TP та фактичним виходом. Уже відкриті позиції оцінюються від mark на старті; витрати повторно не списуються. Для нової позиції витрати списуються у момент входу. Виходи та partial за OHLC-bar припускаються відомими на close цієї свічки.

`best_single_trade_gross_capture_pct` = найбільший gross price-point внесок однієї угоди в цьому інтервалі / амплітуда хвилі. Це не net return: різні угоди мають різний ATR, можуть перекриватися, а ціни open/stop можуть бути кращими за close-півот. Тому значення не обрізається; у хвиль із позицією діапазон **−26,2%…113,0%**. Показник не можна віднімати від100% і називати результат «доступним втраченим прибутком».

`net_r_during_move` — сума внесків однойменних позицій, включно з нереалізованим результатом на піку. У повному CSV окремо є протилежні позиції (`opposite_net_r_during_move`) та сума обох напрямків (`all_sides_net_r_during_move`). Основна метрика покриття стосується саме напрямку руху, а не будь-якої відкритої угоди.

## Перевірки та межі висновку

- Відновлені pass-події точно збігаються з оригінальними мультимножинами: A181, B3_HIGH44, R48_HIGH134, EARLY_EPISODE147.
- Відновлено всі251 фактичні угоди OLD_PROFILE; net R збігається з LAB160c з точністю<1e-9. Часткові виходи й portfolio reject reasons записані окремо.
- Відтворено попереднє raw-покриття:61/877,67/539,70/345 для6/24/48h.
- Синтетичні тести перевірили pivot symmetry/nonoverlap, partial MTM, carried-position MTM та одноразове списання витрат. Таблиці причин і зв'язків узгоджені з кожною хвилею.
- Підготовка gate-даних, availability OI, видалення пропущених рядків і execution припущення успадковані від старого replay. Price-рухи рахуються на окремій регулярній price-only сітці. Це не нова перевірка tick fills чи publication lag.
- 2021–2024 вже досліджувалися. Це development-аудит, не pristine OOS. При іншому визначенні руху відсотки зміняться; sensitivity2ATR показана, але не охоплює всі можливі визначення.
- Немає оцінки oracle P/L, який бот міг би гарантовано заробити на всіх хвилях. Рух, видимий заднім числом, не тотожний прогнозованій можливості.

## Що це означає для наступного дослідження

Потрібно розширювати **класи розпізнаваних подій**, а не очікувати великого ефекту лише від concurrency або довшого утримання. Зокрема, дослідити, які price/Crowd/OI зміни повторюються перед непокритими хвилями й відрізняють їх від схожих станів без руху. Пропущені хвилі тут — labels для такого дослідження; обов'язковий контроль — усі аналогічні моменти, де сильного руху не було.

Саме такого прогнозного порівняння аудит не замінює. LAB160c уже показав, що просте послаблення Z може додавати збиткові угоди. Потрібен наступний тест умовної ймовірності й сили руху на всій вибірці, а потім transfer у доступний entry. Production не змінено.

## Відтворення та файли

Джерела: `btc_5m.zip`, SHA25613188498f1f9eadc98550237590734bf65ec865ebe927458301d038e533858bd; flow ZIP SHA256b6c80084751305f394270c4b133abbf89a0264634924891251b13b33afbe5e0d. Ті самі release `btc` і parent LAB160c.

З repo root, два ZIP у сусідньому `data/` або через `LAB160C_DATA`:

```bash
python3 labs/LAB160D_MISSED_MOVE_AUDIT_20261010/run_audit.py
python3 labs/LAB160D_MISSED_MOVE_AUDIT_20261010/enrich_audit.py
python3 labs/LAB160D_MISSED_MOVE_AUDIT_20261010/verify_audit.py
python3 labs/LAB160D_MISSED_MOVE_AUDIT_20261010/build_report.py
```

Dependencies: numpy,pandas,matplotlib. Пакет містить код, gate journal, price moves, поелементний аудит, links до фактичних угод, portfolio decisions, summaries, приклади й validation. Проміжна20MB price-tape pickle та source ZIP не включені; price tape відновлює `run_audit.py` для побудови графіка.
'''
(O/'LAB160D_REPORT_UK.md').write_text(report);print('report and chart ready')
