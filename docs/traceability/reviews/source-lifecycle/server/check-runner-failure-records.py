"""Review-only injected exception checks; these are not real Cargo failure runs."""
from pathlib import Path
import importlib.util
import json
import subprocess
import sys

HERE = Path(__file__).resolve().parent
# HERE is nativeweave/recovery/design-review/server-review.
SOURCE = HERE.parents[2] / 'NativeWeave-Design-research/experiments/server-retained-bytes/run.py'
sys.dont_write_bytecode = True  # Keep the reviewed source tree read-only.
original_run = subprocess.run
observations = []
for kind in ('timeout', 'missing-tool'):
    spec = importlib.util.spec_from_file_location('reviewed_server_runner', SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    out = HERE / ('injected-' + kind)

    def injected_run(command, *args, **kwargs):
        if command[0] == 'cargo' and 'test' in command:
            if kind == 'timeout':
                raise subprocess.TimeoutExpired(command, 240,
                    output=b'SYNTHETIC_TIMEOUT_PARTIAL_STDOUT\n',
                    stderr=b'SYNTHETIC_TIMEOUT_PARTIAL_STDERR\n')
            raise FileNotFoundError('SYNTHETIC_MISSING_TOOL')
        return original_run(command, *args, **kwargs)

    subprocess.run = injected_run
    sys.argv = [str(SOURCE), '--out', str(out)]
    try:
        code = module.main()
    finally:
        subprocess.run = original_run
    result = json.loads((out / 'result.json').read_text())
    command = result['commands'][-1]
    assert code == 1 and result['success'] is False
    assert command['command'][0] == 'cargo' and 'test' in command['command']
    if kind == 'timeout':
        assert command['exit_code'] == 124 and command['timed_out'] is True
        assert 'SYNTHETIC_TIMEOUT_PARTIAL_STDOUT' in (out / command['stdout']).read_text()
        assert 'SYNTHETIC_TIMEOUT_PARTIAL_STDERR' in (out / command['stderr']).read_text()
    else:
        assert command['exit_code'] == 127 and command['timed_out'] is False
        assert 'SYNTHETIC_MISSING_TOOL' in (out / command['stderr']).read_text()
    assert (out / 'inputs/src/lib.rs').is_file()
    observations.append({'case':kind, 'kind':'injected Python exception; not an actual Cargo failure',
                         'expected_failed_command_and_logs_preserved':True,
                         'runner_input_hash':result['source_sha256_before']['run.py'],
                         'result':str(out.relative_to(HERE) / 'result.json')})
(HERE / 'runner-failure-checks.json').write_text(json.dumps(observations, indent=2)+'\n')
print('Review-only injected exception checks passed; no actual Cargo timeout was exercised.')
