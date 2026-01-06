import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Токен бота (получите у @BotFather)
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    
    # ID администраторов (через запятую)
    ADMIN_IDS = [int(id.strip()) for id in os.getenv('ADMIN_IDS', '').split(',') if id.strip()]
    
    # Настройки базы данных
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    # ID канала (если нужно, например: -1001234567890)
    CHANNEL_ID = os.getenv('CHANNEL_ID', '')
