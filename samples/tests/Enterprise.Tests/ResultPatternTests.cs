using Enterprise.Core.Common;
using FluentAssertions;
using Xunit;

namespace Enterprise.Tests;

public class ResultPatternTests
{
    [Fact]
    public void SuccessResult_ShouldContainValue_AndBeSuccess()
    {
        // Arrange & Act
        var result = Result<int>.Success(42);

        // Assert
        result.IsSuccess.Should().BeTrue();
        result.IsFailure.Should().BeFalse();
        result.Value.Should().Be(42);
        result.Error.Should().BeEmpty();
    }

    [Fact]
    public void FailureResult_ShouldContainErrorMessage_AndBeFailure()
    {
        // Arrange & Act
        var result = Result<string>.Failure("Invalid customer state");

        // Assert
        result.IsSuccess.Should().BeFalse();
        result.IsFailure.Should().BeTrue();
        result.Error.Should().Be("Invalid customer state");
    }

    [Fact]
    public void AccessingValueOnFailure_ShouldThrowInvalidOperationException()
    {
        // Arrange
        var result = Result<string>.Failure("Error occurred");

        // Act
        var act = () => _ = result.Value;

        // Assert
        act.Should().Throw<InvalidOperationException>()
            .WithMessage("*failed result*");
    }
}
