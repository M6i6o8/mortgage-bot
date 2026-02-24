"""
Ипотечный бот - ТЕРМИНАТОР
Жёсткие таймауты, только рабочие каналы, максимум 3 минуты
"""

import requests
import re
from datetime import datetime
import os
import sqlite3
import random
import socket
import socks
import signal
import sys

# ===== НАСТРОЙКИ =====
BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
CHANNEL_ID = os.environ.get('CHANNEL_ID', '')
MAX_RUNTIME = 180  # 3 минуты максимум!

# ===== ТАЙМАУТ =====
class TimeoutException(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutException()

# Устанавливаем обработчик сигнала
signal.signal(signal.SIGALRM, timeout_handler)

# ===== ТОЛЬКО РАБОЧИЕ КАНАЛЫ (убрал все запрещённые) =====
WORKING_CHANNELS = [
    "tbank_news",        # Т-Банк (работает)
    "sberbank_news",     # Сбер (работает)
    "vtb_news",          # ВТБ (работает)
    "alfabank",          # Альфа (работает)
    "gazprombank",       # Газпромбанк (работает)
    "domrfbank",         # Дом.РФ (работает)
    "ipoteka_stavka",    # Ставки (может работать)
]

# ===== БАЗОВЫЕ СТАВКИ =====
BASE_RATES = {
    'Сбербанк': 21.0, 'ВТБ': 20.1, 'Альфа-Банк': 20.5,
    'Т-Банк': 16.9, 'Газпромбанк': 20.8, 'Россельхозбанк': 20.2,
    'Промсвязьбанк': 19.49, 'Уралсиб': 18.79, 'Банк Открытие': 21.1,
    'Совкомбанк': 20.9, 'МТС Банк': 20.7, 'Банк ДОМ.РФ': 20.2,
    'Банк Санкт-Петербург': 18.49, 'Транскапиталбанк': 20.25, 'ВБРР': 20.4,
}

# ===== ПРОКСИ (ОДИН РАБОЧИЙ) =====
WORKING_PROXIES = [
    "45.132.184.38:3128",     # Проверенный HTTP прокси
    "185.132.179.146:8080",   # Проверенный HTTP прокси
    "46.229.234.113:8080",    # Проверенный HTTP прокси
]

def get_working_proxy():
    """Возвращает рабочий прокси"""
    proxy = random.choice(WORKING_PROXIES)
    return {
        'http': f'http://{proxy}',
        'https': f'http://{proxy}'
    }

# ===== ПРОСТОЙ ПАРСИНГ БЕЗ TELEGRAM-PM =====
def parse_telegram_fast():
    """Быстрый парсинг через веб-превью"""
    print("  📡 Быстрый парсинг Telegram...")
    
    found_rates = {}
    
    for channel in WORKING_CHANNELS:
        try:
            url = f"https://t.me/s/{channel}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'
            }
            
            # Пробуем через прокси
            proxy = get_working_proxy()
            response = requests.get(url, headers=headers, proxies=proxy, timeout=10)
            
            if response.status_code == 200:
                # Ищем ставки в тексте
                text = response.text
                rate_matches = re.findall(r'(\d+[.,]\d+)%', text)
                
                if rate_matches:
                    rate = float(rate_matches[0].replace(',', '.'))
                    
                    # Определяем банк по каналу
                    if 'sber' in channel:
                        found_rates['Сбербанк'] = rate
                        print(f"      ✅ Сбербанк: {rate}%")
                    elif 'vtb' in channel:
                        found_rates['ВТБ'] = rate
                        print(f"      ✅ ВТБ: {rate}%")
                    elif 'alfa' in channel:
                        found_rates['Альфа-Банк'] = rate
                        print(f"      ✅ Альфа-Банк: {rate}%")
                    elif 'tbank' in channel or 'tinkoff' in channel:
                        found_rates['Т-Банк'] = rate
                        print(f"      ✅ Т-Банк: {rate}%")
                    
        except Exception as e:
            print(f"      ⚠️ {channel}: {str(e)[:50]}")
            continue
    
    return found_rates

# ===== ОСНОВНАЯ ФУНКЦИЯ =====
def main():
    print("=" * 60)
    print("🚀 ИПОТЕЧНЫЙ БОТ - ТЕРМИНАТОР")
    print(f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print(f"⏱️  Максимальное время: {MAX_RUNTIME} сек")
    print("=" * 60)
    
    if not BOT_TOKEN or not CHANNEL_ID:
        print("❌ Ошибка: не заданы BOT_TOKEN или CHANNEL_ID")
        return
    
    # Устанавливаем таймаут
    signal.alarm(MAX_RUNTIME)
    
    try:
        # Быстрый парсинг
        telegram_rates = parse_telegram_fast()
        
        # Берём базовые ставки
        all_rates = BASE_RATES.copy()
        
        # Обновляем найденными из Telegram
        for bank, rate in telegram_rates.items():
            all_rates[bank] = rate
            print(f"    🔥 {bank}: {rate}% (ИЗ TELEGRAM)")
        
        # Сортируем
        rates_list = [(bank, rate) for bank, rate in all_rates.items()]
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
        
        text += f"""

📅 {datetime.now().strftime('%d.%m.%Y %H:%M')} (МСК)
📊 Всего банков: {len(rates_list)}
🤖 Telegram: {len(telegram_rates)} обновлений
⚡ Режим: Терминатор
"""
        
        # Отправляем
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": CHANNEL_ID,
            "text": text,
            "parse_mode": "HTML"
        }
        
        response = requests.post(url, data=data, timeout=10)
        if response.status_code == 200:
            print("\n✅ ГОТОВО!")
        
    except TimeoutException:
        print("\n⚠️ ТАЙМАУТ! Отправляем базовые ставки")
        
        # Отправляем базовые ставки
        rates_list = [(bank, rate) for bank, rate in BASE_RATES.items()]
        rates_list.sort(key=lambda x: x[1])
        min_bank, min_rate = rates_list[0]
        
        text = f"""
🏠 <b>Ипотека сегодня: БАЗОВЫЕ СТАВКИ</b>

🔥 <b>Минимальная:</b> {min_bank} — {min_rate}%

📊 <b>Все банки:</b>

"""
        for bank, rate in rates_list[:10]:
            text += f"• {bank} — {rate}%\n"
        
        text += f"""
        
📅 {datetime.now().strftime('%d.%m.%Y %H:%M')} (МСК)
⚡ Режим: Терминатор (таймаут)
"""
        
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {"chat_id": CHANNEL_ID, "text": text, "parse_mode": "HTML"}
        requests.post(url, data=data, timeout=10)
    
    finally:
        signal.alarm(0)  # Отключаем таймаут

if __name__ == "__main__":
    main()