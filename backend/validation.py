"""Benchmark settings validation and defaults."""
from __future__ import annotations




def validate_settings(value):
    if not isinstance(value, dict):
        raise ValueError('A configuração precisa ser um objeto JSON.')
    models = value.get('models')
    if not isinstance(models, list) or not 1 <= len(models) <= 20:
        raise ValueError('Selecione de 1 a 20 modelos.')
    if any(not isinstance(m, str) or not m.strip() or len(m) > 200 for m in models):
        raise ValueError('Nome de modelo inválido.')
    prompt = value.get('prompt')
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 16000:
        raise ValueError('Informe um prompt de até 16.000 caracteres.')
    result = {'models': list(dict.fromkeys(models)), 'prompt': prompt}
    for name, default, low, high in [('num_predict', 128, 1, 4096), ('num_ctx', 4096, 512, 131072), ('repetitions', 3, 2, 10), ('timeout', 180, 10, 1800)]:
        number = value.get(name, default)
        if type(number) is not int or not low <= number <= high:
            raise ValueError(f'{name}: informe um inteiro entre {low} e {high}.')
        result[name] = number
    if type(value.get('think', False)) is not bool:
        raise ValueError('think precisa ser verdadeiro ou falso.')
    result['think'] = value.get('think', False)
    return result
