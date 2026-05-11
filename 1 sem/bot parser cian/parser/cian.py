import os
import time
import random
import re
from urllib.parse import urlencode, urlunparse, urlparse, ParseResult

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
)
import pandas as pd

CITY_NAME = "chelyabinsk"
PAGES_LIMIT = '1'
MODE = "full"  # test or full
SALE = 'rent'  # sale or rent

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), f"{CITY_NAME}_cian_{SALE}.csv")

CITY_REGIONS = {
    "moscow": {"name": "Москва", "region": "1"},
    "spb": {"name": "Санкт-Петербург", "region": "2"},
    "ekaterinburg": {"name": "Екатеринбург", "region": "4743"},
    "chelyabinsk": {"name": "Челябинск", "region": "5048"},
}

COLUMNS = [
    "Ссылка",
    "Адрес",
    "Цена",
    "Тип помещения",
    "Площадь",
    "Этаж",
    "Этажей в доме",
    "Телефон",
]

HEADLESS = True
SELECTORS_BY_SALE_TYPE = {
    'sale': {
        'price': [
            "[data-testid='price-amount']",
            "[itemprop='price']",
            "[data-mark='MainPrice']",
            "span[class*='Price']",
            "[class*='price']",
        ],
        'address': [
            "[data-testid='address']",
            "[data-name='Address']",
            "[itemprop='address']",
            "[class*='address']",
        ],
        'title': [
            "h1[data-name='OfferTitle']",
            "h1[data-testid='object-title']",
            "h1",
        ],
    },
    'rent': {
        'price': [
            "[data-testid='price-amount']",
            "[class*='price-value']",
            "[class*='MainPrice']",
            "span[class*='price']",
            "[itemprop='price']",
        ],
        'address': [
            "[data-testid='address']",
            "[class*='address']",
            "[data-name='Address']",
            "[itemprop='address']",
        ],
        'title': [
            "h1[data-testid='object-title']",
            "h1[data-name='OfferTitle']",
            "h1",
        ],
    }
}

def get_selectors(selector_type):
    """Возвращает селекторы для текущего типа сделки (sale/rent)."""
    sale_type = SALE if SALE in SELECTORS_BY_SALE_TYPE else 'sale'
    return SELECTORS_BY_SALE_TYPE[sale_type].get(selector_type, [])


# ================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==================

def get_driver():
    """Создает и возвращает драйвер браузера (Firefox → Chrome)."""
    try:
        options = FirefoxOptions()
        if HEADLESS:
            options.add_argument("--headless")
            options.add_argument("--width=1920")
            options.add_argument("--height=1080")
        driver = webdriver.Firefox(options=options)
        print("✓ Firefox браузер запущен")
        return driver
    except Exception as e:
        print(f"⚠ Firefox не найден: {e}")
        print("Пробуем Chrome...")
        try:
            options = ChromeOptions()
            if HEADLESS:
                options.add_argument("--headless")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--window-size=1920,1080")
            driver = webdriver.Chrome(options=options)
            print("✓ Chrome браузер запущен")
            return driver
        except Exception as e2:
            print(f"✗ Ошибка при запуске браузера: {e2}")
            raise


def resolve_settings():
    """Готовит настройки без запросов к пользователю."""
    mode = (MODE or "test").strip().lower()
    pages_raw = PAGES_LIMIT if PAGES_LIMIT is not None else 0
    pages = int(pages_raw) if isinstance(pages_raw, (int, float, str)) and str(pages_raw).isdigit() else 0
    city_key = (CITY_NAME or "").strip().lower()

    if city_key not in CITY_REGIONS:
        raise ValueError(f"Город '{CITY_NAME}' не найден в CITY_REGIONS")

    city_info = CITY_REGIONS[city_key]

    if mode not in ("test", "full"):
        mode = "test"

    max_pages = None if mode == "full" else (pages if pages > 0 else 1)
    return mode, max_pages, city_info


