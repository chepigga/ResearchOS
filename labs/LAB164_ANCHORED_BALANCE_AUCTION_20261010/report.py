from run import *

def table(d):
 def fmt(x):return f'{x:.3f}' if isinstance(x,(float,np.floating)) else str(x)
 return '\n'.join(['| '+' | '.join(d.columns)+' |','| '+' | '.join(['---']*len(d.columns))+' |']+['| '+' | '.join(fmt(x) for x in row)+' |' for row in d.itertuples(index=False,name=None)])
def main():
 s=pd.read_csv(O/'signals.csv');b=pd.read_csv(O/'balances.csv');summary=pd.read_csv(O/'summary.csv');ab=pd.read_csv(O/'ablation.csv');pairs=pd.read_csv(O/'paired_stages.csv');coverage=pd.read_csv(O/'wave_coverage.csv');valid=s[s.split!='PURGED'];geo=[]
 for (split,stage),q in valid.groupby(['split','stage']):
  g=q[q.geometry_valid];geo.append(dict(split=split,stage=stage,n=len(q),positive_geometry=len(g),already_passed=int((~q.geometry_valid).sum()),target_first_pct=100*(g.geometry_outcome=='TARGET').mean(),invalidation_first_pct=100*(g.geometry_outcome=='INVALIDATION').mean(),timeout_pct=100*(g.geometry_outcome=='TIMEOUT').mean(),median_rr=g.rr.median()))
 geo=pd.DataFrame(geo);geo.to_csv(O/'geometry_summary.csv',index=False)
 check=summary[(summary.split=='CHECK')&(summary.grouping=='stage')];p=pairs[(pairs.split=='CHECK')&(pairs.stage=='RETEST_HOLD')].iloc[0];fr=valid[(valid.split=='CHECK')&(valid.stage=='FAILED_RETURN')];matched=pd.read_csv(O/'wave_matches.csv');union=matched[matched.split=='CHECK'].move_id.nunique();total=int(coverage[coverage.split=='CHECK'].waves.iloc[0]);changed=valid[valid.stage=='BREAKOUT'].shape_changed.mean()*100
 # Additional substantive invariants.
 assert np.all(b.start.iloc[1:].to_numpy()>b.end.iloc[:-1].to_numpy())
 assert np.all(s[s.stage!='BREAKOUT'].i>=s[s.stage!='BREAKOUT'].break_i+2)
 assert np.all(s.break_i>s.det)
 assert np.all(s[s.stage!='BREAKOUT'].i-s[s.stage!='BREAKOUT'].break_i<=72)
 assert not valid[['id','stage']].duplicated().any()
 (O/'final_validation.json').write_text(json.dumps(dict(nonoverlapping_balances=True,confirmations_at_least_two_bars_after_break=True,confirmation_within_six_hours=True,unique_balance_stage=True,annotation_review='Six deterministic charts inspected before outcome tables; oscillating ranges visible; close lines do not verify every wick-level touch. Fixed detector is narrow, not exhaustive.',readout='No parameter tuning after outcomes'),indent=2))
 fig,ax=plt.subplots(1,2,figsize=(12,4));stages=['BREAKOUT','RETEST_HOLD','FAILED_RETURN'];x=np.arange(3)
 for j,split in enumerate(['DISCOVERY','VALIDATION','CHECK']):
  q=summary[(summary.split==split)&(summary.grouping=='stage')].set_index('stage');ax[0].bar(x+(j-1)*.24,q.loc[stages,'success_pct'],width=.24,label=split)
 ax[0].set_xticks(x,stages,rotation=12);ax[0].set_ylabel('+2 ATR before -1 ATR, %');ax[0].legend(fontsize=8);ax[0].set_title('All signals per stage (different episode samples)')
 q=ab[ab.split=='CHECK'];ax[1].plot(np.arange(4),q.brier,'o-',label='Model');ax[1].axhline(q.constant_train_brier.iloc[0],ls='--',color='gray',label='Discovery constant');ax[1].set_xticks(np.arange(4),['Price + TF','+ Crowd','+ OI','+ Profile']);ax[1].set_ylabel('Brier score (lower is better)');ax[1].set_title('Check 2025–2026, matched 96 breakouts');ax[1].legend();fig.tight_layout();fig.savefig(O/'results_overview.png',dpi=150);plt.close(fig)
 text=f'''# LAB164 — ANCHORED BALANCE × BREAKOUT × RETEST × FLOW

Завершено 2026-10-10. Дані BTC M5 за 2021-01 — 2026-08-10; контекст D1/H4/H1/M15/M5, без M1. Production не змінювався.

## Головний висновок

Розділення **ринкового сценарію, сигналу та геометрії входу** виявило конкретну проблему: підтвердження може відбирати цікаві епізоди, але приходити запізно. У CHECK ретест має 40.35% успіху проти 36.08% усіх пробоїв; проте на **тих самих 57 епізодах** перший пробій має 45.61%, а ретест — 40.35%. Порівняння тих самих епізодів ретроспективне: наперед невідомо, які пробої матимуть ретест. Це не готовий спосіб торгувати тільки ці пробої.

Для FAILED_RETURN медіана відстані до POC — **{fr.route_atr.median():.3f} ATR**, до інвалідації — **{fr.risk_atr.median():.3f} ATR**. У {(fr.route_atr<=0).sum()} із {len(fr)} сигналів ціна вже пройшла POC. Правильно описаний розворот ще не означає хороший вхід.

## Що саме пораховано

Баланс визначається на закритому H1 за останніми шістьма барами: ширина 1–4 ATR, ефективність шляху <=0.35, >=3 перетинів середини, >=2 закриттів у кожній зовнішній третині. Межі фіксуються при виявленні. Це **одна вузька формалізація**, а не всі трейдерські баланси. Наступний баланс використовує лише бари після завершення попереднього епізоду.

Профіль починається з першої M5 свічки знайденого балансу й накопичується до бару перед пробоєм. Після цього він заморожений: POC, VAH/VAL, HVN2, LVN, P/B/b/D. 40 bins, рівномірний розподіл обсягу всередині high–low M5; не footprint. Форма відрізняється від trailing24h у {changed:.1f}% пробоїв. Це доводить різницю ознак, а не її торгову цінність.

Пробій: закриття на 0.1 ATR поза межами. Протягом 6h перша підтверджена гілка: дотик межі та два закриття ззовні (RETEST_HOLD), або два закриття всередині (FAILED_RETURN). Повторні пізні гілки цього епізоду не рахуються. Два закриття — операційне підтвердження, не доказ стійкого прийняття ціни.

Знайдено **{len(b)} балансів**, 274 пробої, 156 ретестів, 97 повернень, 21 непідтверджений вихід, 7 балансів без виходу за 24h. Разом 527 спостережень стадій, але **не 527 незалежних угод**. Первинні незалежні одиниці — баланси.

Графіки обрано механічно по одному на рік за близькістю ширини до медіани, без відбору за результатом. Перегляд до оцінки майбутнього руху підтвердив наявність коливань; показав також затримку повернення до POC. Параметри після перегляду не змінювалися.

![Розмітка](annotation_audit.png)

## Рух після сигналу

Успіх: майбутнє закриття досягає +2 ATR раніше за −1 ATR у наступні 24h. ATR фіксований на сигналі. «Хибний» тут включає несприятливий бар'єр першим і невирішені випадки. Це не win rate торгової системи: угоди, intrabar SL/TP та costs не симулювалися.

{table(summary[summary.grouping=='stage'][['split','stage','n','success_pct','adverse_first_pct','unresolved_pct','median_mfe','median_delay']])}

Парне порівняння, що відокремлює зміну вибірки від очікування підтвердження:

{table(pairs)}

Для FAILED_RETURN напрямок пізнішого сигналу протилежний пробою. Його парне порівняння не є порівнянням двох входів в один напрямок.

## Геометрія конкретного сценарію

Продовження: ціль — одна ширина балансу від пробитої межі, скасування — 0.1 ATR всередині. Повернення: ціль POC, скасування — за екстремумом спроби пробою +0.1 ATR. Результати нижче тільки для додатної відстані до цілі й скасування; перевірка за майбутніми **закриттями**, без виконання ордерів.

{table(geo[geo.split=='CHECK'])}

Вузькі рівні скасування для continuation особливо чутливі до intrabar руху і витрат. Ці показники не дають PF/EV реального виконання. Медіанне RR не можна множити на загальний відсоток успіху для розрахунку EV.

## Чи додають Crowd, OI та профіль інформацію

Фіксована logistic regression C=1: навчання тільки 2021–2023; 2024 validation; 2025–2026 CHECK без перенавчання. Ціна включає структуру п'яти TF, ширину/ефективність балансу, прогрес за годину та відносний обсяг. Потім L/S і зміна crowd z, OI quantity за годину, потім anchored profile. Збережено відстань до відомих H1/H4 swing obstacles й price progress / relative volume. Ці ознаки не ідентифікують причинно «хто штовхає» ціну.

Однакова повна вибірка: лише 123 навчальні пробої, 49 validation, 96 CHECK. Шість пробоїв виключено через відсутні ознаки. Для такої кількості ознак навчальна вибірка мала. Інтервали — paired bootstrap за тижнями, 500 повторів; не враховують невизначеність самого навчання.

{table(ab)}

У CHECK профіль знижує Brier на 0.0079 та піднімає AUC приблизно 0.538 → 0.606; інтервал різниці Brier **перетинає нуль**. У 2024 додавання профілю погіршує Brier. Повна модель CHECK майже дорівнює простому прогнозу сталої частоти з навчання. Стабільна додаткова цінність не підтверджена; це не доказ відсутності взаємозв'язків загалом. Інтеракції та нелінійні моделі тут не досліджувалися.

## Скільки хвиль впізнано

Успадковані незалежні хвилі M5 close з відкатом 1 H1 ATR та амплітудою >=3 ATR. Зараховується сигнал потрібного напрямку до вершини, якщо залишився >=1 ATR і вершина не далі 24h. Хвилі — ретроспективні мітки для аудиту, не відомі на вході.

{table(coverage[coverage.split=='CHECK'])}

Об'єднання трьох стадій впізнало **{union}/{total} = {100*union/total:.2f}%** хвиль CHECK (без подвійного рахунку). Стадії окремо додавати не можна. Медіана залишкового руху умовна — тільки серед упізнаних хвиль. Покриття не означає фактично взятий прибуток. Прямого порівняння з попередніми 91.6% немає: там інший період і фактичні позиції.

Детектор дає приблизно чотири первинні пробої на місяць у довгій історії. Отже він **не вирішує задачу масового розширення охоплення рухів**. Перш ніж послаблювати цей детектор, потрібна незалежна ручна розмітка бажаних типів балансів/імпульсів: інакше ми знову підлаштуємо правила під результат.

## Межі висновку й відтворення

Це development-дослідження на вже багаторазово використаній історії, не pristine OOS. Не перебирали пороги за майбутнім P/L. Результат не є підставою міняти production або ризик. Вузький баланс, коротке підтвердження, реконструйований профіль та обмежена кількість епізодів залишають інші механізми відкритими.

Перевірено prefix invariance детектора, збереження суми обсягу профілю, неперетин балансів, часовий порядок, унікальність стадій, відсутність майбутніх барів у профілі, повторний розрахунок кожного 17-го label. Вхідні дані й causal TF успадковано з LAB162/LAB163; перевірки їхнього джерела наведено у lineage.json.

Відтворення з кореня ResearchOS: `python3 labs/LAB164_ANCHORED_BALANCE_AUCTION_20261010/run.py`, потім `evaluate.py` і `report.py` з тієї ж папки. Потрібні кеші LAB162_tape.pkl і LAB163_context.pkl та LAB161_waves.csv; їхні генератори є у попередніх LAB. Залежності: numpy, pandas, matplotlib, scikit-learn. В архіві код, фіксований протокол, всі події, таблиці, графіки й перевірки; великі відтворювані кеші не дублюються.
'''
 (O/'LAB164_REPORT_UK.md').write_text(text)
 import sklearn,platform
 (O/'versions.json').write_text(json.dumps(dict(python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__,sklearn=sklearn.__version__),indent=2))
 lineage=json.loads((R/'results/LAB162_20261010/LAB162_data_audit.json').read_text());(O/'lineage.json').write_text(json.dumps(lineage,indent=2))
 files=sorted(list(Path(__file__).parent.glob('*.py'))+list(Path(__file__).parent.glob('*.md'))+[p for p in O.iterdir() if p.is_file() and p.suffix not in ['.log'] and p.name!='manifest.json']);manifest={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files};(O/'manifest.json').write_text(json.dumps(manifest,indent=2));files.append(O/'manifest.json');dest=R/'artifacts/LAB164_ANCHORED_BALANCE_AUCTION.zip'
 with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for p in files:z.write(p,p.relative_to(R))
 print('Archive',dest.stat().st_size,'bytes; unique CHECK waves',union,'/',total);print(geo[geo.split=='CHECK'].to_string(index=False))
if __name__=='__main__':main()
