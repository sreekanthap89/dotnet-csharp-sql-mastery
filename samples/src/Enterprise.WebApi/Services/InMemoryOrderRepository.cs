using System.Collections.Concurrent;
using Enterprise.Core.Domain;
using Enterprise.Core.Interfaces;

namespace Enterprise.WebApi.Services;

public class InMemoryOrderRepository : IOrderRepository, IOutboxRepository
{
    private readonly ConcurrentDictionary<Guid, Order> _orders = new();
    private readonly ConcurrentBag<OutboxMessage> _outbox = [];

    public Task<Order?> GetByIdAsync(Guid id, CancellationToken ct = default)
    {
        _orders.TryGetValue(id, out var order);
        return Task.FromResult(order);
    }

    public Task AddAsync(Order order, CancellationToken ct = default)
    {
        _orders[order.Id] = order;
        return Task.CompletedTask;
    }

    public Task SaveChangesAsync(CancellationToken ct = default) => Task.CompletedTask;

    public Task AddMessageAsync(OutboxMessage message, CancellationToken ct = default)
    {
        _outbox.Add(message);
        return Task.CompletedTask;
    }

    public Task<IReadOnlyList<OutboxMessage>> GetUnprocessedMessagesAsync(int batchSize, CancellationToken ct = default)
    {
        var messages = _outbox.Where(m => m.ProcessedOnUtc == null).Take(batchSize).ToList();
        return Task.FromResult<IReadOnlyList<OutboxMessage>>(messages);
    }

    public Task MarkAsProcessedAsync(Guid messageId, CancellationToken ct = default)
    {
        var message = _outbox.FirstOrDefault(m => m.Id == messageId);
        if (message != null)
        {
            message.ProcessedOnUtc = DateTime.UtcNow;
        }
        return Task.CompletedTask;
    }
}
