"""Pure metric conversion and result summaries."""
from __future__ import annotations

import math
import statistics


def seconds(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        return None
    return value / 1e9


def token_count(value):
    return value if type(value) is int and value >= 0 else None


def usage(rows):
    completed = [row for row in rows if row['status'] == 'completed']
    result = {'completed_runs': len(completed), 'excluded_runs': sum(row['status'] in {'failed', 'cancelled'} for row in rows)}
    for field in ['prompt_tokens', 'tokens', 'prompt_cached_tokens', 'total_tokens']:
        values = [token_count(row.get(field)) for row in completed]
        result[field] = sum(values) if values and all(value is not None for value in values) else None
    return result


def metrics(final, elapsed, first_content, first_text):
    count = final.get('eval_count')
    if type(count) is not int or count < 0:
        raise ValueError('Ollama não retornou uma contagem de tokens válida.')
    generation = seconds(final.get('eval_duration'))
    prompt = token_count(final.get('prompt_eval_count'))
    return {
        'tokens': count,
        'tokens_per_s': count / generation if generation and count else None,
        'first_content_s': first_content,
        'first_text_s': first_text,
        'wall_s': elapsed,
        'total_s': seconds(final.get('total_duration')),
        'load_s': seconds(final.get('load_duration')),
        'prompt_tokens': prompt,
        'prompt_cached_tokens': token_count(final.get('prompt_eval_cached_count')),
        'total_tokens': prompt + count if prompt is not None else None,
        'prompt_s': seconds(final.get('prompt_eval_duration')),
        'generation_s': generation,
        'done_reason': final.get('done_reason', 'unknown'),
    }


def summarize(rows):
    result = []
    for model in dict.fromkeys(row['model'] for row in rows):
        selected = [r for r in rows if r['model'] == model and r['status'] == 'completed']
        initial = next((r for r in selected if r['run'] == 1), None)
        warm = [r for r in selected if r['run'] > 1]
        summary = {'model': model, 'initial': initial, 'repeated_count': len(warm)}
        for field in ['tokens_per_s', 'first_text_s', 'wall_s']:
            values = [r[field] for r in warm if isinstance(r.get(field), (int, float))]
            summary[field] = statistics.median(values) if values else None
        result.append(summary)
    return result
