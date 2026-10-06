# Section 18: ASP.NET Core Web API Fundamentals


> **Curriculum Navigation:**  
> ⏪ [Previous: Section 17 – ADO.NET & Entity Framework Core Architecture](./170_ado_dotnet_and_entity_framework.md) | 🏠 [Master Index](./README.md) | ⏩ [Next: Section 19 – Web API Security, Authentication & JWT Deep-Dive](./190_web_api_authentication_and_jwt.md)

---


### Q182. What is Web API? What is the purpose of Web API?

#### 1. Executive Summary & Core Concept
- **ASP.NET Core Web API** is an enterprise HTTP service framework designed to build **lightweight, stateless, RESTful services** consumed by a broad range of clients (Single Page Applications like React/Angular, native mobile apps for iOS/Android, IoT devices, and external microservices).
- **Core Purpose**: Exposes backend business domain data and operations over standard **HTTP protocols and verbs** using standardized data formats (principally **JSON** or XML), decoupling frontend presentation layers completely from backend data and business logic.

#### 2. Deep-Dive Architecture & Runtime Internals
- **HTTP Request Pipeline**:
  1. An HTTP request enters the web server via **Kestrel**.
  2. The request passes through the **Middleware Pipeline** (Authentication, Authorization, CORS, Routing).
  3. The **Endpoint Routing Engine** matches the URL and HTTP verb to an Action Method.
  4. The **Model Binder** extracts parameters from the Route, QueryString, Headers, and HTTP Body (via `System.Text.Json`).
  5. The Action executes, returns an `IActionResult` or strongly typed object, and the **Output Formatter** serializes the response into the negotiated content type (e.g., `application/json`).

```
ASP.NET Core Web API Pipeline:
HTTP Request ──▶ [ Kestrel Web Server ]
                       │
                       ▼
            [ Middleware Pipeline ] (Auth, CORS, Logging)
                       │
                       ▼
            [ Endpoint Routing ] ──▶ Model Binding & Validation
                       │
                       ▼
            [ API Controller Action ] ──▶ Returns Domain Object
                       │
                       ▼
            [ JSON Output Formatter ] ──▶ HTTP 200 OK + JSON Payload
```

#### 3. Production-Ready Code Implementation
```csharp
using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;

namespace EnterpriseArchitecture.WebApis;

public record ProductDto(int Id, string Sku, decimal Price);
public record CreateProductRequest(string Sku, decimal Price);

[ApiController]
[Route("api/v1/products")]
[Produces("application/json")]
public sealed class ProductsController : ControllerBase
{
    // GET api/v1/products
    [HttpGet]
    [ProducesResponseType(typeof(IEnumerable<ProductDto>), StatusCodes.Status200OK)]
    public async Task<IActionResult> GetAllProducts()
    {
        await Task.Yield(); // Simulating database fetch
        var products = new List<ProductDto>
        {
            new(1, "SKU-CLOUD-01", 99.99m),
            new(2, "SKU-CLOUD-02", 149.99m)
        };
        return Ok(products); // HTTP 200 OK with JSON array
    }

    // POST api/v1/products
    [HttpPost]
    [ProducesResponseType(typeof(ProductDto), StatusCodes.Status201Created)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    public async Task<IActionResult> CreateProduct([FromBody] CreateProductRequest request)
    {
        if (request.Price <= 0)
            return BadRequest(new ProblemDetails { Title = "Invalid Price", Detail = "Price must be strictly positive." });

        await Task.Yield();
        var created = new ProductDto(100, request.Sku, request.Price);

        // Standard REST: Returns HTTP 201 Created + Location Header pointing to new resource!
        return CreatedAtAction(nameof(GetAllProducts), new { id = created.Id }, created);
    }
}
```

#### 4. Line-by-Line Code Walkthrough
- `[ApiController]`: Enables automatic model validation (returning automatic HTTP 400 Bad Request if validation fails) and infers parameter binding sources.
- `[Route("api/v1/products")]`: Attribute routing defining the canonical REST resource URI.
- `CreatedAtAction(...)`: Conforms to HTTP specifications by emitting an HTTP 201 Created status alongside a `Location` header pointing to the newly created entity.

#### 5. Real-World Enterprise Use Case & Application
The architectural backbone for modern SaaS platforms: A single ASP.NET Core Web API cluster services web applications (Next.js/React), native mobile apps (Flutter/Swift), and third-party partner integration webhooks.

#### 6. Common Pitfalls, Memory Traps & Anti-Patterns
- Returning raw internal database entities (EF Core entities) from API endpoints. This causes circular reference serialization crashes, leaks internal database schema details, and invites **Over-Posting Security Vulnerabilities**. Always project to explicit **Data Transfer Objects (DTOs)**.

#### 7. Senior / Architect Interview Follow-ups
- **Interviewer**: *"What are Minimal APIs introduced in .NET 6/7/8, and how do they compare architecturally to Controller-based Web APIs?"*
- **Expert Answer**: Minimal APIs (`app.MapGet("/api/products", () => ...);`) bypass the heavy Controller reflection, action invoker, and model metadata infrastructure. They map HTTP endpoints directly to lightweight delegates, reducing memory allocations and dramatically cutting startup time. They are ideal for high-performance microservices, serverless AWS Lambda / Azure Functions, and low-latency APIs.

---

### Q183. What are Web API advantages over WCF and web services?

