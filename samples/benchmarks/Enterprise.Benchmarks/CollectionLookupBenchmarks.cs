using System.Collections.Frozen;
using System.Collections.Immutable;
using BenchmarkDotNet.Attributes;

namespace Enterprise.Benchmarks;

[MemoryDiagnoser]
[HideColumns("Job", "Error", "StdDev", "Median", "RatioSD")]
public class CollectionLookupBenchmarks
{
    private const int ItemCount = 1_000;
    private static readonly string[] Keys = Enumerable.Range(0, ItemCount).Select(i => $"Tenant_Config_Key_{i:D5}").ToArray();
    private static readonly string MissingKey = "Tenant_Config_Key_99999";
    private static readonly string ExistingKey = "Tenant_Config_Key_00500";

    private Dictionary<string, int> _standardDictionary = null!;
    private FrozenDictionary<string, int> _frozenDictionary = null!;
    private ImmutableDictionary<string, int> _immutableDictionary = null!;

    [GlobalSetup]
    public void Setup()
    {
        var data = Keys.ToDictionary(k => k, k => Random.Shared.Next(1, 1000));
        _standardDictionary = new Dictionary<string, int>(data);
        _frozenDictionary = data.ToFrozenDictionary();
        _immutableDictionary = data.ToImmutableDictionary();
    }

    [Benchmark(Baseline = true)]
    public bool StandardDictionary_TryGetValue_Hit()
    {
        return _standardDictionary.TryGetValue(ExistingKey, out _);
    }

    [Benchmark]
    public bool FrozenDictionary_TryGetValue_Hit()
    {
        return _frozenDictionary.TryGetValue(ExistingKey, out _);
    }

    [Benchmark]
    public bool ImmutableDictionary_TryGetValue_Hit()
    {
        return _immutableDictionary.TryGetValue(ExistingKey, out _);
    }

    [Benchmark]
    public bool StandardDictionary_TryGetValue_Miss()
    {
        return _standardDictionary.TryGetValue(MissingKey, out _);
    }

    [Benchmark]
    public bool FrozenDictionary_TryGetValue_Miss()
    {
        return _frozenDictionary.TryGetValue(MissingKey, out _);
    }
}
