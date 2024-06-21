import os
import hashlib
from bs4 import BeautifulSoup, Comment
import unicodedata
from warcio.archiveiterator import ArchiveIterator
import re
import csv
from sudachipy import tokenizer, dictionary
from datetime import datetime
from fuzzywuzzy import fuzz

tokenizer_obj = dictionary.Dictionary().create()
mode = tokenizer.Tokenizer.SplitMode.C

def mark_proper_nouns(text):
    tokens = tokenizer_obj.tokenize(text, mode)
    marked_text = ""
    for token in tokens:
        if token.part_of_speech()[0] == '名詞' and token.part_of_speech()[1] == '固有名詞':
            marked_text += f"<NE>{token.surface()}</NE>"
        else:
            marked_text += token.surface()
    return marked_text

def remove_duplicates_and_keep_last(texts, threshold=90):
    unique_texts = []
    seen_titles = set()
    last_seen_index = {}

    for i, text in enumerate(texts):
        for seen in seen_titles:
            if fuzz.ratio(text, seen) > threshold:
                last_seen_index[seen] = i
                break
        seen_titles.add(text)
    
    skip_to_index = -1
    for i, text in enumerate(texts):
        if i <= skip_to_index:
            continue
        if text in last_seen_index:
            skip_to_index = last_seen_index[text]
        unique_texts.append(text)
    
    return unique_texts


def extract_date(text):
    date_pattern = r'(\d{4}年\d{2}月\d{2}日 \d{2}:\d{2})'
    date_match = re.search(date_pattern, text)
    
    date = convert_date_format(date_match.group(1)) if date_match else 'Неизвестно'
    remaining_text = re.sub(date_pattern, '', text, count=1) if date_match else text
    
    return date, remaining_text.strip()

def remove_unwanted_phrases_from_end(text):
    unwanted_patterns = [
        r'<NE>Twitter</NE>\(公式アカウント\)',
        r'<NE>Facebook</NE>\(ファンページ\)',
        r'<NE>Google</NE>\+',
        r'Ustream',
        r'ニコニコ',
        r'<NE>YouTube</NE>',
        r'関連サービス',
        r'livedoor',
        r'livedoor ニュース',
        r'© <NE>LINE</NE> Corporation',
        r'ログイン',
        r'ログインするアカウントをお選びください。',
        r'以下のいずれかのアカウントでBLOGOSにログインすることができます。',
        r'コメントを書き込むには',
        r'FacebookID、TwitterID のいずれかで認証を行う必要があります。',
        r'※livedoorIDでログインした場合、ご利用できるのはフォロー機能、マイページ機能、支持するボタンのみとなります。',
        r'<NE>twitter</NE> ID',
        r'<NE>facebook</NE> ID',
        r'livedoor ID',
        r'ログインしてBLOGOSをもっと便利に',
        r'Tweet \d+ コメント'
    ]

    unwanted_patterns.sort(key=lambda x: len(x), reverse=True)

    for pattern in unwanted_patterns:
        text = re.sub(pattern, '', text)

    text = re.sub(r'\s+', ' ', text).strip()

    return text

def normalize_text(text):
    return unicodedata.normalize('NFKC', text)

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

