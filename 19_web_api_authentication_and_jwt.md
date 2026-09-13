# Section 19: Web API Security, Authentication & JWT Deep-Dive

> **Curriculum Navigation:**  
> ⏪ [Previous: Section 18 – ASP.NET Core Web API Fundamentals](./18_web_api_basics.md) | 🏠 [Master Index](./README.md) | ⏩ [Next: Section 20 – Advanced Web API: Con-Neg, Formatters & HTTP Contract](./20_web_api_advanced.md)

---

### Q190. What are the types of authentication techniques in web API?

#### 1. Executive Summary & Core Concept
- **Authentication** is the security process of **verifying the identity of a client or user attempting to access an API**.
- Primary authentication mechanisms used in modern Web APIs:
  1. **Token-Based / JWT Authentication (Bearer Token)**: **(Enterprise Standard)** Stateless JSON Web Tokens containing signed claims.
  2. **API Key Authentication**: Pre-shared secret keys passed via custom headers (`X-Api-Key`), common in service-to-service B2B integrations.
  3. **OAuth 2.0 & OpenID Connect (OIDC)**: Delegated authorization framework using identity providers (Azure Entra ID, Auth0, Okta).
  4. **Mutual TLS (mTLS)**: Hardware/certificate-level cryptographic handshake verifying client certificates.
  5. **Basic Authentication (Legacy)**: Base64-encoded username and password passed in headers. Strictly insecure unless over TLS.

#### 2. Deep-Dive Architecture & Runtime Internals
- In ASP.NET Core, authentication is decoupled into an **Authentication Scheme Pipeline**:
  1. The **Authentication Middleware (`UseAuthentication`)** intercepts incoming requests.
  2. The registered **`IAuthenticationHandler`** for the default scheme extracts credentials from headers.
  3. If valid, it constructs a **`ClaimsPrincipal`** containing **`ClaimsIdentity`** objects and assigns it to **`HttpContext.User`**.
  4. Subsequent controllers and authorization attributes (`[Authorize]`) query `HttpContext.User`.

```
ASP.NET Core Authentication Pipeline:
Incoming HTTP Request (Authorization: Bearer <token>)
                         │
                         ▼
        [ Authentication Middleware ]
                         │
                         ▼
         [ JwtBearerHandler (IAuthenticationHandler) ]
           - Validates signature with Secret Key
           - Validates Issuer, Audience, Expiry
                         │
                         ▼
Constructs ClaimsPrincipal ──▶ Assigned to HttpContext.User
                         │
                         ▼
        [ Authorization Middleware ([Authorize]) ] ──▶ Evaluates Policies & Roles
```

#### 3. Production-Ready Code Implementation
Configuring multi-scheme authentication in modern ASP.NET Core:

```csharp
using System.Text;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.IdentityModel.Tokens;

namespace EnterpriseArchitecture.Security;

public static class SecurityConfiguration
{
    public static void ConfigureAuthentication(IServiceCollection services, string signingKey, string issuer, string audience)
    {
        var keyBytes = Encoding.UTF8.GetBytes(signingKey);

        services.AddAuthentication(options =>
        {
            // Set JWT as default challenge and authenticate scheme
            options.DefaultAuthenticateScheme = JwtBearerDefaults.AuthenticationScheme;
            options.DefaultChallengeScheme = JwtBearerDefaults.AuthenticationScheme;
        })
        .AddJwtBearer(options =>
        {
            options.RequireHttpsMetadata = true; // Enforce HTTPS
            options.SaveToken = true;
            options.TokenValidationParameters = new TokenValidationParameters
            {
                ValidateIssuerSigningKey = true,
                IssuerSigningKey = new SymmetricSecurityKey(keyBytes),
                ValidateIssuer = true,
                ValidIssuer = issuer,
                ValidateAudience = true,
                ValidAudience = audience,
                ValidateLifetime = true, // Rejects expired tokens!
                ClockSkew = TimeSpan.FromMinutes(1) // Minimal clock drift tolerance
            };
        });

        services.AddAuthorization();
    }
}
```

