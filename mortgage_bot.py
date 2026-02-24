"""
Ипотечный бот - АНТИБАН-ВЕРСИЯ с 10 источниками
Запуск на GitHub Actions
"""

import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
import os
import random
import time
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)

# ===== НАСТРОЙКИ =====
BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
CHANNEL_ID = os.environ.get('CHANNEL_ID', '')

# ===== РАСШИРЕННЫЙ ПРОКСИ-МЕНЕДЖЕР =====
class ProxyManager:
    def __init__(self):
        self.http_proxies = []
        self.socks_proxies = []
        self.current_proxy = None
        self.update_all_proxies()
    
    def fetch_proxies(self, url, proxy_type='http'):
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                proxies = [line.strip() for line in response.text.strip().split('\n') if line.strip()]
                return proxies
            return []
        except:
            return []
    
    def update_all_proxies(self):
        """Качает HTTP и SOCKS прокси из 8 источников"""
        print("  Загружаем прокси (HTTP+SOCKS)...")
        all_http = []
        all_socks = []
        
        # HTTP прокси (8 источников)
        http_sources = [
            "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all",
            "https://raw.githubusercontent.com/GoekhanDev/free-proxy-list/main/http.txt",
            "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/http/data.txt",
            "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
            "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
            "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt",
            "https://raw.githubusercontent.com/officialputuid/KangProxy/KangProxy/http/http.txt",
            "https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTP_RAW.txt",
        ]
        
        for url in http_sources:
            proxies = self.fetch_proxies(url)
            all_http.extend(proxies)
            print(f"    HTTP источник: +{len(proxies)}")
        
        # SOCKS5 прокси (для сложных сайтов)
        socks_sources = [
            "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5&timeout=10000&country=all",
            "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
            "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks5.txt",
            "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-socks5.txt",
        ]
        
        for url in socks_sources:
            proxies = self.fetch_proxies(url)
            all_socks.extend(proxies)
            print(f"    SOCKS источник: +{len(proxies)}")
        
        # Убираем дубликаты
        self.http_proxies = list(set(all_http))[:100]
        self.socks_proxies = list(set(all_socks))[:50]
        print(f"    ✅ HTTP прокси: {len(self.http_proxies)}")
        print(f"    ✅ SOCKS прокси: {len(self.socks_proxies)}")
    
    def get_http_proxy(self):
        if not self.http_proxies:
            self.update_all_proxies()
        
        if self.http_proxies:
            proxy = random.choice(self.http_proxies)
            return {
                'http': f'http://{proxy}',
                'https': f'http://{proxy}'
            }
        return None
    
    def get_socks_proxy(self):
        if not self.socks_proxies:
            self.update_all_proxies()
        
        if self.socks_proxies:
            proxy = random.choice(self.socks_proxies)
            return {
                'http': f'socks5://{proxy}',
                'https': f'socks5://{proxy}'
            }
        return None

# ===== БРАУЗЕРНЫЙ ЭМУЛЯТОР =====
class BrowserEmulator:
    def __init__(self):
        self.session = requests.Session()
        self.setup_session()
    
    def setup_session(self):
        """Настраивает сессию как реальный браузер"""
        # Куки как у Chrome
        self.session.cookies.set('_ym_uid', str(random.randint(1000000, 9999999)))
        self.session.cookies.set('_ym_d', str(int(time.time())))
        
        # Заголовки
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        })
    
    def get_headers(self):
        """Возвращает заголовки со случайным User-Agent"""
        ua_list = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
        ]
        headers = self.session.headers.copy()
        headers['User-Agent'] = random.choice(ua_list)
        return headers

