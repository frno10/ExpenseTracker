import asyncio
import logging
from datetime import datetime, date, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..services.recurring_expense_service import RecurringExpenseService

logger = logging.getLogger(__name__)


class RecurringExpenseScheduler:
    """Background scheduler for processing recurring expenses."""
    
    def __init__(self):
        self.is_running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the recurring expense scheduler."""
        if self.is_running:
            logger.warning("Recurring expense scheduler is already running")
            return
        
        self.is_running = True
        self._task = asyncio.create_task(self._scheduler_loop())
        logger.info("Recurring expense scheduler started")
    
    async def stop(self):
        """Stop the recurring expense scheduler."""
        if not self.is_running:
            return
        
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        logger.info("Recurring expense scheduler stopped")
    
    async def _scheduler_loop(self):
        """Main scheduler loop that runs every hour."""
        while self.is_running:
            try:
                await self._process_recurring_expenses()
                await self._create_notifications()
                
                # Sleep for 1 hour
                await asyncio.sleep(3600)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in recurring expense scheduler: {e}")
                # Sleep for 5 minutes before retrying
                await asyncio.sleep(300)
    
    async def _process_recurring_expenses(self):
        """Process all due recurring expenses."""
        try:
            # Get database session
            db_gen = get_db()
            db = next(db_gen)
            
            try:
                service = RecurringExpenseService(db)
                
                # Process due recurring expenses for all users
                results = await service.process_due_recurring_expenses()
                
                if results['processed'] > 0:
                    logger.info(
                        f"Processed {results['processed']} recurring expenses: "
                        f"{results['created']} created, {results['failed']} failed"
                    )
                
                if results['errors']:
                    for error in results['errors']:
                        logger.error(
                            f"Failed to process recurring expense {error['recurring_expense_id']}: "
                            f"{error['error']}"
                        )
            
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error processing recurring expenses: {e}")
    
    async def _create_notifications(self):
        """Create notifications for upcoming recurring expenses."""
        try:
            # Get database session
            db_gen = get_db()
            db = next(db_gen)
            
            try:
                service = RecurringExpenseService(db)
                
                # Create notifications for all users
                notifications_created = await service.create_upcoming_notifications()
                
                if notifications_created > 0:
                    logger.info(f"Created {notifications_created} recurring expense notifications")
            
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error creating recurring expense notifications: {e}")
    
    async def process_user_recurring_expenses(self, user_id: str):
        """Process recurring expenses for a specific user (for manual triggering)."""
        try:
            # Get database session
            db_gen = get_db()
            db = next(db_gen)
            
            try:
                service = RecurringExpenseService(db)
                
                # Process due recurring expenses for specific user
                from uuid import UUID
                results = await service.process_due_recurring_expenses(UUID(user_id))
                
                logger.info(
                    f"Processed {results['processed']} recurring expenses for user {user_id}: "
                    f"{results['created']} created, {results['failed']} failed"
                )
                
                return results
            
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error processing recurring expenses for user {user_id}: {e}")
            raise


# Global scheduler instance
recurring_expense_scheduler = RecurringExpenseScheduler()


async def start_recurring_expense_scheduler():
    """Start the global recurring expense scheduler."""
    await recurring_expense_scheduler.start()


async def stop_recurring_expense_scheduler():
    """Stop the global recurring expense scheduler."""
    await recurring_expense_scheduler.stop()


async def process_user_recurring_expenses_manually(user_id: str):
    """Manually process recurring expenses for a user."""
    return await recurring_expense_scheduler.process_user_recurring_expenses(user_id)