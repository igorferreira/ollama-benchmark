"""Pure metric conversion and result summaries."""
from __future__ import annotations

import math
import statistics


def seconds(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        return None
    return value / 1e9


def metrics(final, elapsed, first_content, first_text):
    count = final.get('eval_count')
    if type(count) is not int or count < 0:
        raise ValueError('Ollama não retornou uma contagem de tokens válida.')
    generation = seconds(final.get('eval_duration'))
    return {
        'tokens': count,
        'tokens_per_s': count / generation if generation and count else None,
        'first_content_s': first_content,
        'first_text_s': first_text,
        'wall_s': elapsed,
        'total_s': seconds(final.get('total_duration')),
        'load_s': seconds(final.get('load_duration')),
        'prompt_tokens': final.get('prompt_eval_count'),
        'prompt_cached_tokens': final.get('prompt_eval_cached_count'),
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
