from pathlib import Path
import json
import pandas as pd,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parents[2];O=R/'results/LAB162_20261010';d=pd.read_pickle(O/'LAB162_tape.pkl');w=pd.read_csv(O/'LAB162_wave_anatomy.csv',parse_dates=['start','peak','end']);w=w[w.definition=='LEG_REV1ATR'];a=pd.read_csv(O/'LAB162_wave_trajectories.csv');a=a[a.definition=='LEG_REV1ATR'];e=pd.read_csv(O/'LAB162_encounters.csv',parse_dates=['time']);ll=pd.read_csv(O/'LAB162_lead_lag_descriptive.csv');audit=json.loads((O/'LAB162_search_audit.json').read_text());LEVELS=['POC_HVN','VAL','VAH','HVN2','LVN']
def md(x):
 x=x.copy()
 for k in x:
  if pd.api.types.is_float_dtype(x[k]):x[k]=x[k].map(lambda v:f'{v:.3f}' if pd.notna(v) else '—')
 return '| '+' | '.join(map(str,x.columns))+' |\n| '+' | '.join(['---']*len(x.columns))+' |\n'+'\n'.join('| '+' | '.join(map(str,r))+' |' for r in x.itertuples(index=False,name=None))
# Overview: relative phase medians are hindsight descriptions, not tradable timing.
phase=a[((a.anchor=='START')&(a.position==0))|((a.anchor=='PEAK')&(a.position==0))|(a.anchor=='FRACTION')].copy();phase['fraction']=np.where(phase.anchor=='START',0,np.where(phase.anchor=='PEAK',1,phase.position))
fig,axs=plt.subplots(2,3,figsize=(15,9))
for col,title,ax in zip(['price_from_start_atr','oi_from_start_pct','ratio_from_start_pct'],['Price change, direction-aligned ATR','OI quantity change, %','L/S ratio change, %'],axs[0]):
 for side,color,label in [(1,'#208b7c','UP waves'),(-1,'#c26157','DOWN waves')]:
  q=phase[phase.side==side].groupby('fraction')[col].median();ax.plot(q.index,q,'o-',color=color,label=label)
 ax.set_title(title,loc='left',fontsize=11,fontweight='bold');ax.set_xlabel('Retrospective wave progress');ax.axhline(0,color='#888',lw=.6);ax.legend(frameon=False,fontsize=9)
ct=pd.crosstab(w.shape_start,w.shape_peak).reindex(index=['D','P','b','B'],columns=['D','P','b','B'],fill_value=0);pct=ct.div(ct.sum(axis=1),axis=0)*100;axs[1,0].imshow(pct,cmap='Blues',vmin=0,vmax=60);axs[1,0].set_xticks(range(4),ct.columns);axs[1,0].set_yticks(range(4),ct.index);axs[1,0].set_xlabel('Shape at peak');axs[1,0].set_ylabel('Shape at start');axs[1,0].set_title('Profile transitions (% within starting shape)',loc='left',fontsize=10,fontweight='bold')
for i in range(4):
 for j in range(4):axs[1,0].text(j,i,f'{pct.iloc[i,j]:.0f}%',ha='center',va='center',color='white' if pct.iloc[i,j]>35 else '#24384b')
q=e[e.split=='CHECK'].groupby('level')[['pass_hit','reject_hit','unresolved']].mean().reindex(LEVELS)*100;bottom=np.zeros(5)
for col,colr,label in [('pass_hit','#208b7c','+1 ATR first'),('reject_hit','#c26157','-1 ATR first'),('unresolved','#cbd2d8','Neither in 6h')]:axs[1,1].bar(range(5),q[col],bottom=bottom,color=colr,label=label);bottom+=q[col].to_numpy()
axs[1,1].set_xticks(range(5),['POC/HVN','VAL','VAH','HVN2','LVN'],rotation=20);axs[1,1].set_title('All encounters: 2025–2026 check',loc='left',fontsize=11,fontweight='bold');axs[1,1].legend(frameon=False,fontsize=8);axs[1,1].set_ylabel('% of encounters')
for feature,color in [('LS_change_1h','#208b7c'),('OI_change_1h','#c26157'),('POC_change_1h','#b58d3b')]:
 z=ll[(ll.feature==feature)&(ll.price_window=='price_next_1h')];axs[1,2].plot(z.year,z.spearman,'o-',color=color,label=feature.replace('_change_1h',''))
