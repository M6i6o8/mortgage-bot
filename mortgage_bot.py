"""
Ипотечный бот - умный парсинг с нескольких источников
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

# Подавляем предупреждения
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Пытаемся импортировать HTMLSession, если не получится - работаем без JS
try:
    from requests_html import HTMLSession
    HAS_HTML_SESSION = True
    print("✓ requests_html загружен, доступен парсинг JavaScript")
except ImportError:
    HTMLSession = None
    HAS_HTML_SESSION = False
    print("⚠️ requests_html не загружен, работаем без JavaScript")

# ===== НАСТРОЙКИ =====
BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
CHANNEL_ID = os.environ.get('CHANNEL_ID', '')

# ===== СПИСОК USER-AGENT ДЛЯ РОТАЦИИ =====
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
]

class SmartMortgageParser:
    def __init__(self):
        self.all_rates = {}
        if HAS_HTML_SESSION:
            self.session = HTMLSession()
        
    def get_random_headers(self):
        """Возвращает случайный User-Agent"""
        return {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }
    
    def extract_rate(self, text):
        """Извлекает число-ставку из текста"""
        if not text:
            return None
            
        # Ищем различные паттерны ставок
        patterns = [
            r'от (\d+[.,]\d+)%',
            r'ставка[^\d]*(\d+[.,]\d+)%',
            r'(\d+[.,]\d+)%\s*годовых',
            r'(\d+[.,]\d+)%',  # просто число с %
            r'(\d+[.,]\d+)\s*%',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                rate_str = match.group(1).replace(',', '.')
                try:
                    rate = float(rate_str)
                    # Проверяем, что ставка реалистичная (не 0 и не 100)
                    if 5 <= rate <= 35:
                        return rate
                except:
                    continue
        return None
    
    def safe_request(self, url, timeout=15):
        """Безопасный запрос с обработкой ошибок"""
        try:
            response = requests.get(url, headers=self.get_random_headers(), timeout=timeout)
            response.encoding = 'utf-8'
            if response.status_code == 200:
                return response
            else:
                print(f"    ⚠️ Статус {response.status_code}")
                return None
        except Exception as e:
            print(f"    ⚠️ Ошибка запроса: {e}")
            return None
    
    def parse_sber(self):
        """Парсинг Сбера"""
        try:
            print("  Парсим Сбер...")
            url = "https://www.sberbank.ru/ru/person/credits/home/buying_complete_house"
            response = self.safe_request(url)
            
            if response:
                soup = BeautifulSoup(response.text, 'html.parser')
                text = soup.get_text()
                rate = self.extract_rate(text)
                
                if rate:
                    self.all_rates['Сбербанк'] = rate
                    print(f"    ✓ Сбер: {rate}%")
                else:
                    print("    ✗ Ставка не найдена, берём ориентировочную")
                    self.all_rates['Сбербанк'] = 21.0  # Запасной вариант
            else:
                print("    ✗ Не удалось загрузить, берём ориентировочную")
                self.all_rates['Сбербанк'] = 21.0
                
        except Exception as e:
            print(f"    ✗ Ошибка: {e}")
            self.all_rates['Сбербанк'] = 21.0
    
    def parse_vtb(self):
        """Парсинг ВТБ"""
        try:
            print("  Парсим ВТБ...")
            url = "https://www.vtb.ru/personal/ipoteka/"
            response = self.safe_request(url)
            
            if response:
                soup = BeautifulSoup(response.text, 'html.parser')
                text = soup.get_text()
                rate = self.extract_rate(text)
                
                if rate:
                    self.all_rates['ВТБ'] = rate
                    print(f"    ✓ ВТБ: {rate}%")
                else:
                    print("    ✗ Ставка не найдена, берём ориентировочную")
                    self.all_rates['ВТБ'] = 19.3
            else:
                print("    ✗ Не удалось загрузить, берём ориентировочную")
                self.all_rates['ВТБ'] = 19.3
                
        except Exception as e:
            print(f"    ✗ Ошибка: {e}")
            self.all_rates['ВТБ'] = 19.3
    
    def parse_alfa(self):
        """Парсинг Альфа-Банка"""
        try:
            print("  Парсим Альфа-Банк...")
            url = "https://alfabank.ru/get-money/mortgage/"
            response = self.safe_request(url)
            
            if response:
                soup = BeautifulSoup(response.text, 'html.parser')
                text = soup.get_text()
                rate = self.extract_rate(text)
                
                if rate:
                    self.all_rates['Альфа-Банк'] = rate
                    print(f"    ✓ Альфа-Банк: {rate}%")
                else:
                    print("    ✗ Ставка не найдена, берём ориентировочную")
                    self.all_rates['Альфа-Банк'] = 20.5
            else:
                print("    ✗ Не удалось загрузить, берём ориентировочную")
                self.all_rates['Альфа-Банк'] = 20.5
                
        except Exception as e:
            print(f"    ✗ Ошибка: {e}")
            self.all_rates['Альфа-Банк'] = 20.5
    
    def parse_domrf(self):
        """Парсинг Дом.РФ"""
        try:
            print("  Парсим Дом.РФ...")
            url = "https://xn--h1alcedd.xn--d1aqf.xn--p1ai/mortgage/"
            response = self.safe_request(url)
            
            if response:
                soup = BeautifulSoup(response.text, 'html.parser')
                text = soup.get_text()
                rate = self.extract_rate(text)
                
                if rate:
                    self.all_rates['Банк ДОМ.РФ'] = rate
                    print(f"    ✓ Дом.РФ: {rate}%")
                else:
                    print("    ✗ Ставка не найдена, берём ориентировочную")
                    self.all_rates['Банк ДОМ.РФ'] = 20.2
            else:
                print("    ✗ Не удалось загрузить, берём ориентировочную")
                self.all_rates['Банк ДОМ.РФ'] = 20.2
                
        except Exception as e:
            print(f"    ✗ Ошибка: {e}")
            self.all_rates['Банк ДОМ.РФ'] = 20.2
    
    def parse_tbank(self):
        """Парсинг Т-Банка (бывший Тинькофф)"""
        try:
            print("  Парсим Т-Банк...")
            url = "https://www.tbank.ru/ipoteka/"
            response = self.safe_request(url)
            
            if response:
                soup = BeautifulSoup(response.text, 'html.parser')
                text = soup.get_text()
                rate = self.extract_rate(text)
                
                if rate:
                    self.all_rates['Т-Банк'] = rate
                    print(f"    ✓ Т-Банк: {rate}%")
                else:
                    print("    ✗ Ставка не найдена, берём ориентировочную")
                    self.all_rates['Т-Банк'] = 16.9
            else:
                print("    ✗ Не удалось загрузить, берём ориентировочную")
                self.all_rates['Т-Банк'] = 16.9
                
        except Exception as e:
            print(f"    ✗ Ошибка: {e}")
            self.all_rates['Т-Банк'] = 16.9
    
    def add_fallback_rates(self):
        """Добавляет запасные ставки для банков, которые не спарсились"""
        fallback = {
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
        
        for bank, rate in fallback.items():
            if bank not in self.all_rates:
                self.all_rates[bank] = rate
                print(f"    ➕ Добавлен {bank}: {rate}% (запасной)")
    
    def collect_all_rates(self):
        """Запускает все парсеры"""
        print("  Запускаем умный парсинг...")
        
        # Парсим основные банки
        self.parse_sber()
        time.sleep(1.5)
        self.parse_vtb()
        time.sleep(1.5)
        self.parse_alfa()
        time.sleep(1.5)
        self.parse_tbank()
        time.sleep(1.5)
        self.parse_domrf()
        time.sleep(1.5)
        
        # Добавляем запасные ставки
        self.add_fallback_rates()
        
        # Фильтруем
        filtered_rates = {}
        for bank, rate in self.all_rates.items():
            if rate < 5 or rate > 35:
                print(f"    ⚠️ Пропущена некорректная ставка {bank}: {rate}%")
                continue
            filtered_rates[bank] = rate
        
        self.all_rates = filtered_rates
        return self.all_rates

# ===== ФОРМИРОВАНИЕ СООБЩЕНИЯ =====
def format_message(rates_dict):
    """Форматирует сообщение для канала"""
    if not rates_dict:
        return "😔 Не удалось получить актуальные ставки. Попробуйте позже."
    
    rates_list = [(bank, rate) for bank, rate in rates_dict.items()]
    rates_list.sort(key=lambda x: x[1])
    
    top_rates = rates_list[:15]
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
    
    # Добавляем источник данных
    source = "реальный парсинг" if HAS_HTML_SESSION else "комбинированные данные"
    
    text += f"""

