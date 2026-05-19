import logging

from .algo import AlgoParser
from .andre import AndreParser
from .base import BaseSignalParser
from .elite import EliteParser
from .hasseb import HaseebParser
from .voyager import VoyagerParser

logger = logging.getLogger(__name__)


class ParserRegistry:
    def __init__(self):
        self._parsers: dict[str, BaseSignalParser] = {}
        self.register("algo", AlgoParser())
        self.register("elite", EliteParser())
        self.register("haseeb", HaseebParser())
        self.register("andre", AndreParser())
        self.register("voyager", VoyagerParser())

    def register(self, name: str, parser: BaseSignalParser) -> None:
        self._parsers[name.lower()] = parser
        logger.debug(f"Зарегистрирован парсер для источника: {name}")

    def get_parser(self, name: str) -> BaseSignalParser | None:
        parser = self._parsers.get(name.lower())
        if not parser:
            logger.warning(f"Парсер для источника '{name}' не найден в реестре.")
        return parser

    def parse_message(self, source_name: str, source_id: int, message_id: int, text: str):
        parser = self.get_parser(source_name)
        if not parser:
            return None
        return parser.parse(source_id=source_id, message_id=message_id, text=text)
