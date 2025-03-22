import threading
import time
import queue
import json
import os
import hashlib
from datetime import datetime

class User:
    def __init__(self, username, password_hash):
        self.username = username
        self.password_hash = password_hash
        self.shopping_lists = {}

class ShoppingList:
    def __init__(self, owner, logger):
        self.owner = owner
        self.lock = threading.Lock()
        self.logger = logger # Получаем объект Logger

    def add_item(self, list_name, item):
        with self.lock:
            if list_name not in self.owner.shopping_lists:
                self.owner.shopping_lists[list_name] = []
            self.owner.shopping_lists[list_name].append(item)
            log_message = f"Добавлен товар: {item} в список '{list_name}'"
            self.logger.log_info(self.owner.username, log_message)
            print(f"{log_message} (Поток: {threading.current_thread().name})")

    def remove_item(self, list_name, item):
        with self.lock:
            if list_name in self.owner.shopping_lists:
                if item in self.owner.shopping_lists[list_name]:
                    self.owner.shopping_lists[list_name].remove(item)
                    log_message = f"Удален товар: {item} из списка '{list_name}'"
                    self.logger.log_info(self.owner.username, log_message)
                    print(f"{log_message} (Поток: {threading.current_thread().name})")
                else:
                    log_message = f"Товар '{item}' не найден в списке '{list_name}'"
                    self.logger.log_info(self.owner.username, log_message)
                    print(f"{log_message} (Поток: {threading.current_thread().name})")
            else:
                log_message = f"Список '{list_name}' не найден."
                self.logger.log_info(self.owner.username, log_message)
                print(f"{log_message} (Поток: {threading.current_thread().name})")

    def display_list(self, list_name):
        with self.lock:
            print(f"\n--- Список покупок '{list_name}' пользователя {self.owner.username} ---")
            if list_name in self.owner.shopping_lists and self.owner.shopping_lists[list_name]:
                for item in self.owner.shopping_lists[list_name]:
                    print(f"- {item}")
            else:
                print("Список покупок пуст.")
            print("----------------------\n")

class UserManager:
    USERS_FILE = "users.json"

    def __init__(self, logger):
        self.users = self.load_users()
        self.lock = threading.Lock()
        self.save_queue = queue.Queue()
        self.save_thread = threading.Thread(target=self.save_worker, daemon=True)
        self.save_thread.start()
        self.logger = logger # Получаем объект Logger

    def register_user(self, username, password):
        with self.lock:
            if username in self.users:
                return False, "Пользователь с таким именем уже существует."

            password_hash = hashlib.sha256(password.encode()).hexdigest()
            new_user = User(username, password_hash)
            self.users[username] = new_user
            self.enqueue_save()
            log_message = f"Зарегистрирован новый пользователь: {username}"
            self.logger.log_info(username, log_message)
            return True, "Регистрация прошла успешно."

    def authenticate_user(self, username, password):
        with self.lock:
            if username not in self.users:
                return None, "Пользователь не найден."

            user = self.users[username]
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            if user.password_hash == password_hash:
                log_message = f"Пользователь {username} успешно аутентифицирован."
                self.logger.log_info(username, log_message)
                return user, "Аутентификация прошла успешно."
            else:
                log_message = f"Неудачная попытка аутентификации пользователя {username} (неверный пароль)."
                self.logger.log_info(username, log_message)
                return None, "Неверный пароль."

    def load_users(self):
        users = {}
        if os.path.exists(self.USERS_FILE):
            try:
                with open(self.USERS_FILE, "r") as f:
                    user_data = json.load(f)
                    for username, data in user_data.items():
                        user = User(username, data["password_hash"])
                        user.shopping_lists = data.get("shopping_lists", {})
                        users[username] = user
            except FileNotFoundError:
                print(f"Файл {self.USERS_FILE} не найден.")
            except json.JSONDecodeError as e:
                self.logger.log_error("Система", f"Ошибка при чтении файла {self.USERS_FILE}: {e}")
                print(f"Ошибка при чтении файла {self.USERS_FILE}. Файл поврежден.")
            except Exception as e:
                self.logger.log_error("Система", f"Непредвиденная ошибка при загрузке пользователей: {e}")

        return users

    def save_users(self):
        with self.lock:
            user_data = {}
            for username, user in self.users.items():
                user_data[username] = {
                    "password_hash": user.password_hash,
                    "shopping_lists": user.shopping_lists
                }

            try:
                with open(self.USERS_FILE, "w") as f:
                    json.dump(user_data, f, indent=4)
                print("Данные пользователей сохранены в файл.")
            except IOError as e:
                self.logger.log_error("Система", f"Ошибка при сохранении данных пользователей в файл: {e}")
                print("Ошибка при сохранении данных пользователей в файл.")

    def enqueue_save(self):
        self.save_queue.put("save")

    def save_worker(self):
        while True:
            self.save_queue.get()
            self.save_users()
            self.save_queue.task_done()
            time.sleep(1)

