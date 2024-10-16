import os
import logging
import requests
import sys
import time
from http import HTTPStatus

from dotenv import load_dotenv
from telebot import apihelper, TeleBot

from extensions import (
    InvalidTokenError,
    InvalidHomeWorkName,
    InvalidHomeWorkStatus,
    InvalidStatusCode,
    APIRequestError,
)

load_dotenv()

logger = logging.getLogger(__name__)

formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

handler = logging.StreamHandler(stream=sys.stdout)
handler.setFormatter(formatter)
handler.setLevel(logging.DEBUG)

logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
PAUSE_BETWEEN_ITERATION = 3
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
DATA_FOR_REQUEST = {
    'url': ENDPOINT,
    'header': HEADERS,
    'params': {'from_date': 0}
}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка токенов."""
    tokens = (
        ('PRACTICUM_TOKEN', PRACTICUM_TOKEN),
        ('TELEGRAM_TOKEN', TELEGRAM_TOKEN),
        ('TELEGRAM_CHAT_ID', TELEGRAM_CHAT_ID)
    )

    invalid_tokens = [token for token, value in tokens if value is None]

    if invalid_tokens:
        message = f'Ошибка проверки токена: {", ".join(invalid_tokens)}.'
        logger.critical(message)
        raise InvalidTokenError(message)


def send_message(bot: TeleBot, message: str):
    """Отправка сообщения о статусе проверки ДЗ в ТГ."""
    try:
        logger.debug(f'Отправка сообщения в чат: {TELEGRAM_CHAT_ID}...')
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.debug(
            f'Сообщение в чат: {TELEGRAM_CHAT_ID} успешно отправлено!'
        )
        return True
    except apihelper.ApiException as error:
        logger.error(f'Возникла ошибка при отправки сообщения... {error}')
        return False


def get_api_answer(timestamp):
    """Отправка API запроса."""
    try:
        DATA_FOR_REQUEST['params']['from_date'] = timestamp

        logger.debug(
            'Отправка запроса на адрес: {url}. '
            'Заголовок: {header}. '
            'Параметры: {params} '.format(**DATA_FOR_REQUEST)
        )
        response = requests.get(
            url=DATA_FOR_REQUEST['url'],
            headers=DATA_FOR_REQUEST['header'],
            params=DATA_FOR_REQUEST['params']
        )

        logger.debug('Ответ от: {url} получен.'.format(**DATA_FOR_REQUEST))

    except requests.RequestException as error:
        raise APIRequestError(f'Ошибка {error} при обращении к {ENDPOINT}.')
    if response.status_code != HTTPStatus.OK:
        raise InvalidStatusCode(
            'API-ответ был получен, но что-то пошло не так...'
            f'Код ответа API: {response.status_code}.'
        )

    return response.json()


def check_response(response: dict):
    """Проверка структуры API-ответа."""
    if not isinstance(response, dict):
        raise TypeError('Ошибка в структуре API-ответа.')
    if 'homeworks' not in response:
        raise KeyError('Отсутствует ключ homeworks в API-ответе.')
    result = response['homeworks']
    if not isinstance(result, list):
        raise TypeError('Ошибка в структуре homeworks в API-ответа.')

    return result


def parse_status(homework: dict):
    """Генерация сообщения для отправки."""
    if 'homework_name' not in homework:
        raise InvalidHomeWorkName('Ошибка в названии ДЗ.')

    if 'status' not in homework or homework['status'] not in HOMEWORK_VERDICTS:
        raise InvalidHomeWorkStatus('Ошибка в статусе ДЗ.')

    homework_name = homework['homework_name']
    verdict = HOMEWORK_VERDICTS[homework['status']]

    return (f'Изменился статус проверки работы "{homework_name}".'
            f' Статус: {verdict}')


def main():
    """Основная логика работы бота."""
    check_tokens()

    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_message = None

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if not homeworks:
                logger.debug('Список с домашними заданиями пуст...')
            else:
                homework_in_progress = homeworks[0]
                text = parse_status(homework_in_progress)
                is_msg_sent = send_message(bot, text)
                if is_msg_sent:
                    logger.debug(
                        'Статус для домашнего задания '
                        f'{homework_in_progress["homework_name"]} изменен. '
                        f'Статус: {homework_in_progress["status"]}.'
                    )
                    new_timestamp = response.get('current_date')
                    if new_timestamp:
                        timestamp = new_timestamp
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if message != last_message:
                send_message(bot, message)
                last_message = message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
