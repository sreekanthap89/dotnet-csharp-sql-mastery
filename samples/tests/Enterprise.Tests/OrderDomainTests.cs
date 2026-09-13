using Enterprise.Core.Domain;
using FluentAssertions;
using Xunit;

namespace Enterprise.Tests;

public class OrderDomainTests
{
    [Fact]
    public void CreateOrder_WithValidArguments_ShouldInstantiatePendingOrder()
    {
        // Arrange
        var id = Guid.NewGuid();
        var customerId = 101;
        var totalAmount = 250.50m;

        // Act
        var order = new Order(id, customerId, totalAmount);

        // Assert
        order.Id.Should().Be(id);
        order.CustomerId.Should().Be(customerId);
        order.TotalAmount.Should().Be(totalAmount);
        order.Status.Should().Be(OrderStatus.Pending);
        order.OrderDateUtc.Should().BeCloseTo(DateTime.UtcNow, TimeSpan.FromSeconds(5));
        order.Items.Should().BeEmpty();
    }

    [Theory]
    [InlineData(0)]
    [InlineData(-1)]
    [InlineData(-100)]
    public void CreateOrder_WithInvalidCustomerId_ShouldThrowArgumentException(int invalidCustomerId)
    {
        // Act
        var act = () => new Order(Guid.NewGuid(), invalidCustomerId, 100m);

        // Assert
        act.Should().Throw<ArgumentException>()
            .WithParameterName("customerId");
    }

    [Fact]
    public void CreateOrder_WithNegativeTotalAmount_ShouldThrowArgumentException()
    {
        // Act
        var act = () => new Order(Guid.NewGuid(), 1, -0.01m);

        // Assert
        act.Should().Throw<ArgumentException>()
            .WithParameterName("totalAmount");
    }

    [Fact]
    public void AddItem_ShouldAppendOrderItemToReadOnlyCollection()
    {
        // Arrange
        var order = new Order(Guid.NewGuid(), 42, 150m);
        var productId = Guid.NewGuid();

        // Act
        order.AddItem(productId, 3, 50m);

        // Assert
        order.Items.Should().HaveCount(1);
        var item = order.Items.First();
        item.OrderId.Should().Be(order.Id);
        item.ProductId.Should().Be(productId);
        item.Quantity.Should().Be(3);
        item.UnitPrice.Should().Be(50m);
    }

    [Fact]
    public void MarkAsShipped_WhenPending_ShouldTransitionToShipped()
    {
        // Arrange
        var order = new Order(Guid.NewGuid(), 42, 100m);

        // Act
        order.MarkAsShipped();

        // Assert
        order.Status.Should().Be(OrderStatus.Shipped);
    }
}