def build_search_page_url(region_id: str, page: int) -> str:
    """Строит URL поиска cat.php с нужным region и p."""
    query = {
        "deal_type": f"{SALE}",
        "engine_version": "2",
        "offer_type": "offices",
        "office_type[0]": "1",
        "p": str(page),
        "region": str(region_id),
    }

    parsed = ParseResult(
        scheme="https",
        netloc="cian.ru",
        path="/cat.php",
        params="",
        query=urlencode(query),
        fragment="",
    )

    return urlunparse(parsed)


def safe_find_text(driver_or_element, selector, default=""):
    """Безопасно возвращает текст по CSS-селектору."""
    try:
        elem = driver_or_element.find_element(By.CSS_SELECTOR, selector)
        return elem.text.strip() if elem else default
    except (NoSuchElementException, AttributeError, StaleElementReferenceException):
        return default


def safe_find_texts(driver_or_element, selectors, default=""):
    """Перебор нескольких селекторов, возвращает первый найденный текст."""
    if isinstance(selectors, str):
        selectors = [selectors]
    for selector in selectors:
        try:
            text = safe_find_text(driver_or_element, selector)
            if text:
                return text
        except Exception:
            continue
    return default


def extract_price(text):
    """Парсит цену из строки. Если диапазон — возвращает строку."""
    if not text:
        return None

    if "–" in text or "-" in text:
        separator = "–" if "–" in text else "-"
        parts = text.split(separator, 1)
        if len(parts) == 2:
            min_price = re.sub(r"[^\d]", "", parts[0].strip())
            max_price = re.sub(r"[^\d]", "", parts[1].strip())
            if min_price and max_price:
                try:
                    min_val = int(min_price)
                    max_val = int(max_price)
                    return f"{min_val} - {max_val}"
                except ValueError:
                    pass

    cleaned = re.sub(r"[^\d]", "", text)
    return int(cleaned) if cleaned else None


def format_number(num):
    """Убирает .0 у float, оставляет int."""
    if num is None:
        return None
    if isinstance(num, float) and num.is_integer():
        return int(num)
    return num


def clean_address(address: str) -> str:
    """Удаляет хвост 'На карте' из адреса."""
    if not address:
        return ""
    address = re.sub(r"\s*На карте.*$", "", address, flags=re.IGNORECASE)
    return address.strip()


def load_existing_links():
    """Считывает уже сохранённые ссылки из файла."""
    if not os.path.exists(OUTPUT_FILE):
        return set()

    try:
        df = pd.read_csv(OUTPUT_FILE, encoding="utf-8-sig")
        if "Ссылка" in df.columns:
            links = set(df["Ссылка"].dropna().astype(str))
            print(f"\n✓ Найден существующий файл: {OUTPUT_FILE}")
            print(f"✓ Уже сохранено объявлений: {len(links)}")
            return links
    except Exception as e:
        print(f"\n⚠ Не удалось прочитать существующий файл {OUTPUT_FILE}: {e}")
    return set()


