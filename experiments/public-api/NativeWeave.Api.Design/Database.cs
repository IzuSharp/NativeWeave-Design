// Design-only declaration fixture. Every behavioral body throws; this is not product code.
#nullable enable
using System;
using System.Collections.Generic;
using System.Data;
using System.Numerics;
using System.Diagnostics.CodeAnalysis;
using System.Text.Json.Serialization.Metadata;
using System.Threading;
using System.Threading.Tasks;

namespace NativeWeave.Data
{
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public enum DatabaseErrorKind { Provider, Constraint, Conversion, ShapeMismatch, UnsupportedCapability, ResourceLimit, ConcurrentUse, InvalidState, UnknownOutcome }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public class DatabaseException : Exception
    {
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public DatabaseException(string message, DatabaseErrorKind kind, string? providerCode = null, ulong correlationId = 0, Exception? innerException = null) : base(message, innerException) { }
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public DatabaseErrorKind Kind => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public string? ProviderCode => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public ulong CorrelationId => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public bool IsTransient => throw new NotSupportedException();
    }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public sealed class ConcurrencyConflictException : DatabaseException
    {
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public ConcurrencyConflictException(string message, long expectedRows, long actualRows) : base(message, DatabaseErrorKind.Constraint) { }
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public long ExpectedRows => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public long ActualRows => throw new NotSupportedException();
    }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public sealed class DatabaseCapabilityException : DatabaseException
    {
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public DatabaseCapabilityException(string capability, string provider) : base(capability, DatabaseErrorKind.UnsupportedCapability) { }
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public string Capability => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public string Provider => throw new NotSupportedException();
    }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public sealed class ValueCodec<T>
    {
        internal ValueCodec() { }
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public uint Id => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public string Name => throw new NotSupportedException();
    }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public static class Codecs
    {
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public static ValueCodec<short> Int16 => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public static ValueCodec<int> Int32 => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public static ValueCodec<long> Int64 => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public static ValueCodec<bool> Boolean => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public static ValueCodec<string> String => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public static ValueCodec<byte[]> Bytes => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public static ValueCodec<Guid> Guid => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public static ValueCodec<DateOnly> Date => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public static ValueCodec<TimeOnly> Time => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public static ValueCodec<DateTimeOffset> UtcInstant => throw new NotSupportedException();
        /// <summary>Maps DateTime values with Kind=Utc to the native UTC-instant codec; Local/Unspecified and precision loss reject.</summary>
        public static ValueCodec<DateTime> UtcDateTime => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public static ValueCodec<double> Double => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public static ValueCodec<float> Single => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public static ValueCodec<decimal> Decimal(byte precision, byte scale) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public static ValueCodec<decimal> DecimalText => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public static ValueCodec<decimal> FixedScaleMoney(byte scale) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public static ValueCodec<T?> Nullable<T>(ValueCodec<T> codec) where T : struct => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public static ValueCodec<T?> NullableReference<T>(ValueCodec<T> codec) where T : class => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public static ValueCodec<T> Json<T>(JsonTypeInfo<T> typeInfo) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public static ValueCodec<TEnum> EnumInt32<TEnum>() where TEnum : struct, Enum => throw new NotSupportedException();
    }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public delegate T RowMaterializer<T>(RowReader row);
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public delegate void EntityWriter<T>(RowWriter row, T value);
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public readonly ref struct RowReader
    {
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public T Get<T>(ResultColumn<T> column) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public T Get<TEntity, T>(Column<TEntity, T> column) where TEntity : class => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public bool IsNull(int ordinal) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public T Read<T>(int ordinal, ValueCodec<T> codec) => throw new NotSupportedException();
    }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public readonly ref struct RowWriter
    {
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public void Set<TEntity, T>(Column<TEntity, T> column, T value) where TEntity : class => throw new NotSupportedException();
    }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public readonly struct ResultColumn<T>
    {
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public int Ordinal => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public string Name => throw new NotSupportedException();
    }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public sealed record ColumnOptions
    {
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public bool IsPrimaryKey { get; init; }
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public bool IsGenerated { get; init; }
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public bool IsConcurrencyToken { get; init; }
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public string? Collation { get; init; }
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public int? MaxLength { get; init; }
    }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public sealed class Column<TEntity, T> where TEntity : class
    {
        internal Column() { }
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public string Name => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public uint Id => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public ValueCodec<T> Codec => throw new NotSupportedException();
    }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public sealed class TableBuilder<TEntity> where TEntity : class
    {
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public TableBuilder(string tableName, string? schema = null) { }
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Column<TEntity, T> Column<T>(string name, ValueCodec<T> codec, ColumnOptions? options = null) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Table<TEntity> Build(RowMaterializer<TEntity> materializer, EntityWriter<TEntity> writer) => throw new NotSupportedException();
    }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public sealed class Table<TEntity> where TEntity : class
    {
        internal Table() { }
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public string Name => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public string? Schema => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public string MetadataHash => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Projection<TEntity> Row => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public EntityKey<TEntity> Key<T>(Column<TEntity, T> column, T value) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public bool TryGetColumn<T>(string name, ValueCodec<T> codec, [NotNullWhen(true)] out Column<TEntity, T>? column) => throw new NotSupportedException();
    }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public sealed class EntityKey<TEntity> where TEntity : class
    {
        internal EntityKey() { }
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public EntityKey<TEntity> And<T>(Column<TEntity, T> column, T value) => throw new NotSupportedException();
    }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public sealed class Projection<T>
    {
        internal Projection() { }
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public string ShapeHash => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public static Projection<T> Create(ReadOnlySpan<ResultField> fields, RowMaterializer<T> materializer) => throw new NotSupportedException();
    }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public sealed class ResultField
    {
        private ResultField() { }
        /// <summary>Creates a static result field with its exact codec configuration and nullability.</summary>
        public static ResultField Create<T>(string name, ValueCodec<T> codec) => throw new NotSupportedException();
        /// <summary>The exact result alias.</summary>
        public string Name => throw new NotSupportedException();
        /// <summary>The logical codec identifier; native configured binding is source-owned.</summary>
        public uint CodecId => throw new NotSupportedException();
        /// <summary>Whether SQL NULL is permitted by the selected typed codec.</summary>
        public bool IsNullable => throw new NotSupportedException();
    }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public sealed class Changes<TEntity> where TEntity : class
    {
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Changes() { }
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Changes<TEntity> Set<T>(Column<TEntity, T> column, T value) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Changes<TEntity> Unset<T>(Column<TEntity, T> column) => throw new NotSupportedException();
    }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public sealed class ConcurrencyCheck<TEntity> where TEntity : class
    {
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public ConcurrencyCheck() { }
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public ConcurrencyCheck<TEntity> Expect<T>(Column<TEntity, T> column, T value) => throw new NotSupportedException();
    }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public sealed class SqlParameters
    {
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public SqlParameters() { }
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public SqlParameters Add<T>(string name, T value, ValueCodec<T> codec) => throw new NotSupportedException();
    }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    /// <summary>An explicit native relationship over registered metadata; no lazy loading or identity map.</summary>
    public sealed class Relation<TParent, TChild> where TParent : class where TChild : class
    {
        private Relation() { }
        /// <summary>Creates an ordered parent-key/child-foreign-key relation.</summary>
        public static Relation<TParent, TChild> Create<T>(Table<TParent> parent, Column<TParent, T> parentKey, Table<TChild> child, Column<TChild, T> foreignKey) => throw new NotSupportedException();
        /// <summary>Returns a new immutable relation with one corresponding key component appended.</summary>
        public Relation<TParent, TChild> And<T>(Column<TParent, T> parentKey, Column<TChild, T> foreignKey) => throw new NotSupportedException();
        /// <summary>Creates a relation from a non-null parent value key to an optional child foreign key.</summary>
        public static Relation<TParent, TChild> CreateOptional<T>(Table<TParent> parent, Column<TParent, T> parentKey, Table<TChild> child, Column<TChild, T?> foreignKey) where T : struct => throw new NotSupportedException();
        /// <summary>Creates a relation from a non-null parent reference key to an optional child foreign key.</summary>
        public static Relation<TParent, TChild> CreateOptionalReference<T>(Table<TParent> parent, Column<TParent, T> parentKey, Table<TChild> child, Column<TChild, T?> foreignKey) where T : class => throw new NotSupportedException();
        /// <summary>Returns a new relation with one optional value-type foreign-key component appended.</summary>
        public Relation<TParent, TChild> AndOptional<T>(Column<TParent, T> parentKey, Column<TChild, T?> foreignKey) where T : struct => throw new NotSupportedException();
        /// <summary>Returns a new relation with one optional reference-type foreign-key component appended.</summary>
        public Relation<TParent, TChild> AndOptionalReference<T>(Column<TParent, T> parentKey, Column<TChild, T?> foreignKey) where T : class => throw new NotSupportedException();
    }
    public enum SqlCommandKind { Query, Mutation, SessionMutating }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public sealed class SqlCommand
    {
        private SqlCommand() { }
        /// <summary>Snapshots built-in scalar values from an interpolated SQL template; values are always parameters.</summary>
        public static SqlCommand Parameterized(FormattableString sql, SqlCommandKind kind = SqlCommandKind.Query, TimeSpan? timeout = null) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public static SqlCommand Create(string sql, SqlParameters? parameters = null, SqlCommandKind kind = SqlCommandKind.Query, TimeSpan? timeout = null) => throw new NotSupportedException();
    }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    [AttributeUsage(AttributeTargets.Class, Inherited = false)]
    public sealed class WeaveTableAttribute : Attribute
    {
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public WeaveTableAttribute(string name) { }
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public string? Schema { get; init; }
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public string? DescriptorName { get; init; }
    }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    [AttributeUsage(AttributeTargets.Property, Inherited = false)]
    public sealed class WeaveColumnAttribute : Attribute
    {
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public WeaveColumnAttribute(string name) { }
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public bool Generated { get; init; }
    }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    [AttributeUsage(AttributeTargets.Property, Inherited = false)]
    public sealed class WeaveKeyAttribute : Attribute { }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    [AttributeUsage(AttributeTargets.Property, Inherited = false)]
    public sealed class WeaveVersionAttribute : Attribute { }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    [AttributeUsage(AttributeTargets.Property, Inherited = false)]
    public sealed class WeaveIgnoreAttribute : Attribute { }
}