#### 1. Executive Summary & Core Concept
- **ASMX Web Services (Legacy .NET 1.0/2.0)**: XML and SOAP only, tied strictly to IIS, obsolete.
- **WCF (Windows Communication Foundation - .NET 3.0/4.x)**: Massive, heavyweight enterprise framework supporting multiple protocols (TCP, Named Pipes, MSMQ, SOAP). Extremely complex XML configuration files (`web.config`), high overhead, and non-cross-platform.
- **ASP.NET Core Web API**:
  1. **Lightweight & High-Performance**: Built directly on modern Kestrel; millions of requests per second.
  2. **Cross-Platform**: Runs natively on Linux, macOS, Docker containers, and Windows.
  3. **First-Class HTTP & REST Support**: Embraces HTTP status codes, headers, and verbs natively.
  4. **Lightweight Formats**: Built natively around JSON, Protobuf, and binary buffers rather than verbose XML SOAP envelopes.
  5. **Modern Developer Experience**: Zero XML config; configured via clean C# code and Dependency Injection.

#### 2. Deep-Dive Architecture & Runtime Internals
Wire Format Comparison:
```
WCF SOAP Envelope (Bloated XML Payload):
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
  <s:Header><wsa:Action>http://tempuri.org/GetPrice</wsa:Action></s:Header>
  <s:Body><GetPriceResponse><Price>99.99</Price></GetPriceResponse></s:Body>
</s:Envelope>
(Heavy XML parsing overhead, ~350 bytes for a single number!)

Web API JSON Payload (Clean, Compact, Fast):
{"price": 99.99}
(Processed in nanoseconds via UTF-8 Utf8JsonReader, ~16 bytes!)
```

#### 3. Production-Ready Code Implementation
Contrast WCF contract boilerplate with Modern Web API:

```csharp
// MODERN ASP.NET CORE WEB API (Clean, minimal, high-throughput)
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Http;

var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

// A complete, production-ready microservice endpoint in 1 line:
app.MapGet("/api/quotes/{ticker}", (string ticker) => 
    Results.Ok(new { Ticker = ticker.ToUpperInvariant(), Price = 142.50m, Timestamp = System.DateTime.UtcNow }));

app.Run();
```

#### 4. Line-by-Line Code Walkthrough
- Demonstrates how 100 lines of WCF Service Contracts, Operation Contracts, Channel Factories, and XML bindings are replaced by concise, high-performance C# Minimal APIs.

#### 5. Real-World Enterprise Use Case & Application
Migrating on-premises legacy WCF services to Kubernetes cloud containers running .NET 8 Web APIs, reducing server resource costs by 70%.

#### 6. Common Pitfalls, Memory Traps & Anti-Patterns
- Attempting to simulate SOAP RPC inside a Web API (e.g., creating endpoints like `POST /api/DoEverythingService`). Embrace standard REST resource-based design.

#### 7. Senior / Architect Interview Follow-ups
- **Interviewer**: *"If a system requires ultra-low-latency inter-service binary communication that WCF NetTcpBinding previously provided, what is the modern .NET replacement?"*
- **Expert Answer**: **gRPC (Google Remote Procedure Call)** over HTTP/2 and HTTP/3. gRPC in modern .NET is officially supported, cross-platform, contract-first (using Protocol Buffers `.proto`), and delivers up to **10x higher throughput** than legacy WCF NetTcpBinding with compact binary serialization and bi-directional streaming.

---

### Q184. What are HTTP verbs or HTTP methods?

#### 1. Executive Summary & Core Concept
- **HTTP Verbs (Methods)** indicate the **desired action to be performed on a specified resource** identified by a URI.
- The 5 core HTTP verbs in RESTful Web APIs:
  1. **`GET`**: Retrieve a resource representation. **Safe and Idempotent**. No request body.
  2. **`POST`**: Create a new resource or execute an operation. **Neither Safe nor Idempotent**.
  3. **`PUT`**: Replace an existing resource entirely (full update). **Idempotent**.
  4. **`PATCH`**: Partially update specific fields of an existing resource. **Not inherently idempotent**.
  5. **`DELETE`**: Remove a resource. **Idempotent**.

#### 2. Deep-Dive Architecture & Runtime Internals
- **Safe Operations**: An HTTP method is **Safe** if it does **not alter server state** (read-only; e.g., `GET`, `HEAD`). Caching proxies and web browsers can freely pre-fetch and cache safe requests.
- **Idempotent Operations**: An HTTP method is **Idempotent** if **making multiple identical requests produces the exact same server state as making a single request**:
  - `PUT /users/5` with `{ name: "Bob" }`: Calling it 1 time or 100 times leaves the user's name as "Bob" (Idempotent).
  - `POST /orders`: Calling it 5 times creates 5 distinct orders (Non-Idempotent; charges credit card 5 times!).
  - `DELETE /users/5`: Calling it once deletes the user (HTTP 204); calling it again finds nothing (HTTP 404), but the server state remains "user 5 does not exist" (Idempotent).

```
HTTP Verbs Semantic Matrix:
Verb   | Purpose            | Safe? | Idempotent? | Success Status
───────┼────────────────────┼───────┼─────────────┼────────────────────────────
GET    | Read / Query       |  YES  |     YES     | 200 OK
POST   | Create / Action    |  NO   |     NO      | 201 Created / 200 OK
PUT    | Full Replace       |  NO   |     YES     | 200 OK / 204 No Content
PATCH  | Partial Update     |  NO   |     NO      | 200 OK / 204 No Content
DELETE | Remove Resource    |  NO   |     YES     | 200 OK / 204 No Content
```

#### 3. Production-Ready Code Implementation
```csharp
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;

namespace EnterpriseArchitecture.HttpVerbs;

[ApiController]
[Route("api/users")]
public sealed class UsersController : ControllerBase
{
    // 1. GET (Safe & Idempotent)
    [HttpGet("{id:int}")]
    public IActionResult GetUser(int id) => Ok(new { Id = id, Name = "Alice" });

    // 2. POST (Neither Safe nor Idempotent - Creates resource)
    [HttpPost]
    public IActionResult CreateUser([FromBody] string name) => 
        Created($"/api/users/1", new { Id = 1, Name = name });

    // 3. PUT (Idempotent - Replaces entire entity)
    [HttpPut("{id:int}")]
    public IActionResult ReplaceUser(int id, [FromBody] string newName) => 
        Ok(new { Id = id, Name = newName });

    // 4. PATCH (Non-idempotent partial modification)
    [HttpPatch("{id:int}/email")]
    public IActionResult UpdateEmail(int id, [FromBody] string newEmail) => 
        NoContent(); // HTTP 204 No Content

    // 5. DELETE (Idempotent - Removes entity)
    [HttpDelete("{id:int}")]
    public IActionResult DeleteUser(int id) => 
        NoContent();
}
```