def append_rows_to_csv(rows):
    """Дозаписывает строки в CSV."""
    if not rows:
        return

    df = pd.DataFrame(rows)
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = None

    df = df[COLUMNS]

    numeric_cols = ["Площадь", "Этаж", "Этажей в доме"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = df[col].apply(format_number)

    if "Цена" in df.columns:
        def format_price(val):
            if isinstance(val, str) and (" - " in val or "–" in val):
                return val
            return format_number(val)
        df["Цена"] = df["Цена"].apply(format_price)

    mode = "a" if os.path.exists(OUTPUT_FILE) else "w"
    header = mode == "w"
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig", mode=mode, header=header)
    print(f"\n✓ Сохранено пачкой {len(df)} объявлений в файл {OUTPUT_FILE}")


# ================== СБОР ССЫЛОК ==================

def collect_cian_links(driver, region_id, mode="full", max_pages=None):
    """Собирает ссылки на объявления по региону."""
    print(f"\n--- СБОР ССЫЛОК С ЦИАН ---")
    print(f"Регион (region): {region_id}")
    all_links = set()
    page = 1

    while True:
        if mode == "test" and max_pages is not None and page > max_pages:
            print(f"\n✓ Достигнут лимит страниц тестового режима: {max_pages}")
            break

        page_url = build_search_page_url(region_id, page)
        print(f"\nСтраница {page}: {page_url}")
        driver.get(page_url)

        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "article, body"))
            )
        except TimeoutException:
            print(" ⚠ Таймаут при загрузке страницы, прекращаем сбор ссылок.")
            break

        time.sleep(0.3)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(0.2)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(0.1)

        page_links = set()

        try:
            # Ищем ссылки на объявления с динамической переменной
            all_links_on_page = driver.find_elements(
                By.XPATH, f"//a[contains(@href, '/{SALE}/commercial/')]"
            )
            for a in all_links_on_page:
                try:
                    href = a.get_attribute("href")
                    if href:
                        m = re.search(rf"/{SALE}/commercial/(\d+)", href)
                        if m:
                            office_id = m.group(1)
                            page_links.add(f"https://cian.ru/{SALE}/commercial/{office_id}/")
                except (StaleElementReferenceException, AttributeError):
                    continue
        except Exception as e:
            print(f" ⚠ Ошибка при поиске ссылок: {e}")

        # Резервный поиск
        try:
            cards = driver.find_elements(By.CSS_SELECTOR, f"article a[href*='/{SALE}/commercial/']")
            for a in cards:
                try:
                    href = a.get_attribute("href")
                    if href:
                        m = re.search(rf"/{SALE}/commercial/(\d+)", href)
                        if m:
                            office_id = m.group(1)
                            page_links.add(f"https://cian.ru/{SALE}/commercial/{office_id}/")
                except (StaleElementReferenceException, AttributeError):
                    continue
        except Exception:
            pass

        if not page_links:
            print(" ⚠ На странице не найдено объявлений.")
            try:
                page_title = driver.title
                print(f" Заголовок страницы: {page_title}")
                page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
                if "робот" in page_text or "captcha" in page_text or "подтвердите" in page_text:
                    print(" ⚠ Возможно, появилась CAPTCHA или блокировка!")
            except Exception:
                pass
            break

        new_links = page_links - all_links
        all_links.update(page_links)
        print(f" ✓ Найдено на странице: {len(page_links)} (новых: {len(new_links)}) | Всего: {len(all_links)}")

        if len(new_links) == 0:
            print(" ⚠ Новых ссылок нет, прекращаем.")
            break

        page += 1
        time.sleep(random.uniform(0.3, 0.7))

    return sorted(all_links)


# ================== ПАРСИНГ СТРАНИЦ ==================

def validate_phone_number(phone):
    """Проверяет и нормализует номер телефона."""
    if not phone or not isinstance(phone, str):
        return None

    phone_clean = phone.strip()
    if not phone_clean:
        return None

    digits_only = re.sub(r"[^\d]", "", phone_clean)
    plus_count = phone_clean.count("+")

    # 10-11 цифр (российский номер)
    if len(digits_only) < 10 or len(digits_only) > 11:
        return None

    if plus_count > 1:
        return None

    if plus_count == 1 and not phone_clean.startswith("+"):
        return None

    if phone_clean.startswith("+7") or (plus_count == 0 and digits_only.startswith("7") and len(digits_only) == 11):
        if len(digits_only) != 11 or not digits_only.startswith("7"):
            return None
        return "+7" + digits_only[1:]

    elif phone_clean.startswith("8") or (plus_count == 0 and digits_only.startswith("8") and len(digits_only) == 11):
        if len(digits_only) != 11:
            return None
        return "+7" + digits_only[1:]

    elif len(digits_only) == 10:
        first_digit = digits_only[0]
        if first_digit in ["9", "3", "4", "5", "8"]:
            return "+7" + digits_only
        return None

    return None


