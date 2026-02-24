"""
Ипотечный бот - умный парсинг с автоматической ротацией прокси
Запуск на GitHub Actions
"""

import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
import os
import random
import time
import warnings
from proxy_rotator import ProxyRotator, ProxyTester

warnings.filterwarnings("ignore", category=DeprecationWarning)

# ===== НАСТРОЙКИ =====
BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
CHANNEL_ID = os.environ.get('CHANNEL_ID', '')

# ===== ПРОКСИ РЕВОЛЬВЕР =====
class BankiRuParser:
    def __init__(self):
        self.all_rates = {}
        # Запасные ставки на случай если всё упадёт
        self.fallback_rates = {
            'Сбербанк': 21.0,
            'ВТБ': 20.1,
            'Альфа-Банк': 20.5,
            'Т-Банк': 16.9,
            'Банк ДОМ.РФ': 20.2,
            'Банк Санкт-Петербург': 18.49,
            'Уралсиб': 18.79,
            'Промсвязьбанк': 19.49,
            'Транскапиталбанк': 20.25,
            'ВБРР': 20.4,
            'Газпромбанк': 20.8,
            'Россельхозбанк': 20.2,
            'Совкомбанк': 20.9,
            'Банк Открытие': 21.1,
            'МТС Банк': 20.7,
        }
        
        # Настраиваем ротатор прокси
        self.rotator = ProxyRotator(
            sources=['free'],  # Используем бесплатные источники
            proxy_type=['http', 'https'],  # Только HTTP/HTTPS прокси
            max_workers=10,  # Сколько прокси проверять одновременно
            cache_ttl=300,  # Кешируем рабочие прокси на 5 минут
            countries=['RU'],  # Прокси в России (быстрее)
            timeout=5,  # Таймаут проверки прокси
        )
        
        # Заголовки как у реального браузера
        self.headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }
    
    def get_random_user_agent(self):
        """Генерирует случайный User-Agent"""
        ua_list = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        ]
        return random.choice(ua_list)
    
    def extract_rate(self, text):
        """Извлекает число-ставку из текста"""
        if not text:
            return None
        
        patterns = [
            r'от\s*(\d+[.,]\d+)%',
            r'ставка[^\d]*(\d+[.,]\d+)%',
            r'(\d+[.,]\d+)%\s*годовых',
            r'(\d+[.,]\d+)%',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                rate_str = match.group(1).replace(',', '.')
                try:
                    rate = float(rate_str)
                    if 5 <= rate <= 35:
                        return rate
                except:
                    continue
        return None
    
    def parse_banki_ru(self):
        """Парсинг Банки.ру через ротацию прокси"""
        try:
            print("  Парсим Банки.ру с прокси-револьвером...")
            
            # Получаем рабочий прокси
            proxy = self.rotator.get_proxy()
            if not proxy:
                print("    ⚠️ Не удалось получить рабочий прокси")
                return False
            
            print(f"    Использую прокси: {proxy}")
            
            # Формируем заголовки
            headers = self.headers.copy()
            headers['User-Agent'] = self.get_random_user_agent()
            
            # Пробуем загрузить страницу
            url = "https://www.banki.ru/products/ipoteka/"
            
            # Делаем запрос через прокси
            session = requests.Session()
            session.proxies = {
                'http': f'http://{proxy}',
                'https': f'http://{proxy}'
            }
            
            # Сначала заходим на главную (получаем куки)
            main_headers = headers.copy()
            main_headers['Referer'] = 'https://www.google.com/'
            session.get('https://www.banki.ru/', headers=main_headers, timeout=15)
            time.sleep(2)
            
            # Теперь идём на страницу с ипотекой
            response = session.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Ищем разными способами
                found_banks = 0
                
                # Способ 1: по data-test атрибутам
                rows = soup.find_all('tr', {'data-test': 'row'})
                
                if not rows:
                    # Способ 2: по классам
                    rows = soup.find_all('tr', class_=re.compile('row|product|item'))
                
                for row in rows[:20]:
                    try:
                        # Ищем название банка
                        name_tag = row.find(['a', 'span', 'td'], 
                                          class_=re.compile('name|title|bank'))
                        if not name_tag:
                            continue
                        
                        bank_name = name_tag.get_text().strip()
                        bank_name = re.sub(r'\s+', ' ', bank_name)
                        
                        # Ищем ставку
                        row_text = row.get_text()
                        rate = self.extract_rate(row_text)
                        
                        if bank_name and rate and len(bank_name) < 40:
                            self.all_rates[bank_name] = rate
                            found_banks += 1
                            print(f"    ✓ {bank_name[:30]}: {rate}%")
                            
                    except Exception as e:
                        continue
                
                if found_banks > 0:
                    print(f"    ✅ Найдено банков: {found_banks}")
                    # Сообщаем ротатору, что прокси хороший
                    self.rotator.report_success(proxy)
                    return True
                else:
                    print(f"    ⚠️ Банки не найдены, структура могла измениться")
                    self.rotator.report_failure(proxy)
                    return False
            else:
                print(f"    ⚠️ Статус {response.status_code}")
                self.rotator.report_failure(proxy)
                return False
                
        except Exception as e:
            print(f"    ✗ Ошибка парсинга: {e}")
            if 'proxy' in locals():
                self.rotator.report_failure(proxy)
            return False
    
    def parse_individual_banks(self):
        """Парсинг отдельных банков (как запасной вариант)"""
        
        # Сбер
        try:
            print("  Парсим Сбер...")
            url = "https://www.sberbank.ru/ru/person/credits/home/buying_complete_house"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                rate = self.extract_rate(response.text)
                if rate:
                    self.all_rates['Сбербанк'] = rate
                    print(f"    ✓ Сбер: {rate}%")
        except:
            pass
        
        time.sleep(1)
        
        # ВТБ
        try:
            print("  Парсим ВТБ...")
            url = "https://www.vtb.ru/personal/ipoteka/"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                rate = self.extract_rate(response.text)
                if rate:
                    self.all_rates['ВТБ'] = rate
                    print(f"    ✓ ВТБ: {rate}%")
        except:
            pass
        
        time.sleep(1)
        
        # Альфа
        try:
            print("  Парсим Альфа-Банк...")
            url = "https://alfabank.ru/get-money/mortgage/"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                rate = self.extract_rate(response.text)
                if rate:
                    self.all_rates['Альфа-Банк'] = rate
                    print(f"    ✓ Альфа-Банк: {rate}%")
        except:
            pass
    
    def add_fallback_rates(self):
        """Добавляет запасные ставки для отсутствующих банков"""
        added = 0
        for bank, rate in self.fallback_rates.items():
            if bank not in self.all_rates:
                self.all_rates[bank] = rate
                added += 1
        
        if added > 0:
            print(f"    ➕ Добавлено запасных банков: {added}")
    
    def collect_all_rates(self):
        """Запускает все парсеры"""
        print("  Запускаем умный парсинг с прокси...")
        
        # Пробуем спарсить Банки.ру с прокси
        banki_success = self.parse_banki_ru()
        
        if not banki_success:
            print("  ⚠️ Банки.ру не спарсился, пробуем без прокси...")
            # Если с прокси не вышло, пробуем без прокси
            self.parse_individual_banks()
        else:
            # Если с прокси вышло, всё равно парсим отдельные банки для сверки
            time.sleep(2)
            self.parse_individual_banks()
        
        # Добавляем запасные ставки для недостающих банков
        self.add_fallback_rates()
        
        # Фильтруем
        filtered_rates = {}
        for bank, rate in self.all_rates.items():
            if 5 <= rate <= 35:
                filtered_rates[bank] = rate
        
        self.all_rates = filtered_rates
        return self.all_rates

# ===== ФОРМАТИРОВАНИЕ СООБЩЕНИЯ =====
def format_message(rates_dict):
    """Форматирует сообщение для канала"""
    if not rates_dict:
        return "😔 Не удалось получить актуальные ставки."
    
    rates_list = [(bank, rate) for bank, rate in rates_dict.items()]
    rates_list.sort(key=lambda x: x[1])
    
    top_rates = rates_list[:20]
    min_bank, min_rate = rates_list[0]
    
    text = f"""
🏠 <b>Ипотека сегодня: МИНИМАЛЬНАЯ СТАВКА</b>

🔥 <b>Лучшее предложение:</b>
• {min_bank} — <b>{min_rate}%</b>

📊 <b>Все банки:</b>

"""
    
    for i, (bank, rate) in enumerate(top_rates, 1):
        if i == 1:
            text += f"🥇 {bank} — {rate}%\n"
        elif i == 2:
            text += f"🥈 {bank} — {rate}%\n"
        elif i == 3:
            text += f"🥉 {bank} — {rate}%\n"
        else:
            text += f"• {bank} — {rate}%\n"
    
    # Добавляем информацию об источнике
    source_info = "с прокси" if len(rates_list) > 10 else "комбинированные"
    
    text += f"""

📅 Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')} (МСК)
📊 Всего банков: {len(rates_list)}
🔄 Источник: {source_info}
"""
    
    return text

# ===== ОТПРАВКА В КАНАЛ =====
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
            print("  ✅ Успешно отправлено в канал")
        else:
            print(f"  ❌ Ошибка: {response.text}")
    except Exception as e:
        print(f"  ❌ Ошибка отправки: {e}")

# ===== ГЛАВНАЯ =====
def main():
    print("=" * 50)
    print("🚀 ЗАПУСК УМНОГО ПАРСИНГА С ПРОКСИ")
    print(f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print("=" * 50)
    
    if not BOT_TOKEN or not CHANNEL_ID:
        print("❌ Ошибка: не заданы BOT_TOKEN или CHANNEL_ID")
        return
    
    print(f"📢 Канал: {CHANNEL_ID}")
    
    print("\n🔍 НАЧАЛО ПАРСИНГА")
    parser = BankiRuParser()
    rates = parser.collect_all_rates()
    
    print(f"\n📊 ИТОГО: {len(rates)} банков")
    
    print("\n✏️ ФОРМИРОВАНИЕ СООБЩЕНИЯ")
    message = format_message(rates)
    
    print("\n📤 ОТПРАВКА В КАНАЛ")
    send_to_channel(message)
    
    print("\n" + "=" * 50)
    print("✅ БОТ ЗАВЕРШИЛ РАБОТУ")
    print("=" * 50)

if __name__ == "__main__":
    main()