#### 4. Line-by-Line Code Walkthrough
- `options.DefaultAuthenticateScheme = JwtBearerDefaults.AuthenticationScheme`: Tells the runtime to inspect the `Authorization: Bearer <token>` header on every request.
- `ClockSkew = TimeSpan.FromMinutes(1)`: Reduces the default 5-minute clock drift tolerance to 1 minute, ensuring expired tokens are rejected promptly.

#### 5. Real-World Enterprise Use Case & Application
Microservice security architectures: The API Gateway terminates external client authentication and propagates validated JWT bearer tokens to downstream internal services.

#### 6. Common Pitfalls, Memory Traps & Anti-Patterns
- Forgetting `app.UseAuthentication()` before `app.UseAuthorization()` in `Program.cs`. In ASP.NET Core, **middleware ordering is strictly sequential**! If `UseAuthorization()` is placed before `UseAuthentication()`, `HttpContext.User` will always be unauthenticated!

#### 7. Senior / Architect Interview Follow-ups
- **Interviewer**: *"What is the difference between Authentication and Authorization?"*
- **Expert Answer**: **Authentication (AuthN)** answers: *"Who are you?"* (Verifying identity via passwords, tokens, or biometrics). **Authorization (AuthZ)** answers: *"What are you allowed to do?"* (Verifying permissions, roles, and policies). Authentication must always precede authorization.

---

### Q191. What is Basic Authentication in Web API?

#### 1. Executive Summary & Core Concept
- **Basic Authentication** is an ancient, simple authentication scheme defined in **RFC 7617**.
- The client sends credentials formatted as **`username:password`**, encoded in **Base64**, inside the HTTP `Authorization` header:
  `Authorization: Basic YWxpY2U6UGFzc3dvcmQxMjMh`.
- **Security Reality**: **Base64 is NOT encryption!** Base64 is merely an encoding scheme that anyone can instantly decode back to plaintext. Therefore, Basic Authentication **MUST NEVER be used over unencrypted HTTP**. It is only permissible over **TLS/HTTPS** for legacy or automated system-to-system scripts.

#### 2. Deep-Dive Architecture & Runtime Internals
Execution flow:
1. Client makes an unauthenticated request to a protected endpoint.
2. Server rejects request with **HTTP 401 Unauthorized** and sends the header: `WWW-Authenticate: Basic realm="CorpApi"`.
3. Client browser or tool prompts user, concatenates `username + ":" + password`, encodes to Base64, and resends with `Authorization: Basic ...`.
4. Server extracts header, decodes Base64, and validates credentials against database/Active Directory.

```
Basic Authentication Flow:
Client ──▶ GET /api/secure ──▶ Server returns HTTP 401 (WWW-Authenticate: Basic)
Client encodes: Base64("admin:SecretPass") = "YWRtaW46U2VjcmV0UGFzcw=="
Client ──▶ GET /api/secure (Authorization: Basic YWRtaW46U2VjcmV0UGFzcw==) ──▶ Server returns HTTP 200 OK
```

#### 3. Production-Ready Code Implementation
Custom Basic Authentication Handler in modern ASP.NET Core:

