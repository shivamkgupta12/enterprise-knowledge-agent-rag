import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

from app.core.schemas import FeedbackRequest

DB_PATH = Path(__file__).resolve().parents[1] / "db" / "feedback.db"


def init_feedback_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            rating INTEGER NOT NULL,
            comment TEXT,
            citations TEXT,
            created_at TEXT NOT NULL
        )
        """
    )

    connection.commit()
    connection.close()


def save_feedback(payload: FeedbackRequest) -> int:
    init_feedback_db()

    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO feedback (
            question,
            answer,
            rating,
            comment,
            citations,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            payload.question,
            payload.answer,
            payload.rating,
            payload.comment,
            json.dumps(payload.citations),
            datetime.now(timezone.utc).isoformat(),
        ),
    )

    connection.commit()
    feedback_id = cursor.lastrowid
    connection.close()

    return int(feedback_id)


def get_feedback_summary() -> dict:
    init_feedback_db()

    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    cursor.execute("SELECT COUNT(*), AVG(rating) FROM feedback")
    count, avg_rating = cursor.fetchone()

    cursor.execute(
        """
        SELECT rating, COUNT(*)
        FROM feedback
        GROUP BY rating
        ORDER BY rating
        """
    )
    distribution = {str(row[0]): row[1] for row in cursor.fetchall()}

    connection.close()

    return {
        "total_feedback": count or 0,
        "average_rating": round(avg_rating or 0, 2),
        "rating_distribution": distribution,
    }
