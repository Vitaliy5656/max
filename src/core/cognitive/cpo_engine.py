"""
CPO Engine (Chain of Preference Optimization).

Manages preference learning for the Ensemble Cognitive Loop.
Records which axis (Temperature vs Persona) produces better results for specific question types.
Provides signals to optimize the loop (skip weaker axis) when confidence is high.
"""
from typing import Optional, Tuple
from ..memory import memory
from ..logger import log

class CPOEngine:
    def __init__(self):
        self._initialized = False

    async def _ensure_initialized(self):
        """Lazy initialization of CPO table."""
        if self._initialized:
            return
            
        if not memory._db:
            await memory.initialize()
            
        try:
            await memory._db.execute("""
                CREATE TABLE IF NOT EXISTS ensemble_cpo_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question_type TEXT,
                    winner_axis TEXT, -- 'temp', 'prompt', 'equal'
                    margin REAL DEFAULT 0.0,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await memory._db.commit()
            self._initialized = True
        except Exception as e:
            log.error(f"CPO Engine init failed: {e}")

    async def record_preference(self, question_type: str, winner: str):
        """Record the outcome of an ensemble run."""
        if not question_type or not winner:
            return
            
        try:
            await self._ensure_initialized()
            await memory._db.execute(
                "INSERT INTO ensemble_cpo_logs (question_type, winner_axis) VALUES (?, ?)",
                (question_type, winner.lower())
            )
            await memory._db.commit()
            log.info(f"CPO recorded: type={question_type} winner={winner}")
        except Exception as e:
            log.error(f"CPO record failed: {e}")

    async def get_preference(self, question_type: str, threshold: int = 5) -> Tuple[str, float]:
        """
        Get the preferred axis for a question type.
        
        Returns:
            (axis, confidence)
            axis: 'temp', 'prompt', or 'both' (if not sure)
            confidence: 0.0 to 1.0 (hit rate)
        """
        try:
            await self._ensure_initialized()
            
            async with memory._db.execute(
                "SELECT winner_axis, COUNT(*) as cnt FROM ensemble_cpo_logs WHERE question_type = ? GROUP BY winner_axis",
                (question_type,)
            ) as cursor:
                rows = await cursor.fetchall()
            
            counts = {row["winner_axis"]: row["cnt"] for row in rows}
            temp_wins = counts.get("temp", 0)
            prompt_wins = counts.get("prompt", 0)
            total = temp_wins + prompt_wins + counts.get("equal", 0)
            
            if total < threshold:
                return "both", 0.0
            
            if temp_wins > prompt_wins:
                conf = temp_wins / total
                return "temp", conf
            elif prompt_wins > temp_wins:
                conf = prompt_wins / total
                return "prompt", conf
            else:
                return "both", 0.0
                
        except Exception as e:
            log.error(f"CPO get_preference failed: {e}")
            return "both", 0.0

# Global instance
cpo_engine = CPOEngine()
