import os,json,logging
from copy import deepcopy
from datetime import datetime,timezone
from decimal import Decimal
from urllib.parse import unquote_plus
import boto3
from processor import parse_lesson,calculate_metrics_from_rows
from rules_engine import evaluate_lesson,load_rules
from student_state import load_students,update_student

s3=boto3.client('s3')
ddb=boto3.resource('dynamodb')
logger=logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def decimal_safe(data):
    return json.loads(json.dumps(data),parse_float=Decimal)

def scan_all(table):
    data=[]; args={}
    while True:
        res=table.scan(**args);data.extend(res.get('Items',[]))
        if 'LastEvaluatedKey' not in res: break
        args={'ExclusiveStartKey':res['LastEvaluatedKey']}
    return data

def recompute(lessons,students_table,rules):
    # Rebuild student states in chronological lesson order. Concurrent invocations require additional coordination.
    students=load_students('students.csv')
    scores={sid:[] for sid in students}
    for item in sorted(lessons,key=lambda d:(d['started_at'],d['lesson_id'])):
        sid=item['student_id']
        if sid not in students:
            logger.warning('Unknown student reference in lesson %s',item['lesson_id'])
            continue
        result=evaluate_lesson(item['metrics'],rules)
        if result=='PASS' and item['lesson_type']=='REGULAR' and students[sid]['status']=='ACTIVE':
            scores[sid].append(float(item['metrics']['lesson_score']))
        actual,before,after=update_student(students[sid],result,item['lesson_type'],rules,scores[sid])
        item['result']=actual
        item['original_result']=result
        item['state_before']=decimal_safe(before)
        item['state_after']=decimal_safe(after)
    for sid,state in students.items():
        students_table.put_item(Item=decimal_safe(state))
    return lessons

def lambda_handler(event,context):
    rules=load_rules('rules_v1.json')
    lessons_table=ddb.Table(os.environ['LESSONS_TABLE'])
    students_table=ddb.Table(os.environ['STUDENTS_TABLE'])
    for record in event.get('Records',[]):
        key=unquote_plus(record['s3']['object']['key'])
        if not key.lower().endswith('.csv'): continue
        bucket=record['s3']['bucket']['name']
        content=s3.get_object(Bucket=bucket,Key=key)['Body'].read().decode('utf-8')
        meta,rows=parse_lesson(content)
        metrics=calculate_metrics_from_rows(meta,rows)
        result=evaluate_lesson(metrics,rules)
        lesson_id=meta['lesson_id']
        existing=lessons_table.get_item(Key={'lesson_id':lesson_id}).get('Item')
        if existing and existing.get('started_at')!=meta['started_at']:
            raise ValueError('Duplicate lesson ID with mismatched start time')
        item=dict(lesson_id=lesson_id,student_id=meta['student_id'],started_at=meta['started_at'],
                  lesson_type=meta['lesson_type'],source_key=key,metrics=decimal_safe(metrics),
                  original_result=result,result=result,rules_version=rules['version'],
                  evaluated_at=datetime.now(timezone.utc).isoformat())
        if not existing: lessons_table.put_item(Item=item)
        all_lessons=scan_all(lessons_table)
        updated=recompute(all_lessons,students_table,rules)
        # Preserve original evaluation timestamp on retries, update decision audit after replay.
        for row in updated:
            lessons_table.update_item(Key={'lesson_id':row['lesson_id']},
                UpdateExpression='SET #result=:r, original_result=:o, state_before=:b, state_after=:a',
                ExpressionAttributeNames={'#result':'result'},
                ExpressionAttributeValues={':r':row['result'],':o':row['original_result'],
                  ':b':row['state_before'],':a':row['state_after']})
        logger.info('Processed lesson %s',lesson_id)
    return {'statusCode':200,'body':'Processed'}
