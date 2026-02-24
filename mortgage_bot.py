"""
Ипотечный бот - РАСШИРЕННАЯ ВЕРСИЯ с SOCKS5 прокси
Запуск на GitHub Actions с Python 3.12
"""

import requests
import re
from datetime import datetime
import os
import sqlite3
import random
from telegram_pm.run import run_tpm

# ===== НАСТРОЙКИ =====
BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
CHANNEL_ID = os.environ.get('CHANNEL_ID', '')

# ===== ПРОКСИ-МЕНЕДЖЕР =====
class ProxyManager:
    def __init__(self):
        self.socks_proxies = []
        self.load_proxies()
    
    def load_proxies(self):
        """Загружает свежие SOCKS5 прокси"""
        try:
            # Источники SOCKS5 прокси
            sources = [
                "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
                "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks5.txt",
                "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-socks5.txt",
                "https://raw.githubusercontent.com/roosterkid/openproxylist/main/SOCKS5_RAW.txt",
                "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5&timeout=10000&country=all"
            ]
            
            all_proxies = []
            for url in sources:
                try:
                    response = requests.get(url, timeout=5)
                    if response.status_code == 200:
                        proxies = response.text.strip().split('\n')
                        all_proxies.extend([p.strip() for p in proxies if p.strip()])
                except:
                    continue
            
            # Убираем дубликаты и оставляем только валидные
            self.socks_proxies = list(set(all_proxies))[:50]
            print(f"    ✅ Загружено SOCKS5 прокси: {len(self.socks_proxies)}")
            
        except Exception as e:
            print(f"    ⚠️ Ошибка загрузки прокси: {e}")
            self.socks_proxies = []
    
    def get_random_proxy(self):
        """Возвращает случайный SOCKS5 прокси"""
        if not self.socks_proxies:
            self.load_proxies()
        
        if self.socks_proxies:
            proxy = random.choice(self.socks_proxies)
            return {
                'http': f'socks5://{proxy}',
                'https': f'socks5://{proxy}'
            }
        return None

# ===== ПАРСЕР TELEGRAM-КАНАЛОВ =====
class TelegramParser:
    def __init__(self):
        self.db_path = "telegram.db"
        # Расширенный список каналов (banki_ru убран)
        self.channels = [
            "ipoteka_rus",        # новости ипотеки
            "tbank_news",          # Т-Банк
            "ipoteka_stavka",      # ставки по ипотеке
            "sberbank_news",       # новости Сбера
            "vtb_news",            # новости ВТБ
            "alfabank",            # Альфа-Банк
            "gazprombank",         # Газпромбанк
            "domrfbank",           # Дом.РФ
            "ipoteka_segodnya",    # ипотека сегодня
            "russian_realty",      # недвижимость РФ
            "ipoteka_2026",        # ипотека в 2026
            "realty_news",         # новости недвижимости
            "banki_today",         # банки сегодня
            "finansist",           # финансы
            "ekonomika_ru",        # экономика РФ
        ]
        
        self.proxy_manager = ProxyManager()
        
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
        
    def parse_channels(self):
        """Парсит Telegram-каналы через telegram-pm с SOCKS5 прокси"""
        print("  📡 Парсим Telegram-каналы с SOCKS5 прокси...")
        
        # Получаем случайный прокси
        proxy = self.proxy_manager.get_random_proxy()
        if proxy:
            print(f"    Используем прокси: {proxy['http']}")
        
        try:
            # Запускаем telegram-pm с прокси
            run_tpm(
                db_path=self.db_path,
                channels=self.channels,
                verbose=True,
                format="sqlite",
                tg_iteration_in_preview_count=1,  # 1 итерация = ~20 сообщений
                tg_sleep_time_seconds=2,
                http_timeout=45,
                proxy=proxy,  # Добавляем SOCKS5 прокси
                http_headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
                }
            )
            
            # Подключаемся к базе
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            found_rates = {}
            
            # Получаем список всех таблиц
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            for table in tables:
                table_name = table[0]
                print(f"    📍 Канал @{table_name}:")
                
                try:
                    # Получаем последние 30 сообщений
                    cursor.execute(f"""
                        SELECT text, date FROM "{table_name}" 
                        ORDER BY date DESC LIMIT 30
                    """)
                    
                    messages = cursor.fetchall()
                    print(f"      Сообщений: {len(messages)}")
                    
                    for text, date in messages:
                        if not text:
                            continue
                        
                        # Ищем все ставки в тексте
                        rate_matches = re.findall(r'(\d+[.,]\d+)%', text)
                        if not rate_matches:
                            continue
                        
                        # Берем первую найденную ставку
                        rate = float(rate_matches[0].replace(',', '.'))
                        
                        # Проверяем все паттерны банков
                        for bank_name, pattern in self.bank_patterns.items():
                            if re.search(pattern, text, re.IGNORECASE):
                                if bank_name not in found_rates or rate < found_rates[bank_name]:
                                    found_rates[bank_name] = rate
                                    print(f"        ✅ {bank_name}: {rate}%")
                                    
                except Exception as e:
                    print(f"      ⚠️ Ошибка: {e}")
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
            print(f"    🔥 {bank}: {rate}% (из Telegram)")
        
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
🔄 Источник: Telegram-каналы + SOCKS5 прокси
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
    print("🚀 ИПОТЕЧНЫЙ БОТ - PROXY + 15 КАНАЛОВ")
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