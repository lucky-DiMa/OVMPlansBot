import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from cron import send_plans_table, mailing, send_notifications

if __name__ == '__main__':
    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_plans_table, 'cron', day_of_week='mon-fri', hour=12, minute=0, end_date='2025-10-13')
    scheduler.add_job(mailing, 'cron', day_of_week='mon-fri', hour=11, minute=40, end_date='2025-10-13')
    for i in range(4):
        scheduler.add_job(send_notifications, 'cron', day_of_week='mon-fri', hour=8 + i, minute=0,
                          end_date='2025-10-13')
        scheduler.add_job(send_notifications, 'cron', day_of_week='mon-fri', hour=8 + i, minute=30,
                          end_date='2025-10-13')
    scheduler.start()
    asyncio.get_event_loop().run_forever()
