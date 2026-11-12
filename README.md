# depgraph

Инструмент визуализации графа зависимостей пакетов NuGet (.NET) с командной
строки. Менеджеры пакетов (`dotnet`, `nuget`) и сторонние библиотеки для
получения зависимостей не используются: данные скачиваются напрямую из
репозитория, применяются только стандартные модули Python (`urllib`,
`json`, `xml`).

Практическая работа по дисциплине «Конфигурационное управление», вариант 11.

## Что делает программа и зачем

Когда устанавливается пакет, менеджер пакетов ставит не только его, но и все
пакеты, от которых он зависит, а те, в свою очередь, тянут свои зависимости.
Получается граф. Программа строит этот граф для заданного пакета и показывает
его в нескольких видах. Работа разбита на этапы:

1. **Прототип.** Настройки читаются из командной строки и проверяются, чтобы
   остальной код работал с корректными данными, а пользователь сразу получал
   понятное сообщение об ошибке.
2. **Сбор данных.** Описание пакета (файл `.nuspec`) скачивается по URL
   репозитория, из него читаются прямые зависимости. Это ровно то, что делает
   менеджер пакетов, но реализовано вручную.
3. **Граф зависимостей.** Обход в глубину без рекурсии (стек ведётся явно),
   потому что рекурсия не выдерживает очень длинных цепочек. Ограничение
   глубины не даёт графу разрастись, обработка циклов не даёт программе
   зависнуть. Тестовый режим позволяет проверять алгоритм на маленьких
   графах, результат для которых можно проверить вручную.
4. **Порядок загрузки.** Порядок, в котором нужно загружать пакеты, чтобы
   к моменту установки каждого из них уже были установлены его зависимости.
5. **Визуализация.** Текст диаграммы Mermaid, изображение SVG и ASCII-дерево.

## Структура репозитория

```
src/depgraph/   исходный код
tests/          модульные тесты (119 тестов)
tests/data/     тестовые репозитории (diamond, cycle, chain, shortcut, broken)
examples/       примеры изображений SVG
run.bat         запуск приложения
test.bat        запуск тестов
```

## Сборка, запуск и тесты

Нужен Python 3.10 или новее. Сборка не требуется, сторонние пакеты не нужны.

```
run.bat --package Newtonsoft.Json --repo https://api.nuget.org/v3/index.json --package-version 13.0.3 --max-depth 1
test.bat
```

`run.bat` запускает `python -m depgraph` с папкой `src` в пути поиска модулей,
`test.bat` запускает все тесты из папки `tests` (модуль `unittest`).

## Настройки

Все параметры задаются опциями командной строки.

| Опция | Обязательная | Описание |
|---|---|---|
| `--package` | да | Имя анализируемого пакета |
| `--repo` | да | URL репозитория или путь к файлу тестового репозитория |
| `--test-mode` | нет | Считать `--repo` путём к файлу тестового репозитория |
| `--package-version` | да, кроме тестового режима | Версия пакета, например `13.0.3` |
| `--output` | нет | Имя файла с изображением графа (`.svg`), по умолчанию `graph.svg`. Папка должна существовать |
| `--ascii-tree` | нет | Дополнительно вывести зависимости в виде ASCII-дерева |
| `--max-depth` | нет | Максимальная глубина анализа, целое число от 1, по умолчанию 3 |
| `--load-order` | нет | Вывести порядок загрузки зависимостей вместо графа |

Глубина отсчитывается от запрошенного пакета: глубина 1 даёт сам пакет и его
прямые зависимости.

### Коды завершения

| Код | Значение |
|---|---|
| 0 | успех |
| 1 | пакет не найден, репозиторий недоступен, файл повреждён или не записан |
| 2 | неверные параметры командной строки |

## Как это работает

1. **Источник данных.** Для NuGet скачивается индекс репозитория (`--repo`),
   в нём ищется адрес файлов пакетов, затем скачивается описание `.nuspec`
   нужной версии и из него берутся зависимости. В тестовом режиме данные
   читаются из файла.
2. **Граф.** Обход в глубину с явным стеком (без рекурсии). Пакет, встреченный
   на такой же или большей глубине, пропускается, это останавливает циклы.
   Пакет, встреченный ближе к корню, обрабатывается заново, поэтому ограничение
   глубины не скрывает близкие к корню пакеты. Циклы затем находятся отдельным
   обходом и выводятся.
