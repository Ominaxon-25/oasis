import asyncio
import sys
from pathlib import Path
from datetime import datetime, date, time, timedelta
import pytz

import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add backend directory to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.database import AsyncSessionLocal, init_db, engine
from app.models import Restaurant, TableZone, Table, Reservation, ReservationStatus


async def seed_data():
    print("[INIT] Initializing database schema...")
    await init_db()

    async with AsyncSessionLocal() as session:
        # Check if already seeded
        from sqlalchemy import select
        existing = await session.execute(select(Restaurant))
        if existing.scalars().first():
            print("[INFO] Database already contains restaurant data. Skipping duplicate seed.")
            return

        print("[START] Seeding realistic B2B data for Tashkent restaurants...")

        tashkent_tz = pytz.timezone("Asia/Tashkent")
        today = datetime.now(tashkent_tz).date()

        # =====================================================================
        # Restaurant 1: Veranda Lounge (Tashkent Center)
        # =====================================================================
        veranda = Restaurant(
            name="Veranda Lounge",
            timezone="Asia/Tashkent",
            operating_hours={"open": "12:00", "close": "23:00"},
            avg_turn_time_mins=90
        )
        session.add(veranda)
        await session.flush()

        # Zones & Tables for Veranda Lounge
        z_main = TableZone(restaurant_id=veranda.id, name="Main Hall")
        z_terrace = TableZone(restaurant_id=veranda.id, name="Summer Terrace")
        z_vip = TableZone(restaurant_id=veranda.id, name="VIP Lounge")
        session.add_all([z_main, z_terrace, z_vip])
        await session.flush()

        tables_veranda = [
            # Main Hall
            Table(zone_id=z_main.id, table_number="T-1", min_capacity=1, max_capacity=2, is_active=True),
            Table(zone_id=z_main.id, table_number="T-2", min_capacity=2, max_capacity=4, is_active=True),
            Table(zone_id=z_main.id, table_number="T-3", min_capacity=2, max_capacity=4, is_active=True),
            Table(zone_id=z_main.id, table_number="T-4", min_capacity=4, max_capacity=6, is_active=True),
            Table(zone_id=z_main.id, table_number="T-5", min_capacity=6, max_capacity=8, is_active=True),
            # Summer Terrace
            Table(zone_id=z_terrace.id, table_number="TR-1", min_capacity=1, max_capacity=2, is_active=True),
            Table(zone_id=z_terrace.id, table_number="TR-2", min_capacity=2, max_capacity=4, is_active=True),
            Table(zone_id=z_terrace.id, table_number="TR-3", min_capacity=4, max_capacity=6, is_active=True),
            # VIP Lounge
            Table(zone_id=z_vip.id, table_number="VIP-1", min_capacity=4, max_capacity=8, is_active=True),
            Table(zone_id=z_vip.id, table_number="VIP-2", min_capacity=6, max_capacity=12, is_active=True),
        ]
        session.add_all(tables_veranda)
        await session.flush()

        # =====================================================================
        # Restaurant 2: Sora Sushi & Steak (Yakkasaray)
        # =====================================================================
        sora = Restaurant(
            name="Sora Sushi & Steak",
            timezone="Asia/Tashkent",
            operating_hours={"open": "13:00", "close": "23:00"},
            avg_turn_time_mins=90
        )
        session.add(sora)
        await session.flush()

        # Zones & Tables for Sora Sushi & Steak
        z_sora_dining = TableZone(restaurant_id=sora.id, name="Dining Room")
        z_sora_bar = TableZone(restaurant_id=sora.id, name="Teppanyaki Bar")
        z_sora_tatami = TableZone(restaurant_id=sora.id, name="Private Tatami VIP")
        session.add_all([z_sora_dining, z_sora_bar, z_sora_tatami])
        await session.flush()

        tables_sora = [
            # Dining Room
            Table(zone_id=z_sora_dining.id, table_number="S-1", min_capacity=1, max_capacity=2, is_active=True),
            Table(zone_id=z_sora_dining.id, table_number="S-2", min_capacity=2, max_capacity=4, is_active=True),
            Table(zone_id=z_sora_dining.id, table_number="S-3", min_capacity=4, max_capacity=6, is_active=True),
            # Teppanyaki Bar
            Table(zone_id=z_sora_bar.id, table_number="TP-1", min_capacity=2, max_capacity=4, is_active=True),
            Table(zone_id=z_sora_bar.id, table_number="TP-2", min_capacity=4, max_capacity=8, is_active=True),
            # Private Tatami VIP
            Table(zone_id=z_sora_tatami.id, table_number="TAT-1", min_capacity=4, max_capacity=8, is_active=True),
            Table(zone_id=z_sora_tatami.id, table_number="TAT-2", min_capacity=6, max_capacity=10, is_active=True),
        ]
        session.add_all(tables_sora)
        await session.flush()

        # =====================================================================
        # Seed Baseline Reservations for Tomorrow to show realistic occupancy
        # =====================================================================
        tomorrow = today + timedelta(days=1)
        res_time_1 = tashkent_tz.localize(datetime.combine(tomorrow, time(19, 0)))
        end_time_1 = res_time_1 + timedelta(minutes=90)

        demo_res_1 = Reservation(
            restaurant_id=veranda.id,
            table_id=tables_veranda[1].id,  # T-2
            customer_name="Alisher Usmanov",
            customer_phone="+998901234567",
            party_size=4,
            reservation_time=res_time_1,
            end_time=end_time_1,
            status=ReservationStatus.CONFIRMED
        )

        res_time_2 = tashkent_tz.localize(datetime.combine(tomorrow, time(20, 0)))
        end_time_2 = res_time_2 + timedelta(minutes=90)

        demo_res_2 = Reservation(
            restaurant_id=sora.id,
            table_id=tables_sora[1].id,  # S-2
            customer_name="Dildora Karimova",
            customer_phone="+998909876543",
            party_size=3,
            reservation_time=res_time_2,
            end_time=end_time_2,
            status=ReservationStatus.CONFIRMED
        )

        session.add_all([demo_res_1, demo_res_2])
        await session.commit()

        print("[SUCCESS] Successfully seeded:")
        print(f"   - {veranda.name} (ID: {veranda.id}) with {len(tables_veranda)} tables across 3 zones")
        print(f"   - {sora.name} (ID: {sora.id}) with {len(tables_sora)} tables across 3 zones")
        print("   - Sample active reservations for tomorrow's dinner service")


if __name__ == "__main__":
    asyncio.run(seed_data())
