# Car & Bike Garage Management System — Days 1–3

This is the uploaded Day 2 FastAPI + MySQL project extended with Service Management and Mechanic Management. The Customer and Vehicle APIs, including the customer's vehicles response from registration search, remain in place.

## Windows / VS Code setup

1. Extract the ZIP and open the extracted folder containing `requirements.txt` in VS Code.
2. In the VS Code PowerShell terminal run:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   ```

3. In MySQL Workbench, run `CREATE DATABASE IF NOT EXISTS garage_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;` if it does not exist. **Keep your existing Day 2 MySQL database and its customer/vehicle rows.**
4. Copy the `.env` from your working Day 2 folder into `garage_day3`. Your uploaded `.env` is retained in this updated ZIP. If needed, copy `.env.example` to `.env` and edit the URL with the working MySQL credentials. Do not share or commit your password.
5. Run `python -m uvicorn app.main:app --reload` from the project root. Open http://127.0.0.1:8000/docs.

At startup, `Base.metadata.create_all()` creates four new tables: `mechanics`, `service_requests`, `service_history`, and `service_mechanics`. It does not delete existing Customer/Vehicle data or change existing columns. If any of these new tables already exist with a different schema, review their structure before starting.

## API overview

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST / GET | `/api/v1/customers` | Create/list customers |
| GET / PUT / DELETE | `/api/v1/customers/{id}` | Read/update/delete a customer |
| POST / GET | `/api/v1/vehicles` | Create/list vehicles |
| GET | `/api/v1/vehicles/search?registration_number=KA22AB1234` | Find a vehicle's customer and up to 100 of their vehicles |
| GET / PUT / DELETE | `/api/v1/vehicles/{id}` | Read/update/delete a vehicle |
| POST / GET | `/api/v1/mechanics` | Create/list mechanics |
| GET / PUT / DELETE | `/api/v1/mechanics/{id}` | Read/update/delete a mechanic |
| GET | `/api/v1/mechanics/{id}/services` | List assigned services |
| POST / GET | `/api/v1/services` | Create/list services; list accepts `customer_id`, `vehicle_id`, or `mechanic_id` filters |
| GET / PUT | `/api/v1/services/{id}` | Read/update service details (PUT does not change customer/vehicle or status) |
| PATCH | `/api/v1/services/{id}/status` | Move service to an allowed next status |
| GET | `/api/v1/services/{id}/history` | View creation, edits, assignments and status events |
| POST / DELETE | `/api/v1/services/{id}/mechanics/{mechanic_id}` | Assign/unassign a mechanic |

Service requests are retained to preserve history; there is no service DELETE endpoint. A mechanic with assigned services cannot be deleted until unassigned. A customer or vehicle referenced by a service cannot be deleted. Unassigning a mechanic preserves the assignment event in history.

## Swagger test order

1. Create a customer and vehicle using the existing POST endpoints. Note their returned IDs. The service's `customer_id` must own the selected `vehicle_id`.
2. POST `/api/v1/mechanics`:

   ```json
   {"name":"Ramesh","phone":"9876543212","specialization":"Engine repair","experience_years":6}
   ```

3. POST `/api/v1/services` (replace `1` with your real customer and vehicle IDs):

   ```json
   {"customer_id":1,"vehicle_id":1,"service_type":"Regular service","complaint":"Engine noise and oil change","arrival_date":"2026-09-29","expected_delivery_date":"2026-10-02"}
   ```

4. POST `/api/v1/services/1/mechanics/1` with actual service and mechanic IDs. GET `/api/v1/mechanics/1/services` lists that mechanic's services.
5. PATCH `/api/v1/services/1/status`:

   ```json
   {"status":"Inspection","note":"Initial inspection completed"}
   ```

6. Continue with `In Service`, optionally `Waiting for Parts` then back to `In Service`, then `Completed` and `Delivered`. GET `/api/v1/services/1/history` shows the events in order. Directly jumping from `Received` to `Delivered` returns 409.
7. GET `/api/v1/services?vehicle_id=1` lists service history for a vehicle. GET `/api/v1/services?customer_id=1` lists a customer's services.

Possible statuses: `Received` → `Inspection` → `In Service` → `Completed` → `Delivered`. From `Inspection` or `In Service`, `Waiting for Parts` is allowed; then return to `In Service`.

A successful POST returns 201, ordinary reads/updates/assignments return 200, missing records return 404, invalid input or a vehicle belonging to another customer returns 422, and duplicate phones or invalid status transitions return 409.

## Files added for Day 3

- `app/models/service.py`, `app/models/mechanic.py`: database tables and relationships.
- `app/schemas/service.py`, `app/schemas/mechanic.py`: request validation and response structures.
- `app/crud/service.py`, `app/crud/mechanic.py`: database operations.
- `app/api/v1/services.py`, `app/api/v1/mechanics.py`: API routes.
- `app/models/customer.py`, `app/models/vehicle.py`, `app/main.py`: updated to register the relationships and routers.

The Customer and Vehicle router files from your uploaded project were preserved. The project does not yet include authentication; add it before public deployment.

## Day 4 — Spare Parts and Inventory

This is the same project and the same `garage_db` database. At startup, SQLAlchemy creates the new `parts` and `service_part_usages` tables if they do not exist. Keep the `.env` file from your working Day 3 project. Existing tables and rows remain unchanged.

### Swagger test order

1. POST `/api/v1/parts` with:

   ```json
   {"name":"Engine Oil Filter","part_number":"OF-123","category":"Filters","available_quantity":5,"price":250.00,"minimum_stock_level":2}
   ```

2. GET `/api/v1/parts` lists inventory. GET `/api/v1/parts/{part_id}` reads a part. PUT `/api/v1/parts/{part_id}` edits name, number, category, price, and minimum level; it intentionally does not edit quantity.
3. Create a service through the Day 3 endpoint if you do not already have one. POST `/api/v1/services/{service_id}/parts` with:

   ```json
   {"part_id":1,"quantity_used":3}
   ```

   Replace IDs with real values. Quantity changes from 5 to 2; the response contains `"low_stock": true` and a reorder alert. GET `/api/v1/parts/low-stock` lists all parts at or below their minimum level. This is an API alert for staff viewing Swagger or a client; it does not send email or push notifications.
4. GET `/api/v1/services/{service_id}/parts` lists part usage for that service. GET `/api/v1/services/{service_id}/history` also shows the `PART_USED` event.
5. POST `/api/v1/parts/{part_id}/restock` with `{"quantity":10}` to add stock. The part leaves the low-stock list when its quantity exceeds the minimum.

A part that has usage history cannot be deleted. Invalid quantities return 422; insufficient stock and duplicate part numbers return 409. Usage is blocked when a service is Completed or Delivered. Stock deduction uses a conditional SQL update in the same transaction as the usage and history inserts, so a failed request does not consume stock. The unit price is captured on each usage record, preserving the service's historical price if the current part price later changes.

### Logic, architecture, and review explanation

- `app/models/part.py`: `Part` stores the inventory fields; `ServicePartUsage` links a part to a service through `part_id` and `service_id`, recording quantity, unit price, and timestamp. One service can use many parts; one part can be used by many services over time.
- `app/schemas/part.py`: Pydantic schemas validate incoming JSON (`quantity_used > 0`, nonnegative stock and price) and define response fields such as `low_stock`.
- `app/crud/part.py`: SQLAlchemy `select()` queries list inventory and usage records.
- `app/api/v1/parts.py`: FastAPI router exposes POST (create or use part), GET (read/list/alerts), PUT (edit details), and DELETE (remove an unused part). It also performs an atomic stock update for part usage.
- `app/main.py` registers the model and router. The SQLAlchemy session comes from `app/core/database.py` and connects to MySQL using `.env`.

Request flow: Swagger sends JSON → router calls schema validation → router checks service and stock → SQLAlchemy updates `parts` and inserts `service_part_usages` plus `service_history` → one commit saves all changes → response reports remaining stock and a low-stock alert.

For a review: “I extended the existing FastAPI and MySQL garage project with spare parts inventory. Each part has a unique part number, category, quantity, price, and minimum stock level. When a part is used for a service, an atomic database update deducts stock and a usage row records the quantity and price. Staff can query the low-stock endpoint and restock parts. The existing Customer, Vehicle, Service, and Mechanic modules continue to work.”

## Complete Garage System — Billing, Cost Tracking and Dashboard

Continue using the existing `garage_db` and your working `.env`. No old tables are dropped. Startup creates `service_charges`, `bills`, and `bill_payments` and checks all ORM relationships. Copy the complete `app` folder when updating the existing project, including the updated Service model; mixing old models with new routers causes missing-relationship errors.

### Complete Swagger workflow

1. Create a customer and their vehicle using the existing APIs.
2. Create a service, then create and assign a mechanic.
3. Create inventory parts, then use them through POST `/api/v1/services/{service_id}/parts`. Stock is deducted and the price is captured in the usage record.
4. POST `/api/v1/services/{service_id}/charges` with `{"description":"Engine repair labour","amount":800.00,"notes":"Oil leak repaired"}`. Additional labour charge rows are allowed.
5. GET `/api/v1/services/{service_id}/cost` shows customer, vehicle, mechanics, labour lines, parts lines, notes, and total service cost.
6. Move the service through Inspection and In Service to Completed. Optional Waiting for Parts returns to In Service.
7. POST `/api/v1/bills` with `{"service_id":1,"discount":100.00,"tax_percent":18.00}` using the actual service ID. Billing is permitted only for Completed or Delivered services. One bill per service is allowed. The tax percentage is an input chosen by staff; the example is test data, not a determination of applicable tax.
8. GET `/api/v1/bills/{bill_id}` views the bill and its stored customer/vehicle/service details. Bill number format is `GAR-000001`.
9. POST `/api/v1/bills/{bill_id}/payments` with `{"amount":500.00,"method":"UPI","reference":"TEST-PAYMENT-001"}`. Payment status changes automatically from Pending to Partially Paid to Paid. Rejects payments above the balance. This records received payments; it does not process payment gateway transactions. Repeating the POST records another payment, so do not retry a successful payment request.
10. GET `/api/v1/bills/{bill_id}/payments` shows payment history. GET `/api/v1/dashboard` shows counts, collected revenue, billed amount and low-stock count.
11. GET `/api/v1/customers/{customer_id}/vehicles` shows up to 100 customer vehicles; GET `/api/v1/customers/{customer_id}/services` shows customer service records with pagination.

### Calculation example

Labour 800 + parts 250 = subtotal 1050. Discount 100 leaves taxable amount 950. Tax at 18% is 171. Final amount is 1121. A payment of 500 leaves 621 outstanding and status Partially Paid. Money calculations use Decimal and round to two decimal places.

### Dashboard definitions

- Cars and bikes are counts from vehicles.
- Vehicles under service counts distinct vehicles with Received, Inspection, In Service, or Waiting for Parts jobs.
- Pending services counts jobs in those active statuses.
- Completed services includes Completed and Delivered.
- Total revenue is money recorded as received in bill_payments, while total billed amount is the sum of invoice amounts.
- Low stock means available quantity is less than or equal to minimum stock level.

### Technology and architecture

Python handles application logic. FastAPI routers expose HTTP endpoints and dependency injection. Pydantic schemas validate request data. SQLAlchemy models define MySQL tables and foreign keys. PyMySQL is the MySQL driver. Uvicorn runs the app. Swagger provides a browser interface to test this backend. The dashboard is a JSON API; a separate graphical user interface is not included.

Models link Customer → Vehicle → Service. Service links to mechanics through service_mechanics, to parts through service_part_usages, and to labour through service_charges. Bill links to one service; Payment links to one bill. Bill details store a snapshot so editing customer contact details later does not change an existing invoice.

## Updating this uploaded project

Extract this ZIP: app, requirements.txt and .env are directly at the archive root. Open the extracted folder in VS Code. Your uploaded .env and database connection files are retained. Run python -m pip install -r requirements.txt, then python -m uvicorn app.main:app --reload. Swagger: http://127.0.0.1:8000/docs. The app creates the new billing tables alongside existing data.