3. **Порядок загрузки.** Постпорядок обхода в глубину: пакет идёт после всех
   своих зависимостей, запрошенный пакет последний. Рёбра, замыкающие цикл,
   игнорируются и отмечаются в выводе.
4. **Вывод.** Текст графа, ASCII-дерево, Mermaid и SVG строятся из одного и того
   же графа.

### Принятые решения

- Узел графа это имя пакета. Версия берётся у первого упоминания пакета.
- Из диапазона версий NuGet берётся нижняя граница (`[1.0, 2.0)` даёт `1.0`).
  Версия приводится к виду, который хранит NuGet (`1.0` превращается в `1.0.0`).
- Зависимости всех целевых платформ (`targetFramework`) из `.nuspec`
  объединяются, повторы убираются.
- Пакеты на предельной глубине не раскрываются (их зависимости не загружаются)
  и помечаются в выводе.
- Ошибка загрузки вложенного пакета не прерывает анализ: пакет помечается как
  незагруженный. Ошибка для запрошенного пакета завершает программу с кодом 1.
- Порядок загрузки не единственный: у независимых пакетов возможны разные
  правильные очередности, программа выдаёт детерминированный.

## Формат тестового репозитория

Одна строка на пакет: `A: B C` значит, что `A` зависит от `B` и `C`.
Имена состоят из заглавных латинских букв. Пакет без зависимостей пишется
как `C:`. Символ `#` начинает комментарий.

```
# Ромб: D нужен и B, и C
A: B C
B: D
C: D E
D:
E:
```

## Функции

### cli.py

- `create_parser`, `add_source_options`, `add_output_options` - разбор опций
  командной строки;
- `create_source` - выбор источника данных (репозиторий NuGet или файл);
- `make_graph` - построение графа по настройкам;
- `render` - текстовый вывод в выбранном режиме;
- `save_image` - сохранение SVG;
- `report_error` - сообщение об ошибке в stderr и код завершения;
- `main` - точка входа.

### config.py

- `validate_package`, `validate_repo`, `validate_version`, `validate_output`,
  `validate_max_depth` - проверка параметров, при ошибке выбрасывают `ConfigError`;
- `build_config` - собирает проверенную конфигурацию `Config`.

### nuget.py

- `fetch` - скачивание URL; `find_package_base` - адрес файлов пакетов из
  индекса; `build_nuspec_url` - адрес описания пакета;
- `parse_dependencies` - зависимости из `.nuspec`;
- `normalize_version`, `resolve_version` - версия в виде NuGet и версия из
  диапазона;
- `NugetSource` - источник данных NuGet (индекс читается один раз);
- `get_direct_dependencies` - прямые зависимости пакета.

### testrepo.py

- `parse_test_repository`, `load_test_repository` - чтение тестового
  репозитория; `FileSource` - источник данных из файла.

### graph.py

- `build_graph` - обход в глубину без рекурсии; `expand` - загрузка
  зависимостей пакета с кэшем; `find_cycles` - поиск циклов; `Graph` - граф.

### order.py

- `load_order` - порядок загрузки (постпорядок обхода, без рекурсии).

### report.py, tree.py, mermaid.py, svg.py

- `report.format_graph`, `report.format_load_order` - текстовый вывод;
- `tree.format_tree` - ASCII-дерево;
- `mermaid.format_mermaid` - диаграмма Mermaid;
- `svg.render_svg`, `svg.write_svg`, `svg.layout` - рисование и сохранение SVG.

## Примеры использования

### Обработка ошибок параметров

Каждая проверка параметров завершает программу с кодом 2 и понятным
сообщением:

```
run.bat --package "bad name" --repo https://example.com --package-version 1.0
depgraph: error: invalid package name: 'bad name' (allowed: letters, digits, '.', '_', '-')

run.bat --package A --repo not-a-url --package-version 1.0
depgraph: error: invalid repository URL: 'not-a-url'

run.bat --package A --repo missing.txt --test-mode
depgraph: error: test repository file not found: missing.txt

run.bat --package A --repo https://example.com --package-version abc
depgraph: error: invalid package version: 'abc'

run.bat --package A --repo https://example.com --package-version 1.0 --output graph.png
depgraph: error: output file must have .svg extension: 'graph.png'

run.bat --package A --repo https://example.com --package-version 1.0 --max-depth 0
depgraph: error: max depth must be at least 1: 0

run.bat --package A --repo https://example.com
depgraph: error: package version is required: --package-version
```

Ошибки данных завершают программу с кодом 1:

```
run.bat --package NoSuchPackage12345 --repo https://api.nuget.org/v3/index.json --package-version 1.0.0
depgraph: error: not found (HTTP 404): https://api.nuget.org/v3-flatcontainer/nosuchpackage12345/1.0.0/nosuchpackage12345.nuspec

run.bat --package A --repo tests\data\broken.txt --test-mode
depgraph: error: line 3: invalid format: 'b: C'

run.bat --package Z --repo tests\data\diamond.txt --test-mode
depgraph: error: package Z is not in tests\data\diamond.txt
```

### Тестовый репозиторий: ромб

```
run.bat --package A --repo tests\data\diamond.txt --test-mode
```

```
Dependency graph of A (max depth 3): 5 packages, 5 dependencies
  A -> B, C
  B -> D
  D -> (none)
  C -> D, E
  E -> (none)
```

Пакет `D` нужен и `B`, и `C`, но в графе он один.

### Тестовый репозиторий: цикл

```
run.bat --package A --repo tests\data\cycle.txt --test-mode --max-depth 5
```

```
Dependency graph of A (max depth 5): 4 packages, 4 dependencies
  A -> B
  B -> C
  C -> A, D
  D -> (none)
Cycles found:
  A -> B -> C -> A
```

Программа не зацикливается, цикл найден и выведен.

### Тестовый репозиторий: ограничение глубины

```
run.bat --package A --repo tests\data\chain.txt --test-mode --max-depth 2
```

```
Dependency graph of A (max depth 2): 3 packages, 2 dependencies
  A -> B
  B -> C
Depth limit reached, not expanded: C
```

### Тестовый репозиторий: пакет, найденный ближе к корню

```
run.bat --package A --repo tests\data\shortcut.txt --test-mode --max-depth 3
```

```
Dependency graph of A (max depth 3): 5 packages, 5 dependencies
  A -> B, D
  B -> C
  C -> D
  D -> E
  E -> (none)
```

`D` сначала встречается на глубине 3 (путь `A-B-C-D`), затем на глубине 1
(`A-D`) и раскрывается заново, поэтому `E` попадает в граф.

### Порядок загрузки

```
run.bat --package A --repo tests\data\diamond.txt --test-mode --load-order
```

```
Load order of A (dependencies first, max depth 3): 5 packages
  1. D
  2. B
  3. E
  4. C
  5. A
```

Для цикла:

```
run.bat --package A --repo tests\data\cycle.txt --test-mode --load-order --max-depth 5
```

```
Load order of A (dependencies first, max depth 5): 4 packages
  1. D
  2. C
  3. B
  4. A
Cycles found:
  A -> B -> C -> A
Edges that close cycles were ignored in the order.
```

### ASCII-дерево, Mermaid и SVG

```
run.bat --package A --repo tests\data\diamond.txt --test-mode --ascii-tree --output examples\diamond.svg
```

```
ASCII tree:
A
|-- B
|   `-- D
`-- C
    |-- D (*)
    `-- E
Legend: (*) shown above

Mermaid:
graph TD
    n0["A"]
    n1["B"]
    n2["D"]
    n3["C"]
    n4["E"]
    n0 --> n1
    n0 --> n3
    n1 --> n2
    n3 --> n2
    n3 --> n4

SVG saved: examples\diamond.svg
```

Пометки в дереве: `(*)` пакет уже показан выше, `(...)` пакет не раскрыт из-за
ограничения глубины, `(cycle)` пакет замыкает цикл. В SVG корень выделен
синим, нераскрытые пакеты нарисованы пунктирной рамкой, рёбра циклов красным
пунктиром. Изображения лежат в папке `examples`.

### Три реальных пакета NuGet

**1. Microsoft.Extensions.Logging 8.0.0** (`examples/logging.svg`)

```
run.bat --package Microsoft.Extensions.Logging --repo https://api.nuget.org/v3/index.json --package-version 8.0.0 --max-depth 1 --ascii-tree --output examples\logging.svg
```

```
Dependency graph of Microsoft.Extensions.Logging 8.0.0 (max depth 1): 7 packages, 6 dependencies
  Microsoft.Extensions.Logging 8.0.0 -> Microsoft.Bcl.AsyncInterfaces 8.0.0, Microsoft.Extensions.DependencyInjection 8.0.0, Microsoft.Extensions.Logging.Abstractions 8.0.0, Microsoft.Extensions.Options 8.0.0, System.Diagnostics.DiagnosticSource 8.0.0, System.ValueTuple 4.5.0