def clean_text(text):
    text = re.sub(r'(?:(https?://)\S+(?=\s|$))(\1\S+)', r'\1', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def remove_image_links(text):
    img_pattern = r'\bhttps?://(?:\S+?\.jpg|.*?\.jpg(?:\?.*?)?)\b'
    return re.sub(img_pattern, '', text)

def remove_multiple_links(links):
    return links[:1]

def convert_date_format(date_str):
    try:
        dt = datetime.strptime(date_str, '%Y年%m月%d日 %H:%M')
        return dt.strftime('%Y-%m-%d %H:%M')
    except ValueError:
        return 'Неизвестно'

def remove_text_in_square_brackets(text):
    text = re.sub(r'\[[^\]]*\]', '', text)
    return text.strip()

def extract_date(text):
    date_pattern = r'(\d{4}年\d{2}月\d{2}日 \d{2}:\d{2})'
    date_match = re.search(date_pattern, text)
    
    date = convert_date_format(date_match.group(1)) if date_match else 'Неизвестно'
    
    text = re.sub(date_pattern, '', text)
    
    return date, text

def remove_unwanted_sections(text):
    patterns = [
        r'モバイル版へ戻る[\s\S]*?(?=\s|$)',      
        r'新規登録 / ログイン[\s\S]*?(?=\s|$)',  
        r'新着記事[\s\S]*?(?=\s|$)',            
        r'ピックアップ[\s\S]*?(?=\s|$)',        
        r'ランキング[\s\S]*?(?=\s|$)',          
        r'コメント[\s\S]*?(?=\s|$)',            
        r'議論[\s\S]*?(?=\s|$)',                
        r'ブロガー[\s\S]*?(?=\s|$)',            
        r'政治家[\s\S]*?(?=\s|$)',             
        r'アンケート[\s\S]*?(?=\s|$)',         
        r'<NE>facebook</NE>[\s\S]*?(?=\s|$)',   
        r'livedoor[\s\S]*?(?=\s|$)',            
        r'<NE>twitter</NE>[\s\S]*?(?=\s|$)',    
        r'ID[\s\S]*?(?=\s|$)',                  
        r'TwitterID[\s\S]*?(?=\s|$)',           
        r'google[\s\S]*?(?=\s|$)',              
        r'BLOGOS[\s\S]*?(?=\s|$)',              
        r'FacebookID[\s\S]*?(?=\s|$)',          
        r'TwitterID[\s\S]*?(?=\s|$)',           
        r'Facebook[\s\S]*?(?=\s|$)',            
        r'facebook[\s\S]*?(?=\s|$)',            
        r'<NE>facebook</NE>[\s\S]*?(?=\s|$)',   
        r'<NE>facebook</NE>',                   
        r'facebook',                            
        r'FacebookID[\s\S]*?(?=\s|$)',          
        r'TwitterID[\s\S]*?(?=\s|$)',  
        r'Facebook[\s\S]*?(?=\s|$)',   
    ]

    for pattern in patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)

    return text

def process_and_save_data(base_directory, csv_file_path):
    seen_texts = set()
    counter = 0
    
    with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['index', 'date', 'text', 'links']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for file in os.listdir(base_directory):
            file_path = os.path.join(base_directory, file)
            if os.path.isfile(file_path) and file.endswith('.warc'):
                print(f'Processing file: {file_path}')
                with open(file_path, 'rb') as stream:
                    for index, record in enumerate(ArchiveIterator(stream)):
                        if record.rec_type == 'response' and 'text/html' in record.http_headers.get_header('Content-Type'):
                            url = record.rec_headers.get_header('WARC-Target-URI')
                            payload = record.content_stream().read()

                            
                            cleaned_text, links = clean_html_and_extract_links(payload.decode('utf-8', errors='ignore'))
                            
                            normalized_text = normalize_text(cleaned_text)
                            
                            date, text_for_marking = extract_date(normalized_text)
                            
                            marked_text = mark_proper_nouns(text_for_marking)

                            
                            cleaned_text = clean_text(marked_text)
                            final_text = remove_image_links(cleaned_text)

                            final_text = remove_text_in_square_brackets(final_text)

                            links = remove_multiple_links(links)

                            final_text = remove_unwanted_sections(final_text)
                            
                            final_text = remove_unwanted_phrases_from_end(final_text)

                            lines = final_text.split('\n')
                            final_text = '\n'.join(remove_duplicates_and_keep_last(lines))

                            text_hash = hashlib.md5(final_text.encode('utf-8')).hexdigest()
                            if text_hash in seen_texts:
                                continue
                            seen_texts.add(text_hash)

                            writer.writerow({'index': counter, 'date': date, 'text': final_text, 'links': ','.join(links)})
                            counter += 1

                            print(f'Очищенный текст из {url} сохранен в CSV')


def main():
    base_directory = '/Users/aleksandratopalidi/Desktop/MLContest/Data'
    target_directory = '/Users/aleksandratopalidi/Desktop/MLContest/Clickhouse'
    subfolders = [ '2023']
    
    os.makedirs(target_directory, exist_ok=True)
    
    for folder in subfolders:
        subfolder_path = os.path.join(base_directory, folder)
        csv_file_path = os.path.join(target_directory, f'{folder}.csv')
        process_and_save_data(subfolder_path, csv_file_path)

if __name__ == '__main__':
    main()

