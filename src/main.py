from pathlib import Path
from datetime import datetime,timezone
from copy import deepcopy
import json
from processor import read_lesson,calculate_metrics_from_rows
from rules_engine import load_rules,evaluate_lesson
from student_state import load_students,update_student

ROOT=Path(__file__).resolve().parents[1]

def run_local():
    rules=load_rules(ROOT/'sample_data/rules_v1.json')
    students=load_students(ROOT/'sample_data/students.csv')
    lessons=[]
    for path in (ROOT/'sample_data/lessons').rglob('*.csv'):
        meta,rows=read_lesson(path)
        lessons.append((meta['started_at'],meta['lesson_id'],meta,rows))
    lessons.sort(key=lambda x:(x[0],x[1]))
    audit=[]; observed=set(); scores={id:[] for id in students}
    for _,lesson_id,meta,rows in lessons:
        if lesson_id in observed: continue # Retried uploads must not advance twice.
        observed.add(lesson_id)
        metrics=calculate_metrics_from_rows(meta,rows)
        result=evaluate_lesson(metrics,rules)
        sid=meta['student_id']
        if sid not in students: raise ValueError('Unknown student ID')
        if result=='PASS' and meta['lesson_type']=='REGULAR' and students[sid]['status']=='ACTIVE':
            scores[sid].append(metrics['lesson_score'])
        actual,before,after=update_student(students[sid],result,meta['lesson_type'],rules,scores[sid])
        audit.append(dict(lesson_id=lesson_id,student_id=sid,started_at=meta['started_at'],
            original_result=result,result=actual,rules_version=rules['version'],metrics=metrics,
            state_before=before,state_after=after,evaluated_at=datetime.now(timezone.utc).isoformat()))
    print('LESSONS')
    for a in audit: print(a['lesson_id'],a['student_id'],a['result'])
    print('STUDENTS')
    for sid,s in students.items(): print(sid,json.dumps(s))
    (ROOT/'results.json').write_text(json.dumps({'lessons':audit,'students':students},indent=2),encoding='utf-8')
    print('Created results.json')

if __name__=='__main__': run_local()
