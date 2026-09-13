using Enterprise.Core.Interfaces;

namespace Enterprise.WebApi.Services;

public class ResilientPaymentGateway : IPaymentGateway
{
    private readonly HttpClient _httpClient;
    private readonly ILogger<ResilientPaymentGateway> _logger;

    public ResilientPaymentGateway(HttpClient httpClient, ILogger<ResilientPaymentGateway> logger)
    {
        _httpClient = httpClient;
        _logger = logger;
    }

    public async Task<bool> ProcessPaymentAsync(Guid orderId, decimal amount, CancellationToken ct = default)
    {
        _logger.LogInformation("Attempting payment for Order {OrderId} of amount {Amount:C}", orderId, amount);

        // In real systems, this calls the external merchant provider over HTTP
        // Protected automatically by the Polly Standard Resilience Handler
        await Task.Delay(50, ct); // Simulated network latency
        return true;
    }
}
