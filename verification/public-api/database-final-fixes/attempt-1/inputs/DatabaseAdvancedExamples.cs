// Design-compilation scenarios only. No database behavior executes against declaration stubs.
#nullable enable
using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using NativeWeave.Data;
using NativeWeave.Database;
using NativeWeave.Query;

namespace NativeWeave.Api.Consumers;

public sealed record AdultStudent(long Id);
public sealed record StudentRank(long Id, long Rank);
public static class AdultStudents
{
    private static readonly TableBuilder<AdultStudent> Builder = new("adult_students");
    public static readonly Column<AdultStudent, long> Id = Builder.Column("id", Codecs.Int64, new ColumnOptions { IsPrimaryKey = true });
    public static readonly Table<AdultStudent> Table = Builder.Build(static r => new AdultStudent(r.Get(Id)), static (r, v) => r.Set(Id, v.Id));
}
public static class DatabaseAdvancedExamples
{
    public static async Task<IReadOnlyList<StudentCredits>> OptionalForeignKeyJoinAsync(DataSession session, CancellationToken token)
    {
        using var query = session.From(Students.Table);
        var enrollment = query.LeftJoin(OptionalEnrollments.Table, "optional_enrollment",
            on => on.Left(Students.Id).AsNullable().Equal(on.Right(OptionalEnrollments.StudentId)));
        var id = query.Column(Students.Id);
        var count = SqlFunctions.Count(query.NullableValue(enrollment, OptionalEnrollments.Id));
        query.GroupBy(id).OrderBy(Students.Id);
        return await query.Select(id, count, static (studentId, enrollmentCount) => new StudentCredits(studentId, enrollmentCount)).ToListAsync(token);
    }
    public static Task<IReadOnlyList<OptionalEnrollment>> RelatedAsync(DataSession session, long studentId, CancellationToken token)
        => session.LoadRelatedAsync(Students.Table.Key(Students.Id, studentId), OptionalEnrollments.StudentRelation, token);

    public static Task<IReadOnlyList<Student>> DynamicAsync(DataSession session, Query<Student> query, int? minimumAge, string? email, CancellationToken token)
    {
        // Ordinary control flow and native-backed proxies; no expression compilation.
        query.WhereIf(minimumAge.HasValue, row => row.GreaterThanOrEqual(Students.Age, minimumAge.GetValueOrDefault()));
        if (email is not null) query.Where(query.Column(Students.Email).ContainsNullableLiteral(email));
        if (Students.Table.TryGetColumn("age", Codecs.Int32, out var age)) query.OrderBy(age).ThenBy(query.Column(Students.Id));
        return query.SelectAll().ToListAsync(token);
    }
    public static async Task<IReadOnlyList<long?>> NullableAggregateAsync(DataSession session, CancellationToken token)
    {
        using var query = session.From(Students.Table);
        var enrollment = query.LeftJoin(Enrollments.Table, "enrollment", on => on.Left(Students.Id).Equal(on.Right(Enrollments.StudentId)));
        var credits = query.NullableValue(enrollment, Enrollments.Credits);
        query.GroupBy(query.Column(Students.Id));
        // Overloads preserve SQL NULL for unmatched/all-null groups.
        return await query.Select(SqlFunctions.Sum(credits.Add(1))).ToListAsync(token);
    }
    public static async Task<IReadOnlyList<StudentRank>> WindowAsync(DataSession session, CancellationToken token)
    {
        using var query = session.From(Students.Table);
        var order = query.Window().OrderBy(query.Column(Students.Id)).RowsBetween(FrameBoundary.UnboundedPreceding, FrameBoundary.CurrentRow);
        return await query.Select(query.Column(Students.Id), SqlFunctions.RowNumber(order), static (id, rank) => new StudentRank(id, rank)).ToListAsync(token);
    }
    public static async Task<IReadOnlyList<AdultStudent>> CommonTableAsync(DataSession session, CancellationToken token)
    {
        using var body = session.From(Students.Table);
        body.WhereGreaterThanOrEqual(Students.Age, 18);
        var projection = body.Projection<AdultStudent>();
        var id = projection.Add(body.Column(Students.Id), "id");
        using var cte = CommonTable<AdultStudent>.Create(AdultStudents.Table, body.Select(projection.Build(row => new AdultStudent(row.Get(id)))));
        using var query = session.From(AdultStudents.Table);
        return await query.With(cte).OrderBy(AdultStudents.Id).SelectAll().ToListAsync(token);
    }
    public static async Task<long> SetBasedAsync(DataSession session, CancellationToken token)
    {
        using var query = session.From(Students.Table);
        query.WhereGreaterThanOrEqual(Students.Age, 18);
        var nextAge = query.Column(Students.Age).Add(1);
        return await query.UpdateAsync(setters => setters.Set(Students.Age, nextAge), token);
    }
    public static async Task SavepointAsync(DataSession session, CancellationToken token)
    {
        await using var tx = await session.BeginTransactionAsync(token);
        await using (var savepoint = await tx.CreateSavepointAsync(token))
        {
            // Native savepoint scopes never commit the outer transaction.
            await savepoint.RollbackAsync(token);
            await savepoint.ReleaseAsync(token);
        }
        await tx.CommitAsync(token);
    }
    public static async Task<BulkResult> BulkAsync(DataSession session, IAsyncEnumerable<Student> rows, CancellationToken token)
    {
        try { return await session.InsertManyAsync(Students.Table, rows, new BulkOptions { Atomicity = BulkAtomicity.PerBatch }, token); }
        catch (Exception error) when (BulkFailure.TryGetProgress(error, out var progress))
        {
            _ = progress.CompletedBatches; // Application recovery can inspect acknowledged partial progress.
            throw; // Preserve cancellation and commit-unknown types.
        }
    }
}
