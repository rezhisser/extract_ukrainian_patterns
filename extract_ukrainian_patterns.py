import os
import re
import pandas as pd

# 🔧 Налаштування
from config_local import project_path, output_path
extensions = ['.html', '.ts']
ignore_dirs = [
    '\\mriia-sync\\',
]
ignore_patterns = [
    r'\bimport\b', r'\bfrom\b', r'\bexport\b', r'\bconsole\.log\b',
    r'\bselector\b', r'\bstyleUrls\b', r'\btemplateUrl\b', r'\b@.*\b',
    r'\btrue\b', r'\bfalse\b', r'\bnull\b'
]
ukrainian_pattern = re.compile(r'[А-Яа-яІіЇїЄєҐґ]{2,}')
results = []

def is_technical_line(line):
    return any(re.search(pattern, line) for pattern in ignore_patterns)

def has_latin(word):
    return re.search(r'[A-Za-z]', word) is not None

def has_ukrainian(word):
    return re.search(r'[А-Яа-яІіЇїЄєҐґ]', word) is not None

def extract_ukrainian_text_and_pattern(line):
    patterns = [
        ("interpolated_with_span", r'([^<>]*[А-Яа-яІіЇїЄєҐґ]{2,}[^<>]*)\s*<span[^>]*>\s*{{[^}]+}}\s*</span>'),
        ("single_quotes", r"'([^'\\]*(?:\\.[^'\\]*)*)'"),
        ("double_quotes", r'"([^"]*[А-Яа-яІіЇїЄєҐґ\'`]{2,}[^"]*)"'),
        ("backticks", r'`([^`]*[А-Яа-яІіЇїЄєҐґ\'`]{2,}[^`]*)`'),
        ("html_text", r'>\s*([^<]*[А-Яа-яІіЇїЄєҐґ]{2,}[^<]*)\s*<')
    ]

    extracted_chunks = []

    for name, pattern in patterns:
        matches = re.findall(pattern, line)
        if matches:
            for match in matches:
                text = match.replace("\\'", "'")
                no_vars = re.sub(r'\${[^}]+}', '', text)

                # зберігаємо розмітку типу <b>, <br>, <span>
                no_vars_preserved_tags = re.sub(r'<(?!/?(b|br|i|span)[ >])[^>]+>', '', no_vars)

                # ✂️ Витягуємо фрази, що містять українські літери
                phrases = [phrase for phrase in re.findall(r"[^%{}<>]+", no_vars_preserved_tags) if
                           ukrainian_pattern.search(phrase)]

                for phrase in phrases:
                    words = phrase.strip().split()
                    fixed_words = []
                    for word in words:
                        if has_ukrainian(word) and has_latin(word):
                            fixed_words.append(word)
                        else:
                            fixed_words.append(word)

                    fixed_text = ' '.join(fixed_words)

                    if ukrainian_pattern.search(fixed_text):
                        contains_latin = any(has_ukrainian(w) and has_latin(w) for w in fixed_words)
                        extracted_chunks.append((fixed_text.strip(), name, contains_latin))

            break  # 🛑 припиняємо після першого знайденого патерну

    return extracted_chunks

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

# 🔍 Пошук
for root, _, files in os.walk(project_path):
    for file in files:
        if not any(file.endswith(ext) for ext in extensions):
            continue

        filepath = os.path.join(root, file)

        if any(ignored in filepath for ignored in ignore_dirs):
            continue

        try:
            with open(filepath, encoding='utf-8') as f:
                for i, line in enumerate(f, 1):
                    if '//' in line:
                        comment_index = line.find('//')
                        protocol_index = line.find('://')
                        if not (protocol_index != -1 and protocol_index - 1 < comment_index < protocol_index + 3):
                            line = line[:comment_index]

                    if ukrainian_pattern.search(line) and not is_technical_line(line):
                        chunks = extract_ukrainian_text_and_pattern(line)
                        for extracted, pattern, contains_latin in chunks:
                            results.append({
                                'Filename': filepath,
                                'Line Number': i,
                                'Text': extracted,
                                'Pattern': pattern,
                                'Source': detect_source(line),
                                'Contains Latin': contains_latin,
                                'Full Line': line.strip()
                            })
        except Exception as e:
            print(f'❌ Помилка при читанні {filepath}: {e}')

# 🧾 Унікальні записи
df = pd.DataFrame(results).drop_duplicates()

# 💾 Збереження
df.to_excel(output_path, index=False)
print(f'✅ Збережено в {output_path}')
