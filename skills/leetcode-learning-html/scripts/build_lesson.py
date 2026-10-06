# -*- coding: utf-8 -*-
"""Compile a problem-specific teaching spec into one portable HTML document."""
import argparse
import ast
import html
import json
import math
import re
from pathlib import Path
from urllib.parse import unquote, urlparse

SKILL = Path(__file__).resolve().parents[1]

def require(condition, message):
    if not condition:
        raise ValueError(message)

def text(value, path):
    require(isinstance(value, str) and value.strip() and value.strip() not in ('...', '……', 'TODO'), f'{path}: expected authored text')

def questions(items, path):
    require(isinstance(items, list), f'{path}: expected list')
    for i, q in enumerate(items):
        text(q.get('prompt'), f'{path}[{i}].prompt')
        choices = q.get('choices', [])
        require(len(choices) >= 2 and sum(c.get('correct') is True for c in choices) == 1, f'{path}[{i}]: exactly one correct choice required')
        for c in choices:
            text(c.get('text'), f'{path}[{i}].choice.text')
            text(c.get('feedback'), f'{path}[{i}].choice.feedback')

def view(data, path):
    kind = data.get('type')
    require(kind in ('state','array','table','graph','tree'), f'{path}: unsupported visualization')
    if kind == 'array':
        require(isinstance(data.get('values'), list), f'{path}: array values required')
        require(all(isinstance(i,int) for i in data.get('pointers',{}).values()), f'{path}: pointer indices must be integers')
    elif kind == 'table':
        require(bool(data.get('columns')) and isinstance(data.get('rows'),list), f'{path}: table columns/rows required')
        require(all(len(row)==len(data['columns']) for row in data['rows']), f'{path}: inconsistent table widths')
    elif kind in ('graph','tree'):
        nodes, edges = data.get('nodes',[]), data.get('edges',[])
        require(nodes and isinstance(edges,list), f'{path}: graph nodes and edges required')
        ids = [n.get('id') for n in nodes]
        require(len(set(ids))==len(ids) and all(isinstance(i,str) and i for i in ids), f'{path}: unique node identities required')
        width,height=data.get('width',720),data.get('height',420)
        for i,n in enumerate(nodes):
            text(n.get('label'), f'{path}.node[{i}].label')
            require(all(isinstance(n.get(k),(int,float)) and math.isfinite(n[k]) for k in ('x','y')), f'{path}: finite node coordinates required')
            require(30<=n['x']<=width-30 and 30<=n['y']<=height-30, f'{path}: node clipped by canvas')
            for other in nodes[:i]:
                require(math.hypot(n['x']-other['x'],n['y']-other['y'])>=65, f'{path}: overlapping nodes {n["id"]}, {other["id"]}')
        for edge in edges:
            require(edge.get('from') in ids and edge.get('to') in ids and edge['from']!=edge['to'], f'{path}: edge must connect existing distinct nodes')

def cases(items, path, minimum):
    require(isinstance(items,list) and len(items)>=minimum, f'{path}: at least {minimum} cases required')
    ids=[c.get('id') for c in items]
    require(len(set(ids))==len(ids) and all(isinstance(i,str) and i for i in ids), f'{path}: unique case ids required')
    for c in items:
        for key in ('name','purpose'):text(c.get(key),f'{path}.{c["id"]}.{key}')
        require('input' in c and 'expected' in c, f'{path}.{c["id"]}: input and expected required')
        require(bool(c.get('frames')), f'{path}.{c["id"]}: real frames required')
        for i,frame in enumerate(c['frames']):
            text(frame.get('caption'),f'{path}.{c["id"]}.{i}.caption')
            text(frame.get('operation'),f'{path}.{c["id"]}.{i}.operation')
            require(isinstance(frame.get('state'),dict) and frame['state'], f'{path}: meaningful state required')
            view(frame.get('view',{}),f'{path}.{c["id"]}.{i}.view')
            if 'question' in frame:questions([frame['question']],f'{path}.{c["id"]}.{i}')

def starter(code, language, path):
    text(code,path)
    if language.lower()!='python':return
    tree=ast.parse(code)
    def signature_only(body):
        for item in body:
            if isinstance(item,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):signature_only(item.body)
            elif not isinstance(item,(ast.Import,ast.ImportFrom,ast.Pass)):
                require(isinstance(item,ast.Expr) and isinstance(item.value,ast.Constant) and isinstance(item.value.value,str), f'{path}: starter contains solution logic')
    signature_only(tree.body)

