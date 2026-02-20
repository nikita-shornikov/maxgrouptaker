#!/usr/bin/env python3
"""
СКРИПТ: Добавление пользователей в группу MAX по имени через веб-интерфейс

При запуске открывает веб-версию MAX, авторизуется, открывает группу.
Для указанного имени:
1. Открывает меню добавления участников
2. Вводит имя в поле поиска ("Найти по имени")
3. Находит ВСЕ результаты поиска с этим именем
4. Добавляет ВСЕХ найденных участников в группу
5. Подтверждает добавление

ТРЕБУЕТ НАСТРОЙКИ: При изменении интерфейса web.max.ru настройте селекторы в config.yaml (см. README.md).
"""
import logging
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Ошибка: установите PyYAML: pip install pyyaml")
    sys.exit(1)

from maxgrouptaker.web_automation import MaxWebAutomation

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def load_config(config_path: Path = Path("config.yaml")) -> dict:
    """Загрузить конфигурацию из YAML."""
    if not config_path.is_file():
        logger.error("Файл конфигурации не найден: %s", config_path)
        logger.info("Создайте config.yaml на основе config.example.yaml")
        sys.exit(1)
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def main():
    """Основная функция скрипта 2 (веб-версия)."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Скрипт 2 (веб): Добавление пользователей в группу MAX по имени через веб-интерфейс"
    )
    parser.add_argument(
        "--chat-id",
        type=str,
        help="ID группы-приёмника (в которую добавляем контакты). Если не указан, будет запрошен интерактивно",
    )
    parser.add_argument(
        "--name",
        type=str,
        help="Имя для поиска (будут добавлены ВСЕ пользователи с этим именем). Если не указано, будет запрошено интерактивно",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config.yaml"),
        help="Путь к config.yaml (по умолчанию: config.yaml)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Запустить браузер в headless режиме (без окна)",
    )
    parser.add_argument(
        "--browser",
        type=str,
        choices=["chromium", "firefox", "webkit"],
        default="chromium",
        help="Тип браузера (по умолчанию: chromium)",
    )
    
    args = parser.parse_args()
    
    # Интерактивный ввод параметров, если они не указаны
    chat_id = args.chat_id
    if not chat_id:
        print("\n" + "=" * 60)
        print("Введите ID группы (chat-id)")
        print("=" * 60)
        print("Как узнать ID группы:")
        print("  1. Откройте группу в web.max.ru")
        print("  2. Посмотрите URL: https://web.max.ru/-71285852438766")
        print("  3. Число после / (с минусом) - это ID группы")
        print("     Пример: -71285852438766")
        print("-" * 60)
        chat_id = input("ID группы: ").strip()
        if not chat_id:
            logger.error("ID группы не указан")
            sys.exit(1)
    
    name = args.name
    if not name:
        print("\n" + "=" * 60)
        print("Введите имя для поиска")
        print("=" * 60)
        print("Будут добавлены ВСЕ пользователи с этим именем")
        print("Примеры: Иван, Петр Петров, Мария")
        print("-" * 60)
        name = input("Имя для поиска: ").strip()
        if not name:
            logger.error("Имя не указано")
            sys.exit(1)
    
    # Загрузка конфига
    config = load_config(args.config)
    
    # Настройки веб-автоматизации из конфига
    web_config = config.get("web_automation", {})
    selectors = web_config.get("selectors")
    timeout = web_config.get("timeout", 30000)
    
    # Обработка имени
    logger.info("=" * 60)
    logger.info("СКРИПТ 2 (ВЕБ): Добавление пользователей в группу MAX по имени")
    logger.info("=" * 60)
    logger.info("Группа-приёмник: %s", chat_id)
    logger.info("Имя для поиска: %s", name)
    logger.info("Браузер: %s (headless: %s)", args.browser, args.headless)
    logger.info("-" * 60)
    logger.info("ВНИМАНИЕ: Откроется браузер. Пожалуйста, авторизуйтесь в MAX (QR-код или пароль)")
    logger.info("-" * 60)
    logger.info("Логика обработки:")
    logger.info("  1. Открывается группа и меню добавления участников")
    logger.info("  2. Вводится имя '%s' в поле поиска", name)
    logger.info("  3. Находятся ВСЕ результаты поиска с этим именем")
    logger.info("  4. ВСЕ найденные участники добавляются в группу")
    logger.info("-" * 60)
    
    try:
        automation = MaxWebAutomation(
            headless=args.headless,
            browser_type=args.browser,
            timeout=timeout,
            selectors=selectors,
            wait_for_auth=True,
        )
        
        with automation:
            added_count = automation.add_users_by_name_to_group(chat_id, name)
            
            logger.info("-" * 60)
            logger.info("✓ ГОТОВО: Обработка завершена")
            logger.info("  • Добавлено пользователей с именем '%s': %s", name, added_count)
            logger.info("=" * 60)
            return 0
            
    except KeyboardInterrupt:
        logger.info("\nПрервано пользователем")
        return 1
    except Exception as e:
        logger.exception("Ошибка при обработке: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
