"""
Ипотечный бот - ФИНАЛЬНАЯ ВЕРСИЯ с глобальными SOCKS5 прокси
Увеличенный сбор постов, улучшенный парсинг ставок
Запуск на GitHub Actions с Python 3.12
"""

import requests
import re
from datetime import datetime
import os
import sqlite3
import random
import socket
import socks
import time
from telegram_pm.run import run_tpm

# ===== НАСТРОЙКИ =====
BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
CHANNEL_ID = os.environ.get('CHANNEL_ID', '')

# ===== ГЛОБАЛЬНЫЙ ПРОКСИ-МЕНЕДЖЕР =====
class GlobalProxyManager:
    def __init__(self):
        self.socks_proxies = []
        self.current_proxy = None
        self.load_proxies()
    
    def load_proxies(self):
        """Загружает свежие SOCKS5 прокси из нескольких источников"""
        try:
            sources = [
                "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
                "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks5.txt",
                "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-socks5.txt",
                "https://raw.githubusercontent.com/roosterkid/openproxylist/main/SOCKS5_RAW.txt",
                "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5&timeout=10000&country=all",
                "https://www.proxy-list.download/api/v1/get?type=socks5",
                "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt"
            ]
            
            all_proxies = []
            for url in sources:
                try:
                    response = requests.get(url, timeout=10)
                    if response.status_code == 200:
                        proxies = response.text.strip().split('\n')
                        # Очищаем от лишних пробелов и пустых строк
                        cleaned = [p.strip() for p in proxies if p.strip()]
                        all_proxies.extend(cleaned)
                        print(f"      📥 Загружено {len(cleaned)} прокси из {url.split('/')[2]}")
                except Exception as e:
                    continue
            
            # Фильтруем только валидные прокси (IP:PORT)
            valid_proxies = []
            for proxy in all_proxies:
                parts = proxy.split(':')
                if len(parts) == 2 and parts[0].count('.') == 3:
                    try:
                        port = int(parts[1])
                        if 1 <= port <= 65535:  # Проверяем, что порт валидный
                            valid_proxies.append(proxy)
                    except:
                        continue
            
            # Убираем дубликаты и берем топ-50
            self.socks_proxies = list(set(valid_proxies))[:50]
            print(f"    ✅ Загружено валидных SOCKS5 прокси: {len(self.socks_proxies)}")
            
        except Exception as e:
            print(f"    ⚠️ Ошибка загрузки прокси: {e}")
            self.socks_proxies = []
    
    def set_global_proxy(self):
        """Устанавливает глобальный SOCKS5 прокси для всего трафика"""
        if not self.socks_proxies:
            self.load_proxies()
        
        # Пробуем разные прокси, пока не найдем рабочий
        for attempt in range(3):
            if not self.socks_proxies:
                break
                
            self.current_proxy = random.choice(self.socks_proxies)
            proxy_parts = self.current_proxy.split(':')
            proxy_host = proxy_parts[0]
            proxy_port = int(proxy_parts[1])
            
            print(f"    🔌 Пытаемся установить прокси: {self.current_proxy}")
            
            try:
                # Настраиваем SOCKS5 для всего сокета
                socks.set_default_proxy(socks.SOCKS5, proxy_host, proxy_port)
                socket.socket = socks.socksocket
                
                # Тестируем прокси простым запросом
                test_socket = socks.socksocket()
                test_socket.settimeout(5)
                test_socket.connect(('telegram.org', 80))
                test_socket.close()
                
                print(f"    ✅ Прокси работает: {self.current_proxy}")
                return True
                
            except Exception as e:
                print(f"    ❌ Прокси не работает: {e}")
                # Удаляем нерабочий прокси из списка
                self.socks_proxies.remove(self.current_proxy)
                # Восстанавливаем стандартный сокет
                socks.set_default_proxy(None)
                socket.socket = socket._socketobject if hasattr(socket, '_socketobject') else socket.socket
                continue
        
        print("    ⚠️ Не удалось найти рабочий прокси")
        return False
    
    def disable_global_proxy(self):
        """Отключает глобальный прокси"""
        try:
            socks.set_default_proxy(None)
            socket.socket = socket._socketobject if hasattr(socket, '_socketobject') else socket.socket
            print("    🔌 Глобальный прокси отключён")
        except:
            pass

