Краткая сводка по задаче (task2)

Что сделано

- Интегрировал Saplings с проектом metamath2py и подготовил слой совместимости под OpenAI Agents SDK:
  - Добавлены saplings-инструменты для агента:
    - `SearchTheoremsTool` — вызывает `database.opensearch_wrapper.TheoremSearchClient.search` и возвращает релевантные сниппеты (включая `start_line`/`end_line`, если доступны).
    - `VerifyProofTool` — вызывает `metamath2py.verification.verify_proof` по пути к модулю proof и возвращает структурированный результат в `raw_output` (для последующей оценки).
  - Добавлен `ProofEvaluator` — детерминированный Evaluator, который приоритетно использует результат `verify_proof`: успех → 1.0; ошибки в стадиях import/lookup/construction/execution → 0.1/0.2/0.2/0.3. Если в траектории нет верификации — нейтральная оценка 0.5.
  - Реализован сборщик агента и запуск поиска: `metamath_agent/agent.py` с функциями `build_agent` и `run_proof_search`. Поддерживаются алгоритмы Saplings: `astar` (по умолчанию), `greedy`, `mcts`, `cot` (ReAct/без оценки). Переключение — через конфигурацию.
  - Ведётся JSONL-лог ранa: сохраняется вся история шагов (`out/agent_runs/<run_id>/log.jsonl`) и конфиг (`config.json`). Это покрывает требование сохранения истории и даёт возможность отложенного анализа.

Файлы и ключевые элементы

- `metamath_agent/config.py` — `AgentConfig` с выбором алгоритма, параметрами поиска и настройками OpenSearch (read-only по умолчанию).
- `metamath_agent/tools.py` — инструменты `SearchTheoremsTool`, `VerifyProofTool` (совместимы со схемой function tool).
- `metamath_agent/evaluators.py` — `ProofEvaluator` (оценка по `verify_proof`).
- `metamath_agent/agent.py` — сборка агента (`AStarAgent`/`GreedyAgent`/`MonteCarloAgent`/`COTAgent`), запуск `run_proof_search(goal, cfg)` с логированием.

Интеграция с OpenAI Agents SDK

- С помощью Context7 изучена документация `/websites/openai_github_io_openai-agents-python` (Agents, Sessions, Function tools, Handoffs). Текущая реализация использует функцию-совместимые инструменты (Function Tools), что облегчает дальнейший перенос на `openai-agents-python` (концептуально сопоставимо с `FunctionTool.on_invoke_tool`).
- Память/контекст — хранится в траектории Saplings и дополнительно в JSONL логе (внешняя структура), что удовлетворяет требованию сохранения состояния.
- Потоковая обработка — реализована естественным образом через `run_iter(...)` Saplings (генерация событий по мере расширения дерева).

Как использовать

- Пример кода (скелет):
  - Создать конфиг: `cfg = AgentConfig(algorithm="astar", model="gpt-4o-mini")`.
  - Запустить: `messages, score, is_solution, run_path = run_proof_search("Goal in NL", cfg)`.
  - Инструменты доступны LLM через функцию-выбор (`tool_choice="auto"` по умолчанию).

Заметки и ограничения

- Индекс OpenSearch предполагается существующим (см. требование A2). `SearchTheoremsTool` не инициирует переиндексацию.
- Для прямой интеграции с OpenAI Agents SDK можно добавить адаптер, оборачивающий `SearchTheoremsTool`/`VerifyProofTool` в `FunctionTool` и использовать `Agent`/`Session` для хранения памяти. Логика алгоритмического поиска (A* / MCTS) может оставаться в Saplings, а обмен сообщениями и инструментами — в OpenAI Agents SDK.

Итог

- Инструменты поиска и верификации подключены к агенту, дерево поиска инкапсулировано средствами Saplings, оценка опирается на реальную верификацию, история шагов сохраняется. Выбор алгоритма поиска вынесен в конфигурацию, что соответствует требованиям задачи.