```csharp
using System;
using System.Net.Http.Headers;
using System.Security.Claims;
using System.Text;
using System.Text.Encodings.Web;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Authentication;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;

namespace EnterpriseArchitecture.BasicAuth;

public sealed class BasicAuthenticationHandler : AuthenticationHandler<AuthenticationSchemeOptions>
{
    public BasicAuthenticationHandler(
        IOptionsMonitor<AuthenticationSchemeOptions> options, 
        ILoggerFactory logger, 
        UrlEncoder encoder) : base(options, logger, encoder) { }

    protected override Task<AuthenticateResult> HandleAuthenticateAsync()
    {
        // 1. Check for Authorization header
        if (!Request.Headers.ContainsKey("Authorization"))
            return Task.FromResult(AuthenticateResult.Fail("Missing Authorization Header"));

        try
        {
            var authHeader = AuthenticationHeaderValue.Parse(Request.Headers.Authorization!);
            if (!authHeader.Scheme.Equals("Basic", StringComparison.OrdinalIgnoreCase))
                return Task.FromResult(AuthenticateResult.Fail("Invalid Authorization Scheme"));

            // 2. Decode Base64 string
            byte[] credentialBytes = Convert.FromBase64String(authHeader.Parameter ?? string.Empty);
            string[] credentials = Encoding.UTF8.GetString(credentialBytes).Split(':', 2);
            string username = credentials[0];
            string password = credentials[1];

            // 3. Validate credentials (In production, verify against secure hash store)
            if (username == "svc_account" && password == "SecureEnvPassword_2026!")
            {
                var claims = new[] { new Claim(ClaimTypes.Name, username), new Claim(ClaimTypes.Role, "ServiceWorker") };
                var identity = new ClaimsIdentity(claims, Scheme.Name);
                var principal = new ClaimsPrincipal(identity);
                var ticket = new AuthenticationTicket(principal, Scheme.Name);

                return Task.FromResult(AuthenticateResult.Success(ticket));
            }

            return Task.FromResult(AuthenticateResult.Fail("Invalid Username or Password"));
        }
        catch
        {
            return Task.FromResult(AuthenticateResult.Fail("Malformed Authorization Header"));
        }
    }
}
```

#### 4. Line-by-Line Code Walkthrough
- `Convert.FromBase64String(...)`: Decodes Base64 bytes.
- `AuthenticateResult.Success(ticket)`: Signs user in for the current request.

#### 5. Real-World Enterprise Use Case & Application
Internal legacy webhook callbacks (e.g., legacy Jenkins or Jira webhooks posting to internal alert endpoints).

#### 6. Common Pitfalls, Memory Traps & Anti-Patterns
- Using Basic Authentication over plain HTTP (`http://`). Anyone sniffing network traffic reads the database password in plaintext!

#### 7. Senior / Architect Interview Follow-ups
- **Interviewer**: *"Why is Basic Authentication fundamentally ill-suited for public Single Page Applications (SPAs)?"*
- **Expert Answer**: Basic Authentication requires the client to **store the raw plaintext password** in the browser (localStorage or memory) to transmit it on every single HTTP request. In public SPAs, storing raw user passwords in JavaScript memory exposes users to XSS attacks and credential theft. Modern architectures use OAuth 2.0 with short-lived access tokens.

---

### Q192. What is API Key Authentication in Web API?

#### 1. Executive Summary & Core Concept
- **API Key Authentication** is an authentication mechanism where the client transmits a **long, unique, randomly generated cryptographic secret token (the API Key)** with every request.
- The key is typically transmitted via:
  1. **Custom HTTP Header (`X-Api-Key`)**: **(Enterprise Standard)**
  2. **Query String Parameter (`?api_key=...`)**: **(Discouraged; logs leak keys in server access logs!)**
- **Primary Use**: **Server-to-Server (B2B) Integrations** (e.g., Stripe, SendGrid, OpenAI API calls). It identifies the *calling application*, not an individual human user.

#### 2. Deep-Dive Architecture & Runtime Internals
- In modern ASP.NET Core, API Key authentication is implemented using a custom **Middleware** or **Endpoint Filter**.
- The server checks the key against a hashed key store:
  - **Security Mandate**: Never store raw API keys in the database! Store **SHA-256 hashes** of the API keys (similar to password hashing) so that a database breach does not expose valid keys!

```
API Key Validation Flow:
Client ──▶ (Header: X-Api-Key: sk_live_8F3a9...) ──▶ Web API Gateway
                                                             │
                                                             ▼
                                                 Computes SHA256(Key)
                                                             │
                                                             ▼
                                                 Matches with DB Hash Table?
                                                             ├─▶ NO  ──▶ Returns HTTP 401 Unauthorized
                                                             └─▶ YES ──▶ Returns HTTP 200 OK
```

#### 3. Production-Ready Code Implementation
Modern C# Endpoint Filter for API Key validation:

```csharp
using System.Security.Cryptography;
using System.Text;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Http;

namespace EnterpriseArchitecture.ApiKeyAuth;

public sealed class ApiKeyEndpointFilter : IEndpointFilter
{
    private const string ApiKeyHeaderName = "X-Api-Key";
    private readonly string _expectedKeyHash; // Pre-computed SHA256 hash of valid key

    public ApiKeyEndpointFilter(string expectedKeyHash)
    {
        _expectedKeyHash = expectedKeyHash;
    }

    public async ValueTask<object?> InvokeAsync(EndpointFilterInvocationContext context, EndpointFilterDelegate next)
    {
        HttpContext httpContext = context.HttpContext;

        // 1. Check for header
        if (!httpContext.Request.Headers.TryGetValue(ApiKeyHeaderName, out var extractedKey))
        {
            return Results.Json(new { error = "API Key missing in X-Api-Key header." }, statusCode: StatusCodes.Status401Unauthorized);
        }

        // 2. Hash extracted key
        byte[] inputBytes = Encoding.UTF8.GetBytes(extractedKey.ToString());
        string calculatedHash = Convert.ToHexString(SHA256.HashData(inputBytes));

        // 3. Constant-time comparison to prevent timing attacks!
        if (!CryptographicOperations.FixedTimeEquals(
                Encoding.UTF8.GetBytes(calculatedHash), 
                Encoding.UTF8.GetBytes(_expectedKeyHash)))
        {
            return Results.Json(new { error = "Unauthorized: Invalid API Key." }, statusCode: StatusCodes.Status401Unauthorized);
        }

        // Authorized: Continue to API action
        return await next(context);
    }
}
```

#### 4. Line-by-Line Code Walkthrough
- `CryptographicOperations.FixedTimeEquals(...)`: Crucial security practice performing a **constant-time byte comparison**, protecting against **Timing Attacks** where hackers measure sub-microsecond response time variations to guess valid keys.

#### 5. Real-World Enterprise Use Case & Application
Payment APIs (Stripe, Adyen) and AI model endpoints (OpenAI, Anthropic): Customers pass `Authorization: Bearer sk_live_...` to authenticate service-to-service calls.

#### 6. Common Pitfalls, Memory Traps & Anti-Patterns
- Passing API keys in query parameters (`/api/data?key=123`). URLs are recorded in plain text in browser histories, proxy logs, and CDN analytics, exposing the secret.

#### 7. Senior / Architect Interview Follow-ups
- **Interviewer**: *"What is a Timing Attack on string comparison, and how does `FixedTimeEquals` prevent it?"*
- **Expert Answer**: Standard string equality (`a == b`) compares characters sequentially and returns `false` on the **very first mismatched character**. An attacker can send millions of requests and measure minute CPU latency differences to determine how many leading characters of a secret key were correct. **`CryptographicOperations.FixedTimeEquals`** always compares all bytes regardless of mismatches, ensuring constant execution time and completely neutralizing timing attacks.

---

### Q193. What is Token-based authentication?

#### 1. Executive Summary & Core Concept
- **Token-Based Authentication** is a **stateless authentication paradigm** where the server generates a cryptographically signed **Security Token** upon successful user login and returns it to the client.
- The client stores the token locally and includes it in the **`Authorization: Bearer <token>`** header of all subsequent HTTP requests.
- **The Decisive Advantage**: **Statelessness**. The server does **not** store session IDs in server memory or distributed session databases. Any server in a server farm can independently validate the token purely by checking its cryptographic signature.

#### 2. Deep-Dive Architecture & Runtime Internals
Session-Based vs Token-Based Comparison:
- **Session-Based (Stateful)**:
  - Client logs in $\rightarrow$ Server stores session object in RAM/Redis $\rightarrow$ Returns Session Cookie $\rightarrow$ Future calls look up session in RAM.
  - **Bottleneck**: Server farms require centralized Redis cache clusters; if Redis goes down, all users are logged out.
- **Token-Based (Stateless)**:
  - Client logs in $\rightarrow$ Server generates signed token containing user claims (`Id=42`, `Role=Admin`) $\rightarrow$ Returns token.
  - Future calls: Server uses its private key to verify the mathematical signature.
  - **Scalability**: Zero database lookups required to verify identity; scales infinitely across global serverless clusters!