#### 4. Line-by-Line Code Walkthrough
- `[HttpGet("{id:int}")]`: Attribute routing constraint ensuring `id` is an integer.
- `NoContent()`: Returns standard HTTP 204 indicating the operation succeeded and there is no payload body to return.

#### 5. Real-World Enterprise Use Case & Application
Payment API integration: Payment gateways use `POST /charges` paired with **Idempotency Keys** (`Idempotency-Key: UUID`) passed in headers to prevent duplicate credit card billing during network retries.

#### 6. Common Pitfalls, Memory Traps & Anti-Patterns
- Using `GET` to mutate data (`GET /users/delete?id=5`). Web crawlers (like Googlebot) following links will automatically trigger deletions!

#### 7. Senior / Architect Interview Follow-ups
- **Interviewer**: *"How does JSON Patch (`RFC 6902`) work in ASP.NET Core for `PATCH` requests?"*
- **Expert Answer**: RFC 6902 defines a JSON structure describing an array of mutation operations (`add`, `remove`, `replace`, `copy`, `move`, `test`). In ASP.NET Core, `JsonPatchDocument<T>` applies these operations to a loaded entity (`patchDoc.ApplyTo(customer)`). Modern architects often prefer simplified DTOs with nullable fields over full JSON Patch to reduce library complexity.

---

### Q185. What is the difference between REST API and Web API?

#### 1. Executive Summary & Core Concept
- **Web API**: A general, broad term for **any application programming interface exposed over HTTP**. It is the implementation framework/technology (e.g., ASP.NET Core Web API). It can use any architectural style: REST, RPC, GraphQL, or ad-hoc custom endpoints.
- **REST API (Representational State Transfer)**: A **specific software architectural style** governed by **Dr. Roy Fielding's 6 constraints (2000)**. A REST API is a specific *type* of Web API that adheres to REST principles (statelessness, resource-based URIs, standard HTTP verbs, and hypermedia).
- **The Core Distinction**: **All REST APIs are Web APIs, but NOT all Web APIs are REST APIs.**

#### 2. Deep-Dive Architecture & Runtime Internals
| Characteristic | Generic Web API (RPC Style) | True RESTful API |
| :--- | :--- | :--- |
| **URI Design** | Action/Verb-oriented (`/api/CreateUser`, `/api/DeleteUser`) | **Noun/Resource-oriented** (`/api/users`, `/api/users/5`) |
| **HTTP Verbs** | Frequently abuses `POST` for everything | Strictly adheres to `GET`, `POST`, `PUT`, `DELETE` |
| **State** | Can be stateful (sessions) or stateless | **Strictly Stateless** |
| **Coupling** | High: Client must know exact action URLs | Low: Discovers resources via links (HATEOAS) |

```
Architectural Comparison:
RPC-Style Web API:     POST /api/Orders/CancelOrder?id=5 (Action verb in URL)
RESTful Web API:       DELETE /api/orders/5              (Standard HTTP verb on Noun URI)
```

#### 3. Production-Ready Code Implementation
```csharp
using Microsoft.AspNetCore.Mvc;

namespace EnterpriseArchitecture.RestVsRpc;

// 1. NON-RESTFUL RPC-STYLE WEB API (Common Anti-Pattern)
[ApiController]
[Route("api/rpc/users")]
public class RpcUserController : ControllerBase
{
    [HttpPost("saveUser")] // Action verb in URI!
    public IActionResult SaveUser() => Ok();

    [HttpPost("deleteUserById")] // Post used for deletion!
    public IActionResult DeleteUser(int id) => Ok();
}

// 2. TRUE RESTFUL API (Standard Resource Modeling)
[ApiController]
[Route("api/rest/users")]
public class RestfulUserController : ControllerBase
{
    [HttpPost] // POST creates new user in /users collection
    public IActionResult Create() => Created();

    [HttpDelete("{id:int}")] // DELETE removes resource identified by URI
    public IActionResult Delete(int id) => NoContent();
}
```

#### 4. Line-by-Line Code Walkthrough
- Illustrates how REST replaces action verbs in URLs with standard HTTP verbs operating on resource nouns.

#### 5. Real-World Enterprise Use Case & Application
Public API ecosystems (Stripe, GitHub, Twilio): External developer adoption requires predictable, standardized REST conventions rather than proprietary custom RPC URLs.

#### 6. Common Pitfalls, Memory Traps & Anti-Patterns
- Using plural and singular nouns inconsistently (`/api/user` vs `/api/orders`). Standardize on **plural nouns** (`/api/users`, `/api/orders`).

#### 7. Senior / Architect Interview Follow-ups
- **Interviewer**: *"What is the Richardson Maturity Model, and what are its 4 levels?"*
- **Expert Answer**: Leonard Richardson defined a model measuring REST compliance:
  - **Level 0 (The Swamp of POX)**: Uses HTTP purely as a transport tunnel for RPC (e.g., SOAP or XML-RPC; single URI, single `POST` verb).
  - **Level 1 (Resources)**: Introduces distinct URIs for individual resources (`/orders/1`).
  - **Level 2 (HTTP Verbs)**: Uses standard HTTP verbs (`GET`, `POST`, `PUT`, `DELETE`) and HTTP status codes (200, 201, 404). **(Where 95% of enterprise "REST" APIs sit)**.
  - **Level 3 (HATEOAS)**: Hypermedia controls; responses include dynamic links guiding the client on valid next actions.