# ===== ПАРСЕР TELEGRAM-КАНАЛОВ =====
class TelegramParser:
    def __init__(self):
        self.db_path = "telegram.db"
        # Расширенный список каналов
        self.channels = [
            "ipoteka_rus", "tbank_news", "ipoteka_stavka",
            "sberbank_news", "vtb_news", "alfabank",
            "gazprombank", "domrfbank", "ipoteka_segodnya",
            "russian_realty", "ipoteka_2026", "realty_news",
            "banki_today", "finansist", "ekonomika_ru",
            "ipoteka_rf", "stavki_ru", "banki_rossii"
        ]
        
        self.proxy_manager = GlobalProxyManager()
        
        # Паттерны банков (расширенные)
        self.bank_patterns = {
            'Сбербанк': r'сбер[банк]*|sber|сбербанк',
            'ВТБ': r'втб|vtb|втб банк',
            'Альфа-Банк': r'альфа|alfa|альфа-банк',
            'Т-Банк': r'т[- ]?банк|тинькофф|tbank|tinkoff|тиньков',
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
            'Райффайзенбанк': r'райффайзен|raiffeisen',
            'Юникредит банк': r'юникредит|unicredit',
            'Росбанк': r'росбанк|rosbank',
            'Почта банк': r'почта|pochta',
            'Хоум кредит': r'хоум|home credit',
        }
        
        # Базовые ставки
        self.base_rates = {
            'Сбербанк': 21.0, 'ВТБ': 20.1, 'Альфа-Банк': 20.5,
            'Т-Банк': 16.9, 'Газпромбанк': 20.8, 'Россельхозбанк': 20.2,
            'Промсвязьбанк': 19.49, 'Уралсиб': 18.79, 'Банк Открытие': 21.1,
            'Совкомбанк': 20.9, 'МТС Банк': 20.7, 'Банк ДОМ.РФ': 20.2,
            'Банк Санкт-Петербург': 18.49, 'Транскапиталбанк': 20.25, 'ВБРР': 20.4,
            'Райффайзенбанк': 20.5, 'Юникредит банк': 20.8, 'Росбанк': 20.6,
            'Почта банк': 21.2, 'Хоум кредит': 21.5,
        }
        
    def parse_channels(self):
        """Парсит Telegram-каналы через глобальный SOCKS5 прокси"""
        print("  📡 Парсим Telegram-каналы через глобальный SOCKS5...")
        
        # Устанавливаем глобальный прокси
        proxy_set = self.proxy_manager.set_global_proxy()
        if not proxy_set:
            print("    ⚠️ Работаем без прокси")
        
        try:
            # Запускаем telegram-pm с УВЕЛИЧЕННЫМ количеством итераций
            run_tpm(
                db_path=self.db_path,
                channels=self.channels,
                verbose=True,
                format="sqlite",
                tg_iteration_in_preview_count=10,  # УВЕЛИЧИЛИ ДО 10 для сбора истории
                tg_sleep_time_seconds=3,
                http_timeout=60,
                http_headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
                }
            )
            
            # Отключаем прокси после использования
            self.proxy_manager.disable_global_proxy()
            
            # Даем время на запись в БД
            time.sleep(2)
            
            # Подключаемся к базе
            if not os.path.exists(self.db_path):
                print("    ⚠️ База данных не создана")
                return {}
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            found_rates = {}
            
            # Получаем список всех таблиц
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            print(f"    📊 Найдено таблиц в БД: {len(tables)}")
            
            for table in tables:
                table_name = table[0]
                print(f"    📍 Канал @{table_name}:")
                
                try:
                    # Получаем все сообщения из канала
                    cursor.execute(f"""
                        SELECT text, date FROM "{table_name}" 
                        ORDER BY date DESC
                    """)
                    
                    messages = cursor.fetchall()
                    print(f"      Сообщений в БД: {len(messages)}")
                    
                    message_count = 0
                    rate_count = 0
                    
                    for text, date in messages:
                        if not text:
                            continue
                        
                        message_count += 1
                        
                        # Ищем все ставки в тексте
                        rate_matches = re.findall(r'(\d+[.,]\d+)%', text)
                        if not rate_matches:
                            continue
                        
                        rate = float(rate_matches[0].replace(',', '.'))
                        
                        # Проверяем все паттерны банков
                        for bank_name, pattern in self.bank_patterns.items():
                            if re.search(pattern, text, re.IGNORECASE):
                                if bank_name not in found_rates or rate < found_rates[bank_name]:
                                    found_rates[bank_name] = rate
                                    print(f"        ✅ {bank_name}: {rate}%")
                                    rate_count += 1
                                    
                    print(f"      Найдено ставок: {rate_count}")
                    
                except Exception as e:
                    print(f"      ⚠️ Ошибка: {e}")
                    continue
            
            conn.close()
            
            # Удаляем базу после использования
            try:
                os.remove(self.db_path)
                print("    🗑️ База данных удалена")
            except:
                pass
            
            return found_rates
            
        except Exception as e:
            print(f"    ⚠️ Критическая ошибка: {e}")
            self.proxy_manager.disable_global_proxy()
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
            print(f"    🔥 {bank}: {rate}% (ИЗ TELEGRAM)")
        
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
    
    # Добавляем статистику по источникам
    telegram_count = len([b for b in rates_dict.keys() if b in rates_dict])
    
    text += f"""

📅 {datetime.now().strftime('%d.%m.%Y %H:%M')} (МСК)
📊 Всего банков: {len(rates_list)}
🤖 Найдено в Telegram: {telegram_count}
🔄 Источник: Глобальные SOCKS5 прокси + база
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
            return True
        else:
            print(f"  ❌ Ошибка: {response.text}")
            return False
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
        return False

# ===== ГЛАВНАЯ =====
def main():
    print("=" * 60)
    print("🚀 ИПОТЕЧНЫЙ БОТ - ФИНАЛ")
    print(f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print("=" * 60)
    
    if not BOT_TOKEN or not CHANNEL_ID:
        print("❌ Ошибка: не заданы BOT_TOKEN или CHANNEL_ID")
        return
    
    # Проверяем доступность Telegram API
    try:
        test_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getMe"
        test_response = requests.get(test_url, timeout=5)
        if test_response.status_code == 200:
            print("✅ Telegram API доступен")
    except:
        print("⚠️ Telegram API недоступен, но пробуем продолжить")
    
    parser = AutoParser()
    rates = parser.collect_all_rates()
    
    if rates:
        message = format_message(rates)
        send_to_channel(message)
        print("\n✅ ГОТОВО")
    else:
        print("❌ Ставки не получены")

if __name__ == "__main__":
    main()