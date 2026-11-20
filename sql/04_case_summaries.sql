-- Account Takeover Detection: Cortex AI_COMPLETE drafts a case summary for the top alerts.
-- Runs once for the top 20 alerts and stores the results, so model cost stays small and bounded.
-- If this model is not available to your account, run SHOW CORTEX BASE MODELS and pick another.
USE ROLE ATO_DEMO_ROLE;
USE WAREHOUSE ATO_DEMO_WH;
USE SCHEMA ACCOUNT_TAKEOVER.DATA;

CREATE OR REPLACE TABLE CASE_SUMMARIES AS
WITH top AS (SELECT * FROM ATO_ALERTS WHERE alert_rank <= 20),
facts AS (
  SELECT t.customer_id, t.alert_rank,
    'Customer ' || t.customer_name || ' (' || t.customer_id || '), home city ' || t.home_city
    || '. Alert score ' || t.alert_score || '. Rules fired: ' || REPLACE(t.rules, '_', ' ') || '. '
    || COALESCE('Credential change at ' || TO_CHAR(s.cred_change_ts, 'YYYY-MM-DD HH24:MI') || ', new payee ' || s.new_payee
                || ', transfer of $' || s.transfer_amount || ' within 24 hours. ', '')
    || COALESCE('Login speed between locations of ' || ROUND(it.max_kmh) || ' km/h. ', '')
    || COALESCE('First login from a new device in country ' || nd.country || ' followed by a payment. ', '')
    || COALESCE(m.denials || ' MFA push denials before an approval. ', '')
    || COALESCE('Login from IP ' || cs.ip_address || ', which failed against ' || cs.customers_failed || ' customers. ', '')
    || COALESCE('Transfer of $' || ua.max_amount || ' against a baseline median of $' || ROUND(ua.baseline_median) || '. ', '')
    AS facts
  FROM top t
  LEFT JOIN RULE_TAKEOVER_SEQUENCE s    ON s.customer_id = t.customer_id
  LEFT JOIN RULE_IMPOSSIBLE_TRAVEL it   ON it.customer_id = t.customer_id
  LEFT JOIN RULE_NEW_DEVICE_COUNTRY nd  ON nd.customer_id = t.customer_id
  LEFT JOIN RULE_MFA_FATIGUE m          ON m.customer_id = t.customer_id
  LEFT JOIN RULE_CREDENTIAL_STUFFING cs ON cs.customer_id = t.customer_id
  LEFT JOIN RULE_UNUSUAL_AMOUNT ua      ON ua.customer_id = t.customer_id
)
SELECT customer_id, alert_rank, CURRENT_TIMESTAMP() AS generated_at,
  TRIM(AI_COMPLETE(
    'llama3.3-70b',
    'You are drafting a case note for a bank fraud investigator reviewing a possible account takeover. '
    || 'In at most 4 short sentences: summarise what happened in time order, say how strongly it suggests '
    || 'takeover and why, and recommend the next investigative step. Use only these facts; do not invent any. '
    || 'Start directly with the summary: no title, preamble or sentence count. '
    || facts
  ), '" ') AS case_summary  -- the model sometimes wraps its answer in quotes
FROM facts;
