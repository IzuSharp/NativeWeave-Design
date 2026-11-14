#!/usr/bin/env python3
"""Isolated .NET 11 declaration/package-flow probe; never builds product or Rust code."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
import zipfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
VERSION = "0.0.1-design-probe"
PROVENANCE = REPO / "verification/engine-completion/linux-reviewed/NativeWeave.Research.Codec.0.0.1.nupkg"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def package(feed: Path, identity: str, files: dict[str, bytes], dependencies: list[str]) -> Path:
    """Assemble a deterministic research nupkg. SDK pack is not under test here."""
    root = ET.Element("package", xmlns="http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd")
    metadata = ET.SubElement(root, "metadata")
    for key, value in {"id": identity, "version": VERSION, "authors": "NativeWeave Design",
                       "description": "Isolated design package-flow probe. Never a published product."}.items():
        ET.SubElement(metadata, key).text = value
    group = ET.SubElement(ET.SubElement(metadata, "dependencies"), "group", targetFramework="net11.0")
    for dependency in dependencies:
        ET.SubElement(group, "dependency", id=dependency, version=f"[{VERSION}]")
    files = dict(files)
    files[identity + ".nuspec"] = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    files["[Content_Types].xml"] = b'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="nuspec" ContentType="application/octet"/></Types>'
    path = feed / f"{identity}.{VERSION}.nupkg"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in sorted(files.items()):
            entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o644 << 16
            archive.writestr(entry, content)
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dotnet", required=True, type=Path)
    parser.add_argument("--work-directory", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--aot", action="store_true", help="Also attempt real linux-x64 AOT; requires compiler/runtime packages.")
    args = parser.parse_args()
    dotnet, work, output = args.dotnet.resolve(), args.work_directory.resolve(), args.output.resolve()
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        raise SystemExit("This probe reuses a Linux x64 research binary; other platforms need a separate evidence row.")
    if work.exists() and any(work.iterdir()):
        raise SystemExit("Use a fresh empty work directory; existing evidence is never overwritten.")
    work.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    sdk_root = dotnet.parent
    sdk = sdk_root / "sdk/11.0.100"
    refs = sdk_root / "packs/Microsoft.NETCore.App.Ref/11.0.0/ref/net11.0"
    compiler = sdk / "Roslyn/bincore/csc.dll"
    if not compiler.is_file() or not refs.is_dir():
        raise SystemExit("The exact SDK 11.0.100/net11.0 reference pack is required.")
    env = dict(os.environ)
    env.update({"DOTNET_ROOT": str(sdk_root), "DOTNET_CLI_HOME": str(work / "cli-home"),
                "NUGET_PACKAGES": str(work / "packages"), "DOTNET_CLI_TELEMETRY_OPTOUT": "1",
                "DOTNET_SKIP_FIRST_TIME_EXPERIENCE": "1", "DOTNET_NOLOGO": "1",
                "DOTNET_CLI_USE_MSBUILD_SERVER": "0", "MSBUILDDISABLENODEREUSE": "1",
                "MSBuildEnableWorkloadResolver": "false"})
    # The consumer's effective PATH contains no Rust toolchain. No producer step invokes Rust either.
    env["PATH"] = str(sdk_root) + ":/usr/bin:/bin"
    for tool in ("cargo", "rustc", "rustup"):
        if shutil.which(tool, path=env["PATH"]) is not None:
            raise SystemExit(f"Unexpected {tool} on the explicit no-Rust consumer PATH")
    results: dict = {"schema_version": "1.0.0", "scope": "design-declarations-and-package-flow",
                     "product_implemented": False, "sdk": "11.0.100", "runtime": "11.0.0", "csharp": "15.0",
                     "platform": {"system": platform.system(), "machine": platform.machine()},
                     "consumer_has_rust_on_path": False, "pristine_machine_claim": False,
                     "native_source": {"path": str(PROVENANCE.relative_to(REPO)), "sha256": digest(PROVENANCE),
                                       "recompiled": False}, "commands": [], "checks": {}, "inputs": {}}
    for source in sorted(HERE.iterdir()):
        if source.is_file():
            results["inputs"][str(source.relative_to(REPO))] = digest(source)

    def normalized(value: str) -> str:
        return value.replace(str(work), "<work>").replace(str(sdk_root), "<dotnet-root>").replace(str(REPO), "<repository>")

    def save() -> None:
        (output / "summary.json").write_text(json.dumps(results, indent=2) + "\n")

    def run(name: str, command: list[str], *, expect: int | None = 0, timeout: int = 120) -> subprocess.CompletedProcess:
        started = time.monotonic()
        try:
            process = subprocess.run(command, cwd=work, env=env, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, text=True, timeout=timeout)
        except subprocess.TimeoutExpired as error:
            text = error.stdout or b""
            if isinstance(text, bytes):
                text = text.decode("utf-8", "replace")
            process = subprocess.CompletedProcess(command, 124, text + "\nPROBE COMMAND TIMED OUT\n")
        log = output / (name + ".log")
        log.write_text(normalized(process.stdout))
        results["commands"].append({"name": name, "argv": [normalized(str(v)) for v in command],
                                   "exit_code": process.returncode, "seconds": round(time.monotonic() - started, 3),
                                   "log": log.name, "sha256": digest(log)})
        save()
        print(f"{name}: exit={process.returncode}", flush=True)
        if expect is not None and process.returncode != expect:
            raise RuntimeError(f"{name} failed; inspect {log}")
        return process

    def csc(name: str, source_files: list[Path], destination: Path, extra: list[str] = (), expect: int | None = 0):
        response = work / (name + ".rsp")
        options = ["-nologo", "-noconfig", "-nostdlib+", "-target:library", "-langversion:15.0",
                   "-nullable:enable", "-warnaserror+", "-deterministic+", f'-out:"{destination}"']
        options += [f'-r:"{p}"' for p in sorted(refs.glob("*.dll"))]
        options += list(extra) + [f'"{p}"' for p in source_files]
        response.write_text("\n".join(options) + "\n")
        # csc treats -noconfig inside a response file as a warning; put it on its command line instead.
        response.write_text(response.read_text().replace("-noconfig\n", ""))
        return run(name, [str(dotnet), str(compiler), "-noconfig", "@" + str(response)], expect=expect)

    try:
        run("sdk-info", [str(dotnet), "--info"])
        interop = HERE.parent / "NativeWeave.Api.Design/Interop.cs"
        consumers = HERE.parent / "NativeWeave.Api.Consumers/InteropExamples.cs"
        for source in (interop, consumers):
            results["inputs"][str(source.relative_to(REPO))] = digest(source)
        csc("interop-declarations", [interop, consumers], work / "InteropCheck.dll",
            [f'-doc:"{work / "InteropCheck.xml"}"'])
        results["checks"]["interop_declarations"] = "design-compiled"
        negative = work / "InvalidBorrow.cs"
        negative.write_text("using System; using NativeWeave.Interop;\nclass InvalidBorrow { static ReadOnlySpan<byte> Escape(NativeBuffer buffer) => buffer.Read<ReadOnlySpan<byte>>(static bytes => bytes); }\n")
        failure = csc("interop-negative-borrow", [negative], work / "InvalidBorrow.dll",
                      [f'-r:"{work / "InteropCheck.dll"}"'], expect=None)
        if failure.returncode == 0 or "CS9244" not in failure.stdout:
            raise RuntimeError("Borrow escape was not rejected with the expected ref-like generic diagnostic")
        results["checks"]["borrow_escape_negative"] = "CS9244"
        layout = HERE.parent / "abi/layout_probe.c"
        run("c-layout-compile", ["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", str(layout), "-o", str(work / "layout_probe")])
        run("c-layout-execute", [str(work / "layout_probe")])
        results["checks"]["shared_c_layout"] = "design-executed-linux-x64"

        generator = work / "NativeWeave.Design.Probe.Generator.dll"
        csc("generator-compile", [HERE / "ProbeGenerator.cs"], generator,
            [f'-r:"{sdk / "Roslyn/bincore/Microsoft.CodeAnalysis.dll"}"',
             f'-r:"{sdk / "Roslyn/bincore/Microsoft.CodeAnalysis.CSharp.dll"}"',
             "-warnaserror-:1701"])
        facade = work / "NativeWeave.Design.Probe.dll"
        csc("facade-compile", [HERE / "ProbeAttributes.cs"], facade)
        feed = work / "feed"
        feed.mkdir()
        with zipfile.ZipFile(PROVENANCE) as original:
            codec = original.read("lib/net11.0/Codec.dll")
            native = original.read("runtimes/linux-x64/native/libnw_codec_research.so")
        results["native_source"]["native_sha256"] = hashlib.sha256(native).hexdigest()
        archives = [
            package(feed, "NativeWeave.Design.Probe.Native", {"lib/net11.0/_._": b"",
                    "runtimes/linux-x64/native/libnw_codec_research.so": native}, []),
            package(feed, "NativeWeave.Design.Probe.BuildAssets", {"lib/net11.0/_._": b"",
                    "tools/net11.0/NativeWeave.Design.Probe.Generator.dll": generator.read_bytes(),
                    "buildTransitive/NativeWeave.Design.Probe.BuildAssets.targets": (HERE / "NativeWeave.Design.Probe.BuildAssets.targets").read_bytes()}, []),
            package(feed, "NativeWeave.Design.Probe", {"lib/net11.0/NativeWeave.Design.Probe.dll": facade.read_bytes(),
                    "lib/net11.0/Codec.dll": codec}, ["NativeWeave.Design.Probe.Native", "NativeWeave.Design.Probe.BuildAssets"])]
        results["packages"] = [{"name": p.name, "sha256": digest(p)} for p in archives]
        (work / "NuGet.Config").write_text('<configuration><packageSources><clear/><add key="probe" value="' + str(feed) + '"/></packageSources><auditSources><clear/></auditSources></configuration>')
        (work / "global.json").write_text('{"sdk":{"version":"11.0.100","rollForward":"disable","allowPrerelease":false}}')
        consumer = work / "consumer"
        consumer.mkdir()
        project = consumer / "Consumer.csproj"
        project.write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net11.0</TargetFramework><LangVersion>15.0</LangVersion><Nullable>enable</Nullable><ImplicitUsings>enable</ImplicitUsings><TreatWarningsAsErrors>true</TreatWarningsAsErrors><NuGetAudit>false</NuGetAudit><EmitCompilerGeneratedFiles>true</EmitCompilerGeneratedFiles><CompilerGeneratedFilesOutputPath>obj/generated</CompilerGeneratedFilesOutputPath><UseSharedCompilation>false</UseSharedCompilation></PropertyGroup><ItemGroup><PackageReference Include="NativeWeave.Design.Probe" Version="[' + VERSION + ']"/></ItemGroup></Project>')
        program = consumer / "Program.cs"
        program.write_bytes((HERE / "Consumer.cs").read_bytes())
        build = [str(dotnet), "build", str(project), "-c", "Release", "--disable-build-servers", "-m:1", "-nodeReuse:false"]
        run("consumer-build", build)
        run_command = [str(dotnet), "run", "--project", str(project), "-c", "Release", "--no-build", "--"]
        initial = run("consumer-run", run_command + ["3"])
        assets = json.loads((consumer / "obj/project.assets.json").read_text())
        actual = sorted(assets["libraries"])
        if actual != sorted([f"{identity}/{VERSION}" for identity in ["NativeWeave.Design.Probe", "NativeWeave.Design.Probe.Native", "NativeWeave.Design.Probe.BuildAssets"]]):
            raise RuntimeError("The fixture restored an unexpected package closure")
        results["resolved_packages"] = actual
        results["checks"]["transitive_generator_and_native"] = "design-executed"
        generated = list((consumer / "obj/generated").rglob("*.g.cs"))
        if len(generated) != 1:
            raise RuntimeError("Expected exactly one generator output; repeated inclusion or missing generator")
        first_generated_hash = digest(generated[0])
        results["checks"]["single_generator_output"] = True
        published_native = consumer / "bin/Release/net11.0/runtimes/linux-x64/native/libnw_codec_research.so"
        if digest(published_native) != results["native_source"]["native_sha256"]:
            raise RuntimeError("RID-free native asset differs from the inherited binary")
        # Add an ordinary entity and modify a DTO; this edits only application C#.
        program.write_text(program.read_text().replace("public sealed class UserSummary\n    {", "public sealed class UserSummary\n    {\n        public decimal? Total { get; init; }")
                           + '\nnamespace Example { [ProbeEntity] public sealed class Order { public long Id { get; init; } public long UserId { get; init; } public decimal Total { get; init; } } }\n')
        run("changed-model-build", build + ["--no-restore"])
        changed = run("changed-model-run", run_command + ["4"])
        changed_generated_hash = digest(generated[0])
        if changed_generated_hash == first_generated_hash or digest(published_native) != results["native_source"]["native_sha256"]:
            raise RuntimeError("A model edit must change generated metadata and leave the native binary unchanged")
        results["checks"]["model_edit_reuses_native"] = True
        results["generated"] = {"initial_sha256": first_generated_hash, "changed_sha256": changed_generated_hash}
        (output / "generated-example.cs").write_bytes(generated[0].read_bytes())
        bad = consumer / "Unsupported.cs"
        bad.write_text("namespace Example { [NativeWeave.Design.Probe.ProbeEntity] public sealed class InvalidModel { public object Payload { get; init; } = new(); } }\n")
        failed = run("unsupported-model-negative", build + ["--no-restore"], expect=None)
        if failed.returncode == 0 or "NWPKGPROBE001" not in failed.stdout:
            raise RuntimeError("Unsupported model did not trigger the generator's expected compile error")
        results["checks"]["unsupported_model_negative"] = "NWPKGPROBE001"
        bad.unlink()
        # Rebuild the supported application and publish framework-dependent without network access.
        run("consumer-publish", [str(dotnet), "publish", str(project), "-c", "Release", "--no-restore", "--disable-build-servers", "-m:1", "-nodeReuse:false", "-o", str(work / "published")])
        run("published-consumer-run", [str(dotnet), str(work / "published/Consumer.dll"), "4"])
        results["checks"]["normal_publish"] = "design-executed-framework-dependent"
        results["checks"]["native_aot"] = "not-attempted"
        if args.aot:
            # The optional online source supplies only official SDK AOT packs, never application-native builds.
            aot_config = work / "NuGet.Aot.Config"
            aot_config.write_text('<configuration><packageSources><clear/><add key="probe" value="' + str(feed) + '"/><add key="nuget.org" value="https://api.nuget.org/v3/index.json"/></packageSources></configuration>')
            aot = run("consumer-aot-publish", [str(dotnet), "publish", str(project), "-c", "Release", "-r", "linux-x64", "-p:PublishAot=true", "-p:NuGetAudit=false", "--configfile", str(aot_config), "--disable-build-servers", "-m:1", "-nodeReuse:false", "-o", str(work / "aot")], expect=None, timeout=180)
            if aot.returncode == 0:
                run("consumer-aot-run", [str(work / "aot/Consumer"), "4", "--aot"])
                results["checks"]["native_aot"] = "design-native-aot-executed"
            else:
                results["checks"]["native_aot"] = "attempt-failed-see-log"
        results["status"] = "passed-design-scope"
    except Exception as error:
        results["status"] = "failed"
        results["failure"] = normalized(str(error))
        save()
        raise
    save()
    return 0


if __name__ == "__main__":
    sys.exit(main())
