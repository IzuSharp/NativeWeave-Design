#nullable enable
using System;
using System.Collections.Generic;
using System.Diagnostics.CodeAnalysis;
namespace NativeWeave.Interop.InventoryRegression;

[return: MaybeNull]
public delegate TResult Projector<TInput, out TResult>([AllowNull] TInput input, [NotNullWhen(true)] out string? found)
    where TInput : class? where TResult : class, IDisposable, new();
public delegate ref readonly T RefReader<T>(ref T value) where T : unmanaged;
public delegate void BorrowAction<T>(scoped in T value) where T : allows ref struct;
public readonly ref struct Borrowed<T> where T : unmanaged { }
public interface IFactory<out T> where T : class { T Create(); }
public abstract class AbstractBase<T> where T : class?
{
    [return: NotNullIfNotNull("value")]
    public abstract string? Mirror([AllowNull] string? value);
    public abstract int this[[AllowNull] string? key, (int Left, int Right) range] { get; }
    public string? Value { [return: NotNull] get => throw new NotSupportedException(); }
}
public sealed class Derived : AbstractBase<string>, IFactory<string>
{
    public override string? Mirror(string? value) => throw new NotSupportedException();
    public override int this[string? key, (int Left, int Right) range] => throw new NotSupportedException();
    public string Create() => throw new NotSupportedException();
}
public abstract class Constraints<TValue, TNonNull, TClass, TBorrow>
    where TValue : struct where TNonNull : notnull where TClass : class?, IDisposable, new()
    where TBorrow : allows ref struct { }
public readonly record struct Point(int X, int Y);
public sealed record Item(string? Name);
[Flags] public enum Flags : ulong { None = 0, Highest = 1UL << 63, All = ulong.MaxValue }
public enum Signed : short { Negative = -2 }
public static class Constants
{
    public const byte Small = 7;
    public const long Minimum = long.MinValue;
    public const ulong Maximum = ulong.MaxValue;
    public const decimal Amount = 1.25m;
    public const string Text = "line\n\"quoted\"";
    public const bool Enabled = false;
    public const char Quote = '\'';
    public const string? Missing = null;
    public const float Infinity = float.PositiveInfinity;
    public const double NotANumber = double.NaN;
    public static TResult Inspect<TInput, TResult>([AllowNull] Dictionary<string, (TInput Value, int Code)[]>? values,
        [MaybeNullWhen(false)] out TResult result, params string[] names)
        where TInput : class? where TResult : class, IDisposable, new() => throw new NotSupportedException();
}
