"""
Ипотечный бот - умный парсинг с нескольких источников
Запуск на GitHub Actions
"""

import requests
from requests_html import HTMLSession
from bs4 import BeautifulSoup
import re
from datetime import datetime
import os
import random
import time

# ===== НАСТРОЙКИ =====
BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
CHANNEL_ID = os.environ.get('CHANNEL_ID', '')

# ===== СПИСОК USER-AGENT ДЛЯ РОТАЦИИ =====
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
]

class SmartMortgageParser:
    def __init__(self):
        self.all_rates = {}
        self.session = HTMLSession()
        
    def get_random_headers(self):
        """Возвращает случайный User-Agent"""
        return {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        }
    
    def extract_rate(self, text):
        """Извлекает число-ставку из текста"""
        # Ищем "от X%" или просто "X%"
        patterns = [
            r'от (\d+[.,]\d+)%',
            r'ставка[^\d]*(\d+[.,]\d+)%',
            r'(\d+[.,]\d+)%\s*годовых',
            r'(\d+[.,]\d+)%',  # просто число с %
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                rate_str = match.group(1).replace(',', '.')
                try:
                    return float(rate_str)
                except:
                    continue
        return None
    
    def parse_sber(self):
        """Парсинг Сбера"""
        try:
            print("  Парсим Сбер...")
            url = "https://www.sberbank.ru/ru/person/credits/home/buying_complete_house"
            response = requests.get(url, headers=self.get_random_headers(), timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                text = soup.get_text()
                rate = self.extract_rate(text)
                
                if rate:
                    self.all_rates['Сбербанк'] = rate
                    print(f"    ✓ Сбер: {rate}%")
                else:
                    print("    ✗ Ставка не найдена")
            else:
                print(f"    ✗ Ошибка загрузки: {response.status_code}")
                
        except Exception as e:
            print(f"    ✗ Ошибка: {e}")
    
    def parse_vtb(self):
        """Парсинг ВТБ"""
        try:
            print("  Парсим ВТБ...")
            url = "https://www.vtb.ru/personal/ipoteka/"
            response = requests.get(url, headers=self.get_random_headers(), timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                text = soup.get_text()
                rate = self.extract_rate(text)
                
                if rate:
                    self.all_rates['ВТБ'] = rate
                    print(f"    ✓ ВТБ: {rate}%")
                else:
                    print("    ✗ Ставка не найдена")
            else:
                print(f"    ✗ Ошибка загрузки: {response.status_code}")
                
        except Exception as e:
            print(f"    ✗ Ошибка: {e}")
    
    def parse_alfa(self):
        """Парсинг Альфа-Банка"""
        try:
            print("  Парсим Альфа-Банк...")
            url = "https://alfabank.ru/get-money/mortgage/"
            response = requests.get(url, headers=self.get_random_headers(), timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                text = soup.get_text()
                rate = self.extract_rate(text)
                
                if rate:
                    self.all_rates['Альфа-Банк'] = rate
                    print(f"    ✓ Альфа-Банк: {rate}%")
                else:
                    print("    ✗ Ставка не найдена")
            else:
                print(f"    ✗ Ошибка загрузки: {response.status_code}")
                
        except Exception as e:
            print(f"    ✗ Ошибка: {e}")
    
    def parse_domrf(self):
        """Парсинг Дом.РФ"""
        try:
            print("  Парсим Дом.РФ...")
            url = "https://xn--h1alcedd.xn--d1aqf.xn--p1ai/mortgage/"
            response = requests.get(url, headers=self.get_random_headers(), timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                text = soup.get_text()
                rate = self.extract_rate(text)
                
                if rate:
                    self.all_rates['Банк ДОМ.РФ'] = rate
                    print(f"    ✓ Дом.РФ: {rate}%")
                else:
                    print("    ✗ Ставка не найдена")
            else:
                print(f"    ✗ Ошибка загрузки: {response.status_code}")
                
        except Exception as e:
            print(f"    ✗ Ошибка: {e}")
    
    def parse_banki_ru(self):
        """Парсинг агрегатора Банки.ру"""
        try:
            print("  Парсим Банки.ру...")
            url = "https://www.banki.ru/products/ipoteka/"
            response = requests.get(url, headers=self.get_random_headers(), timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                # Ищем блоки с банками
                bank_blocks = soup.find_all('div', class_=re.compile('product-item|bank-item'))
                
                for block in bank_blocks[:10]:  # Первые 10 банков
                    text = block.get_text()
                    bank_name_match = re.search(r'([А-Я][а-я]+(?:\s+[А-Я][а-я]+)*)', text)
                    rate = self.extract_rate(text)
                    
                    if bank_name_match and rate:
                        bank_name = bank_name_match.group(1).strip()
                        # Сохраняем, если ставка ниже текущей для этого банка
                        if bank_name in self.all_rates:
                            self.all_rates[bank_name] = min(self.all_rates[bank_name], rate)
                        else:
                            self.all_rates[bank_name] = rate
                
                print(f"    ✓ Найдено банков: {len(bank_blocks)}")
            else:
                print(f"    ✗ Ошибка загрузки: {response.status_code}")
                
        except Exception as e:
            print(f"    ✗ Ошибка: {e}")
    
    def parse_with_javascript(self, url, selector):
        """
        Для сайтов с JavaScript (использует requests-html)
        """
        try:
            session = HTMLSession()
            response = session.get(url, headers=self.get_random_headers(), timeout=15)
            response.html.render(timeout=20, sleep=3)  # Ждем выполнения JS
            
            elements = response.html.find(selector)
            if elements:
                return elements[0].text
            return None
            
        except Exception as e:
            print(f"    ✗ Ошибка JS парсинга: {e}")
            return None
        finally:
            session.close()
    
    def collect_all_rates(self):
        """Запускает все парсеры"""
        print("  Запускаем умный парсинг...")
        
        # Парсим конкретные банки
        self.parse_sber()
        time.sleep(2)  # Задержка, чтобы не забанили
        self.parse_vtb()
        time.sleep(2)
        self.parse_alfa()
        time.sleep(2)
        self.parse_domrf()
        time.sleep(2)
        
        # Парсим агрегаторы
        self.parse_banki_ru()
        time.sleep(2)
        
        # Фильтруем слишком низкие ставки (льготные программы)
        filtered_rates = {}
        for bank, rate in self.all_rates.items():
            if rate < 5:  # Пропускаем льготные ставки
                print(f"    ⚠ Пропущена льготная ставка {bank}: {rate}%")
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

📊 <b>Все банки (реальные ставки с сайтов):</b>

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
🔄 Данные: парсинг официальных сайтов и агрегаторов
🤖 Режим: умный парсинг
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
    
    # Парсинг
    print("\n🔍 НАЧАЛО ПАРСИНГА")
    parser = SmartMortgageParser()
    rates = parser.collect_all_rates()
    
    print(f"\n📊 ИТОГО: {len(rates)} банков")
    
    # Формирование сообщения
    print("\n✏️ ФОРМИРОВАНИЕ СООБЩЕНИЯ")
    message = format_message(rates)
    
    # Отправка
    print("\n📤 ОТПРАВКА В КАНАЛ")
    send_to_channel(message)
    
    print("\n" + "=" * 50)
    print("✅ БОТ ЗАВЕРШИЛ РАБОТУ")
    print("=" * 50)

if __name__ == "__main__":
    main()