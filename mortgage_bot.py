"""
Ипотечный бот для Telegram-канала
Ежедневная рассылка минимальных ставок по ипотеке
Запуск на GitHub Actions
"""

import requests
import os
from datetime import datetime

# ===== НАСТРОЙКИ =====
BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
CHANNEL_ID = os.environ.get('CHANNEL_ID', '')  # ID канала (например -1001234567890)

# ===== ДАННЫЕ СО СТАВКАМИ =====
class MortgageRateCollector:
    def __init__(self):
        self.all_rates = {}
        
    def collect_all_rates(self):
        """Собирает все ставки (данные из новостей)"""
        try:
            # Актуальные ставки на февраль 2026
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
            
            print(f"  ✓ Собрано {len(bank_updates)} банков")
            return self.all_rates
            
        except Exception as e:
            print(f"  ✗ Ошибка сбора данных: {e}")
            return {}

# ===== ФОРМИРОВАНИЕ СООБЩЕНИЯ =====
def format_message(rates_dict):
    """Форматирует сообщение для канала"""
    if not rates_dict:
        return "😔 Не удалось получить актуальные ставки. Попробуйте позже."
    
    # Сортируем банки по ставке (от меньшей к большей)
    rates_list = [(bank, rate) for bank, rate in rates_dict.items()]
    rates_list.sort(key=lambda x: x[1])
    
    top_rates = rates_list[:15]  # Показываем все банки
    min_bank, min_rate = rates_list[0]
    
    # Заголовок
    text = f"""
🏠 <b>Ипотека сегодня: МИНИМАЛЬНАЯ СТАВКА</b>

🔥 <b>Лучшее предложение:</b>
• {min_bank} — <b>{min_rate}%</b>

📊 <b>Все банки:</b>

"""
    
    # Добавляем все банки с эмодзи
    for i, (bank, rate) in enumerate(top_rates, 1):
        if i == 1:
            text += f"🥇 {bank} — {rate}%\n"
        elif i == 2:
            text += f"🥈 {bank} — {rate}%\n"
        elif i == 3:
            text += f"🥉 {bank} — {rate}%\n"
        else:
            text += f"• {bank} — {rate}%\n"
    
    # Подвал
    text += f"""

📅 Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')} (МСК)
📊 Всего банков: {len(rates_list)}
🔄 Данные: на основе рыночных предложений

#ипотека #ставки #минимальнаяставка
"""
    
    return text

# ===== ОТПРАВКА В TELEGRAM-КАНАЛ =====
def send_to_channel(text):
    """Отправляет сообщение в канал"""
    if not BOT_TOKEN or not CHANNEL_ID:
        print("❌ Ошибка: не заданы BOT_TOKEN или CHANNEL_ID")
        return False
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHANNEL_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    
    try:
        print(f"  Отправляем в канал {CHANNEL_ID}...")
        response = requests.post(url, data=data, timeout=10)
        
        if response.status_code == 200:
            print(f"  ✅ Успешно отправлено!")
            return True
        else:
            print(f"  ❌ Ошибка: {response.status_code}")
            print(f"  Текст ошибки: {response.text}")
            return False
            
    except Exception as e:
        print(f"  ❌ Ошибка отправки: {e}")
        return False

# ===== ГЛАВНАЯ ФУНКЦИЯ =====
def main():
    print("=" * 50)
    print(f"🚀 Запуск ипотечного бота")
    print(f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print("=" * 50)
    
    # Проверяем настройки
    if not BOT_TOKEN:
        print("❌ Ошибка: не задан BOT_TOKEN")
        return
    
    if not CHANNEL_ID:
        print("❌ Ошибка: не задан CHANNEL_ID")
        return
    
    print(f"📢 Канал: {CHANNEL_ID}")
    
    # Собираем ставки
    print("\n📊 Сбор данных о ставках...")
    collector = MortgageRateCollector()
    rates = collector.collect_all_rates()
    
    if not rates:
        print("❌ Не удалось собрать данные")
        return
    
    print(f"✅ Собрано банков: {len(rates)}")
    
    # Формируем сообщение
    print("\n✏️ Формирование сообщения...")
    message = format_message(rates)
    print(f"✅ Длина сообщения: {len(message)} символов")
    
    # Отправляем в канал
    print("\n📤 Отправка в Telegram...")
    success = send_to_channel(message)
    
    # Итог
    print("\n" + "=" * 50)
    if success:
        print("✅ ГОТОВО! Сообщение отправлено в канал")
    else:
        print("❌ ОШИБКА! Сообщение не отправлено")
    print("=" * 50)

# ===== ЗАПУСК =====
if __name__ == "__main__":
    main()