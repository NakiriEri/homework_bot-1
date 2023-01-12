import os
from dotenv import load_dotenv
import requests
import logging
import telegram
import time
from http import HTTPStatus

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


class EmptyDict(Exception):
    """Пустой словь или его нет."""

    pass


class NotNewHomework(Exception):
    """Нет новой домашней работы."""

    pass


class KeyNotInDict(Exception):
    """Нет новой домашней работы."""

    pass


class ListHomeworkEmpty(Exception):
    """Нет новой домашней работы."""

    pass


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter(
    '%(asctime)s, %(levelname)s, %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)


def check_tokens():
    """Проверка доступности токенов."""
    return all(
        [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    )


def send_message(bot, message):
    """Отправка сообщения в телеграмм"""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.info('Успешная отправка сообщения.')
    except Exception as error:
        raise SystemError(f'Не отправляются сообщения, {error}')


def get_api_answer(timestamp):
    """Получение запроса."""
    timestamp = timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except requests.RequestException:
        raise EmptyDict(
            'недоступность эндпоинта'
            'https://practicum.yandex.ru/api/user_api/homework_statuses/')
    if response.status_code != HTTPStatus.OK:
        raise EmptyDict('API возвращает код'
                        'отличный от 200')
    return response.json()


def check_response(response):
    """Проверка правильно данных в запросе."""
    if not response:
        logger.error('Пустой Словарь')
        raise EmptyDict("Пустой словарь в ответе API")
    if not isinstance(response, dict):
        logger.error('Ответ на запрос не словарь')
        print(type(response))
        raise TypeError("Ответ на запрос не словарь")
    homework = response.get('homeworks')
    if type(homework) is not list:
        logger.error("Нет list в API ответе")
        raise ListHomeworkEmpty("Нет list в API ответе")
    return response.get('homeworks')


def parse_status(homework):
    """Получение статуса работы."""
    homework_statuses = homework.get("status")
    homework_name = homework.get("homework_name")
    if not homework_statuses:
        logger.error('Неверный статус домешней работы')
        raise KeyError("Неверный статус домешней работы")
    if not homework_name:
        logger.error("Нет имени домашней работы")
        raise KeyError("Нет имени домашней работы")
    verdict = HOMEWORK_VERDICTS[homework_statuses]
    if homework_statuses not in HOMEWORK_VERDICTS:
        logger.error("Такого статуса нет в системе")
        raise KeyError(
            'Статуса нет вHOMEWORK_VERDICTSS'
                     )

    logger.info(
        f'Изменился статус проверки работы "{homework_name}". {verdict}'
    )
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    check_tokens()
    last_status = None
    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            if homework:
                message = parse_status(homework[0])
                if message != last_status:
                    send_message(bot, message)
                    last_status = message
                else:
                    logging.info('Статус домашних работ не изменился')
            else:
                logging.info('API пуст, домашних работ не найдено!')
            timestamp = response.get('current_date')

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.warning("Произошла ошибка отправки сообщения")
            if last_status != message:
                send_message(bot, message)
                last_status = message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
