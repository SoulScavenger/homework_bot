"""Кастомные исключения."""


class InvalidTokenError(Exception):
    """Кастомное исключения для Токенов."""


class SendMessageError(Exception):
    """Кастомное исключения для отправки сообщений."""


class InvalidHomeWorkStatus(Exception):
    """Кастомное исключения для статуса ДЗ."""


class InvalidHomeWorkName(Exception):
    """Кастомное исключения для имени ДЗ."""
