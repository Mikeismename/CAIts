import pandas as pd
from clickhouse_driver import Client
from transformers import BertTokenizer, BertModel
import torch
import numpy as np


host = 'localhost'
user = 'default'
password = ''
database = 'mydatabase'


client = Client(host=host, user=user, password=password, database=database)

# Инициализация токенизатора и модели
tokenizer = BertTokenizer.from_pretrained('yandex/yandex-gpt')  
model = BertModel.from_pretrained('yandex/yandex-gpt')

def get_embeddings(text):
    inputs = tokenizer(text, return_tensors='pt', truncation=True, padding=True)
    with torch.no_grad():
        outputs = model(**inputs)
    return outputs.last_hidden_state.mean(dim=1).numpy()[0]

def search_clickhouse(embedding, time):

    query_time = f"SELECT * FROM embeddings WHERE time = '{time}'"
    results_time = client.execute(query_time)
    
    if results_time:

        results = []
        for row in results_time:
            db_embedding = np.array(row[1:385]) 
            similarity = np.dot(embedding, db_embedding) / (np.linalg.norm(embedding) * np.linalg.norm(db_embedding))
            results.append((similarity, row))

        results.sort(key=lambda x: x[0], reverse=True)
        
        if results:
            # Возврат самой схожей строки и ее URL
            best_match = results[0][1]
            url = best_match[-1]  
            return url

    return None

def main(query, time):
    embedding = get_embeddings(query)
    url = search_clickhouse(embedding, time)
    if url:
        print(f"Found URL: {url}")
    else:
        print("No matching documents found.")

if __name__ == "__main__":
    query = "やはがきによる人架空請求誕||硬!dたにコモど全ルルコジアルルアたレア"
    time = "2023-06-21"  
    main(query, time)
