import os
import hashlib
import json
import requests
from bs4 import BeautifulSoup, Comment
import unicodedata
from warcio.archiveiterator import ArchiveIterator

# Загрузка конфигурации
with open('config.json', 'r') as config_file:
    config = json.load(config_file)

# Функция очистки HTML контента и извлечения ссылок
def clean_html_and_extract_links(html_content):
    soup = BeautifulSoup(html_content, 'lxml')
    for script in soup(["script", "style", "footer", "header", "nav", "aside", "form"]):
        script.decompose()
    for element in soup(text=lambda text: isinstance(text, Comment)):
        element.extract()
    for ad in soup.find_all(class_=["ad", "advertisement"]):
        ad.decompose()
    
    links = [a['href'] for a in soup.find_all('a', href=True)]
    text = soup.get_text(separator=' ')
    return text, links

# Функция генерации имени файла
def generate_filename(url, index):
    max_length = 100
    filename = os.path.basename(url).replace('/', '_') + f"_{index}"
    if len(filename) == 0:
        filename = hashlib.md5(url.encode('utf-8')).hexdigest()
    if len(filename) > max_length:
        filename = hashlib.md5(url.encode('utf-8')).hexdigest() + f'_{index}.txt'
    else:
        filename = filename[:max_length] + f'_{index}.txt'
    return filename

# Функция нормализации текста
def normalize_text(text):
    return unicodedata.normalize('NFKC', text)

# Функция обработки и сохранения данных
def process_and_save_data(base_directory, target_directory):
    seen_texts = set()
    for root, dirs, files in os.walk(base_directory):
        for dir_name in dirs:
            source_dir = os.path.join(root, dir_name)
            target_dir = os.path.join(target_directory, dir_name)
            os.makedirs(target_dir, exist_ok=True)
            
            for file in os.listdir(source_dir):
                file_path = os.path.join(source_dir, file)
                if file.endswith('.warc'):
                    with open(file_path, 'rb') as stream:
                        for index, record in enumerate(ArchiveIterator(stream)):
                            if record.rec_type == 'response' and 'text/html' in record.http_headers.get_header('Content-Type'):
                                url = record.rec_headers.get_header('WARC-Target-URI')
                                payload = record.content_stream().read()
                                cleaned_text, links = clean_html_and_extract_links(payload.decode('utf-8', errors='ignore'))
                                normalized_text = normalize_text(cleaned_text)

                                text_hash = hashlib.md5(normalized_text.encode('utf-8')).hexdigest()
                                if text_hash in seen_texts:
                                    continue
                                seen_texts.add(text_hash)

                                output_file_name = generate_filename(url, index)
                                if not output_file_name.endswith('.txt'):
                                    output_file_name += '.txt'
                                output_file_path = os.path.join(target_dir, output_file_name)

                                with open(output_file_path, 'w', encoding='utf-8') as output_file:
                                    output_file.write(normalized_text + "\n\nLinks:\n" + "\n".join(links))
                                    print(f'Очищенный текст из {url} сохранен в {output_file_path}')

# Основная функция
def main():
    base_directory = '/private/tmp/unpacked_files'
    target_directory = '/Users/aleksandratopalidi/Desktop/HackatonProductAI'
    process_and_save_data(base_directory, target_directory)

if __name__ == '__main__':
    main()