---

### Q186. What are REST guidelines? What is the difference between Rest and Restful?

#### 1. Executive Summary & Core Concept
- **REST (Representational State Transfer)**: The architectural paradigm defined by Dr. Roy Fielding in his 2000 doctoral dissertation.
- **RESTful**: An adjective describing an API or system that **strictly adheres to and complies with the 6 REST architectural constraints**.
- **The 6 Core REST Constraints**:
  1. **Client-Server Architecture**: Separation of user interface concerns from data storage concerns.
  2. **Statelessness**: Every request from client to server must contain all information necessary to understand and process the request. No client context stored on server.
  3. **Cacheability**: Responses must implicitly or explicitly define themselves as cacheable or non-cacheable (`Cache-Control` headers).
  4. **Uniform Interface**: The defining constraint: Identification of resources, manipulation of resources through representations, self-descriptive messages, and HATEOAS.
  5. **Layered System**: A client cannot tell whether it is connected directly to the end server or an intermediate proxy, load balancer, or CDN.
  6. **Code on Demand (Optional)**: Server can temporarily extend client functionality by transferring executable code (e.g., JavaScript).

#### 2. Deep-Dive Architecture & Runtime Internals
- **Statelessness Under the Hood**:
  - The server stores **zero session state** in memory (`Session["User"]` is forbidden in pure REST).
  - Client state is transferred via **cryptographic bearer tokens (JWTs)** inside the HTTP `Authorization` header on every single request.
  - This allows the cloud infrastructure to place a stateless load balancer in front of 100 API servers; any request can be handled by any server without session replication!

```
Stateless Cloud Scalability:
Client ──(Sends JWT in Header)──▶ [ Load Balancer ]
                                          │
                   ┌──────────────────────┼──────────────────────┐
                   ▼                      ▼                      ▼
             [ API Node 1 ]         [ API Node 2 ]         [ API Node 3 ]
             (Zero Session Memory! Validates JWT Cryptographically & Executes!)
```

#### 3. Production-Ready Code Implementation
Demonstrating HATEOAS (Level 3 REST) in ASP.NET Core:

```csharp
using System.Collections.Generic;
using Microsoft.AspNetCore.Mvc;

namespace EnterpriseArchitecture.RestGuidelines;

public record LinkDto(string Href, string Rel, string Method);
public record AccountModel(int AccountId, decimal Balance, List<LinkDto> Links);

[ApiController]
[Route("api/accounts")]
public sealed class AccountsController : ControllerBase
{
    [HttpGet("{id:int}")]
    public IActionResult GetAccount(int id)
    {
        var account = new AccountModel(id, 1500.00m, new List<LinkDto>
        {
            // HATEOAS Links instructing client on valid next actions!
            new($"/api/accounts/{id}", "self", "GET"),
            new($"/api/accounts/{id}/deposits", "deposit", "POST"),
            new($"/api/accounts/{id}/withdrawals", "withdraw", "POST")
        });

        return Ok(account);
    }
}
```

#### 4. Line-by-Line Code Walkthrough
- `Links`: Implements HATEOAS (Hypermedia As The Engine Of Application State), guiding frontend clients dynamically.

#### 5. Real-World Enterprise Use Case & Application
Building globally scalable cloud APIs on AWS or Azure: Statelessness ensures that auto-scaling groups can spin up 50 new container instances during traffic surges without state migration.

#### 6. Common Pitfalls, Memory Traps & Anti-Patterns
- Storing state in `HttpContext.Session` inside a Web API, breaking horizontal scaling across Kubernetes pods.

#### 7. Senior / Architect Interview Follow-ups
- **Interviewer**: *"Why do most enterprise production APIs stop at Richardson Maturity Level 2 and avoid Level 3 (HATEOAS)?"*
- **Expert Answer**: While HATEOAS is academically elegant, in practical enterprise engineering it introduces significant payload bloat (adding link arrays to millions of JSON records), increases bandwidth costs, and provides minimal real-world value when frontend teams already use strongly-typed TypeScript clients generated from OpenAPI / Swagger specifications.

---

### Q187. Is it possible to use WCF as Restful services?

#### 1. Executive Summary & Core Concept
- **YES.** It was possible in legacy .NET Framework to configure WCF to expose RESTful services.
- **Mechanism**:
  - Implemented using the **`webHttpBinding`** and the **`[WebGet]`** or **`[WebInvoke]`** attributes from `System.ServiceModel.Web`.
- **Modern Architectural Reality**: While technically possible in legacy .NET 4.x, **WCF REST is completely obsolete and deprecated**. Modern systems build REST APIs exclusively with **ASP.NET Core Web API**.

#### 2. Deep-Dive Architecture & Runtime Internals
- In legacy WCF:
  - `[WebGet(UriTemplate = "products/{id}", ResponseFormat = WebMessageFormat.Json)]`: Mapped HTTP GET requests to service contracts.
  - `[WebInvoke(Method = "POST", UriTemplate = "products")]`: Mapped HTTP POST requests.
- WCF routed requests through its legacy channel dispatcher stack, which was complex, heavily configured via XML, and significantly slower than modern ASP.NET Core pipelines.

#### 3. Production-Ready Code Implementation
Legacy WCF REST Contract (Historical Reference):

```csharp
using System.ServiceModel;
using System.ServiceModel.Web;

namespace EnterpriseArchitecture.LegacyWcfRest;

[ServiceContract]
public interface ILegacyProductService
{
    // WCF REST GET ANNOTATION
    [OperationContract]
    [WebGet(UriTemplate = "products/{id}", ResponseFormat = WebMessageFormat.Json)]
    string GetProduct(string id);

    // WCF REST POST ANNOTATION
    [OperationContract]
    [WebInvoke(Method = "POST", UriTemplate = "products", RequestFormat = WebMessageFormat.Json)]
    void CreateProduct(string payload);
}
```