Depth limit reached, not expanded: Microsoft.Bcl.AsyncInterfaces, Microsoft.Extensions.DependencyInjection, Microsoft.Extensions.Logging.Abstractions, Microsoft.Extensions.Options, System.Diagnostics.DiagnosticSource, System.ValueTuple

ASCII tree:
Microsoft.Extensions.Logging 8.0.0
|-- Microsoft.Bcl.AsyncInterfaces 8.0.0 (...)
|-- Microsoft.Extensions.DependencyInjection 8.0.0 (...)
|-- Microsoft.Extensions.Logging.Abstractions 8.0.0 (...)
|-- Microsoft.Extensions.Options 8.0.0 (...)
|-- System.Diagnostics.DiagnosticSource 8.0.0 (...)
`-- System.ValueTuple 4.5.0 (...)
Legend: (...) not expanded: depth limit

Mermaid:
graph TD
    n0["Microsoft.Extensions.Logging 8.0.0"]
    n1["Microsoft.Bcl.AsyncInterfaces 8.0.0"]
    n2["Microsoft.Extensions.DependencyInjection 8.0.0"]
    n3["Microsoft.Extensions.Logging.Abstractions 8.0.0"]
    n4["Microsoft.Extensions.Options 8.0.0"]
    n5["System.Diagnostics.DiagnosticSource 8.0.0"]
    n6["System.ValueTuple 4.5.0"]
    n0 --> n1
    n0 --> n2
    n0 --> n3
    n0 --> n4
    n0 --> n5
    n0 --> n6
    classDef limit stroke-dasharray: 4 4
    class n1,n2,n3,n4,n5,n6 limit

SVG saved: examples\logging.svg
```

**2. Newtonsoft.Json 13.0.3** (`examples/newtonsoft.svg`)

```
run.bat --package Newtonsoft.Json --repo https://api.nuget.org/v3/index.json --package-version 13.0.3 --max-depth 1 --ascii-tree --output examples\newtonsoft.svg
```

```
Dependency graph of Newtonsoft.Json 13.0.3 (max depth 1): 7 packages, 6 dependencies
  Newtonsoft.Json 13.0.3 -> Microsoft.CSharp 4.3.0, NETStandard.Library 1.6.1, System.ComponentModel.TypeConverter 4.3.0, System.Runtime.Serialization.Primitives 4.3.0, System.Runtime.Serialization.Formatters 4.3.0, System.Xml.XmlDocument 4.3.0
Depth limit reached, not expanded: Microsoft.CSharp, NETStandard.Library, System.ComponentModel.TypeConverter, System.Runtime.Serialization.Primitives, System.Runtime.Serialization.Formatters, System.Xml.XmlDocument

ASCII tree:
Newtonsoft.Json 13.0.3
|-- Microsoft.CSharp 4.3.0 (...)
|-- NETStandard.Library 1.6.1 (...)
|-- System.ComponentModel.TypeConverter 4.3.0 (...)
|-- System.Runtime.Serialization.Primitives 4.3.0 (...)
|-- System.Runtime.Serialization.Formatters 4.3.0 (...)
`-- System.Xml.XmlDocument 4.3.0 (...)
Legend: (...) not expanded: depth limit

Mermaid:
graph TD
    n0["Newtonsoft.Json 13.0.3"]
    n1["Microsoft.CSharp 4.3.0"]
    n2["NETStandard.Library 1.6.1"]
    n3["System.ComponentModel.TypeConverter 4.3.0"]
    n4["System.Runtime.Serialization.Primitives 4.3.0"]
    n5["System.Runtime.Serialization.Formatters 4.3.0"]
    n6["System.Xml.XmlDocument 4.3.0"]
    n0 --> n1
    n0 --> n2
    n0 --> n3
    n0 --> n4
    n0 --> n5
    n0 --> n6
    classDef limit stroke-dasharray: 4 4
    class n1,n2,n3,n4,n5,n6 limit

SVG saved: examples\newtonsoft.svg
```

**3. Serilog 3.1.1** (`examples/serilog.svg`)

```
run.bat --package Serilog --repo https://api.nuget.org/v3/index.json --package-version 3.1.1 --max-depth 2 --ascii-tree --output examples\serilog.svg
```

```
Dependency graph of Serilog 3.1.1 (max depth 2): 6 packages, 5 dependencies
  Serilog 3.1.1 -> System.Diagnostics.DiagnosticSource 7.0.2, System.ValueTuple 4.5.0
  System.Diagnostics.DiagnosticSource 7.0.2 -> System.Memory 4.5.5, System.Runtime.CompilerServices.Unsafe 6.0.0
  System.ValueTuple 4.5.0 -> NETStandard.Library 1.6.1
