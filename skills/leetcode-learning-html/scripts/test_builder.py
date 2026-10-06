# -*- coding: utf-8 -*-
"""Regression checks for blank exercises, safe embedding and valid diagram structure."""
import json
import tempfile
import unittest
from pathlib import Path
from build_lesson import build, validate
from demo_binary_search import make_lesson, verify_algorithms

class BuilderChecks(unittest.TestCase):
    def setUp(self):self.lesson=make_lesson()
    def test_reference_and_trace_oracles(self):self.assertEqual(verify_algorithms(),1500)
    def test_reject_solution_as_starter(self):
        self.lesson['code']['starter']=self.lesson['code']['reference']
        with self.assertRaisesRegex(ValueError,'solution logic'):validate(self.lesson)
    def test_reject_answer_placeholder(self):
        slot=self.lesson['code']['slots'][0];slot['hint']=slot['accepted'][0]
        with self.assertRaisesRegex(ValueError,'exposes'):validate(self.lesson)
    def test_reject_missing_slot_binding(self):
        self.lesson['code']['skeleton']+='\n{{unknownSlot}}'
        with self.assertRaisesRegex(ValueError,'matching skeleton'):validate(self.lesson)
    def test_reject_invalid_graph_edges_and_overlap(self):
        graph={'type':'tree','width':400,'height':300,'nodes':[{'id':'left','label':'2','x':100,'y':100},{'id':'right','label':'None','x':280,'y':100,'status':'missing'}],'edges':[{'from':'left','to':'right','dashed':True}]}
        self.lesson['cases'][0]['frames'][0]['view']=graph;validate(self.lesson)
        graph['edges'][0]['to']='not-present'
        with self.assertRaisesRegex(ValueError,'existing distinct nodes'):validate(self.lesson)
        graph['edges'][0]['to']='right';graph['nodes'][1]['x']=110
        with self.assertRaisesRegex(ValueError,'overlapping'):validate(self.lesson)
    def test_safe_json_embedding_and_real_home(self):
        self.lesson['problem']['summary']='文字 </script><script>throw new Error("escaped")</script> & <b>'
        with tempfile.TemporaryDirectory() as directory:
            directory=Path(directory);(directory/'index.html').write_text('<h1>home</h1>',encoding='utf-8')
            output=build(self.lesson,directory/'lesson.html','index.html');source=output.read_text(encoding='utf-8')
            self.assertNotIn('</script><script>throw',source)
            start=source.index('<script type="application/json" id="lessonData">')+len('<script type="application/json" id="lessonData">')
            payload=json.loads(source[start:source.index('</script>',start)])
            self.assertEqual(payload['problem']['summary'],self.lesson['problem']['summary']);self.assertEqual(payload['home'],'index.html')
            with self.assertRaisesRegex(ValueError,'does not exist'):build(self.lesson,directory/'lesson.html','missing.html')

if __name__=='__main__':unittest.main()