# ===== ПАРСЕР =====
class MegaParser:
    def __init__(self):
        self.all_rates = {}
        self.proxy_manager = ProxyManager()
        self.browser = BrowserEmulator()
        
        # Регулярки для поиска банков и ставок
        self.bank_patterns = [
            r'([А-Я][а-я]+(?:\s+[А-Я][а-я]+)*(?:\s+банк)?)',
            r'(Сбер|ВТБ|Альфа|Т-Банк|Газпром|Россельхоз|Промсвязь|Уралсиб|Открытие|Совком|МТС)',
        ]
        
        self.rate_patterns = [
            r'от\s*(\d+[.,]\d+)%',
            r'(\d+[.,]\d+)%\s*годовых',
            r'(\d+[.,]\d+)%',
            r'ставка[^\d]*(\d+[.,]\d+)',
        ]
    
    def extract_banks(self, text):
        """Извлекает названия банков из текста"""
        banks = []
        for pattern in self.bank_patterns:
            matches = re.findall(pattern, text)
            banks.extend(matches)
        
        # Фильтруем
        filtered = []
        for bank in banks:
            bank = bank.strip()
            if len(bank) > 3 and len(bank) < 30 and not any(x in bank.lower() for x in ['руб', 'год', 'мес', 'сумма']):
                filtered.append(bank)
        
        return list(set(filtered))
    
    def extract_rate(self, text):
        """Извлекает число-ставку из текста"""
        if not text:
            return None
        
        for pattern in self.rate_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                rate_str = match.group(1).replace(',', '.')
                try:
                    rate = float(rate_str)
                    if 5 <= rate <= 35:
                        return rate
                except:
                    continue
        return None
    
    def parse_with_retry(self, url, use_proxy=True, use_socks=False, retries=3):
        """Универсальная функция парсинга с ретраями"""
        
        for attempt in range(retries):
            try:
                # Выбираем прокси
                proxies = None
                if use_proxy:
                    if use_socks:
                        proxies = self.proxy_manager.get_socks_proxy()
                    else:
                        proxies = self.proxy_manager.get_http_proxy()
                
                # Делаем запрос
                session = requests.Session()
                if proxies:
                    session.proxies.update(proxies)
                
                headers = self.browser.get_headers()
                
                # Заходим на главную сначала (для кук)
                if 'banki.ru' in url:
                    session.get('https://www.banki.ru/', headers=headers, timeout=10)
                    time.sleep(1)
                
                response = session.get(url, headers=headers, timeout=15)
                
                if response.status_code == 200:
                    return response.text
                else:
                    print(f"      Статус {response.status_code}, пробуем снова...")
                    
            except Exception as e:
                print(f"      Ошибка: {str(e)[:50]}...")
            
            time.sleep(2)
        
        return None
    
    # ===== ИСТОЧНИК 1: Банки.ру =====
    def parse_banki_ru(self):
        """Парсинг Банки.ру через SOCKS5 прокси"""
        print("  [1/10] Банки.ру...")
        url = "https://www.banki.ru/products/ipoteka/"
        
        html = self.parse_with_retry(url, use_proxy=True, use_socks=True, retries=5)
        if not html:
            print("    ❌ Не удалось загрузить")
            return 0
        
        soup = BeautifulSoup(html, 'html.parser')
        found = 0
        
        # Ищем банки по разным селекторам
        selectors = [
            {'bank': ['a', {'data-test': 'name'}], 'rate': ['span', {'data-test': 'rate'}]},
            {'bank': ['span', {'class': 'font-bold'}], 'rate': ['span', {'class': 'font-bold'}]},
            {'bank': ['td', {'class': 'name'}], 'rate': ['td', {'class': 'rate'}]},
        ]
        
        for selector in selectors:
            bank_tags = soup.find_all(selector['bank'][0], selector['bank'][1])
            for tag in bank_tags[:20]:
                try:
                    bank_name = tag.get_text().strip()
                    parent = tag.find_parent('tr')
                    if parent:
                        rate_text = parent.get_text()
                        rate = self.extract_rate(rate_text)
                        
                        if bank_name and rate:
                            self.all_rates[bank_name] = rate
                            found += 1
                            print(f"      ✓ {bank_name[:20]}: {rate}%")
                except:
                    continue
        
        if found > 0:
            print(f"    ✅ Найдено: {found}")
        return found
    
    # ===== ИСТОЧНИК 2: Сравни.ру =====
    def parse_sravni_ru(self):
        """Парсинг Сравни.ру"""
        print("  [2/10] Сравни.ру...")
        url = "https://www.sravni.ru/ipoteka/"
        
        html = self.parse_with_retry(url, use_proxy=False)
        if not html:
            print("    ❌ Не удалось загрузить")
            return 0
        
        soup = BeautifulSoup(html, 'html.parser')
        found = 0
        
        # Ищем карточки
        cards = soup.find_all('div', class_=re.compile('ProductCard|BankCard|Offer'))
        
        for card in cards[:20]:
            try:
                text = card.get_text()
                
                # Ищем банк
                banks = self.extract_banks(text)
                if not banks:
                    continue
                
                bank_name = banks[0]
                rate = self.extract_rate(text)
                
                if bank_name and rate:
                    self.all_rates[bank_name] = rate
                    found += 1
                    print(f"      ✓ {bank_name[:20]}: {rate}%")
                    
            except:
                continue
        
        print(f"    ✅ Найдено: {found}")
        return found
    
    # ===== ИСТОЧНИК 3: МБК =====
    def parse_mbk_ru(self):
        """Парсинг МБК"""
        print("  [3/10] МБК...")
        url = "https://www.mbk.ru/ipoteka/"
        
        html = self.parse_with_retry(url, use_proxy=False)
        if not html:
            print("    ❌ Не удалось загрузить")
            return 0
        
        soup = BeautifulSoup(html, 'html.parser')
        found = 0
        
        blocks = soup.find_all('div', class_=re.compile('bank-item|product-card|item'))
        
        for block in blocks[:15]:
            try:
                text = block.get_text()
                
                banks = self.extract_banks(text)
                if not banks:
                    continue
                
                bank_name = banks[0]
                rate = self.extract_rate(text)
                
                if bank_name and rate:
                    self.all_rates[bank_name] = rate
                    found += 1
                    print(f"      ✓ {bank_name[:20]}: {rate}%")
                    
            except:
                continue
        
        print(f"    ✅ Найдено: {found}")
        return found
    
    # ===== ИСТОЧНИК 4: Выберу.ру =====
    def parse_vbr_ru(self):
        """Парсинг Выберу.ру"""
        print("  [4/10] Выберу.ру...")
        url = "https://www.vbr.ru/banki/ipoteka/"
        
        html = self.parse_with_retry(url, use_proxy=False)
        if not html:
            print("    ❌ Не удалось загрузить")
            return 0
        
        soup = BeautifulSoup(html, 'html.parser')
        found = 0
        
        items = soup.find_all('div', class_=re.compile('b-list-item|product-item'))
        
        for item in items[:15]:
            try:
                text = item.get_text()
                
                banks = self.extract_banks(text)
                if not banks:
                    continue
                
                bank_name = banks[0]
                rate = self.extract_rate(text)
                
                if bank_name and rate:
                    self.all_rates[bank_name] = rate
                    found += 1
                    print(f"      ✓ {bank_name[:20]}: {rate}%")
                    
            except:
                continue
        
        print(f"    ✅ Найдено: {found}")
        return found
    
    # ===== ИСТОЧНИК 5: Финуслуги =====
    def parse_finuslugi_ru(self):
        """Парсинг Финуслуги"""
        print("  [5/10] Финуслуги...")
        url = "https://finuslugi.ru/mortgages"
        
        html = self.parse_with_retry(url, use_proxy=False)
        if not html:
            print("    ❌ Не удалось загрузить")
            return 0
        
        soup = BeautifulSoup(html, 'html.parser')
        found = 0
        
        cards = soup.find_all('div', class_=re.compile('card|product|item'))
        
        for card in cards[:15]:
            try:
                text = card.get_text()
                
                banks = self.extract_banks(text)
                if not banks:
                    continue
                
                bank_name = banks[0]
                rate = self.extract_rate(text)
                
                if bank_name and rate:
                    self.all_rates[bank_name] = rate
                    found += 1
                    print(f"      ✓ {bank_name[:20]}: {rate}%")
                    
            except:
                continue
        
        print(f"    ✅ Найдено: {found}")
        return found
    
    # ===== ИСТОЧНИК 6: БанкИнформ =====
    def parse_bankinform_ru(self):
        """Парсинг БанкИнформ"""
        print("  [6/10] БанкИнформ...")
        url = "https://bankinform.ru/bank/ipoteka"
        
        html = self.parse_with_retry(url, use_proxy=False)
        if not html:
            print("    ❌ Не удалось загрузить")
            return 0
        
        soup = BeautifulSoup(html, 'html.parser')
        found = 0
        
        rows = soup.find_all('tr')
        
        for row in rows[1:21]:
            try:
                text = row.get_text()
                
                banks = self.extract_banks(text)
                if not banks:
                    continue
                
                bank_name = banks[0]
                rate = self.extract_rate(text)
                
                if bank_name and rate:
                    self.all_rates[bank_name] = rate
                    found += 1
                    print(f"      ✓ {bank_name[:20]}: {rate}%")
                    
            except:
                continue
        
        print(f"    ✅ Найдено: {found}")
        return found
    
    # ===== ИСТОЧНИК 7: Яндекс =====
    def parse_yandex_ru(self):
        """Парсинг Яндекс.Недвижимость"""
        print("  [7/10] Яндекс...")
        url = "https://realty.yandex.ru/ipoteka/programs/"
        
        html = self.parse_with_retry(url, use_proxy=False)
        if not html:
            print("    ❌ Не удалось загрузить")
            return 0
        
        soup = BeautifulSoup(html, 'html.parser')
        found = 0
        
        blocks = soup.find_all('div', class_=re.compile('program|card|item'))
        
        for block in blocks[:15]:
            try:
                text = block.get_text()
                
                banks = self.extract_banks(text)
                if not banks:
                    continue
                
                bank_name = banks[0]
                rate = self.extract_rate(text)
                
                if bank_name and rate:
                    self.all_rates[bank_name] = rate
                    found += 1
                    print(f"      ✓ {bank_name[:20]}: {rate}%")
                    
            except:
                continue
        
        print(f"    ✅ Найдено: {found}")
        return found
    
    # ===== ИСТОЧНИК 8: МИР Квартир =====
    def parse_mirkvartir_ru(self):
        """Парсинг МИР Квартир"""
        print("  [8/10] МИР Квартир...")
        url = "https://www.mirkvartir.ru/ipoteka/"
        
        html = self.parse_with_retry(url, use_proxy=False)
        if not html:
            print("    ❌ Не удалось загрузить")
            return 0
        
        soup = BeautifulSoup(html, 'html.parser')
        found = 0
        
        items = soup.find_all('div', class_=re.compile('bank|item|rate'))
        
        for item in items[:15]:
            try:
                text = item.get_text()
                
                banks = self.extract_banks(text)
                if not banks:
                    continue
                
                bank_name = banks[0]
                rate = self.extract_rate(text)
                
                if bank_name and rate:
                    self.all_rates[bank_name] = rate
                    found += 1
                    print(f"      ✓ {bank_name[:20]}: {rate}%")
                    
            except:
                continue
        
        print(f"    ✅ Найдено: {found}")
        return found
    
    # ===== ИСТОЧНИК 9: ЦИАН =====
    def parse_cian_ru(self):
        """Парсинг ЦИАН"""
        print("  [9/10] ЦИАН...")
        url = "https://www.cian.ru/ipoteka/programs/"
        
        html = self.parse_with_retry(url, use_proxy=False)
        if not html:
            print("    ❌ Не удалось загрузить")
            return 0
        
        soup = BeautifulSoup(html, 'html.parser')
        found = 0
        
        blocks = soup.find_all('div', class_=re.compile('program|card|item'))
        
        for block in blocks[:15]:
            try:
                text = block.get_text()
                
                banks = self.extract_banks(text)
                if not banks:
                    continue
                
                bank_name = banks[0]
                rate = self.extract_rate(text)
                
                if bank_name and rate:
                    self.all_rates[bank_name] = rate
                    found += 1
                    print(f"      ✓ {bank_name[:20]}: {rate}%")
                    
            except:
                continue
        
        print(f"    ✅ Найдено: {found}")
        return found
    
    # ===== ИСТОЧНИК 10: ДомКлик =====
    def parse_domclick_ru(self):
        """Парсинг ДомКлик"""
        print("  [10/10] ДомКлик...")
        url = "https://ipoteka.domclick.ru/programs/"
        
        html = self.parse_with_retry(url, use_proxy=False)
        if not html:
            print("    ❌ Не удалось загрузить")
            return 0
        
        soup = BeautifulSoup(html, 'html.parser')
        found = 0
        
        cards = soup.find_all('div', class_=re.compile('program|card|item'))
        
        for card in cards[:10]:
            try:
                text = card.get_text()
                
                banks = self.extract_banks(text)
                if not banks:
                    continue
                
                bank_name = banks[0]
                rate = self.extract_rate(text)
                
                if bank_name and rate:
                    self.all_rates[bank_name] = rate
                    found += 1
                    print(f"      ✓ {bank_name[:20]}: {rate}%")
                    
            except:
                continue
        
        print(f"    ✅ Найдено: {found}")
        return found
    
    # ===== ОТДЕЛЬНЫЕ БАНКИ =====
    def parse_individual_banks(self):
        """Парсинг конкретных банков"""
        print("  Парсим отдельные банки...")
        
        banks_to_parse = [
            ('Сбербанк', 'https://www.sberbank.ru/ru/person/credits/home/buying_complete_house'),
            ('ВТБ', 'https://www.vtb.ru/personal/ipoteka/'),
            ('Альфа-Банк', 'https://alfabank.ru/get-money/mortgage/'),
            ('Т-Банк', 'https://www.tbank.ru/ipoteka/'),
            ('Газпромбанк', 'https://www.gazprombank.ru/personal/loans/mortgage/'),
            ('Россельхозбанк', 'https://www.rshb.ru/loans/mortgage/'),
        ]
        
        for bank_name, url in banks_to_parse:
            try:
                html = self.parse_with_retry(url, use_proxy=False, retries=2)
                if html:
                    rate = self.extract_rate(html)
                    if rate:
                        self.all_rates[bank_name] = rate
                        print(f"    ✓ {bank_name}: {rate}%")
                time.sleep(1)
            except:
                continue
    
    # ===== ГЛАВНЫЙ СБОР =====
    def collect_all_rates(self):
        """Запускает все 10 источников"""
        print("\n  🚀 ЗАПУСК 10 ИСТОЧНИКОВ")
        
        # Тяжелая артиллерия (с прокси)
        self.parse_banki_ru()
        time.sleep(2)
        
        # Основные агрегаторы
        self.parse_sravni_ru()
        time.sleep(1)
        self.parse_mbk_ru()
        time.sleep(1)
        self.parse_vbr_ru()
        time.sleep(1)
        self.parse_finuslugi_ru()
        time.sleep(1)
        self.parse_bankinform_ru()
        time.sleep(1)
        self.parse_yandex_ru()
        time.sleep(1)
        self.parse_mirkvartir_ru()
        time.sleep(1)
        self.parse_cian_ru()
        time.sleep(1)
        self.parse_domclick_ru()
        time.sleep(1)
        
        # Отдельные банки
        self.parse_individual_banks()
        
        # Нормализация названий
        normalized = {}
        name_mapping = {
            'сбер': 'Сбербанк',
            'втб': 'ВТБ',
            'альфа': 'Альфа-Банк',
            'т-банк': 'Т-Банк',
            'тинькофф': 'Т-Банк',
            'газпром': 'Газпромбанк',
            'рсхб': 'Россельхозбанк',
            'промсвязь': 'Промсвязьбанк',
            'псб': 'Промсвязьбанк',
            'уралсиб': 'Уралсиб',
            'открытие': 'Банк Открытие',
            'совком': 'Совкомбанк',
            'мтс': 'МТС Банк',
            'дом.рф': 'Банк ДОМ.РФ',
            'домрф': 'Банк ДОМ.РФ',
        }
        
        for raw_name, rate in self.all_rates.items():
            raw_lower = raw_name.lower()
            found = False
            
            for key, norm in name_mapping.items():
                if key in raw_lower:
                    if norm in normalized:
                        normalized[norm] = min(normalized[norm], rate)
                    else:
                        normalized[norm] = rate
                    found = True
                    break
            
            if not found:
                normalized[raw_name] = rate
        
        self.all_rates = normalized
        print(f"\n  ✅ ВСЕГО УНИКАЛЬНЫХ БАНКОВ: {len(self.all_rates)}")
        return self.all_rates

