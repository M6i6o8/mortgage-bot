"""
Ипотечный бот - умный парсинг с Банки.ру и других источников
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

# ===== НАСТРОЙКИ =====
BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
CHANNEL_ID = os.environ.get('CHANNEL_ID', '')

# ===== СПИСОК USER-AGENT ДЛЯ РОТАЦИИ =====
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
]

class SmartMortgageParser:
    def __init__(self):
        self.all_rates = {}
        
    def get_random_headers(self):
        """Возвращает случайный User-Agent"""
        return {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        }
    
    def extract_rate(self, text):
        """Извлекает число-ставку из текста"""
        if not text:
            return None
            
        patterns = [
            r'от\s*(\d+[.,]\d+)%',
            r'ставка[^\d]*(\d+[.,]\d+)%',
            r'(\d+[.,]\d+)%\s*годовых',
            r'(\d+[.,]\d+)%',
            r'(\d+[.,]\d+)\s*%',
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
    
    def parse_banki_ru(self):
        """Парсинг Банки.ру - основной источник"""
        try:
            print("  Парсим Банки.ру...")
            url = "https://www.banki.ru/products/ipoteka/"
            response = self.safe_request(url)
            
            if not response:
                print("    ✗ Не удалось загрузить Банки.ру")
                return
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Ищем все строки с банками
            # На Банки.ру таблица с классом 'products-table'
            rows = soup.find_all('tr', {'data-test': 'row'})
            
            if not rows:
                # Альтернативный поиск
                rows = soup.find_all('tr', class_=re.compile('row|product'))
            
            bank_count = 0
            for row in rows[:20]:  # Первые 20 банков
                try:
                    # Название банка
                    name_cell = row.find('td', class_=re.compile('name|bank'))
                    if not name_cell:
                        continue
                    
                    bank_name = name_cell.get_text().strip()
                    bank_name = re.sub(r'\s+', ' ', bank_name)
                    
                    # Ставка - ищем во всей строке
                    row_text = row.get_text()
                    rate = self.extract_rate(row_text)
                    
                    if bank_name and rate and len(bank_name) < 30:
                        self.all_rates[bank_name] = rate
                        bank_count += 1
                        print(f"    ✓ {bank_name}: {rate}%")
                        
                except Exception as e:
                    continue
            
            print(f"    ✅ Найдено банков на Банки.ру: {bank_count}")
            
        except Exception as e:
            print(f"    ✗ Ошибка парсинга Банки.ру: {e}")
    
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
                    print("    ✗ Ставка не найдена")
            else:
                print("    ✗ Не удалось загрузить")
                
        except Exception as e:
            print(f"    ✗ Ошибка: {e}")
    
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
                    print("    ✗ Ставка не найдена")
            else:
                print("    ✗ Не удалось загрузить")
                
        except Exception as e:
            print(f"    ✗ Ошибка: {e}")
    
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
                    print("    ✗ Ставка не найдена")
            else:
                print("    ✗ Не удалось загрузить")
                
        except Exception as e:
            print(f"    ✗ Ошибка: {e}")
    
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
                    print("    ✗ Ставка не найдена")
            else:
                print("    ✗ Не удалось загрузить")
                
        except Exception as e:
            print(f"    ✗ Ошибка: {e}")
    
    def collect_all_rates(self):
        """Запускает все парсеры"""
        print("  Запускаем умный парсинг...")
        
        # Сначала парсим Банки.ру (там больше всего банков)
        self.parse_banki_ru()
        time.sleep(2)
        
        # Парсим отдельные банки для сверки
        self.parse_sber()
        time.sleep(1.5)
        self.parse_vtb()
        time.sleep(1.5)
        self.parse_alfa()
        time.sleep(1.5)
        self.parse_domrf()
        
        # Фильтруем ставки
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

📅 Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')} (МСК)
📊 Всего банков: {len(rates_list)}
🔄 Источник: Банки.ру и официальные сайты
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
    
    if not BOT_TOKEN or not CHANNEL_ID:
        print("❌ Ошибка: не заданы BOT_TOKEN или CHANNEL_ID")
        return
    
    print(f"📢 Канал: {CHANNEL_ID}")
    
    print("\n🔍 НАЧАЛО ПАРСИНГА")
    parser = SmartMortgageParser()
    rates = parser.collect_all_rates()
    
    print(f"\n📊 ИТОГО: {len(rates)} банков")
    
    print("\n✏️ ФОРМИРОВАНИЕ СООБЩЕНИЯ")
    message = format_message(rates)
    print(f"📏 Длина: {len(message)} символов")
    
    print("\n📤 ОТПРАВКА В КАНАЛ")
    send_to_channel(message)
    
    print("\n" + "=" * 50)
    print("✅ БОТ ЗАВЕРШИЛ РАБОТУ")
    print("=" * 50)

if __name__ == "__main__":
    main()