namespace NativeWeave.Database
{
    using NativeWeave.Data;
    using NativeWeave.Query;
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public enum DatabaseProvider { PostgreSql, Sqlite }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public enum TransactionOutcome { InProgress, Committed, RolledBack, Unknown }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public enum TransactionState { Active, Failed, CommitInFlight, RollbackInFlight, Closed }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public enum ConnectionDisposition { Usable, ProviderResetPending, Quarantined, Discarded }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public enum CleanupStatus { NotStarted, Pending, Succeeded, RollbackUnconfirmed, Failed }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public sealed record DatabaseCloseResult(CleanupStatus Status, ulong CorrelationId, string? ProviderCode, bool LocalResourcesReleased, ConnectionDisposition ConnectionDisposition, bool DeadlineExceeded);
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public sealed record TransactionOptions
    {
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public IsolationLevel? Isolation { get; init; }
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public string? RecoveryKey { get; init; }
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public TimeSpan CommitTimeout { get; init; } = TimeSpan.FromSeconds(30);
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public TimeSpan CleanupTimeout { get; init; } = TimeSpan.FromSeconds(5);
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public bool ReadOnly { get; init; }
    }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public sealed record DatabaseLimits
    {
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public int MaxConnections { get; init; } = 32;
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public int MaxWaiters { get; init; } = 128;
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public TimeSpan AdmissionTimeout { get; init; } = TimeSpan.FromSeconds(15);
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public int MaxBufferedRows { get; init; } = 10_000;
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public long MaxBufferedBytes { get; init; } = 16 * 1024 * 1024;
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public int MaxBatchRows { get; init; } = 256;
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public long MaxBatchBytes { get; init; } = 1024 * 1024;
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public long MaxFieldBytes { get; init; } = 8 * 1024 * 1024;
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public int MaxQueryNodes { get; init; } = 4096;
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public int MaxQueryDepth { get; init; } = 64;
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public int MaxParameters { get; init; } = 999;
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public long MaxParameterBytes { get; init; } = 4 * 1024 * 1024;
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public int MaxPreparedPlans { get; init; } = 128;
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public long MaxPreparedPlanBytes { get; init; } = 8 * 1024 * 1024;
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public TimeSpan CommandTimeout { get; init; } = TimeSpan.FromSeconds(30);
    }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public sealed class DatabaseCapabilities
    {
        internal DatabaseCapabilities() { }
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public DatabaseProvider Provider => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public string Profile => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public bool Supports(string capability) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public IReadOnlyList<string> Names => throw new NotSupportedException();
    }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public sealed class DataSourceBuilder
    {
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public DataSourceBuilder() { }
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public DataSourceBuilder ConfigureLimits(DatabaseLimits limits) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public DataSourceBuilder WithName(string name) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public DataSource Build() => throw new NotSupportedException();
    }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public sealed class DataSource : IDisposable, IAsyncDisposable
    {
        internal DataSource() { }
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public string Name => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public DatabaseProvider Provider => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public DatabaseCapabilities Capabilities => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public DatabaseLimits Limits => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public DatabaseAdministration Administration => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public DatabaseCloseResult Cleanup => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Task<DataSession> OpenSessionAsync(CancellationToken cancellationToken = default) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Task<bool> CanConnectAsync(CancellationToken cancellationToken = default) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Task<DatabaseCloseResult> CloseAsync(TimeSpan waitBudget, CancellationToken cancellationToken = default) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public void Dispose() => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public ValueTask DisposeAsync() => throw new NotSupportedException();
    }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public sealed class DataSession : IDisposable, IAsyncDisposable
    {
        internal DataSession() { }
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public DataSource Source => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public DataTransaction? Transaction => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public DatabaseCloseResult Cleanup => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Query<TEntity> From<TEntity>(Table<TEntity> table) where TEntity : class => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Task<long> ExecuteAsync(SqlCommand command, CancellationToken cancellationToken = default) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Task<T> ScalarAsync<T>(SqlCommand command, ValueCodec<T> codec, CancellationToken cancellationToken = default) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Task<IReadOnlyList<T>> QueryAsync<T>(SqlCommand command, Projection<T> projection, CancellationToken cancellationToken = default) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public IAsyncEnumerable<T> StreamAsync<T>(SqlCommand command, Projection<T> projection, CancellationToken cancellationToken = default) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Task<DataTransaction> BeginTransactionAsync(CancellationToken cancellationToken = default) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Task<DataTransaction> BeginTransactionAsync(TransactionOptions options, CancellationToken cancellationToken = default) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        /// <summary>Loads bounded related rows through a native relation query; never tracks them.</summary>
        public Task<IReadOnlyList<TChild>> LoadRelatedAsync<TParent, TChild>(EntityKey<TParent> parentKey, Relation<TParent, TChild> relation, CancellationToken cancellationToken = default) where TParent : class where TChild : class => throw new NotSupportedException();
        public Task<TEntity?> FindAsync<TEntity>(Table<TEntity> table, EntityKey<TEntity> key, CancellationToken cancellationToken = default) where TEntity : class => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Task<long> InsertAsync<TEntity>(Table<TEntity> table, TEntity entity, CancellationToken cancellationToken = default) where TEntity : class => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Task<T> InsertReturningAsync<TEntity, T>(Table<TEntity> table, TEntity entity, Projection<T> returning, CancellationToken cancellationToken = default) where TEntity : class => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Task<long> UpdateAsync<TEntity>(Table<TEntity> table, EntityKey<TEntity> key, Changes<TEntity> changes, CancellationToken cancellationToken = default) where TEntity : class => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Task<long> UpdateCheckedAsync<TEntity>(Table<TEntity> table, EntityKey<TEntity> key, Changes<TEntity> changes, ConcurrencyCheck<TEntity> concurrency, CancellationToken cancellationToken = default) where TEntity : class => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Task<long> DeleteAsync<TEntity>(Table<TEntity> table, EntityKey<TEntity> key, CancellationToken cancellationToken = default) where TEntity : class => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Task<long> DeleteCheckedAsync<TEntity>(Table<TEntity> table, EntityKey<TEntity> key, ConcurrencyCheck<TEntity> concurrency, CancellationToken cancellationToken = default) where TEntity : class => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Task<BulkResult> InsertManyAsync<TEntity>(Table<TEntity> table, IAsyncEnumerable<TEntity> rows, BulkOptions? options = null, CancellationToken cancellationToken = default) where TEntity : class => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Task<long> UpsertAsync<TEntity>(Table<TEntity> table, TEntity entity, ConflictTarget<TEntity> conflict, Changes<TEntity> update, CancellationToken cancellationToken = default) where TEntity : class => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Task<DatabaseCloseResult> CloseAsync(TimeSpan waitBudget, CancellationToken cancellationToken = default) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public void Dispose() => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public ValueTask DisposeAsync() => throw new NotSupportedException();
    }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public sealed class DataTransaction : IDisposable, IAsyncDisposable
    {
        internal DataTransaction() { }
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public TransactionOutcome Outcome => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public TransactionState State => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public bool CommitAttempted => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public string? RecoveryKey => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public DatabaseCloseResult Cleanup => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Task CommitAsync(CancellationToken admissionToken = default) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Task RollbackAsync(CancellationToken admissionToken = default) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Task<Savepoint> CreateSavepointAsync(CancellationToken cancellationToken = default) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Task<DatabaseCloseResult> CloseAsync(TimeSpan waitBudget, CancellationToken cancellationToken = default) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public void Dispose() => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public ValueTask DisposeAsync() => throw new NotSupportedException();
    }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public sealed class Savepoint : IAsyncDisposable
    {
        internal Savepoint() { }
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Task RollbackAsync(CancellationToken cancellationToken = default) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Task ReleaseAsync(CancellationToken cancellationToken = default) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public ValueTask DisposeAsync() => throw new NotSupportedException();
    }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public sealed class CommitOutcomeUnknownException : DatabaseException
    {
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public CommitOutcomeUnknownException(string message, string? recoveryKey, string? providerCode = null, ulong correlationId = 0) : base(message, DatabaseErrorKind.UnknownOutcome, providerCode, correlationId) { }
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public TransactionOutcome Outcome => TransactionOutcome.Unknown;
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public string? RecoveryKey => throw new NotSupportedException();
    }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public sealed class DatabaseCleanupException : DatabaseException
    {
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public DatabaseCleanupException(string message, DatabaseCloseResult cleanup) : base(message, DatabaseErrorKind.Provider) { }
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public DatabaseCloseResult Cleanup => throw new NotSupportedException();
    }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public enum BulkAtomicity { All, PerBatch }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public sealed record BulkOptions
    {
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public int BatchSize { get; init; } = 256;
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public BulkAtomicity Atomicity { get; init; } = BulkAtomicity.All;
    }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public sealed record BulkResult(long RowsAffected, int Batches, bool CommittedByOperation);
    /// <summary>Immutable bulk progress at the failure boundary; completed batches are distinct from uncertain current-batch effects.</summary>
    public sealed record BulkProgress(long RowsAffectedInCompletedBatches, int CompletedBatches, bool CompletedBatchesCommitted, TransactionOutcome CurrentTransactionOutcome);
    /// <summary>Reads bounded progress attached by InsertManyAsync without wrapping or replacing the original exception.</summary>
    public static class BulkFailure
    {
        /// <summary>Returns false for an exception not produced by an admitted bulk operation; never scans inner exceptions.</summary>
        public static bool TryGetProgress(Exception exception, [NotNullWhen(true)] out BulkProgress? progress) => throw new NotSupportedException();
    }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public sealed class ConflictTarget<TEntity> where TEntity : class
    {
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public ConflictTarget(string constraintName) { }
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public static ConflictTarget<TEntity> Columns<T>(Column<TEntity, T> column) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public ConflictTarget<TEntity> And<T>(Column<TEntity, T> column) => throw new NotSupportedException();
    }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public enum MigrationTransactionMode { Transactional, NonTransactional }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public sealed record Migration(long Version, string Description, string Sql, MigrationTransactionMode TransactionMode = MigrationTransactionMode.Transactional);
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public sealed class MigrationBundle
    {
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public MigrationBundle(DatabaseProvider provider, IReadOnlyList<Migration> migrations) { }
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public string ContentHash => throw new NotSupportedException();
    }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public sealed record MigrationOptions
    {
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public long? TargetVersion { get; init; }
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public TimeSpan LockTimeout { get; init; } = TimeSpan.FromSeconds(30);
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public bool AllowNonTransactional { get; init; }
    }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public sealed record MigrationStatus(long Version, string Description, string Checksum, bool Applied);
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public sealed record MigrationReport(int AppliedCount, long? CurrentVersion, bool Completed);
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public sealed record SchemaColumn(string Name, string StoreType, bool IsNullable, bool IsPrimaryKey);
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public sealed record SchemaTable(string? Schema, string Name, IReadOnlyList<SchemaColumn> Columns);
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public sealed class DatabaseAdministration
    {
        internal DatabaseAdministration() { }
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Task<MigrationReport> MigrateAsync(MigrationBundle bundle, MigrationOptions? options = null, CancellationToken cancellationToken = default) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Task<IReadOnlyList<MigrationStatus>> GetMigrationStatusAsync(MigrationBundle bundle, CancellationToken cancellationToken = default) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Task ValidateMigrationsAsync(MigrationBundle bundle, CancellationToken cancellationToken = default) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Task<IReadOnlyList<SchemaTable>> GetTablesAsync(string? schema = null, CancellationToken cancellationToken = default) => throw new NotSupportedException();
    }
}

