-- PostgreSQL 16 — Azure Database for PostgreSQL Flexible Server -- Schema: trading (best practice: avoid public
schema for application tables) CREATE SCHEMA IF NOT EXISTS trading;

CREATE TABLE trading.instrument (
    instrument_id varchar(20) NOT NULL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    instrument_type VARCHAR(20) NOT NULL,
    CHECK (instrument_type IN ('EQUITY', 'BOND', 'ETF','FOREX', 'CRYPTO')),
    currency VARCHAR(3) NOT NULL,
    exchange VARCHAR(20) NOT NULL,
    sector VARCHAR(50),
    isin CHAR(12),
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL
);

CREATE TABLE trading.account (
    account_id VARCHAR (20) NOT NULL PRIMARY KEY,
    account_name VARCHAR(50) NOT NULL,
    account_type VARCHAR(20) NOT NULL,
    CHECK (account_type IN ('INDIVIDUAL', 'INSTITUTIONAL', 'PROP')),
    account_status VARCHAR(20) NOT NULL,
    CHECK (account_status IN ('ACTIVE', 'CLOSED', 'SUSPENDED')),
    base_currency VARCHAR(3) NOT NULL,
    risk_tier VARCHAR(20) NOT NULL,
    CHECK (risk_tier BETWEEN 1 AND 3),
    opened_date DATE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
);

CREATE TABLE trading.trade (
    trade_id VARCHAR(36) NOT NULL PRIMARY KEY,
    account_id VARCHAR(20) NOT NULL,
    REFERENCES trading.account(account_id),
    instrument_id VARCHAR(20) NOT NULL,
    REFERENCES trading.instrument(instrument_id),
    trade_type CHAR(1) NOT NULL CHECK (trade_type IN ('B', 'S')),
    quantity NUMERIC(18, 4) NOT NULL,
    price NUMERIC(18, 6) NOT NULL,
    trade_date DATE NOT NULL,
    gross_value DECIMAL (18,6) GENERATED ALWASYS AS (quantity * price) STORED,
    currency CHAR(3) NOT NULL,
    trade_timestamp TIMESTAMPTZ NOT NULL
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    CHECK (status IN ('PENDING', 'EXECUTED', 'CANCELLED', 'FAILED')),
    broker_id VARCHAR(20),
    order_id VARCHAR(36),
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
);

CREATE INDEX idx_trades_account ON trading.trades(account_id);
CREATE INDEX idx_trades_instrument ON trading.trades(instrument_id);
CREATE INDEX idx_trades_timestamp ON trading.trades(trade_timestamp DESC);

CREATE TABLE trading.position (
    position_id BIGSERIAL NOT NULL PRIMARY KEY,
    account_id VARCHAR(20) NOT NULL,
    REFERENCES trading.account(account_id),
    instrument_id VARCHAR(20) NOT NULL,
    REFERENCES trading.instrument(instrument_id),
    quantity_long NUMERIC(18, 6) NOT NULL DEFAULT 0,
    quantity_short NUMERIC(18, 6) NOT NULL DEFAULT 0,
    average_cost NUMERIC(18, 6) ,
    market_value NUMERIC(18, 6),
    unrealized_pnl NUMERIC(18, 6),
    currency CHAR(3) NOT NULL,
    as_of_date DATE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
    CONSTRAINT uq_position UNIQUE (account_id, instrument_id, as_of_date)
);

CREATE TABLE trading.market_prices (
    price_id BIGSERIAL NOT NULL PRIMARY KEY,
    instrument_id VARCHAR(20) NOT NULL,
    REFERENCES trading.instrument(instrument_id),
    price_date DATE NOT NULL,
    open_price NUMERIC(18, 6),
    high_price NUMERIC(18, 6),
    low_price NUMERIC(18, 6),
    close_price NUMERIC(18, 6),
    volume BIGINT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
    CONSTRAINT uq_market_price UNIQUE (instrument_id, price_date)
);