```
Session-Based (Stateful):
Client ──▶ Server 1 (Stores Session in RAM)
Client ──▶ Server 2 (ERROR: Session missing! Requires Sticky Sessions or Redis!)

Token-Based (Stateless):
Client ──▶ Server 1 (Returns Signed Token)
Client ──▶ Server 2 (Validates signature using shared secret key! SUCCESS!)
```

#### 3. Production-Ready Code Implementation
```csharp
using System.Security.Claims;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace EnterpriseArchitecture.TokenAuth;

[ApiController]
[Route("api/secure-vault")]
public sealed class SecureVaultController : ControllerBase
{
    // ENDPOINT PROTECTED BY TOKEN AUTHENTICATION
    [HttpGet("user-profile")]
    [Authorize] // Enforces valid bearer token!
    public IActionResult GetUserProfile()
    {
        // Extract claims directly from the cryptographically validated token!
        // ZERO database lookups required!
        string? userId = User.FindFirstValue(ClaimTypes.NameIdentifier);
        string? userEmail = User.FindFirstValue(ClaimTypes.Email);

        return Ok(new
        {
            UserId = userId,
            Email = userEmail,
            Message = "Stateless token successfully validated."
        });
    }
}
```

#### 4. Line-by-Line Code Walkthrough
- `[Authorize]`: Intercepts request, invokes JWT validation, and rejects with HTTP 401 if token is missing, expired, or tampered with.
- `User.FindFirstValue(...)`: Reads claims decoded directly from the token payload.

#### 5. Real-World Enterprise Use Case & Application
Single Sign-On (SSO) across enterprise ecosystems: A user logs in once via a centralized Identity Provider, receives a signed token, and uses that token across 20 distinct microservices.

#### 6. Common Pitfalls, Memory Traps & Anti-Patterns
- Storing large amounts of data (e.g., entire user profile avatars) inside a token. Tokens are transmitted on **every single HTTP request**; bloated tokens waste network bandwidth.

#### 7. Senior / Architect Interview Follow-ups
- **Interviewer**: *"If Token-Based authentication is stateless, how do you immediately revoke or invalidate a compromised token before its expiration time?"*
- **Expert Answer**: This is the fundamental tradeoff of stateless tokens. Revocation strategies:
  1. **Short Lifespans + Refresh Tokens**: Set access token expiration to 5-15 minutes; revoke the long-lived **Refresh Token** in the database when access must be cut.
  2. **Token Revocation Blacklist (Bloom Filter / Redis)**: Store revoked token IDs (`jti`) in a high-speed in-memory Redis blacklist checked by the API Gateway.
  3. **Security Stamp Validation**: Invalidate all tokens for a user by updating a `TokenVersion` counter in the user table when passwords change.

---

### Q194. What is JWT Authentication?

#### 1. Executive Summary & Core Concept
- **JWT (JSON Web Token)** is an open industry standard (**RFC 7519**) that defines a compact, self-contained format for securely transmitting information between parties as a JSON object.
- **Self-Contained**: Contains all information about the user (identity, roles, permissions) within the token payload itself.
- **Digitally Signed**: Tokens are cryptographically signed using either:
  - A **Symmetric Secret Key** (HMAC-SHA256 / HS256): Same secret key signs and validates.
  - An **Asymmetric Public/Private Key Pair** (RSA / RS256): Private key signs; public key validates.

#### 2. Deep-Dive Architecture & Runtime Internals
- **Symmetric (HS256) vs Asymmetric (RS256) in Microservices**:
  - **HS256**: Requires every microservice to share the exact same private secret key. If one microservice is breached, the attacker can forge tokens for all services!
  - **RS256**: The Identity Provider holds the **Private Key** to sign tokens. All microservices hold only the **Public Key** to validate tokens. Safe for zero-trust microservice meshes.

```
RS256 Asymmetric Token Architecture:
Identity Server (Holds Private Key) ──(Signs JWT)──▶ Client Receives Token
                                                              │
                                ┌─────────────────────────────┴─────────────────────────────┐
                                ▼                                                           ▼
                   [ Billing Microservice ]                                    [ Shipping Microservice ]
                   (Holds Public Key ONLY!)                                    (Holds Public Key ONLY!)
                   (Validates signature cleanly; cannot forge tokens!)         (Validates signature cleanly!)
```

