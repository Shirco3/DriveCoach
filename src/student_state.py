import csv
from copy import deepcopy

def load_students(path):
    with open(path,encoding='utf-8',newline='') as f:
        return {r['student_id']: {k:r[k] for k in ('student_id','program','lessons_completed','review_count','next_lesson_type','status')} for r in csv.DictReader(f)}

def update_student(student,result,lesson_type,rules,passing_scores):
    before=deepcopy(student)
    if student['status'] != 'ACTIVE' or result=='INVALID': return result,before,deepcopy(student)
    if result=='REVIEW':
        next_count=int(student['review_count'])+1
        if next_count > rules['programs'][student['program']]['max_reviews']:
            result='FAIL'
        else:
            student['review_count']=next_count
            student['next_lesson_type']='PRACTICE'
    if result=='FAIL':
        if student['program']=='STANDARD':
            student['program']='EXTENDED'
            student['review_count']=0
        else: student['status']='INSTRUCTOR_REVIEW'
    elif result=='PASS':
        if lesson_type=='REGULAR':
            student['lessons_completed']=int(student['lessons_completed'])+1
        student['next_lesson_type']='REGULAR'
        if int(student['lessons_completed'])>=rules['programs'][student['program']]['lessons']:
            student['status']='COMPLETED'
            if passing_scores: student['final_score']=sum(passing_scores)/len(passing_scores)
    return result,before,deepcopy(student)
