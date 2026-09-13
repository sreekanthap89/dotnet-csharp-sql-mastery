# Enterprise Mastery Companion Code Samples

Welcome to the companion production-grade code laboratory for the [.NET, C# & SQL Master Reference Guide](../README.md).

This solution is designed as a runnable, testable, and benchmarkable multi-project suite implementing the architectural patterns taught across the 31 documentation modules.

---

## 📁 Projects Structure

```
samples/
│
├── EnterpriseMastery.slnx          # Modern .NET Solution connecting all projects
│
├── src/
│   ├── Enterprise.Core/            # Domain Entities, Result Pattern, Interfaces, Outbox Message
│   └── Enterprise.WebApi/          # ASP.NET Core 8 Web API, Polly v8, Middleware, Minimal APIs
│
├── tests/
│   └── Enterprise.Tests/           # xUnit, FluentAssertions, WebApplicationFactory Integration Tests
│
├── benchmarks/
│   └── Enterprise.Benchmarks/      # BenchmarkDotNet Suite: Span vs Substring, FrozenDictionary vs Dictionary
│
└── database/
    ├── docker-compose.yml          # Instant local SQL Server 2022 + Redis cluster
    ├── 01_schema_and_rcsi.sql      # Tables, E-S-R Non-Clustered Indexes & RCSI Enablement
    └── 02_deadlock_simulation.sql  # Deadlock reproduction and Extended Events query
```

---

## 🚀 How to Run the Projects

### 1. Build the Entire Solution
```bash
dotnet build samples/EnterpriseMastery.slnx
```

### 2. Run Automated Unit & Integration Tests
```bash
dotnet test samples/EnterpriseMastery.slnx
```
- Validates Railway-oriented `Result<T>` pattern.
- Enforces `Order` domain entity invariants.
- Executes full HTTP API requests against `WebApplicationFactory<Program>` testing correlation IDs, Polly resilience, and HTTP status codes.

### 3. Run the ASP.NET Core Web API
```bash
dotnet run --project samples/src/Enterprise.WebApi/Enterprise.WebApi.csproj
```
- Navigate to Swagger UI: `http://localhost:5000/swagger` or `https://localhost:5001/swagger`
- Test `POST /api/v1/orders` to observe the **Transactional Outbox Pattern** and **Polly Resilience Handlers** in action.

### 4. Run BenchmarkDotNet Performance Profiling
```bash
# Benchmarks must be executed in Release mode for accurate JIT optimization!
dotnet run -c Release --project samples/benchmarks/Enterprise.Benchmarks/Enterprise.Benchmarks.csproj
```
- **StringAllocationBenchmarks**: Compares classic string allocation against zero-allocation `Span<char>` and `string.Create()`.
- **CollectionLookupBenchmarks**: Measures `FrozenDictionary` vs standard `Dictionary` vs `ImmutableDictionary` in .NET 8.

### 5. Start Local SQL Server & Redis (Docker)
```bash
cd samples/database
docker-compose up -d
```
Connect via SQL Server Management Studio (SSMS) or Azure Data Studio:
- **Server**: `localhost,1433`
- **Username**: `sa`
- **Password**: `SecurePassword123!`
- Execute `01_schema_and_rcsi.sql` to initialize schemas with Read Committed Snapshot Isolation and E-S-R indexing.
