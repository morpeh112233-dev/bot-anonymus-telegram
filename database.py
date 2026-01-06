import psycopg2
from psycopg2.extras import RealDictCursor
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, connection_string):
        self.conn_string = connection_string
        self.init_db()
    
    def get_connection(self):
        return psycopg2.connect(self.conn_string, sslmode='require')
    
    def init_db(self):
        """Создание таблиц"""
        commands = (
            """
            CREATE TABLE IF NOT EXISTS questions (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                message_id INTEGER,
                admin_message_id INTEGER,
                question_text TEXT NOT NULL,
                answer_text TEXT,
                asked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                answered_at TIMESTAMP,
                is_answered BOOLEAN DEFAULT FALSE
            )
            """,
        )
        
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            for command in commands:
                cur.execute(command)
            cur.close()
            conn.commit()
            logger.info("База данных инициализирована")
        except Exception as e:
            logger.error(f"Ошибка инициализации БД: {e}")
        finally:
            if conn:
                conn.close()
    
    def save_question(self, user_id, message_id, question_text):
        """Сохранить вопрос от пользователя"""
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO questions (user_id, message_id, question_text) VALUES (%s, %s, %s) RETURNING id",
                (user_id, message_id, question_text)
            )
            question_id = cur.fetchone()[0]
            conn.commit()
            cur.close()
            return question_id
        except Exception as e:
            logger.error(f"Ошибка сохранения вопроса: {e}")
            return None
        finally:
            if conn:
                conn.close()
    
    def get_user_by_admin_message(self, admin_message_id):
        """Найти пользователя по ID сообщения админа"""
        try:
            conn = self.get_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(
                "SELECT * FROM questions WHERE admin_message_id = %s",
                (admin_message_id,)
            )
            result = cur.fetchone()
            cur.close()
            return result
        except Exception as e:
            logger.error(f"Ошибка поиска пользователя: {e}")
            return None
        finally:
            if conn:
                conn.close()
    
    def save_admin_message_id(self, question_id, admin_message_id):
        """Сохранить ID сообщения админа"""
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            cur.execute(
                "UPDATE questions SET admin_message_id = %s WHERE id = %s",
                (admin_message_id, question_id)
            )
            conn.commit()
            cur.close()
        except Exception as e:
            logger.error(f"Ошибка сохранения ID админа: {e}")
        finally:
            if conn:
                conn.close()
    
    def mark_as_answered(self, question_id, answer_text):
        """Отметить вопрос как отвеченный"""
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            cur.execute(
                "UPDATE questions SET answer_text = %s, is_answered = TRUE, answered_at = CURRENT_TIMESTAMP WHERE id = %s",
                (answer_text, question_id)
            )
            conn.commit()
            cur.close()
        except Exception as e:
            logger.error(f"Ошибка отметки ответа: {e}")
        finally:
            if conn:
                conn.close()
