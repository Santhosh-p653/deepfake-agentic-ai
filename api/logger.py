import logging
import os
os.markedirs("logs",exist_ok=True)
logging.basicConfig(level=logging.INFO,format="%(asctime)s[%(levelname)s]%(message)s",handlers=[logging.FileHandler("logs/app.log"),logging.StreamHandler()])
logger = logging.getLogger(__name__)
