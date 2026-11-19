-- Account Takeover Detection: cleanup. Removes everything the setup created.
USE ROLE ACCOUNTADMIN;
DROP DATABASE IF EXISTS ACCOUNT_TAKEOVER;   -- tables, rule views, alerts view, case summaries
DROP WAREHOUSE IF EXISTS ATO_DEMO_WH;
DROP ROLE IF EXISTS ATO_DEMO_ROLE;