def extract_phone_number(driver):
    """Получение телефона: кликает кнопку и парсит номер из модального окна."""
    try:
        phone_button = None

        # Ищем кнопку "Показать телефон"
        button_selectors = [
            "//button[contains(text(), 'Показать телефон')]",
            "//*[contains(text(), 'Показать телефон')]",
            "//button[contains(@class, 'phone')]",
            "[data-testid*='phone']",
            "button[class*='phone']",
            "button[class*='Phone']",
        ]

        for selector in button_selectors:
            try:
                if selector.startswith("//"):
                    elements = driver.find_elements(By.XPATH, selector)
                else:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)

                for elem in elements:
                    try:
                        if elem.is_displayed() and elem.is_enabled():
                            phone_button = elem
                            break
                    except:
                        continue

                if phone_button:
                    break
            except:
                continue

        if not phone_button:
            print(" ⚠ Кнопка 'Показать телефон' не найдена")
            return None

        # === КРИТИЧЕСКАЯ ЧАСТЬ: ПРАВИЛЬНЫЙ КЛИК ===
        try:
            # Скролим к кнопке
            driver.execute_script("arguments[0].scrollIntoView(true);", phone_button)
            time.sleep(0.3)

            # Кликаем JavaScript-ом (более надежно)
            driver.execute_script("arguments[0].click();", phone_button)
            print(" ✓ Клик выполнен")

        except Exception as click_error:
            print(f" ⚠ Ошибка при клике: {click_error}")
            try:
                # Резервный способ - обычный click()
                phone_button.click()
            except:
                return None

        # === ОЖИДАЕМ МОДАЛЬНОЕ ОКНО ===
        time.sleep(0.5)  # Начальная задержка для открытия

        try:
            # Ждем модального окна с текстом (более специфичный селектор)
            WebDriverWait(driver, 4).until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, "div[role='dialog'], div[class*='modal'], div[class*='Modal']"))
            )
            print(" ✓ Модальное окно открыто")
        except:
            print(" ⚠ Модальное окно не открыло в срок")
            pass

        time.sleep(0.8)  # Дополнительная задержка для полной загрузки модального окна

        # === ПАТТЕРНЫ ДЛЯ ПОИСКА НОМЕРА ===
        phone_patterns = [
            r"\+7[\s\-\(\)]*\d[\s\-\(\)]*\d[\s\-\(\)]*\d[\s\-\(\)]*\d[\s\-\(\)]*\d[\s\-\(\)]*\d[\s\-\(\)]*\d[\s\-\(\)]*\d[\s\-\(\)]*\d[\s\-\(\)]*\d",
            r"8[\s\-\(\)]*\d[\s\-\(\)]*\d[\s\-\(\)]*\d[\s\-\(\)]*\d[\s\-\(\)]*\d[\s\-\(\)]*\d[\s\-\(\)]*\d[\s\-\(\)]*\d[\s\-\(\)]*\d[\s\-\(\)]*\d",
            r"\+?7[\s\-\(\)]*\d{3}[\s\-\(\)]*\d{3}[\s\-\(\)]*\d{2}[\s\-\(\)]*\d{2}",
            r"\+7\s*\d{3}\s*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}",
        ]

        # === СПОСОБ 1: МОДАЛЬНОЕ ОКНО ===
        modal_selectors = [
            "div[role='dialog']",
            "div[class*='modal']",
            "div[class*='Modal']",
            "div[class*='popup']",
            "div[class*='Popup']",
        ]

        for sel in modal_selectors:
            try:
                modals = driver.find_elements(By.CSS_SELECTOR, sel)
                for modal in modals:
                    try:
                        if not modal.is_displayed():
                            continue

                        modal_text = modal.text or modal.get_attribute("textContent") or ""

                        if not modal_text:
                            continue

                        for pattern in phone_patterns:
                            phone_match = re.search(pattern, modal_text)
                            if phone_match:
                                phone_raw = phone_match.group(0)
                                phone = validate_phone_number(phone_raw)
                                if phone:
                                    print(f" ✓ Номер найден в модальном окне: {phone}")
                                    return phone

                    except:
                        continue
            except:
                continue

        # === СПОСОБ 2: TEL-ССЫЛКИ ===
        try:
            tel_links = driver.find_elements(By.CSS_SELECTOR, "a[href^='tel:']")
            for link in tel_links:
                try:
                    href = link.get_attribute("href")
                    if href:
                        phone_text = href.split("tel:")[-1].split("?")[0]
                        phone = validate_phone_number(phone_text)
                        if phone:
                            print(f" ✓ Номер найден в tel-ссылке: {phone}")
                            return phone
                except:
                    continue
        except:
            pass

        # === СПОСОБ 3: ВЕСЬ ТЕКСТ СТРАНИЦЫ (FALLBACK) ===
        try:
            page_text = driver.find_element(By.TAG_NAME, "body").text
            for pattern in phone_patterns:
                phone_match = re.search(pattern, page_text)
                if phone_match:
                    phone_raw = phone_match.group(0)
                    phone = validate_phone_number(phone_raw)
                    if phone:
                        print(f" ✓ Номер найден на странице: {phone}")
                        return phone
        except:
            pass

        print(" ⚠ Номер телефона не найден")
        return None

    except Exception as e:
        print(f" ✗ Ошибка при извлечении номера: {e}")
        return None


