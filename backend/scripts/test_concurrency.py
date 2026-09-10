import asyncio
import sys
from pathlib import Path
from datetime import datetime, date, time, timedelta
import pytz
import httpx

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_URL = "http://127.0.0.1:8000"


async def run_test_suite():
    print("=" * 70)
    print("OASIS B2B BACKEND: CONCURRENCY & INTEGRATION TEST SUITE")
    print("=" * 70)

    tashkent_tz = pytz.timezone("Asia/Tashkent")
    target_date = (datetime.now(tashkent_tz) + timedelta(days=2)).date()

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        # 1. Health Check
        health_resp = await client.get("/health")
        assert health_resp.status_code == 200, f"Health check failed: {health_resp.text}"
        print(f"[1] Health Check: OK ({health_resp.json()['service']})")

        # 2. Availability Engine Test
        avail_resp = await client.get(
            "/api/v1/availability",
            params={
                "restaurant_id": 1,
                "date": target_date.isoformat(),
                "party_size": 4
            }
        )
        assert avail_resp.status_code == 200, f"Availability check failed: {avail_resp.text}"
        avail_data = avail_resp.json()
        print(f"[2] Dynamic Availability Engine: OK")
        print(f"    - Date: {avail_data['date']}, Party Size: {avail_data['party_size']}")
        print(f"    - Total Bookable Slots Found: {len(avail_data['available_slots'])}")
        if avail_data['available_slots']:
            sample_slot = avail_data['available_slots'][0]
            print(f"    - Sample Slot: {sample_slot['time']} ({sample_slot['available_tables_count']} matching tables available)")

        # 3. Successful Reservation Creation
        res_time = tashkent_tz.localize(datetime.combine(target_date, time(18, 0)))
        create_payload = {
            "restaurant_id": 1,
            "table_id": 2,  # T-2 (capacity 2-4)
            "customer_name": "Aziz Rakhimov",
            "customer_phone": "+998901112233",
            "party_size": 4,
            "reservation_time": res_time.isoformat()
        }
        res_resp = await client.post("/api/v1/reservations", json=create_payload)
        assert res_resp.status_code == 201, f"Initial reservation creation failed: {res_resp.text}"
        created_res = res_resp.json()
        print(f"[3] Standard Reservation Creation: OK")
        print(f"    - Reservation ID: #{created_res['id']} (Status: {created_res['status']})")
        print(f"    - Table ID: {created_res['table_id']} | Time: {created_res['reservation_time']}")

        # 4. CONCURRENCY CONTROL & ROW LOCKING DEMONSTRATION
        # Fire 2 identical simultaneous booking requests for Table 3 (T-3) at 19:30
        print("\n[4] CONCURRENCY & RACE CONDITION TEST (Simultaneous Double-Booking Attack)")
        conflict_time = tashkent_tz.localize(datetime.combine(target_date, time(19, 30)))
        table_to_lock = 3  # T-3

        payload_client_a = {
            "restaurant_id": 1,
            "table_id": table_to_lock,
            "customer_name": "Concurrent Client A (Alice)",
            "customer_phone": "+998901110001",
            "party_size": 4,
            "reservation_time": conflict_time.isoformat()
        }
        payload_client_b = {
            "restaurant_id": 1,
            "table_id": table_to_lock,
            "customer_name": "Concurrent Client B (Bob)",
            "customer_phone": "+998901110002",
            "party_size": 4,
            "reservation_time": conflict_time.isoformat()
        }

        print(f"    -> Dispatching 2 concurrent POST /api/v1/reservations requests for Table {table_to_lock} at {conflict_time.strftime('%H:%M')}...")
        response_a, response_b = await asyncio.gather(
            client.post("/api/v1/reservations", json=payload_client_a),
            client.post("/api/v1/reservations", json=payload_client_b),
            return_exceptions=False
        )

        status_codes = {response_a.status_code, response_b.status_code}
        print(f"    -> Client A Result: Status {response_a.status_code}")
        print(f"    -> Client B Result: Status {response_b.status_code}")

        # Assert row locking prevented double booking: Exactly one 201 and one 409
        assert 201 in status_codes, "Expected one request to succeed with HTTP 201"
        assert 409 in status_codes, "Expected the conflicting request to be rejected with HTTP 409"

        conflict_response = response_a if response_a.status_code == 409 else response_b
        conflict_json = conflict_response.json()
        print("    [ROW LOCKING VERIFIED] Conflicting request rejected with uniform error:")
        print(f"       Code: {conflict_json['error']['code']}")
        print(f"       Message: \"{conflict_json['error']['message']}\"")
        assert "Selected table is no longer available" in conflict_json['error']['message']

        # 5. B2B Vendor Dashboard: Floor Plan
        fp_resp = await client.get("/api/v1/vendor/floor-plan", params={"restaurant_id": 1})
        assert fp_resp.status_code == 200, f"Floor plan query failed: {fp_resp.text}"
        fp_data = fp_resp.json()
        total_tables_in_fp = sum(len(z['tables']) for z in fp_data['zones'])
        print(f"\n[5] B2B Vendor Floor Plan: OK")
        print(f"    - Restaurant: {fp_data['restaurant_name']}")
        print(f"    - Zones Count: {len(fp_data['zones'])} | Total Tables: {total_tables_in_fp}")

        # 6. B2B Vendor Dashboard: Table Status / Walk-in Seating
        seat_resp = await client.patch(
            "/api/v1/vendor/tables/4/status",
            json={
                "seat_walk_in": True,
                "customer_name": "Walk-in Diplomat",
                "party_size": 4
            }
        )
        assert seat_resp.status_code == 200, f"Walk-in seating failed: {seat_resp.text}"
        print(f"[6] B2B Table Status & Walk-in Seating: OK")
        print(f"    - {seat_resp.json()['message']}")

        # 7. B2B Vendor Dashboard: Analytics
        analytics_resp = await client.get("/api/v1/vendor/analytics", params={"restaurant_id": 1})
        assert analytics_resp.status_code == 200, f"Analytics query failed: {analytics_resp.text}"
        analytics_data = analytics_resp.json()
        print(f"[7] B2B Vendor Analytics: OK")
        print(f"    - Total Tables: {analytics_data['total_tables']}")
        print(f"    - Active Tables: {analytics_data['active_tables']}")
        print(f"    - Occupancy Rate: {analytics_data['occupancy_rate_pct']}%")
        print(f"    - Total Parties Today: {analytics_data['total_parties_today']}")

    print("\n" + "=" * 70)
    print("ALL TEST SUITE ASSERTIONS PASSED WITH ZERO CONFLICTS OR LEAKS!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_test_suite())
