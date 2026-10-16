import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from processor import count_events,calculate_metrics,parse_lesson
from rules_engine import load_rules,evaluate_lesson
from student_state import load_students,update_student
ROOT=Path(__file__).resolve().parents[1]
class CoreTests(unittest.TestCase):
    def test_runs_merge(self):
        data=[0]*15+[1]*10+[0]*15
        self.assertEqual(count_events(data,lambda x:x==0),1)
        self.assertEqual(count_events([0]*15+[1]*50+[0]*15,lambda x:x==0),2)
    def test_real_lesson(self):
        metrics=calculate_metrics(ROOT/'sample_data/lessons/CAR-01/2026-10-05/L-1001.csv')
        self.assertAlmostEqual(metrics['duration_min'],20)
        self.assertEqual(evaluate_lesson(metrics,load_rules(ROOT/'sample_data/rules_v1.json')),'PASS')
    def test_program(self):
        students=load_students(ROOT/'sample_data/students.csv')
        rules=load_rules(ROOT/'sample_data/rules_v1.json')
        result,_,state=update_student(students['S-001'],'PASS','REGULAR',rules,[90])
        self.assertEqual(state['lessons_completed'],10)
    def test_invalid(self):
        r=load_rules(ROOT/'sample_data/rules_v1.json')
        self.assertEqual(evaluate_lesson({'duration_min':2},r),'INVALID')
if __name__=='__main__': unittest.main()
