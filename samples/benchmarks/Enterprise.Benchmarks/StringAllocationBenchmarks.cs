using BenchmarkDotNet.Attributes;
using BenchmarkDotNet.Running;

namespace Enterprise.Benchmarks;

[MemoryDiagnoser]
[RankColumn]
public class StringAllocationBenchmarks
{
    private const string RawInput = "Enterprise.Microservice.Commerce.OrderService.v1.0.42";

    // 1. Classic Substring Approach (Allocates 3 Heap Strings)
    [Benchmark(Baseline = true)]
    public string SubstringAllocating()
    {
        int firstDot = RawInput.IndexOf('.');
        int secondDot = RawInput.IndexOf('.', firstDot + 1);
        int thirdDot = RawInput.IndexOf('.', secondDot + 1);

        string part1 = RawInput.Substring(0, firstDot);
        string part2 = RawInput.Substring(firstDot + 1, secondDot - firstDot - 1);
        string part3 = RawInput.Substring(secondDot + 1, thirdDot - secondDot - 1);

        return $"{part1}-{part2}-{part3}";
    }

    // 2. High-Performance Span & string.Create (Zero Intermediate Heap Allocations!)
    [Benchmark]
    public string SpanZeroAllocation()
    {
        ReadOnlySpan<char> span = RawInput.AsSpan();
        int firstDot = span.IndexOf('.');
        int secondDot = span.Slice(firstDot + 1).IndexOf('.') + firstDot + 1;
        int thirdDot = span.Slice(secondDot + 1).IndexOf('.') + secondDot + 1;

        ReadOnlySpan<char> part1 = span.Slice(0, firstDot);
        ReadOnlySpan<char> part2 = span.Slice(firstDot + 1, secondDot - firstDot - 1);
        ReadOnlySpan<char> part3 = span.Slice(secondDot + 1, thirdDot - secondDot - 1);

        int totalLen = part1.Length + 1 + part2.Length + 1 + part3.Length;

        return string.Create(totalLen, (RawInput, firstDot, secondDot, thirdDot), (dest, state) =>
        {
            ReadOnlySpan<char> s = state.RawInput.AsSpan();
            ReadOnlySpan<char> p1 = s.Slice(0, state.firstDot);
            ReadOnlySpan<char> p2 = s.Slice(state.firstDot + 1, state.secondDot - state.firstDot - 1);
            ReadOnlySpan<char> p3 = s.Slice(state.secondDot + 1, state.thirdDot - state.secondDot - 1);

            int pos = 0;
            p1.CopyTo(dest.Slice(pos));
            pos += p1.Length;

            dest[pos++] = '-';

            p2.CopyTo(dest.Slice(pos));
            pos += p2.Length;

            dest[pos++] = '-';

            p3.CopyTo(dest.Slice(pos));
        });
    }
}