def validate(lesson):
    for section in ('meta','problem','model','code','transfer'):require(isinstance(lesson.get(section),dict),f'{section}: required')
    meta=lesson['meta'];require(isinstance(meta.get('id'),int) and meta['id']>0,'meta.id: positive problem number required')
    for key in ('title','slug','difficulty'):text(meta.get(key),f'meta.{key}')
    require(isinstance(meta.get('tags'),list),'meta.tags: list required')
    for source in (meta.get('source'),lesson['transfer'].get('source')):
        if source:require(urlparse(source).scheme=='https' and urlparse(source).hostname in ('leetcode.com','leetcode.cn'), 'Source must be a confirmed official HTTPS LeetCode URL')
    problem=lesson['problem'];text(problem.get('summary'),'problem.summary');text(problem.get('signature'),'problem.signature')
    require(bool(problem.get('constraints')) and bool(problem.get('examples')),'Problem constraints and examples required')
    model=lesson['model'];
    for key in ('headline','state','contract','operation','invariant','boundary','answer'):text(model.get(key),f'model.{key}')
    for key in ('time','space'):text(model.get('complexity',{}).get(key),f'model.complexity.{key}')
    ladder=lesson.get('ladder',[]);require(len(ladder)>=3 and any(l.get('current') is True for l in ladder),'A cognitive ladder with current-problem placement is required')
    for level in ladder:
        for key in ('title','detail','problem'):text(level.get(key),f'ladder.{key}')
    cases(lesson.get('cases'),'cases',3)
    require(any('question' in f for c in lesson['cases'] for f in c['frames']),'At least one question must depend on a visible execution frame')
    require(len(lesson.get('stages',[]))==6,'Template requires six authored modules')
    case_ids={c['id'] for c in lesson['cases']}
    for i,stage in enumerate(lesson['stages']):
        for key in ('title','goal'):text(stage.get(key),f'stages[{i}].{key}')
        require(isinstance(stage.get('notes'),list),f'stages[{i}].notes: list required')
        questions(stage.get('questions'),f'stages[{i}].questions')
        if stage.get('case'):require(stage['case'] in case_ids,'Stage references nonexistent case')
    code=lesson['code'];language=meta.get('language','Python')
    starter(code.get('starter'),language,'code.starter');text(code.get('reference'),'code.reference')
    if language.lower()=='python':ast.parse(code['reference'])
    require(bool(code.get('checklist')),'code.checklist required');text(code.get('skeleton'),'code.skeleton')
    slots=code.get('slots',[]);require(bool(slots),'Manual semantic slots required')
    ids=[s.get('id') for s in slots]
    require(len(set(ids))==len(ids) and all(isinstance(i,str) and re.fullmatch(r'[A-Za-z]\w*',i) for i in ids),'Valid unique slot ids required')
    require(set(re.findall(r'\{\{(\w+)\}\}',code['skeleton']))==set(ids),'Every slot must have a matching skeleton token')
    for slot in slots:
        for key in ('label','hint'):text(slot.get(key),f'slot.{key}')
        require(bool(slot.get('accepted')) and all(isinstance(a,str) and a.strip() for a in slot['accepted']),'Slot accepted answers must be nonempty strings')
        require(not any(slot['hint'].strip()==a.strip() for a in slot['accepted']),'Slot hint exposes the exact answer')
    transfer=lesson['transfer']
    for key in ('title','summary','newProof','reference'):text(transfer.get(key),f'transfer.{key}')
    starter(transfer.get('starter'),language,'transfer.starter')
    if language.lower()=='python':ast.parse(transfer['reference'])
    require(all(transfer.get(k) for k in ('preserved','changed','checklist','questions')),'A real migration with changes, proof and diagnosis is required')
    questions(transfer['questions'],'transfer.questions');cases(transfer.get('cases'),'transfer.cases',2)

def build(lesson, output, home=None):
    validate(lesson)
    output=Path(output).resolve()
    if home:
        target=urlparse(home)
        require(not target.scheme and not home.startswith('//'),'Home must be a relative local link')
        require((output.parent/unquote(target.path)).resolve().is_file(),'Home link does not exist relative to output')
        lesson={**lesson,'home':home}
    template=(SKILL/'assets/lesson-shell.html').read_text(encoding='utf-8')
    data=json.dumps(lesson,ensure_ascii=False,allow_nan=False).replace('&','\\u0026').replace('<','\\u003c').replace('>','\\u003e')
    replacements={'__DOCUMENT_TITLE__':html.escape(f'#{lesson["meta"]["id"]} {lesson["meta"]["title"]} · 算法认知实验室'),'__LESSON_CSS__':(SKILL/'assets/lesson.css').read_text(encoding='utf-8'),'__LESSON_JS__':(SKILL/'assets/lesson.js').read_text(encoding='utf-8'),'__LESSON_JSON__':data}
    # Substitute placeholders in one pass, without interpreting marker text inside authored content.
    document=re.sub('|'.join(map(re.escape,replacements)),lambda m:replacements[m.group()],template)
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(document,encoding='utf-8')
    return output

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('lesson',type=Path);parser.add_argument('--output',required=True,type=Path);parser.add_argument('--home')
    args=parser.parse_args();lesson=json.loads(args.lesson.read_text(encoding='utf-8-sig'));print(build(lesson,args.output,args.home))
