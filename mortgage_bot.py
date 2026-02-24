"""
Ипотечный бот - ПОЛНЫЙ АВТОПИЛОТ с RSS-парсингом Telegram-каналов
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

# ===== ПАРСЕР TELEGRAM-КАНАЛОВ ЧЕРЕЗ RSS =====
class TelegramRSSParser:
    def __init__(self):
        self.channels = {
            'banki_ru': 'https://rsshub.app/telegram/channel/banki_ru',
            'ipoteka_rus': 'https://rsshub.app/telegram/channel/ipoteka_rus',
            'tbank_news': 'https://rsshub.app/telegram/channel/tbank_news'
        }
        
        # Резервные RSS-мосты
        self.backup_bridges = [
            'https://rss-bridge.org/bridge01/?action=display&bridge=TelegramBridge&channel=',
            'https://tg.i-c-a.su/rss/',
            'https://rss.telegram.org/'
        ]
    
    def get_random_headers(self):
        """Заголовки для запроса"""
        return {
            'User-Agent': random.choice([
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15',
            ])
        }
    
    def parse_channel_rss(self, channel_name, url):
        """Парсит RSS-ленту канала"""
        try:
            headers = self.get_random_headers()
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                return []
            
            soup = BeautifulSoup(response.text, 'xml')
            items = soup.find_all('item') or soup.find_all('entry')
            
            messages = []
            for item in items[:15]:  # Последние 15 сообщений
                title = item.find('title')
                description = item.find('description')
                pub_date = item.find('pubDate') or item.find('published')
                
                text = ''
                if title and title.text:
                    text += title.text + ' '
                if description and description.text:
                    text += description.text
                
                if text.strip():
                    messages.append({
                        'text': text,
                        'date': pub_date.text if pub_date else '',
                        'channel': channel_name
                    })
            
            return messages
            
        except Exception as e:
            print(f"    ⚠️ Ошибка RSS {channel_name}: {e}")
            return []
    
    def parse_all_channels(self):
        """Парсит все каналы и ищет ставки"""
        print("  📡 Парсим Telegram-каналы через RSS...")
        
        all_messages = []
        bank_rates = {}
        
        # Словарь банков и их паттернов
        bank_patterns = {
            'Сбербанк': r'сбер[банк]*|sber',
            'ВТБ': r'втб|vtb',
            'Альфа-Банк': r'альфа|alfa',
            'Т-Банк': r'т[- ]?банк|тинькофф|tbank|tinkoff',
            'Газпромбанк': r'газпром|gazprombank',
            'Россельхозбанк': r'россельхоз|рсхб|rshb',
            'Промсвязьбанк': r'промсвязь|псб|psb',
            'Уралсиб': r'уралсиб|uralsib',
            'Банк Открытие': r'открытие|otkritie',
            'Совкомбанк': r'совком|sovcombank',
            'МТС Банк': r'мтс|mts',
            'Банк ДОМ.РФ': r'дом\.рф|domrf',
            'Банк Санкт-Петербург': r'санкт-петербург|bspb',
            'Транскапиталбанк': r'транскапитал|tcb',
            'ВБРР': r'вбрр|vbrr',
        }
        
        # Парсим каждый канал
        for channel_name, url in self.channels.items():
            messages = self.parse_channel_rss(channel_name, url)
            all_messages.extend(messages)
            print(f"    📍 @{channel_name}: {len(messages)} сообщений")
        
        # Ищем ставки в сообщениях
        for msg in all_messages:
            text = msg['text'].lower()
            
            # Ищем ставку (число с %)
            rate_matches = re.findall(r'(\d+[.,]\d+)%', msg['text'])
            if not rate_matches:
                continue
            
            rate = float(rate_matches[0].replace(',', '.'))
            
            # Проверяем, какой банк упомянут
            for bank_name, pattern in bank_patterns.items():
                if re.search(pattern, text, re.IGNORECASE):
                    if bank_name not in bank_rates or rate < bank_rates[bank_name]:
                        bank_rates[bank_name] = rate
                        print(f"      ✅ {bank_name}: {rate}% (из @{msg['channel']})")
        
        return bank_rates

# ===== ОСНОВНОЙ ПАРСЕР =====
class AutoParser:
    def __init__(self):
        self.all_rates = {}
        self.telegram_parser = TelegramRSSParser()
        
        # Базовые ставки (на случай если ничего не спарсится)
        self.base_rates = {
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
    
    # ===== ГЛАВНЫЙ СБОР =====
    def collect_all_rates(self):
        print("\n  🚀 ЗАПУСК АВТОМАТИЧЕСКОГО СБОРА")
        
        # Парсим Telegram-каналы через RSS
        telegram_rates = self.telegram_parser.parse_all_channels()
        
        # Добавляем найденные ставки
        for bank, rate in telegram_rates.items():
            self.all_rates[bank] = rate
        
        # Добавляем базовые ставки для банков, которых нет
        for bank, rate in self.base_rates.items():
            if bank not in self.all_rates:
                self.all_rates[bank] = rate
                print(f"    ➕ {bank}: {rate}% (базовая)")
        
        print(f"\n  ✅ ВСЕГО БАНКОВ: {len(self.all_rates)}")
        return self.all_rates

# ===== ФОРМАТИРОВАНИЕ СООБЩЕНИЯ =====
def format_message(rates_dict):
    if not rates_dict:
        return "😔 Не удалось получить ставки"
    
    rates_list = [(bank, rate) for bank, rate in rates_dict.items()]
    rates_list.sort(key=lambda x: x[1])
    
    min_bank, min_rate = rates_list[0]
    
    text = f"""
🏠 <b>Ипотека сегодня: МИНИМАЛЬНАЯ СТАВКА</b>

🔥 <b>Лучшее предложение:</b>
• {min_bank} — <b>{min_rate}%</b>

📊 <b>Все банки:</b>

"""
    
    for i, (bank, rate) in enumerate(rates_list, 1):
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
📊 Всего банков: {len(rates_list)}
🔄 Источник: Telegram-каналы + база
"""
    
    return text

# ===== ОТПРАВКА В КАНАЛ =====
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
        else:
            print(f"  ❌ Ошибка: {response.text}")
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")

# ===== ГЛАВНАЯ =====
def main():
    print("=" * 60)
    print("🚀 ИПОТЕЧНЫЙ БОТ - АВТОПИЛОТ (RSS)")
    print(f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print("=" * 60)
    
    if not BOT_TOKEN or not CHANNEL_ID:
        print("❌ Ошибка: не заданы BOT_TOKEN или CHANNEL_ID")
        return
    
    parser = AutoParser()
    rates = parser.collect_all_rates()
    
    message = format_message(rates)
    send_to_channel(message)
    
    print("\n✅ ГОТОВО")

if __name__ == "__main__":
    main()