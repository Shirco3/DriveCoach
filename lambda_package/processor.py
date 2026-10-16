import csv
import io
from pathlib import Path

REQUIRED = {'t_ms','speed','accel_long_ms2','accel_lat_ms2','steering_deg','speed_limit_kmh'}
META = {'lesson_id','student_id','lesson_type','started_at','sample_rate_hz','speed_unit'}

def parse_lesson(text):
    lines = text.splitlines()
    meta = {}
    body = []
    for line in lines:
        if line.startswith('#'):
            key, sep, value = line[1:].partition(':')
            if not sep: raise ValueError('Invalid metadata header')
            meta[key.strip()] = value.strip()
        elif line.strip():
            body.append(line)
    if not META.issubset(meta): raise ValueError('Missing lesson metadata')
    if meta['lesson_type'] not in ('REGULAR','PRACTICE'): raise ValueError('Invalid lesson type')
    rate = int(meta['sample_rate_hz'])
    if rate <= 0: raise ValueError('Invalid sample rate')
    reader = csv.DictReader(io.StringIO('\n'.join(body)))
    if not reader.fieldnames or not REQUIRED.issubset(reader.fieldnames): raise ValueError('Missing CSV columns')
    measurements = list(reader)
    if not measurements: raise ValueError('No measurements')
    return meta, measurements

def read_lesson(path):
    return parse_lesson(Path(path).read_text(encoding='utf-8'))

def count_events(values, predicate):
    # Qualified runs must last 15 samples; gaps < 50 samples merge events.
    runs=[]; start=None
    for i, x in enumerate(values):
        if predicate(x):
            if start is None: start=i
        elif start is not None:
            if i-start >= 15: runs.append((start,i))
            start=None
    if start is not None and len(values)-start>=15: runs.append((start,len(values)))
    events=0; previous_end=None
    for a,b in runs:
        if previous_end is None or a-previous_end >= 50: events+=1
        previous_end=b
    return events

def calculate_metrics_from_rows(meta, rows):
    rate=int(meta['sample_rate_hz'])
    units=meta['speed_unit'].lower().replace('/','')
    factors={'kmh':1, 'mph':1.609344, 'ms':3.6, 'mps':3.6}
    if units not in factors: raise ValueError('Unsupported speed unit: '+units)
    speeds=[float(r['speed'])*factors[units] for r in rows]
    speed_limits=[float(r['speed_limit_kmh']) for r in rows]
    longitudinal=[float(r['accel_long_ms2']) for r in rows]
    lateral=[float(r['accel_lat_ms2']) for r in rows]
    moving=[s for s in speeds if s>2]
    pct=100*sum(s>limit+5 for s,limit in zip(speeds,speed_limits))/len(rows)
    brakes=count_events(longitudinal,lambda x:x<=-3.5)
    accels=count_events(longitudinal,lambda x:x>=3.0)
    turns=count_events(lateral,lambda x:abs(x)>=4.0)
    score=max(0,min(100,100-2*pct-5*brakes-3*accels-4*turns))
    return dict(duration_min=len(rows)/rate/60,
                distance_km=sum(s/3.6/rate/1000 for s in speeds),
                avg_moving_speed_kmh=sum(moving)/len(moving) if moving else 0,
                pct_time_over_limit=pct, harsh_brake_count=brakes,
                harsh_accel_count=accels, sharp_turn_count=turns,
                max_lateral_g=max(abs(x) for x in lateral)/9.81,
                lesson_score=score)

def calculate_metrics(path):
    meta, rows=read_lesson(path)
    return calculate_metrics_from_rows(meta,rows)
