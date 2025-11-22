Краткая сводка по задаче (task2)

Что сделано

- Интегрировал Saplings с проектом metamath2py и подготовил слой совместимости под OpenAI Agents SDK:
  - Добавлены saplings-инструменты для агента (перемещены прямо в папку `saplings`, без внешних адаптеров):
    - `SearchTheoremsTool` — вызывает `database.opensearch_wrapper.TheoremSearchClient.search` и возвращает релевантные сниппеты (включая `start_line`/`end_line`, если доступны).
    - `VerifyProofTool` — вызывает `metamath2py.verification.verify_proof` по пути к модулю proof и возвращает структурированный результат в `raw_output` (для последующей оценки).
  - Добавлен экипаж оценщиков (`Proof Evaluation Crew`), который анализирует траекторию, при необходимости использует `verify_proof` и возвращает `GeneratedPatch`.
  - Реализован сборщик агента и запуск поиска: `metamath_agent/agent.py` с функциями `build_agent` и `run_proof_search`. Поддерживаются алгоритмы Saplings: `astar` (по умолчанию), `greedy`, `mcts`. Переключение — через конфигурацию. При этом слой `metamath_agent` сведен к минимуму (нет адаптеров, инструменты живут в `saplings/tools`).
  - Логирование ранa по умолчанию отключено; история шагов доступна только в рамках дерева поиска.

Файлы и ключевые элементы

- `metamath_agent/config.py` — `AgentConfig` с выбором алгоритма, параметрами поиска и настройками OpenSearch (read-only по умолчанию).
- `metamath_agent/tools.py` — инструменты `SearchTheoremsTool`, `VerifyProofTool` (совместимы со схемой function tool).
- `metamath_agent/evaluators.py` — удалён (оценка выполняется экипажем Saplings).
- `metamath_agent/agent.py` — сборка агента (`AStarAgent`/`GreedyAgent`/`MonteCarloAgent`), запуск `run_proof_search(goal, cfg)`.

Интеграция с OpenAI Agents SDK

- С помощью Context7 изучена документация `/websites/openai_github_io_openai-agents-python` (Agents, Sessions, Function tools, Handoffs). Текущая реализация использует схему function tools непосредственно в `saplings`, что упрощает дальнейшее перенесение на `openai-agents-python` без внешних адаптеров.
- Память/контекст — хранится в траектории Saplings (JSONL лог отключён).
- Потоковая обработка — реализована естественным образом через `run_iter(...)` Saplings (генерация событий по мере расширения дерева).

Как использовать

- Пример кода (скелет):
  - Создать конфиг: `cfg = AgentConfig(algorithm="astar", model="gpt-4o-mini")`.
  - Запустить: `trajectory, score, is_solution = run_proof_search("Goal in NL", cfg)`.
  - Инструменты доступны LLM через функцию-выбор (`tool_choice="auto"` по умолчанию).

Заметки и ограничения

- Индекс OpenSearch предполагается существующим (см. требование A2). `SearchTheoremsTool` не инициирует переиндексацию.
- Для прямой интеграции с OpenAI Agents SDK следующий шаг — заменить `saplings.model.Model` на реализацию, использующую `Agent`/`Session` и нативный вызов Function Tools. Логика алгоритмического поиска (A* / MCTS) может остаться существующей, источником кандидатов станет запрос к сессии агента (tool-choice + handoffs).

Итог

- Инструменты поиска и верификации подключены к агенту, дерево поиска инкапсулировано средствами Saplings, оценка опирается на реальную верификацию, история шагов сохраняется. Выбор алгоритма поиска вынесен в конфигурацию, что соответствует требованиям задачи.