#### 4. Line-by-Line Code Walkthrough
- `[WebGet]`: Binds method to HTTP GET.
- `[WebInvoke]`: Binds method to other HTTP verbs.

#### 5. Real-World Enterprise Use Case & Application
Enterprise migration projects: Recognizing legacy WCF REST endpoints during system audits and rewriting them as ASP.NET Core Controllers.

#### 6. Common Pitfalls, Memory Traps & Anti-Patterns
- Attempting to port WCF REST to Linux containers. CoreWCF supports SOAP, but modern REST should always be authored in ASP.NET Core.

#### 7. Senior / Architect Interview Follow-ups
- **Interviewer**: *"What is CoreWCF, and does it support WCF REST in modern .NET 8?"*
- **Expert Answer**: **CoreWCF** is an open-source project supported by Microsoft and AWS to facilitate porting legacy WCF services to .NET 6/8. It primarily supports SOAP bindings (`BasicHttpBinding`, `NetTcpBinding`) for legacy enterprise protocols. For REST endpoints, Microsoft explicitly recommends migrating directly to standard ASP.NET Core Minimal APIs or Controllers.

---

### Q188. How to consume Web API from a .NET MVC application?

#### 1. Executive Summary & Core Concept
- In modern .NET, external Web APIs are consumed using **`HttpClient` managed via `IHttpClientFactory`**.
- **The Core Rule**: Never instantiate `HttpClient` manually using `new HttpClient()` inside controllers!
- **Enterprise Standard**: Use **Typed HttpClients** registered in Dependency Injection, paired with **Polly** for retry policies, circuit breakers, and exponential backoff.

#### 2. Deep-Dive Architecture & Runtime Internals
- **The Socket Exhaustion Disaster of `new HttpClient()`**:
  - Even though `HttpClient` implements `IDisposable`, disposing it does **NOT** immediately close the underlying physical OS TCP socket!
  - The OS leaves the socket in the **`TIME_WAIT`** state for 240 seconds to ensure stray packets are drained.
  - If a web application instantiates `new HttpClient()` on every request under heavy load, all available ephemeral OS sockets are exhausted, crashing the server with `System.Net.Sockets.SocketException: Only one usage of each socket address is normally permitted`.
- **`IHttpClientFactory` Architecture**:
  - Pools and manages the lifecycle of the underlying **`HttpMessageHandler`** instances.
  - Reuses physical TCP sockets across requests, eliminating socket exhaustion while automatically refreshing DNS changes every 2 minutes.

```
Socket Exhaustion vs IHttpClientFactory:
Anti-Pattern: new HttpClient() per request ──▶ 10,000 Sockets trapped in TIME_WAIT! (Server Crashes!)
Enterprise:   IHttpClientFactory ──▶ Pools underlying SocketsHttpHandler! (Reuses TCP connections!)
```

#### 3. Production-Ready Code Implementation
The following code demonstrates a resilient, typed `HttpClient` in modern .NET:

```csharp
using System;
using System.Net.Http;
using System.Net.Http.Json;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.DependencyInjection;

namespace EnterpriseArchitecture.ApiConsumption;

public record OrderSummary(int OrderId, decimal Amount);

// 1. TYPED HTTP CLIENT SERVICE
public sealed class OrderApiClient
{
    private readonly HttpClient _httpClient;

    // Injected with pre-configured pooled HttpClient
    public OrderApiClient(HttpClient httpClient)
    {
        _httpClient = httpClient;
    }

    public async Task<OrderSummary?> FetchOrderAsync(int orderId, CancellationToken ct = default)
    {
        // High-performance System.Text.Json streaming deserialization directly from network socket!
        return await _httpClient.GetFromJsonAsync<OrderSummary>($"api/v1/orders/{orderId}", ct);
    }
}

// 2. REGISTRATION IN PROGRAM.CS (With BaseAddress and Resilience)
public static class ServiceRegistration
{
    public static void ConfigureApiClient(IServiceCollection services)
    {
        // Registers typed client with IHttpClientFactory lifecycle management
        services.AddHttpClient<OrderApiClient>(client =>
        {
            client.BaseAddress = new Uri("https://orders-microservice.corp.internal/");
            client.Timeout = TimeSpan.FromSeconds(10);
            client.DefaultRequestHeaders.Add("Accept", "application/json");
        });
    }
}
```

#### 4. Line-by-Line Code Walkthrough
- `GetFromJsonAsync<T>(...)`: Reads directly from the HTTP response stream without allocating intermediate string objects.
- `services.AddHttpClient<OrderApiClient>(...)`: Automatically configures underlying pooled socket handlers.

#### 5. Real-World Enterprise Use Case & Application
Microservice mesh communication: An API Gateway or MVC frontend calling downstream microservices with circuit-breaker protection.

#### 6. Common Pitfalls, Memory Traps & Anti-Patterns
- Using `client.GetStringAsync()` followed by `JsonSerializer.Deserialize()`. This allocates a large string in memory; always deserialize directly from the stream using `GetFromJsonAsync()`.

#### 7. Senior / Architect Interview Follow-ups
- **Interviewer**: *"How does `IHttpClientFactory` handle DNS changes for long-lived connections?"*
- **Expert Answer**: A naive static `HttpClient` holds open TCP sockets indefinitely, never detecting DNS updates when an upstream service changes IP addresses. `IHttpClientFactory` solves this by giving underlying `HttpMessageHandler` instances a default lifetime of **2 minutes**. When expired, the handler is marked as deactive, allowing existing requests to drain, while new requests spawn a fresh handler that resolves DNS anew, completely eliminating stale DNS bugs!

