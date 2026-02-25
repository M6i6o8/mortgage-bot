"""
Ипотечный бот - С ОТОБРАЖЕНИЕМ ИЗМЕНЕНИЙ
Показывает, какие ставки изменились за день
"""

import os
import re
import json
import asyncio
import requests
from datetime import datetime, timedelta
from telethon import TelegramClient

# ===== НАСТРОЙКИ =====
BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
CHANNEL_ID = os.environ.get('CHANNEL_ID', '')

# Telegram API credentials
API_ID = 2040
API_HASH = 'b18441a1ff607e10a989891a5462e627'

# Файлы для хранения данных
HISTORY_FILE = 'rates_history.json'
LAST_STATE_FILE = 'last_state.json'  # Для сравнения с предыдущим днём

# Каналы для парсинга
TARGET_CHANNELS = [
    'tbank_news',
    'alfabank',
    'gazprombank',
    'ipoteka_stavka',
    'ipoteka_rus',
    'ipoteka_segodnya',
]

# Начальные базовые ставки
INITIAL_RATES = {
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

# Паттерны банков
BANK_PATTERNS = {
    'Сбербанк': r'сбер[банк]*|sber|сбербанк',
    'ВТБ': r'втб|vtb|втб банк',
    'Альфа-Банк': r'альфа|alfa|альфа-банк',
    'Т-Банк': r'т[- ]?банк|тинькофф|tbank|tinkoff',
    'Газпромбанк': r'газпром|gazprombank|газпромбанк',
    'Россельхозбанк': r'россельхоз|рсхб|rshb|сельхозбанк',
    'Промсвязьбанк': r'промсвязь|псб|psb|промсвязьбанк',
    'Уралсиб': r'уралсиб|uralsib',
    'Банк Открытие': r'открытие|otkritie',
    'Совкомбанк': r'совком|sovcombank|совкомбанк',
    'МТС Банк': r'мтс|mts|мтс банк',
    'Банк ДОМ.РФ': r'дом\.рф|domrf|дом рф',
    'Банк Санкт-Петербург': r'санкт-петербург|bspb|банк спб',
    'Транскапиталбанк': r'транскапитал|tcb|ткб',
    'ВБРР': r'вбрр|vbrr',
}

class RateHistory:
    """Класс для работы с историей ставок"""
    
    def __init__(self):
        self.history = self.load(HISTORY_FILE)
        self.last_state = self.load(LAST_STATE_FILE)
        self.changes = {}  # Изменения с прошлого раза
    
    def load(self, filename):
        """Загружает данные из файла"""
        if os.path.exists(filename):
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save(self, filename, data):
        """Сохраняет данные в файл"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def update(self, bank, rate):
        """Обновляет ставку для банка, если она ниже"""
        bank_key = bank.strip()
        current = self.history.get(bank_key)
        
        if current is None or rate < current:
            self.history[bank_key] = rate
            return True
        return False
    
    def get_final_rates(self):
        """Возвращает финальные ставки (история + начальные)"""
        final = {}
        
        # Сначала добавляем все из истории
        for bank, rate in self.history.items():
            final[bank] = rate
        
        # Добавляем начальные для банков, которых нет в истории
        for bank, rate in INITIAL_RATES.items():
            if bank not in final:
                final[bank] = rate
                print(f"    📊 Начальная ставка для {bank}: {rate}%")
        
        return final
    
    def detect_changes(self):
        """Определяет изменения с прошлого запуска"""
        self.changes = {}
        current_rates = self.get_final_rates()
        
        for bank, current_rate in current_rates.items():
            last_rate = self.last_state.get(bank)
            
            if last_rate is None:
                # Новый банк
                self.changes[bank] = {
                    'old': None,
                    'new': current_rate,
                    'type': 'new'
                }
            elif abs(current_rate - last_rate) > 0.01:  # Ставка изменилась
                self.changes[bank] = {
                    'old': last_rate,
                    'new': current_rate,
                    'type': 'changed'
                }
        
        return self.changes
    
    def save_state(self):
        """Сохраняет текущее состояние для сравнения в будущем"""
        self.save(LAST_STATE_FILE, self.get_final_rates())
        self.save(HISTORY_FILE, self.history)

class TelegramParser:
    def __init__(self):
        self.client = TelegramClient('mortgage_bot_session', API_ID, API_HASH)
        self.rate_history = RateHistory()
        self.new_finds = 0
    
    def extract_rate(self, text):
        """Извлекает ставку из текста с фильтрацией"""
        if not text:
            return None
        
        rate_matches = re.findall(r'(\d+[.,]\d+)%', text)
        if not rate_matches:
            return None
        
        try:
            rate = float(rate_matches[0].replace(',', '.'))
            
            # Фильтруем только реалистичные рыночные ставки
            if 10 <= rate <= 30:
                return rate
            else:
                if rate < 10:
                    print(f"          🟡 Отброшено (слишком низкая): {rate}%")
                elif rate > 30:
                    print(f"          🔴 Отброшено (слишком высокая): {rate}%")
                return None
        except:
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
            
            entity = await self.client.get_entity(channel_username)
            messages = await self.client.get_messages(entity, limit=50)
            
            channel_found = 0
            
            for msg in messages:
                if not msg.text:
                    continue
                
                rate = self.extract_rate(msg.text)
                if not rate:
                    continue
                
                bank = self.identify_bank(msg.text, channel_username)
                if not bank:
                    continue
                
                if self.rate_history.update(bank, rate):
                    self.new_finds += 1
                    print(f"        ✅ НОВАЯ МИНИМАЛЬНАЯ СТАВКА! {bank}: {rate}%")
                else:
                    print(f"        ℹ️ {bank}: {rate}% (выше текущей)")
            
            if channel_found == 0:
                print(f"        ⚠️ Новых ставок не найдено")
                
        except Exception as e:
            if "username" in str(e) or "No user" in str(e):
                print(f"        ❌ Канал @{channel_username} не существует")
            else:
                print(f"        ❌ Ошибка: {str(e)[:100]}")
    
    async def run(self):
        """Запускает парсинг всех каналов"""
        print("  📡 Подключаемся к Telegram API...")
        
        try:
            await self.client.connect()
            
            if not await self.client.is_user_authorized():
                print("    ❌ Ошибка: нет авторизации")
                return
            else:
                print("    ✅ Уже авторизованы")
            
            print(f"\n  🔍 Начинаем парсинг {len(TARGET_CHANNELS)} каналов...")
            print(f"  📊 Текущая история: {len(self.rate_history.history)} банков")
            
            for channel in TARGET_CHANNELS:
                await self.parse_channel(channel)
                await asyncio.sleep(1.5)
            
            # Определяем изменения
            changes = self.rate_history.detect_changes()
            
            # Сохраняем обновлённые данные
            self.rate_history.save_state()
            
            print(f"\n  📊 Найдено новых минимальных ставок: {self.new_finds}")
            print(f"  📊 Всего в истории: {len(self.rate_history.history)} банков")
            print(f"  📊 Изменений с прошлого раза: {len(changes)}")
            
            await self.client.disconnect()
            
            return changes
            
        except Exception as e:
            print(f"    ❌ Критическая ошибка: {e}")
            return {}

def format_changes(changes):
    """Форматирует список изменений для отображения"""
    if not changes:
        return ""
    
    text = "\n📊 <b>Изменения за сутки:</b>\n"
    
    for bank, data in changes.items():
        if data['type'] == 'new':
            text += f"➕ {bank}: <b>{data['new']}%</b> (новый банк)\n"
        elif data['type'] == 'changed':
            old = data['old']
            new = data['new']
            if new < old:
                text += f"📉 {bank}: {old}% → <b>{new}%</b> (снижение)\n"
            else:
                text += f"📈 {bank}: {old}% → <b>{new}%</b> (повышение)\n"
    
    return text

def format_message(rate_history, changes):
    """Формирует сообщение для канала"""
    final_rates = rate_history.get_final_rates()
    
    # Сортируем по ставке
    rates_list = [(bank, rate) for bank, rate in final_rates.items()]
    rates_list.sort(key=lambda x: x[1])
    
    min_bank, min_rate = rates_list[0]
    
    # Формируем сообщение
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
    
    # Добавляем блок с изменениями
    text += format_changes(changes)
    
    # Добавляем статистику
    history_count = len(rate_history.history)
    
    text += f"""

📅 {datetime.now().strftime('%d.%m.%Y %H:%M')} (МСК)
📊 Всего банков: {len(rates_list)}
🤖 В истории: {history_count}
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
    print("🚀 ИПОТЕЧНЫЙ БОТ - С ОТОБРАЖЕНИЕМ ИЗМЕНЕНИЙ")
    print(f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print("=" * 60)
    
    if not BOT_TOKEN or not CHANNEL_ID:
        print("❌ Ошибка: не заданы токены")
        return
    
    # Создаём и запускаем парсер
    parser = TelegramParser()
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        changes = loop.run_until_complete(parser.run())
        
        # Формируем и отправляем сообщение
        message = format_message(parser.rate_history, changes)
        send_to_channel(message)
        
        print("\n✅ ГОТОВО")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
    finally:
        loop.close()

if __name__ == "__main__":
    main()