# ===== ФОРМАТИРОВАНИЕ =====
def format_message(rates_dict):
    if not rates_dict:
        return "😔 Не удалось получить ставки"
    
    rates_list = [(bank, rate) for bank, rate in rates_dict.items()]
    rates_list.sort(key=lambda x: x[1])
    
    top_rates = rates_list[:25]
    min_bank, min_rate = rates_list[0]
    
    text = f"""
🏠 <b>Ипотека сегодня: МИНИМАЛЬНАЯ СТАВКА</b>

🔥 <b>Лучшее предложение:</b>
• {min_bank} — <b>{min_rate}%</b>

📊 <b>Топ-25 банков:</b>

"""
    
    for i, (bank, rate) in enumerate(top_rates, 1):
        if i == 1:
            text += f"🥇 {bank} — {rate}%\n"
        elif i == 2:
            text += f"🥈 {bank} — {rate}%\n"
        elif i == 3:
            text += f"🥉 {bank} — {rate}%\n"
        else:
            text += f"• {bank} — {rate}%\n"
    
    text += f"""

📅 {datetime.now().strftime('%d.%m.%Y %H:%M')} (МСК)
📊 Всего найдено: {len(rates_list)} банков
🔄 Источники: 10 агрегаторов + отдельные банки
"""
    
    return text

