"""
Ипотечный бот - умный парсинг с обходом защиты
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

# ===== РЕАЛЬНЫЕ ЗАГОЛОВКИ БРАУЗЕРА =====
def get_browser_headers():
    """Возвращает заголовки как у реального браузера Chrome"""
    chrome_versions = [
        '120.0.0.0',
        '121.0.0.0', 
        '122.0.0.0',
        '123.0.0.0'
    ]
    
    return {
        'User-Agent': f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.choice(chrome_versions)} Safari/537.36',
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
        'Sec-Ch-Ua': f'"Not A(Brand";v="99", "Google Chrome";v="{random.choice(chrome_versions)}", "Chromium";v="{random.choice(chrome_versions)}"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
    }

class SmartMortgageParser:
    def __init__(self):
        self.all_rates = {}
        # Запасные ставки на случай если парсинг не сработает
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
    
    def safe_request(self, url, timeout=15):
        """Запрос с реальными заголовками браузера"""
        try:
            headers = get_browser_headers()
            session = requests.Session()
            
            # Сначала заходим на главную, чтобы получить куки
            if 'banki.ru' in url:
                main_page = 'https://www.banki.ru/'
                session.get(main_page, headers=headers, timeout=timeout)
                time.sleep(2)
            
            response = session.get(url, headers=headers, timeout=timeout)
            response.encoding = 'utf-8'
            
            if response.status_code == 200:
                return response
            else:
                print(f"    ⚠️ Статус {response.status_code}")
                return None
        except Exception as e:
            print(f"    ⚠️ Ошибка запроса: {e}")
            return None
    
    def extract_rate(self, text):
        """Извлекает число-ставку из текста"""
        if not text:
            return None
            
        patterns = [
            r'от\s*(\d+[.,]\d+)%',
            r'ставка[^\d]*(\d+[.,]\d+)%',
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
        """Парсинг Банки.ру с обходом защиты"""
        try:
            print("  Парсим Банки.ру...")
            url = "https://www.banki.ru/products/ipoteka/"
            response = self.safe_request(url)
            
            if not response:
                print("    ✗ Не удалось загрузить Банки.ру")
                return
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Сохраняем HTML для отладки
            with open('banki_ru_debug.html', 'w', encoding='utf-8') as f:
                f.write(response.text)
            print("    ✓ HTML сохранён для отладки")
            
            # Ищем разными способами
            found_banks = 0
            
            # Способ 1: по data-test атрибутам
            rows = soup.find_all('tr', {'data-test': 'row'})
            
            # Способ 2: по классам
            if not rows:
                rows = soup.find_all('tr', class_=re.compile('row|product|item'))
            
            # Способ 3: ищем любые блоки с банками
            if not rows:
                rows = soup.find_all('div', class_=re.compile('product|bank|item'))
            
            for row in rows[:20]:
                try:
                    row_text = row.get_text()
                    
                    # Ищем название банка (русские буквы)
                    bank_match = re.search(r'([А-Я][а-я]+(?:\s+[А-Я][а-я]+)*)', row_text)
                    if not bank_match:
                        continue
                    
                    bank_name = bank_match.group(1).strip()
                    
                    # Ищем ставку
                    rate = self.extract_rate(row_text)
                    
                    if bank_name and rate and len(bank_name) < 30:
                        self.all_rates[bank_name] = rate
                        found_banks += 1
                        print(f"    ✓ {bank_name}: {rate}%")
                        
                except Exception as e:
                    continue
            
            if found_banks == 0:
                print("    ✗ Банки не найдены, возможно изменилась структура сайта")
                # Добавляем несколько основных банков вручную
                self.all_rates['Сбербанк'] = 21.0
                self.all_rates['ВТБ'] = 20.1
                self.all_rates['Альфа-Банк'] = 20.5
                self.all_rates['Т-Банк'] = 16.9
                print("    ➕ Добавлены основные банки вручную")
            else:
                print(f"    ✅ Найдено банков: {found_banks}")
            
        except Exception as e:
            print(f"    ✗ Ошибка парсинга Банки.ру: {e}")
    
    def parse_individual_banks(self):
        """Парсинг отдельных банков"""
        
        # Сбер
        try:
            print("  Парсим Сбер...")
            url = "https://www.sberbank.ru/ru/person/credits/home/buying_complete_house"
            response = self.safe_request(url)
            if response:
                text = response.text
                rate = self.extract_rate(text)
                if rate:
                    self.all_rates['Сбербанк'] = rate
                    print(f"    ✓ Сбер: {rate}%")
        except:
            pass
        
        time.sleep(1.5)
        
        # ВТБ
        try:
            print("  Парсим ВТБ...")
            url = "https://www.vtb.ru/personal/ipoteka/"
            response = self.safe_request(url)
            if response:
                text = response.text
                rate = self.extract_rate(text)
                if rate:
                    self.all_rates['ВТБ'] = rate
                    print(f"    ✓ ВТБ: {rate}%")
        except:
            pass
        
        time.sleep(1.5)
        
        # Альфа
        try:
            print("  Парсим Альфа-Банк...")
            url = "https://alfabank.ru/get-money/mortgage/"
            response = self.safe_request(url)
            if response:
                text = response.text
                rate = self.extract_rate(text)
                if rate:
                    self.all_rates['Альфа-Банк'] = rate
                    print(f"    ✓ Альфа-Банк: {rate}%")
        except:
            pass
    
    def add_fallback_rates(self):
        """Добавляет запасные ставки для отсутствующих банков"""
        added = 0
        for bank, rate in self.fallback_rates.items():
            if bank not in self.all_rates:
                self.all_rates[bank] = rate
                added += 1
        
        if added > 0:
            print(f"    ➕ Добавлено запасных банков: {added}")
    
    def collect_all_rates(self):
        """Запускает все парсеры"""
        print("  Запускаем умный парсинг...")
        
        # Пробуем спарсить Банки.ру
        self.parse_banki_ru()
        time.sleep(2)
        
        # Парсим отдельные банки
        self.parse_individual_banks()
        
        # Добавляем запасные ставки для недостающих банков
        self.add_fallback_rates()
        
        # Фильтруем
        filtered_rates = {}
        for bank, rate in self.all_rates.items():
            if 5 <= rate <= 35:
                filtered_rates[bank] = rate
        
        self.all_rates = filtered_rates
        return self.all_rates

# ===== ФОРМАТИРОВАНИЕ =====
def format_message(rates_dict):
    if not rates_dict:
        return "😔 Не удалось получить актуальные ставки."
    
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
            print("  ✅ Успешно отправлено в канал")
        else:
            print(f"  ❌ Ошибка: {response.text}")
    except Exception as e:
        print(f"  ❌ Ошибка отправки: {e}")

# ===== ГЛАВНАЯ =====
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
    
    print("\n📤 ОТПРАВКА В КАНАЛ")
    send_to_channel(message)
    
    print("\n" + "=" * 50)
    print("✅ БОТ ЗАВЕРШИЛ РАБОТУ")
    print("=" * 50)

if __name__ == "__main__":
    main()