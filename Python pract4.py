import threading
import time
import json

class ShoppingList:
    def __init__(self, filename="shopping_list.json"):
        self.filename = filename
        self.shopping_list = self.load_list()
        self.lock = threading.Lock()  # Защита от гонок данных
        self.save_thread = None

    def load_list(self):
        """Загружает список покупок из файла."""
        try:
            with open(self.filename, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return []
        except json.JSONDecodeError:
            print(f"Ошибка при чтении файла {self.filename}.  Возвращен пустой список.")
            return []

    def save_list(self):
        """Сохраняет список покупок в файл."""
        with self.lock:
            try:
                with open(self.filename, 'w') as f:
                    json.dump(self.shopping_list, f, indent=4)
                print("Список покупок сохранен.")
            except Exception as e:
                print(f"Ошибка при сохранении списка: {e}")

    def add_item(self, item):
        """Добавляет товар в список."""
        with self.lock:
            self.shopping_list.append(item)
        self.schedule_save()

    def remove_item(self, item):
        """Удаляет товар из списка."""
        with self.lock:
            if item in self.shopping_list:
                self.shopping_list.remove(item)
            else:
                print(f"Товар '{item}' не найден в списке.")
        self.schedule_save()


    def display_list(self):
        """Отображает список покупок."""
        with self.lock:
            if not self.shopping_list:
                print("Список покупок пуст.")
            else:
                print("Список покупок:")
                for i, item in enumerate(self.shopping_list):
                    print(f"{i+1}. {item}")

    def schedule_save(self):
        """Запускает или перезапускает поток для сохранения списка."""
        if self.save_thread and self.save_thread.is_alive():
            # Если поток сохранения уже запущен, просто завершим его
            # (в реальности лучше бы использовать Event для более грациозной остановки)
            self.save_thread.join() # Ожидаем завершения потока
            self.save_thread = None

        self.save_thread = threading.Thread(target=self.save_list)
        self.save_thread.daemon = True  # Поток завершится вместе с основной программой
        self.save_thread.start()



def main():
    shopping_list = ShoppingList()

    while True:
        print("\nЧек-лист покупок:")
        print("1. Добавить товар")
        print("2. Удалить товар")
        print("3. Показать список")
        print("4. Выйти")

        choice = input("Выберите действие: ")

        if choice == "1":
            item = input("Введите название товара: ")
            shopping_list.add_item(item)
        elif choice == "2":
            item = input("Введите название товара для удаления: ")
            shopping_list.remove_item(item)
        elif choice == "3":
            shopping_list.display_list()
        elif choice == "4":
            print("Выход из программы.")
            break
        else:
            print("Некорректный выбор. Попробуйте снова.")

if __name__ == "__main__":
    main()
