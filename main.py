import re
import json
import threading
import time
from pathlib import Path
from typing import Dict, List
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import sys

# словарь для тегов из Бесконечного лета и Ren'Py
static_mapping = {
    "th": "Мысли", "me": "Семён", "dv": "Алиса", "sl": "Славя", 
    "un": "Лена", "us": "Ульяна", "mz": "Мику", "mt": "Ольга Дмитриевна",
    "sh": "Шурик", "el": "Электроник", "al": "Алиса", "cs": "Крысёнок",
    "mi": "Мику", "uv": "Виола", "zh": "Женя", "pi": "Пионер",
    "pn": "Пионерка", "sq": "Сова", "bus": "Водитель автобуса",
    "ba": "Борисыч", "sa": "Саша",
}

class AliceDvacheskayaTheme:
    """Цветовая палитра в стиле Алисы Двачевской"""
    COLORS = {
        'bg_dark': '#1a0f0f',
        'bg_medium': '#2a1a1a', 
        'bg_light': '#3a2525',
        'accent_rust': '#c45c2a',
        'accent_amber': '#ff8c42',
        'accent_burnt': '#8b4513',
        'text_cream': "#fa5412",
        'text_warm': "#f37033",
        'success_moss': '#8a9a5b',
        'error_wine': '#722f37',
        'border_gold': '#daa520',
    }

