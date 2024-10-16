"""Кастомные исключения."""


class InvalidTokenError(Exception):
    """Кастомное исключения для Токенов."""


class InvalidHomeWorkStatus(Exception):
    """Кастомное исключения для статуса ДЗ."""


class InvalidHomeWorkName(Exception):
    """Кастомное исключения для имени ДЗ."""


class InvalidStatusCode(Exception):
    """Кастомное исключения для кода получения API запроса."""


class APIRequestError(Exception):
    """Кастомное исключения для API запроса."""
