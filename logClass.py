import logging

class RTKLogger:
    def __init__(self, log_file='MAINRTK.log'):
        # Настройка логирования
        try:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler(log_file),
                    logging.StreamHandler()
                ]
            )
            logging.info("Логирование началось.")
        except Exception as e:
            print(f"Ошибка при настройке логирования: {e}")
    
    def log_info(self, mes):
        logging.info(f"{mes}")
    
    def log_error(self, mes):
        logging.error(f"{mes}")
