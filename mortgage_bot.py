"""
Ипотечный бот - ФИНАЛЬНАЯ ВЕРСИЯ с Telethon
Без проверки номера, работает через файл сессии
Запуск на GitHub Actions
"""

import os
import re
import asyncio
import requests
from datetime import datetime
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

# ===== НАСТРОЙКИ =====
BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
CHANNEL_ID = os.environ.get('CHANNEL_ID', '')

# Telegram API credentials (публичные)
API_ID = 2040
API_HASH = 'b18441a1ff607e10a989891a5462e627'

# Каналы для парсинга (только существующие)
TARGET_CHANNELS = [
    'tbank_news',        # Т-Банк
    'alfabank',          # Альфа
    'gazprombank',       # Газпромбанк
    'ipoteka_stavka',    # Ставки по ипотеке
    'ipoteka_rus',       # Ипотека в России
    'ipoteka_segodnya',  # Ипотека сегодня
    'realty_news',       # Новости недвижимости
    'banki_today',       # Банки сегодня
]

# Базовые ставки (подстраховка)
BASE_RATES = {
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

# Паттерны для определения банков
BANK_PATTERNS = {
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

class TelegramParser:
    def __init__(self):
        self.client = TelegramClient('mortgage_bot_session', API_ID, API_HASH)
        self.found_rates = {}
    
    def extract_rate(self, text):
        """Извлекает ставку из текста"""
        if not text:
            return None
        rate_match = re.search(r'(\d+[.,]\d+)%', text)
        if rate_match:
            try:
                return float(rate_match.group(1).replace(',', '.'))
            except:
                return None
        return None
    
    def identify_bank(self, text, channel):
        """Определяет банк по тексту или каналу"""
        # Сначала ищем по паттернам в тексте
        for bank_name, pattern in BANK_PATTERNS.items():
            if re.search(pattern, text, re.IGNORECASE):
                return bank_name
        
        # Если не нашли, определяем по имени канала
        channel_lower = channel.lower()
        if 'sber' in channel_lower:
            return 'Сбербанк'
        elif 'vtb' in channel_lower:
            return 'ВТБ'
        elif 'alfa' in channel_lower:
            return 'Альфа-Банк'
        elif 'tbank' in channel_lower or 'tinkoff' in channel_lower:
            return 'Т-Банк'
        elif 'gazprom' in channel_lower:
            return 'Газпромбанк'
        elif 'domrf' in channel_lower:
            return 'Банк ДОМ.РФ'
        
        return None
    
    async def parse_channel(self, channel_username):
        """Парсит один канал"""
        try:
            print(f"    📍 Парсим @{channel_username}")
            
            # Получаем сущность канала
            entity = await self.client.get_entity(channel_username)
            
            # Получаем последние 30 сообщений
            messages = await self.client.get_messages(entity, limit=30)
            
            channel_found = 0
            
            for msg in messages:
                if not msg.text:
                    continue
                
                # Извлекаем ставку
                rate = self.extract_rate(msg.text)
                if not rate:
                    continue
                
                # Определяем банк
                bank = self.identify_bank(msg.text, channel_username)
                if not bank:
                    continue
                
                # Сохраняем, если ставка ниже текущей
                if bank not in self.found_rates or rate < self.found_rates[bank]:
                    self.found_rates[bank] = rate
                    channel_found += 1
                    print(f"        ✅ {bank}: {rate}%")
            
            if channel_found == 0:
                print(f"        ⚠️ Ставок не найдено")
                
        except Exception as e:
            print(f"        ❌ Ошибка: {str(e)[:100]}")
    
    async def run(self):
        """Запускает парсинг всех каналов"""
        print("  📡 Подключаемся к Telegram API...")
        
        try:
            # Подключаемся с существующей сессией
            await self.client.connect()
            
            # Проверяем, авторизованы ли мы
            if not await self.client.is_user_authorized():
                print("    ❌ Ошибка: нет авторизации. Файл сессии не работает")
                return {}
            else:
                print("    ✅ Уже авторизованы (через файл сессии)")
            
            # Парсим каждый канал
            for channel in TARGET_CHANNELS:
                await self.parse_channel(channel)
                await asyncio.sleep(1)  # Пауза между каналами
            
            # Отключаемся
            await self.client.disconnect()
            
            return self.found_rates
            
        except Exception as e:
            print(f"    ❌ Критическая ошибка: {e}")
            return {}

def format_message(found_rates):
    """Форматирует сообщение для канала"""
    # Объединяем с базовыми ставками
    all_rates = BASE_RATES.copy()
    for bank, rate in found_rates.items():
        all_rates[bank] = rate
    
    # Сортируем по ставке
    rates_list = [(bank, rate) for bank, rate in all_rates.items()]
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
    
    # Добавляем статистику
    telegram_count = len(found_rates)
    
    text += f"""

📅 {datetime.now().strftime('%d.%m.%Y %H:%M')} (МСК)
📊 Всего банков: {len(rates_list)}
🤖 Найдено в Telegram: {telegram_count}
🔄 Источник: MTProto API (Telethon)
"""
    
    return text

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
            print("  ✅ Отправлено в канал!")
            return True
        else:
            print(f"  ❌ Ошибка: {response.text}")
            return False
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
        return False

def main():
    print("=" * 60)
    print("🚀 ИПОТЕЧНЫЙ БОТ - TELEGRAM API (ФИНАЛ)")
    print(f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print("=" * 60)
    
    # Проверяем наличие необходимых переменных
    if not BOT_TOKEN:
        print("❌ Ошибка: не задан BOT_TOKEN")
        return
    
    if not CHANNEL_ID:
        print("❌ Ошибка: не задан CHANNEL_ID")
        return
    
    print(f"📢 Канал: {CHANNEL_ID}")
    
    # Создаём и запускаем парсер
    parser = TelegramParser()
    
    # Запускаем асинхронную функцию
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        found_rates = loop.run_until_complete(parser.run())
        
        # Формируем и отправляем сообщение
        message = format_message(found_rates)
        send_to_channel(message)
        
        print("\n✅ ГОТОВО")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
    finally:
        loop.close()

if __name__ == "__main__":
    main()