axs[1,2].axhline(0,color='#777',lw=.7);axs[1,2].set_ylim(-.15,.15);axs[1,2].set_title('Past 1h change vs NEXT 1h price',loc='left',fontsize=11,fontweight='bold');axs[1,2].set_ylabel('Spearman correlation');axs[1,2].legend(frameon=False,fontsize=9)
for ax in axs.flat:ax.spines[['top','right']].set_visible(False)
fig.suptitle('LAB162 | What accompanies a price wave?',x=.06,ha='left',fontsize=20,fontweight='bold');fig.text(.06,.93,'Wave anatomy is retrospective. Encounter outcomes begin after the contact candle closes.',fontsize=11,color='#56687a');fig.tight_layout(rect=[0,0,1,.91]);fig.savefig(O/'LAB162_overview.png',dpi=140);plt.close(fig)
# Representative examples: one per initial structural shape, nearest median amplitude/duration in2024.
examples=[]
for shape in ['D','P','b','B']:
 q=w[(w.year==2024)&(w.shape_start==shape)&(w.duration_h<=24)&w.oi_change_pct.notna()&w.ratio_change_pct.notna()].copy();q['distance']=abs(np.log(q.amplitude_atr/q.amplitude_atr.median()))+abs(np.log(q.duration_h/q.duration_h.median()));examples.append(q.sort_values(['distance','move_id']).iloc[0])
examples=pd.DataFrame(examples);examples.to_csv(O/'LAB162_examples.csv',index=False);fig,axes=plt.subplots(4,3,figsize=(16,13))
for row,ww in enumerate(examples.itertuples()):
 start=ww.start;peak=ww.peak;st=d.loc[start];fixed=d.loc[start-pd.Timedelta(minutes=5)];v=d.loc[start-pd.Timedelta(hours=3):peak+pd.Timedelta(hours=3)];x=(v.index-start).total_seconds()/3600;end=(peak-start).total_seconds()/3600
 axes[row,0].plot(x,(v.close-st.close)/st.atr,color='#253d5a',lw=1.3,label='Close');axes[row,0].plot(x,(v.POC_HVN-st.close)/st.atr,color='#a7802e',ls='--',label='Moving POC')
 for level,color in [('POC_HVN','#a7802e'),('VAL','#788bb6'),('VAH','#788bb6'),('HVN2','#b87b8e'),('LVN','#7e9b65')]:
  if np.isfinite(fixed[level]):axes[row,0].axhline((fixed[level]-st.close)/st.atr,color=color,lw=.7,ls=':',label='Fixed '+level)
 axes[row,1].plot(x,100*(v.oi_quantity/st.oi_quantity-1),color='#208b7c');axes[row,2].plot(x,100*(v.ratio/st.ratio-1),color='#b5685e')
 for ax in axes[row]:ax.axvline(0,color='#999',ls='--',lw=.8);ax.axvline(end,color='#999',ls='--',lw=.8);ax.axvspan(0,end,color='#d8e2eb',alpha=.22);ax.spines[['top','right']].set_visible(False);ax.set_xlabel('Hours from starting pivot')
 axes[row,0].set_title(f'{ww.shape_start} → {ww.shape_peak} | {ww.move_id} | {start:%Y-%m-%d}',fontsize=10,loc='left',fontweight='bold');axes[row,0].set_ylabel('Price / starting ATR');axes[row,1].set_title('OI quantity change (%)',fontsize=10,loc='left');axes[row,2].set_title('L/S ratio change (%)',fontsize=10,loc='left')
