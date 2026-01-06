import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, connection_string: str):
        self.conn_string = connection_string
        self.init_db()
    
    def get_connection(self):
        """Получить соединение с базой данных"""
        return psycopg2.connect(self.conn_string, sslmode='require')
    
    def init_db(self):
        """Создание таблиц в базе данных"""
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
            conn.commit()
            cur.close()
            conn.close()
            logger.info("✅ База данных инициализирована успешно")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации БД: {e}")
    
    def save_question(self, user_id: int, message_id: int, question_text: str) -> Optional[int]:
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
            conn.close()
            logger.info(f"✅ Вопрос сохранен с ID: {question_id}")
            return question_id
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения вопроса: {e}")
            return None
    
    def get_user_by_admin_message(self, admin_message_id: int) -> Optional[Dict[str, Any]]:
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
            conn.close()
            return dict(result) if result else None
        except Exception as e:
            logger.error(f"❌ Ошибка поиска пользователя: {e}")
            return None
    
    def save_admin_message_id(self, question_id: int, admin_message_id: int):
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
            conn.close()
            logger.info(f"✅ Сохранен admin_message_id {admin_message_id} для вопроса {question_id}")
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения ID админа: {e}")
    
    def mark_as_answered(self, question_id: int, answer_text: str):
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
            conn.close()
            logger.info(f"✅ Вопрос {question_id} отмечен как отвеченный")
        except Exception as e:
            logger.error(f"❌ Ошибка отметки ответа: {e}")
    
    def get_stats(self) -> Dict[str, int]:
        """Получить статистику вопросов"""
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            
            cur.execute("SELECT COUNT(*) FROM questions")
            total = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM questions WHERE is_answered = TRUE")
            answered = cur.fetchone()[0]
            
            cur.close()
            conn.close()
            
            return {
                "total": total,
                "answered": answered,
                "pending": total - answered
            }
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики: {e}")
            return {"total": 0, "answered": 0, "pending": 0}
    
    def get_pending_questions(self):
        """Получить все неотвеченные вопросы"""
        try:
            conn = self.get_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(
                "SELECT * FROM questions WHERE is_answered = FALSE ORDER BY asked_at DESC"
            )
            results = cur.fetchall()
            cur.close()
            conn.close()
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"❌ Ошибка получения неотвеченных вопросов: {e}")
            return []
