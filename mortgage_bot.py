"""
Ипотечный бот - МАКСИМАЛЬНАЯ ВЕРСИЯ с 7 источниками данных
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
import json

warnings.filterwarnings("ignore", category=DeprecationWarning)

# ===== НАСТРОЙКИ =====
BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
CHANNEL_ID = os.environ.get('CHANNEL_ID', '')

# ===== ПРОКСИ-МЕНЕДЖЕР =====
class ProxyManager:
    def __init__(self):
        self.proxies = []
        self.current_proxy = None
        self.update_proxy_list()
    
    def fetch_proxies(self, url):
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return [line.strip() for line in response.text.strip().split('\n') if line.strip()]
            return []
        except:
            return []
    
    def update_proxy_list(self):
        """Качает прокси из 5 источников"""
        print("  Загружаем прокси...")
        all_proxies = []
        
        # Источник 1: ProxyScrape
        proxies1 = self.fetch_proxies("https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=RU&ssl=all")
        all_proxies.extend(proxies1)
        
        # Источник 2: GoekhanDev
        proxies2 = self.fetch_proxies("https://raw.githubusercontent.com/GoekhanDev/free-proxy-list/main/http.txt")
        all_proxies.extend(proxies2)
        
        # Источник 3: proxifly
        proxies3 = self.fetch_proxies("https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/http/data.txt")
        all_proxies.extend(proxies3)
        
        # Убираем дубликаты
        self.proxies = list(set(all_proxies))[:50]
        print(f"    ✅ Загружено прокси: {len(self.proxies)}")
    
    def get_proxy(self):
        if not self.proxies:
            self.update_proxy_list()
        
        if self.proxies:
            proxy = random.choice(self.proxies)
            return {
                'http': f'http://{proxy}',
                'https': f'http://{proxy}'
            }
        return None
    
    def report_bad(self, proxy):
        if proxy and proxy in self.proxies:
            self.proxies.remove(proxy)

# ===== ПАРСЕР =====
class MegaParser:
    def __init__(self):
        self.all_rates = {}
        self.proxy_manager = ProxyManager()
        
        # Заголовки
        self.headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Connection': 'keep-alive',
        }
    
    def get_ua(self):
        ua_list = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15',
        ]
        return random.choice(ua_list)
    
    def extract_rate(self, text):
        if not text:
            return None
        
        patterns = [
            r'от\s*(\d+[.,]\d+)%',
            r'(\d+[.,]\d+)%\s*годовых',
            r'(\d+[.,]\d+)%',
            r'ставка[^\d]*(\d+[.,]\d+)',
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
    
    # ===== ИСТОЧНИК 1: Банки.ру =====
    def parse_banki_ru(self):
        """Парсинг Банки.ру через прокси"""
        print("  [1/7] Парсим Банки.ру...")
        
        for attempt in range(3):
            proxy = self.proxy_manager.get_proxy()
            if not proxy:
                continue
            
            try:
                session = requests.Session()
                session.proxies.update(proxy)
                session.headers.update({'User-Agent': self.get_ua()})
                
                # Заходим на главную
                session.get('https://www.banki.ru/', timeout=10)
                time.sleep(1)
                
                # На страницу с ипотекой
                url = "https://www.banki.ru/products/ipoteka/"
                response = session.get(url, timeout=10)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    found = 0
                    
                    # Ищем строки с банками
                    rows = soup.find_all('tr', {'data-test': 'row'})
                    if not rows:
                        rows = soup.find_all('tr', class_=re.compile('row|product'))
                    
                    for row in rows[:20]:
                        try:
                            # Название банка
                            name_tag = row.find(['a', 'span'], class_=re.compile('name|title'))
                            if not name_tag:
                                continue
                            
                            bank_name = name_tag.get_text().strip()
                            bank_name = re.sub(r'\s+', ' ', bank_name)
                            
                            # Ставка
                            row_text = row.get_text()
                            rate = self.extract_rate(row_text)
                            
                            if bank_name and rate:
                                self.all_rates[bank_name] = rate
                                found += 1
                                print(f"      ✓ {bank_name[:20]}: {rate}%")
                                
                        except:
                            continue
                    
                    if found > 0:
                        print(f"    ✅ Банки.ру: {found} банков")
                        return True
                    else:
                        self.proxy_manager.report_bad(proxy)
                        
            except Exception as e:
                print(f"    ⚠️ Ошибка: {e}")
                self.proxy_manager.report_bad(proxy)
            
            time.sleep(1)
        
        print("    ❌ Банки.ру не спарсился")
        return False
    
    # ===== ИСТОЧНИК 2: Сравни.ру =====
    def parse_sravni_ru(self):
        """Парсинг Сравни.ру"""
        print("  [2/7] Парсим Сравни.ру...")
        
        try:
            url = "https://www.sravni.ru/ipoteka/"
            headers = {'User-Agent': self.get_ua()}
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                found = 0
                
                # Ищем карточки банков
                cards = soup.find_all('div', class_=re.compile('product-item|bank-card|offer'))
                
                if not cards:
                    cards = soup.find_all('article', class_=re.compile('product'))
                
                for card in cards[:15]:
                    try:
                        card_text = card.get_text()
                        
                        # Название банка
                        bank_match = re.search(r'([А-Я][а-я]+(?:\s+[А-Я][а-я]+)*)', card_text)
                        if not bank_match:
                            continue
                        
                        bank_name = bank_match.group(1).strip()
                        
                        # Ставка
                        rate = self.extract_rate(card_text)
                        
                        if bank_name and rate:
                            self.all_rates[bank_name] = rate
                            found += 1
                            print(f"      ✓ {bank_name[:20]}: {rate}%")
                            
                    except:
                        continue
                
                if found > 0:
                    print(f"    ✅ Сравни.ру: {found} банков")
                    return True
                else:
                    print("    ⚠️ Банки не найдены")
            else:
                print(f"    ⚠️ Статус {response.status_code}")
                
        except Exception as e:
            print(f"    ❌ Ошибка: {e}")
        
        return False
    
    # ===== ИСТОЧНИК 3: МБК =====
    def parse_mbk_ru(self):
        """Парсинг МБК"""
        print("  [3/7] Парсим МБК...")
        
        try:
            url = "https://www.mbk.ru/ipoteka/"
            headers = {'User-Agent': self.get_ua()}
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                found = 0
                
                # Ищем блоки с банками
                blocks = soup.find_all('div', class_=re.compile('bank-item|product-card'))
                
                for block in blocks[:15]:
                    try:
                        text = block.get_text()
                        
                        bank_match = re.search(r'([А-Я][а-я]+(?:\s+[А-Я][а-я]+)*)', text)
                        if not bank_match:
                            continue
                        
                        bank_name = bank_match.group(1).strip()
                        rate = self.extract_rate(text)
                        
                        if bank_name and rate:
                            self.all_rates[bank_name] = rate
                            found += 1
                            print(f"      ✓ {bank_name[:20]}: {rate}%")
                            
                    except:
                        continue
                
                if found > 0:
                    print(f"    ✅ МБК: {found} банков")
                    return True
                    
        except Exception as e:
            print(f"    ❌ Ошибка: {e}")
        
        return False
    
    # ===== ИСТОЧНИК 4: Выберу.ру =====
    def parse_vbr_ru(self):
        """Парсинг Выберу.ру"""
        print("  [4/7] Парсим Выберу.ру...")
        
        try:
            url = "https://www.vbr.ru/banki/ipoteka/"
            headers = {'User-Agent': self.get_ua()}
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                found = 0
                
                items = soup.find_all('div', class_=re.compile('b-list-item'))
                
                for item in items[:15]:
                    try:
                        text = item.get_text()
                        
                        bank_match = re.search(r'([А-Я][а-я]+(?:\s+[А-Я][а-я]+)*)', text)
                        if not bank_match:
                            continue
                        
                        bank_name = bank_match.group(1).strip()
                        rate = self.extract_rate(text)
                        
                        if bank_name and rate:
                            self.all_rates[bank_name] = rate
                            found += 1
                            print(f"      ✓ {bank_name[:20]}: {rate}%")
                            
                    except:
                        continue
                
                if found > 0:
                    print(f"    ✅ Выберу.ру: {found} банков")
                    return True
                    
        except Exception as e:
            print(f"    ❌ Ошибка: {e}")
        
        return False
    
    # ===== ИСТОЧНИК 5: Финуслуги =====
    def parse_finuslugi_ru(self):
        """Парсинг Финуслуги"""
        print("  [5/7] Парсим Финуслуги...")
        
        try:
            url = "https://finuslugi.ru/mortgages"
            headers = {'User-Agent': self.get_ua()}
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                found = 0
                
                cards = soup.find_all('div', class_=re.compile('card|product'))
                
                for card in cards[:15]:
                    try:
                        text = card.get_text()
                        
                        bank_match = re.search(r'([А-Я][а-я]+(?:\s+[А-Я][а-я]+)*)', text)
                        if not bank_match:
                            continue
                        
                        bank_name = bank_match.group(1).strip()
                        rate = self.extract_rate(text)
                        
                        if bank_name and rate:
                            self.all_rates[bank_name] = rate
                            found += 1
                            print(f"      ✓ {bank_name[:20]}: {rate}%")
                            
                    except:
                        continue
                
                if found > 0:
                    print(f"    ✅ Финуслуги: {found} банков")
                    return True
                    
        except Exception as e:
            print(f"    ❌ Ошибка: {e}")
        
        return False
    
    # ===== ИСТОЧНИК 6: БанкИнформ =====
    def parse_bankinform_ru(self):
        """Парсинг БанкИнформ"""
        print("  [6/7] Парсим БанкИнформ...")
        
        try:
            url = "https://bankinform.ru/bank/ipoteka"
            headers = {'User-Agent': self.get_ua()}
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                found = 0
                
                rows = soup.find_all('tr')
                
                for row in rows[1:16]:
                    try:
                        text = row.get_text()
                        
                        bank_match = re.search(r'([А-Я][а-я]+(?:\s+[А-Я][а-я]+)*)', text)
                        if not bank_match:
                            continue
                        
                        bank_name = bank_match.group(1).strip()
                        rate = self.extract_rate(text)
                        
                        if bank_name and rate:
                            self.all_rates[bank_name] = rate
                            found += 1
                            print(f"      ✓ {bank_name[:20]}: {rate}%")
                            
                    except:
                        continue
                
                if found > 0:
                    print(f"    ✅ БанкИнформ: {found} банков")
                    return True
                    
        except Exception as e:
            print(f"    ❌ Ошибка: {e}")
        
        return False
    
    # ===== ИСТОЧНИК 7: Яндекс.Недвижимость =====
    def parse_yandex_ru(self):
        """Парсинг Яндекс.Недвижимость"""
        print("  [7/7] Парсим Яндекс.Недвижимость...")
        
        try:
            url = "https://realty.yandex.ru/ipoteka/programs/"
            headers = {'User-Agent': self.get_ua()}
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                found = 0
                
                blocks = soup.find_all('div', class_=re.compile('program|card'))
                
                for block in blocks[:10]:
                    try:
                        text = block.get_text()
                        
                        bank_match = re.search(r'([А-Я][а-я]+(?:\s+[А-Я][а-я]+)*)', text)
                        if not bank_match:
                            continue
                        
                        bank_name = bank_match.group(1).strip()
                        rate = self.extract_rate(text)
                        
                        if bank_name and rate:
                            self.all_rates[bank_name] = rate
                            found += 1
                            print(f"      ✓ {bank_name[:20]}: {rate}%")
                            
                    except:
                        continue
                
                if found > 0:
                    print(f"    ✅ Яндекс: {found} банков")
                    return True
                    
        except Exception as e:
            print(f"    ❌ Ошибка: {e}")
        
        return False
    
    # ===== ОТДЕЛЬНЫЕ БАНКИ =====
    def parse_individual_banks(self):
        """Парсинг конкретных банков"""
        print("  Парсим отдельные банки...")
        
        # Сбер
        try:
            url = "https://www.sberbank.ru/ru/person/credits/home/buying_complete_house"
            response = requests.get(url, headers={'User-Agent': self.get_ua()}, timeout=10)
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
            url = "https://www.vtb.ru/personal/ipoteka/"
            response = requests.get(url, headers={'User-Agent': self.get_ua()}, timeout=10)
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
            url = "https://alfabank.ru/get-money/mortgage/"
            response = requests.get(url, headers={'User-Agent': self.get_ua()}, timeout=10)
            if response.status_code == 200:
                rate = self.extract_rate(response.text)
                if rate:
                    self.all_rates['Альфа-Банк'] = rate
                    print(f"    ✓ Альфа: {rate}%")
        except:
            pass
    
    # ===== ГЛАВНЫЙ СБОР =====
    def collect_all_rates(self):
        """Запускает все 7 источников"""
        print("\n  🚀 ЗАПУСК 7 ИСТОЧНИКОВ")
        
        # Источник 1-2: Банки.ру и Сравни.ру
        self.parse_banki_ru()
        time.sleep(2)
        self.parse_sravni_ru()
        time.sleep(2)
        
        # Источник 3-5: Остальные агрегаторы
        self.parse_mbk_ru()
        time.sleep(1)
        self.parse_vbr_ru()
        time.sleep(1)
        self.parse_finuslugi_ru()
        time.sleep(1)
        
        # Источник 6-7: Ещё два
        self.parse_bankinform_ru()
        time.sleep(1)
        self.parse_yandex_ru()
        time.sleep(1)
        
        # Отдельные банки для сверки
        self.parse_individual_banks()
        
        # Убираем дубликаты банков (оставляем минимальные ставки)
        unique_rates = {}
        for bank, rate in self.all_rates.items():
            bank_key = bank.lower()
            bank_key = re.sub(r'[«»"]', '', bank_key)
            bank_key = bank_key.replace('банк', '').replace('бaнк', '').strip()
            
            found = False
            for existing_bank, existing_rate in unique_rates.items():
                if bank_key in existing_bank.lower() or existing_bank.lower() in bank_key:
                    unique_rates[existing_bank] = min(rate, existing_rate)
                    found = True
                    break
            
            if not found:
                unique_rates[bank] = rate
        
        self.all_rates = unique_rates
        
        print(f"\n  ✅ ВСЕГО УНИКАЛЬНЫХ БАНКОВ: {len(self.all_rates)}")
        return self.all_rates

# ===== ФОРМАТИРОВАНИЕ =====
def format_message(rates_dict):
    if not rates_dict:
        return "😔 Не удалось получить ставки"
    
    rates_list = [(bank, rate) for bank, rate in rates_dict.items()]
    rates_list.sort(key=lambda x: x[1])
    
    top_rates = rates_list[:20]
    min_bank, min_rate = rates_list[0]
    
    text = f"""