class Logger:
    LOG_FILE = "shopping_list.log"

    def __init__(self):
        self.log_queue = queue.Queue()
        self.log_thread = threading.Thread(target=self.log_worker, daemon=True)
        self.log_thread.start()

    def log_info(self, username, message):
        self.log_queue.put(("[INFO]", username, message))

    def log_error(self, username, message):
        self.log_queue.put(("[ERROR]", username, message))

    def log_worker(self):
        while True:
            try:
                log_level, username, message = self.log_queue.get()
                now = datetime.now()
                timestamp = now.strftime("%d.%m.%Y %H:%M:%S")
                log_record = f"{log_level} [{timestamp}] [{username}] - {message}\n"

                with open(self.LOG_FILE, "a") as f:
                    f.write(log_record)
                self.log_queue.task_done()
            except Exception as e:
                print(f"Ошибка в потоке логирования: {e}")
            finally:
                time.sleep(0.1) # Чтобы не спамить файл в случае ошибки

def main():
    logger = Logger()  # Создаем объект Logger
    user_manager = UserManager(logger)  # Передаем Logger в UserManager
    current_user = None

    while True:
        if current_user:
            print(f"\nВы вошли как {current_user.username}. Что вы хотите сделать?")
            print("1. Добавить товар в список")
            print("2. Удалить товар из списка")
            print("3. Посмотреть список")
            print("4. Выйти из учетной записи")
            print("5. Завершить программу")

            choice = input("Выберите действие: ")

            try: # Добавлена обработка ошибок
                if choice == "1":
                    list_name = input("Введите название списка: ")
                    item = input("Введите название товара: ")
                    shopping_list = ShoppingList(current_user, logger) # Передаем Logger в ShoppingList
                    shopping_list.add_item(list_name, item)
                    user_manager.enqueue_save()

                elif choice == "2":
                    list_name = input("Введите название списка: ")
                    item = input("Введите название товара: ")
                    shopping_list = ShoppingList(current_user, logger) # Передаем Logger в ShoppingList
                    shopping_list.remove_item(list_name, item)
                    user_manager.enqueue_save()

                elif choice == "3":
                    list_name = input("Введите название списка: ")
                    shopping_list = ShoppingList(current_user, logger)  # Передаем Logger в ShoppingList
                    shopping_list.display_list(list_name)

                elif choice == "4":
                    current_user = None
                    print("Вы вышли из учетной записи.")
                    logger.log_info("Система", "Пользователь вышел из учетной записи.")

                elif choice == "5":
                    print("Завершение программы.")
                    logger.log_info("Система", "Программа завершена.")
                    break

                else:
                    print("Неверный выбор.")
                    logger.log_info("Система", "Неверный выбор в меню.")
            except Exception as e:
                logger.log_error(current_user.username if current_user else "Система", f"Непредвиденная ошибка: {e}")
                print(f"Произошла ошибка: {e}")


        else:
            print("\nДобро пожаловать!")
            print("1. Регистрация")
            print("2. Вход")
            print("3. Завершить программу")

            choice = input("Выберите действие: ")

            try: # Добавлена обработка ошибок
                if choice == "1":
                    username = input("Введите имя пользователя: ")
                    password = input("Введите пароль: ")
                    success, message = user_manager.register_user(username, password)
                    print(message)

                elif choice == "2":
                    username = input("Введите имя пользователя: ")
                    password = input("Введите пароль: ")
                    user, message = user_manager.authenticate_user(username, password)
                    if user:
                        current_user = user
                        print(message)
                    else:
                        print(message)

                elif choice == "3":
                    print("Завершение программы.")
                    logger.log_info("Система", "Программа завершена.")
                    break

                else:
                    print("Неверный выбор.")
                    logger.log_info("Система", "Неверный выбор в меню.")

            except Exception as e:
                logger.log_error("Система", f"Непредвиденная ошибка: {e}")
                print(f"Произошла ошибка: {e}")

    # Завершаем потоки
    user_manager.save_queue.put(None)
    user_manager.save_thread.join()
    logger.log_queue.put(None)
    logger.log_thread.join()

if __name__ == "__main__":
    main()