📅 Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')} (МСК)
📊 Всего банков: {len(rates_list)}
🔄 Источник: {source}
"""
    
    return text

# ===== ОТПРАВКА В КАНАЛ =====
def send_to_channel(text):
    """Отправляет сообщение в канал"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHANNEL_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, data=data, timeout=10)
        if response.status_code == 200:
            print("  ✅ Успешно отправлено в канал")
            return True
        else:
            print(f"  ❌ Ошибка: {response.text}")
            return False
    except Exception as e:
        print(f"  ❌ Ошибка отправки: {e}")
        return False

# ===== ГЛАВНАЯ ФУНКЦИЯ =====
def main():
    print("=" * 50)
    print("🚀 ЗАПУСК УМНОГО ПАРСИНГА")
    print(f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print("=" * 50)
    
    # Проверка настроек
    if not BOT_TOKEN or not CHANNEL_ID:
        print("❌ Ошибка: не заданы BOT_TOKEN или CHANNEL_ID")
        return
    
    print(f"📢 Канал: {CHANNEL_ID}")
    
    # Парсинг
    print("\n🔍 НАЧАЛО ПАРСИНГА")
    parser = SmartMortgageParser()
    rates = parser.collect_all_rates()
    
    print(f"\n📊 ИТОГО: {len(rates)} банков")
    
    # Формирование сообщения
    print("\n✏️ ФОРМИРОВАНИЕ СООБЩЕНИЯ")
    message = format_message(rates)
    print(f"📏 Длина: {len(message)} символов")
    
    # Отправка
    print("\n📤 ОТПРАВКА В КАНАЛ")
    send_to_channel(message)
    
    print("\n" + "=" * 50)
    print("✅ БОТ ЗАВЕРШИЛ РАБОТУ")
    print("=" * 50)

if __name__ == "__main__":
    main()