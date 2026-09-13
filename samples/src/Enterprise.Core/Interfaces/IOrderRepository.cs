using Enterprise.Core.Domain;

namespace Enterprise.Core.Interfaces;

public interface IOrderRepository
{
    Task<Order?> GetByIdAsync(Guid id, CancellationToken ct = default);
    Task AddAsync(Order order, CancellationToken ct = default);
    Task SaveChangesAsync(CancellationToken ct = default);
}

public interface IOutboxRepository
{
    Task AddMessageAsync(OutboxMessage message, CancellationToken ct = default);
    Task<IReadOnlyList<OutboxMessage>> GetUnprocessedMessagesAsync(int batchSize, CancellationToken ct = default);
    Task MarkAsProcessedAsync(Guid messageId, CancellationToken ct = default);
}

public interface IPaymentGateway
{
    Task<bool> ProcessPaymentAsync(Guid orderId, decimal amount, CancellationToken ct = default);
}
