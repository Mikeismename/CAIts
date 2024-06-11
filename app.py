import json
from transformers import pipeline, AutoTokenizer, AutoModelForQuestionAnswering
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import requests
from elasticsearch import Elasticsearch

# Загрузка конфигурации
with open('config.json', 'r') as config_file:
    config = json.load(config_file)

# Настройка подключения к Elasticsearch
client = Elasticsearch(
    cloud_id=config['ELASTICSEARCH_CLOUD_ID'],
    basic_auth=("elastic", config['ELASTIC_PASSWORD'])
)

# Загрузка модели и токенизатора BERT для QA
tokenizer = AutoTokenizer.from_pretrained("bert-base-multilingual-cased")
model = AutoModelForQuestionAnswering.from_pretrained("bert-base-multilingual-cased")
qa_pipeline = pipeline("question-answering", model=model, tokenizer=tokenizer)

# Функция перевода текста с использованием Yandex Translate API
def translate_text(text, target_language='ru'):
    translate_url = "https://translate.api.cloud.yandex.net/translate/v2/translate"
    headers = {
        "Authorization": f"Api-Key {config['YANDEX_TRANSLATE_API_KEY']}",
        "Content-Type": "application/json"
    }
    data = {
        "targetLanguageCode": target_language,
        "texts": [text]
    }
    response = requests.post(translate_url, headers=headers, json=data)
    translation = response.json()['translations'][0]['text']
    return translation

# Функция для обработки запроса
def process_query(query, index_names):
    results = []
    for index_name in index_names:
        response = client.search(
            index=index_name,
            body={
                "query": {
                    "match": {
                        "content": query
                    }
                }
            }
        )
        for hit in response['hits']['hits']:
            content = hit['_source']['content']
            s3_key = hit['_source']['s3_key']
            result = qa_pipeline({'question': query, 'context': content})
            if result['score'] > 0.1:  # Применяем порог для фильтрации нерелевантных ответов
                translated_answer = translate_text(result['answer'])
                results.append({
                    'answer': translated_answer,
                    'score': result['score'],
                    'context': s3_key
                })
    return results

# Обработчики для Telegram бота
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("2019 - Данные до 2019 года", callback_data='data_2019')],
        [InlineKeyboardButton("2020 - Добавить данные за 2020", callback_data='add_2020')],
        [InlineKeyboardButton("2021 - Добавить данные за 2021", callback_data='add_2021')],
        [InlineKeyboardButton("2022 - Добавить данные за 2022", callback_data='add_2022')],
        [InlineKeyboardButton("2023 - Добавить данные за 2023", callback_data='add_2023')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Привет! Я бот для новостей. Выберите действие:', reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    action = query.data.split('_')[0]
    year = query.data.split('_')[1]

    if action == 'data':
        index_names = ['index_pre_2019']
    elif year == '2023':
        index_names = ['index_2022', 'index_2023']
    else:
        index_names = [f"index_{year}"]

    results = process_query('Ваш запрос', index_names)
    response_text = '\n'.join([f"{res['answer']} (Источник: {res['context']})" for res in results])
    await query.edit_message_text(text=response_text)

# Обработчик запроса от пользователя
async def handle_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_query = update.message.text
    index_names = ["index_2022", "index_2023"]  # Пример для 2022 и 2023 годов
    results = process_query(user_query, index_names)
    response_text = '\n'.join([f"{res['answer']} (Источник: {res['context']})" for res in results])
    await update.message.reply_text(response_text)

def main() -> None:
    print("Запуск бота")
    application = Application.builder().token(config['TELEGRAM_BOT_TOKEN']).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(CommandHandler("query", handle_query))

    application.run_polling()

if __name__ == '__main__':
    main()