namespace NativeWeave.Database.Sqlite
{
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public enum SqliteOpenMode { ReadWriteCreate, ReadWrite, ReadOnly, Memory }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public enum SqliteJournalMode { Wal, Delete, Memory }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public enum SqliteBeginMode { Deferred, Immediate }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public enum SqliteSynchronousMode { Normal, Full }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public sealed class SqliteOptions
    {
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public SqliteOpenMode Mode { get; set; } = SqliteOpenMode.ReadWriteCreate;
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public SqliteJournalMode JournalMode { get; set; } = SqliteJournalMode.Wal;
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public SqliteSynchronousMode Synchronous { get; set; } = SqliteSynchronousMode.Full;
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public SqliteBeginMode BeginMode { get; set; } = SqliteBeginMode.Deferred;
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public TimeSpan BusyTimeout { get; set; } = TimeSpan.FromSeconds(5);
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public bool ForeignKeys { get; set; } = true;
    }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public static class SqliteDataSource
    {
        /// <summary>Package descriptor for optional preflight; ordinary Create performs negotiation automatically.</summary>
        public static NativeWeave.Interop.EngineDescriptor Engine => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public static DataSource Create(string path, Action<SqliteOptions>? configure = null) => throw new NotSupportedException();
    }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public static class SqliteDataSourceBuilderExtensions
    {
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public static DataSourceBuilder UseSqlite(this DataSourceBuilder builder, string path, Action<SqliteOptions>? configure = null) => throw new NotSupportedException();
    }
}

