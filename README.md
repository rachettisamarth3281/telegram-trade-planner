# Telegram Signal Paper Trading System

A modular, audit-first paper trading signal analysis and simulation platform.

> [!IMPORTANT]
> **SIMULATION ONLY**: This system is strictly engineered for receiving, parsing, validating, risk calculation, paper execution, and statistical analysis of trading signals. **No live exchange or broker orders are ever placed.**

---

## 🌟 Phase 2: Telegram Signal Ingestion Layer

The Telegram Ingestion Layer provides an MTProto client listener and development mock mode to ingest messages from VIP channels with complete auditability, idempotency, and message filtering.

### Key Ingestion Features:
1. **Telethon MTProto Client**:
   - Listens to configured private VIP channels or groups (`TELEGRAM_SOURCE_CHAT_ID`).
   - Supports userbot authentication with session persistence.
2. **Idempotency Guarantee**:
   - Unique composite index on `(source_chat_id, telegram_message_id)` ensures that duplicate messages are rejected and never create duplicate signal records.
3. **Filtering Rules**:
   - Automatically ignores media without text/captions (`MEDIA_WITHOUT_TEXT_CAPTION`).
   - Ignores empty messages (`EMPTY_MESSAGE_TEXT`, `WHITESPACE_ONLY_MESSAGE`).
   - Ignores system service messages (`SYSTEM_SERVICE_MESSAGE`).
   - Ignores non-signal reactions/emojis (`MESSAGE_TOO_SHORT_NON_SIGNAL`).
4. **Preserved Auditability**:
   - Stores the exact original message, Telegram message ID, chat ID, sender ID, username, and timestamps (`telegram_timestamp`, `received_at`, `created_at`, `updated_at`).
5. **Secure Structured Logging**:
   - Emits structured events:
     - `TELEGRAM_MESSAGE_RECEIVED`
     - `TELEGRAM_MESSAGE_DUPLICATE`
     - `TELEGRAM_MESSAGE_IGNORED`
     - `TELEGRAM_CONNECTION_ERROR`
   - Automatically masks API credentials, hashes, session strings, and phone numbers in logs.
6. **Development / Mock Ingestion Mode**:
   - Run without Telegram credentials by setting `TELEGRAM_MOCK_MODE=true` or posting directly to the mock API endpoint `/api/v1/telegram/mock-ingest`.

---

## 🛠️ Telegram Setup Guide

### Step 1: Obtain Telegram API Credentials
1. Log in to [https://my.telegram.org](https://my.telegram.org) with your Telegram account phone number.
2. Navigate to **API development tools**.
3. Create a new application and copy:
   - `App api_id` (Integer)
   - `App api_hash` (String)

### Step 2: Configure Environment Variables
Copy `.env.example` to `.env` in the root or `backend/` directory:
```env
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=0123456789abcdef0123456789abcdef
TELEGRAM_SESSION=paper_trading_session
TELEGRAM_PHONE=+1234567890
TELEGRAM_SOURCE_CHAT_ID=-1001234567890
```

### Step 3: Run the Ingestion Pipeline
```powershell
cd d:\FX\backend
.\venv\Scripts\activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

On first startup with live credentials, Telethon will prompt in the terminal for the Telegram SMS/login code to authenticate your session file. Once logged in, the session is saved in `paper_trading_session.session`.

### Testing in Mock Development Mode
If you don't have Telegram credentials ready, test the ingestion pipeline using the mock endpoint:
```powershell
# Ingest mock signal via curl or PowerShell:
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/v1/telegram/mock-ingest" `
  -ContentType "application/json" `
  -Body '{"message_id": 1001, "chat_id": "-1001234567890", "text": "Sell gold @ 4350.53\nSL 4358"}'
```

---

## 🧪 Running Automated Tests

```powershell
cd d:\FX\backend
pytest -v
```

All 29 test cases cover:
- Telegram message filtering rules (photos without text, service messages, empty messages)
- Idempotent deduplication (duplicate messages are rejected)
- Exact database persistence of signals and raw text
- Credential masking and structured event logging
- REST mock ingestion endpoints and health checks