#### 3. Production-Ready Code Implementation
Generating a cryptographically signed JWT in C# using `System.IdentityModel.Tokens.Jwt`:

```csharp
using System;
using System.Collections.Generic;
using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Text;
using Microsoft.IdentityModel.Tokens;

namespace EnterpriseArchitecture.JwtAuth;

public static class JwtTokenIssuer
{
    public static string GenerateEnterpriseToken(
        string userId, 
        string email, 
        IEnumerable<string> roles,
        string secretKey, 
        string issuer, 
        string audience,
        TimeSpan validityDuration)
    {
        var key = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(secretKey));
        var credentials = new SigningCredentials(key, SecurityAlgorithms.HmacSha256);

        // 1. Define Claims (Identity Payload)
        var claims = new List<Claim>
        {
            new(JwtRegisteredClaimNames.Sub, userId),
            new(JwtRegisteredClaimNames.Email, email),
            new(JwtRegisteredClaimNames.Jti, Guid.NewGuid().ToString("N")), // Unique Token ID
            new(JwtRegisteredClaimNames.Iat, DateTimeOffset.UtcNow.ToUnixTimeSeconds().ToString(), ClaimValueTypes.Integer64)
        };

        // Add user roles
        foreach (var role in roles)
        {
            claims.Add(new Claim(ClaimTypes.Role, role));
        }

        // 2. Build Token
        var tokenDescriptor = new JwtSecurityToken(
            issuer: issuer,
            audience: audience,
            claims: claims,
            notBefore: DateTime.UtcNow,
            expires: DateTime.UtcNow.Add(validityDuration),
            signingCredentials: credentials);

        // 3. Serialize to Compact Base64 URL String (Header.Payload.Signature)
        return new JwtSecurityTokenHandler().WriteToken(tokenDescriptor);
    }
}
```

#### 4. Line-by-Line Code Walkthrough
- `JwtRegisteredClaimNames.Jti`: Assigns a unique GUID (`jti` claim) to the token, crucial for auditing and token blacklisting.
- `SecurityAlgorithms.HmacSha256`: Cryptographic algorithm signing the header and payload.
- `WriteToken(...)`: Serializes the three parts into standard dot-separated base64 string format.

#### 5. Real-World Enterprise Use Case & Application
Decentralized microservice ecosystems: Authentication servers issue JWTs, allowing 50 independent downstream microservices to validate client permissions in milliseconds without calling back to the authentication database.

#### 6. Common Pitfalls, Memory Traps & Anti-Patterns
- **Using Weak Symmetric Keys**: Using secret keys shorter than 256 bits (32 bytes). In modern .NET, the JWT handler throws an `ArgumentOutOfRangeException` if the signing key is too short.

#### 7. Senior / Architect Interview Follow-ups
- **Interviewer**: *"Is a JWT encrypted by default, and can a client read the claims inside a standard JWT?"*
- **Expert Answer**: **NO, a standard JWT is NOT encrypted!** A standard JWT is **Signed (JWS - JSON Web Signature)**, not Encrypted (JWE - JSON Web Encryption). The payload is merely Base64URL-encoded. Anyone who intercepts the token can decode it and read all claim values in plain text. **Never store passwords, credit card numbers, or sensitive PII inside a JWT payload!**

---

### Q195. What are the parts of a JWT token?

#### 1. Executive Summary & Core Concept
- A JSON Web Token (JWT) consists of **three distinct parts separated by dots (`.`)**:
  `Header.Payload.Signature`
- **Part 1: Header**: Metadata specifying the **token type (`JWT`)** and the **signing algorithm (`HS256` or `RS256`)**.
- **Part 2: Payload**: The **Claims set** containing user data, permissions, expiration timestamps (`exp`), and issuers (`iss`).
- **Part 3: Signature**: A **cryptographic hash** computed by signing the Base64-encoded Header and Payload using the server's private secret key.

