"""
Автоматизация веб-версии MAX через Playwright.
Добавление номеров из Excel в группу с проверками.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

try:
    from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright
except ImportError:
    sync_playwright = None  # type: ignore
    Browser = None  # type: ignore
    BrowserContext = None  # type: ignore
    Page = None  # type: ignore
    Playwright = None  # type: ignore

logger = logging.getLogger(__name__)


class MaxWebAutomation:
    """
    Автоматизация веб-версии MAX через Playwright.
    
    Требует настройки селекторов для элементов интерфейса MAX.
    Селекторы можно настроить в config.yaml или передать при инициализации.
    """

    def __init__(
        self,
        *,
        headless: bool = False,
        browser_type: str = "chromium",
        timeout: int = 30000,
        selectors: dict[str, str] | None = None,
        wait_for_auth: bool = True,
    ):
        """
        Инициализация автоматизации веб-версии MAX.
        
        Args:
            headless: Запускать браузер в headless режиме (без окна)
            browser_type: Тип браузера ('chromium', 'firefox', 'webkit')
            timeout: Таймаут ожидания элементов (мс)
            selectors: Словарь с CSS/XPath селекторами для элементов интерфейса
            wait_for_auth: Ждать авторизации пользователя (True) или использовать существующую сессию
        """
        if sync_playwright is None:
            raise ImportError(
                "Playwright не установлен. Установите: pip install playwright && playwright install"
            )
        
        self.headless = headless
        self.browser_type = browser_type
        self.timeout = timeout
        self.wait_for_auth = wait_for_auth
        
        # Селекторы по умолчанию (настроены под реальный интерфейс MAX)
        self.selectors = {
            # Навигация и поиск групп
            "search_input": "input[placeholder*='Найти'], input[placeholder*='Поиск']",  # Поле поиска групп/чатов
            "search_container": ".search",  # Контейнер поиска
            "chat_list_item": ".item[data-index]",  # Элемент списка групп/чатов (div.item с data-index)
            "chat_list_button": ".item[data-index] button.cell",  # Кнопка для перехода в группу (button.cell внутри .item)
            "scrollable_list": ".scrollListScrollable, .scrollable",  # Скроллируемый контейнер списка
            
            # Проверка участников в группе (для is_member_of_group)
            "group_info_button": "button[aria-label*='Открыть профиль'], button[aria-label*='открыть профиль'], button.main.content--clickable, button.content--clickable",  # Кнопка открытия профиля/информации о группе (в topbar)
            "members_tab": "button:has-text('Участники'), button:has-text('участники')",  # Вкладка участников
            "members_list": ".scrollListScrollable, [data-testid='members-list']",  # Список участников
            "member_item": "[data-member-id], [data-user-id], .item[data-index]",  # Элемент участника в списке
            
            # Добавление участников
            "add_members_button": "button:has-text('Добавить участников'), button.cell--primary.cell--clickable:has-text('Добавить участников'), button.cell.cell--primary:has-text('Добавить участников')",  # Кнопка "Добавить участников" для открытия модального окна добавления
            "add_in_subscribers_button": "button:has-text('Добавить'), button.cell--clickable:has-text('Добавить'), .content button.cell--clickable.cell--primary",  # Кнопка добавления участников ВНУТРИ меню подписчиков
            "add_modal": ".modal",  # Модальное окно добавления участников
            "add_modal_search": "[data-testid='modal'] input[placeholder='Найти по имени'], [data-testid='modal'] .search input, .modal .search input, .modal input[placeholder*='Найти по имени'], .modal input[placeholder*='Поиск']",  # Поле поиска/ввода имени в модальном окне «Выберите участников»
            "add_by_phone_input": "input[type='tel'], input[placeholder*='номер'], input[placeholder*='телефон'], .modal .search input",  # Поле ввода номера для добавления
            "add_modal_list": ".modal .list .item[data-index]",  # Элементы списка в модальном окне (для выбора из результатов поиска)
            "add_modal_item_button": ".modal .item[data-index] button.cell--clickable",  # Кнопка добавления внутри элемента списка (кнопка для добавления в список)
            "add_button": "button[aria-label*='добавить'], button.button--neutral-primary.button--stretched:has-text('Добавить'), button[aria-label='Добавить'], button[aria-label='добавить'], button.button--neutral-primary:has-text('Добавить'), button:has-text('Добавить')",  # Кнопка финального подтверждения «Добавить» (aria-label может быть «добавить.»)
            
            # Общие
            "close_button": "button[aria-label*='Закрыть'], button[aria-label*='закрыть']",  # Кнопка закрытия
            "confirm_button": "button:has-text('Подтвердить'), button:has-text('подтвердить')",  # Кнопка подтверждения
            **(selectors or {}),
        }
        
        self.playwright: Playwright | None = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None

    def start(self) -> None:
        """Запустить браузер и открыть веб-версию MAX."""
        if self.playwright is not None:
            logger.warning("Браузер уже запущен")
            return
        
        logger.info("Запуск браузера...")
        self.playwright = sync_playwright().start()
        
        browser_launcher = {
            "chromium": self.playwright.chromium,
            "firefox": self.playwright.firefox,
            "webkit": self.playwright.webkit,
        }.get(self.browser_type, self.playwright.chromium)
        
        self.browser = browser_launcher.launch(headless=self.headless)
        self.context = self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        )
        self.page = self.context.new_page()
        self.page.set_default_timeout(self.timeout)
        
        logger.info("Открытие веб-версии MAX...")
        self.page.goto("https://web.max.ru", wait_until="networkidle")
        
        if self.wait_for_auth:
            logger.info("Ожидание авторизации...")
            logger.info("Пожалуйста, авторизуйтесь в браузере (QR-код или пароль)")
            # Ждём пока пользователь авторизуется (проверяем наличие элементов чатов)
            self._wait_for_auth()

    def _wait_for_auth(self, max_wait: int = 300) -> None:
        """Ждать авторизации пользователя (появление списка чатов)."""
        if self.page is None:
            return
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            try:
                # Проверяем наличие элементов, которые появляются после авторизации
                # Это нужно настроить под реальный интерфейс
                if self.page.locator(self.selectors.get("search_input", "body")).count() > 0:
                    # Дополнительная проверка: есть ли список чатов
                    time.sleep(2)  # Даём время на загрузку
                    logger.info("Авторизация успешна")
                    return
            except Exception:
                pass
            time.sleep(2)
        
        logger.warning("Таймаут ожидания авторизации. Продолжаем...")

    def stop(self) -> None:
        """Закрыть браузер."""
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        
        self.page = None
        self.context = None
        self.browser = None
        self.playwright = None
        logger.info("Браузер закрыт")

    def __enter__(self) -> MaxWebAutomation:
        """Контекстный менеджер: вход."""
        self.start()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Контекстный менеджер: выход."""
        self.stop()

    def navigate_to_group(self, chat_id: int | str) -> bool:
        """
        Перейти к группе по chat_id.
        
        Args:
            chat_id: ID группы или название
            
        Returns:
            True если успешно перешли к группе
        """
        if self.page is None:
            raise RuntimeError("Браузер не запущен. Вызовите start()")
        
        try:
            # Вариант 1: Прямой переход по URL
            import re as _re
            chat_id_str = str(chat_id).strip()
            # Инвайт-ссылка: https://max.ru/join/TOKEN или https://web.max.ru/join/TOKEN
            _join = _re.search(r'max\.ru/join/(\S+)', chat_id_str)
            if _join:
                url = f"https://web.max.ru/join/{_join.group(1)}"
            elif not chat_id_str.startswith("-"):
                # Числовой ID без минуса — группы обычно с минусом
                url = f"https://web.max.ru/-{chat_id_str}"
            else:
                url = f"https://web.max.ru/{chat_id_str}"
            
            logger.info("Переход к группе: %s", url)
            self.page.goto(url, wait_until="networkidle", timeout=self.timeout)
            time.sleep(5)  # Увеличено время ожидания загрузки группы
            
            # Ждём появления элементов группы (например, topbar или контента группы)
            try:
                # Ждём появления элементов интерфейса группы
                logger.debug("Ожидание загрузки интерфейса группы...")
                self.page.wait_for_selector("main, .openedChat, .topbar, .header", timeout=15000)
                time.sleep(3)  # Дополнительное ожидание для полной загрузки всех элементов
                logger.info("Группа загружена")
            except Exception as e:
                logger.debug("Элементы группы не найдены, но продолжаем: %s", e)
                time.sleep(3)  # Всё равно ждём дополнительное время
            
            # Проверяем, что мы в группе (можно проверить наличие элементов группы)
            return True
            
        except Exception as e:
            logger.warning("Прямой переход не удался, пробуем через поиск: %s", e)
            
            # Вариант 2: Поиск группы через поиск
            try:
                # Ищем поле поиска (может быть в контейнере .search)
                search_container = self.selectors.get("search_container")
                search_input_selector = self.selectors.get("search_input")
                
                # Пробуем найти input внутри контейнера поиска или напрямую
                if search_container:
                    search_input = self.page.locator(f"{search_container} input").first
                    if search_input.count() == 0:
                        search_input = self.page.locator(search_input_selector).first
                else:
                    search_input = self.page.locator(search_input_selector).first
                
                if search_input.count() > 0:
                    search_input.fill(str(chat_id))
                    time.sleep(2)  # Ждём результатов поиска
                    
                    # Клик по кнопке внутри первого результата поиска
                    # Сначала пробуем найти кнопку для перехода в группу
                    chat_button_selector = self.selectors.get("chat_list_button", ".item[data-index] button.cell")
                    chat_button = self.page.locator(chat_button_selector).first
                    
                    if chat_button.count() > 0:
                        chat_button.click()
                        time.sleep(2)
                        logger.info("Переход к группе через поиск успешен (клик по кнопке)")
                        return True
                    else:
                        # Если кнопка не найдена, пробуем кликнуть по элементу списка
                        chat_item_selector = self.selectors.get("chat_list_item", ".item[data-index]")
                        first_result = self.page.locator(chat_item_selector).first
                        if first_result.count() > 0:
                            first_result.click()
                            time.sleep(2)
                            logger.info("Переход к группе через поиск успешен (клик по элементу)")
                            return True
                        else:
                            logger.warning("Результаты поиска не найдены")
            except Exception as e2:
                logger.error("Не удалось перейти к группе через поиск: %s", e2)
            
            return False

    def get_group_members(self, chat_id: int | str) -> list[dict[str, Any]]:
        """
        Получить список участников группы (используется только для проверки is_member_of_group).
        
        Args:
            chat_id: ID группы
            
        Returns:
            Список словарей с полями: user_id (остальные поля могут быть пустыми)
        """
        if self.page is None:
            raise RuntimeError("Браузер не запущен")
        
        if not self.navigate_to_group(chat_id):
            logger.error("Не удалось перейти к группе %s", chat_id)
            return []
        
        logger.info("Открытие списка участников группы...")
        members = []
        
        try:
            # Шаг 1: Открыть информацию о группе (кнопка в topbar)
            info_button = self.selectors.get("group_info_button")
            if info_button:
                try:
                    # Ищем кнопку в topbar (может быть button.main.content--clickable или button[aria-label*='Открыть профиль'])
                    info_btn = self.page.locator(info_button).first
                    if info_btn.count() > 0:
                        info_btn.click()
                        time.sleep(2)  # Ждём открытия интерфейса профиля/информации
                        logger.debug("Интерфейс профиля группы открыт")
                    else:
                        logger.debug("Кнопка информации не найдена")
                except Exception as e:
                    logger.debug("Ошибка при открытии информации о группе: %s", e)
            
            # Шаг 2: Перейти на вкладку участников
            members_tab = self.selectors.get("members_tab")
            if members_tab:
                try:
                    self.page.click(members_tab, timeout=5000)
                    time.sleep(2)
                except Exception:
                    logger.debug("Вкладка участников не найдена")
            
            # Шаг 3: Прокрутить список и собрать участников
            members_list = self.selectors.get("members_list", "body")
            member_item = self.selectors.get("member_item", "div")
            
            # Прокручиваем список до конца
            last_count = 0
            scroll_attempts = 0
            max_scrolls = 50
            
            while scroll_attempts < max_scrolls:
                # Парсим текущие элементы участников
                member_elements = self.page.locator(member_item).all()
                current_count = len(member_elements)
                
                if current_count == last_count:
                    # Больше не загружается
                    break
                
                last_count = current_count
                
                # Прокручиваем вниз
                self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(1)
                scroll_attempts += 1
            
            logger.info("Найдено участников: %s", last_count)
            
            # Шаг 4: Извлекаем только user_id участников (для проверки is_member_of_group)
            for i, element in enumerate(self.page.locator(member_item).all()):
                try:
                    # Извлекаем только user_id из data-атрибута
                    user_id_attr = element.get_attribute("data-member-id") or element.get_attribute("data-user-id")
                    user_id = int(user_id_attr) if user_id_attr and user_id_attr.isdigit() else None
                    
                    if user_id:
                        members.append({
                            "user_id": user_id,
                            "first_name": "",
                            "last_name": "",
                            "username": "",
                            "phone": "",
                        })
                    
                    if (i + 1) % 10 == 0:
                        logger.debug("Обработано участников: %s/%s", i + 1, last_count)
                        
                except Exception as e:
                    logger.warning("Ошибка при извлечении user_id участника %s: %s", i, e)
                    continue
            
            logger.info("Собрано участников: %s", len(members))
            return members
            
        except Exception as e:
            logger.exception("Ошибка при получении участников группы: %s", e)
            return []

    def check_user_exists(self, phone: str) -> int | None:
        """
        Проверить, есть ли пользователь с таким номером в MAX.
        
        Args:
            phone: Номер телефона
            
        Returns:
            user_id если пользователь найден, None если нет
        """
        if self.page is None:
            raise RuntimeError("Браузер не запущен")
        
        try:
            phone_normalized = self._normalize_phone(phone)
            if not phone_normalized:
                return None
            
            logger.debug("Поиск пользователя по номеру: %s***", phone_normalized[:4])
            
            # Шаг 1: Открыть поиск
            search_container = self.selectors.get("search_container")
            search_input_selector = self.selectors.get("search_input")
            
            # Пробуем найти input внутри контейнера поиска или напрямую
            if search_container:
                search_input = self.page.locator(f"{search_container} input").first
                if search_input.count() == 0:
                    search_input = self.page.locator(search_input_selector).first
            else:
                search_input = self.page.locator(search_input_selector).first
            
            if search_input.count() == 0:
                logger.warning("Поле поиска не найдено")
                return None
            
            search_input.fill(phone_normalized)
            time.sleep(2)  # Ждём результатов поиска
            
            # Шаг 2: Проверяем результаты поиска
            # Ищем элементы списка (div.item с data-index или data-chat-id)
            chat_item_selector = self.selectors.get("chat_list_item", ".item[data-index]")
            results = self.page.locator(chat_item_selector).all()
            
            if len(results) > 0:
                # Пытаемся извлечь user_id из первого результата
                first_result = results[0]
                # Пробуем разные атрибуты для user_id
                user_id_attr = (
                    first_result.get_attribute("data-user-id") or
                    first_result.get_attribute("data-chat-id") or
                    first_result.get_attribute("data-id")
                )
                
                if user_id_attr and user_id_attr.isdigit():
                    return int(user_id_attr)
                else:
                    # Если user_id нет в атрибутах, но результат есть - пользователь найден
                    # Возвращаем 1 как индикатор что пользователь существует
                    # (для добавления по номеру user_id может быть не нужен)
                    logger.debug("Пользователь найден, но user_id не извлечён из атрибутов")
                    return 1  # Индикатор что пользователь существует
            
            return None
            
        except Exception as e:
            logger.warning("Ошибка при проверке пользователя %s: %s", phone[:4] + "***", e)
            return None

    def is_member_of_group(self, chat_id: int | str, user_id: int) -> bool:
        """
        Проверить, состоит ли пользователь уже в группе.
        
        Args:
            chat_id: ID группы
            user_id: ID пользователя
            
        Returns:
            True если пользователь уже в группе
        """
        members = self.get_group_members(chat_id)
        for member in members:
            if member.get("user_id") == user_id:
                return True
        return False

    def add_user_to_group(self, chat_id: int | str, phone: str) -> bool:
        """
        Добавить пользователя в группу по номеру телефона.
        
        Args:
            chat_id: ID группы
            phone: Номер телефона пользователя
            
        Returns:
            True если пользователь успешно добавлен
        """
        if self.page is None:
            raise RuntimeError("Браузер не запущен")
        
        try:
            if not self.navigate_to_group(chat_id):
                return False
            
            phone_normalized = self._normalize_phone(phone)
            if not phone_normalized:
                logger.warning("Невалидный номер телефона: %s", phone)
                return False
            
            logger.info("Добавление пользователя %s*** в группу %s", phone_normalized[:4], chat_id)
            
            # Шаг 1: Открыть меню добавления участников
            add_button_selector = self.selectors.get("add_members_button")
            if add_button_selector:
                try:
                    # Ищем кнопку в cellList (может быть button.cell--clickable.cell--primary)
                    add_button = self.page.locator(add_button_selector).first
                    if add_button.count() > 0:
                        add_button.click()
                        time.sleep(2)  # Ждём открытия меню добавления
                        logger.debug("Меню добавления участников открыто")
                    else:
                        logger.debug("Кнопка добавления не найдена")
                except Exception as e:
                    logger.debug("Ошибка при открытии меню добавления: %s", e)
            
            # Шаг 2: Найти поле ввода номера в модальном окне
            # Сначала пробуем найти поле поиска в модальном окне
            modal_search_selector = self.selectors.get("add_modal_search")
            phone_input_selector = self.selectors.get("add_by_phone_input")
            
            phone_input = None
            if modal_search_selector:
                phone_input = self.page.locator(modal_search_selector).first
                if phone_input.count() == 0:
                    phone_input = self.page.locator(phone_input_selector).first
            else:
                phone_input = self.page.locator(phone_input_selector).first
            
            if phone_input and phone_input.count() > 0:
                phone_input.fill(phone_normalized)
                time.sleep(2)  # Ждём результатов поиска
                
                # Шаг 2.1: Если есть результаты поиска, кликаем по кнопке добавления внутри первого элемента списка
                modal_item_button_selector = self.selectors.get("add_modal_item_button")
                if modal_item_button_selector:
                    # Ищем кнопку добавления внутри первого элемента списка
                    add_to_list_button = self.page.locator(modal_item_button_selector).first
                    if add_to_list_button.count() > 0:
                        add_to_list_button.click()
                        time.sleep(1)
                        logger.debug("Клик по кнопке добавления в список выполнен")
                    else:
                        # Если кнопка не найдена, пробуем кликнуть по самому элементу списка
                        modal_list_selector = self.selectors.get("add_modal_list")
                        if modal_list_selector:
                            first_result = self.page.locator(modal_list_selector).first
                            if first_result.count() > 0:
                                first_result.click()
                                time.sleep(1)
                                logger.debug("Клик по первому элементу списка выполнен")
            else:
                logger.warning("Поле ввода номера не найдено")
            
            # Шаг 3: Подтвердить добавление (финальная кнопка "Добавить")
            confirm_button_selector = self.selectors.get("add_button") or self.selectors.get("confirm_button")
            if confirm_button_selector:
                confirm_btn = self.page.locator(confirm_button_selector).first
                if confirm_btn.count() > 0:
                    confirm_btn.click()
                    time.sleep(2)  # Ждём завершения добавления
                    logger.debug("Добавление подтверждено (кнопка 'Добавить' нажата)")
                    
                    # Шаг 3.1: Закрываем модальное окно если оно не закрылось автоматически
                    # (чтобы цикл мог повториться для следующего номера)
                    close_button_selector = self.selectors.get("close_button")
                    if close_button_selector:
                        try:
                            close_btn = self.page.locator(close_button_selector).first
                            if close_btn.count() > 0:
                                close_btn.click()
                                time.sleep(1)
                                logger.debug("Модальное окно закрыто")
                        except Exception:
                            pass  # Модальное окно могло закрыться автоматически
                else:
                    logger.warning("Кнопка подтверждения добавления не найдена")
            
            # Шаг 4: Проверяем успешность (можно проверить появление уведомления или проверкой участников)
            logger.info("Пользователь добавлен (требует проверки)")
            return True
            
        except Exception as e:
            logger.exception("Ошибка при добавлении пользователя %s в группу: %s", phone[:4] + "***", e)
            return False

    def add_users_by_name_to_group(self, chat_id: int | str, name: str) -> int:
        """
        Добавить всех пользователей с указанным именем в группу.
        
        Args:
            chat_id: ID группы
            name: Имя для поиска
            
        Returns:
            Количество добавленных пользователей
        """
        if self.page is None:
            raise RuntimeError("Браузер не запущен")
        
        try:
            if not self.navigate_to_group(chat_id):
                return 0
            
            logger.info("Поиск и добавление пользователей с именем '%s' в группу %s", name, chat_id)
            
            # Шаг 0: Открыть профиль группы (кнопка в topbar с aria-label="Открыть профиль...")
            logger.info("Открытие профиля группы...")
            group_info_selector = self.selectors.get("group_info_button")
            if group_info_selector:
                try:
                    logger.debug("Ожидание появления кнопки открытия профиля...")
                    # Ждём появления кнопки открытия профиля (может быть button.main.content--clickable)
                    # Пробуем разные селекторы
                    selectors_to_try = [
                        "button[aria-label*='Открыть профиль']",
                        "button.main.content--clickable",
                        "button.content--clickable",
                        group_info_selector
                    ]
                    
                    group_info_button = None
                    for sel in selectors_to_try:
                        try:
                            self.page.wait_for_selector(sel, timeout=10000, state="visible")
                            group_info_button = self.page.locator(sel).first
                            if group_info_button.count() > 0:
                                logger.info("Кнопка открытия профиля найдена по селектору: %s", sel)
                                break
                        except Exception:
                            continue
                    
                    if group_info_button and group_info_button.count() > 0:
                        logger.info("Кликаем по кнопке открытия профиля...")
                        time.sleep(1)  # Небольшая пауза перед кликом
                        
                        # Пробуем несколько способов клика
                        try:
                            # Способ 1: Обычный клик
                            group_info_button.click(timeout=5000, force=True)
                            logger.info("Клик выполнен (обычный способ)")
                        except Exception as e1:
                            logger.debug("Обычный клик не сработал: %s", e1)
                            try:
                                # Способ 2: Через JavaScript
                                logger.debug("Пробуем клик через JavaScript...")
                                self.page.evaluate("""
                                    (function() {
                                        const btn = document.querySelector('button[aria-label*="Открыть профиль"]') || 
                                                   document.querySelector('button.main.content--clickable') ||
                                                   document.querySelector('button.content--clickable');
                                        if (btn) {
                                            btn.click();
                                            return true;
                                        }
                                        return false;
                                    })();
                                """)
                                logger.info("Клик выполнен (через JavaScript)")
                            except Exception as e2:
                                logger.warning("Клик через JavaScript не сработал: %s", e2)
                        
                        time.sleep(4)  # Ждём открытия профиля группы
                        logger.info("Профиль группы должен быть открыт")
                    else:
                        logger.warning("Кнопка открытия профиля не найдена ни по одному селектору")
                        logger.info("Продолжаем без открытия профиля...")
                        time.sleep(2)
                except Exception as e:
                    logger.warning("Ошибка при открытии профиля группы: %s", e)
                    logger.info("Продолжаем без открытия профиля...")
                    time.sleep(2)
            
            # Шаг 1: Открыть меню добавления участников (кнопка "Добавить участников" для группового чата; для канала — "Подписчики")
            logger.info("Поиск кнопки добавления участников (add_members_button)...")
            add_button_selector = self.selectors.get("add_members_button")
            if add_button_selector:
                try:
                    logger.debug("Селектор кнопки: %s", add_button_selector)
                    # Ждём появления кнопки
                    try:
                        self.page.wait_for_selector(add_button_selector, timeout=15000, state="visible")
                        time.sleep(1)
                    except Exception:
                        logger.debug("Кнопка не появилась по селектору, пробуем найти...")
                    
                    add_button = self.page.locator(add_button_selector).first
                    logger.debug("Найдено элементов: %s", add_button.count())
                    
                    # Если не найдено, пробуем найти по тексту "Добавить участников" (групповой чат) или "Подписчики" (канал)
                    if add_button.count() == 0:
                        logger.info("Кнопка не найдена по селектору, ищем по тексту...")
                        add_button = self.page.locator("button:has-text('Добавить участников'), button:has-text('Подписчики')").first
                        logger.debug("Найдено кнопок: %s", add_button.count())
                    
                    if add_button.count() > 0:
                        logger.info("Кнопка найдена, кликаем...")
                        add_button.click()
                        time.sleep(2)
                        
                        # В групповом чате модалка «Выберите участников» открывается сразу.
                        # В канале сначала открывается меню, и нужен ещё клик по «Добавить».
                        # Не кликаем по кнопке «Добавить» (add_in_subscribers), если модалка уже видна —
                        # иначе можно нажать «Закрыть» или подтверждение и закрыть модалку.
                        modal_selector = self.selectors.get("add_modal", ".modal")
                        modal_already_open = False
                        try:
                            self.page.wait_for_selector(modal_selector, timeout=4000)
                            # Проверяем, что видно именно модалку выбора участников (есть поле поиска)
                            search_in_modal = self.page.locator("[data-testid='modal'] input[placeholder='Найти по имени'], .modal .search input").first
                            if search_in_modal.count() > 0 and search_in_modal.is_visible():
                                modal_already_open = True
                                logger.info("Модальное окно «Выберите участников» уже открыто (групповой чат), второй клик не нужен")
                        except Exception:
                            pass
                        
                        if not modal_already_open:
                            logger.info("Поиск кнопки добавления в меню (канал)...")
                            time.sleep(2)
                            add_in_subscribers_selector = self.selectors.get("add_in_subscribers_button")
                            add_in_subscribers_selectors = [
                                add_in_subscribers_selector,
                                "button:has-text('Добавить')",
                                "button.cell--clickable:has-text('Добавить')",
                                "button.cell--primary:has-text('Добавить')",
                                ".content button.cell--clickable.cell--primary",
                                "button.cell--clickable.cell--primary",
                            ]
                            add_in_subscribers_button = None
                            for sel in add_in_subscribers_selectors:
                                if not sel:
                                    continue
                                try:
                                    btn = self.page.locator(sel).first
                                    if btn.count() > 0:
                                        add_in_subscribers_button = btn
                                        break
                                except Exception:
                                    continue
                            if add_in_subscribers_button and add_in_subscribers_button.count() > 0:
                                try:
                                    add_in_subscribers_button.click(timeout=5000, force=True)
                                    time.sleep(3)
                                except Exception:
                                    try:
                                        self.page.evaluate("""(function(){
                                            var b = Array.from(document.querySelectorAll('button')).find(function(btn){
                                                return btn.textContent.includes('Добавить') && btn.classList.contains('cell--clickable');
                                            });
                                            if(b){ b.click(); return true; }
                                            return false;
                                        })();""")
                                    except Exception:
                                        pass
                                    time.sleep(3)
                        
                        try:
                            self.page.wait_for_selector(modal_selector, timeout=12000)
                            time.sleep(2)
                            logger.info("Модальное окно добавления участников открыто")
                        except Exception as e:
                            logger.warning("Модальное окно не появилось: %s", e)
                            time.sleep(2)
                    else:
                        logger.warning("Кнопка добавления не найдена по селектору: %s", add_button_selector)
                        logger.info("Попробуйте обновить селектор add_members_button в config.yaml")
                        return 0
                except Exception as e:
                    logger.exception("Ошибка при открытии меню добавления: %s", e)
                    return 0
            else:
                logger.warning("Селектор add_members_button не настроен в config.yaml")
                return 0
            
            # Шаг 2: Найти поле поиска в модальном окне («Найти по имени») и ввести имя
            logger.info("Поиск поля ввода имени в модальном окне...")
            modal_search_selector = self.selectors.get("add_modal_search")
            if not modal_search_selector:
                modal_search_selector = "[data-testid='modal'] input[placeholder='Найти по имени'], [data-testid='modal'] .search input, .modal .search input, .modal input[placeholder*='Найти по имени']"
            
            logger.debug("Селектор поля поиска: %s", modal_search_selector)
            # Ждём появления поля поиска в модальном окне (модал «Выберите участников»)
            try:
                self.page.wait_for_selector(modal_search_selector, timeout=10000, state="visible")
                time.sleep(0.5)  # даём полю отрисоваться
            except Exception as e:
                logger.warning("Ожидание поля поиска по селектору не сработало: %s", e)
            
            search_input = self.page.locator(modal_search_selector).first
            if search_input.count() == 0:
                logger.warning("Поле поиска не найдено по селектору: %s", modal_search_selector)
                logger.info("Пробуем найти поле по [data-testid='modal'] или .modal...")
                fallback = self.page.locator("[data-testid='modal'] input[type='text'], .modal .body input").first
                if fallback.count() > 0:
                    search_input = fallback
                    modal_search_selector = "[data-testid='modal'] input[type='text'], .modal .body input"
                    logger.info("Используем запасной селектор поля поиска")
                else:
                    logger.info("Попробуйте обновить селектор add_modal_search в config.yaml")
                    return 0
            
            # Очищаем поле и вводим имя
            # Убираем смайлики и эмодзи из имени для поиска
            # (поиск может не находить контакты со смайликами, поэтому ищем по текстовой части)
            import re
            # Убираем все эмодзи и смайлики из имени для поиска
            # Это включает основные диапазоны Unicode для эмодзи
            name_for_search = re.sub(
                r'[\U0001F300-\U0001F9FF\U00002600-\U000027BF\U0001F600-\U0001F64F\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002700-\U000027BF\U0001F900-\U0001F9FF\U00002600-\U000026FF\U00002700-\U000027BF]+',
                '',
                name
            ).strip()
            # Если после удаления смайликов ничего не осталось, используем исходное имя
            if not name_for_search:
                name_for_search = name

            # Паттерн для точного совпадения: "Борис" совпадает с "Борис Иванов",
            # но НЕ с "Борисов" или "Бабушка"
            name_pattern = re.compile(
                r'(?<![а-яёa-zA-ZА-ЯЁ])' + re.escape(name_for_search) + r'(?![а-яёa-zA-ZА-ЯЁ])',
                re.IGNORECASE | re.UNICODE,
            )

            modal_list_selector = self.selectors.get("add_modal_list", ".modal .list .item")
            modal_item_button_selector = self.selectors.get("add_modal_item_button")
            BATCH_SIZE = 10
            total_added = 0
            is_first_batch = True
            add_button_selector_for_reopen = self.selectors.get("add_members_button")
            PAUSE_EVERY = 100       # пауза каждые N добавленных участников
            PAUSE_SECONDS = 3600    # длина паузы в секундах (1 час)
            last_pause_at = 0       # сколько было добавлено на момент последней паузы
            
            def _fill_search_and_get_list():
                search_el = self.page.locator(modal_search_selector).first
                if search_el.count() == 0:
                    return [], []
                try:
                    search_el.click()
                    time.sleep(0.3)
                    # fill() всегда заменяет всё содержимое поля целиком —
                    # сначала пустая строка (сброс), затем нужное имя
                    search_el.fill('')
                    time.sleep(0.1)
                    search_el.fill(name_for_search)
                except Exception:
                    return [], []
                # Ждём пока MAX обновит список под фильтр
                time.sleep(3.0)
                add_buttons = self.page.locator(modal_item_button_selector).all()
                list_items = self.page.locator(modal_list_selector).all() if len(add_buttons) == 0 else []
                return add_buttons, list_items
            
            def _click_confirm_add():
                for sel in ["button[aria-label*='добавить']", "button.button--neutral-primary.button--stretched:has-text('Добавить')", "button:has-text('Добавить')"]:
                    try:
                        btn = self.page.locator(sel).first
                        if btn.count() > 0 and btn.is_visible():
                            btn.click(timeout=5000, force=True)
                            return True
                    except Exception:
                        continue
                return False
            
            logger.info("Добавление по имени '%s' партиями по %s...", name_for_search, BATCH_SIZE)
            modal_sel = self.selectors.get("add_modal", ".modal")

            def _get_search_el():
                return self.page.locator(modal_search_selector).first

            def _type_name_and_get_matching(index: int):
                """Вводит имя в поиск и возвращает элемент с нужным индексом."""
                logger.info("  [%s] Ищем поле поиска...", index)
                sel = _get_search_el()
                if sel.count() == 0:
                    logger.info("  [%s] Поле поиска не найдено — выходим", index)
                    return None
                try:
                    logger.info("  [%s] Клик по полю поиска...", index)
                    sel.click(timeout=5000, force=True)
                    time.sleep(0.2)
                    logger.info("  [%s] Очистка и ввод имени '%s'...", index, name_for_search)
                    # force=True — не ждать actionability (обходит зависание при rate-limit)
                    # timeout=5000 — максимум 5 сек на операцию
                    sel.fill('', force=True, timeout=5000)
                    time.sleep(0.1)
                    sel.fill(name_for_search, force=True, timeout=5000)
                except Exception as e:
                    logger.warning("  [%s] Не удалось ввести имя в поиск: %s", index, e)
                    return None

                logger.info("  [%s] Ждём результатов поиска...", index)
                time.sleep(2.5)

                btns = self.page.locator(modal_item_button_selector).all() if modal_item_button_selector else []
                elements = btns if btns else self.page.locator(modal_list_selector).all()
                logger.info("  [%s] Найдено элементов в списке: %s", index, len(elements))

                if not elements:
                    logger.info("  [%s] Список пуст — все добавлены или поиск не дал результатов", index)
                    return None

                # Фильтруем по имени
                matching = []
                for el in elements:
                    text = ''
                    try:
                        # timeout=3000 — чтобы evaluate() не зависал при заторможённой странице
                        text = el.evaluate("""el => {
                            const item = el.closest('[data-index]') || el.closest('.item') || el.parentElement;
                            return (item?.innerText || '').trim().slice(0, 150);
                        }""", timeout=3000)
                        text = (text or '').strip()
                    except Exception:
                        pass
                    if not text or name_pattern.search(text):
                        matching.append(el)

                logger.info("  [%s] Подходящих по имени: %s", index, len(matching))

                if index < len(matching):
                    return matching[index]

                logger.info("  [%s] Индекс >= кол-ва результатов (%s) — партия завершена", index, len(matching))
                return None

            def _open_add_members_modal():
                """Открывает модалку добавления участников (ищет кнопку, кликает).
                Возвращает True если модалка открылась."""
                for btn_sel in [
                    "button:has-text('Добавить участников')",
                    add_button_selector_for_reopen,
                    "button.cell--primary:has-text('Добавить участников')",
                    "button:has-text('Подписчики')",
                ]:
                    if not btn_sel:
                        continue
                    try:
                        self.page.wait_for_selector(btn_sel, timeout=5000, state="visible")
                        time.sleep(0.5)
                        self.page.locator(btn_sel).first.click(timeout=5000, force=True)
                        time.sleep(2)
                        # Для каналов может быть второй клик «Добавить» внутри меню
                        try:
                            add_in = self.page.locator("button.cell--clickable:has-text('Добавить')").first
                            if add_in.count() > 0 and add_in.is_visible():
                                add_in.click(timeout=3000)
                                time.sleep(2)
                        except Exception:
                            pass
                        self.page.wait_for_selector(modal_sel, timeout=8000)
                        time.sleep(0.5)
                        self.page.wait_for_selector(modal_search_selector, timeout=6000, state="visible")
                        return True
                    except Exception:
                        continue
                return False

            def _reopen_modal():
                """Переоткрывает модалку после закрытия. Возвращает True если успешно."""
                time.sleep(2)

                # Возможно модалка уже открыта
                try:
                    if _get_search_el().is_visible():
                        return True
                except Exception:
                    pass

                # Попытка 1: кнопка «Добавить участников» видна напрямую
                if _open_add_members_modal():
                    logger.info("Модалка открыта")
                    return True

                # Попытка 2: профиль группы закрылся вместе с модалкой —
                # открываем его снова, затем ищем кнопку
                logger.info("Кнопка не найдена, переоткрываем профиль группы...")
                group_info_selectors = [
                    "button[aria-label*='Открыть профиль']",
                    "button[aria-label*='открыть профиль']",
                    "button.main.content--clickable",
                    "button.content--clickable",
                    self.selectors.get("group_info_button", ""),
                ]
                for sel in group_info_selectors:
                    if not sel:
                        continue
                    try:
                        self.page.wait_for_selector(sel, timeout=5000, state="visible")
                        self.page.locator(sel).first.click(timeout=5000, force=True)
                        time.sleep(3)
                        logger.info("Профиль группы переоткрыт")
                        break
                    except Exception:
                        continue

                # Теперь снова ищем кнопку добавления
                if _open_add_members_modal():
                    logger.info("Модалка открыта после переоткрытия профиля")
                    return True

                return False

            while True:
                if not is_first_batch:
                    logger.info("Следующая партия... Открываем «Добавить участников»...")
                    if not _reopen_modal():
                        logger.warning("Не удалось открыть модалку")
                        break

                # ── Набираем партию: каждый раз вводим имя → берём [i]-й результат ──
                # После клика контакт остаётся в списке на той же позиции,
                # поэтому следующий ввод имени берём уже элемент [i+1], [i+2]...
                clicked_in_this_batch = 0
                for i in range(BATCH_SIZE):
                    el = _type_name_and_get_matching(index=i)
                    if el is None:
                        logger.info("Результаты поиска закончились на позиции %s.", i)
                        break
                    try:
                        el.scroll_into_view_if_needed(timeout=3000)
                        time.sleep(0.2)
                        el.click(timeout=3000, force=True)
                        clicked_in_this_batch += 1
                    except Exception as e:
                        logger.warning("Ошибка клика по элементу %s: %s", i, e)
                        break
                    time.sleep(0.5)

                if clicked_in_this_batch == 0:
                    if is_first_batch:
                        logger.warning("Не найдено результатов для имени '%s'", name_for_search)
                    else:
                        logger.info("Больше нет пользователей для добавления.")
                    break

                logger.info("Выбрано %s человек, нажимаем «Добавить»...", clicked_in_this_batch)
                if not _click_confirm_add():
                    logger.warning("Кнопка «Добавить» не найдена")
                    break

                total_added += clicked_in_this_batch
                time.sleep(2)

                # Если набрали меньше полной партии — больше никого нет
                if clicked_in_this_batch < BATCH_SIZE:
                    logger.info("Все пользователи добавлены.")
                    break

                # Пауза каждые PAUSE_EVERY добавленных участников
                if total_added - last_pause_at >= PAUSE_EVERY:
                    logger.info(
                        "Добавлено %s участников. Пауза %s мин...",
                        total_added, PAUSE_SECONDS // 60,
                    )
                    for remaining in range(PAUSE_SECONDS, 0, -60):
                        logger.info("  Возобновление через %s мин.", remaining // 60)
                        time.sleep(60)
                    last_pause_at = total_added
                    logger.info("Пауза окончена, продолжаем...")

                is_first_batch = False
            
            added_count = total_added
            logger.info("Всего добавлено пользователей с именем '%s': %s", name_for_search, added_count)
            
            if added_count == 0:
                logger.warning("Не найдено результатов для имени '%s'", name)
                logger.info("Возможные причины:")
                logger.info("  1. Пользователей с таким именем нет в ваших контактах")
                logger.info("  2. Селекторы не настроены правильно (проверьте config.yaml)")
                logger.info("  3. Модальное окно не открылось или открылось не полностью")
                # Делаем скриншот для отладки
                try:
                    screenshot_path = f"debug_screenshot_{int(time.time())}.png"
                    self.page.screenshot(path=screenshot_path)
                    logger.info("Скриншот сохранён: %s", screenshot_path)
                except Exception:
                    pass
                # Закрываем модальное окно
                close_button_selector = self.selectors.get("close_button")
                if close_button_selector:
                    try:
                        close_btn = self.page.locator(close_button_selector).first
                        if close_btn.count() > 0:
                            close_btn.click()
                            time.sleep(1)
                    except Exception:
                        pass
                return 0
            
            # Закрываем модальное окно, если оно ещё открыто (после последней партии могло закрыться по «Добавить»)
            close_button_selector = self.selectors.get("close_button")
            if close_button_selector:
                try:
                    close_btn = self.page.locator(close_button_selector).first
                    if close_btn.count() > 0:
                        close_btn.click()
                        time.sleep(1)
                        logger.debug("Модальное окно закрыто")
                except Exception:
                    pass  # Модальное окно могло закрыться автоматически
            
            return added_count
            
        except Exception as e:
            logger.exception("Ошибка при добавлении пользователей с именем '%s' в группу: %s", name, e)
            return 0

    @staticmethod
    def _normalize_phone(phone: str) -> str | None:
        """Нормализовать номер телефона."""
        if not phone:
            return None
        
        digits = "".join(c for c in phone if c.isdigit())
        if not digits:
            return None
        
        if digits.startswith("8") and len(digits) == 11:
            digits = "7" + digits[1:]
        elif digits.startswith("7") and len(digits) == 11:
            pass
        elif len(digits) == 10:
            digits = "7" + digits
        else:
            return digits
        
        return digits
