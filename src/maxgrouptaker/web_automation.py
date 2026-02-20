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
            "add_members_button": "button:has-text('Подписчики'), button.cell--clickable:has-text('Подписчики'), button.cell--primary:has-text('Подписчики'), button.cell--clickable.cell--primary:has-text('Подписчики')",  # Кнопка "Подписчики" для перехода в меню подписчиков
            "add_in_subscribers_button": "button:has-text('Добавить'), button.cell--clickable:has-text('Добавить'), .content button.cell--clickable.cell--primary",  # Кнопка добавления участников ВНУТРИ меню подписчиков
            "add_modal": ".modal",  # Модальное окно добавления участников
            "add_modal_search": ".modal .search input, .modal input[placeholder*='Поиск'], .modal input[placeholder*='поиск'], .modal input[placeholder*='Найти по имени']",  # Поле поиска/ввода имени в модальном окне
            "add_by_phone_input": "input[type='tel'], input[placeholder*='номер'], input[placeholder*='телефон'], .modal .search input",  # Поле ввода номера для добавления
            "add_modal_list": ".modal .list .item[data-index]",  # Элементы списка в модальном окне (для выбора из результатов поиска)
            "add_modal_item_button": ".modal .item[data-index] button.cell--clickable",  # Кнопка добавления внутри элемента списка (кнопка для добавления в список)
            "add_button": "button[aria-label='Добавить'], button[aria-label='добавить'], button.button--neutral-primary:has-text('Добавить'), button:has-text('Добавить'), button:has-text('добавить')",  # Кнопка финального подтверждения добавления участника в группу
            
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
            # Формат URL: https://web.max.ru/-71285852438766 (с минусом)
            # Если chat_id уже содержит минус - используем как есть, иначе добавляем минус
            chat_id_str = str(chat_id)
            if not chat_id_str.startswith("-"):
                # Если это положительное число, добавляем минус (группы обычно с минусом)
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
            
            # Шаг 1: Открыть меню добавления участников (кнопка "Подписчики")
            logger.info("Поиск кнопки 'Подписчики' для добавления участников...")
            add_button_selector = self.selectors.get("add_members_button")
            if add_button_selector:
                try:
                    logger.debug("Селектор кнопки: %s", add_button_selector)
                    # Ждём появления кнопки "Подписчики"
                    try:
                        self.page.wait_for_selector(add_button_selector, timeout=15000, state="visible")
                        time.sleep(1)
                    except Exception:
                        logger.debug("Кнопка не появилась по селектору, пробуем найти...")
                    
                    add_button = self.page.locator(add_button_selector).first
                    logger.debug("Найдено элементов: %s", add_button.count())
                    
                    # Если не найдено, пробуем найти по тексту
                    if add_button.count() == 0:
                        logger.info("Кнопка не найдена по селектору, ищем по тексту 'Подписчики'...")
                        add_button = self.page.locator("button:has-text('Подписчики')").first
                        logger.debug("Найдено кнопок с текстом 'Подписчики': %s", add_button.count())
                    
                    if add_button.count() > 0:
                        logger.info("Кнопка 'Подписчики' найдена, кликаем...")
                        add_button.click()
                        time.sleep(4)  # Увеличено время ожидания открытия меню подписчиков
                        logger.info("Меню 'Подписчики' открыто")
                        
                        # Теперь нужно найти кнопку добавления участников ВНУТРИ меню подписчиков
                        logger.info("Поиск кнопки добавления участников в меню подписчиков...")
                        time.sleep(2)  # Дополнительное ожидание загрузки меню
                        
                        # Ищем кнопку добавления в меню подписчиков (может быть кнопка "Добавить" или другая)
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
                                logger.debug("Пробуем селектор: %s", sel)
                                btn = self.page.locator(sel).first
                                count = btn.count()
                                logger.debug("Найдено элементов: %s", count)
                                if count > 0:
                                    logger.info("Кнопка добавления найдена по селектору: %s", sel)
                                    add_in_subscribers_button = btn
                                    break
                            except Exception as e:
                                logger.debug("Ошибка с селектором %s: %s", sel, e)
                                continue
                        
                        if add_in_subscribers_button and add_in_subscribers_button.count() > 0:
                            logger.info("Кликаем по кнопке добавления в меню подписчиков...")
                            try:
                                add_in_subscribers_button.click(timeout=5000, force=True)
                                logger.info("Клик выполнен")
                            except Exception as e:
                                logger.debug("Обычный клик не сработал, пробуем через JavaScript: %s", e)
                                # Пробуем через JavaScript
                                self.page.evaluate("""
                                    (function() {
                                        const buttons = Array.from(document.querySelectorAll('button'));
                                        const addBtn = buttons.find(btn => 
                                            btn.textContent.includes('Добавить') && 
                                            btn.classList.contains('cell--clickable')
                                        );
                                        if (addBtn) {
                                            addBtn.click();
                                            return true;
                                        }
                                        return false;
                                    })();
                                """)
                                logger.info("Клик выполнен через JavaScript")
                            time.sleep(4)  # Ждём открытия модального окна добавления
                        else:
                            logger.warning("Кнопка добавления в меню подписчиков не найдена")
                            logger.info("Продолжаем, возможно модальное окно уже открыто...")
                        
                        # Ждём появления модального окна
                        try:
                            modal_selector = self.selectors.get("add_modal", ".modal")
                            logger.debug("Ожидание появления модального окна...")
                            self.page.wait_for_selector(modal_selector, timeout=15000)
                            time.sleep(3)  # Дополнительное ожидание для полной загрузки модального окна
                            logger.info("Модальное окно добавления участников открыто")
                        except Exception as e:
                            logger.warning("Модальное окно не появилось, но продолжаем: %s", e)
                            time.sleep(3)  # Всё равно ждём дополнительное время
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
            
            # Шаг 2: Найти поле поиска в модальном окне и ввести имя
            logger.info("Поиск поля ввода имени в модальном окне...")
            modal_search_selector = self.selectors.get("add_modal_search")
            search_input = None
            if modal_search_selector:
                logger.debug("Селектор поля поиска: %s", modal_search_selector)
                search_input = self.page.locator(modal_search_selector).first
                logger.debug("Найдено полей поиска: %s", search_input.count())
            else:
                # Если селектор не найден, пробуем найти поле поиска альтернативными способами
                modal_search_selector = ".modal .search input, .modal input[placeholder*='Поиск'], .modal input[placeholder*='поиск'], .modal input[placeholder*='Найти по имени']"
                search_input = self.page.locator(modal_search_selector).first
            
            if not search_input or search_input.count() == 0:
                logger.warning("Поле поиска не найдено по селектору: %s", modal_search_selector)
                logger.info("Попробуйте обновить селектор add_modal_search в config.yaml")
                # Пробуем найти любое поле input в модальном окне
                logger.info("Пробуем найти любое поле input в модальном окне...")
                modal_selector = self.selectors.get("add_modal", ".modal")
                if modal_selector:
                    all_inputs = self.page.locator(f"{modal_selector} input").all()
                    logger.info("Найдено input полей в модальном окне: %s", len(all_inputs))
                    if len(all_inputs) > 0:
                        search_input = all_inputs[0]
                        logger.info("Используем первое найденное поле input")
                    else:
                        return 0
                else:
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
            
            modal_list_selector = self.selectors.get("add_modal_list", ".modal .list .item")
            modal_item_button_selector = self.selectors.get("add_modal_item_button")
            
            # Шаг 3: Добавляем пользователей по одному. Каждый раз вводим имя в поиск (чтобы список = только «Ц»),
            # затем нажимаем кнопку по счёту: 1-й раз — первую, 2-й раз — вторую и т.д. Так добавляется следующий «Ц», а не тот же первый.
            added_count = 0
            max_iterations = 500  # защита от бесконечного цикла
            
            logger.info("Добавление по имени '%s': каждый раз в поиск вводится имя, затем нажимается по счёту (1-й, 2-й, 3-й…).", name_for_search)
            
            for iteration in range(max_iterations):
                # 1. Каждый раз заново вводим имя в поиск — список показывает только совпадения (только «Ц»)
                search_input_el = self.page.locator(modal_search_selector).first
                if search_input_el.count() == 0:
                    logger.warning("Поле поиска не найдено на итерации %s", iteration + 1)
                    break
                search_input_el.clear()
                time.sleep(0.4)
                search_input_el.fill(name_for_search)
                time.sleep(2.5)  # ждём обновления результатов
                
                # 2. Берём все кнопки добавления в текущем списке (только отфильтрованные по имени)
                add_buttons = self.page.locator(modal_item_button_selector).all()
                if len(add_buttons) == 0:
                    # Пробуем по элементам списка
                    list_items = self.page.locator(modal_list_selector).all()
                    if len(list_items) == 0:
                        logger.debug("Результатов для '%s' больше нет (итерация %s).", name_for_search, iteration + 1)
                        break
                    # Кликаем по счёту: added_count = индекс следующего (0, 1, 2…)
                    if added_count >= len(list_items):
                        break
                    item_to_click = list_items[added_count]
                    try:
                        item_to_click.scroll_into_view_if_needed()
                        time.sleep(0.2)
                        item_to_click.click(timeout=3000, force=True)
                        added_count += 1
                        if added_count <= 3 or added_count % 10 == 0:
                            logger.info("  Добавлен пользователь %s (по имени '%s')", added_count, name_for_search)
                        time.sleep(0.8)
                    except Exception as e:
                        logger.warning("Ошибка при клике по элементу списка (индекс %s): %s", added_count, e)
                        break
                    continue
                
                # 3. Кликаем по счёту: 1-й раз — первая кнопка (индекс 0), 2-й раз — вторая (индекс 1) и т.д.
                if added_count >= len(add_buttons):
                    logger.debug("Все %s пользователей по имени '%s' уже добавлены.", len(add_buttons), name_for_search)
                    break
                
                btn_to_click = add_buttons[added_count]
                try:
                    btn_to_click.scroll_into_view_if_needed()
                    time.sleep(0.2)
                    btn_to_click.click(timeout=3000, force=True)
                except Exception:
                    try:
                        self.page.evaluate("""
                            (function(button) {
                                if (button && button.offsetParent !== null) {
                                    button.click();
                                    return true;
                                }
                                return false;
                            })(arguments[0]);
                        """, btn_to_click.element_handle())
                    except Exception as e:
                        logger.warning("Не удалось кликнуть по кнопке добавления (индекс %s): %s", added_count, e)
                        break
                
                added_count += 1
                if added_count <= 3 or added_count % 10 == 0:
                    logger.info("  Добавлен пользователь %s (по имени '%s')", added_count, name_for_search)
                time.sleep(0.8)
            
            logger.info("Выбрано пользователей для добавления: %s (по имени '%s').", added_count, name_for_search)
            
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
            
            # Шаг 5: Подтвердить добавление всех выбранных (финальная кнопка "Добавить")
            logger.info("Поиск кнопки подтверждения добавления...")
            confirm_button_selector = self.selectors.get("add_button") or self.selectors.get("confirm_button")
            
            # Пробуем разные селекторы для кнопки "Добавить"
            confirm_selectors_to_try = [
                "button[aria-label='Добавить']",
                "button.button--neutral-primary[aria-label='Добавить']",
                "button.button--stretched[aria-label='Добавить']",
                confirm_button_selector,
                "button:has-text('Добавить')",
            ]
            
            confirm_btn = None
            for sel in confirm_selectors_to_try:
                if not sel:
                    continue
                try:
                    logger.debug("Пробуем селектор кнопки подтверждения: %s", sel)
                    btn = self.page.locator(sel).first
                    count = btn.count()
                    logger.debug("Найдено кнопок: %s", count)
                    if count > 0:
                        # Проверяем что кнопка видима и кликабельна
                        if btn.is_visible():
                            logger.info("Кнопка подтверждения найдена по селектору: %s", sel)
                            confirm_btn = btn
                            break
                except Exception as e:
                    logger.debug("Ошибка с селектором %s: %s", sel, e)
                    continue
            
            if confirm_btn and confirm_btn.count() > 0:
                logger.info("Кликаем по кнопке подтверждения добавления...")
                try:
                    # Способ 1: Обычный клик
                    confirm_btn.click(timeout=5000, force=True)
                    logger.info("Клик выполнен (обычный способ)")
                except Exception as e1:
                    logger.debug("Обычный клик не сработал: %s", e1)
                    try:
                        # Способ 2: Через JavaScript
                        logger.debug("Пробуем клик через JavaScript...")
                        self.page.evaluate("""
                            (function() {
                                const btn = document.querySelector('button[aria-label="Добавить"]') ||
                                           document.querySelector('button.button--neutral-primary[aria-label="Добавить"]');
                                if (btn && btn.offsetParent !== null) {
                                    btn.click();
                                    return true;
                                }
                                return false;
                            })();
                        """)
                        logger.info("Клик выполнен (через JavaScript)")
                    except Exception as e2:
                        logger.warning("Клик через JavaScript не сработал: %s", e2)
                
                time.sleep(3)  # Ждём завершения добавления
                logger.info("Добавление подтверждено: добавлено %s пользователей с именем '%s'", added_count, name)
            else:
                logger.warning("Кнопка подтверждения добавления не найдена")
                logger.info("Попробуйте обновить селектор add_button в config.yaml")
                # Пробуем найти любую кнопку с текстом "Добавить"
                logger.info("Пробуем найти кнопку с текстом 'Добавить'...")
                all_buttons = self.page.locator("button:has-text('Добавить')").all()
                logger.info("Найдено кнопок с текстом 'Добавить': %s", len(all_buttons))
                if len(all_buttons) > 0:
                    logger.info("Кликаем по первой найденной кнопке 'Добавить'...")
                    try:
                        all_buttons[0].click(timeout=5000, force=True)
                        time.sleep(3)
                        logger.info("Добавление подтверждено (через альтернативную кнопку)")
                    except Exception as e:
                        logger.warning("Не удалось кликнуть по альтернативной кнопке: %s", e)
                        return 0
                else:
                    logger.error("Кнопка 'Добавить' не найдена. Возможно, пользователи не были выбраны из списка.")
                    return 0
            
            # Шаг 5: Закрываем модальное окно (чтобы цикл мог повториться для следующего имени)
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
