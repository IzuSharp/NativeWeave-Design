// Compile-only consumer scenarios. Database calls intentionally cannot execute against design stubs.
#nullable enable
using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.DependencyInjection;
using NativeWeave.Data;
using NativeWeave.Database;
using NativeWeave.Database.Sqlite;
using NativeWeave.Query;

namespace NativeWeave.Api.Consumers;

[WeaveTable("students", DescriptorName = "Students")]
public sealed partial record Student([property: WeaveKey] long Id, string Name, int Age, string? Email, [property: WeaveVersion] long Version);
public sealed record Enrollment(long Id, long StudentId, int Credits);
public sealed record StudentCredits(long StudentId, long EnrollmentCount);

// Explicit handwritten equivalent of the specified generator output. This does not claim a generator ran.
public static class Students
{
    private static readonly TableBuilder<Student> Builder = new("students");
    public static readonly Column<Student, long> Id = Builder.Column("id", Codecs.Int64, new ColumnOptions { IsPrimaryKey = true });
    public static readonly Column<Student, string> Name = Builder.Column("name", Codecs.String);
    public static readonly Column<Student, int> Age = Builder.Column("age", Codecs.Int32);
    public static readonly Column<Student, string?> Email = Builder.Column("email", Codecs.NullableReference(Codecs.String));
    public static readonly Column<Student, long> Version = Builder.Column("version", Codecs.Int64, new ColumnOptions { IsConcurrencyToken = true });
    public static readonly Table<Student> Table = Builder.Build(
        static row => new Student(row.Get(Id), row.Get(Name), row.Get(Age), row.Get(Email), row.Get(Version)),
        static (row, value) => { row.Set(Id, value.Id); row.Set(Name, value.Name); row.Set(Age, value.Age); row.Set(Email, value.Email); row.Set(Version, value.Version); });
    public static Projection<Student> Row => Table.Row;
}
public static class Enrollments
{
    private static readonly TableBuilder<Enrollment> Builder = new("enrollments");
    public static readonly Column<Enrollment, long> Id = Builder.Column("id", Codecs.Int64, new ColumnOptions { IsPrimaryKey = true });
    public static readonly Column<Enrollment, long> StudentId = Builder.Column("student_id", Codecs.Int64);
    public static readonly Column<Enrollment, int> Credits = Builder.Column("credits", Codecs.Int32);
    public static readonly Table<Enrollment> Table = Builder.Build(
        static row => new Enrollment(row.Get(Id), row.Get(StudentId), row.Get(Credits)),
        static (row, value) => { row.Set(Id, value.Id); row.Set(StudentId, value.StudentId); row.Set(Credits, value.Credits); });
}
public static class DatabaseExamples
{
    public static async Task<IReadOnlyList<Student>> MinimalAsync(CancellationToken cancellationToken)
    {
        await using var source = SqliteDataSource.Create("students.db");
        await using var session = await source.OpenSessionAsync(cancellationToken);
        using var query = session.From(Students.Table);
        return await query.WhereGreaterThanOrEqual(Students.Age, 18).OrderBy(Students.Id).Take(100).SelectAll().ToListAsync(cancellationToken);
    }
    public static async Task StreamAsync(DataSource source, Func<Student, Task> consume, CancellationToken cancellationToken)
    {
        await using var session = await source.OpenSessionAsync(cancellationToken);
        using var query = session.From(Students.Table);
        query.Where(row => row.GreaterThanOrEqual(Students.Age, 18).And(row.IsNotNull(Students.Email))).OrderBy(Students.Id);
        await foreach (var student in query.SelectAll().AsAsyncEnumerable().WithCancellation(cancellationToken))
            await consume(student);
    }
    public static async Task<IReadOnlyList<StudentCredits>> JoinAsync(DataSession session, CancellationToken cancellationToken)
    {
        using var query = session.From(Students.Table);
        var enrollments = query.LeftJoin(Enrollments.Table, "e", on => on.Left(Students.Id).Equal(on.Right(Enrollments.StudentId)));
        var id = query.Column(Students.Id);
        var count = SqlFunctions.Count(query.NullableValue(enrollments, Enrollments.Id));
        query.GroupBy(id).OrderBy(Students.Id);
        return await query.Select(id, count, static (studentId, enrollmentCount) => new StudentCredits(studentId, enrollmentCount)).ToListAsync(cancellationToken);
    }
    public static async Task ChangeAsync(DataSession session, Student student, CancellationToken requestToken)
    {
        await using var transaction = await session.BeginTransactionAsync(new TransactionOptions { RecoveryKey = $"student/{student.Id}/{student.Version}" }, requestToken);
        var changes = new Changes<Student>().Set(Students.Email, (string?)null).Set(Students.Version, checked(student.Version + 1));
        var expected = new ConcurrencyCheck<Student>().Expect(Students.Version, student.Version);
        await session.UpdateCheckedAsync(Students.Table, Students.Table.Key(Students.Id, student.Id), changes, expected, requestToken);
        await transaction.CommitAsync(requestToken);
        // CommitOutcomeUnknownException must enter application recovery with the same idempotency identity.
    }
    public static async Task<IReadOnlyList<Student>> PreparedAsync(DataSession session, CancellationToken cancellationToken)
    {
        using var query = session.From(Students.Table);
        var age = query.Parameter("minimum_age", Codecs.Int32);
        query.Where(query.Column(Students.Age).GreaterThan(query.ParameterValue(age))).OrderBy(Students.Id).Take(50);
        using var prepared = query.SelectAll().Prepare();
        return await prepared.ToListAsync(session, new QueryParameters().Set(age, 18), cancellationToken);
    }
    public static IServiceCollection Register(IServiceCollection services)
        => services.AddNativeWeaveDatabase(builder => builder.UseSqlite("students.db").ConfigureLimits(new DatabaseLimits { MaxConnections = 4 }));
}
