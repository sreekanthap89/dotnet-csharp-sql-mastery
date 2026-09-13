namespace Enterprise.Core.Common;

public class Result
{
    public bool IsSuccess { get; }
    public bool IsFailure => !IsSuccess;
    public string Error { get; }

    protected Result(bool isSuccess, string error)
    {
        if (isSuccess && !string.IsNullOrEmpty(error))
            throw new InvalidOperationException("Successful result cannot have an error.");
        if (!isSuccess && string.IsNullOrEmpty(error))
            throw new InvalidOperationException("Failing result must have an error message.");

        IsSuccess = isSuccess;
        Error = error;
    }

    public static Result Success() => new(true, string.Empty);
    public static Result Failure(string error) => new(false, error);
}

public class Result<T> : Result
{
    private readonly T? _value;

    public T Value => IsSuccess 
        ? _value! 
        : throw new InvalidOperationException("Cannot access value of a failed result.");

    private Result(T value) : base(true, string.Empty) => _value = value;
    private Result(string error) : base(false, error) => _value = default;

    public static Result<T> Success(T value) => new(value);
    public static new Result<T> Failure(string error) => new(error);
}