def _extract_float_from_text(text):
    """Извлекает float из текста."""
    if not text:
        return None
    m = re.search(r"(\d+[.,]?\d*)", text)
    if not m:
        return None
    s = m.group(1).replace(",", ".").replace(" ", "").replace("\xa0", "")
    try:
        return float(s)
    except Exception:
        return None


def parse_cian_page(driver, url, idx, total):
    """Парсит одну детальную страницу объявления ЦИАН."""
    try:
        print(f"\n[{idx}/{total}] ЦИАН: {url}")
        driver.get(url)

        try:
            WebDriverWait(driver, 12).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
            )
        except TimeoutException:
            print(" ⚠ Таймаут при загрузке объявления")
            return None

        time.sleep(0.4)

        data = {
            "Ссылка": url,
            "Адрес": "",
            "Цена": None,
            "Тип помещения": "",
            "Площадь": None,
            "Этаж": None,
            "Этажей в доме": None,
            "Телефон": None,
        }

        # Используем адаптивные селекторы для текущего типа сделки
        price_selectors = get_selectors('price')
        price_text = safe_find_texts(driver, price_selectors)
        if price_text:
            data["Цена"] = extract_price(price_text)

        # Адрес — адаптивные селекторы
        address_selectors = get_selectors('address')
        address = safe_find_texts(driver, address_selectors)
        if address:
            data["Адрес"] = clean_address(address)

        # Заголовок — адаптивные селекторы
        title_selectors = get_selectors('title')
        title_text = safe_find_texts(driver, title_selectors)
        if title_text:
            title_lower = title_text.lower()
            data["Тип помещения"] = "Офис" if "офис" in title_lower else "Свобод. назнач."
        else:
            data["Тип помещения"] = "Свобод. назнач."

        # Площадь и этаж — резервные методы (работают универсально)
        total_area = None
        floor_cur = None
        floor_total = None

        try:
            el = driver.find_element(
                By.XPATH,
                "//*[contains(text(),'Площадь')]/ancestor::*[self::div or self::li or self::span][1]",
            )
            area_text = el.text
            m = re.search(r"([\d\s]+[.,]?\d*)\s*м²", area_text)
            if m:
                number_str = m.group(1).replace(" ", "").replace(" ", "")
                v = _extract_float_from_text(number_str)
                if v:
                    total_area = format_number(v)
        except Exception:
            pass

        try:
            el = driver.find_element(
                By.XPATH,
                "//*[contains(text(),'Этаж')]/ancestor::*[self::div or self::li][1]",
            )
            m = re.search(r"(-?\d+)\s*из\s*(\d+)", el.text)
            if m:
                c = int(m.group(1))
                t = int(m.group(2))
                floor_cur, floor_total = c, t
        except Exception:
            pass

        # Полный текст страницы (резервный источник)
        try:
            page_text = driver.find_element(By.TAG_NAME, "body").text
        except Exception:
            page_text = ""

        # Площадь — резервный поиск
        if total_area is None:
            m = re.search(r"Площадь[:\s]*([\d\s]+[.,]?\d*)\s*м²", page_text, re.IGNORECASE)
            if not m:
                m = re.search(r"([\d\s]+[.,]?\d*)\s*м²", page_text)
            if m:
                number_str = (m.group(1) if m.lastindex else m.group(0)).replace(" ", "").replace(" ", "")
                v = _extract_float_from_text(number_str)
                if v:
                    total_area = format_number(v)

        data["Площадь"] = total_area

        # Этаж — резервный поиск
        if floor_cur is None or floor_total is None:
            m = re.search(r"Этаж\s+(-?\d+)\s+из\s+(\d+)", page_text, re.IGNORECASE)
            if m:
                try:
                    c = int(m.group(1))
                    t = int(m.group(2))
                    floor_cur, floor_total = c, t
                except Exception:
                    pass

        data["Этаж"] = floor_cur
        data["Этажей в доме"] = floor_total

        # Телефон
        phone_result = extract_phone_number(driver)
        data["Телефон"] = phone_result if phone_result else None

        time.sleep(random.uniform(0.3, 0.6))
        return data

    except Exception as e:
        print(f" ✗ Ошибка при парсинге страницы: {e}")
        return None


