"""Log em JSON, para correlacionar request_id entre resposta, log e auditoria."""

import json
import logging

_CAMPOS_PADRAO = set(logging.LogRecord("", 0, "", 0, "", None, None).__dict__) | {"message"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        dados = {
            "nivel": record.levelname,
            "logger": record.name,
            "mensagem": record.getMessage(),
        }
        dados.update({k: v for k, v in record.__dict__.items() if k not in _CAMPOS_PADRAO})
        if record.exc_info:
            dados["excecao"] = self.formatException(record.exc_info)
        return json.dumps(dados, default=str, ensure_ascii=False)


def configurar_logging(debug: bool) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=logging.DEBUG if debug else logging.INFO, handlers=[handler])
