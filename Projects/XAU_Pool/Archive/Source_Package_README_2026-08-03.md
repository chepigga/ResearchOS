# Пакет для коміту в ResearchOS — 2026-08-03

Розпакувати в корінь репозиторію `chepigga/ResearchOS`. Структура
шляхів уже відповідає наявній.

## Що додається

```
Projects/AK47/Specs/     SPEC_XAU_POOL_SELECTION_LAB_001.md  + Додатки A, B, C
Projects/AK47/Research/  XAU_POOL_SELECTION_LAB_001_Report.md
Projects/AK47/Code/      9 скриптів для відтворення (GOVERNANCE §відтворюваність)
Projects/FXArena/Reports/ ExitPolicyTournament_v002_Report.md
Projects/FXArena/Specs/  FXArena_SPEC_ExitTP3_v003.md   (DRAFT, не заморожено)
ResearchOS_registry_entries_2026-08-03.md   ← вручну внести в RESEARCH_REGISTER.md
                                              і LESSONS_LEARNED.md
```

## Що ПОТРІБНО зробити вручну

1. **RESEARCH_REGISTER.md** — внести два записи з
   `ResearchOS_registry_entries_2026-08-03.md` (блок A)
2. **LESSONS_LEARNED.md** — внести 8 уроків (блок B)
3. **Projects/FXArena/STATUS.md** — зняти блокер B5:
   модель знайдено в `Releases/v.1.1/weights_schedule_GEOstar_MICRO30_TP2_TO120.pkl`
4. **Projects/FXArena/Releases/c2_trades_loop_PINNED.pkl** — перейменувати
   або перемістити в Archive. Це НЕ канонічна фікстура (N=3715 проти 3535)
5. **Projects/AK47/BACKLOG.md** — позначити, що P4 (REGIME_BREAK) частково
   покрито: режимні фічі дають 2% ефекту, тричі не підтвердились

## Відтворення XAU-лабораторії

```bash
# дані (не в репозиторії, ~155 MB):
curl -L https://github.com/chepigga/ResearchOS/releases/download/ak47/\
XAUUSD_M1_20220601_20260723_TICK_NATIVE.csv -o xau_m1.csv

python3 step1_mechanics.py    # верифікація 15 механік
python3 step2_pool.py          # пул 266 297 кандидатів
python3 step3_baseline.py      # базова лінія (місяць x напрям x ТФ)
python3 step56_wf.py           # IS
python3 step7_oos1.py          # OOS-1
python3 step8_oos2.py          # OOS-2
python3 gate4_perm.py          # permutation (~5 хв, з контрольними точками)
python3 ablation.py            # абляція
python3 step9_control.py       # CONTROL 2026
```

Скрипти очікують `xau_m1.parquet` у `/home/claude/`. Проміжні артефакти
(`pool.parquet`, `pool_excess.parquet`, `baseline.parquet`) створюються
автоматично.

## Ключовий результат

```
                 IS      OOS-1     OOS-2    CONTROL
підйом       +0.3591   +0.3466   +0.3959   +0.3539
рівень       +0.3294   +0.3240   +0.3643   +0.3363
місяців +      16/16     10/10     11/11      7/7

permutation: z = 23.4, 0 із 37 шафлів досягли реального
Усі 5 gates PASS на всіх 4 періодах.
Статус: CANDIDATE (не CANONICAL — немає портфеля, prop-обмежень, форварду)
```
