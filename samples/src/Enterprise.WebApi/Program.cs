using Enterprise.Core.Domain;
using Enterprise.Core.Interfaces;
using Enterprise.WebApi.Middleware;
using Enterprise.WebApi.Services;
using Microsoft.AspNetCore.Mvc;

var builder = WebApplication.CreateBuilder(args);

// 1. DI Services
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

// Repositories
builder.Services.AddSingleton<InMemoryOrderRepository>();
builder.Services.AddSingleton<IOrderRepository>(sp => sp.GetRequiredService<InMemoryOrderRepository>());
builder.Services.AddSingleton<IOutboxRepository>(sp => sp.GetRequiredService<InMemoryOrderRepository>());

// Resilience: Register HttpClient with Polly v8 Standard Resilience Handler
builder.Services.AddHttpClient<IPaymentGateway, ResilientPaymentGateway>(client =>
{
    client.BaseAddress = new Uri("https://api.payments.mock");
    client.Timeout = TimeSpan.FromSeconds(5);
})
.AddStandardResilienceHandler(options =>
{
    options.Retry.MaxRetryAttempts = 3;
    options.Retry.UseJitter = true;
    options.CircuitBreaker.FailureRatio = 0.5;
    options.CircuitBreaker.SamplingDuration = TimeSpan.FromSeconds(10);
});

// Exception Handling
builder.Services.AddExceptionHandler<GlobalExceptionHandler>();
builder.Services.AddProblemDetails();

var app = builder.Build();

// 2. Middleware Pipeline
app.UseMiddleware<CorrelationIdMiddleware>();
app.UseExceptionHandler();

if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

app.UseHttpsRedirection();

// 3. Minimal API Endpoints
var ordersApi = app.MapGroup("/api/v1/orders").WithTags("Orders");

// POST: Create an Order with Transactional Outbox Pattern
ordersApi.MapPost("/", async (
    [FromBody] CreateOrderRequest request,
    IOrderRepository orderRepo,
    IOutboxRepository outboxRepo,
    IPaymentGateway paymentGateway,
    CancellationToken ct) =>
{
    if (request.CustomerId <= 0)
        return Results.BadRequest(new ProblemDetails { Detail = "CustomerId must be positive." });
    if (request.TotalAmount <= 0)
        return Results.BadRequest(new ProblemDetails { Detail = "TotalAmount must be positive." });

    var order = new Order(Guid.NewGuid(), request.CustomerId, request.TotalAmount);
    await orderRepo.AddAsync(order, ct);

    // Save Outbox Event (guaranteeing eventual consistency)
    var outboxEvent = new OutboxMessage
    {
        EventType = "OrderCreated",
        Payload = System.Text.Json.JsonSerializer.Serialize(new { order.Id, order.CustomerId, order.TotalAmount })
    };
    await outboxRepo.AddMessageAsync(outboxEvent, ct);

    // Process Payment via Polly Resilient Gateway
    await paymentGateway.ProcessPaymentAsync(order.Id, order.TotalAmount, ct);

    return Results.Created($"/api/v1/orders/{order.Id}", new { order.Id, order.Status, order.TotalAmount });
})
.WithName("CreateOrder")
.Produces(StatusCodes.Status201Created)
.ProducesProblem(StatusCodes.Status400BadRequest);

// GET: Retrieve Order by ID
ordersApi.MapGet("/{id:guid}", async (Guid id, IOrderRepository orderRepo, CancellationToken ct) =>
{
    var order = await orderRepo.GetByIdAsync(id, ct);
    return order != null ? Results.Ok(order) : Results.NotFound();
})
.WithName("GetOrderById")
.Produces<Order>(StatusCodes.Status200OK)
.Produces(StatusCodes.Status404NotFound);

app.Run();

public record CreateOrderRequest(int CustomerId, decimal TotalAmount);
