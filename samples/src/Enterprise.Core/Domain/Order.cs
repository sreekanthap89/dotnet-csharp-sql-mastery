namespace Enterprise.Core.Domain;

public enum OrderStatus
{
    Pending,
    Processing,
    Shipped,
    Delivered,
    Cancelled
}

public class Order
{
    public Guid Id { get; private set; }
    public int CustomerId { get; private set; }
    public decimal TotalAmount { get; private set; }
    public OrderStatus Status { get; private set; }
    public DateTime OrderDateUtc { get; private set; }
    private readonly List<OrderItem> _items = [];
    public IReadOnlyCollection<OrderItem> Items => _items.AsReadOnly();

    // Private constructor for ORM / persistence
    private Order() { }

    public Order(Guid id, int customerId, decimal totalAmount)
    {
        if (customerId <= 0)
            throw new ArgumentException("Customer ID must be positive.", nameof(customerId));
        if (totalAmount < 0)
            throw new ArgumentException("Total amount cannot be negative.", nameof(totalAmount));

        Id = id;
        CustomerId = customerId;
        TotalAmount = totalAmount;
        Status = OrderStatus.Pending;
        OrderDateUtc = DateTime.UtcNow;
    }

    public void AddItem(Guid productId, int quantity, decimal unitPrice)
    {
        _items.Add(new OrderItem(Guid.NewGuid(), Id, productId, quantity, unitPrice));
    }

    public void MarkAsShipped()
    {
        if (Status == OrderStatus.Cancelled)
            throw new InvalidOperationException("Cannot ship a cancelled order.");

        Status = OrderStatus.Shipped;
    }
}

public class OrderItem
{
    public Guid Id { get; private set; }
    public Guid OrderId { get; private set; }
    public Guid ProductId { get; private set; }
    public int Quantity { get; private set; }
    public decimal UnitPrice { get; private set; }

    public OrderItem(Guid id, Guid orderId, Guid productId, int quantity, decimal unitPrice)
    {
        Id = id;
        OrderId = orderId;
        ProductId = productId;
        Quantity = quantity;
        UnitPrice = unitPrice;
    }
}
