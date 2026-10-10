from pathlib import Path
import json
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parents[2];O=R/'results/LAB163_20261010';s=pd.read_csv(O/'LAB163_scenario_summary.csv');e=pd.read_csv(O/'LAB163_encounters.csv');q=pd.read_csv(O/'LAB163_scenarios.csv',parse_dates=['time','break_time','reentry_time','snapshot_time']);c=pd.read_csv(O/'LAB163_selected_candidates.csv');audit=json.loads((O/'LAB163_search_audit.json').read_text());d=pd.read_pickle(R/'results/LAB162_20261010/LAB162_tape.pkl');cx=pd.read_pickle(O/'LAB163_context.pkl')
def md(x):
 x=x.copy()
 for k in x:
  if pd.api.types.is_float_dtype(x[k]):x[k]=x[k].map(lambda v:f'{v:.2f}' if pd.notna(v) else '—')
 return '| '+' | '.join(map(str,x.columns))+' |\n| '+' | '.join(['---']*len(x.columns))+' |\n'+'\n'.join('| '+' | '.join(map(str,r))+' |' for r in x.itertuples(index=False,name=None))
base=s[s.grouping=='mode'][['split','mode','n','target_pct','stop_pct','timeout_pct','route_atr_median','risk_atr_median','rr_median']];higher=s[(s.grouping=='mode+higher_context')&(s.split=='CHECK')][['mode','higher_context','n','target_pct','stop_pct','rr_median']]
ctx=[]
for tf in ['D1','H4','H1','M15','M5']:
 for state,n in e[tf].value_counts().items():ctx.append(dict(tf=tf,state=state,n=int(n),pct=100*n/len(e)))
pd.DataFrame(ctx).to_csv(O/'LAB163_context_coverage.csv',index=False)
fig,ax=plt.subplots(1,2,figsize=(12,4.5));periods=['DISCOVERY','VALIDATION','CHECK']
for mode,color in [('ROLL24','#278e87'),('PRIOR_DAY','#ae823e')]:
 v=base[base['mode']==mode].set_index('split').loc[periods];ax[0].plot(range(3),v.target_pct,'o-',color=color,label=mode);ax[1].plot(range(3),v.rr_median,'o-',color=color,label=mode)
