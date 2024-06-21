import pandas as pd
from clickhouse_driver import Client

host = 'localhost'
user = 'default'
password = ''
database = 'mydatabase'

client = Client(host=host, user=user, password=password, database=database)

file_path = 'embeddings.csv'
data = pd.read_csv(file_path)

new_columns = [f'column{i+1}' for i in range(len(data.columns))]
data.columns = new_columns

columns = data.columns.tolist()
print("Columns:", columns)  # Вывод имен столбцов для проверки

insert_query = f"INSERT INTO mydatabase.embeddings ({', '.join(columns)}) VALUES"

batch_size = 1000  # Размер пакета
for i in range(0, len(data), batch_size):
    batch = data.iloc[i:i + batch_size]
    client.execute(insert_query, [tuple(row) for row in batch.values])

print("Данные успешно отправлены в ClickHouse")
