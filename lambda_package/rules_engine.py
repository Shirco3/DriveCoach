import json
import operator
OPS={'>':operator.gt,'>=':operator.ge,'<':operator.lt,'<=':operator.le,'==':operator.eq,'!=':operator.ne}

def load_rules(path):
    with open(path,encoding='utf-8') as f: return json.load(f)

def evaluate_lesson(metrics,rules):
    if metrics['duration_min']<rules['min_duration_min']: return 'INVALID'
    for group,name in [('fail_if_any','FAIL'),('review_if_any','REVIEW')]:
        for c in rules[group]:
            if OPS[c['op']](metrics[c['metric']],c['value']): return name
    return 'PASS'