ax[0].set_ylabel('POC reached before invalidation, %');ax[1].set_ylabel('Median target distance / stop distance')
for a in ax:a.set_xticks(range(3),['2021–2023','2024','2025–2026']);a.spines[['top','right']].set_visible(False);a.legend(frameon=False);a.grid(axis='y',alpha=.15)
ax[0].set_ylim(30,60);fig.suptitle('LAB163 | Failed break → re-entry → failed retest → POC',fontsize=15,fontweight='bold');fig.tight_layout(rect=[0,0,1,.92]);fig.savefig(O/'LAB163_scenarios.png',dpi=140);plt.close(fig)
# A representative2024rolling-profile case, nearest median route and risk; no outcome selection.
x=q[(q.split=='VALIDATION')&(q['mode']=='ROLL24')].copy();x['dist']=abs(np.log(x.route_atr/x.route_atr.median()))+abs(np.log(x.risk_atr/x.risk_atr.median()));ex=x.sort_values(['dist','time']).iloc[0];ex.to_frame('value').to_csv(O/'LAB163_example.csv');v=d.loc[ex.break_time-pd.Timedelta(hours=12):ex.time+pd.Timedelta(hours=24)];tt=(v.index-ex.time).total_seconds()/3600;fig,axes=plt.subplots(2,1,figsize=(13,7),gridspec_kw={'height_ratios':[3,1.3]},sharex=True);axes[0].plot(tt,v.close,color='#2c4563',lw=1);p=d.loc[ex.snapshot_time]
for level,col in [('VAL','#7197b2'),('VAH','#7197b2'),('POC_HVN','#ae823e')]:axes[0].axhline(p[level],color=col,ls='--',lw=.8,label=level)
axes[0].axhline(ex.stop,color='#b75f59',ls=':',label='Invalidation');axes[0].legend(frameon=False,ncol=4)
for name,t,col in [('Break',ex.break_time,'#777'),('Re-entry',ex.reentry_time,'#278e87'),('Signal',ex.time,'#b75f59')]:axes[0].axvline((t-ex.time).total_seconds()/3600,color=col,ls=':',lw=.8)
tfs=['D1','H4','H1','M15','M5'];states=cx.loc[v.index,[t+'_trend' for t in tfs]].to_numpy().T;axes[1].imshow(states,aspect='auto',interpolation='nearest',cmap='RdYlGn',vmin=-1,vmax=1,extent=[tt.min(),tt.max(),4.5,-.5]);axes[1].set_yticks(range(5),tfs);axes[1].set_xlabel('Hours relative to signal (0)');axes[1].set_title('Causally available structure: red DOWN / yellow BALANCE / green UP',fontsize=10,loc='left');axes[0].set_title(f'{ex.time:%Y-%m-%d %H:%M} UTC | side={ex.side:+d} | outcome={ex.outcome} | representative, not selected for profit',fontsize=10,loc='left');axes[0].set_ylabel('BTCUSDT price');fig.tight_layout();fig.savefig(O/'LAB163_example.png',dpi=140);plt.close(fig)
report=f'''# LAB163 — D1 → H4 → H1 → M15 → M5 × PROFILE

Виконано2026-10-10. BTCUSDT2021–доступний серпень2026. Parent LAB162 `bbe97e66e5276b123482571b65176bed65b72f18`. M1 не використовується. Production без змін.

## Результат

**Додавання цього конкретного визначення багатомасштабного контексту не дало підтвердженого стабільного покращення.** Воно відокремило деякі різні ситуації, але найсильніша відібрана перевага2021–2024 не повторилася у2025–2026. Це не доказ, що тренд неважливий або будь-яка торгівля профілем неможлива.

Також перевірено конкретний сценарій **вихід за VAH/VAL → повернення всередину value → невдалий повторний вихід → POC**. У пізнішому періоді POC досягався раніше інвалідації приблизно44% часу. Число не є PF або торговим winrate: тут close-бар'єри без виконання й витрат, різні відстані доцілі/інвалідації та окремі timeout.

## Як визначено контекст без майбутніх даних

Для D1/H4/H1/M15/M5 агрегація за UTC, лише повністю закриті свічки. Swing high/low підтверджується двома свічками ліворуч і двома праворуч; стає відомим лише на close другої правої. UP — останні два підтверджені максимуми та мінімуми обидва зростають; DOWN — обидва падають; інакше BALANCE. До появи двох екстремумів обох типів — UNKNOWN. Фаза IMPULSE/PULLBACK — знак останнього3-свічкового руху відносно структурного напрямку.

Узгодження всіх таймфреймів не вимагалося. ПеревіреноWITH/AGAINST/BALANCE щодо напрямку підходу, поєднання старших трендів, H1відкат/імпульс, локальні M15/M5 та форми профілю/OI/Crowd. Це операційна розмітка, не єдине можливе визначення тренду; підтвердження екстремумів має природну затримку.

## Контакти з рівнями: сильний кандидат не втримався

Збережено рівно ті самі19665подій LAB162 (19662 після6h-purge), ті самі рівні та результати±1ATR за6h від close контакту. База порівняння — той самий рівень, тип close та напрямок підходу.

Розглянуто8258комірок десяти наперед заданих сімейств,16516порівнянь PASS/REJECT. Лише157комірок мають достатню підтримку discovery≥100подій/20тижнів і validation≥30/10тижнів. Порогові вимоги приросту≥10п.п. у2021–2023 та≥5п.п. у2024 пройшли2рядки, але **це один і той самий набір подій**, а не дві незалежні знахідки: H1=BALANCE автоматично має фазуFLAT.

Єдиний сценарій: підхід вниз доPOC/HVN, контакт закрився назад над рівнем, структураH4проти підходу (UP), H1=BALANCE. Частка подальшого проходу вниз на1ATR раніше зустрічного1ATR:

| Період | N | У сценарії | У відповідній базі | Різниця |
|---|---:|---:|---:|---:|
|2021–2023|112|48,2%|36,7%|+11,5п.п.|
|2024|32|50,0%|38,5%|+11,5п.п.|
|2025–2026|52|25,0%|39,7%|−14,7п.п.|

Тижневий bootstrap95%CI різниці уCHECK:−25,0…−4,9п.п. Результат змінив знак; не переносимо його в бот. Інтервал умовний на цей пошук, без заяви про pristineOOS та без корекції всієї історії багаторазових досліджень. Пороги після результату не послаблено.

## Конкретна послідовність failed break

Два фіксовані профілі: ROLL24 — trailing24h перед breakout; PRIOR_DAY — профіль останнього завершеного UTC-дня, доступний перед breakout. POC/VAL/VAH іATR на breakout заморожуються.

Правила: breakout-close заVAH/VAL на0,1ATR із попередньогоclose всерединіvalue; повернення всередину протягом6h; повторний тест межі протягомнаступних3h іclose≥0,1ATR назад усередині. На сигнал у бікPOC потрібно≥0,5поточногоATR доцілі. Інвалідація — за екстремумом усього відрізка breakout→trigger плюс0,1breakoutATR. Горизонт24h, перша close-подіяPOC/інвалідація/timeout. Один pending сценарій на режимпрофілю, cooldown6h. Однакові епізоди двох режимів можуть перекриватися.

Усього2817сценаріїв до24h-purge. Всі правила задано до результатів. Профіль останнього балансу/імпульсу тут ще не реалізований: перевірено саме rolling24h і попередній UTC-день.

{md(base)}

![Сценарії](LAB163_scenarios.png)

`rr_median` — медіана відношення початкових цінових відстаней доPOC та інвалідації. Її не можна множити на агреговану частку успіхів і називати отриманий результатEV: розміри та результати пов'язані, timeout має окремий шлях. Показники не враховують execution та costs.

## Старший контекст сценарію в2025–2026

HIGHER_WITH: D1іH4 у напрямку сигналу наPOC; HIGHER_AGAINST: обидва проти; MIXED_BALANCE: інші відомі поєднання.

{md(higher)}

ПриROLL24 узгодженняD1/H4 має46,2% досягненняPOC проти38,5% при протилежному контексті, але **лише39випадків у кожній групі**. УPRIOR_DAY картина інша:37,5% за старшим напрямком проти48,6% проти нього (32/35випадків). Це малі й неоднорідні групи, а не підтверджене правило «торгувати тільки за трендом».

Повні таблиці заформаюP/B/b/D та поєднаннямH1/M15 збережені, але кращі дрібні підгрупи не оголошуються новими переможцями після переглядуCHECK.

## Приклад із контекстом

Приклад2024ROLL24 обрано найближчим до медіан відстані доPOC та інвалідації, без вибору за результатом. Горизонтальні рівні заморожені передbreakout; нижче — контекст, який реально був відомий на кожномуclose. Нульчасу — підтвердженийсигнал; це дослідницькийсценарій, не виконанаугода.

![Контекст сценарію](LAB163_example.png)

## Перевірки й межі

- Синтетично перевірено затримку підтвердженнясвінгу, prefixinvariance, оновленнястаршихTF лише наїхclose.
- Контактнірезультати точно збігаються зLAB162; рівніscenario відомідоbreakout; trigger пізнішеre-entry; cooldown іpurge перевірені.
- Перераховано результати на вибірці кожного7-госценарію без використання збереженогоoutcome; значеннязбігаються.
- ПочатковийUNKNOWN збережено, даніне домальовано; D1 стаєдоступним2021-01-14. Часткиконтекстів уLAB163_context_coverage.csv.
- Profile реконструйованоізM5volume,24h/40bins; B — структурнийдвогорбийLAB162, не старийDOUBLE. Затримкаflow5хв — припущенняджерела, не перевіренаliveдоставка.
- H1phase — лише рухостанніх3закритихбарів відносноструктури. Це не повна семантика імпульсу/відкату, не ручна розміткаграфіка. Існують інші визначення, але їх не підбирали заCHECK.
- Множинністькомбінацій велика, більшістькомірок малі. Негативнийрезультат обмежений цимконкретнимпротоколом. Роки вже використовувалисяпроектом, тож це не pristineOOS.
- Немає прибутковості/PF/DD або зміниproduction. Наявність тренду не гарантує прогнозованоїреакції конкретного рівня.

## Відтворення

ПотрібенвідновлюванийLAB162_tape.pkl іLAB162_encounters.csv ізпопередньогоLAB. Джерела/hash успадкованіLAB162. Запускізrepo root:

```bash
python3 labs/LAB163_MULTITIMEFRAME_PROFILE_CONTEXT_20261010/run.py
python3 labs/LAB163_MULTITIMEFRAME_PROFILE_CONTEXT_20261010/analyze.py
python3 labs/LAB163_MULTITIMEFRAME_PROFILE_CONTEXT_20261010/verify.py
python3 labs/LAB163_MULTITIMEFRAME_PROFILE_CONTEXT_20261010/build_report.py
```

Архів: код, протокол, M5-рядкиконтекстуCSV.gz, всіcontact/scenarioподії, повнікомірки, summaries, графіки, перевірки. Проміжнийcontext.pkl відтворюється run.py і не включений.
'''
import re
report=re.sub(r'([А-Яа-яІіЇїЄєҐґ])([A-Za-z0-9])', r'\1 \2', report)
report=re.sub(r'([A-Za-z0-9])([А-Яа-яІіЇїЄєҐґ])', r'\1 \2', report)
for old,new in {'доступним2021':'доступним 2021','доступнийсерпень':'доступний серпень','доступнідані':'доступні дані','напередзаданих':'наперед заданих','свінгу':'свінгу','затримку підтвердженнясвінгу':'затримку підтвердження свінгу','оновленнястарших':'оновлення старших','лише наїх':'лише на їх','Контактнірезультати':'Контактні результати','дослідницькийсценарій':'дослідницький сценарій','виконанаугода':'виконана угода','рівніscenario':'рівні scenario','Спільнийконтекст':'Спільний контекст','даніне':'дані не','Затримкаflow':'Затримка flow','Неочікуванийрезультат':'Неочікуваний результат','Негативнийрезультат':'Негативний результат','цимконкретнимпротоколом':'цим конкретним протоколом','використовувалисяпроектом':'використовувалися проектом','Множинністькомбінацій':'Множинність комбінацій','більшістькомірок':'більшість комірок','розміткаграфіка':'розмітка графіка','семантика імпульсу/відкату':'семантика імпульсу/відкату','Потрібенвідновлюваний':'Потрібен відновлюваний','ізпопереднього':'із попереднього','Запускіз':'Запуск із','Протоколбез':'Протокол без','Повнітаблиці':'Повні таблиці','Повнікомірки':'Повні комірки'}.items():report=report.replace(old,new)
(O/'LAB163_REPORT_UK.md').write_text(report);print('REPORT READY')
