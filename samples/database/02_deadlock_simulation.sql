-- =========================================================================
-- SCRIPT 02: DEADLOCK SIMULATION & FORENSICS (SQL ERROR 1205)
-- =========================================================================

USE EnterpriseCommerceDb;
GO

-- Table Setup for Deadlock Reproduction
IF OBJECT_ID('dbo.AccountA', 'U') IS NOT NULL DROP TABLE dbo.AccountA;
IF OBJECT_ID('dbo.AccountB', 'U') IS NOT NULL DROP TABLE dbo.AccountB;

CREATE TABLE dbo.AccountA (Id INT PRIMARY KEY, Balance DECIMAL(18,2));
CREATE TABLE dbo.AccountB (Id INT PRIMARY KEY, Balance DECIMAL(18,2));

INSERT INTO dbo.AccountA VALUES (1, 1000.00);
INSERT INTO dbo.AccountB VALUES (1, 2000.00);
GO

/*
-- INSTRUCTIONS TO REPRODUCE DEADLOCK:
-- Open two separate query windows in SSMS / Azure Data Studio:

-- [SESSION 1]:
BEGIN TRANSACTION;
UPDATE dbo.AccountA SET Balance = Balance - 100 WHERE Id = 1;
WAITFOR DELAY '00:00:05'; -- Wait 5 seconds to let Session 2 acquire lock
UPDATE dbo.AccountB SET Balance = Balance + 100 WHERE Id = 1;
COMMIT TRANSACTION;

-- [SESSION 2] (Run simultaneously with Session 1):
BEGIN TRANSACTION;
UPDATE dbo.AccountB SET Balance = Balance - 50 WHERE Id = 1;
WAITFOR DELAY '00:00:05';
UPDATE dbo.AccountA SET Balance = Balance + 50 WHERE Id = 1;
COMMIT TRANSACTION;

-- RESULT: SQL Server's Lock Monitor detects circular wait, picks a victim,
-- and terminates one session with:
-- "Msg 1205, Level 13, State 45: Transaction was deadlocked on lock resources
-- with another process and has been chosen as the deadlock victim. Rerun the transaction."
*/

-- =========================================================================
-- QUERYING DEADLOCK XML GRAPHS VIA EXTENDED EVENTS
-- =========================================================================
SELECT 
    XEvent.query('(event/data/value/deadlock)[1]') AS DeadlockGraphXml,
    XEvent.value('(event/@timestamp)[1]', 'datetime2') AS UtcTimestamp
FROM (
    SELECT CAST(target_data AS XML) AS TargetData
    FROM sys.dm_xe_session_targets st
    JOIN sys.dm_xe_sessions s ON s.address = st.event_session_address
    WHERE s.name = 'system_health' AND st.target_name = 'ring_buffer'
) AS Data
CROSS APPLY TargetData.nodes('//RingBufferTarget/event[@name="xml_deadlock_report"]') AS XEventData(XEvent);
GO
