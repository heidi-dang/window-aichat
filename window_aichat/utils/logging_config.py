import os
import logging

def setup_logging():
    log_dir = os.path.join(os.path.expanduser("~"), ".aichatdesktop")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "app.log")

    # Get root logger
    root_logger = logging.getLogger()
    # Avoid adding duplicate handlers
    if not root_logger.handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(log_file, encoding="utf-8"),
                logging.StreamHandler(),
            ],
        )

    # Set up module-specific loggers
    logging.getLogger("window_aichat").setLevel(logging.INFO)
