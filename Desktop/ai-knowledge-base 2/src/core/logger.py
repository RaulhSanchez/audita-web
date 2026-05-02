import logging
import json
import os
from datetime import datetime

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "funcName": record.funcName
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record)

def setup_logger():
    os.makedirs("logs", exist_ok=True)
    logger = logging.getLogger("cortexa")
    logger.setLevel(logging.INFO)
    
    # Consola
    c_handler = logging.StreamHandler()
    c_handler.setFormatter(JsonFormatter())
    logger.addHandler(c_handler)
    
    # Archivo
    f_handler = logging.FileHandler("logs/app.log")
    f_handler.setFormatter(JsonFormatter())
    logger.addHandler(f_handler)
    
    return logger

logger = setup_logger()
