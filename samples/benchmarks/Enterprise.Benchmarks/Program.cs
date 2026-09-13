using BenchmarkDotNet.Running;
using Enterprise.Benchmarks;

Console.WriteLine("=== Enterprise Performance Benchmark Suite ===");
Console.WriteLine("Executing Memory & CPU Allocation Profiling...");

var summary = BenchmarkRunner.Run<StringAllocationBenchmarks>();
