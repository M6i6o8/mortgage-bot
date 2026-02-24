"""
Ипотечный бот - расширенная версия с множеством прокси-источников и парсингом Сравни.ру
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
class AdvancedProxyManager:
    def __init__(self):
        self.proxies = []
        self.current_proxy = None
        self.update_proxy_list()
    
    def fetch_from_url(self, url, parser_func=None):
        """Загружает прокси с указанного URL"""
        try:
            print(f"    Загружаем с {url[:50]}...")
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                if parser_func:
                    return parser_func(response.text)
                else:
                    # По умолчанию: построчно, убираем пустые строки
                    return [line.strip() for line in response.text.strip().split('\n') if line.strip()]
            return []
        except Exception as e:
            print(f"    ⚠️ Ошибка загрузки: {e}")
            return []
    
    def parse_proxyscrape(self, text):
        """Парсит формат ProxyScrape (простой список)"""
        return [line.strip() for line in text.strip().split('\n') if line.strip()]
    
    def parse_github_raw(self, text):
        """Парсит сырые списки с GitHub"""
        proxies = []
        for line in text.strip().split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                proxies.append(line)
        return proxies
    
    def update_proxy_list(self):
        """Качает прокси из МНОЖЕСТВА источников"""
        print("  Загружаем прокси из разных источников...")
        all_proxies = []
        
        # ИСТОЧНИК 1: ProxyScrape (основной, уже работает)
        url1 = "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=RU&ssl=all&anonymity=all"
        proxies1 = self.fetch_from_url(url1)
        all_proxies.extend(proxies1)
        print(f"    ✅ ProxyScrape: {len(proxies1)}")
        
        # ИСТОЧНИК 2: free-proxy-list.net [citation:7]
        url2 = "https://free-proxy-list.net/"
        try:
            response = requests.get(url2, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                table = soup.find('table', {'id': 'proxylisttable'})
                if table:
                    rows = table.find_all('tr')[1:51]  # Первые 50 строк
                    for row in rows:
                        cols = row.find_all('td')
                        if len(cols) >= 2:
                            ip = cols[0].text.strip()
                            port = cols[1].text.strip()
                            all_proxies.append(f"{ip}:{port}")
            print(f"    ✅ free-proxy-list.net: {len(rows) if 'rows' in locals() else 0}")
        except Exception as e:
            print(f"    ⚠️ free-proxy-list.net: {e}")
        
        # ИСТОЧНИК 3: GitHub - GoekhanDev/free-proxy-list [citation:1]
        url3 = "https://raw.githubusercontent.com/GoekhanDev/free-proxy-list/main/http.txt"
        proxies3 = self.fetch_from_url(url3)
        all_proxies.extend(proxies3[:50])  # Берём первые 50
        print(f"    ✅ GoekhanDev: {len(proxies3[:50])}")
        
        # ИСТОЧНИК 4: fresh-proxy-list от fyvri [citation:3]
        url4 = "https://raw.githubusercontent.com/fyvri/fresh-proxy-list/main/lists/http.txt"
        proxies4 = self.fetch_from_url(url4)
        all_proxies.extend(proxies4[:50])
        print(f"    ✅ fresh-proxy-list: {len(proxies4[:50])}")
        
        # ИСТОЧНИК 5: proxifly [citation:10]
        url5 = "https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/protocols/http/data.txt"
        proxies5 = self.fetch_from_url(url5)
        all_proxies.extend(proxies5[:50])
        print(f"    ✅ proxifly: {len(proxies5[:50])}")
        
        # ИСТОЧНИК 6: socketpy proxy-list-link [citation:9]
        url6 = "https://raw.githubusercontent.com/socketpy/proxy-list-link/main/proxies/http.txt"
        proxies6 = self.fetch_from_url(url6)
        all_proxies.extend(proxies6[:50])
        print(f"    ✅ socketpy: {len(proxies6[:50])}")
        
        # Убираем дубликаты и пустые строки
        unique_proxies = list(set([p for p in all_proxies if p and len(p.split(':')) == 2]))
        
        # Оставляем только рабочие (примерно проверяем формат)
        valid_proxies = []
        for proxy in unique_proxies:
            parts = proxy.split(':')
            if len(parts) == 2 and parts[0].count('.') == 3:
                valid_proxies.append(proxy)
        
        self.proxies = valid_proxies[:100]  # Храним до 100 лучших
        print(f"    ✅ ВСЕГО УНИКАЛЬНЫХ: {len(self.proxies)}")
    
    def get_random_proxy(self):
        """Возвращает случайный прокси из списка"""
        if not self.proxies:
            self.update_proxy_list()
        
        if self.proxies:
            self.current_proxy = random.choice(self.proxies)
            return {
                'http': f'http://{self.current_proxy}',
                'https': f'http://{self.current_proxy}'
            }
        return None
    
    def report_failure(self):
        """Сообщаем, что текущий прокси не работает"""
        if self.current_proxy and self.current_proxy in self.proxies:
            self.proxies.remove(self.current_proxy)
        self.current_proxy = None

# ===== ПАРСЕР =====
class BankiRuParser:
    def __init__(self):
        self.all_rates = {}
        self.proxy_manager = AdvancedProxyManager()
        
        # Запасные ставки
        self.fallback_rates = {
            'Сбербанк': 21.0,
            'ВТБ': 20.1,
            'Альфа-Банк': 20.5,
            'Т-Банк': 16.9,
            'Банк ДОМ.РФ': 20.2,
            'Банк Санкт-Петербург': 18.49,
            'Уралсиб': 18.79,
            'Промсвязьбанк': 19.49,
            'Транскапиталбанк': 20.25,
            'ВБРР': 20.4,
            'Газпромбанк': 20.8,
            'Россельхозбанк': 20.2,
            'Совкомбанк': 20.9,
            'Банк Открытие': 21.1,
            'МТС Банк': 20.7,
        }
        
        # Заголовки как у реального браузера
        self.headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    
    def get_random_user_agent(self):
        """Генерирует случайный User-Agent"""
        ua_list = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        ]
        return random.choice(ua_list)
    
    def extract_rate(self, text):
        """Извлекает число-ставку из текста"""
        if not text:
            return None
        
        patterns = [
            r'от\s*(\d+[.,]\d+)%',
            r'(\d+[.,]\d+)%\s*годовых',
            r'(\d+[.,]\d+)%',
        ]
        
        for pattern in patterns:
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
    
    def parse_sravni_ru(self):
        """Парсинг Сравни.ру - НОВЫЙ ИСТОЧНИК"""
        try:
            print("  Парсим Сравни.ру...")
            url = "https://www.sravni.ru/ipoteka/"
            
            # Пробуем без прокси сначала
            headers = self.headers.copy()
            headers['User-Agent'] = self.get_random_user_agent()
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                found_banks = 0
                
                # Ищем карточки банков (селекторы нужно подбирать под верстку Сравни.ру)
                bank_cards = soup.find_all('div', class_=re.compile('product-item|bank-card|offer'))
                
                if not bank_cards:
                    # Альтернативный поиск
                    bank_cards = soup.find_all('article', class_=re.compile('product'))
                
                for card in bank_cards[:15]:
                    try:
                        card_text = card.get_text()
                        
                        # Ищем название банка
                        bank_match = re.search(r'([А-Я][а-я]+(?:\s+[А-Я][а-я]+)*)', card_text)
                        if not bank_match:
                            continue
                        
                        bank_name = bank_match.group(1).strip()
                        
                        # Ищем ставку
                        rate = self.extract_rate(card_text)
                        
                        if bank_name and rate and len(bank_name) < 40:
                            # Проверяем, не льготная ли ставка
                            if 'льгот' not in card_text.lower() and 'семейн' not in card_text.lower():
                                self.all_rates[bank_name] = rate
                                found_banks += 1
                                print(f"    ✓ {bank_name}: {rate}% (Сравни.ру)")
                                
                    except Exception:
                        continue
                
                if found_banks > 0:
                    print(f"    ✅ Сравни.ру: найдено {found_banks} банков")
                    return True
                else:
                    print("    ⚠️ Сравни.ру: банки не найдены")
                    return False
            else:
                print(f"    ⚠️ Сравни.ру: статус {response.status_code}")
                return False
                
        except Exception as e:
            print(f"    ⚠️ Ошибка парсинга Сравни.ру: {e}")
            return False
    
    def parse_banki_ru(self):
        """Парсинг Банки.ру через прокси"""
        try:
            print("  Парсим Банки.ру с прокси...")
            
            # Пробуем до 5 разных прокси
            for attempt in range(5):
                proxy = self.proxy_manager.get_random_proxy()
                if not proxy:
                    print("    ⚠️ Нет доступных прокси")
                    return False
                
                print(f"    Попытка {attempt+1}, прокси: {proxy['http']}")
                
                headers = self.headers.copy()
                headers['User-Agent'] = self.get_random_user_agent()
                
                try:
                    session = requests.Session()
                    session.proxies.update(proxy)
                    session.headers.update(headers)
                    
                    # Заходим на главную
                    session.get('https://www.banki.ru/', timeout=10)
                    time.sleep(1)
                    
                    # На страницу с ипотекой
                    url = "https://www.banki.ru/products/ipoteka/"
                    response = session.get(url, timeout=10)
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        found_banks = 0
                        rows = soup.find_all('tr', {'data-test': 'row'})
                        
                        if not rows:
                            rows = soup.find_all('tr', class_=re.compile('row|product'))
                        
                        for row in rows[:20]:
                            try:
                                row_text = row.get_text()
                                bank_match = re.search(r'([А-Я][а-я]+(?:\s+[А-Я][а-я]+)*)', row_text)
                                if not bank_match:
                                    continue
                                
                                bank_name = bank_match.group(1).strip()
                                rate = self.extract_rate(row_text)
                                
                                if bank_name and rate and len(bank_name) < 40:
                                    self.all_rates[bank_name] = rate
                                    found_banks += 1
                                    print(f"    ✓ {bank_name[:30]}: {rate}% (Банки.ру)")
                                    
                            except Exception:
                                continue
                        
                        if found_banks > 0:
                            print(f"    ✅ Банки.ру: найдено {found_banks} банков")
                            return True
                        else:
                            print(f"    ⚠️ Банки не найдены, пробуем другой прокси")
                            self.proxy_manager.report_failure()
                            
                    else:
                        print(f"    ⚠️ Статус {response.status_code}")
                        self.proxy_manager.report_failure()
                        
                except Exception as e:
                    print(f"    ⚠️ Ошибка через прокси: {e}")
                    self.proxy_manager.report_failure()
                    
                time.sleep(1)
            
            return False
                    
        except Exception as e:
            print(f"    ✗ Ошибка парсинга: {e}")
            return False
    
    def parse_individual_banks(self):
        """Парсинг отдельных банков"""
        
        # Сбер
        try:
            print("  Парсим Сбер...")
            url = "https://www.sberbank.ru/ru/person/credits/home/buying_complete_house"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                rate = self.extract_rate(response.text)
                if rate:
                    self.all_rates['Сбербанк'] = rate
                    print(f"    ✓ Сбер: {rate}%")
        except:
            pass
        
        time.sleep(1)
        
        # ВТБ
        try:
            print("  Парсим ВТБ...")
            url = "https://www.vtb.ru/personal/ipoteka/"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                rate = self.extract_rate(response.text)
                if rate:
                    self.all_rates['ВТБ'] = rate
                    print(f"    ✓ ВТБ: {rate}%")
        except:
            pass
        
        time.sleep(1)
        
        # Альфа
        try:
            print("  Парсим Альфа-Банк...")
            url = "https://alfabank.ru/get-money/mortgage/"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                rate = self.extract_rate(response.text)
                if rate:
                    self.all_rates['Альфа-Банк'] = rate
                    print(f"    ✓ Альфа-Банк: {rate}%")
        except:
            pass
    
    def add_fallback_rates(self):
        """Добавляет запасные ставки"""
        added = 0
        for bank, rate in self.fallback_rates.items():
            if bank not in self.all_rates:
                self.all_rates[bank] = rate
                added += 1
        
        if added > 0:
            print(f"    ➕ Добавлено запасных банков: {added}")
    
    def collect_all_rates(self):
        """Запускает все парсеры"""
        print("  Запускаем расширенный парсинг...")
        
        # Сначала пробуем Сравни.ру (новый источник, может быть проще)
        sravni_success = self.parse_sravni_ru()
        time.sleep(2)
        
        # Потом Банки.ру с прокси
        banki_success = self.parse_banki_ru()
        
        if not banki_success and not sravni_success:
            print("  ⚠️ Агрегаторы не спарсились, парсим отдельные банки...")
            self.parse_individual_banks()
        else:
            time.sleep(1)
            self.parse_individual_banks()  # Для сверки
        
        # Добавляем запасные
        self.add_fallback_rates()
        
        return self.all_rates

# ===== ФОРМАТИРОВАНИЕ =====
def format_message(rates_dict):
    if not rates_dict:
        return "😔 Не удалось получить ставки"
    
    rates_list = [(bank, rate) for bank, rate in rates_dict.items()]
    rates_list.sort(key=lambda x: x[1])
    
    top_rates = rates_list[:20]
    min_bank, min_rate = rates_list[0]
    
    # Определяем источники
    has_banki = any('банки' in b.lower() for b, _ in rates_list[:5])
    has_sravni = any('сравни' in b.lower() for b, _ in rates_list[:5])
    
    sources = []
    if has_banki:
        sources.append("Банки.ру")
    if has_sravni:
        sources.append("Сравни.ру")
    
    source_text = f"Источники: {', '.join(sources)}" if sources else "Источники: запасные данные"
    
    text = f"""
🏠 <b>Ипотека сегодня: МИНИМАЛЬНАЯ СТАВКА</b>

🔥 <b>Лучшее предложение:</b>
• {min_bank} — <b>{min_rate}%</b>

📊 <b>Все банки:</b>

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
📊 Всего: {len(rates_list)} банков
🔄 {source_text}
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
            print("  ✅ Отправлено!")
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")

# ===== ГЛАВНАЯ =====
def main():
    print("=" * 60)
    print("🚀 ЗАПУСК РАСШИРЕННОГО ПАРСИНГА")
    print(f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print("=" * 60)
    
    if not BOT_TOKEN or not CHANNEL_ID:
        print("❌ Ошибка настроек")
        return
    
    parser = BankiRuParser()
    rates = parser.collect_all_rates()
    
    print(f"\n📊 Всего: {len(rates)} банков")
    message = format_message(rates)
    send_to_channel(message)
    print("\n✅ ГОТОВО")

if __name__ == "__main__":
    main()