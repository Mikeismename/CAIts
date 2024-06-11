import json
import boto3
from elasticsearch import Elasticsearch, helpers
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Загрузка конфигурации
with open('config.json', 'r') as config_file:
    config = json.load(config_file)

# Настройка boto3 для S3
session = boto3.session.Session()
s3 = session.client(
    service_name='s3',
    endpoint_url='https://storage.yandexcloud.net',
    aws_access_key_id=config['YANDEX_ACCESS_KEY_ID'],
    aws_secret_access_key=config['YANDEX_SECRET_ACCESS_KEY']
)

# Создание экземпляра клиента Elasticsearch
client = Elasticsearch(
    cloud_id=config['ELASTICSEARCH_CLOUD_ID'],
    basic_auth=("elastic", config['ELASTIC_PASSWORD'])
)

# Проверка подключения к Elasticsearch
try:
    client.info()
    logging.info("Successfully connected to Elasticsearch")
except Exception as e:
    logging.error(f"Failed to connect to Elasticsearch: {e}")
    exit(1)

# Функция для загрузки и индексации файлов
def index_files_from_s3(bucket_name, s3_prefix, max_files=1000):  # Уменьшили количество файлов для тестирования
    try:
        # Список объектов в бакете с заданным префиксом
        response = s3.list_objects_v2(Bucket=bucket_name, Prefix=s3_prefix)
        if 'Contents' not in response:
            logging.info(f"No files found in S3 prefix '{s3_prefix}'")
            return
        
        actions = []

        for idx, obj in enumerate(response['Contents']):
            if idx >= max_files:
                break
            s3_key = obj['Key']
            file_obj = s3.get_object(Bucket=bucket_name, Key=s3_key)
            content = file_obj['Body'].read().decode('utf-8')
            
            logging.info(f"Indexing file {s3_key} with content length {len(content)}")

            # Определение индекса на основе года
            year = s3_prefix.split('/')[0]
            index_name = f"index_{year}"

            # Создаем действие для индексации в Elasticsearch
            action = {
                "_index": index_name,
                "_source": {
                    "content": content,
                    "s3_key": s3_key
                }
            }
            actions.append(action)
        
        # Выполняем пакетную индексацию
        if actions:
            helpers.bulk(client, actions)
            logging.info(f"Successfully indexed {len(actions)} files from S3 prefix '{s3_prefix}' to index '{index_name}'")
        else:
            logging.info(f"No files found in S3 prefix '{s3_prefix}'")
    except Exception as e:
        logging.error(f"An error occurred: {e}")

if __name__ == "__main__":
    # Пример использования
    bucket_name = config['S3_BUCKET']
    s3_prefixes = ["2022", "2023"]  # Добавьте здесь другие годы по мере необходимости

    # Индексация файлов для каждого префикса
    for s3_prefix in s3_prefixes:
        index_files_from_s3(bucket_name, s3_prefix)
