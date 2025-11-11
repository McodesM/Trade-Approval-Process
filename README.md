### Design Choices:
Implicit Approver Assignment: The approver is not manually assigned. The first non-requester who performs an Update or Approve action automatically becomes the trade’s approver. This matches the example scenario where the approver makes an edit before final approval, avoiding the need for a dedicated “assign approver” endpoint.

Thin Views, Rich Services: The API viewset layer is deliberately kept minimal, only handling request parsing, validation, and response formatting.
All business logic, permission checks, and state transitions are kept in the services/ layer (trade_workflow.py, use_cases.py).
This separation keeps the system modular, testable, and easy to extend.

DTO-Centric Workflow: All operations are applied to immutable TradeDTO (Data Transfer Objects) rather than the ORM models directly.
This isolates domain logic from persistence concerns and simplifies testing and reasoning about transitions.

No User Table: Explicit User IDs:
User identity is passed explicitly via userId in the request body, rather than being derived from Django’s authentication system.
This design aligns with the brief, which only specifies user IDs in requests and examples, and keeps the scope focused on workflow logic rather than authentication.

### Enhancement:
Extended the workflow to allow multiple successive updates while in the NeedsReapproval state.
This reflects realistic approval cycles, where an approver may make several adjustments before the requester provides final reapproval.
The requester can still only reapprove once the trade is in NeedsReapproval state.


# 1) Setup

Python 3.11+

pip 
venv (optional)

# 2) Install & run

### (optional) create venv
python -m venv .venv

. .venv/bin/activate 

Windows: .venv\Scripts\activate

### install
pip install -r requirements.txt

### migrate DB (SQLite)
python manage.py makemigrations
python manage.py migrate

### run tests
python manage.py test

### run server
python manage.py runserver
### API at http://127.0.0.1:8000/api/


# 3) API Overview

Base URL prefix: /api/

| Endpoint                          | Method  | Description                                                     | Allowed States (pre → post)                                                                                             | Who                                                                               |
| --------------------------------- | ------- | --------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| `/trades/submit`                  | `POST`  | Create & submit a trade                                         | `Draft → PendingApproval`                                                                                               | **Requester**                                                                     |
| `/trades/{id}/approve`            | `POST`  | Approve a submitted trade or re-approve after updates           | `PendingApproval / NeedsReapproval → Approved`                                                                          | **Approver** (first non-requester becomes approver) or **Requester** (re-approve) |
| `/trades/{id}/cancel`             | `POST`  | Cancel a trade                                                  | `* → Cancelled` (not if already terminal)                                                                               | **Requester** or **Approver**                                                     |
| `/trades/{id}/update`             | `PATCH` | Approver updates economic fields (partial), requires reapproval | `PendingApproval → NeedsReapproval` *(optionally also `NeedsReapproval → NeedsReapproval`)* | **Approver** (first updater can be assigned)                                      |
| `/trades/{id}/send-to-execute`    | `POST`  | Send an approved trade to counterparty                          | `Approved → SentToCounterparty`                                                                                         | **Approver**                                                                      |
| `/trades/{id}/book`               | `POST`  | Book the trade with `strike` once executed                      | `SentToCounterparty → Executed`                                                                                         | **Requester** or **Approver**                                                     |
| `/trades/{id}/history`            | `GET`   | Tabular history of actions                                      | n/a                                                                                                                     | Anyone                                                                            |
| `/trades/{id}/diff`               | `POST`  | Differences between two versions                                | n/a                                                                                                                     | Anyone                                                                            |
| `/trades/{id}/versions/{version}` | `GET`   | Trade details snapshot at a version                             | n/a                                                                                                                     | Anyone                                                                            |


# 4) Request/Response Shapes & Examples

All requests are JSON; all responses are JSON.
Unauthenticated; pass userId explicitly where needed.

## Submit Trade

POST /api/trades/submit/

{
  "userId": "user_001",
  "tradeDetails": {
    "tradingEntity": "Validus Capital Ltd",
    "counterparty": "Bank of England",
    "direction": "BUY",
    "style": "FORWARD",
    "notionalCurrency": "USD",
    "notionalAmount": 5000000.00,
    "underlying": ["USD", "EUR"],
    "tradeDate": "2025-11-01",
    "valueDate": "2025-11-05",
    "deliveryDate": "2025-11-10"
  }
}


Response

{ "id": 1, "state": "PendingApproval" }

## Approve

POST /api/trades/1/approve/

{ "userId": "user_002" }


Response

{ "id": 1, "state": "Approved" }

--Update

PATCH /api/trades/1/update/

{
  "userId": "user_002",
  "tradeUpdateDetails": { "notionalAmount": 2000000.00 }
}