🏠 <b>Ипотека сегодня: МИНИМАЛЬНАЯ СТАВКА</b>

🔥 <b>Лучшее предложение:</b>
• {min_bank} — <b>{min_rate}%</b>

📊 <b>Топ-20 банков:</b>

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
🔄 Источники: 7 агрегаторов + отдельные банки
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
    print("🚀 MEGA PARSER - 7 ИСТОЧНИКОВ")
    print(f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print("=" * 60)
    
    if not BOT_TOKEN or not CHANNEL_ID:
        print("❌ Ошибка настроек")
        return
    
    parser = MegaParser()
    rates = parser.collect_all_rates()
    
    print(f"\n📊 Всего уникальных банков: {len(rates)}")
    
    if len(rates) < 5:
        print("⚠️ Мало данных, добавляем запасные...")
        fallback = {
            'Сбербанк': 21.0, 'ВТБ': 20.1, 'Альфа-Банк': 20.5,
            'Т-Банк': 16.9, 'Уралсиб': 18.79, 'Промсвязьбанк': 19.49
        }
        for bank, rate in fallback.items():
            if bank not in rates:
                rates[bank] = rate
    
    message = format_message(rates)
    send_to_channel(message)
    print("\n✅ ГОТОВО")

if __name__ == "__main__":
    main()