#!/usr/bin/env python3
"""Verify API-INT-007/008 against frozen design inputs and small compiler fixtures.

This is author validation of the symbol exporter, not independent acceptance,
product execution, or a replacement for the retained review notes. Each invocation
requires a new evidence directory. Canonical docs/api outputs are never written.
"""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import os
import platform
import shutil
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
API = HERE.parent

FIXTURE = r'''#nullable enable
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
'''


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dotnet', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    dotnet = str(Path(args.dotnet).resolve())
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    steps, assertions, inputs = [], [], []
    passed = False
    env = dict(os.environ, DOTNET_CLI_TELEMETRY_OPTOUT='1', DOTNET_NOLOGO='1',
               DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1', DOTNET_CLI_USE_MSBUILD_SERVER='0')

    def freeze(source, destination):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        inputs.append({'path': source.relative_to(ROOT).as_posix(),
                       'snapshot': destination.relative_to(output).as_posix(), 'sha256': digest(destination)})

    def run(name, command, cwd=API):
        arguments = [str(x) for x in command]
        begin = time.monotonic()
        proc = subprocess.run(arguments, cwd=cwd, env=env, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=120)
        log = output / (name + '.log')
        log.write_bytes(proc.stdout)
        steps.append({'id': name, 'command': arguments, 'cwd': str(cwd), 'exit_code': proc.returncode,
                      'duration_seconds': round(time.monotonic() - begin, 3),
                      'log': log.name, 'log_sha256': digest(log)})
        print(name + ': exit ' + str(proc.returncode), flush=True)
        if proc.returncode:
            raise RuntimeError(name + ' failed; see ' + str(log))
        return proc.stdout.decode()

    def check(name, condition):
        assertions.append({'id': name, 'passed': bool(condition)})
        if not condition:
            raise AssertionError(name)

    def symbols(directory):
        data = json.loads((directory / 'public-api.json').read_text())
        return {row['id']: row for row in data['symbols']}

    try:
        for path in [HERE / 'Program.cs', HERE / 'NativeWeave.Api.Inventory.csproj', HERE / 'packages.lock.json',
                     Path(__file__).resolve(), API / 'Directory.Build.props', API / 'global.json', API / 'NuGet.Offline.Config']:
            freeze(path, output / 'inputs' / path.relative_to(API))
        actual_source = output / 'inputs' / 'NativeWeave.Api.Design'
        for path in sorted((API / 'NativeWeave.Api.Design').glob('*.cs')):
            freeze(path, actual_source / path.name)
        actual_output = output / 'actual'
        actual_output.mkdir()
        for path in sorted((ROOT / 'docs/api').glob('*-symbol-policies.json')):
            freeze(path, actual_output / path.name)
        check('sdk-is-pinned', run('sdk', [dotnet, '--version']).strip() == '11.0.100')
        with tempfile.TemporaryDirectory(prefix='nw-inventory-build-') as temporary:
            build = Path(temporary)
            run('inventory-build', [dotnet, 'build', output / 'inputs/NativeWeave.Api.Inventory/NativeWeave.Api.Inventory.csproj',
                                   '--configfile', output / 'inputs/NuGet.Offline.Config', '-p:RestoreLockedMode=true',
                                   '--disable-build-servers', '-p:UseSharedCompilation=false', '--nologo', '-v:minimal',
                                   '--artifacts-path', build])
            inventory = build / 'bin/NativeWeave.Api.Inventory/debug/NativeWeave.Api.Inventory.dll'
            run('actual-export', [dotnet, inventory, actual_source, Path(dotnet).parent, actual_output])
            actual = symbols(actual_output)
            known = actual['M:NativeWeave.Interop.EngineCatalog.TryGet(System.String,NativeWeave.Interop.EngineDescriptor@)']
            check('tryget-parameter-attribute-metadata', known['parameters'][1]['attributes'] ==
                  ['System.Diagnostics.CodeAnalysis.NotNullWhenAttribute(true)'])
            check('tryget-parameter-attribute-rendering', '[System.Diagnostics.CodeAnalysis.NotNullWhenAttribute(true)] out NativeWeave.Interop.EngineDescriptor? descriptor' in known['signature'])
            buffer = actual['T:NativeWeave.Interop.NativeBuffer']
            check('nativebuffer-sealed-declaration', buffer['signature'] ==
                  'public sealed class NativeWeave.Interop.NativeBuffer : System.IDisposable')
            check('nativebuffer-sealed-metadata', buffer['is_sealed'] and buffer['modifiers'] == ['public', 'sealed'])
            check('plain-type-reference-metadata', buffer['base_type'] == 'object' and buffer['interfaces'] == ['System.IDisposable'])
            reader = actual['T:NativeWeave.Interop.NativeBufferReader`1']
            check('generic-delegate-complete-signature', reader['signature'] ==
                  'public delegate TResult NativeWeave.Interop.NativeBufferReader<TResult>(System.ReadOnlySpan<byte> bytes)')
            check('generic-delegate-metadata', reader['return_or_value_type'] == 'TResult' and
                  reader['parameters'][0]['type'] == 'System.ReadOnlySpan<byte>' and reader['type_parameters'][0]['name'] == 'TResult')
            missing = actual['F:NativeWeave.Interop.EngineLoadFailure.MissingExport']
            check('enum-value-metadata-and-rendering', missing['has_constant_value'] and missing['constant_value'] == 5 and
                  missing['constant_value_type'] == 'System.Int32' and missing['signature'].endswith('MissingExport = 5'))
            check('enum-underlying-type', actual['T:NativeWeave.Interop.EngineLoadFailure']['enum_underlying_type'] == 'int' and
                  actual['T:NativeWeave.Server.ServerCapabilities']['enum_underlying_type'] == 'ulong')
            check('server-static-declaration', actual['T:NativeWeave.Server.NativeServer']['signature'] ==
                  'public static class NativeWeave.Server.NativeServer')
            check('server-record-declaration', actual['T:NativeWeave.Server.ServerEvent']['is_record'] and
                  actual['T:NativeWeave.Server.ServerEvent']['signature'].startswith('public sealed record class '))
            check('server-abstract-declaration', actual['T:NativeWeave.Server.ServerRoutes']['signature'].startswith('public abstract class '))
            check('ref-like-readonly-type', actual['T:NativeWeave.Data.RowReader']['signature'] ==
                  'public readonly ref struct NativeWeave.Data.RowReader' and actual['T:NativeWeave.Data.RowReader']['is_ref_like'])
            query = actual['T:NativeWeave.Query.Query`1']
            check('class-generic-constraints', query['generic_constraints'] == ['where TEntity : class'] and
                  query['type_parameters'][0]['has_reference_type_constraint'] and query['signature'].endswith('where TEntity : class'))
            for row in actual.values():
                for attribute in row['attributes'] + row['return_attributes']:
                    check('rendered-attribute:' + row['id'] + ':' + attribute, attribute in row['signature'])
                for parameter in row['parameters']:
                    for attribute in parameter['attributes']:
                        check('rendered-parameter-attribute:' + row['id'] + ':' + parameter['name'], attribute in row['signature'])

            fixture_source = output / 'fixture-source'
            fixture_source.mkdir()
            (fixture_source / 'Fixture.cs').write_text(FIXTURE)
            fixture_output = output / 'fixture'
            fixture_output.mkdir()
            names = ['Projector', 'RefReader', 'BorrowAction', 'Borrowed', 'IFactory', 'AbstractBase', 'Derived',
                     'Constraints', 'Point', 'Item', 'Flags', 'Signed', 'Constants']
            policy = {'package': 'exporter-test-only', 'semantic_section': 'docs/api/interop.md#1-scope-and-boundaries',
                      'native_operations': ['none'], 'tasks': ['A13'], 'capability': 'symbol-exporter fixture only',
                      'cost_profile': 'No product execution; declarations are compiled to Roslyn symbols.'}
            for domain in ('database', 'server', 'interop'):
                data = {'types': {'NativeWeave.Interop.InventoryRegression.' + name: policy for name in names}
                        if domain == 'interop' else {}}
                (fixture_output / (domain + '-symbol-policies.json')).write_text(json.dumps(data, indent=2) + '\n')
            run('fixture-export', [dotnet, inventory, fixture_source, Path(dotnet).parent, fixture_output])
            fixture = symbols(fixture_output)
            prefix = 'NativeWeave.Interop.InventoryRegression.'
            projector = fixture['T:' + prefix + 'Projector`2']
            check('delegate-return-attribute', projector['return_attributes'] == ['System.Diagnostics.CodeAnalysis.MaybeNullAttribute'] and
                  projector['signature'].startswith('[return: System.Diagnostics.CodeAnalysis.MaybeNullAttribute]\npublic delegate TResult '))
            check('delegate-variance', '<TInput, out TResult>' in projector['signature'] and projector['type_parameters'][1]['variance'] == 'Out')
            check('delegate-generic-constraints', projector['generic_constraints'] ==
                  ['where TInput : class?', 'where TResult : class, System.IDisposable, new()'] and
                  projector['signature'].endswith('where TInput : class? where TResult : class, System.IDisposable, new()'))
            check('delegate-parameter-attributes', projector['parameters'][0]['attributes'] == ['System.Diagnostics.CodeAnalysis.AllowNullAttribute'] and
                  '[System.Diagnostics.CodeAnalysis.AllowNullAttribute] TInput input' in projector['signature'])
            reference = fixture['T:' + prefix + 'RefReader`1']
            check('delegate-ref-readonly-return', 'delegate ref readonly T ' in reference['signature'] and reference['return_ref_kind'] == 'RefReadOnly')
            borrow = fixture['T:' + prefix + 'BorrowAction`1']
            check('delegate-ref-like-constraint', borrow['type_parameters'][0]['allows_ref_like_type'] and
                  borrow['generic_constraints'] == ['where T : allows ref struct'] and 'scoped in T value' in borrow['signature'])
            constrained = fixture['T:' + prefix + 'Constraints`4']
            check('all-generic-constraint-metadata', constrained['generic_constraints'] == [
                'where TValue : struct', 'where TNonNull : notnull',
                'where TClass : class?, System.IDisposable, new()', 'where TBorrow : allows ref struct'])
            check('unmanaged-generic-constraint', fixture['T:' + prefix + 'Borrowed`1']['generic_constraints'] == ['where T : unmanaged'])
            derived = fixture['T:' + prefix + 'Derived']
            check('constructed-base-and-interface', derived['base_type'] == prefix + 'AbstractBase<string>' and
                  derived['interfaces'] == [prefix + 'IFactory<string>'] and
                  derived['signature'].endswith(' : ' + prefix + 'AbstractBase<string>, ' + prefix + 'IFactory<string>'))
            mirror = fixture['M:' + prefix + 'AbstractBase`1.Mirror(System.String)']
            check('method-return-attribute', mirror['return_attributes'] == ['System.Diagnostics.CodeAnalysis.NotNullIfNotNullAttribute("value")'] and
                  '[return: System.Diagnostics.CodeAnalysis.NotNullIfNotNullAttribute("value")]' in mirror['signature'])
            indexer = next(row for row in fixture.values() if row['id'].startswith('P:' + prefix + 'AbstractBase`1.Item('))
            check('indexer-parameter-attribute', 'this[[System.Diagnostics.CodeAnalysis.AllowNullAttribute] string? key, (int Left, int Right) range]' in indexer['signature'])
            getter = fixture['P:' + prefix + 'AbstractBase`1.Value']
            check('getter-return-attribute-target', '{ [return: System.Diagnostics.CodeAnalysis.NotNullAttribute] get; }' in getter['signature'] and
                  not getter['signature'].startswith('[return:'))
            inspect = next(row for row in fixture.values() if row['id'].startswith('M:' + prefix + 'Constants.Inspect'))
            check('complex-parameter-attribute-boundary',
                  '[System.Diagnostics.CodeAnalysis.AllowNullAttribute] System.Collections.Generic.Dictionary<string, (TInput Value, int Code)[]>? values' in inspect['signature'] and
                  '[System.Diagnostics.CodeAnalysis.MaybeNullWhenAttribute(false)] out TResult result' in inspect['signature'] and
                  'params string[] names' in inspect['signature'])
            check('method-generic-constraint-metadata', inspect['generic_constraints'] == projector['generic_constraints'])
            for name, value in [('Highest', 2**63), ('All', 2**64 - 1)]:
                row = fixture['F:' + prefix + 'Flags.' + name]
                check('unsigned-enum:' + name, row['constant_value'] == value and str(value) in row['signature'])
            check('signed-enum', fixture['T:' + prefix + 'Signed']['enum_underlying_type'] == 'short' and
                  fixture['F:' + prefix + 'Signed.Negative']['constant_value'] == -2)
            expected = {'Small': 7, 'Minimum': -(2**63), 'Maximum': 2**64 - 1, 'Amount': 1.25,
                        'Text': 'line\n"quoted"', 'Enabled': False, 'Quote': "'", 'Missing': None,
                        'Infinity': 'Infinity', 'NotANumber': 'NaN'}
            for name, value in expected.items():
                row = fixture['F:' + prefix + 'Constants.' + name]
                check('constant:' + name, row['is_const'] and row['has_constant_value'] and row['constant_value'] == value and ' = ' in row['signature'])
            check('record-struct-and-class-shapes', fixture['T:' + prefix + 'Point']['signature'].startswith('public readonly record struct ') and
                  fixture['T:' + prefix + 'Item']['signature'].startswith('public sealed record class '))
            again = output / 'determinism'
            again.mkdir()
            for path in actual_output.glob('*-symbol-policies.json'):
                shutil.copyfile(path, again / path.name)
            run('repeat-export', [dotnet, inventory, actual_source, Path(dotnet).parent, again])
            check('deterministic-json', digest(actual_output / 'public-api.json') == digest(again / 'public-api.json'))
            check('deterministic-reference', digest(actual_output / 'reference.md') == digest(again / 'reference.md'))
            # The second copies only establish determinism; retain hashes, not duplicate artifacts.
            shutil.rmtree(again)
        passed = True
    finally:
        artifacts = [{'path': path.relative_to(output).as_posix(), 'sha256': digest(path)}
                     for path in sorted(output.rglob('*')) if path.is_file() and path.name != 'summary.json']
        summary = {'schema_version': '1.0.0', 'scope': 'API-INT-007/008 compiler-symbol exporter author validation',
                   'started_at_utc': started, 'recorded_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   'platform': platform.system(), 'architecture': platform.machine(), 'passed': passed,
                   'independent_review': False, 'product_implemented': False, 'product_operations_executed': False,
                   'native_aot_executed': False, 'canonical_reference_updated': False,
                   'inputs': inputs, 'steps': steps, 'assertions': assertions, 'artifacts': artifacts,
                   'limits': ['Source snapshots identify the exact declarations and policies checked; later edits require regeneration.',
                              'This checks compiler-derived declaration metadata and rendering, not runtime product behavior.',
                              'API-INT-007/008 remain subject to independent exact-content review.']}
        (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
        print(json.dumps({'passed': passed, 'assertions': len(assertions), 'summary': str(output / 'summary.json')}))


if __name__ == '__main__':
    main()
