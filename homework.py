import os
import logging
import requests
import sys
import time
from http import HTTPStatus

from dotenv import load_dotenv
from telebot import TeleBot

from extensions import (
    InvalidTokenError,
    InvalidHomeWorkName,
    InvalidHomeWorkStatus,
    SendMessageError,
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


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка токенов."""
    try:
        if not all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
            raise InvalidTokenError

    except InvalidTokenError:
        logger.critical('Ошибка проверки токена.')
        sys.exit()


def send_message(bot: TeleBot, message: str):
    """Отправка сообщения о статусе проверки ДЗ в ТГ."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.debug('Сообщение успешно отправлено!')
    except SendMessageError:
        logger.error('Возникла ошибка при отправки сообщения...')


def get_api_answer(timestamp):
    """Отправка API запроса."""
    try:
        response = requests.get(
            ENDPOINT, headers=HEADERS, params={'from_date': timestamp}
        )
        logger.debug(f'Отправка запроса на адрес: {ENDPOINT}')
    except requests.RequestException:
        logger.error(f'Ошибка при работе с Эндпоинтом {ENDPOINT}. '
                     f'Код ошибки: {response.status_code}')
    if response.status_code != HTTPStatus.OK:
        raise requests.RequestException

    return response.json()


def check_response(response: dict):
    """Проверка структуры API-ответа."""
    if not isinstance(response, dict):
        logger.error('Ошибка в структуре API-ответа.')
        raise TypeError
    elif 'homeworks' not in response:
        logger.error('Отсутствует ключ homework в API-ответе.')
        raise KeyError
    elif not isinstance(response['homeworks'], list):
        logger.error('Ошибка в структуре homework в API-ответа.')
        raise TypeError
    else:
        return True


def parse_status(homework: dict):
    """Генерация сообщения для отправки."""
    if 'homework_name' not in homework:
        logger.error('Ошибка в названии ДЗ.')
        raise InvalidHomeWorkName('Ошибка в названии ДЗ.')
    if 'status' not in homework or homework['status'] not in HOMEWORK_VERDICTS:
        logger.error('Ошибка в статусе ДЗ.')
        raise InvalidHomeWorkStatus('Ошибка в статусе ДЗ.')

    homework_name = homework['homework_name']
    verdict = HOMEWORK_VERDICTS[homework['status']]

    return (f'Изменился статус проверки работы "{homework_name}".'
            f'Статус: {verdict}')


def main():
    """Основная логика работы бота."""
    check_tokens()

    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    homeworks_stats = dict()

    while True:
        try:
            response = get_api_answer(timestamp=timestamp)
            if check_response(response):
                homeworks = response['homeworks']
                if len(homeworks) == 0:
                    logger.debug('Список с домашними заданиями пуст...')
                else:
                    for homework in homeworks[::-1]:
                        homework_name = homework['homework_name']
                        homework_stat = homework['status']
                        if homework_name in homeworks_stats:
                            if (
                                homework_stat == homeworks_stats[homework_name]
                            ):
                                logger.debug('Статус для домашнего задания '
                                             f'{homework_name} не изменен...')

                                continue
                            else:
                                text = parse_status(homework)
                                send_message(bot, text)
                                logger.debug('Статус для домашнего задания '
                                             f'{homework_name} изменен. '
                                             f'Статус: {homework_stat}.')
                                homeworks_stats[homework_name] = homework_stat
                        else:
                            text = parse_status(homework)
                            send_message(bot, text)
                            logger.debug('Статус для домашнего задания '
                                         f'{homework_name} изменен. '
                                         f'Статус: {homework_stat}.')
                            homeworks_stats[homework_name] = homework_stat
                        time.sleep(PAUSE_BETWEEN_ITERATION)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(f'{message}')
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