namespace NativeWeave.Database.PostgreSql
{
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public enum PostgreSqlTlsMode { VerifyFull, DisableForLocalDevelopment }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public sealed class PostgreSqlOptions
    {
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public PostgreSqlTlsMode TlsMode { get; set; } = PostgreSqlTlsMode.VerifyFull;
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public string? RootCertificatePath { get; set; }
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public string ApplicationName { get; set; } = "NativeWeave";
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public TimeSpan ConnectTimeout { get; set; } = TimeSpan.FromSeconds(15);
    }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public static class PostgreSqlDataSource
    {
        /// <summary>Package descriptor for optional preflight; ordinary Create performs negotiation automatically.</summary>
        public static NativeWeave.Interop.EngineDescriptor Engine => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public static DataSource Create(string connectionString, Action<PostgreSqlOptions>? configure = null) => throw new NotSupportedException();
    }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public static class PostgreSqlDataSourceBuilderExtensions
    {
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public static DataSourceBuilder UsePostgreSql(this DataSourceBuilder builder, string connectionString, Action<PostgreSqlOptions>? configure = null) => throw new NotSupportedException();
    }
}

namespace NativeWeave.Query
{
    using NativeWeave.Data;
    using NativeWeave.Database;
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public enum SortDirection { Ascending, Descending }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public enum NullOrder { First, Last }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public enum SetOperation { Union, UnionAll, Intersect, Except }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public enum FrameBoundary { UnboundedPreceding, CurrentRow, UnboundedFollowing }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public enum RowLockMode { Update, Share, NoKeyUpdate, KeyShare }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public enum LockWait { Wait, NoWait, SkipLocked }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public readonly struct SqlPredicate
    {
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public SqlPredicate And(SqlPredicate other) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public SqlPredicate Or(SqlPredicate other) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public SqlPredicate Not() => throw new NotSupportedException();
    }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public readonly struct SqlExpression<T>
    {
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public SqlPredicate Equal(T value) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public SqlPredicate Equal(SqlExpression<T> other) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public SqlPredicate NotEqual(T value) => throw new NotSupportedException();
        /// <summary>Compares compatible same-owner native expressions using SQL semantics.</summary>
        public SqlPredicate NotEqual(SqlExpression<T> other) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public SqlPredicate GreaterThan(T value) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public SqlPredicate GreaterThan(SqlExpression<T> other) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public SqlPredicate GreaterThanOrEqual(T value) => throw new NotSupportedException();
        /// <summary>Compares compatible same-owner native expressions using SQL semantics.</summary>
        public SqlPredicate GreaterThanOrEqual(SqlExpression<T> other) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public SqlPredicate LessThan(T value) => throw new NotSupportedException();
        /// <summary>Compares compatible same-owner native expressions using SQL semantics.</summary>
        public SqlPredicate LessThan(SqlExpression<T> other) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public SqlPredicate LessThanOrEqual(T value) => throw new NotSupportedException();
        /// <summary>Compares compatible same-owner native expressions using SQL semantics.</summary>
        public SqlPredicate LessThanOrEqual(SqlExpression<T> other) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public SqlPredicate Between(T lower, T upper) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public SqlPredicate IsNull() => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public SqlPredicate IsNotNull() => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public SqlPredicate NullSafeEqual(T value) => throw new NotSupportedException();
        /// <summary>Compares compatible same-owner native expressions using SQL semantics.</summary>
        public SqlPredicate NullSafeEqual(SqlExpression<T> other) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public SqlPredicate In(ReadOnlySpan<T> values) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public SqlPredicate NotIn(ReadOnlySpan<T> values) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public SqlPredicate In(QuerySelection<T> subquery) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public SqlExpression<T> Over(WindowDefinition window) => throw new NotSupportedException();
    }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    /// <summary>Typed numeric operators; Rust owns overflow and provider semantics.</summary>
    public static class SqlArithmeticExtensions
    {
        /// <summary>Calls the native numeric add operation.</summary>
        public static SqlExpression<T> Add<T>(this SqlExpression<T> expression, T value) where T : INumber<T> => throw new NotSupportedException();
        /// <summary>Applies native numeric arithmetic to compatible expressions in the same query.</summary>
        public static SqlExpression<T> Add<T>(this SqlExpression<T> expression, SqlExpression<T> value) where T : INumber<T> => throw new NotSupportedException();
        /// <summary>Applies native arithmetic while preserving SQL NULL propagation.</summary>
        public static SqlExpression<T?> Add<T>(this SqlExpression<T?> expression, T value) where T : struct, INumber<T> => throw new NotSupportedException();
        /// <summary>Applies native arithmetic to nullable expressions while preserving SQL NULL propagation.</summary>
        public static SqlExpression<T?> Add<T>(this SqlExpression<T?> expression, SqlExpression<T?> value) where T : struct, INumber<T> => throw new NotSupportedException();
        /// <summary>Calls the native numeric subtract operation.</summary>
        public static SqlExpression<T> Subtract<T>(this SqlExpression<T> expression, T value) where T : INumber<T> => throw new NotSupportedException();
        /// <summary>Applies native numeric arithmetic to compatible expressions in the same query.</summary>
        public static SqlExpression<T> Subtract<T>(this SqlExpression<T> expression, SqlExpression<T> value) where T : INumber<T> => throw new NotSupportedException();
        /// <summary>Applies native arithmetic while preserving SQL NULL propagation.</summary>
        public static SqlExpression<T?> Subtract<T>(this SqlExpression<T?> expression, T value) where T : struct, INumber<T> => throw new NotSupportedException();
        /// <summary>Applies native arithmetic to nullable expressions while preserving SQL NULL propagation.</summary>
        public static SqlExpression<T?> Subtract<T>(this SqlExpression<T?> expression, SqlExpression<T?> value) where T : struct, INumber<T> => throw new NotSupportedException();
        /// <summary>Calls the native numeric multiply operation.</summary>
        public static SqlExpression<T> Multiply<T>(this SqlExpression<T> expression, T value) where T : INumber<T> => throw new NotSupportedException();
        /// <summary>Applies native numeric arithmetic to compatible expressions in the same query.</summary>
        public static SqlExpression<T> Multiply<T>(this SqlExpression<T> expression, SqlExpression<T> value) where T : INumber<T> => throw new NotSupportedException();
        /// <summary>Applies native arithmetic while preserving SQL NULL propagation.</summary>
        public static SqlExpression<T?> Multiply<T>(this SqlExpression<T?> expression, T value) where T : struct, INumber<T> => throw new NotSupportedException();
        /// <summary>Applies native arithmetic to nullable expressions while preserving SQL NULL propagation.</summary>
        public static SqlExpression<T?> Multiply<T>(this SqlExpression<T?> expression, SqlExpression<T?> value) where T : struct, INumber<T> => throw new NotSupportedException();
        /// <summary>Calls the native numeric divide operation.</summary>
        public static SqlExpression<T> Divide<T>(this SqlExpression<T> expression, T value) where T : INumber<T> => throw new NotSupportedException();
        /// <summary>Applies native numeric arithmetic to compatible expressions in the same query.</summary>
        public static SqlExpression<T> Divide<T>(this SqlExpression<T> expression, SqlExpression<T> value) where T : INumber<T> => throw new NotSupportedException();
        /// <summary>Applies native arithmetic while preserving SQL NULL propagation.</summary>
        public static SqlExpression<T?> Divide<T>(this SqlExpression<T?> expression, T value) where T : struct, INumber<T> => throw new NotSupportedException();
        /// <summary>Applies native arithmetic to nullable expressions while preserving SQL NULL propagation.</summary>
        public static SqlExpression<T?> Divide<T>(this SqlExpression<T?> expression, SqlExpression<T?> value) where T : struct, INumber<T> => throw new NotSupportedException();
    }
    public static class SqlStringExtensions
    {
        /// <summary>Explicit nullable-text operation with the same SQL UNKNOWN and escaping rules.</summary>
        public static SqlPredicate ContainsNullableLiteral(this SqlExpression<string?> expression, string value) => throw new NotSupportedException();
        /// <summary>Explicit nullable-text pattern operation; no .NET culture comparison is implied.</summary>
        public static SqlPredicate LikeNullable(this SqlExpression<string?> expression, string pattern, char escape = '\\') => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public static SqlPredicate ContainsLiteral(this SqlExpression<string> expression, string value) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public static SqlPredicate StartsWithLiteral(this SqlExpression<string> expression, string value) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public static SqlPredicate EndsWithLiteral(this SqlExpression<string> expression, string value) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public static SqlPredicate Like(this SqlExpression<string> expression, string pattern, char escape = '\\') => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public static SqlExpression<string> Collate(this SqlExpression<string> expression, string collation) => throw new NotSupportedException();
    }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public readonly struct QueryRow<TEntity> where TEntity : class
    {
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public SqlExpression<T> Get<T>(Column<TEntity, T> column) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public SqlPredicate Equal<T>(Column<TEntity, T> column, T value) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public SqlPredicate GreaterThanOrEqual<T>(Column<TEntity, T> column, T value) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public SqlPredicate IsNull<T>(Column<TEntity, T> column) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public SqlPredicate IsNotNull<T>(Column<TEntity, T> column) => throw new NotSupportedException();
    }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public readonly struct JoinPredicate<TLeft, TRight> where TLeft : class where TRight : class
    {
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public SqlExpression<T> Left<T>(Column<TLeft, T> column) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public SqlExpression<T> Right<T>(Column<TRight, T> column) => throw new NotSupportedException();
    }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public readonly struct JoinedTable<TEntity> where TEntity : class { }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public readonly struct LeftJoinedTable<TEntity> where TEntity : class { }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public readonly struct QueryParameter<T> { }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public sealed class QueryParameters
    {
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public QueryParameters() { }
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public QueryParameters Set<T>(QueryParameter<T> parameter, T value) => throw new NotSupportedException();
    }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public sealed class ProjectionBuilder<T>
    {
        internal ProjectionBuilder() { }
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public ResultColumn<TValue> Add<TValue>(SqlExpression<TValue> expression, string alias) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Projection<T> Build(RowMaterializer<T> materializer) => throw new NotSupportedException();
    }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public sealed class Query<TEntity> : IDisposable where TEntity : class
    {
        internal Query() { }
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public QueryRow<TEntity> Row => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Query<TEntity> Where(SqlPredicate predicate) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Query<TEntity> Where(Func<QueryRow<TEntity>, SqlPredicate> predicate) => throw new NotSupportedException();
        /// <summary>Invokes and appends the predicate only when condition is true; no query work occurs for a false condition.</summary>
        public Query<TEntity> WhereIf(bool condition, Func<QueryRow<TEntity>, SqlPredicate> predicate) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Query<TEntity> WhereEqual<T>(Column<TEntity, T> column, T value) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Query<TEntity> WhereGreaterThanOrEqual<T>(Column<TEntity, T> column, T value) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Query<TEntity> WhereIsNull<T>(Column<TEntity, T> column) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Query<TEntity> WhereIsNotNull<T>(Column<TEntity, T> column) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public SqlExpression<T> Column<T>(Column<TEntity, T> column) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public SqlExpression<T> Column<TJoin, T>(JoinedTable<TJoin> table, Column<TJoin, T> column) where TJoin : class => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public SqlExpression<T?> NullableValue<TJoin, T>(LeftJoinedTable<TJoin> table, Column<TJoin, T> column) where TJoin : class where T : struct => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public SqlExpression<T?> NullableValue<TJoin, T>(LeftJoinedTable<TJoin> table, Column<TJoin, T?> column) where TJoin : class where T : struct => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public SqlExpression<T?> NullableReference<TJoin, T>(LeftJoinedTable<TJoin> table, Column<TJoin, T> column) where TJoin : class where T : class? => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public SqlPredicate HasMatch<TJoin>(LeftJoinedTable<TJoin> table) where TJoin : class => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public JoinedTable<TJoin> InnerJoin<TJoin>(Table<TJoin> table, string alias, Func<JoinPredicate<TEntity, TJoin>, SqlPredicate> on) where TJoin : class => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public LeftJoinedTable<TJoin> LeftJoin<TJoin>(Table<TJoin> table, string alias, Func<JoinPredicate<TEntity, TJoin>, SqlPredicate> on) where TJoin : class => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Query<TEntity> OrderBy<T>(Column<TEntity, T> column, SortDirection direction = SortDirection.Ascending, NullOrder nullOrder = NullOrder.Last) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Query<TEntity> OrderBy<T>(SqlExpression<T> expression, SortDirection direction = SortDirection.Ascending, NullOrder nullOrder = NullOrder.Last) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Query<TEntity> ThenBy<T>(Column<TEntity, T> column, SortDirection direction = SortDirection.Ascending, NullOrder nullOrder = NullOrder.Last) => throw new NotSupportedException();
        /// <summary>Appends a same-query expression ordering after an existing OrderBy.</summary>
        public Query<TEntity> ThenBy<T>(SqlExpression<T> expression, SortDirection direction = SortDirection.Ascending, NullOrder nullOrder = NullOrder.Last) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Query<TEntity> GroupBy<T>(SqlExpression<T> expression) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Query<TEntity> Having(SqlPredicate predicate) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Query<TEntity> Distinct() => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Query<TEntity> Take(int count) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Query<TEntity> Skip(int count) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Query<TEntity> SeekAfter<T>(Column<TEntity, T> uniqueOrderKey, T value) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Query<TEntity> WithTimeout(TimeSpan timeout) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Query<TEntity> With<TCte>(CommonTable<TCte> commonTable) where TCte : class => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Query<TEntity> ForUpdate(RowLockMode mode = RowLockMode.Update, LockWait wait = LockWait.Wait) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public SqlExpression<T> Value<T>(T value, ValueCodec<T> codec) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public QueryParameter<T> Parameter<T>(string name, ValueCodec<T> codec) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public SqlExpression<T> ParameterValue<T>(QueryParameter<T> parameter) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public SqlPredicate Exists<T>(QuerySelection<T> subquery) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public SqlExpression<long> CountRows() => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public WindowDefinition Window() => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public ProjectionBuilder<T> Projection<T>() => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public QuerySelection<T> Select<T>(Projection<T> projection) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public QuerySelection<T> Select<T>(SqlExpression<T> expression) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public QuerySelection<TOut> Select<T1, T2, TOut>(SqlExpression<T1> first, SqlExpression<T2> second, Func<T1, T2, TOut> materializer) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public QuerySelection<TEntity> SelectAll() => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Task<long> CountAsync(CancellationToken cancellationToken = default) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Task<bool> AnyAsync(CancellationToken cancellationToken = default) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Task<long> UpdateAsync(Changes<TEntity> changes, CancellationToken cancellationToken = default) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Task<long> UpdateAsync(Action<UpdateSetters<TEntity>> setters, CancellationToken cancellationToken = default) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Task<long> DeleteAsync(CancellationToken cancellationToken = default) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Query<TEntity> Clone() => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public void Dispose() => throw new NotSupportedException();
    }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public sealed class UpdateSetters<TEntity> where TEntity : class
    {
        internal UpdateSetters() { }
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public UpdateSetters<TEntity> Set<T>(Column<TEntity, T> column, T value) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public UpdateSetters<TEntity> Set<T>(Column<TEntity, T> column, SqlExpression<T> value) => throw new NotSupportedException();
    }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public readonly struct QuerySelection<T>
    {
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public QuerySelection<T> Combine(QuerySelection<T> other, SetOperation operation = SetOperation.UnionAll) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Task<IReadOnlyList<T>> ToListAsync(CancellationToken cancellationToken = default) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Task<T[]> ToArrayAsync(CancellationToken cancellationToken = default) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Task<T> FirstAsync(CancellationToken cancellationToken = default) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Task<T?> FirstOrDefaultAsync(CancellationToken cancellationToken = default) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Task<T> SingleAsync(CancellationToken cancellationToken = default) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Task<T?> SingleOrDefaultAsync(CancellationToken cancellationToken = default) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public IAsyncEnumerable<T> AsAsyncEnumerable(CancellationToken cancellationToken = default) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public PreparedQuery<T> Prepare() => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public string ToSql() => throw new NotSupportedException();
    }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public sealed class PreparedQuery<T> : IDisposable
    {
        internal PreparedQuery() { }
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public Task<IReadOnlyList<T>> ToListAsync(DataSession session, QueryParameters? parameters = null, CancellationToken cancellationToken = default) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public IAsyncEnumerable<T> AsAsyncEnumerable(DataSession session, QueryParameters? parameters = null, CancellationToken cancellationToken = default) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public void Dispose() => throw new NotSupportedException();
    }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public sealed class CommonTable<T> : IDisposable where T : class
    {
        private CommonTable() { }
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public static CommonTable<T> Create(Table<T> declaredShape, QuerySelection<T> body, bool recursive = false) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public void Dispose() => throw new NotSupportedException();
    }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public sealed class WindowDefinition
    {
        internal WindowDefinition() { }
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public WindowDefinition PartitionBy<T>(SqlExpression<T> expression) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public WindowDefinition OrderBy<T>(SqlExpression<T> expression, SortDirection direction = SortDirection.Ascending, NullOrder nullOrder = NullOrder.Last) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public WindowDefinition RowsBetween(FrameBoundary start, FrameBoundary end) => throw new NotSupportedException();
    }
    /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
    public static class SqlFunctions
    {
        /// <summary>Produces a non-null scalar by a native SQL COALESCE.</summary>
        public static SqlExpression<T> Coalesce<T>(SqlExpression<T?> expression, T fallback) where T : struct => throw new NotSupportedException();
        /// <summary>Produces a non-null reference scalar by a native SQL COALESCE.</summary>
        public static SqlExpression<T> CoalesceReference<T>(SqlExpression<T?> expression, T fallback) where T : class => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public static SqlExpression<long> Count<T>(SqlExpression<T> expression, bool distinct = false) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public static SqlExpression<long?> Sum(SqlExpression<int> expression) => throw new NotSupportedException();
        /// <summary>Aggregates non-null inputs natively and returns SQL NULL when none remain.</summary>
        public static SqlExpression<long?> Sum(SqlExpression<int?> expression) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public static SqlExpression<long?> Sum(SqlExpression<long> expression) => throw new NotSupportedException();
        /// <summary>Aggregates non-null inputs natively and returns SQL NULL when none remain.</summary>
        public static SqlExpression<long?> Sum(SqlExpression<long?> expression) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public static SqlExpression<decimal?> Sum(SqlExpression<decimal> expression) => throw new NotSupportedException();
        /// <summary>Aggregates non-null inputs natively and returns SQL NULL when none remain.</summary>
        public static SqlExpression<decimal?> Sum(SqlExpression<decimal?> expression) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public static SqlExpression<double?> Sum(SqlExpression<double> expression) => throw new NotSupportedException();
        /// <summary>Aggregates non-null inputs natively and returns SQL NULL when none remain.</summary>
        public static SqlExpression<double?> Sum(SqlExpression<double?> expression) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public static SqlExpression<double?> Average(SqlExpression<int> expression) => throw new NotSupportedException();
        /// <summary>Aggregates non-null inputs natively and returns SQL NULL when none remain.</summary>
        public static SqlExpression<double?> Average(SqlExpression<int?> expression) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public static SqlExpression<decimal?> Average(SqlExpression<decimal> expression) => throw new NotSupportedException();
        /// <summary>Aggregates non-null inputs natively and returns SQL NULL when none remain.</summary>
        public static SqlExpression<decimal?> Average(SqlExpression<decimal?> expression) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public static SqlExpression<T?> Min<T>(SqlExpression<T> expression) where T : struct => throw new NotSupportedException();
        /// <summary>Returns the native minimum non-null value or SQL NULL.</summary>
        public static SqlExpression<T?> Min<T>(SqlExpression<T?> expression) where T : struct => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public static SqlExpression<T?> Max<T>(SqlExpression<T> expression) where T : struct => throw new NotSupportedException();
        /// <summary>Returns the native maximum non-null value or SQL NULL.</summary>
        public static SqlExpression<T?> Max<T>(SqlExpression<T?> expression) where T : struct => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public static SqlExpression<string?> MinText(SqlExpression<string> expression) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public static SqlExpression<string?> MaxText(SqlExpression<string> expression) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        /// <summary>Uses the documented provider numeric result conversion and preserves empty-set NULL.</summary>
        public static SqlExpression<double?> Sum(SqlExpression<float> expression) => throw new NotSupportedException();
        /// <summary>Uses the documented provider numeric result conversion and preserves empty-set NULL.</summary>
        public static SqlExpression<double?> Sum(SqlExpression<float?> expression) => throw new NotSupportedException();
        /// <summary>Uses the documented provider numeric result conversion and preserves empty-set NULL.</summary>
        public static SqlExpression<double?> Average(SqlExpression<long> expression) => throw new NotSupportedException();
        /// <summary>Uses the documented provider numeric result conversion and preserves empty-set NULL.</summary>
        public static SqlExpression<double?> Average(SqlExpression<long?> expression) => throw new NotSupportedException();
        /// <summary>Uses the documented provider numeric result conversion and preserves empty-set NULL.</summary>
        public static SqlExpression<double?> Average(SqlExpression<double> expression) => throw new NotSupportedException();
        /// <summary>Uses the documented provider numeric result conversion and preserves empty-set NULL.</summary>
        public static SqlExpression<double?> Average(SqlExpression<double?> expression) => throw new NotSupportedException();
        /// <summary>Uses the documented provider numeric result conversion and preserves empty-set NULL.</summary>
        public static SqlExpression<double?> Average(SqlExpression<float> expression) => throw new NotSupportedException();
        /// <summary>Uses the documented provider numeric result conversion and preserves empty-set NULL.</summary>
        public static SqlExpression<double?> Average(SqlExpression<float?> expression) => throw new NotSupportedException();
        /// <summary>Returns the provider-collated minimum of nullable text inputs.</summary>
        public static SqlExpression<string?> MinNullableText(SqlExpression<string?> expression) => throw new NotSupportedException();
        /// <summary>Returns the provider-collated maximum of nullable text inputs.</summary>
        public static SqlExpression<string?> MaxNullableText(SqlExpression<string?> expression) => throw new NotSupportedException();
        public static SqlExpression<long> RowNumber(WindowDefinition window) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public static SqlExpression<long> Rank(WindowDefinition window) => throw new NotSupportedException();
        /// <summary>Design declaration; normative behavior, ownership, errors, availability, and costs are specified in docs/api/database.md.</summary>
        public static SqlExpression<T> Case<T>(SqlPredicate condition, SqlExpression<T> whenTrue, SqlExpression<T> whenFalse) => throw new NotSupportedException();
    }
}

namespace Microsoft.Extensions.DependencyInjection
{
    /// <summary>Optional NativeWeave.Database.DependencyInjection package; does not register sessions implicitly.</summary>
    public static class NativeWeaveDatabaseServiceCollectionExtensions
    {
        /// <summary>Registers one container-owned singleton data source using the ordinary builder.</summary>
        public static IServiceCollection AddNativeWeaveDatabase(this IServiceCollection services, Action<NativeWeave.Database.DataSourceBuilder> configure) => throw new NotSupportedException();
        /// <summary>Registers a container-owned keyed singleton; use standard GetRequiredKeyedService.</summary>
        public static IServiceCollection AddKeyedNativeWeaveDatabase(this IServiceCollection services, string name, Action<NativeWeave.Database.DataSourceBuilder> configure) => throw new NotSupportedException();
    }
}
