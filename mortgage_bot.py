"""
Ипотечный бот - ПРОСТАЯ RSS-ВЕРСИЯ
Использует публичные RSS-мосты для Telegram
"""

import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
import os
import time

# ===== НАСТРОЙКИ =====
BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
CHANNEL_ID = os.environ.get('CHANNEL_ID', '')

# ===== RSS-МОСТЫ ДЛЯ TELEGRAM =====
class TelegramRSSParser:
    def __init__(self):
        # Каналы и их RSS-ссылки (рабочие на 2026 год)
        self.channels = {
            'banki_ru': [
                'https://rsshub.app/telegram/channel/banki_ru',
                'https://tg.i-c-a.su/rss/banki_ru.xml',
                'https://rss.bring10.com/telegram/channel/banki_ru'
            ],
            'ipoteka_rus': [
                'https://rsshub.app/telegram/channel/ipoteka_rus',
                'https://tg.i-c-a.su/rss/ipoteka_rus.xml',
                'https://rss.bring10.com/telegram/channel/ipoteka_rus'
            ],
            'tbank_news': [
                'https://rsshub.app/telegram/channel/tbank_news',
                'https://tg.i-c-a.su/rss/tbank_news.xml',
                'https://rss.bring10.com/telegram/channel/tbank_news'
            ]
        }
        
        # Паттерны банков
        self.bank_patterns = {
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
        
        # Базовые ставки
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
    
    def fetch_rss(self, url):
        """Загружает RSS-ленту"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'
            }
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.text
        except:
            pass
        return None
    
    def parse_rss_items(self, xml_content):
        """Парсит RSS и возвращает список сообщений"""
        try:
            soup = BeautifulSoup(xml_content, 'xml')
            items = []
            
            # Ищем item или entry
            for item in soup.find_all(['item', 'entry']):
                title = item.find('title')
                description = item.find('description')
                content = item.find('content') or item.find('content:encoded')
                
                text = ''
                if title and title.text:
                    text += title.text + ' '
                if description and description.text:
                    text += description.text + ' '
                if content and content.text:
                    text += content.text
                
                if text.strip():
                    items.append(text.strip())
            
            return items[:20]  # Последние 20 сообщений
        except:
            return []
    
    def extract_rates_from_text(self, text, channel_name):
        """Ищет в тексте ставки и банки"""
        found = {}
        
        # Ищем все ставки в тексте
        rate_matches = re.findall(r'(\d+[.,]\d+)%', text)
        if not rate_matches:
            return found
        
        # Берем первую ставку
        rate = float(rate_matches[0].replace(',', '.'))
        
        # Проверяем каждый банк
        for bank_name, pattern in self.bank_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                if bank_name not in found or rate < found[bank_name]:
                    found[bank_name] = rate
                    print(f"      ✅ {bank_name}: {rate}% (из @{channel_name})")
        
        return found
    
    def parse_all_channels(self):
        """Парсит все каналы через RSS"""
        print("  📡 Парсим Telegram-каналы через RSS...")
        
        all_rates = {}
        
        for channel_name, urls in self.channels.items():
            print(f"    📍 @{channel_name}:")
            
            # Пробуем каждый URL для канала
            for url in urls:
                print(f"      Пробуем {url[:50]}...")
                xml_content = self.fetch_rss(url)
                
                if xml_content:
                    messages = self.parse_rss_items(xml_content)
                    print(f"        Найдено сообщений: {len(messages)}")
                    
                    # Ищем ставки в каждом сообщении
                    for msg in messages:
                        rates = self.extract_rates_from_text(msg, channel_name)
                        for bank, rate in rates.items():
                            if bank not in all_rates or rate < all_rates[bank]:
                                all_rates[bank] = rate
                    
                    if messages:
                        break  # Если нашли сообщения, другие URL не пробуем
                else:
                    print(f"        ❌ Не загрузился")
            
            time.sleep(1)  # Пауза между каналами
        
        return all_rates

# ===== ОСНОВНОЙ КЛАСС =====
class MortgageBot:
    def __init__(self):
        self.rss_parser = TelegramRSSParser()
        self.rates = {}
    
    def collect_rates(self):
        print("\n  🚀 ЗАПУСК СБОРА СТАВОК")
        
        # Парсим Telegram
        telegram_rates = self.rss_parser.parse_all_channels()
        
        # Добавляем найденные ставки
        for bank, rate in telegram_rates.items():
            self.rates[bank] = rate
        
        # Добавляем базовые ставки для остальных
        for bank, rate in self.rss_parser.base_rates.items():
            if bank not in self.rates:
                self.rates[bank] = rate
                print(f"    ➕ {bank}: {rate}% (базовая)")
        
        print(f"\n  ✅ ВСЕГО БАНКОВ: {len(self.rates)}")
        return self.rates

# ===== ФОРМАТИРОВАНИЕ =====
def format_message(rates):
    if not rates:
        return "😔 Не удалось получить ставки"
    
    sorted_rates = sorted(rates.items(), key=lambda x: x[1])
    min_bank, min_rate = sorted_rates[0]
    
    text = f"""
🏠 <b>Ипотека сегодня: МИНИМАЛЬНАЯ СТАВКА</b>

🔥 <b>Лучшее предложение:</b>
• {min_bank} — <b>{min_rate}%</b>

📊 <b>Все банки:</b>

"""
    
    for i, (bank, rate) in enumerate(sorted_rates, 1):
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
📊 Всего банков: {len(sorted_rates)}
🔄 Источник: RSS-мосты Telegram
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
        else:
            print(f"  ❌ Ошибка: {response.text}")
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")

# ===== ГЛАВНАЯ =====
def main():
    print("=" * 60)
    print("🚀 ИПОТЕЧНЫЙ БОТ - RSS-ВЕРСИЯ")
    print(f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print("=" * 60)
    
    if not BOT_TOKEN or not CHANNEL_ID:
        print("❌ Ошибка: не заданы BOT_TOKEN или CHANNEL_ID")
        return
    
    bot = MortgageBot()
    rates = bot.collect_rates()
    
    message = format_message(rates)
    send_to_channel(message)
    
    print("\n✅ ГОТОВО")

if __name__ == "__main__":
    main()