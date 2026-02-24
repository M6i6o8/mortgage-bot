"""
Ипотечный бот - ПОЛНЫЙ АВТОПИЛОТ с telegram-pm
Запуск на GitHub Actions с Python 3.12
"""

import requests
import re
from datetime import datetime
import os
import sqlite3
from telegram_pm.run import run_tpm

# ===== НАСТРОЙКИ =====
BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
CHANNEL_ID = os.environ.get('CHANNEL_ID', '')

# ===== ПАРСЕР TELEGRAM-КАНАЛОВ =====
class TelegramParser:
    def __init__(self):
        self.db_path = "telegram.db"
        self.channels = ["banki_ru", "ipoteka_rus", "tbank_news"]
        
        # Словарь банков и их паттернов
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
        
    def parse_channels(self):
        """Парсит Telegram-каналы через telegram-pm"""
        print("  📡 Парсим Telegram-каналы через telegram-pm...")
        
        try:
            # Запускаем telegram-pm
            run_tpm(
                channels=self.channels,
                db_path=self.db_path,
                tg_iteration_in_preview_count=2,  # ~40 сообщений с канала
                verbose=False
            )
            
            # Подключаемся к базе
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            found_rates = {}
            
            # Для каждого канала проверяем сообщения
            for channel in self.channels:
                try:
                    # Проверяем, есть ли таблица
                    cursor.execute(f"""
                        SELECT name FROM sqlite_master 
                        WHERE type='table' AND name='{channel}'
                    """)
                    
                    if not cursor.fetchone():
                        continue
                    
                    # Получаем последние 30 сообщений
                    cursor.execute(f"""
                        SELECT text, date FROM "{channel}" 
                        ORDER BY date DESC LIMIT 30
                    """)
                    
                    messages = cursor.fetchall()
                    
                    for text, date in messages:
                        if not text:
                            continue
                        
                        # Ищем ставку (число с %)
                        rate_matches = re.findall(r'(\d+[.,]\d+)%', text)
                        if not rate_matches:
                            continue
                        
                        rate = float(rate_matches[0].replace(',', '.'))
                        
                        # Проверяем все паттерны банков
                        for bank_name, pattern in self.bank_patterns.items():
                            if re.search(pattern, text, re.IGNORECASE):
                                if bank_name not in found_rates or rate < found_rates[bank_name]:
                                    found_rates[bank_name] = rate
                                    print(f"      ✅ {bank_name}: {rate}% (из @{channel})")
                                    
                except Exception as e:
                    continue
            
            conn.close()
            
            # Удаляем базу после использования
            try:
                os.remove(self.db_path)
            except:
                pass
            
            return found_rates
            
        except Exception as e:
            print(f"    ⚠️ Ошибка telegram-pm: {e}")
            return {}

# ===== ОСНОВНОЙ ПАРСЕР =====
class AutoParser:
    def __init__(self):
        self.telegram_parser = TelegramParser()
        self.all_rates = {}
    
    def collect_all_rates(self):
        print("\n  🚀 ЗАПУСК АВТОМАТИЧЕСКОГО СБОРА")
        
        # Парсим Telegram-каналы
        telegram_rates = self.telegram_parser.parse_channels()
        
        # Добавляем найденные ставки
        for bank, rate in telegram_rates.items():
            self.all_rates[bank] = rate
        
        # Добавляем базовые ставки для банков, которых нет
        for bank, rate in self.telegram_parser.base_rates.items():
            if bank not in self.all_rates:
                self.all_rates[bank] = rate
                print(f"    ➕ {bank}: {rate}% (базовая)")
        
        print(f"\n  ✅ ВСЕГО БАНКОВ: {len(self.all_rates)}")
        return self.all_rates

# ===== ФОРМАТИРОВАНИЕ =====
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
🔄 Источник: Telegram-каналы (telegram-pm)
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
    print("🚀 ИПОТЕЧНЫЙ БОТ - TELEGRAM-PM ВЕРСИЯ")
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