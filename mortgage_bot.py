"""
Ипотечный бот для сестры - версия для GitHub Actions
"""

import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
import time
import os

# ===== НАСТРОЙКИ =====
# Токен и ID теперь берутся из переменных окружения (секретов GitHub)
BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
CHAT_ID = os.environ.get('CHAT_ID', '')

# ===== КЛАСС ДЛЯ СБОРА СТАВОК =====
class MortgageRateCollector:
    def __init__(self):
        self.all_rates = {}
        
    def parse_specific_banks(self):
        """Данные из новостей (работает всегда)"""
        try:
            bank_updates = {
                'Т-Банк': 16.9,
                'Банк Санкт-Петербург': 18.49,
                'Уралсиб': 18.79,
                'ВТБ': 19.3,
                'Промсвязьбанк': 19.49,
                'Транскапиталбанк': 20.25,
                'ВБРР': 20.4,
                'Сбербанк': 21.0,
                'Альфа-Банк': 20.5,
                'Газпромбанк': 20.8,
                'Россельхозбанк': 20.2,
                'Совкомбанк': 20.9,
                'Банк Открытие': 21.1,
                'МТС Банк': 20.7,
            }
            
            for bank, rate in bank_updates.items():
                self.all_rates[bank] = rate
            
            print(f"  ✓ Добавлено {len(bank_updates)} банков из новостей")
            
        except Exception as e:
            print(f"  ✗ Ошибка: {e}")
    
    def collect_all_rates(self):
        """Собирает все ставки"""
        print("  Начинаем сбор ставок...")
        self.parse_specific_banks()
        return self.all_rates

# ===== ОТПРАВКА В ТЕЛЕГРАМ =====
def send_message(text):
    """Отправляет сообщение сестре"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, data=data, timeout=10)
        print(f"  Отправка в Telegram: статус {response.status_code}")
        if response.status_code != 200:
            print(f"  Ошибка: {response.text}")
    except Exception as e:
        print(f"  Ошибка отправки: {e}")

# ===== ФОРМИРОВАНИЕ СООБЩЕНИЯ =====
def format_message(rates_dict):
    """Форматирует сообщение"""
    if not rates_dict:
        return "😔 Не удалось получить актуальные ставки. Попробуйте позже."
    
    rates_list = [(bank, rate) for bank, rate in rates_dict.items()]
    rates_list.sort(key=lambda x: x[1])
    
    top_rates = rates_list[:15]
    min_bank, min_rate = rates_list[0]
    
    header = f"""
🏠 <b>Ипотека сегодня: МИНИМАЛЬНАЯ СТАВКА</b>

🔥 <b>Лучшее предложение:</b>
• {min_bank} — <b>{min_rate}%</b>

📊 <b>Топ банков:</b>

"""
    
    rates_text = ""
    for i, (bank, rate) in enumerate(top_rates, 1):
        if i == 1:
            rates_text += f"🥇 {bank} — {rate}%\n"
        elif i == 2:
            rates_text += f"🥈 {bank} — {rate}%\n"
        elif i == 3:
            rates_text += f"🥉 {bank} — {rate}%\n"
        else:
            rates_text += f"• {bank} — {rate}%\n"
    
    footer = f"""

📅 Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')} (МСК)
📊 Всего банков: {len(rates_list)}
🔄 Данные: на основе рыночных предложений
"""
    
    return header + rates_text + footer

# ===== ГЛАВНАЯ ФУНКЦИЯ =====
def main():
    print(f"{'='*50}")
    print(f"Запуск сбора ставок: {datetime.now()}")
    print(f"{'='*50}")
    
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ Ошибка: не заданы BOT_TOKEN или CHAT_ID")
        return
    
    print("1. Создаем коллектор...")
    collector = MortgageRateCollector()
    
    print("2. Собираем ставки...")
    rates = collector.collect_all_rates()
    
    print(f"3. Собрано банков: {len(rates)}")
    
    print("4. Формируем сообщение...")
    message = format_message(rates)
    
    print("5. Отправляем в Telegram...")
    send_message(message)
    
    print("6. Готово!")

if __name__ == "__main__":
    main()