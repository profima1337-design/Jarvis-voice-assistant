import json
import os
import queue
import random
import socket
import subprocess
import sys
import time
import urllib.parse
import webbrowser
import pyautogui
import pygame
import sounddevice as sd
from vosk import KaldiRecognizer, Model

# Аварийный тормоз PyAutoGUI
pyautogui.FAILSAFE = True

# Инициализируем звуковой движок pygame
try:
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.mixer.init()
except Exception as e:
    print(f"[Предупреждение звука]: Не удалось настроить микшер: {e}")

# Очередь для хранения аудиопотока
audio_queue = queue.Queue()


def callback(indata, frames, time, status):
    if status:
        print(status, file=sys.stderr)
    audio_queue.put(bytes(indata))


# =====================================================================
#         ДИНАМИЧЕСКИЕ ЗАГЛУШКИ ДЛЯ ГРАФИЧЕСКОГО ИНТЕРФЕЙСА (GUI)
# =====================================================================

# В этом словаре будут храниться команды, добавленные из GUI во время работы программы
GUI_DYNAMIC_COMMANDS = []


def add_gui_command(keywords, action_type, action_value, log_message=None):
    """
    Заглушка-функция для GUI. Позволяет динамически добавить команду.
    Пример использования из GUI-файла:
        import voice_input
        voice_input.add_gui_command(["включи стрим"], "web_page", "https://twitch.tv")
    """
    new_command = {
        "keywords": [k.lower().strip() for k in keywords],
        "action_type": action_type,  # "sound", "web_page", "run_script", "function"
        "action_value": action_value,  # Путь к файлу, URL-ссылка или имя функции
        "log_message": log_message,
    }
    GUI_DYNAMIC_COMMANDS.append(new_command)
    print(f"[GUI]: Успешно добавлена новая команда для слов: {keywords}")


def clear_gui_commands():
    """Очищает все добавленные через интерфейс команды"""
    global GUI_DYNAMIC_COMMANDS
    GUI_DYNAMIC_COMMANDS = []
    print("[GUI]: Динамические команды полностью очищены.")


# =====================================================================
#                      ВСПЕМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =====================================================================


def check_internet(timeout=1.5):
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(
            ("8.8.8.8", 53)
        )
        return True
    except socket.error:
        return False


def play_specific_sound(file_path):
    try:
        if os.path.exists(file_path):
            if file_path.endswith(".wav"):
                sound = pygame.mixer.Sound(file_path)
                sound.play()
                while pygame.mixer.get_busy():
                    pygame.time.Clock().tick(10)
            else:
                pygame.mixer.music.load(file_path)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
        else:
            print(f"[Система]: Файл {file_path} не найден! Пропускаю звук.")
    except Exception as e:
        print(f"[Ошибка звука]: {e}")


def play_random_sound():
    try:
        sound_id = random.randint(1, 3)
        sound_path = f"sounds/{sound_id}.wav"
        if not os.path.exists(sound_path):
            sound_path = f"sounds/{sound_id}.mp3"

        if os.path.exists(sound_path):
            if sound_path.endswith(".wav"):
                pygame.mixer.Sound(sound_path).play()
            else:
                pygame.mixer.music.load(sound_path)
                pygame.mixer.music.play()
            while pygame.mixer.get_busy() or pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
    except Exception as e:
        print(f"[Ошибка случайного звука]: {e}")


def launch_program(paths, name):
    for path in paths:
        if os.path.exists(path):
            print(f"[Джарвис]: Запускаю {name}...")
            subprocess.Popen(path)
            play_random_sound()
            return True
    print(f"[Джарвис]: Не удалось найти установленный {name} на ПК.")
    play_specific_sound("sounds/error_command.mp3")
    return False


def open_web_page(url, success_message):
    if not check_internet():
        print("[Джарвис]: Сэр, соединение с интернетом отсутствует.")
        play_specific_sound("sounds/no_internet.mp3")
        return
    if success_message:
        print(success_message)
    webbrowser.open(url)
    play_random_sound()


def press_hotkey_with_delay(key1, key2):
    pyautogui.keyDown(key1)
    time.sleep(0.1)
    pyautogui.press(key2)
    time.sleep(0.1)
    pyautogui.keyUp(key1)
    play_random_sound()

# =====================================================================
#                      ГЛАВНЫЙ ДВИЖОК КОМАНД
# =====================================================================


