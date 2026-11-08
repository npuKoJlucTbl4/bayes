
import tkinter as tk
from tkinter import ttk, filedialog
from pathlib import Path
import re
import random
import math


class BayesianApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Байесовская экспертная система")
        self.root.geometry("1100x700")
        self.root.minsize(850, 550)

        self.questions = []
        self.question_order = []
        self.artists = []
        self.artist_data = {}
        self.answers = {}

        self.current_question = 0
        self.database_path = None

        self.create_interface()
        self.create_menu()

    # Главное меню
    def create_menu(self):
        menu_bar = tk.Menu(self.root)

        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(
            label="Открыть базу знаний...",
            command=self.open_database,
            accelerator="Ctrl+O"
        )
        file_menu.add_command(
            label="Очистить все ответы",
            command=self.reset_answers,
            accelerator="Ctrl+R"
        )
        file_menu.add_separator()
        file_menu.add_command(
            label="Выход",
            command=self.root.destroy
        )

        menu_bar.add_cascade(label="Файл", menu=file_menu)

        self.root.config(menu=menu_bar)
        self.root.bind(
            "<Control-o>",
            lambda event: self.open_database()
        )
        self.root.bind(
            "<Control-r>",
            lambda event: self.reset_answers()
        )

    # Чтение базы знаний
    def parse_database(self, path):
        content = Path(path).read_bytes().decode("cp1251")
        lines = content.splitlines()

        questions = []
        artist_data = {}

        reading_questions = False
        reading_artists = False

        for line in lines:
            line = line.strip()

            if line == "Вопросы:":
                reading_questions = True
                continue

            if reading_questions:
                if not line:
                    reading_questions = False
                    reading_artists = True
                    continue

                match = re.match(r"^\d+\.\s*(.*)", line)

                if match:
                    questions.append(match.group(1))

            elif reading_artists and line and "," in line:
                parts = [part.strip() for part in line.split(",")]

                if len(parts) < 2:
                    continue

                name = parts[0]

                try:
                    prior = float(parts[1])

                    if not 0 <= prior <= 1:
                        raise ValueError(
                            f"Некорректная априорная вероятность: {name}"
                        )

                    if (len(parts) - 2) % 3 != 0:
                        raise ValueError(
                            f"Некорректное количество параметров: {name}"
                        )

                    evidence = {}

                    for i in range(2, len(parts), 3):
                        question_number = int(parts[i])
                        py = float(parts[i + 1])
                        pn = float(parts[i + 2])

                        if not 1 <= question_number <= len(questions):
                            raise ValueError(
                                f"Некорректный номер вопроса у {name}: "
                                f"{question_number}"
                            )

                        if not 0 <= py <= 1 or not 0 <= pn <= 1:
                            raise ValueError(
                                f"Некорректные py/pn у {name}"
                            )

                        evidence[question_number - 1] = (py, pn)

                    artist_data[name] = {
                        "prior": prior,
                        "evidence": evidence
                    }

                except (ValueError, IndexError) as e:
                    raise ValueError(
                        f"Ошибка в строке художника '{name}': {e}"
                    )

        if not questions or not artist_data:
            raise ValueError(
                "Не удалось обнаружить вопросы или художников."
            )

        if sum(data["prior"] for data in artist_data.values()) <= 0:
            raise ValueError(
                "Сумма априорных вероятностей должна быть больше нуля."
            )

        return questions, artist_data

    # Открытие файла
    def open_database(self):
        path = filedialog.askopenfilename(
            title="Открыть базу знаний",
            filetypes=[
                ("База знаний MKB", "*.mkb"),
                ("Все файлы", "*.*")
            ]
        )

        if not path:
            return

        try:
            questions, artist_data = self.parse_database(path)

            self.questions = questions
            self.artist_data = artist_data
            self.artists = list(artist_data.keys())

            self.question_order = list(enumerate(questions))
            random.shuffle(self.question_order)

            self.answers = {}
            self.current_question = 0
            self.database_path = path

            self.update_results()
            self.update_history()
            self.show_question()

            self.status_text.set(
                f"Загружена база: {Path(path).name}. "
                f"Вопросов: {len(questions)}, "
                f"художников: {len(self.artists)}."
            )

        except Exception as e:
            self.status_text.set(
                f"Ошибка загрузки базы: {e}"
            )

    # Создание интерфейса
    def create_interface(self):
        style = ttk.Style()

        style.configure("Treeview", rowheight=25)
        style.configure(
            "Treeview.Heading",
            font=("Arial", 10, "bold")
        )

        main = ttk.PanedWindow(
            self.root,
            orient=tk.HORIZONTAL
        )
        main.pack(
            fill=tk.BOTH,
            expand=True,
            padx=10,
            pady=10
        )

        left = ttk.Frame(main, padding=10)
        right = ttk.Frame(main, padding=10)

        main.add(left, weight=2)
        main.add(right, weight=3)

        # Вопросы
        ttk.Label(
            left,
            text="Текущий вопрос",
            font=("Arial", 13, "bold")
        ).pack(anchor="w", pady=(0, 10))

        self.question_number = ttk.Label(
            left,
            text="Вопросы не загружены"
        )
        self.question_number.pack(anchor="w")

        self.question_text = ttk.Label(
            left,
            text="Откройте базу знаний через меню «Файл».",
            font=("Arial", 12),
            wraplength=420,
            justify=tk.LEFT
        )
        self.question_text.pack(
            fill=tk.X,
            pady=15
        )

        ttk.Label(
            left,
            text="Ответ (от -5 до 5):"
        ).pack(anchor="w")

        self.answer_entry = ttk.Entry(
            left,
            font=("Arial", 12)
        )
        self.answer_entry.pack(
            fill=tk.X,
            pady=5
        )
        self.answer_entry.config(state=tk.DISABLED)

        self.answer_entry.bind(
            "<Return>",
            lambda event: self.submit_answer()
        )

        # Навигация
        nav = ttk.Frame(left)
        nav.pack(fill=tk.X, pady=10)

        self.prev_button = ttk.Button(
            nav,
            text="← Назад",
            command=self.previous_question,
            state=tk.DISABLED
        )
        self.prev_button.pack(
            side=tk.LEFT,
            expand=True,
            fill=tk.X,
            padx=(0, 3)
        )

        self.submit_button = ttk.Button(
            nav,
            text="Ответить →",
            command=self.submit_answer,
            state=tk.DISABLED
        )
        self.submit_button.pack(
            side=tk.LEFT,
            expand=True,
            fill=tk.X,
            padx=(3, 0)
        )

        self.clear_button = ttk.Button(
            left,
            text="Очистить ответ",
            command=self.clear_answer,
            state=tk.DISABLED
        )
        self.clear_button.pack(fill=tk.X)

        # История ответов
        ttk.Separator(left).pack(
            fill=tk.X,
            pady=15
        )

        ttk.Label(
            left,
            text="Ответы пользователя",
            font=("Arial", 12, "bold")
        ).pack(
            anchor="w",
            pady=(0, 5)
        )

        history_frame = ttk.Frame(left)
        history_frame.pack(
            fill=tk.BOTH,
            expand=True
        )

        self.history = ttk.Treeview(
            history_frame,
            columns=("number", "question", "answer"),
            show="headings"
        )

        self.history.heading(
            "number",
            text="№"
        )
        self.history.heading(
            "question",
            text="Содержание вопроса"
        )
        self.history.heading(
            "answer",
            text="Ответ"
        )

        self.history.column(
            "number",
            width=40,
            minwidth=40,
            anchor=tk.CENTER,
            stretch=False
        )
        self.history.column(
            "question",
            width=270,
            minwidth=150,
            anchor=tk.W
        )
        self.history.column(
            "answer",
            width=65,
            minwidth=50,
            anchor=tk.CENTER,
            stretch=False
        )

        history_scroll = ttk.Scrollbar(
            history_frame,
            orient=tk.VERTICAL,
            command=self.history.yview
        )

        self.history.configure(
            yscrollcommand=history_scroll.set
        )

        self.history.pack(
            side=tk.LEFT,
            fill=tk.BOTH,
            expand=True
        )
        history_scroll.pack(
            side=tk.RIGHT,
            fill=tk.Y
        )

        # Результаты
        ttk.Label(
            right,
            text="Результаты",
            font=("Arial", 13, "bold")
        ).pack(
            anchor="w",
            pady=(0, 10)
        )

        self.result_table = ttk.Treeview(
            right,
            columns=("artist", "weight"),
            show="headings"
        )

        self.result_table.heading(
            "artist",
            text="Художник"
        )
        self.result_table.heading(
            "weight",
            text="Вес"
        )

        self.result_table.column(
            "artist",
            width=300,
            anchor=tk.W
        )
        self.result_table.column(
            "weight",
            width=130,
            anchor=tk.CENTER
        )

        result_scroll = ttk.Scrollbar(
            right,
            orient=tk.VERTICAL,
            command=self.result_table.yview
        )

        self.result_table.configure(
            yscrollcommand=result_scroll.set
        )

        self.result_table.pack(
            side=tk.LEFT,
            fill=tk.BOTH,
            expand=True
        )
        result_scroll.pack(
            side=tk.RIGHT,
            fill=tk.Y
        )

        # Строка состояния
        self.status_text = tk.StringVar(
            value="Ожидание загрузки базы знаний."
        )

        status = ttk.Label(
            self.root,
            textvariable=self.status_text,
            relief=tk.SUNKEN,
            anchor=tk.W,
            padding=5
        )
        status.pack(
            side=tk.BOTTOM,
            fill=tk.X
        )

    
    # Расчёт апостериорных вероятностей
    def calculate_probabilities(self):
        probabilities = {}

        for artist, data in self.artist_data.items():
            # Начальная априорная вероятность
            probability = data["prior"]

            # Перебираем вопросы в фактическом порядке прохождения
            for question_index, _ in self.question_order:

                if question_index not in self.answers:
                    continue

                answer = self.answers[question_index]

                if answer == 0:
                    continue

                evidence = data["evidence"].get(question_index)

                if evidence is None:
                    continue

                py, pn = evidence

                # Ответ "Да"
                if answer > 0:
                    denominator = (
                        py * probability
                        + pn * (1 - probability)
                    )

                    if denominator > 0:
                        posterior_yes = (
                            py * probability / denominator
                        )
                    else:
                        posterior_yes = probability

                    probability = (
                        probability
                        + answer * (posterior_yes - probability) / 5
                    )

                # Ответ "Нет"
                else:
                    denominator = (
                        (1 - py) * probability
                        + (1 - pn) * (1 - probability)
                    )

                    if denominator > 0:
                        posterior_no = (
                            (1 - py) * probability / denominator
                        )
                    else:
                        posterior_no = probability

                    probability = (
                        posterior_no
                        + (answer + 5) * (
                            probability - posterior_no
                        ) / 5
                    )

            probabilities[artist] = probability

        return probabilities


    # Обновление таблицы результатов
    def update_results(self):
        self.result_table.delete(
            *self.result_table.get_children()
        )

        if not self.artist_data:
            return

        probabilities = self.calculate_probabilities()

        sorted_artists = sorted(
            probabilities.items(),
            key=lambda item: item[1],
            reverse=True
        )

        for artist, probability in sorted_artists:
            self.result_table.insert(
                "",
                tk.END,
                values=(
                    artist,
                    f"{probability:.6f}"
                )
            )

    # Полный сброс ответов
    def reset_answers(self):
        if not self.question_order:
            return

        self.answers.clear()
        self.current_question = 0

        random.shuffle(self.question_order)
        self.update_history()
        self.update_results()
        self.show_question()

        self.status_text.set(
            "Все ответы очищены. Начат новый проход вопросов."
        )

    # Отображение вопроса
    def show_question(self):
        if not self.question_order:
            return

        position = self.current_question
        original_index, question = self.question_order[position]

        self.question_number.config(
            text=f"Вопрос {position + 1} из {len(self.question_order)}"
        )

        self.question_text.config(text=question)

        self.answer_entry.config(state=tk.NORMAL)
        self.answer_entry.delete(0, tk.END)

        if original_index in self.answers:
            self.answer_entry.insert(
                0,
                str(self.answers[original_index])
            )

        self.prev_button.config(
            state=tk.NORMAL if position > 0 else tk.DISABLED
        )

        self.submit_button.config(
            text=(
                "Ответить →"
                if position < len(self.question_order) - 1
                else "Завершить"
            ),
            state=tk.NORMAL
        )

        self.clear_button.config(state=tk.NORMAL)

        self.answer_entry.focus_set()

    # Сохранение ответа и переход дальше
    def submit_answer(self):
        if not self.question_order:
            return

        value = self.answer_entry.get().strip()

        try:
            answer = int(value)

            if not -5 <= answer <= 5:
                raise ValueError

        except ValueError:
            self.status_text.set(
                "Ошибка: введите целое число от -5 до 5."
            )
            self.answer_entry.focus_set()
            return

        original_index, _ = self.question_order[
            self.current_question
        ]

        self.answers[original_index] = answer

        self.update_history()
        self.update_results()

        if self.current_question < len(self.question_order) - 1:
            self.current_question += 1
            self.show_question()

            self.status_text.set(
                f"Ответ сохранён: {answer}. "
                f"Переход к вопросу "
                f"{self.current_question + 1}."
            )
        else:
            self.status_text.set(
                "Все вопросы пройдены. "
                "Результаты пересчитаны."
            )

    # Обновление истории ответов
    def update_history(self):
        self.history.delete(
            *self.history.get_children()
        )

        for index in sorted(self.answers):
            self.history.insert(
                "",
                tk.END,
                values=(
                    index + 1,
                    self.questions[index],
                    self.answers[index]
                )
            )

    # Очистка ответа
    def clear_answer(self):
        if not self.question_order:
            return

        original_index, _ = self.question_order[
            self.current_question
        ]

        self.answer_entry.delete(0, tk.END)

        if original_index in self.answers:
            del self.answers[original_index]

        self.update_history()
        self.update_results()

        self.status_text.set(
            f"Ответ на вопрос {original_index + 1} удалён."
        )

        self.answer_entry.focus_set()

    # Переход к предыдущему вопросу
    def previous_question(self):
        if self.current_question > 0:
            self.current_question -= 1
            self.show_question()


if __name__ == "__main__":
    root = tk.Tk()
    app = BayesianApp(root)
    root.mainloop()