---

### Q189. What is the difference between Web API and MVC Controller?

#### 1. Executive Summary & Core Concept
- **MVC Controller (`Controller`)**:
  - Inherits from `Microsoft.AspNetCore.Mvc.Controller`.
  - Primary Purpose: **Renders HTML User Interfaces (Views)**.
  - Returns: **`ViewResult`**, generating HTML via Razor view engines (`.cshtml`).
  - Contains view helper methods: `View()`, `PartialView()`, `ViewBag`, `ViewData`.
- **Web API Controller (`ControllerBase`)**:
  - Inherits from `Microsoft.AspNetCore.Mvc.ControllerBase`.
  - Primary Purpose: **Returns raw structured data (JSON, Protobuf, XML)**.
  - Returns: **`IActionResult`**, `ActionResult<T>`, or raw DTO objects.
  - Omits HTML view engine dependencies, making it lighter and faster.

#### 2. Deep-Dive Architecture & Runtime Internals
| Dimension | MVC Controller | Web API Controller |
| :--- | :--- | :--- |
| **Base Class** | `Controller` (inherits from `ControllerBase`) | **`ControllerBase`** |
| **Primary Output** | HTML Web Pages (Server-Side Rendering) | **Raw Data (JSON, XML)** |
| **Decoration** | None or `[Route]` | **`[ApiController]`** |
| **Model Validation** | Manual check: `if (!ModelState.IsValid)` | **Automatic**: Returns HTTP 400 Bad Request if invalid |
| **View Engine Support**| Full support for Razor, `ViewBag`, `ViewData` | View engine dependencies stripped |

```
Inheritance Hierarchy in ASP.NET Core:
ControllerBase (Contains: Ok(), BadRequest(), NotFound(), File(), Unauthorized())
      │
      ├──▶ [ Web API Controllers inherit HERE! ] (Lightweight, pure data)
      │
      ▼
Controller (Adds: View(), PartialView(), ViewComponent(), ViewBag, TempData)
      │
      └──▶ [ MVC Controllers inherit HERE! ] (Renders HTML UI)
```

#### 3. Production-Ready Code Implementation
```csharp
using Microsoft.AspNetCore.Mvc;

namespace EnterpriseArchitecture.MvcVsApi;

// 1. MVC CONTROLLER: Serves HTML Pages
public sealed class CustomerMvcController : Controller
{
    // Returns HTML View
    public IActionResult Index()
    {
        ViewBag.Title = "Customer Management";
        return View(); // Searches for Views/CustomerMvc/Index.cshtml
    }
}

// 2. WEB API CONTROLLER: Serves Raw JSON Data
[ApiController]
[Route("api/customers")]
public sealed class CustomerApiController : ControllerBase
{
    // Returns Raw JSON Data
    [HttpGet]
    public IActionResult GetCustomers()
    {
        var data = new[] { new { Id = 1, Code = "CUST_01" } };
        return Ok(data); // Serializes to application/json
    }
}
```

#### 4. Line-by-Line Code Walkthrough
- `class CustomerApiController : ControllerBase`: Inherits only HTTP status helper methods, skipping unused view engines.

#### 5. Real-World Enterprise Use Case & Application
Unified enterprise applications: Using MVC controllers to render public marketing pages and server-rendered dashboards, while exposing Web API controllers for mobile app consumption.

#### 6. Common Pitfalls, Memory Traps & Anti-Patterns
- Inheriting Web API controllers from `Controller` instead of `ControllerBase`. This drags in unused view engine infrastructure.

#### 7. Senior / Architect Interview Follow-ups
- **Interviewer**: *"What specific behaviors does the `[ApiController]` attribute enable when applied to a Web API controller?"*
- **Expert Answer**: The `[ApiController]` attribute enables 5 critical runtime behaviors:
  1. **Automatic HTTP 400 Responses**: If `ModelState` fails validation, the action is bypassed, and a standard RFC 7807 `ProblemDetails` 400 Bad Request is returned automatically.
  2. **Binding Source Parameter Inference**: Automatically infers `[FromBody]` for complex types, `[FromRoute]` for route parameters, and `[FromQuery]` for primitives.
  3. **Multipart/form-data Inference**: Automatically infers `[FromForm]` for `IFormFile` parameters.
  4. **Attribute Routing Requirement**: Mandates that all actions use attribute routing.
  5. **Problem Details Formatting for Error Status Codes**: Standardizes all client error responses.

---

### Q190. What is the difference between PUT and PATCH (and POST) in REST APIs?

#### 1. Executive Summary & Core Concept
- **`POST` (Resource Creation / Processing)**: **Non-Idempotent**. Submits an entity to the specified resource, usually causing a state change or side-effects on the server. Executing 10 identical POST requests creates 10 duplicate resources.
- **`PUT` (Complete Replacement / Upsert)**: **Idempotent**. Replaces the entire target resource with the uploaded representation. If a client omits fields in the PUT payload, those fields are overwritten with null/defaults on the server. Executing 10 identical PUT requests leaves the server in the exact same state as 1 request.
- **`PATCH` (Partial Modification)**: **Non-Idempotent by specification (though often implemented idempotently)**. Modifies only the specific fields described in the payload without replacing the entire resource. Implemented via **RFC 7396 (JSON Merge Patch)** or **RFC 6902 (JSON Patch operations)**.

| HTTP Verb | Semantics | Idempotent? | Safe? (Read-Only) | Payload Expectation | Response Code on Create | Response Code on Update |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **POST** | Create child resource / Trigger workflow | ❌ No | ❌ No | New entity representation | `201 Created` (`Location` header) | N/A |
| **PUT** | Replace entire existing resource / Upsert | ✅ **Yes** | ❌ No | **Complete** entity representation | `201 Created` | `200 OK` or `204 No Content` |
| **PATCH** | Apply delta modifications to existing resource | ⚠️ Context-dependent | ❌ No | **Delta** modifications only | N/A (Targets existing) | `200 OK` or `204 No Content` |