Depth limit reached, not expanded: System.Memory, System.Runtime.CompilerServices.Unsafe, NETStandard.Library

ASCII tree:
Serilog 3.1.1
|-- System.Diagnostics.DiagnosticSource 7.0.2
|   |-- System.Memory 4.5.5 (...)
|   `-- System.Runtime.CompilerServices.Unsafe 6.0.0 (...)
`-- System.ValueTuple 4.5.0
    `-- NETStandard.Library 1.6.1 (...)
Legend: (...) not expanded: depth limit

Mermaid:
graph TD
    n0["Serilog 3.1.1"]
    n1["System.Diagnostics.DiagnosticSource 7.0.2"]
    n2["System.Memory 4.5.5"]
    n3["System.Runtime.CompilerServices.Unsafe 6.0.0"]
    n4["System.ValueTuple 4.5.0"]
    n5["NETStandard.Library 1.6.1"]
    n0 --> n1
    n0 --> n4
    n1 --> n2
    n1 --> n3
    n4 --> n5
    classDef limit stroke-dasharray: 4 4
    class n2,n3,n5 limit

SVG saved: examples\serilog.svg
```

## Сравнение с реальным менеджером пакетов (этап 4)

Как сравнивали: создан проект командой `dotnet new console`, в него добавлен
пакет `Microsoft.Extensions.Logging 8.0.0` (`dotnet add package`). Платформа
проекта: `<впишите TargetFramework из файла Cmp.csproj>`. Порядок установки
менеджера взят из подробного лога `dotnet restore --verbosity detailed`
(строки `Installing`).

Порядок загрузки нашей программы:

```
run.bat --package Microsoft.Extensions.Logging --repo https://api.nuget.org/v3/index.json --package-version 8.0.0 --max-depth 10 --load-order
```

```
<вставьте вывод>
```

Порядок установки менеджера:

```
<вставьте строки Installing из restore.log>
```

Результат сравнения: `<одно предложение: совпадают ли наборы пакетов и версии, совпадает ли порядок>`.

Причины возможных расхождений:

- Наша программа объединяет зависимости **всех** платформ из `.nuspec`, а
  менеджер собирает зависимости для одной платформы проекта. Поэтому в нашем
  списке может быть больше пакетов (например, пакеты, нужные только старым
  платформам).
- Версии выбираются по-разному: мы берём нижнюю границу диапазона у первого
  упоминания, менеджер разрешает конфликты версий по собственным правилам.
- Порядок не единственный: независимые пакеты можно загружать в любой
  очерёдности, а менеджер может скачивать их параллельно. Наш порядок
  детерминированный. Различие в порядке не является ошибкой, пока зависимости
  стоят раньше зависимых пакетов.

## Сравнение со штатными инструментами визуализации (этап 5)

Для NuGet нет штатного инструмента, который рисует граф зависимостей.
Использованы штатные средства, показывающие зависимости проекта списком и
путями: `dotnet list package --include-transitive` и `dotnet nuget why`.

```
dotnet list package --include-transitive
```

```
<вставьте вывод>
```

```
dotnet nuget why Cmp.csproj Microsoft.Extensions.Options
```

```
<вставьте вывод>
```

Результат сравнения: `<наборы пакетов, версии, чем представление отличается:
плоский список и пути против графа, дерева и картинки>`.

Причины расхождений те же: платформа проекта и объединение всех платформ в
нашей программе, различия в выборе версий. Кроме того, `dotnet list` выводит
плоский список без связей «кто кого требует», а наша программа показывает
рёбра, дерево и изображение.

## Ограничения

- В SVG пакеты расставлены рядами по расстоянию от корня. Если в ряду много
  пакетов, изображение получается очень широким: например,
  `Microsoft.Extensions.Logging` на глубине 3 даёт изображение шириной около
  14 700 пикселей. Пересечения рёбер не минимизируются, ребро, пропускающее
  ряд, может пройти поверх чужой рамки. Для демонстрации используется
  небольшая глубина.
- Версии выбираются упрощённо (нижняя граница диапазона у первого упоминания),
  как в NuGet они выбираются не всегда.
- Зависимости объединяются по всем платформам, поэтому граф может быть больше
  графа для одной платформы.