Response

{ "id": 1, "state": "NeedsReapproval" }

## Send to Execute

POST /api/trades/1/send-to-execute/

{ "userId": "user_002" }


Response

{ "id": 1, "state": "SentToCounterparty" }

--Book

POST /api/trades/1/book/

{ "userId": "user_001", "strike": 1.24567 }


Response

{ "id": 1, "state": "Executed", "strike": "1.245670" }

## History

GET /api/trades/1/history/

Response (truncated)

{
  "tradeId": 1,
  "history": [
    { "action": "Submit", "actorUserId": "user_001", "toState": "PendingApproval" },
    { "action": "Approve", "actorUserId": "user_002", "toState": "Approved" }
  ]
}

## Diff Versions

POST /api/trades/1/diff/

{ "fromVersion": 1, "toVersion": 2 }


Response

{ "diff": { "notional_amount": ["5000000.00", "2000000.00"] } }

## Version Snapshot

GET /api/trades/1/versions/1/

Response (truncated)

{
  "tradeId": 1,
  "version": 1,
  "state": "PendingApproval",
  "snapshot": { "notional_amount": "5000000.00", "direction": "BUY" }
}

# 5) Scenarios

## Scenario 1- Submit -> Book:

### Endpoint: POST /api/trades/submit/

--Input:

{
  "userId": "user_001",
  "tradeDetails": {
    "tradingEntity": "Validus Capital Ltd",
    "counterparty": "Bank of England",
    "direction": "BUY",
    "style": "FORWARD",
    "notionalCurrency": "USD",
    "notionalAmount": 5000000.00,
    "underlying": ["USD", "EUR"],
    "tradeDate": "2025-11-01",
    "valueDate": "2025-11-05",
    "deliveryDate": "2025-11-10"
  }
}
--Output:

{ "id": 1, "state": "PendingApproval" }

### Endpoint: POST /api/trades/1/approve/

--Input: { "userId": "user_002" }

--Output: { "id": 1, "state": "Approved" }

### Endpoint: POST /api/trades/1/send-to-execute/

--Input: { "userId": "user_002" }

--Output: { "id": 1, "state": "SentToCounterparty" }

### Endpoint: POST /api/trades/1/book/

--Input: { "userId": "user_001", "strike": 1.24567 }

--Output: { "id": 1, "state": "Executed", "strike": "1.245670" }

## Scenario 2- Trade updated before approval:

### Endpoint: POST /api/trades/submit/

--Input: { ...same as Scenario 1... }

--Output: { "id": 2, "state": "PendingApproval" }

### Endpoint: PATCH /api/trades/2/update/

--Input:

{
  "userId": "user_002",
  "tradeUpdateDetails": { "notionalAmount": 2000000.00 }
}

--Output:

{ "id": 2, "state": "NeedsReapproval" }

### Endpoint: POST /api/trades/2/approve/

--Input: { "userId": "user_001" }

--Output: { "id": 2, "state": "Approved" }

### Endpoint: POST /api/trades/2/send-to-execute/

--Input: { "userId": "user_002" }

--Output: { "id": 2, "state": "SentToCounterparty" }

### Endpoint: POST /api/trades/2/book/

--Input: { "userId": "user_001", "strike": 1.14567 }

--Output: { "id": 2, "state": "Executed", "strike": "1.145670" }

## Scenario 3-cancel:

### Endpoint: POST /api/trades/submit/

--Input: { ...same as Scenario 1... }

--Output: { "id": 3, "state": "PendingApproval" }

### Endpoint: POST /api/trades/3/approve/

--Input: { "userId": "user_002" }

--Output: { "id": 3, "state": "Approved" }

### Endpoint: POST /api/trades/3/cancel/

--Input: { "userId": "user_001" }

--Output: { "id": 3, "state": "Cancelled" }

## Scenario 4 – Multi-update before Reapproval

### Endpoint: PATCH /api/trades/2/update/

--Input:

{
  "userId": "user_002",
  "tradeUpdateDetails": { "notionalAmount": 2500000.00 }
}

--Output:

{ "id": 2, "state": "NeedsReapproval" }

### Endpoint: PATCH /api/trades/2/update/

--Input:

{
  "userId": "user_002",
  "tradeUpdateDetails": { "style": "OPTION" }
}

--Output:

{ "id": 2, "state": "NeedsReapproval" }

### Endpoint: POST /api/trades/2/approve/

--Input:

{ "userId": "user_001" }

--Output:

{ "id": 2, "state": "Approved" }

## Note:

AI tools were used for test and model boilerplate setup, documentation formatting, and refining phrasing in the README. All system design decisions, workflow logic, and state transition rules were independently reasoned, implemented, and validated by me.