# ================== ОСНОВНАЯ ЛОГИКА ==================

def main():
    driver = None
    try:
        print("=" * 60)
        print("ПАРСЕР ОБЪЯВЛЕНИЙ ОФИСОВ (ПРОДАЖА & АРЕНДА)")
        print("ЦИАН (cat.php, region, p)")
        print("=" * 60)

        mode, test_pages, city_info = resolve_settings()
        region_id = city_info["region"]

        print(f"\nАвторежим: {mode.upper()}, город: {city_info['name']}, тип сделки: {SALE}")
        print(f"Страниц (для test): {test_pages or 'все'}")

        existing_links = load_existing_links()

        print("\nЗапуск браузера для сбора ссылок...")
        driver = get_driver()

        print("\n" + "=" * 60)
        print("СБОР ССЫЛОК НА ОБЪЯВЛЕНИЯ (ЦИАН)")
        print("=" * 60)

        all_links = collect_cian_links(
            driver,
            region_id=region_id,
            mode=mode,
            max_pages=test_pages,
        )

        if not all_links:
            print("\n✗ Ссылки не найдены, работа завершена.")
            return

        links_to_parse = [u for u in all_links if u not in existing_links]

        print(f"\nВсего найдено ссылок: {len(all_links)}")
        print(f"Из них новых (ещё нет в таблице): {len(links_to_parse)}")

        if not links_to_parse:
            print("\n✓ Новых объявлений нет, всё уже в таблице.")
            return

        print("\n" + "=" * 60)
        print("ПАРСИНГ ДЕТАЛЬНЫХ СТРАНИЦ (ЦИАН)")
        print("=" * 60)

        total = len(links_to_parse)
        rows_to_save = []
        total_parsed = 0

        for idx, url in enumerate(links_to_parse, 1):
            row = parse_cian_page(driver, url, idx, total)
            if row:
                rows_to_save.append(row)

            # Сохраняем каждые 10 объявлений
            if len(rows_to_save) >= 10:
                append_rows_to_csv(rows_to_save)
                total_parsed += len(rows_to_save)
                rows_to_save = []

        # Сохраняем оставшиеся
        if rows_to_save:
            append_rows_to_csv(rows_to_save)
            total_parsed += len(rows_to_save)

        print(f"\n{'=' * 60}")
        print("✓ ПАРСИНГ ЗАВЕРШЁН")
        print(f"✓ Всего новых объявлений сохранено: {total_parsed}")
        print(f"✓ Файл с данными: {OUTPUT_FILE}")
        print(f"{'=' * 60}")

    except KeyboardInterrupt:
        print("\n\n⚠ Парсинг прерван пользователем")
    except Exception as e:
        print(f"\n✗ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if driver:
            print("\nЗакрываем браузер...")
            driver.quit()
        print("Готово!")


if __name__ == "__main__":
    main()