class RenPyParser:
    def __init__(self):
        self.char_pattern = re.compile(r'^\s*\$?\s*(\w+)\s*=\s*Character\s*\(\s*u?[\'"]([^\'"]+)[\'"]')
        self.dialogue_pattern = re.compile(r'^\s*(?:(\w+)\s*)?"(.+)"')
        self.custom_mapping = {}
        
    def load_custom_mapping(self, filepath: Path):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                self.custom_mapping = json.load(f)
            return True
        except:
            self.custom_mapping = {}
            return False
            
    def save_custom_mapping(self, filepath: Path):
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.custom_mapping, f, ensure_ascii=False, indent=2)
            return True
        except:
            return False
    
    def add_custom_tag(self, tag: str, name: str):
        self.custom_mapping[tag] = name
        
    def extract_script(self, input_path: Path, output_path: Path, with_names: bool = True, progress_callback=None) -> Dict:
        dynamic_mapping = {}
        results = {
            'dialogues': [],
            'characters_found': {},
            'total_replicas': 0,
            'success': False
        }

        # Собираем динамический словарь персонажей
        try:
            with open(input_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                total_lines = len(lines)
                
            for i, line in enumerate(lines):
                m = self.char_pattern.match(line)
                if m:
                    tag, name = m.groups()
                    dynamic_mapping[tag] = name
                    
                if progress_callback and i % 100 == 0:
                    progress = (i / total_lines) * 0.3
                    progress_callback(progress, "🔍 Поиск персонажей...")
                    
        except Exception as e:
            return results

        # Итоговый словарь (пользовательские теги имеют приоритет)
        mapping = {**static_mapping, **dynamic_mapping, **self.custom_mapping}
        results['characters_found'] = mapping

        dialogues = []
        current_speaker = None
        current_text = []

        def save_current_dialogue():
            if current_text:
                full_text = " ".join(current_text).strip()
                if full_text and not self._should_skip_line(full_text):
                    if with_names and current_speaker:
                        name = mapping.get(current_speaker, current_speaker)
                        dialogues.append(f"{name}: {full_text}")
                    else:
                        dialogues.append(full_text)

        # Обработка диалогов
        try:
            with open(input_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                total_lines = len(lines)
                
            for i, line in enumerate(lines):
                m = self.dialogue_pattern.match(line)
                if m:
                    speaker, text = m.groups()
                    
                    if self._should_skip_line(text):
                        continue

                    # Если сменился говорящий или закончилась многострочная реплика
                    if speaker != current_speaker and current_text:
                        save_current_dialogue()
                        current_text = []

                    current_speaker = speaker
                    
                    # Обработка многострочных реплик
                    if line.rstrip().endswith('\\'):
                        current_text.append(text.rstrip('\\').strip())
                    else:
                        current_text.append(text)
                        save_current_dialogue()
                        current_text = []
                        current_speaker = None

                if progress_callback and i % 100 == 0:
                    progress = 0.3 + (i / total_lines) * 0.6
                    progress_callback(progress, f"📖 Обработка строк... {i}/{total_lines}")

            # Последняя реплика
            save_current_dialogue()

        except Exception as e:
            return results

        # Сохранение результата
        try:
            if progress_callback:
                progress_callback(0.9, "💾 Сохранение результата...")
                
            dialogues_output = "\n\n".join(dialogues)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(dialogues_output)
                
            results['dialogues'] = dialogues
            results['total_replicas'] = len(dialogues)
            results['success'] = True
            
            if progress_callback:
                progress_callback(1.0, "✅ Готово!")
            
        except Exception as e:
            pass

        return results

    def _should_skip_line(self, text: str) -> bool:
        """Проверяет, нужно ли пропустить строку"""
        skip_patterns = [
            r'\.(png|jpg|jpeg|mp3|ogg|wav)',
            "persistent.", "MatrixColor", "mods/",
            r'^show\s+', r'^hide\s+', r'^scene\s+',
            r'^play\s+', r'^stop\s+', r'^queue\s+',
            r'^with\s+', r'^pause\s+'
        ]
        text_lower = text.lower()
        return any(re.search(pattern, text_lower, re.IGNORECASE) for pattern in skip_patterns)


class ModernRenPyParserGUI:
    def __init__(self):
        self.parser = RenPyParser()
        self.theme = AliceDvacheskayaTheme()
        self.setup_gui()
        
    def setup_gui(self):
        """Создаём современный интерфейс на tkinter"""
        self.root = tk.Tk()
        self.root.title("♢ Алхимический Столик Алисы Двачевской • Dialogue Extractor ♢")
        self.root.geometry("1100x850")
        self.root.configure(bg=self.theme.COLORS['bg_dark'])
        
        # Устанавливаем иконку окна
        self.set_window_icon()
        
        # Центрируем окно
        self.center_window()
        
        # Стиль для ttk элементов
        self.setup_styles()
        
        self.create_widgets()
        
    def set_window_icon(self):
        """Устанавливает иконку окна"""
        def resource_path(relative_path):
            """Получить абсолютный путь к ресурсу (работает для dev и для exe)"""
            try:
                base_path = sys._MEIPASS
            except Exception:
                base_path = os.path.abspath(".")
            return os.path.join(base_path, relative_path)

        icon_path = resource_path("alice.ico")
        print(f"Путь к иконке: {icon_path}")
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
                print(f"✓ Иконка установлена: {icon_path}")
                return
            except Exception as e:
                print(f"❌ Ошибка загрузки иконки {icon_path}: {e}")
        else:
            print(f"❌ Файл иконки не найден: {icon_path}")
        print("ℹ️ Иконка не найдена, используется стандартная иконка Windows")
        
    def center_window(self):
        """Центрирует окно на экране"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        
    def setup_styles(self):
        """Настраиваем стили для элементов"""
        style = ttk.Style()
        
        # Настройка стилей для тёмной темы
        style.configure('TFrame', background=self.theme.COLORS['bg_dark'])
        style.configure('TLabel', background=self.theme.COLORS['bg_dark'], 
                       foreground=self.theme.COLORS['text_cream'], font=('Arial', 10))
        style.configure('TLabelframe', background=self.theme.COLORS['bg_medium'],
                       foreground=self.theme.COLORS['text_cream'])
        style.configure('TLabelframe.Label', background=self.theme.COLORS['bg_medium'],
                       foreground=self.theme.COLORS['accent_amber'])
        
        # Стиль для кнопок - ИСПРАВЛЕННАЯ СТРОКА
        style.configure('Accent.TButton', background=self.theme.COLORS['accent_rust'],
                       foreground=self.theme.COLORS['text_cream'], font=('Arial', 10, 'bold'),
                       focuscolor='none')
        
        # Исправленная строка - убраны лишние скобки
        style.map('Accent.TButton', 
                 background=[('active', self.theme.COLORS['accent_amber'])])
        
        style.configure('Large.TButton', font=('Arial', 11, 'bold'), padding=(20, 15))
        
    def create_widgets(self):
        """Создаём все элементы интерфейса"""
        # Главный контейнер
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Заголовок
        title_label = tk.Label(main_frame, text="♢ АЛХИМИЧЕСКИЙ СТОЛИК АЛИСЫ ДВАЧЕВСКОЙ ♢",
                              bg=self.theme.COLORS['bg_dark'], fg=self.theme.COLORS['accent_amber'],
                              font=('Arial', 18, 'bold'))
        title_label.pack(pady=(0, 5))
        
        subtitle_label = tk.Label(main_frame, text="Dialogue Extractor • Магия извлечения диалогов",
                                bg=self.theme.COLORS['bg_dark'], fg=self.theme.COLORS['text_warm'],
                                font=('Arial', 12, 'italic'))
        subtitle_label.pack(pady=(0, 20))
        
        # Секция файлов
        file_frame = ttk.LabelFrame(main_frame, text=" 📜 СВИТОК ИСТОРИИ ", padding=15)
        file_frame.pack(fill='x', pady=10)
        
        # Входной файл
        input_frame = tk.Frame(file_frame, bg=self.theme.COLORS['bg_medium'])
        input_frame.pack(fill='x', pady=8)
        
        tk.Label(input_frame, text="Путь к .rpy файлу:", 
                bg=self.theme.COLORS['bg_medium'], fg=self.theme.COLORS['text_warm'],
                font=('Arial', 10)).pack(anchor='w')
        
        input_subframe = tk.Frame(input_frame, bg=self.theme.COLORS['bg_medium'])
        input_subframe.pack(fill='x', pady=5)
        
        self.input_entry = tk.Entry(input_subframe, bg=self.theme.COLORS['bg_light'],
                                   fg=self.theme.COLORS['text_cream'], font=('Arial', 10),
                                   width=60, insertbackground=self.theme.COLORS['text_cream'])
        self.input_entry.pack(side='left', fill='x', expand=True, padx=(0, 10))
        
        self.browse_input_btn = ttk.Button(input_subframe, text="📂 ОБЗОР", 
                                          command=self.browse_input_file,
                                          style='Accent.TButton')
        self.browse_input_btn.pack(side='right')
        
        # Выходной файл
        output_frame = tk.Frame(file_frame, bg=self.theme.COLORS['bg_medium'])
        output_frame.pack(fill='x', pady=8)
        
        tk.Label(output_frame, text="Сохранить как:", 
                bg=self.theme.COLORS['bg_medium'], fg=self.theme.COLORS['text_warm']).pack(anchor='w')
        
        output_subframe = tk.Frame(output_frame, bg=self.theme.COLORS['bg_medium'])
        output_subframe.pack(fill='x', pady=5)
        
        self.output_entry = tk.Entry(output_subframe, bg=self.theme.COLORS['bg_light'],
                                    fg=self.theme.COLORS['text_cream'], font=('Arial', 10),
                                    width=60, insertbackground=self.theme.COLORS['text_cream'])
        self.output_entry.pack(side='left', fill='x', expand=True, padx=(0, 10))
        self.output_entry.insert(0, "диалоги.txt")
        
        self.browse_output_btn = ttk.Button(output_subframe, text="💾 ВЫБРАТЬ", 
                                           command=self.browse_output_file,
                                           style='Accent.TButton')
        self.browse_output_btn.pack(side='right')
        
        # Настройки
        settings_frame = ttk.LabelFrame(main_frame, text=" ⚗️ НАСТРОЙКИ АЛХИМИКА ", padding=15)
        settings_frame.pack(fill='x', pady=10)
        
        self.names_var = tk.BooleanVar(value=True)
        self.names_check = tk.Checkbutton(settings_frame, text="Добавлять имена персонажей к репликам",
                                         variable=self.names_var,
                                         bg=self.theme.COLORS['bg_medium'],
                                         fg=self.theme.COLORS['text_cream'],
                                         selectcolor=self.theme.COLORS['accent_rust'],
                                         activebackground=self.theme.COLORS['bg_medium'],
                                         activeforeground=self.theme.COLORS['text_cream'],
                                         font=('Arial', 10))
        self.names_check.pack(anchor='w', padx=10, pady=5)
        
        # Секция тегов
        tags_frame = ttk.LabelFrame(main_frame, text=" 🎭 МАСКИ ПЕРСОНАЖЕЙ ", padding=15)
        tags_frame.pack(fill='x', pady=10)
        
        # Поля для ввода тегов
        tags_input_frame = tk.Frame(tags_frame, bg=self.theme.COLORS['bg_medium'])
        tags_input_frame.pack(fill='x', padx=10, pady=10)
        
        tk.Label(tags_input_frame, text="Тег:", 
                bg=self.theme.COLORS['bg_medium'], fg=self.theme.COLORS['text_warm']).grid(row=0, column=0, sticky='w')
        
        tk.Label(tags_input_frame, text="Имя персонажа:", 
                bg=self.theme.COLORS['bg_medium'], fg=self.theme.COLORS['text_warm']).grid(row=0, column=1, sticky='w')
        
        self.tag_entry = tk.Entry(tags_input_frame, bg=self.theme.COLORS['bg_light'],
                                 fg=self.theme.COLORS['text_cream'], font=('Arial', 10),
                                 width=25, insertbackground=self.theme.COLORS['text_cream'])
        self.tag_entry.grid(row=1, column=0, sticky='ew', padx=(0, 10))
        
        self.name_entry = tk.Entry(tags_input_frame, bg=self.theme.COLORS['bg_light'],
                                  fg=self.theme.COLORS['text_cream'], font=('Arial', 10),
                                  width=25, insertbackground=self.theme.COLORS['text_cream'])
        self.name_entry.grid(row=1, column=1, sticky='ew', padx=(0, 10))
        
        self.add_tag_btn = ttk.Button(tags_input_frame, text="✨ ДОБАВИТЬ", 
                                     command=self.add_custom_tag,
                                     style='Accent.TButton')
        self.add_tag_btn.grid(row=1, column=2, padx=(10, 0))
        
        tags_input_frame.columnconfigure(0, weight=1)
        tags_input_frame.columnconfigure(1, weight=1)
        
        # Кнопки управления тегами
        tags_buttons_frame = tk.Frame(tags_frame, bg=self.theme.COLORS['bg_medium'])
        tags_buttons_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Button(tags_buttons_frame, text="💾 Сохранить теги", 
                  command=self.save_tags, style='Accent.TButton').pack(side='left', padx=(0, 10))
        
        ttk.Button(tags_buttons_frame, text="📂 Загрузить теги", 
                  command=self.load_tags, style='Accent.TButton').pack(side='left')
        
        # Главная кнопка
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x', pady=20)
        
        self.run_button = ttk.Button(button_frame, text="🔮 СОВЕРШИТЬ АЛХИМИЮ!", 
                                    command=self.run_parser,
                                    style='Accent.TButton')
        self.run_button.config(style='Large.TButton')
        self.run_button.pack(pady=10)
        
        # Прогресс бар
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill='x', pady=10)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var,
                                           maximum=100, length=900)
        self.progress_bar.pack(fill='x', pady=5)
        
        self.progress_label = tk.Label(progress_frame, text="Готов к великой алхимии...",
                                      bg=self.theme.COLORS['bg_dark'], fg=self.theme.COLORS['text_warm'],
                                      font=('Arial', 9))
        self.progress_label.pack()
        
        # Результаты
        results_frame = ttk.LabelFrame(main_frame, text=" 📖 ЛЕТОПИСЬ РЕЗУЛЬТАТОВ ", padding=15)
        results_frame.pack(fill='both', expand=True, pady=10)
        
        self.result_text = scrolledtext.ScrolledText(results_frame,
                                                    bg=self.theme.COLORS['bg_light'],
                                                    fg=self.theme.COLORS['text_cream'],
                                                    insertbackground=self.theme.COLORS['text_cream'],
                                                    font=('Arial', 9),
                                                    wrap=tk.WORD,
                                                    height=15)
        self.result_text.pack(fill='both', expand=True, padx=5, pady=5)
        self.result_text.insert('1.0', "Здесь будут отображаться результаты алхимии...\n\n"
                                      "Выберите .rpy файл и нажмите кнопку 'СОВЕРШИТЬ АЛХИМИЮ!'")
        self.result_text.config(state='disabled')
        
    def browse_input_file(self):
        """Обзор входного файла"""
        filename = filedialog.askopenfilename(
            title="Выберите свиток истории (.rpy файл)",
            filetypes=[
                ("Ren'Py files", "*.rpy"),
                ("All files", "*.*")
            ]
        )
        if filename:
            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, filename)
            
    def browse_output_file(self):
        """Обзор выходного файла"""
        filename = filedialog.asksaveasfilename(
            title="Сохранить летопись как...",
            defaultextension=".txt",
            filetypes=[
                ("Text files", "*.txt"),
                ("All files", "*.*")
            ],
            initialfile="диалоги.txt"
        )
        if filename:
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, filename)
            
    def add_custom_tag(self):
        """Добавление пользовательского тега"""
        tag = self.tag_entry.get().strip()
        name = self.name_entry.get().strip()
        
        if tag and name:
            self.parser.add_custom_tag(tag, name)
            messagebox.showinfo("✨ Маска создана!", f"Теперь '{tag}' означает '{name}'")
            self.tag_entry.delete(0, tk.END)
            self.name_entry.delete(0, tk.END)
        else:
            messagebox.showwarning("💫 Внимание!", "Заполните оба поля!")
            
    def save_tags(self):
        """Сохранение тегов в файл"""
        filename = filedialog.asksaveasfilename(
            title="Сохранить коллекцию масок...",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile="персонажи.json"
        )
        if filename and self.parser.save_custom_mapping(Path(filename)):
            messagebox.showinfo("💾 Коллекция сохранена", "Ваши маски в безопасности")
            
    def load_tags(self):
        """Загрузка тегов из файла"""
        filename = filedialog.askopenfilename(
            title="Загрузить коллекцию масок...",
            filetypes=[("JSON files", "*.json")]
        )
        if filename and self.parser.load_custom_mapping(Path(filename)):
            messagebox.showinfo("📂 Коллекция загружена", "Маски готовы к использованию")
            
    def update_progress(self, value, text):
        """Обновление прогресса"""
        self.progress_var.set(value * 100)
        self.progress_label.config(text=text)
        self.root.update_idletasks()
        
    def run_parser(self):
        """Запуск парсера"""
        input_file = self.input_entry.get().strip()
        output_file = self.output_entry.get().strip()
        
        if not input_file:
            messagebox.showerror("🔮 Ошибка", "Выберите свиток истории (.rpy файл)!")
            return
            
        if not output_file:
            messagebox.showerror("🔮 Ошибка", "Укажите путь для сохранения летописи!")
            return
            
        # Проверяем существование входного файла
        if not Path(input_file).exists():
            messagebox.showerror("🔮 Свиток не найден", f"Файл не существует:\n{input_file}")
            return
            
        # Блокируем кнопку на время обработки
        self.run_button.config(state='disabled')
        self.result_text.config(state='normal')
        self.result_text.delete('1.0', tk.END)
        self.result_text.insert('1.0', "🕯️ Зажигаю свечи алхимии...\n\n")
        self.root.update_idletasks()
        
        def parse_wrapper():
            result = self.parser.extract_script(
                Path(input_file), 
                Path(output_file),
                with_names=self.names_var.get(),
                progress_callback=self.update_progress
            )
            
            # Возвращаемся в основной поток для обновления UI
            self.root.after(0, lambda: self.show_results(result))
            
        # Запускаем в отдельном потоке
        thread = threading.Thread(target=parse_wrapper)
        thread.daemon = True
        thread.start()
        
    def show_results(self, result: Dict):
        """Показ результатов"""
        self.run_button.config(state='normal')
        self.result_text.delete('1.0', tk.END)
        
        if result['success']:
            result_display = "✨ АЛХИМИЯ СОВЕРШЕНА! ✨\n\n"
            result_display += f"📖 Извлечено реплик: {result['total_replicas']}\n\n"
            result_display += "🎭 Распознанные лики:\n"
            
            for tag, name in list(result['characters_found'].items())[:10]:
                result_display += f"   • {tag} → {name}\n"
                
            if len(result['characters_found']) > 10:
                result_display += f"   ... и ещё {len(result['characters_found']) - 10} персонажей\n"
                
            result_display += f"\n💾 Летопись сохранена: {self.output_entry.get()}\n\n"
            
            if result['dialogues']:
                result_display += "📜 Первые строки летописи:\n\n"
                for i, dialogue in enumerate(result['dialogues'][:5], 1):
                    result_display += f"{i}. {dialogue}\n\n"
                    
            self.result_text.insert('1.0', result_display)
            
            # Показываем уведомление об успехе
            messagebox.showinfo("🎉 АЛХИМИЯ УСПЕШНА!", 
                              f"Диалоги успешно извлечены!\n\n"
                              f"Извлечено реплик: {result['total_replicas']}\n"
                              f"Сохранено в: {self.output_entry.get()}")
            
        else:
            error_text = "💫 Заклинание не сработало...\n\n"
            error_text += "Возможные причины:\n"
            error_text += "• Свиток повреждён или запечатан\n"
            error_text += "• Это не настоящий свиток Ren'Py\n"
            error_text += "• Магия встретила сопротивление\n"
            error_text += "• Проверьте путь к файлу\n"
            self.result_text.insert('1.0', error_text)
            
        self.result_text.config(state='disabled')
        
    def run(self):
        """Запуск приложения"""
        self.root.mainloop()


def main():
    app = ModernRenPyParserGUI()
    app.run()


if __name__ == "__main__":
    main()