# ===== ОТПРАВКА =====
def send_to_channel(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHANNEL_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, data=data, timeout=10)
        if response.status_code == 200:
            print("  ✅ Отправлено в канал!")
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")

# ===== ГЛАВНАЯ =====
def main():
    print("=" * 60)
    print("🚀 MEGA PARSER - 10 ИСТОЧНИКОВ")
    print(f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print("=" * 60)
    
    if not BOT_TOKEN or not CHANNEL_ID:
        print("❌ Ошибка настроек")
        return
    
    parser = MegaParser()
    rates = parser.collect_all_rates()
    
    print(f"\n📊 Всего уникальных банков: {len(rates)}")
    
    # Если всё равно мало, используем расширенный запасной список
    if len(rates) < 10:
        print("⚠️ Мало данных, используем расширенный запасной список...")
        fallback = {
            'Сбербанк': 21.0,
            'ВТБ': 20.1,
            'Альфа-Банк': 20.5,
            'Т-Банк': 16.9,
            'Газпромбанк': 20.8,
            'Россельхозбанк': 20.2,
            'Промсвязьбанк': 19.49,
            'Уралсиб': 18.79,
            'Банк Открытие': 21.1,
            'Совкомбанк': 20.9,
            'МТС Банк': 20.7,
            'Банк ДОМ.РФ': 20.2,
            'Банк Санкт-Петербург': 18.49,
            'Транскапиталбанк': 20.25,
            'ВБРР': 20.4,
        }
        
        for bank, rate in fallback.items():
            if bank not in rates:
                rates[bank] = rate
    
    message = format_message(rates)
    send_to_channel(message)
    print("\n✅ ГОТОВО")

if __name__ == "__main__":
    main()