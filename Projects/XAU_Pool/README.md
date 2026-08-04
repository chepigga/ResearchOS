# XAU_Pool

Окремий ResearchOS-проєкт для дослідження XAUUSD через пул незалежних торгових механік і каузальний selection layer.

## Поточний результат

`XAU_POOL_SELECTION_LAB_001 v001` має формальний `PASS` за звітом і статус `CANDIDATE`:

- CONTROL selected raw EV: `+0.2261R`;
- CONTROL excess level: `+0.3363R`;
- CONTROL lift: `+0.3539R`;
- CONTROL N: `1,506`;
- 44/44 позитивних місяці за excess;
- permutation: `z=23.4`, 0/37 shuffles досягли реального результату.

Це ще не canonical trading system: відсутні portfolio simulation, FTMO constraints, MQL5 parity і forward після 2026-07-23.

## Навігація

- [STATUS.md](STATUS.md) — operational source of truth.
- [BACKLOG.md](BACKLOG.md) — наступні перевірки.
- [Specs/](Specs/) — специфікація та додатки.
- [Reports/](Reports/) — лабораторний звіт.
- [Code/Python/](Code/Python/) — код відтворення.
- [Results/](Results/) — lineage та перелік відсутніх outputs.
- [Decisions/](Decisions/) — ADR.

## Походження

Матеріали надійшли 2026-08-04 у пакеті `files.zip`, де XAU-дослідження було розміщене під `Projects/AK47/`. За прямим рішенням користувача воно імпортоване як окремий проєкт `XAU_Pool`. Оригінальні зміст і назви лабораторних файлів збережені.