axes[0,0].legend(frameon=False,fontsize=6,ncol=2);fig.suptitle('LAB162 | Four mechanically selected wave examples',x=.06,ha='left',fontsize=20,fontweight='bold');fig.text(.06,.945,'Shaded: hindsight wave. Horizontal levels frozen BEFORE start. Dashed gold: moving POC.',fontsize=11,color='#56687a');fig.tight_layout(rect=[0,0,1,.93]);fig.savefig(O/'LAB162_examples.png',dpi=130);plt.close(fig)
# Tables used verbatim in report, with transparent denominators.
flow=w.groupby('side').agg(waves=('move_id','size'),oi_valid=('oi_change_pct','count'),oi_median_pct=('oi_change_pct','median'),ls_valid=('ratio_change_pct','count'),ls_median_pct=('ratio_change_pct','median'),poc_migration_median_atr=('poc_migration_atr','median')).reset_index();flow.to_csv(O/'LAB162_direction_summary.csv',index=False)
near=[]
for level in LEVELS:
 for typ in ['fixed','prior']:
  v=w[f'peak_dist_{typ}_{level}'].dropna();near.append(dict(level=level,snapshot=typ,valid_waves=len(v),near_peak_pct=100*(v<=.25).mean()))
near=pd.DataFrame(near);near.to_csv(O/'LAB162_peak_proximity.csv',index=False);check=e[e.split=='CHECK'].groupby('level').agg(n=('event_id','size'),pass_pct=('pass_hit',lambda s:100*s.mean()),reject_pct=('reject_hit',lambda s:100*s.mean()),unresolved_pct=('unresolved',lambda s:100*s.mean())).reset_index();check.to_csv(O/'LAB162_check_level_summary.csv',index=False)
llp=ll[ll.price_window=='price_next_1h'].pivot(index='year',columns='feature',values='spearman').reset_index();fixedcols=[f'peak_dist_fixed_{k}' for k in LEVELS];anynear=100*(w[fixedcols].min(axis=1)<=.25).mean();stationary=100*(w.poc_migration_atr.abs()<.25).mean()
report=f'''# LAB162 — PRICE WAVE × PROFILE TRANSITIONS × OI × CROWD

Виконано 2026-10-10. BTCUSDT, 2021–10 серпня 2026. Parent LAB161 `c254ca9e76e2103ba23de130edf4ded4c62a4bd5`. Production без змін.

## Відповідь

**Взаємозв'язки постфактум є, але проста універсальна схема «цей профіль/вузол штовхає або зупиняє ціну» не підтвердилася.** У значних висхідних хвилях L/S у медіані падає на4,42%, у низхідних зростає на4,43%. OI змінюється значно неоднорідніше. Це опис того, що відбулося всередині вже відібраних хвиль, а не доказ, що зміна L/S випереджала рух або спричинила його.

Дослідження включає **2680 хвиль** основного1ATR-визначення та2363 хвилі2ATR-чутливості,115984 вирівняні спостереження й43519 внутрішніх сегментів (два визначення не складаємо як незалежні рухи). Для незалежної від відбору хвиль перевірки — **19662 взаємодії з рівнями** після6h-purge,18781 унікальний час події. До purge19665 подій; у2024 видалено3 події з невалідним поточним OI.

![Огляд](LAB162_overview.png)

## 1. Що відбувається всередині хвилі

{md(flow)}

`side=1` — висхідна хвиля; `side=-1` — низхідна. OI — кількість контрактів, L/S — співвідношення кількості long/short-акаунтів, а не доларові позиції. Відсотки — медіана відносної зміни від стартового до кінцевого close-екстремуму. Кількість валідних flow-спостережень показана окремо.

Рух часто супроводжується зміною L/S проти напрямку ціни. Це сумісно з контртрендовою поведінкою вимірюваної групи акаунтів, але не ідентифікує конкретних покупців/продавців, ліквідації чи причину руху. OI в середньому не розрізняє «відкривали long» і «відкривали short»: кожен контракт має обидві сторони.

**POC зазвичай рухається набагато повільніше:** у{stationary:.1f}% хвиль його абсолютне переміщення від передстартового профілю до піку менше0,25 стартовогоATR. Для trailing24h-профілю на хвилях медіанної тривалості кілька годин це важлива практична межа: старий головний вузол не обов'язково пересувається разом із поточним імпульсом.

Форма профілю також часто змінюється всередині хвилі. Матриця нижче — кількості, без трактування як ймовірностей майбутнього руху; ми вже відібрали великі хвилі:

{md(ct.reset_index())}

Траєкторії до старту та до/після піку збережено для−12/−6/−3/−1/0/+0,5/+1/+3/+6/+12годин, а також25/50/75% тривалості хвилі. Внутрішні імпульси/відкати виділені порогом0,5стартовогоATR; вони ретроспективні й не є готовими входами.

## 2. Чи зупиняються хвилі біля профілю

Для кожної хвилі зафіксовано профіль **за одну M5-свічку до її старту**. Окремо виміряно рівні з останньої свічки перед піком. «Близько» = не далі0,25ATR на момент піку; вимірювання за close, не за тінню.

{md(near)}

`fixed` — перед стартом; `prior` — перед піком. Усього лише{anynear:.1f}% хвиль завершують close-екстремум поблизу хоча б одного з п'яти зафіксованих рівнів. Це не означає, що обсяг не впливає на ринок: результат залежить від24h-вікна,40bins, порога0,25ATR, close-півотів і реконструкції обсягу. Це також не тест проти випадкового розташування рівнів. Проте вибрані рівні не дали простого пояснення більшості кінцевих екстремумів через сам факт близькості.

**Не можна назвати вузол причиною зупинки лише тому, що він сформувався в її районі.** Саме тому передстартовий профіль збережений окремо від поточного.

## 3. Що відбувається після всіх торкань рівнів

Події шукаються по всій M5-історії, навіть якщо великої хвилі потім немає. Рівень відомий із попередньої свічки. Ціна підходить із визначеного боку, high/low торкається смуги±0,1ATR. Подія стає відомою на close. Далі перевіряємо, який close-бар'єр від **цього close** досягнуто першим за6h: +1ATR у напрямку підходу або−1ATR проти нього. Якщо жоден — unresolved. Великі переміщення самої контактної свічки не зараховуються в майбутній результат.

Пізній CHECK:2025–доступний2026,5855 подій:

{md(check)}

Це умовні частоти після контактів, не твердження, що рівень викликав реакцію. Один timestamp інколи стосується кількох рівнів; не трактуємо їх як незалежні спроби. HVN2/LVN відсутні там, де алгоритм не знайшов відповідного другого вузла/западини.

Видно обидва типи реакції біля кожного рівня. Наприклад, LVN не забезпечує універсальний прохід, а POC/HVN не забезпечує універсальний відскок. У повних таблицях відокремлено закриття за рівнем, повернення на бік підходу та close у зоні рівня.

## 4. Чи пояснюють реакцію форма + OI + Crowd

Порівняння зроблено з базою того самого рівня, типу закриття, напрямку підходу і попереднього6h-тренду. Додатково перевірено форму, OI4h, напрямок Z натовпу, перехід форми за попередню годину та спільну комбінацію.

- Знайдено3857 умовних комірок; PASS і REJECT дають7714 розглянутих перевірок.
- Лише **78 комірок** мають достатній наперед заданий обсяг: навчання≥100подій/20тижнів і2024≥30подій/10тижнів.
- Для сильного кандидата вимагали приріст≥10п.п. у2021–2023 та≥5п.п. у2024 над відповідною базою.
- **Жодна комірка не пройшла обидві вимоги.** Одна достатньо наповнена комірка досягла+10п.п. у discovery, але не повторила перевагу у validation. Відібраних кандидатів для фінальної перевірки —0.

Це не доводить відсутності будь-якого слабшого зв'язку. Вибірка сильно розріджується після розбиття на всі стани, а пороги10/5п.п. навмисно вимагають суттєвого ефекту. Повні результати, включно з меншими позитивними й негативними приростами, збережені. Пороги після перегляду результату не послаблювалися.

## 5. Описує минуле чи передбачає наступне

Додаткова описова перевірка, додана після розбору подій; вона не використовувалася для відбору кандидата. На фіксованих годинних точках порівняно зміну L/S, OI та POC за попередню годину зі зміною ціни за наступну годину. Наведено Spearman correlation:

{md(llp)}

У цих простих безумовних годинних зв'язках значення близькі до нуля. Це не суперечить помітній зміні L/S всередині відібраних великих хвиль: там є відбір за майбутнім рухом і змінна тривалість, тут — усі годинні моменти й фіксований горизонт. Нелінійні взаємодії та інші масштаби таким тестом не виключені.

## 6. Приклади на графіку

Для кожної початкової форми D/P/b/B взято хвилю2024, найближчу до медіан її групи за амплітудою та тривалістю, з тривалістю≤24h і валідними flow у кінцях. Відбір не залежить від краси пояснення або прибутковості. Тло — ретроспективна хвиля; горизонтальні рівні — перед стартом; золотий пунктир — поточний POC.

![Чотири приклади](LAB162_examples.png)

{md(examples[['move_id','start','peak','side','shape_start','shape_peak','amplitude_atr','duration_h']])}

## Визначення й обмеження

- Хвилі успадковані зLAB161/LAB160d: close-M5 екстремуми, розворот1ATR, амплітуда≥3ATR;2ATR sensitivity збережена окремо. Початок/пік відомі заднім числом. Контекст CONT/REV/FLAT визначається попереднім6h-рухом на старті; це не хвилі Елліотта і не повна розмітка ринкової структури.
- Profile:24h/40bins, рівномірний розподіл M5volume між high/low, не справжній tick footprint. POC/VAL/VAH перевірені на точну відповідністьLAB161.
- **B — нове структурне визначення:** два піки згладженого3bins-профілю, відстань≥6bins, другий≥70% головного, западина≤70% меншого піку. Для HVN2 достатньо50%; LVN потрібна виражена западина. Інакше P/b задаються верхньою/нижньою третиною POC та перевагою обсягу1,15; рештаD. СтарийDOUBLE збережено окремо й не прирівняно доB. Вторинні локальні піки шукаються у внутрішніх bins; крайові форми можуть бути класифіковані інакше.
- B займає приблизно28% валідних M5-профілів, старийDOUBLE близько8%; тому LAB159 gate не переносився на нову класифікацію без тесту.
-473 невалідні записи OI≤0 перетворені на missing для OI-траєкторій. Три контакти з таким OI вилучені. Missing flow не домальовано. Flow має успадковане припущення затримки5хв, не виміряний live publication lag.
- Навчання2021–2023, validation2024, check2025–2026;6h-purge на межах. Роки вже використовувалися у проекті: не pristineOOS. Пошук багатьох комбінацій потребує подальшого незалежного підтвердження.
- Зіставлення форми/OI/Crowd умовне на ціновий контекст контакту. Немає рандомізованого експерименту або повного набору учасників/ліквідацій/ліквідності, тому причинне «штовхає/зупиняє» не встановлено.
- Немає execution replay, costs, PF/DD або нового live-сигналу. Показники бар'єрів є описом ціни.

## Що отримали

LAB162 дає відтворювану анатомію: **як рухалися ціна, OI, L/S та профіль**, де були старі рівні, як проходили внутрішні імпульси/відкати й що відбувалося після контактів незалежно від появи великої хвилі. Помітна зміна всередині хвилі не перетворилася автоматично на сильний передвісник. Дані не виправдовують ні універсального правила по літері профілю, ні твердження, що ці ознаки взагалі марні.

## Відтворення

ПотрібенLAB161_dataset.pkl іLAB161_waves.csv (відновлюються кодомLAB161), а також оригінальний flowZIP у сусідньомуdata/ абоLAB160C_DATA. SHA256 джерел —LAB162_data_audit.json. Код працює зnumpy,pandas,numba,scipy,matplotlib.

```bash
python3 labs/LAB162_WAVE_PROFILE_FLOW_TRAJECTORIES_20261010/prepare.py
python3 labs/LAB162_WAVE_PROFILE_FLOW_TRAJECTORIES_20261010/events.py
python3 labs/LAB162_WAVE_PROFILE_FLOW_TRAJECTORIES_20261010/waves.py
python3 labs/LAB162_WAVE_PROFILE_FLOW_TRAJECTORIES_20261010/analyze.py
python3 labs/LAB162_WAVE_PROFILE_FLOW_TRAJECTORIES_20261010/lead_lag.py
python3 labs/LAB162_WAVE_PROFILE_FLOW_TRAJECTORIES_20261010/verify.py
python3 labs/LAB162_WAVE_PROFILE_FLOW_TRAJECTORIES_20261010/build_report.py
```

Архів містить повні encounters, wave trajectories, anatomy, internal legs, transitions, всі conditional cells, контрольні таблиці, графіки, протокол і код. Великий відновлюванийLAB162_tape.pkl не включено. Звіт та графіки не замінюють поелементні таблиці.
'''
(O/'LAB162_REPORT_UK.md').write_text(report);print('REPORT READY')
