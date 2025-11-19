"""COLEHUB integration service for reading Cole's points and tasks."""

import logging
from typing import Dict, List, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta

from app.config import settings

logger = logging.getLogger(__name__)

# COLEHUB database connection (separate from main app database)
colehub_engine = None
ColehubSession = None


def init_colehub_connection():
    """Initialize COLEHUB database connection."""
    global colehub_engine, ColehubSession

    if not settings.colehub_database_url:
        logger.warning("COLEHUB database URL not configured")
        return

    try:
        colehub_engine = create_engine(settings.colehub_database_url)
        ColehubSession = sessionmaker(bind=colehub_engine)
        logger.info("COLEHUB database connection initialized")
    except Exception as e:
        logger.error(f"Failed to connect to COLEHUB database: {e}")


def get_colehub_session():
    """Get COLEHUB database session."""
    if ColehubSession is None:
        raise RuntimeError("COLEHUB database not initialized")
    return ColehubSession()


class ColehubService:
    """Service for querying COLEHUB data."""

    def __init__(self):
        """Initialize COLEHUB service."""
        pass

    async def get_cole_points(self) -> Optional[Dict]:
        """
        Get Cole's current points and statistics.

        Returns:
            Dictionary with points data or None if not available
        """
        if ColehubSession is None:
            logger.warning("COLEHUB not configured, returning mock data")
            return self._get_mock_points()

        try:
            session = get_colehub_session()

            # Example query - adjust based on actual COLEHUB schema
            # This assumes there's a 'points' table with user_id and points columns
            query = text("""
                SELECT
                    user_id,
                    total_points,
                    points_today,
                    points_this_week,
                    current_streak,
                    last_updated
                FROM points
                WHERE user_id = :user_id
                LIMIT 1
            """)

            result = session.execute(query, {"user_id": "cole"}).fetchone()
            session.close()

            if result:
                return {
                    "user_id": result[0],
                    "total_points": result[1],
                    "points_today": result[2],
                    "points_this_week": result[3],
                    "current_streak": result[4],
                    "last_updated": result[5].isoformat() if result[5] else None,
                }
            else:
                logger.warning("No points data found for Cole")
                return self._get_mock_points()

        except Exception as e:
            logger.error(f"Error fetching Cole's points: {e}")
            return self._get_mock_points()

    async def get_cole_tasks(self, limit: int = 10) -> List[Dict]:
        """
        Get Cole's pending tasks.

        Args:
            limit: Maximum number of tasks to return

        Returns:
            List of task dictionaries
        """
        if ColehubSession is None:
            logger.warning("COLEHUB not configured, returning mock data")
            return self._get_mock_tasks()

        try:
            session = get_colehub_session()

            # Example query - adjust based on actual COLEHUB schema
            query = text("""
                SELECT
                    task_id,
                    title,
                    description,
                    points_reward,
                    due_date,
                    status,
                    created_at
                FROM tasks
                WHERE user_id = :user_id
                  AND status = 'pending'
                ORDER BY due_date ASC
                LIMIT :limit
            """)

            results = session.execute(
                query,
                {"user_id": "cole", "limit": limit}
            ).fetchall()
            session.close()

            tasks = []
            for row in results:
                tasks.append({
                    "task_id": row[0],
                    "title": row[1],
                    "description": row[2],
                    "points_reward": row[3],
                    "due_date": row[4].isoformat() if row[4] else None,
                    "status": row[5],
                    "created_at": row[6].isoformat() if row[6] else None,
                })

            return tasks if tasks else self._get_mock_tasks()

        except Exception as e:
            logger.error(f"Error fetching Cole's tasks: {e}")
            return self._get_mock_tasks()

    async def get_recent_achievements(self, days: int = 7) -> List[Dict]:
        """
        Get Cole's recent achievements.

        Args:
            days: Number of days to look back

        Returns:
            List of achievement dictionaries
        """
        if ColehubSession is None:
            logger.warning("COLEHUB not configured, returning mock data")
            return self._get_mock_achievements()

        try:
            session = get_colehub_session()

            since = datetime.now() - timedelta(days=days)

            query = text("""
                SELECT
                    achievement_id,
                    title,
                    description,
                    points_earned,
                    earned_at
                FROM achievements
                WHERE user_id = :user_id
                  AND earned_at >= :since
                ORDER BY earned_at DESC
            """)

            results = session.execute(
                query,
                {"user_id": "cole", "since": since}
            ).fetchall()
            session.close()

            achievements = []
            for row in results:
                achievements.append({
                    "achievement_id": row[0],
                    "title": row[1],
                    "description": row[2],
                    "points_earned": row[3],
                    "earned_at": row[4].isoformat() if row[4] else None,
                })

            return achievements if achievements else self._get_mock_achievements()

        except Exception as e:
            logger.error(f"Error fetching achievements: {e}")
            return self._get_mock_achievements()

    def _get_mock_points(self) -> Dict:
        """Return mock points data when COLEHUB is unavailable."""
        return {
            "user_id": "cole",
            "total_points": 1250,
            "points_today": 50,
            "points_this_week": 275,
            "current_streak": 5,
            "last_updated": datetime.now().isoformat(),
            "mock": True
        }

    def _get_mock_tasks(self) -> List[Dict]:
        """Return mock tasks data when COLEHUB is unavailable."""
        return [
            {
                "task_id": 1,
                "title": "Complete math homework",
                "description": "Finish chapter 5 problems",
                "points_reward": 25,
                "due_date": (datetime.now() + timedelta(days=1)).isoformat(),
                "status": "pending",
                "created_at": datetime.now().isoformat(),
                "mock": True
            },
            {
                "task_id": 2,
                "title": "Practice piano",
                "description": "30 minutes of practice",
                "points_reward": 15,
                "due_date": datetime.now().isoformat(),
                "status": "pending",
                "created_at": datetime.now().isoformat(),
                "mock": True
            }
        ]

    def _get_mock_achievements(self) -> List[Dict]:
        """Return mock achievements when COLEHUB is unavailable."""
        return [
            {
                "achievement_id": 1,
                "title": "Week Warrior",
                "description": "Earned 200+ points this week",
                "points_earned": 50,
                "earned_at": (datetime.now() - timedelta(days=2)).isoformat(),
                "mock": True
            }
        ]


# Global COLEHUB service instance
colehub_service = ColehubService()


def get_colehub_service() -> ColehubService:
    """Get COLEHUB service instance."""
    return colehub_service
