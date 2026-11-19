-- Account Takeover Detection: setup. Creates ONLY the objects below.
--   Role       ATO_DEMO_ROLE   (least privilege for the example)
--   Warehouse  ATO_DEMO_WH     (XSMALL, 60s auto-suspend)
--   Database   ACCOUNT_TAKEOVER (schema DATA)
-- Part A needs a role that can create roles, warehouses and databases (e.g. ACCOUNTADMIN).
-- Synthetic data only. Not production, fraud, security or compliance advice.

-- ---------- Part A: admin ----------
USE ROLE ACCOUNTADMIN;
CREATE ROLE IF NOT EXISTS ATO_DEMO_ROLE;
CREATE WAREHOUSE IF NOT EXISTS ATO_DEMO_WH
  WAREHOUSE_SIZE = 'XSMALL' AUTO_SUSPEND = 60 AUTO_RESUME = TRUE INITIALLY_SUSPENDED = TRUE;
CREATE DATABASE IF NOT EXISTS ACCOUNT_TAKEOVER;
CREATE SCHEMA IF NOT EXISTS ACCOUNT_TAKEOVER.DATA;

GRANT USAGE, OPERATE ON WAREHOUSE ATO_DEMO_WH TO ROLE ATO_DEMO_ROLE;
GRANT OWNERSHIP ON DATABASE ACCOUNT_TAKEOVER TO ROLE ATO_DEMO_ROLE COPY CURRENT GRANTS;
GRANT OWNERSHIP ON SCHEMA ACCOUNT_TAKEOVER.DATA TO ROLE ATO_DEMO_ROLE COPY CURRENT GRANTS;
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE ATO_DEMO_ROLE;   -- AI_COMPLETE
SET me = (SELECT CURRENT_USER());
GRANT ROLE ATO_DEMO_ROLE TO USER IDENTIFIER($me);

-- ---------- Part B: demo role ----------
USE ROLE ATO_DEMO_ROLE;
USE WAREHOUSE ATO_DEMO_WH;
USE SCHEMA ACCOUNT_TAKEOVER.DATA;

CREATE OR REPLACE TABLE CUSTOMERS (
  customer_id STRING PRIMARY KEY, customer_name STRING, segment STRING, home_city STRING, home_country STRING,
  confirmed_ato BOOLEAN COMMENT 'Synthetic ground truth from closed investigations; used only to measure rules');
CREATE OR REPLACE TABLE IDENTITY_EVENTS (
  event_id STRING PRIMARY KEY, customer_id STRING, event_ts TIMESTAMP_NTZ,
  event_type STRING COMMENT 'LOGIN_SUCCESS, LOGIN_FAIL, MFA_DENY, MFA_APPROVE',
  ip_address STRING, device_id STRING, city STRING, country STRING,
  latitude FLOAT, longitude FLOAT, session_id STRING);
CREATE OR REPLACE TABLE ACCOUNT_CHANGES (
  change_id STRING PRIMARY KEY, customer_id STRING, change_ts TIMESTAMP_NTZ,
  change_type STRING COMMENT 'PASSWORD_RESET, PHONE_CHANGE, EMAIL_CHANGE, PAYEE_ADDED',
  payee_id STRING, session_id STRING);
CREATE OR REPLACE TABLE TRANSACTIONS (
  txn_id STRING PRIMARY KEY, customer_id STRING, txn_ts TIMESTAMP_NTZ, amount NUMBER(12,0),
  payee_id STRING, session_id STRING);

-- Rule weights live in a table so analysts can tune them without editing SQL.
CREATE OR REPLACE TABLE RULE_WEIGHTS (rule_name STRING PRIMARY KEY, points NUMBER);
INSERT INTO RULE_WEIGHTS VALUES
  ('takeover_sequence', 50), ('impossible_travel', 30), ('new_device_country', 25),
  ('mfa_fatigue', 35), ('credential_stuffing', 20), ('unusual_amount', 15);