def execute_command(command_text):
    cmd = command_text.lower().strip()
    print(f"[Обработка команды]: {cmd}")

    # -----------------------------------------------------------------
    # СНАЧАЛА ПРОВЕРЯЕМ ДИНАМИЧЕСКИЕ КОМАНДЫ, ДОБАВЛЕННЫЕ ИЗ GUI
    # -----------------------------------------------------------------
    global GUI_DYNAMIC_COMMANDS
    for item in GUI_DYNAMIC_COMMANDS:
        if any(keyword in cmd for keyword in item["keywords"]):
            if item.get("log_message"):
                print(item["log_message"])
            else:
                print(f"[Джарвис]: Выполняю команду из интерфейса...")

            action_type = item.get("action_type")
            action_value = item.get("action_value")

            if action_type == "sound":
                play_specific_sound(action_value)
                return
            elif action_type == "web_page":
                open_web_page(action_value, f"[Джарвис]: Открываю ссылку {action_value}")
                return
            elif action_type == "run_script":
                print(f"[Джарвис]: Запускаю внешний скрипт: {action_value}")
                subprocess.Popen([sys.executable, action_value])
                play_random_sound()
                return
            elif action_type == "function":
                # Заглушка на случай, если GUI захочет передать название встроенной Python-функции
                print(f"[Джарвис]: Вызываю привязанную функцию: {action_value}")
                if action_value in globals():
                    globals()[action_value]()
                play_random_sound()
                return

    # -----------------------------------------------------------------
    # ЕСЛИ В GUI НЕТ СОВПАДЕНИЙ, РАБОТАЮТ СТАНДАРТНЫЕ ВСТРОЕННЫЕ КОМАНДЫ
    # -----------------------------------------------------------------

    # --- 1. ПРИВЕТСТВИЕ И ДОБРОЕ УТРО ---
    if any(word in cmd for word in ["привет", "здравствуй", "салам", "ку"]):
        print("[Джарвис]: Здравствуйте, сэр. Чем могу помочь?")
        play_specific_sound("sounds/dobroe_utro.wav")
        return

    elif "утро" in cmd or "утром" in cmd:
        print("[Джарвис]: Доброе утро, сэр. Система готова к работе.")
        play_specific_sound("sounds/dobroe_utro.wav")
        return

    # --- 2. КАК ДЕЛА / НАСТРОЕНИЕ ---
    elif any(word in cmd for word in ["как дела", "как настроение", "как жизнь", "ты как"]):
        print("[Джарвис]: Всё функционирует в штатном режиме, сэр. Спасибо, что спросили.")
        play_specific_sound("sounds/nastroenie.mp3")
        return

    # --- 3. РЕАКЦИЯ НА БЛАГОДАРНОСТЬ ---
    elif any(word in cmd for word in ["спасибо", "благодарю", "благодарен"]):
        print("[Джарвис]: Всегда к вашим услугам, сэр.")
        play_specific_sound("sounds/vsegda_k_vasim_uslugam.wav")
        return

    # --- 4. РЕАКЦИЯ НА ОСКОРБЛЕНИЯ ---
    elif any(
        word in cmd
        for word in ["нахуй", "на хуй", "пошел ты", "сука", "блядь", "заебал"]
    ):
        print("[Джарвис]: Сами идите нахуй, сэр.")
        play_specific_sound("sounds/sami_idite_nahuy.mp3")
        return

    # Намерения закрытия / сворачивания для додумывалки
    is_close = any(word in cmd for word in ["закрой", "выключи", "убери", "выключить"])
    is_minimize = any(word in cmd for word in ["сверни", "спрячь", "убавь", "тише"])
    is_maximize = any(word in cmd for word in ["разверни", "громче", "прибавь"])

    # --- УМНЫЙ ПОИСК В ИНТЕРНЕТЕ ---
    if any(word in cmd for word in ["найди", "найти", "загугли", "сколько", "почему", "зачем", "кто", "что такое"]):
        if not check_internet():
            print("[Джарвис]: Сэр, соединение с интернетом отсутствует.")
            play_specific_sound("sounds/no_internet.mp3")
            return

        search_query = (
            cmd.replace("найди в браузере", "")
            .replace("найти в браузере", "")
            .replace("загугли в браузере", "")
            .replace("открой в браузере", "")
            .replace("открой", "")
            .replace("в браузере", "")
            .replace("найди", "")
            .replace("найти", "")
            .replace("загугли", "")
            .strip()
        )

        if search_query:
            print(f"[Джарвис]: Ищу в Google: {search_query}")
            url_query = urllib.parse.quote(search_query)
            webbrowser.open(f"https://google.com{url_query}")
            play_random_sound()
            return
        else:
            print("[Джарвис]: Сэр, вы не уточнили, что именно нужно найти.")
            play_specific_sound("sounds/error_command.mp3")
            return

    # --- МУЗЫКА В БРАУЗЕРЕ ---
    elif "музыку" in cmd or "музыка" in cmd:
        if is_close:
            print("[Джарвис]: Закрываю вкладку с музыкой.")
            pyautogui.hotkey("ctrl", "w")
            play_random_sound()
        else:
            open_web_page(
                "https://yandex.ru", "[Джарвис]: Открываю Яндекс Музыку."
            )
        return

    # --- БРАУЗЕР И ВЕБ-САЙТЫ ---
    elif any(
        word in cmd
        for word in ["браузер", "интернет", "хром", "ютуб", "youtube", "сайт"]
    ):
        if is_close:
            print("[Джарвис]: Жестко закрываю все процессы браузеров.")
            os.system("taskkill /f /im chrome.exe /t")
            os.system("taskkill /f /im browser.exe /t")
            os.system("taskkill /f /im msedge.exe /t")
            os.system("taskkill /f /im opera.exe /t")
            play_random_sound()
        else:
            if "ютуб" in cmd or "youtube" in cmd:
                open_web_page("https://youtube.com", "[Джарвис]: Открываю Ютуб.")
            elif "гугл" in cmd or "google" in cmd:
                open_web_page("https://google.com", "[Джарвис]: Открываю Гугл.")
            elif "яндекс" in cmd or "yandex" in cmd or "поиск" in cmd:
                open_web_page("https://yandex.ru", "[Джарвис]: Открываю Яндекс.")
            else:
                print("[Джарвис]: Открываю ваш основной браузер.")
                webbrowser.open("https://google.com")
                play_random_sound()
        return

    # --- УНИВЕРСАЛЬНЫЙ ЗАПУСК И ЗАКРЫТИЕ ЛЮБЫХ ПРОГРАММ ---
    elif any(
        word in cmd
        for word in ["стим", "тим", "роблокс", "roblox", "телеграм", "телега", "telegram", "дискорд", "discord"]
    ):
        apps_data = {
            "steam": {
                "process": "steam.exe",
                "name": "Steam",
                "paths": ["C:\\Program Files (x86)\\Steam\\steam.exe", "C:\\Program Files\\Steam\\steam.exe"]
            },
            "roblox": {
                "process": "RobloxPlayerBeta.exe",
                "name": "Roblox",
                "paths": [
                    os.path.expandvars("%LocalAppData%\\Roblox\\Versions\\*\\RobloxPlayerBeta.exe"),
                    os.path.expandvars("%ProgramFiles(x86)%\\Roblox\\Versions\\*\\RobloxPlayerBeta.exe")
                ]
            },
            "telegram": {
                "process": "Telegram.exe",
                "name": "Telegram",
                "paths": [
                    os.path.expandvars("%AppData%\\Telegram Desktop\\Telegram.exe"),
                    "C:\\Program Files\\Telegram Desktop\\Telegram.exe"
                ]
            },
            "discord": {
                "process": "Discord.exe",
                "name": "Discord",
                "paths": [
                    os.path.expandvars("%LocalAppData%\\Discord\\app-*\\Discord.exe"),
                    os.path.expandvars("%LocalAppData%\\Discord\\Discord.exe")
                ]
            }
        }

        target_app = None
        if any(w in cmd for w in ["стим", "тим"]): target_app = apps_data["steam"]
        elif any(w in cmd for w in ["роблокс", "roblox"]): target_app = apps_data["roblox"]
        elif any(w in cmd for w in ["телеграм", "телега", "telegram"]): target_app = apps_data["telegram"]
        elif any(w in cmd for w in ["дискорд", "discord"]): target_app = apps_data["discord"]

        if target_app:
            if is_close:
                print(f"[Джарвис]: Системно закрываю {target_app['name']}.")
                os.system(f"taskkill /f /im {target_app['process']} /t")
                play_random_sound()
            else:
                import glob
                real_paths = []
                for p in target_app['paths']:
                    if "*" in p: real_paths.extend(glob.glob(p))
                    else: real_paths.append(p)
                launch_program(real_paths, target_app["name"])
        return

    # --- ДИСПЕТЧЕР ЗАДАЧ ---
    elif "диспетчер" in cmd or "задач" in cmd or "менеджер" in cmd:
        if is_close:
            print("[Джарвис]: Закрываю диспетчер задач через системную команду.")
            os.system("taskkill /f /im taskmgr.exe")
            play_random_sound()
        else:
            print("[Джарвис]: Открываю диспетчер задач.")
            subprocess.Popen("taskmgr.exe")
            play_random_sound()
        return

    # --- СВЕРНУТЬ ВСЕ ОКНА ---
    elif "окна" in cmd or "вкладки" in cmd or "все" in cmd:
        if is_minimize or is_close:
            print("[Джарвис]: Сворачиваю абсолютно все окна.")
            os.system('powershell -command "(New-Object -ComObject shell.application).MinimizeAll()"')
            play_random_sound()
        return

    # --- ТЕКУЩЕЕ ОКНО ---
    elif "окно" in cmd:
        if is_close:
            print("[Джарвис]: Пытаюсь закрыть активное окно.")
            press_hotkey_with_delay("alt", "f4")
        elif is_minimize:
            print("[Джарвис]: Принудительно сворачиваю текущее окно на рабочий стол.")
            pyautogui.keyDown("win")
            time.sleep(0.05)
            pyautogui.press("d")
            time.sleep(0.05)
            pyautogui.keyUp("win")
            play_random_sound()
        return

    # --- УПРАВЛЕНИЕ ГРОМКОСТЬЮ ПК ---
    elif any(word in cmd for word in ["звук", "громкость", "тише", "громче", "максимум", "минимум"]):
        if is_close or "муте" in cmd:
            print("[Джарвис]: Изменяю режим немоты.")
            pyautogui.press("volumemute")
            play_random_sound()
            return

        if any(word in cmd for word in ["максимум", "полную", "сто", "100"]):
            print("[Джарвис]: Устанавливаю максимальную громкость.")
            for _ in range(50): pyautogui.press("volumeup")
            play_random_sound()
            return

        if any(word in cmd for word in ["минимум", "ноль", "0"]):
            print("[Джарвис]: Снижаю громкость до минимума.")
            for _ in range(50): pyautogui.press("volumedown")
            play_random_sound()
            return

        steps = 3
        if any(word in cmd for word in ["десять", "10", "пятнадцать"]): steps = 8
        elif any(word in cmd for word in ["пять", "5", "чуть"]): steps = 2

        if any(word in cmd for word in ["громче", "прибавь", "добавь", "повысь"]):
            print(f"[Джарвис]: Делаю громче на {steps} шагов.")
            for _ in range(steps): pyautogui.press("volumeup")
            play_random_sound()
        elif any(word in cmd for word in ["тише", "убавь", "снизь", "меньше"]):
            print(f"[Джарвис]: Делаю тише на {steps} шагов.")
            for _ in range(steps): pyautogui.press("volumedown")
            play_random_sound()
        else:
            pyautogui.press("volumedown")
            play_random_sound()
        return

    # --- НЕИЗВЕСТНАЯ КОМАНДА ---
    elif cmd:
        print("[Джарвис]: Команда не распознана.")
        play_specific_sound("sounds/error_command.mp3")


