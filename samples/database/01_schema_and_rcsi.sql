-- =========================================================================
-- SCRIPT 01: DATABASE INITIALIZATION, RCSI ENABLEMENT & E-S-R INDEXING
-- =========================================================================

-- 1. Create Enterprise Database
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'EnterpriseCommerceDb')
BEGIN
    CREATE DATABASE EnterpriseCommerceDb;
END
GO

USE EnterpriseCommerceDb;
GO

-- 2. ENABLE READ COMMITTED SNAPSHOT ISOLATION (RCSI)
-- Eliminates reader-writer blocking by using row versioning in tempdb!
ALTER DATABASE EnterpriseCommerceDb
SET READ_COMMITTED_SNAPSHOT ON WITH ROLLBACK IMMEDIATE;
GO

-- 3. Create Orders Table
IF OBJECT_ID('dbo.Orders', 'U') IS NOT NULL
    DROP TABLE dbo.Orders;
GO

CREATE TABLE dbo.Orders
(
    Id UNIQUEIDENTIFIER NOT NULL CONSTRAINT PK_Orders PRIMARY KEY CLUSTERED,
    CustomerId INT NOT NULL,
    TotalAmount DECIMAL(18, 2) NOT NULL,
    OrderStatus VARCHAR(20) NOT NULL,
    OrderDateUtc DATETIME2(3) NOT NULL,
    CreatedOnUtc DATETIME2(3) NOT NULL CONSTRAINT DF_Orders_Created DEFAULT SYSUTCDATETIME()
);
GO

-- 4. Create Outbox Table for Transactional Messaging
IF OBJECT_ID('dbo.OutboxMessages', 'U') IS NOT NULL
    DROP TABLE dbo.OutboxMessages;
GO

CREATE TABLE dbo.OutboxMessages
(
    Id UNIQUEIDENTIFIER NOT NULL CONSTRAINT PK_OutboxMessages PRIMARY KEY CLUSTERED,
    OccurredOnUtc DATETIME2(3) NOT NULL,
    EventType NVARCHAR(250) NOT NULL,
    Payload NVARCHAR(MAX) NOT NULL,
    ProcessedOnUtc DATETIME2(3) NULL,
    ErrorMessage NVARCHAR(MAX) NULL
);
GO

-- Index for Background Outbox Polling: Filtered Index on Unprocessed Messages
CREATE NONCLUSTERED INDEX NCIX_OutboxMessages_Unprocessed
ON dbo.OutboxMessages (OccurredOnUtc ASC)
WHERE ProcessedOnUtc IS NULL;
GO

-- 5. APPLY THE E-S-R RULE NON-CLUSTERED INDEX ON ORDERS
-- Target Query:
-- SELECT CustomerId, TotalAmount, OrderDateUtc
-- FROM Orders
-- WHERE CustomerId = @CustomerId AND OrderStatus = 'SHIPPED'
-- ORDER BY OrderDateUtc DESC;

CREATE NONCLUSTERED INDEX NCIX_Orders_Customer_Status_Date_Covering
ON dbo.Orders (
    CustomerId ASC,       -- 1. Equality Predicate 1
    OrderStatus ASC,      -- 2. Equality Predicate 2
    OrderDateUtc DESC     -- 3. Sort Order (Eliminates Sort Operator!)
)
INCLUDE (
    TotalAmount           -- 4. Covers SELECT columns (Zero Bookmark Lookups!)
);
GO

PRINT 'Database, Schema, RCSI, and E-S-R Indexes initialized successfully.';
