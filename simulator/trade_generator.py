import json
import os
import random
import uuid
from datetime import datetime, timedelta, date
from pathlib import Path

# Reproducible seed ensures CI tests can assert specific fraud row counts
random.seed(42)

# --- CONFIGURATION & MOCK DATA ---
INSTRUMENTS = [
    {"instrument_id": "INST-RY", "symbol": "RY", "base_price": 130.0, "instrument_type": "EQUITY", "currency": "CAD", "exchange": "TSX"},
    {"instrument_id": "INST-TD", "symbol": "TD", "base_price": 82.0, "instrument_type": "EQUITY", "currency": "CAD", "exchange": "TSX"},
    {"instrument_id": "INST-SHOP", "symbol": "SHOP", "base_price": 95.0, "instrument_type": "EQUITY", "currency": "CAD", "exchange": "TSX"},
    {"instrument_id": "INST-CNR", "symbol": "CNR", "base_price": 175.0, "instrument_type": "EQUITY", "currency": "CAD", "exchange": "TSX"},
    {"instrument_id": "INST-AAPL", "symbol": "AAPL", "base_price": 190.0, "instrument_type": "EQUITY", "currency": "USD", "exchange": "NASDAQ"},
    {"instrument_id": "INST-MSFT", "symbol": "MSFT", "base_price": 415.0, "instrument_type": "EQUITY", "currency": "USD", "exchange": "NASDAQ"},
    {"instrument_id": "INST-NVDA", "symbol": "NVDA", "base_price": 875.0, "instrument_type": "EQUITY", "currency": "USD", "exchange": "NASDAQ"},
    {"instrument_id": "INST-SPY", "symbol": "SPY", "base_price": 520.0, "instrument_type": "ETF", "currency": "USD", "exchange": "NYSE"},
]

ACCOUNTS = [
    {"account_id": "ACC-0001", "account_type": "INDIVIDUAL", "risk_tier": 1},
    {"account_id": "ACC-0002", "account_type": "INSTITUTIONAL", "risk_tier": 2},
    {"account_id": "ACC-0003", "account_type": "PROP", "risk_tier": 3},
    {"account_id": "ACC-FRAD", "account_type": "INDIVIDUAL", "risk_tier": 1},
]

CLEAN_ACCOUNTS = [a for a in ACCOUNTS if a["account_id"] != "ACC-FRAD"]
FRAUD_ACCOUNT = next(a for a in ACCOUNTS if a["account_id"] == "ACC-FRAD")

# --- applying the geometic brownian motion concept---

def gbm_price(base: float, vol: float = 0.015) -> float:
    return round(base * (1 + random.gauss(0, vol)), 4)

def t2_settlement(d: date) -> date:
    count, x = 0, d
    while count < 2:
        x += timedelta(days=1)
        if x.weekday() < 5:
            count += 1
    return x

def market_hour_ts(d: date) -> str:
    h = random.randint(9, 15)
    m = random.randint(30 if h == 9 else 0, 59)
    return datetime(d.year, d.month, d.day, h, m, random.randint(0, 59)).isoformat()

# --- CORE LOGIC ---

def make_trade(trade_date: date, inst: dict, account: dict, trade_type: str, price: float = None) -> dict:
    p = price if price is not None else gbm_price(inst["base_price"])
    return {
        "trade_id": str(uuid.uuid4()),
        "account_id": account["account_id"],
        "instrument_id": inst["instrument_id"],
        "trade_type": trade_type,
        "quantity": round(random.uniform(10, 500), 2),
        "price": p,
        "currency": inst["currency"],
        "trade_timestamp": market_hour_ts(trade_date),
        "settlement_date": t2_settlement(trade_date).isoformat(),
        "status": "EXECUTED",
        "broker_id": f"BRK-{random.randint(1, 5):02d}",
        "order_id": None, # Null for standard clean trades
    }

def make_fraud_pair(trade_date: date) -> tuple:
    """
    Creates a 'Wash Trade' pair: Buy and Sell on the same account at the same price.
    Injected to trigger fraud signals: 
    1. Identical Price 
    2. Shared Order ID 
    3. Zero net PnL
    """
    inst = random.choice(INSTRUMENTS)
    shared_oid = str(uuid.uuid4())
    
    buy = make_trade(trade_date, inst, FRAUD_ACCOUNT, "B")
    sell = make_trade(trade_date, inst, FRAUD_ACCOUNT, "S")
    
    sell["price"] = buy["price"]  # Forced match
    buy["order_id"] = shared_oid
    sell["order_id"] = shared_oid
    
    return buy, sell

def generate_day(trade_date: date, n_clean: int = 50, n_fraud_pairs: int = 3) -> list:
    """Generates a full day of mixed clean and fraudulent trading activity."""
    trades = []
    
    # Generate legitimate traffic
    for _ in range(n_clean):
        inst = random.choice(INSTRUMENTS)
        account = random.choice(CLEAN_ACCOUNTS)
        trades.append(make_trade(trade_date, inst, account, random.choice(["B", "S"])))
    
    # Inject deterministic fraud pairs
    for _ in range(n_fraud_pairs):
        b, s = make_fraud_pair(trade_date)
        trades.extend([b, s])
    
    random.shuffle(trades)
    return trades

# --- EXECUTION ---

if __name__ == "__main__":
    output_dir = Path("simulator/output")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate data for the last 5 business days
    today = date.today()
    trade_days = [today - timedelta(days=i) for i in range(7) if (today - timedelta(days=i)).weekday() < 5][:5]
    trade_days.reverse()
    
    total_trades = 0
    for td in trade_days:
        trades = generate_day(td)
        outfile = output_dir / f"trades_{td.isoformat()}.jsonl"
        
        with open(outfile, "w") as f:
            for tr in trades:
                f.write(json.dumps(tr) + "\n")
        
        total_trades += len(trades)
        fraud_count = sum(1 for t in trades if t['account_id'] == 'ACC-FRAD')
        print(f"Generated {outfile.name}: {len(trades)} trades ({fraud_count} fraud rows)")

    print(f"\nSimulation Complete: {total_trades} total trades across {len(trade_days)} days.")