# =====================================================================
#                         ГЛАВНЫЙ ЦИКЛ СТАРТА
# =====================================================================


def start_jarvis():
    if not os.path.exists("model"):
        print("[Ошибка]: Папка 'model' не найдена! Скачайте её и положите рядом со скриптом.")
        sys.exit(1)

    print("=== ИНИЦИАЛИЗАЦИЯ ДЖАРВИСА (ПОДДЕРЖКА GUI API) ===")
    model = Model("model")
    samplerate = 16000
    recognizer = KaldiRecognizer(model, samplerate)

    triggers = ["джарвис", "джарвиз", "чарвис", "жарвис", "гарвис", "арвис", "джарвисе"]
    print(f"[Инфо]: Имена активации: {triggers}")
    print("[Статус]: Локальный Джарвис слушает эфир.")

    with sd.RawInputStream(
        samplerate=samplerate,
        blocksize=8000,
        device=None,
        dtype="int16",
        channels=1,
        callback=callback,
    ):
        while True:
            data = audio_queue.get()
            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                speech = result.get("text", "")
                if not speech:
                    continue

                has_trigger, active_trigger = False, ""
                for word in triggers:
                    if word in speech:
                        has_trigger, active_trigger = True, word
                        break
                if not has_trigger:
                    continue

                print(f"\n[Вы сказали]: {speech}")
                command_clean = speech.replace(active_trigger, "").strip()

                if command_clean:
                    execute_command(command_clean)
                else:
                    print("[Джарвис]: Да, сэр? Слушаю...")
                    play_random_sound()


if __name__ == "__main__":
    try:
        start_jarvis()
    except KeyboardInterrupt:
        print("\n[Статус]: Выключение системы Джарвис.")
