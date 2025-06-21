import os
import re
import pandas as pd

# 🔧 Налаштування
from config_local import project_path
extensions = ['.html', '.ts']
ignore_patterns = [
    r'\bimport\b', r'\bfrom\b', r'\bexport\b', r'\bconsole\.log\b',
    r'\bselector\b', r'\bstyleUrls\b', r'\btemplateUrl\b', r'\b@.*\b',
    r'\btrue\b', r'\bfalse\b', r'\bnull\b'
]
ukrainian_pattern = re.compile(r'[А-Яа-яІіЇїЄєҐґ]{2,}')
results = []

# Технічні рядки
def is_technical_line(line):
    return any(re.search(pattern, line) for pattern in ignore_patterns)

# Функція витягування тексту та визначення патерну
def extract_ukrainian_text_and_pattern(line):
    patterns = [
        ("single_quotes", r"'([^']*[А-Яа-яІіЇїЄєҐґ\'`]{2,}[^']*)'"),
        ("double_quotes", r'"([^"]*[А-Яа-яІіЇїЄєҐґ\'`]{2,}[^"]*)"'),
        ("backticks", r'`([^`]*[А-Яа-яІіЇїЄєҐґ\'`]{2,}[^`]*)`'),
        ("html_text", r'>\s*([А-Яа-яІіЇїЄєҐґ0-9 ,.\-:;!?()\'"]{3,})\s*<')
    ]

    for name, pattern in patterns:
        matches = re.findall(pattern, line)
        if matches:
            cleaned_results = []
            for match in matches:
                # 1. Деекрануємо апострофи
                text = match.replace("\\'", "'")

                # 2. Видаляємо динамічні вставки типу ${...}
                no_vars = re.sub(r'\${[^}]+}', '', text)

                # 3. Замінюємо латинське 'i' на українське 'і' в кириличних словах
                def fix_i(word):
                    if re.search(r'[А-Яа-яІіЇїЄєҐґ]', word):  # якщо є хоч одна кирилична літера
                        return word.replace('i', 'і')
                    return word

                # 4. Витягуємо українські фрази та застосовуємо fix_i
                ukrainian_chunks = re.findall(r"[А-Яа-яІіЇїЄєҐґ0-9 ,.\-:;!?()']{2,}", no_vars)
                fixed = [fix_i(chunk.strip()) for chunk in ukrainian_chunks if chunk.strip()]
                cleaned_results.extend(fixed)

            if cleaned_results:
                return ' | '.join(cleaned_results), name
    return None, None


# Визначаємо джерело (source): атрибут чи шаблон
def detect_source(line):
    if '<ng-template' in line or '</ng-template>' in line:
        return 'ng-template'
    if re.search(r'tooltip|data-tooltip|data-awesome-tooltip', line):
        return 'tooltip'
    if re.search(r'placeholder\s*=', line):
        return 'placeholder'
    if re.search(r'title\s*=', line):
        return 'title'
    return 'innerText'

# Пошук
for root, _, files in os.walk(project_path):
    for file in files:
        if any(file.endswith(ext) for ext in extensions):
            filepath = os.path.join(root, file)
            try:
                with open(filepath, encoding='utf-8') as f:
                    for i, line in enumerate(f, 1):
                        if '//' in line:
                            comment_index = line.find('//')
                            protocol_index = line.find('://')
                            if not (
                                    protocol_index != -1 and comment_index > protocol_index - 1 and comment_index < protocol_index + 3):
                                line = line[:comment_index]
                        if ukrainian_pattern.search(line) and not is_technical_line(line):
                            extracted, pattern = extract_ukrainian_text_and_pattern(line)
                            if extracted:
                                source = detect_source(line)
                                results.append({
                                    'Filename': filepath,
                                    'Line Number': i,
                                    'Text': extracted,
                                    'Pattern': pattern,
                                    'Source': source,
                                    'Full Line': line.strip()
                                })
            except Exception as e:
                print(f'❌ Помилка при читанні {filepath}: {e}')

# Унікальні записи
df = pd.DataFrame(results).drop_duplicates()

# Збереження
from config_local import output_path
df.to_excel(output_path, index=False)
print(f'✅ Збережено в {output_path}')
