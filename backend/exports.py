"""CSV result representation and spreadsheet formula protection."""
from __future__ import annotations

import csv
import io


CSV_FIELDS = ['model', 'run', 'phase', 'status', 'loaded_before', 'tokens', 'tokens_per_s', 'first_content_s', 'first_text_s', 'wall_s', 'total_s', 'load_s', 'prompt_tokens', 'prompt_cached_tokens', 'total_tokens', 'output_tokens_observed', 'token_observation_status', 'prompt_s', 'generation_s', 'done_reason', 'size_vram', 'size_memory', 'error']


def csv_export(state):
    output = io.StringIO(newline='')
    fields = CSV_FIELDS + ['started_at', 'prompt', 'num_predict', 'num_ctx', 'repetitions', 'timeout', 'think', 'live_token_count']
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction='ignore')
    writer.writeheader()
    for row in state['rows']:
        value = {**row, **{k: v for k, v in (state['settings'] or {}).items() if k != 'models'}, 'started_at': state['started_at']}
        # Spreadsheet applications may interpret user-supplied strings as formulas.
        value = {k: "'" + v if isinstance(v, str) and v.startswith(('=', '+', '-', '@', '\t', '\r', '\n')) else v for k, v in value.items()}
        writer.writerow(value)
    return '\ufeff' + output.getvalue()
