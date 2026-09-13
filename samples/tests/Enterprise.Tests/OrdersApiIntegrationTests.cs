using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using FluentAssertions;
using Microsoft.AspNetCore.Mvc.Testing;
using Xunit;

namespace Enterprise.Tests;

public class OrdersApiIntegrationTests : IClassFixture<WebApplicationFactory<Program>>
{
    private readonly WebApplicationFactory<Program> _factory;
    private readonly HttpClient _client;

    public OrdersApiIntegrationTests(WebApplicationFactory<Program> factory)
    {
        _factory = factory;
        _client = factory.CreateClient();
    }

    [Fact]
    public async Task PostOrder_WithValidPayload_Returns201Created_AndCorrelationIdHeader()
    {
        // Arrange
        var request = new { CustomerId = 123, TotalAmount = 99.95m };

        // Act
        var response = await _client.PostAsJsonAsync("/api/v1/orders", request);

        // Assert
        response.StatusCode.Should().Be(HttpStatusCode.Created);
        response.Headers.Should().ContainKey(Enterprise.WebApi.Middleware.CorrelationIdMiddleware.CorrelationHeader);

        var content = await response.Content.ReadFromJsonAsync<JsonElement>();
        content.GetProperty("id").GetString().Should().NotBeNullOrWhiteSpace();
        content.GetProperty("totalAmount").GetDecimal().Should().Be(99.95m);
    }

    [Fact]
    public async Task PostOrder_WithInvalidCustomerId_Returns400BadRequest()
    {
        // Arrange
        var request = new { CustomerId = -5, TotalAmount = 50.00m };

        // Act
        var response = await _client.PostAsJsonAsync("/api/v1/orders", request);

        // Assert
        response.StatusCode.Should().Be(HttpStatusCode.BadRequest);
    }

    [Fact]
    public async Task GetOrderById_WhenOrderDoesNotExist_Returns404NotFound()
    {
        // Arrange
        var missingId = Guid.NewGuid();

        // Act
        var response = await _client.GetAsync($"/api/v1/orders/{missingId}");

        // Assert
        response.StatusCode.Should().Be(HttpStatusCode.NotFound);
    }

    [Fact]
    public async Task CustomCorrelationId_IsPreservedInResponse()
    {
        // Arrange
        var customCorrelationId = "custom-trace-id-abc-123";
        using var message = new HttpRequestMessage(HttpMethod.Get, $"/api/v1/orders/{Guid.NewGuid()}");
        message.Headers.Add(Enterprise.WebApi.Middleware.CorrelationIdMiddleware.CorrelationHeader, customCorrelationId);

        // Act
        var response = await _client.SendAsync(message);

        // Assert
        response.Headers.GetValues(Enterprise.WebApi.Middleware.CorrelationIdMiddleware.CorrelationHeader).Should().ContainSingle(customCorrelationId);
    }
}
