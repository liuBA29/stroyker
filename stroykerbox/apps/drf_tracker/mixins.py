from typing import Optional, Any
import ast
import ipaddress
import logging
import traceback

from django.db import connection
from django.utils.timezone import now
from django.contrib.auth import get_user_model
from django.conf import settings
from constance import config

from .models import APIRequestLog

logger = logging.getLogger(__name__)

User = get_user_model()


class LoggingMixin:
    CLEANED_SUBSTITUTE = '-----------------------'

    sensitive_fields = {}

    def initial(self, request, *args, **kwargs) -> None:
        self.log = {'requested_at': now()}
        self.log['data'] = (
            self._clean_data(request.body)
            if config.API_TRACKER_DECODE_REQUEST_BODY
            else ''
        )
        self.logging_methods = self._get_logging_methods()

        super().initial(request, *args, **kwargs)  # type: ignore

        try:
            # Доступ к request.data *в первый раз* анализирует тело запроса, что может вызвать
            # Исключения ParseError и UnsupportedMediaType. Важно не проглотить это,
            # поскольку (в зависимости от деталей реализации) они могут быть подняты только один раз, и
            # Логика DRF требует, чтобы они были вызваны представлением для корректной работы обработки ошибок.
            data = self.request.data.dict()  # type: ignore
        except AttributeError:
            data = self.request.data  # type: ignore
        self.log['data'] = self._clean_data(data)

    def _get_logging_methods(self) -> list:
        return config.API_TRACKER_ALLOWED_METHODS

    def handle_exception(self, exc):
        response = super().handle_exception(exc)  # type: ignore
        self.log['errors'] = traceback.format_exc()

        return response

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(  # type: ignore
            request, response, *args, **kwargs
        )

        if self.should_log(request, response):
            if (
                connection.settings_dict.get('ATOMIC_REQUESTS')
                and getattr(response, 'exception', None)
                and connection.in_atomic_block
            ):
                # ответ с исключением (HTTP-статус, например: 401, 404 и т. д.)
                # поточечное отключение атомарного блока для журнала
                # дескрипторов (TransactionManagementError)
                connection.set_rollback(True)
                connection.set_rollback(False)
            if response.streaming:
                rendered_content = None
            elif hasattr(response, 'rendered_content'):
                rendered_content = response.rendered_content
            else:
                rendered_content = response.getvalue()

            user = self._get_user(request)

            self.log.update(
                {
                    'remote_addr': self._get_ip_address(request),
                    'view': self._get_view_name(request),
                    'view_method': self._get_view_method(request),
                    'path': self._get_path(request),
                    'host': request.get_host(),
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                    'method': request.method,
                    'query_params': self._clean_data(request.query_params.dict()),
                    'user': user,
                    'response_ms': self._get_response_ms(),
                    'response': self._clean_data(rendered_content),
                    'status_code': response.status_code,
                }
            )
            try:
                self.handle_log()
            except Exception:
                logger.exception('Logging API call raise exception!')
        return response

    def handle_log(self) -> None:
        """
        Момент обработки лога.
        По-дефолту - создаем объект модели APIRequestLog с данными запроса/ответа.
        """
        APIRequestLog(**self.log).save()

    def _get_path(self, request, char_limit: int = 200) -> str:
        return request.path[:char_limit]

    def _get_ip_address(self, request) -> str:
        ipaddr = request.META.get('HTTP_X_FORWARDED_FOR', None)
        if ipaddr:
            ipaddr = ipaddr.split(',')[0]
        else:
            ipaddr = request.META.get('REMOTE_ADDR', '').split(',')[0]

        possibles = (ipaddr.lstrip('[').split(']')[0], ipaddr.split(':')[0])

        for addr in possibles:
            try:
                return str(ipaddress.ip_address(addr))
            except ValueError:
                pass

        return ipaddr

    def _get_view_name(self, request) -> Optional[str]:
        method = request.method.lower()
        try:
            attributes = getattr(self, method)
            return f'{type(attributes.__self__).__module__}.{type(attributes.__self__).__name__}'

        except AttributeError:
            return None

    def _get_view_method(self, request) -> Optional[str]:
        if hasattr(self, 'action'):
            return self.action or None
        return request.method.lower()

    def _get_user(self, request) -> Optional[User]:  # type: ignore
        user = request.user
        if user.is_anonymous:
            return None
        return user

    def _get_response_ms(self) -> int:
        """
        Получение продолжительности цикла ответа на запрос в миллисекундах.
        В случае отрицательного значения возвращается 0.
        """
        response_timedelta = now() - self.log['requested_at']
        response_ms = int(response_timedelta.total_seconds() * 1000)
        return max(response_ms, 0)

    def should_log(self, request, response) -> bool:
        """
        Метод, который должен возвращает True, если запрос должен быть залогиован.
        """
        if not config.API_TRACKER_ON or (
            settings.DEBUG and not config.API_TRACKER_USE_IN_DEBUG
        ):
            return False
        return (
            self.logging_methods == '__all__' or request.method in self.logging_methods
        )

    def _clean_data(self, data: Any) -> Any:
        """
        Предварительная очистка словаря данных от потенциально конфиденциальной информации
        перед отправкой данных в БД.
        Функция, основанная на функции ядра django "_clean_credentials".

        Так же поля, определенные django, по умолчанию очищаются с помощью этого метода.

        Можно задать свои собственные конфиденциальные поля, переопределив поле sensitive_fields класса.
        например: sensitive_fields = {'поле1', 'поле2'}
        """
        if isinstance(data, bytes):
            data = data.decode(errors='replace')

        if isinstance(data, list):
            return [self._clean_data(d) for d in data]

        if isinstance(data, dict):
            SENSITIVE_FIELDS = {
                'api',
                'token',
                'key',
                'secret',
                'password',
                'signature',
            }

            data = dict(data)

            if self.sensitive_fields:
                SENSITIVE_FIELDS = SENSITIVE_FIELDS | {
                    field.lower() for field in self.sensitive_fields
                }

            for key, value in data.items():
                try:
                    value = ast.literal_eval(value)
                except (ValueError, SyntaxError):
                    pass
                if isinstance(value, (list, dict)):
                    data[key] = self._clean_data(value)
                if key.lower() in SENSITIVE_FIELDS:
                    data[key] = self.CLEANED_SUBSTITUTE
        return data