#### 2. Deep-Dive Architecture & Runtime Internals
```
PUT vs PATCH Architectural Impact:

Original Resource: { "id": 42, "name": "Alice", "role": "Admin", "email": "alice@corp.com" }

Client Request: { "name": "Alice Smith" }

1. Received by PUT /api/users/42:
   ──▶ The contract requires FULL replacement!
   ──▶ Result: { "id": 42, "name": "Alice Smith", "role": null, "email": null } ❌ DATA LOSS ACCIDENT!

2. Received by PATCH /api/users/42:
   ──▶ The contract requires DELTA modification!
   ──▶ Result: { "id": 42, "name": "Alice Smith", "role": "Admin", "email": "alice@corp.com" } ✅ INTENDED!
```

#### 3. Production-Ready Code Implementation
```csharp
using System;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;

namespace EnterpriseArchitecture.HttpVerbs;

public record UpdateUserProfilePutDto(string Name, string Role, string Email); // Must supply ALL fields!
public record UpdateUserEmailPatchDto(string Email); // Delta only!

[ApiController]
[Route("api/users")]
public sealed class UserController : ControllerBase
{
    private readonly IUserService _userService;

    public UserController(IUserService userService) => _userService = userService;

    // 1. POST: Non-idempotent creation
    [HttpPost]
    public async Task<IActionResult> CreateUserAsync([FromBody] CreateUserDto dto, CancellationToken ct)
    {
        var created = await _userService.CreateAsync(dto, ct);
        return CreatedAtAction(nameof(GetUserByIdAsync), new { id = created.Id }, created);
    }

    // 2. PUT: Idempotent FULL REPLACEMENT
    [HttpPut("{id:guid}")]
    public async Task<IActionResult> ReplaceUserAsync(Guid id, [FromBody] UpdateUserProfilePutDto dto, CancellationToken ct)
    {
        var updated = await _userService.ReplaceAsync(id, dto, ct);
        return updated ? NoContent() : NotFound();
    }

    // 3. PATCH: Partial update (JSON Merge Patch RFC 7396 standard)
    [HttpPatch("{id:guid}/email")]
    public async Task<IActionResult> PatchEmailAsync(Guid id, [FromBody] UpdateUserEmailPatchDto dto, CancellationToken ct)
    {
        var patched = await _userService.UpdateEmailOnlyAsync(id, dto.Email, ct);
        return patched ? NoContent() : NotFound();
    }

    [HttpGet("{id:guid}")]
    public async Task<IActionResult> GetUserByIdAsync(Guid id) => Ok();
}
```

#### 4. Line-by-Line Code Walkthrough
- `ReplaceUserAsync (PUT)`: Accepts `UpdateUserProfilePutDto` containing all mutable fields, updating the entire relational record idempotently.
- `PatchEmailAsync (PATCH)`: Accepts only `UpdateUserEmailPatchDto`, issuing a pinpoint SQL statement: `UPDATE Users SET Email = @Email WHERE Id = @Id`.

#### 5. Real-World Enterprise Use Case & Application
E-commerce account management: Changing a customer's shipping address uses `PATCH /api/customers/{id}/address` to avoid sending 50 profile fields over a mobile cellular connection and risking wiping out phone numbers or preferences.

#### 6. Common Pitfalls, Memory Traps & Anti-Patterns
- **Using PUT for Partial Updates**: When frontend engineers use PUT to send only `{ "isActive": false }`, the backend clears all other fields if mapped naively.
- **Using RFC 6902 JSON Patch with Reflection**: `JsonPatchDocument<T>` uses runtime reflection to parse `add`, `remove`, `replace` operations, which degrades throughput and introduces vulnerabilities. Prefer typed delta DTOs (RFC 7396) in high-scale systems.

#### 7. Senior / Architect Interview Follow-ups
- **Interviewer**: *"Is HTTP PATCH strictly idempotent by RFC standards?"*
- **Expert Answer**: **No, not by default.** RFC 5789 explicitly states that PATCH is **not required to be idempotent**. For example, a PATCH operation that appends an item to a list or increments a counter (`{ "op": "increment", "path": "/views" }`) produces different results on every execution. However, when PATCH is used to set specific scalar values (`{ "email": "new@domain.com" }`), it behaves idempotently in practice.

---

### Q191. Minimal APIs vs Controllers in ASP.NET Core: When to choose which?

#### 1. Executive Summary & Core Concept
- **Controller-Based APIs**: The traditional MVC pattern (introduced in ASP.NET Core 1.0). Relies on reflection to discover controllers and actions, uses MVC action filters, model binders, and `ControllerBase` inheritance. Best for large, enterprise-wide applications with complex shared filter pipelines.
- **Minimal APIs** (introduced in .NET 6, perfected in .NET 8/9): A streamlined, lightweight approach that maps route endpoints directly to lambdas or methods using `app.MapGet()`, `app.MapPost()`. Bypasses the heavy MVC pipeline, supports compile-time **Request Delegate Generators (RDG)** via Source Generators, starts up **3x faster**, and delivers **higher requests/sec with lower memory allocation**.
- **When to Choose**: Choose Minimal APIs for microservices, cloud-native serverless functions, IoT APIs, and high-performance read-heavy services. Choose Controllers when working with legacy enterprise MVC apps or when teams rely heavily on MVC action filters.

