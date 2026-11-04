# depgraph

Инструмент визуализации графа зависимостей пакетов NuGet (.NET).
Работает из командной строки. Менеджеры пакетов и сторонние библиотеки
для получения зависимостей не используются.

Текущий статус: этап 1 из 5 (разбор и проверка параметров).

## Структура

- `src/depgraph/` - исходный код;
- `tests/` - тесты и тестовые данные;
- `run.bat` - запуск приложения;
- `test.bat` - запуск тестов.

## Настройки

Все параметры задаются опциями командной строки.

| Опция | Обязательная | Описание |
|---|---|---|
| `--package` | да | Имя анализируемого пакета |
| `--repo` | да | URL репозитория или путь к файлу тестового репозитория |
| `--test-mode` | нет | Считать `--repo` путём к файлу тестового репозитория |
| `--package-version` | да | Версия пакета, например `13.0.3` |
| `--output` | нет | Имя файла с изображением графа (`.svg`), по умолчанию `graph.svg` |
| `--ascii-tree` | нет | Вывести зависимости в виде ASCII-дерева |
| `--max-depth` | нет | Максимальная глубина анализа, целое число от 1, по умолчанию 3 |

## Функции

- `cli.create_parser` - создаёт разборщик опций командной строки;
- `cli.format_config` - форматирует параметры в виде «ключ: значение»;
- `cli.main` - точка входа, возвращает код завершения;
- `config.validate_*` - проверка отдельных параметров, при ошибке
  выбрасывают `ConfigError`;
- `config.build_config` - собирает проверенную конфигурацию.

## Запуск и тесты

Нужен Python 3.10 или новее. Сборка не требуется.

```
run.bat --package Newtonsoft.Json --repo https://api.nuget.org/v3/index.json --package-version 13.0.3
test.bat
```

## Примеры

Запуск с реальным репозиторием:

```
run.bat --package Newtonsoft.Json --repo https://api.nuget.org/v3/index.json --package-version 13.0.3
package: Newtonsoft.Json
repo: https://api.nuget.org/v3/index.json
test_mode: False
version: 13.0.3
output: graph.svg
ascii_tree: False
max_depth: 3
```

Запуск с тестовым репозиторием:

```
run.bat --package A --repo tests\data\sample_repo.txt --test-mode --package-version 1.0 --max-depth 5
```

Пример ошибки:

```
run.bat --package A --repo https://example.com --package-version abc
depgraph: error: invalid package version: 'abc'
```