#### 2. Deep-Dive Architecture & Runtime Internals
Signature Computation Formula:
```
Signature = HMACSHA256(
    Base64UrlEncode(Header) + "." + Base64UrlEncode(Payload),
    SecretKey
)
```
- **Tamper-Proof Guarantee**:
  - If a malicious client tampers with the Payload (e.g., changing `"Role": "User"` to `"Role": "Admin"`), the resulting recalculated hash on the server **will not match the Signature**.
  - The server rejects the modified token immediately without executing any application logic!

```
Visual Breakdown of a JWT:
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTYiLCJuYW1lIjoiQWxpY2UifQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
│                                   │                                           │
└──────────── HEADER ───────────────┴──────────────── PAYLOAD ──────────────────┴───────────── SIGNATURE ───────────┘
```

#### 3. Production-Ready Code Implementation
Decoding and inspecting the three parts of a JWT programmatically:

```csharp
using System;
using System.IdentityModel.Tokens.Jwt;

namespace EnterpriseArchitecture.JwtInspection;

public static class JwtDeconstructor
{
    public static void InspectRawToken(string jwtToken)
    {
        var handler = new JwtSecurityTokenHandler();

        if (!handler.CanReadToken(jwtToken))
            throw new ArgumentException("Invalid JWT token format.");

        JwtSecurityToken token = handler.ReadJwtToken(jwtToken);

        // PART 1: HEADER
        Console.WriteLine("================ 1. HEADER ================");
        Console.WriteLine($"Algorithm: {token.Header.Alg}");
        Console.WriteLine($"Type:      {token.Header.Typ}");

        // PART 2: PAYLOAD (CLAIMS)
        Console.WriteLine("\n================ 2. PAYLOAD (CLAIMS) ================");
        Console.WriteLine($"Issuer:     {token.Issuer}");
        Console.WriteLine($"Valid To:   {token.ValidTo:O}");
        foreach (var claim in token.Claims)
        {
            Console.WriteLine($"Claim: {claim.Type,-30} = {claim.Value}");
        }

        // PART 3: SIGNATURE
        Console.WriteLine("\n================ 3. SIGNATURE ================");
        Console.WriteLine($"Raw Signature Hash: {token.RawSignature}");
    }
}
```

#### 4. Line-by-Line Code Walkthrough
- `handler.ReadJwtToken(...)`: Parses the token without validating the cryptographic signature (useful for client-side claim inspection).
- `token.RawSignature`: The cryptographic verification block.

#### 5. Real-World Enterprise Use Case & Application
API Gateways inspecting token headers to route requests to specific internal microservice clusters based on tenant IDs embedded in token claims.

#### 6. Common Pitfalls, Memory Traps & Anti-Patterns
- **The `"alg": "none"` Vulnerability**: A historic security flaw where early JWT parsers allowed attackers to set the algorithm header to `none`, causing parsers to skip signature verification entirely! Modern .NET JWT libraries completely forbid `none` algorithms.

#### 7. Senior / Architect Interview Follow-ups
- **Interviewer**: *"What are the standard Registered Claim Names defined in RFC 7519?"*
- **Expert Answer**: RFC 7519 standardizes 7 registered claims:
  1. **`iss` (Issuer)**: Identifies the principal that issued the JWT.
  2. **`sub` (Subject)**: Identifies the principal that is the subject of the JWT (e.g., UserId).
  3. **`aud` (Audience)**: Identifies the intended recipients (e.g., ApiResourceName).
  4. **`exp` (Expiration Time)**: Timestamp on or after which the token MUST NOT be accepted.
  5. **`nbf` (Not Before)**: Timestamp before which the token MUST NOT be accepted.
  6. **`iat` (Issued At)**: Timestamp when the token was created.
  7. **`jti` (JWT ID)**: Unique identifier for the token (used for replay attack prevention).

---

### Q196. Where does the JWT token reside in the request?

#### 1. Executive Summary & Core Concept
- In standard RESTful communication, the JWT token resides in the **HTTP Request Headers** under the **`Authorization`** header, prefixed with the keyword **`Bearer`** followed by a single space:
  `Authorization: Bearer <jwt_token_string>`