| Metric / Feature | Controller-Based APIs | Minimal APIs (.NET 8 / 9) |
| :--- | :--- | :--- |
| **Startup Overhead** | High (Scans all loaded assemblies for `[ApiController]`) | **Near Instant** (Direct routing table registration) |
| **Compilation Model** | Runtime reflection for model binding | **Compile-Time Source Generators (RDG)** (AOT-ready) |
| **Native AOT Support** | Limited (Heavy reflection breaks Native AOT) | **Full First-Class Native AOT Support** |
| **Filter Pipeline** | MVC Action Filters (`IActionFilter`, `IAsyncActionFilter`) | Endpoint Filters (`IEndpointFilter`) |
| **Memory Allocation** | ~2x higher per request (allocates `ActionContext`) | **Near-Zero Allocation** |
| **Code Structure** | Scaffolds multiple files per controller | Fluent, co-located endpoint definitions |

#### 2. Deep-Dive Architecture & Runtime Internals
```
Request Dispatch Pipeline Comparison:

1. Controller-Based Pipeline:
   HTTP Request ──▶ Kestrel ──▶ Routing ──▶ MVC Middleware ──▶ Action Discovery 
                ──▶ Model Binding (Reflection) ──▶ Action Filters ──▶ Controller Instantiation (DI)
                ──▶ Action Execution ──▶ Result Filters ──▶ JSON Serialization

2. Minimal API Pipeline:
   HTTP Request ──▶ Kestrel ──▶ Endpoint Routing ──▶ Endpoint Filter ──▶ Delegate (Source Generated) ──▶ Response!
   (Bypasses entire MVC infrastructure stack!)
```

#### 3. Production-Ready Code Implementation
```csharp
using System;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.DependencyInjection;

var builder = WebApplication.CreateBuilder(args);

// Register dependencies
builder.Services.AddSingleton<IOrderService, OrderService>();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

var app = builder.Build();

// Grouped Route Endpoint with Endpoint Filters and Typed Results
var ordersApi = app.MapGroup("/api/orders")
    .WithTags("Orders")
    .AddEndpointFilter(async (invocationContext, next) =>
    {
        // Custom Endpoint Filter (Equivalent to ActionFilter)
        var logger = invocationContext.HttpContext.RequestServices.GetRequiredService<ILogger<Program>>();
        logger.LogInformation("Validating order endpoint request...");
        return await next(invocationContext);
    });

// Map Endpoints with TypedResults for compile-time OpenAPI schema generation
ordersApi.MapGet("/{id:guid}", async (Guid id, IOrderService service, CancellationToken ct) =>
{
    var order = await service.GetByIdAsync(id, ct);
    return order is not null 
        ? Results.Ok(order) 
        : Results.NotFound();
})
.WithName("GetOrderById")
.Produces<OrderResponseDto>(StatusCodes.Status200OK)
.Produces(StatusCodes.Status404NotFound);

ordersApi.MapPost("/", async (CreateOrderRequestDto dto, IOrderService service, CancellationToken ct) =>
{
    var created = await service.CreateAsync(dto, ct);
    return Results.Created($"/api/orders/{created.Id}", created);
});

app.Run();

public interface IOrderService
{
    Task<OrderResponseDto?> GetByIdAsync(Guid id, CancellationToken ct);
    Task<OrderResponseDto> CreateAsync(CreateOrderRequestDto dto, CancellationToken ct);
}
public record CreateOrderRequestDto(string CustomerName, decimal Total);
public record OrderResponseDto(Guid Id, string CustomerName, decimal Total);
public class OrderService : IOrderService
{
    public Task<OrderResponseDto?> GetByIdAsync(Guid id, CancellationToken ct) => 
        Task.FromResult<OrderResponseDto?>(new OrderResponseDto(id, "Acme Corp", 450.00m));
    public Task<OrderResponseDto> CreateAsync(CreateOrderRequestDto dto, CancellationToken ct) => 
        Task.FromResult(new OrderResponseDto(Guid.NewGuid(), dto.CustomerName, dto.Total));
}
```

#### 4. Line-by-Line Code Walkthrough
- `app.MapGroup("/api/orders")`: Organizes endpoints logically with shared route prefixes, auth policies, and filters without requiring a controller class.
- `.AddEndpointFilter(...)`: Injects cross-cutting concerns (validation, logging, telemetry) in the exact same manner as MVC action filters.
- `Results.Ok(order)` / `Results.NotFound()`: Emits strongly typed `IResult` objects that integrate with OpenAPI / Swagger documentation automatically.

#### 5. Real-World Enterprise Use Case & Application
Serverless Azure Functions & Container Apps: Microservices running on container orchestrators (Kubernetes / Azure Container Apps) use Minimal APIs compiled with **Native AOT**, booting in 15 milliseconds with a 25 MB memory footprint, compared to 1,200 ms and 120 MB for standard controller-based apps.

#### 6. Common Pitfalls, Memory Traps & Anti-Patterns
- **The "Giant Program.cs" Anti-Pattern**: Writing 500 endpoint definitions in a single `Program.cs` file. Enterprise Minimal APIs organize endpoints into modular extension classes (e.g., `app.MapOrderEndpoints()`, `app.MapCustomerEndpoints()`).
- **Missing Model Validation**: Minimal APIs do not automatically validate `DataAnnotations` like `[ApiController]` does. Use **FluentValidation** integrated via an endpoint filter.

#### 7. Senior / Architect Interview Follow-ups
- **Interviewer**: *"How do Minimal APIs enable Native AOT compilation in .NET 8/9 where traditional Controllers fail?"*
- **Expert Answer**: Controller-based APIs rely heavily on runtime reflection to inspect assemblies, discover controllers, instantiate them via activator reflection, and match action parameters. Native AOT requires all types and call graphs to be known at compile time (trimming reflection). Minimal APIs in .NET 8 use **Request Delegate Generators (RDG)**: a C# Source Generator that inspects route lambdas during compilation and generates static, non-reflective C# dispatch code, allowing the entire application to compile to native machine binaries (`.exe` or ELF) with zero JIT or runtime reflection.

