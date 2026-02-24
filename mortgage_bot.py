"""
Ипотечный бот - ГЛОБАЛЬНЫЕ SOCKS5 ПРОКСИ
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
        """Загружает свежие SOCKS5 прокси"""
        try:
            sources = [
                "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
                "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks5.txt",
                "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-socks5.txt",
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
            
            # Фильтруем только валидные прокси (IP:PORT)
            valid_proxies = []
            for proxy in all_proxies:
                parts = proxy.split(':')
                if len(parts) == 2 and parts[0].count('.') == 3:
                    valid_proxies.append(proxy)
            
            self.socks_proxies = list(set(valid_proxies))[:30]
            print(f"    ✅ Загружено SOCKS5 прокси: {len(self.socks_proxies)}")
            
        except Exception as e:
            print(f"    ⚠️ Ошибка загрузки прокси: {e}")
            self.socks_proxies = []
    
    def set_global_proxy(self):
        """Устанавливает глобальный SOCKS5 прокси для всего трафика"""
        if not self.socks_proxies:
            self.load_proxies()
        
        if self.socks_proxies:
            self.current_proxy = random.choice(self.socks_proxies)
            proxy_parts = self.current_proxy.split(':')
            proxy_host = proxy_parts[0]
            proxy_port = int(proxy_parts[1])
            
            print(f"    🔌 Устанавливаем глобальный прокси: {self.current_proxy}")
            
            # Настраиваем SOCKS5 для всего сокета
            socks.set_default_proxy(socks.SOCKS5, proxy_host, proxy_port)
            socket.socket = socks.socksocket
            
            return True
        return False
    
    def disable_global_proxy(self):
        """Отключает глобальный прокси"""
        socks.set_default_proxy(None)
        socket.socket = socket._socketobject if hasattr(socket, '_socketobject') else socket.socket
        print("    🔌 Глобальный прокси отключён")

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
            "banki_today", "finansist", "ekonomika_ru"
        ]
        
        self.proxy_manager = GlobalProxyManager()
        
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
            'Сбербанк': 21.0, 'ВТБ': 20.1, 'Альфа-Банк': 20.5,
            'Т-Банк': 16.9, 'Газпромбанк': 20.8, 'Россельхозбанк': 20.2,
            'Промсвязьбанк': 19.49, 'Уралсиб': 18.79, 'Банк Открытие': 21.1,
            'Совкомбанк': 20.9, 'МТС Банк': 20.7, 'Банк ДОМ.РФ': 20.2,
            'Банк Санкт-Петербург': 18.49, 'Транскапиталбанк': 20.25, 'ВБРР': 20.4,
        }
        
    def parse_channels(self):
        """Парсит Telegram-каналы через глобальный SOCKS5 прокси"""
        print("  📡 Парсим Telegram-каналы через глобальный SOCKS5...")
        
        # Устанавливаем глобальный прокси
        proxy_set = self.proxy_manager.set_global_proxy()
        if not proxy_set:
            print("    ⚠️ Не удалось установить прокси, работаем без прокси")
        
        try:
            # Запускаем telegram-pm (теперь весь трафик идёт через прокси)
            run_tpm(
                db_path=self.db_path,
                channels=self.channels,
                verbose=True,
                format="sqlite",
                tg_iteration_in_preview_count=1,
                tg_sleep_time_seconds=2,
                http_timeout=45,
                http_headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
                    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
                }
            )
            
            # Отключаем прокси после использования
            self.proxy_manager.disable_global_proxy()
            
            # Подключаемся к базе
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            found_rates = {}
            
            # Получаем список всех таблиц
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            for table in tables:
                table_name = table[0]
                
                try:
                    cursor.execute(f"""
                        SELECT text FROM "{table_name}" 
                        ORDER BY date DESC LIMIT 30
                    """)
                    
                    messages = cursor.fetchall()
                    
                    for (text,) in messages:
                        if not text:
                            continue
                        
                        rate_matches = re.findall(r'(\d+[.,]\d+)%', text)
                        if not rate_matches:
                            continue
                        
                        rate = float(rate_matches[0].replace(',', '.'))
                        
                        for bank_name, pattern in self.bank_patterns.items():
                            if re.search(pattern, text, re.IGNORECASE):
                                if bank_name not in found_rates or rate < found_rates[bank_name]:
                                    found_rates[bank_name] = rate
                                    print(f"      ✅ {bank_name}: {rate}% (из @{table_name})")
                                    
                except Exception as e:
                    continue
            
            conn.close()
            
            try:
                os.remove(self.db_path)
            except:
                pass
            
            return found_rates
            
        except Exception as e:
            print(f"    ⚠️ Ошибка: {e}")
            self.proxy_manager.disable_global_proxy()
            return {}

# ===== ОСТАЛЬНОЙ КОД БЕЗ ИЗМЕНЕНИЙ =====
class AutoParser:
    def __init__(self):
        self.telegram_parser = TelegramParser()
        self.all_rates = {}
    
    def collect_all_rates(self):
        print("\n  🚀 ЗАПУСК АВТОМАТИЧЕСКОГО СБОРА")
        telegram_rates = self.telegram_parser.parse_channels()
        
        for bank, rate in telegram_rates.items():
            self.all_rates[bank] = rate
            print(f"    🔥 {bank}: {rate}% (из Telegram)")
        
        for bank, rate in self.telegram_parser.base_rates.items():
            if bank not in self.all_rates:
                self.all_rates[bank] = rate
                print(f"    ➕ {bank}: {rate}% (базовая)")
        
        print(f"\n  ✅ ВСЕГО БАНКОВ: {len(self.all_rates)}")
        return self.all_rates

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
🔄 Источник: Telegram-каналы + глобальные SOCKS5
"""
    
    return text

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
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")

def main():
    print("=" * 60)
    print("🚀 ИПОТЕЧНЫЙ БОТ - ГЛОБАЛЬНЫЕ SOCKS5")
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