- **Alternative Storage / Transport Channels**:
  - **HTTP-Only, Secure Cookies**: **(Recommended for browser SPAs)** Protects against Cross-Site Scripting (XSS) attacks by preventing JavaScript from accessing the token.
  - **Query String Parameter**: Used **only** for specialized protocols that do not support custom headers (e.g., establishing WebSockets or **SignalR** connections: `?access_token=<jwt>`).

#### 2. Deep-Dive Architecture & Runtime Internals
Security Vector Comparison:
| Storage / Transmission | Transport Location | XSS Vulnerability | CSRF Vulnerability |
| :--- | :--- | :--- | :--- |
| **Authorization Header** | `Authorization: Bearer ...` | **Vulnerable if in localStorage** | **100% Immune to CSRF** |
| **HttpOnly Cookie** | `Cookie: jwt_token=...` | **100% Protected from XSS** | **Vulnerable unless Anti-CSRF token used** |
| **Query String** | `?access_token=...` | Vulnerable (Logged in server access logs) | Vulnerable |

```
Standard HTTP Transmission:
GET /api/v1/secure/transactions HTTP/1.1
Host: api.enterprise.corp
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Accept: application/json
```

#### 3. Production-Ready Code Implementation
Configuring SignalR to extract JWT from query strings while standard Web API extracts from the `Authorization` header:

```csharp
using System.Threading.Tasks;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.Extensions.DependencyInjection;

namespace EnterpriseArchitecture.TokenLocations;

public static class TokenLocationConfiguration
{
    public static void ConfigureTokenExtraction(IServiceCollection services)
    {
        services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
            .AddJwtBearer(options =>
            {
                options.Events = new JwtBearerEvents
                {
                    // SPECIALIZED OVERRIDE: Support WebSockets & SignalR (which cannot send headers)
                    OnMessageReceived = context =>
                    {
                        // 1. Check standard Authorization header first
                        // (Handled automatically by default JwtBearer middleware)

                        // 2. If missing, check query string for real-time WebSocket channels
                        var accessToken = context.Request.Query["access_token"];
                        var path = context.HttpContext.Request.Path;

                        // Only extract from query string for dedicated hub endpoints!
                        if (!string.IsNullOrEmpty(accessToken) && path.StartsWithSegments("/hubs"))
                        {
                            context.Token = accessToken;
                        }

                        return Task.CompletedTask;
                    }
                };
            });
    }
}
```

#### 4. Line-by-Line Code Walkthrough
- `OnMessageReceived`: Allows intercepting and reading JWT tokens from non-standard channels (like WebSocket query parameters) specifically for SignalR hubs.

#### 5. Real-World Enterprise Use Case & Application
Real-time financial trading dashboards: REST API data queries use the standard `Authorization: Bearer` header, while live stock price push streams use the SignalR `access_token` query parameter over WebSockets.

#### 6. Common Pitfalls, Memory Traps & Anti-Patterns
- Storing JWT tokens in the browser's **`localStorage`**. If the web application has a single XSS vulnerability (e.g., from a third-party npm package), malicious JavaScript can read `localStorage.getItem('token')` and steal the user's session! Store tokens in memory or **`HttpOnly; Secure; SameSite=Strict`** cookies.

#### 7. Senior / Architect Interview Follow-ups
- **Interviewer**: *"How do you defend against Cross-Site Request Forgery (CSRF) if you store JWT tokens in HttpOnly cookies?"*
- **Expert Answer**: When tokens are stored in cookies, browsers automatically append them to cross-site requests, making the API vulnerable to CSRF. Architects solve this using the **SameSite Cookie Attribute (`SameSite=Strict` or `Lax`)** and the **Double Submit Cookie Pattern**: The server sets an HttpOnly cookie containing the JWT and a second non-HttpOnly cookie containing a random CSRF token. Frontend JavaScript reads the CSRF token and copies it into a custom header (`X-XSRF-TOKEN`). The API validates that the header matches the cookie, defeating CSRF.
