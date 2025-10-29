

## 7) Конфигурация (настраиваемые параметры)

```python
MAX_ITERS = 300
MAX_DEPTH = 12
TOPK_LEMMAS = 10
BEAM_MIN = 1
BEAM_MAX = 5
SUB_TRIES_PER_NODE = 5          # сколько раз правим подстановки на узле
LEMMA_SWAPS_PER_NODE = 3        # сколько раз заменяем леммы на узле
SWAP_AT_ONCE = 1                # сколько лемм меняем за один swap
QUERY_PHRASE_SLOP = 1
```

## 8) Алгоритм (контрольный поток; реализовать как FSM/оркестратор)

### Инициализация

1. `S = G0(GoalNL) -> StatementSpec`.
2. `A1.save(S)` — записать класс.
3. `C0 = A2.retrieve(S, TOPK_LEMMAS)` — кандидаты лемм.
4. `P0 = A3.plan(S, C0)`.
5. `push(stack, node(P0, alt_queue = mk_alts(C0, BEAM_MAX)))`.

### Главный цикл (DFS-луч)

Повторять, пока `iters < MAX_ITERS` и `stack` не пуст:

1. `node = top(stack)`; `iters += 1`.
2. **Сборка и проверка:**

   * `A4.build_and_save(node.plan)` → рабочий proof + снапшот.
   * `report = A5.verify(node.plan.for)`; `artifacts.log(...)`.
   * Если `report.ok` → **SUCCESS**: сохранить и выйти.
3. **Refine на узле (A6):**

   * Если `node.counters.sub_tries < SUB_TRIES_PER_NODE`:

     * `node.plan = A6.refine_substitutions(node.plan, report)` (корректируем подстановки **в 1 шаге**; не более `SWAP_AT_ONCE`).
     * `node.counters.sub_tries += 1`; `continue`.
   * Если `node.counters.lemma_swaps < LEMMA_SWAPS_PER_NODE`:

     * `C' = A2.retrieve_local(S, context=node.plan, k=TOPK_LEMMAS)`.
     * `P' = A6.swap_one_lemma(node.plan, pick_from(C', node.alt_queue))`.
     * `node.counters.lemma_swaps += 1`.
     * `push(stack, node(P', alt_queue = mk_alts(C', BEAM_MAX)))`; `continue`.
4. **Backtrack:**

   * `pop(stack)` — узел исчерпан.
   * Если `stack` не пуст:

     * `parent = top(stack)`.
     * Если у `parent.alt_queue` есть ещё альтернативы:

       * `P'' = A3.plan_from_alt(parent, next(parent.alt_queue))`.
       * `push(stack, node(P''))`.
     * Иначе — цикл продолжит backtrack на следующей итерации.
5. Если цикл завершился без успеха → **FAIL**.

### Примечания к A6 (эвристики подстановок/замен)

* **refine_substitutions:** при ошибках «mismatch assertion/expected», «несовпадение строк» — править подстановки **в последнем/предпоследнем** шаге `call`. Опираемся на `report.issues` и `search.context_by_anchor(...)` для уточнения.
* **swap_one_lemma:** выбираем шаг `call` с минимальным доверием (низкий `score` источной леммы / частые провалы), заменяем **ровно одну** лемму (не более `SWAP_AT_ONCE`), остальные шаги плана сохраняем.
* **alt_queue:** хранит до `BEAM_MAX` альтернатив на уровне. Можно уменьшать до `BEAM_MIN`, если подряд были «локальные улучшения» (эвристика — например, меньше ошибок в последних шагах).

## 9) CLI (MVP)

```
$ prove_nl --goal "докажи X ..." --name MyTheorem \
  --max-iters 300 --beam-min 1 --beam-max 5 \
  --topk-lemmas 10 --sub-tries 5 --lemma-swaps 3
```

* Печатает краткий прогресс; на выходе — путь к артефактам и итог.

## 10) Структура проекта (минимум)

```
agent/
  __init__.py
  orchestrator.py        # FSM/цикл
  agents.py              # G0,A1..A6,A8
  tools.py               # обёртки theorem/proof/search/artifacts
  types.py               # dataclasses для Spec/Plan/Report/BranchState
  config.py
  cli.py

snapshots/               # создаётся на лету
logs/
classes/                 # итоговые классы
proofs/                  # рабочие proofs
```

## 11) Обработка ошибок и логирование

* Любая ошибка сборки/выполнения → запись в `logs/<run_id>.jsonl` с `attempt_id`, `plan`, `exception`, `trace`.
* Proof-снапшот сохраняется **перед** верификацией (даже если импорт упадёт).
* Если индекс поиска недоступен — немедленный FAIL с диагностикой (без попыток его строить).

## 12) Definition of Done (приёмка)

* CLI успешно обрабатывает `GoalNL`, создаёт `classes/<Name>.py`, минимальный `proofs/<Name>.py`, ведёт JSONL-лог и снапшоты.
* Реализован полный цикл **DFS-луч** с настроечными лимитами: `SUB_TRIES_PER_NODE`, `LEMMA_SWAPS_PER_NODE`, `SWAP_AT_ONCE`, `BEAM_MIN/MAX`.
* На успехе — верификатор возвращает `ok=True`; сохраняются все артефакты.
* На неуспехе — чёткий отчёт (последний `VerifyReport`, глубина/итерации, статистика замен и подстановок) + все артефакты попыток.
* Нет вызовов переиндексации; поиск работает только по существующему индексу.

---

Хочешь — могу дополнить шаблонами dataclass’ов для `StatementSpec/Plan/BranchState` и заготовкой оркестратора (скелет функций/классов) для прямой вставки.
