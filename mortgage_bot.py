"""
Ипотечный бот - умный парсинг с самодельным прокси-менеджером
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

# ===== СВОЙ ПРОКСИ-МЕНЕДЖЕР =====
class SimpleProxyManager:
    def __init__(self):
        self.proxies = []
        self.current_proxy = None
        self.update_proxy_list()
    
    def update_proxy_list(self):
        """Качает свежий список бесплатных прокси"""
        try:
            # Публичный API бесплатных прокси (работает без ключей)
            url = "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=RU&ssl=all&anonymity=all"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                # Разбираем построчно
                proxy_lines = response.text.strip().split('\n')
                # Берём только российские, которые работают быстро
                self.proxies = [p.strip() for p in proxy_lines if p.strip()][:50]
                print(f"    ✅ Загружено прокси: {len(self.proxies)}")
            else:
                print(f"    ⚠️ Не удалось загрузить прокси, статус: {response.status_code}")
                # Запасные прокси (на всякий случай)
                self.proxies = [
                    "185.132.179.146:8080",
                    "45.132.184.38:3128",
                    "46.229.234.113:8080"
                ]
        except Exception as e:
            print(f"    ⚠️ Ошибка загрузки прокси: {e}")
            self.proxies = []
    
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
        """Сообщаем, что текущий прокси не работает - заменяем"""
        if self.current_proxy and self.current_proxy in self.proxies:
            self.proxies.remove(self.current_proxy)
        self.current_proxy = None

# ===== ПАРСЕР =====
class BankiRuParser:
    def __init__(self):
        self.all_rates = {}
        self.proxy_manager = SimpleProxyManager()
        
        # Запасные ставки на случай если всё упадёт
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
    
    def parse_banki_ru(self):
        """Парсинг Банки.ру через прокси"""
        try:
            print("  Парсим Банки.ру с прокси...")
            
            # Пробуем до 3 разных прокси
            for attempt in range(3):
                # Получаем случайный прокси
                proxy = self.proxy_manager.get_random_proxy()
                if not proxy:
                    print("    ⚠️ Нет доступных прокси")
                    return False
                
                print(f"    Попытка {attempt+1}, прокси: {proxy['http']}")
                
                headers = self.headers.copy()
                headers['User-Agent'] = self.get_random_user_agent()
                
                try:
                    # Делаем запрос через прокси
                    session = requests.Session()
                    session.proxies.update(proxy)
                    session.headers.update(headers)
                    
                    # Сначала заходим на главную
                    session.get('https://www.banki.ru/', timeout=10)
                    time.sleep(1)
                    
                    # Теперь на страницу с ипотекой
                    url = "https://www.banki.ru/products/ipoteka/"
                    response = session.get(url, timeout=10)
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # Ищем банки
                        found_banks = 0
                        rows = soup.find_all('tr', {'data-test': 'row'})
                        
                        if not rows:
                            rows = soup.find_all('tr', class_=re.compile('row|product'))
                        
                        for row in rows[:20]:
                            try:
                                row_text = row.get_text()
                                # Ищем название банка
                                bank_match = re.search(r'([А-Я][а-я]+(?:\s+[А-Я][а-я]+)*)', row_text)
                                if not bank_match:
                                    continue
                                
                                bank_name = bank_match.group(1).strip()
                                rate = self.extract_rate(row_text)
                                
                                if bank_name and rate and len(bank_name) < 40:
                                    self.all_rates[bank_name] = rate
                                    found_banks += 1
                                    print(f"    ✓ {bank_name[:30]}: {rate}%")
                                    
                            except Exception:
                                continue
                        
                        if found_banks > 0:
                            print(f"    ✅ Найдено банков: {found_banks}")
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
        """Парсинг отдельных банков (как запасной вариант)"""
        
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
        print("  Запускаем умный парсинг с прокси...")
        
        # Пробуем Банки.ру
        banki_success = self.parse_banki_ru()
        
        if not banki_success:
            print("  ⚠️ Банки.ру не спарсился, парсим отдельные банки...")
            self.parse_individual_banks()
        else:
            time.sleep(1)
            self.parse_individual_banks()
        
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
    print("=" * 50)
    print("🚀 ЗАПУСК С ПРОКСИ")
    print(f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print("=" * 50)
    
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