# -*- coding: utf-8 -*-
"""A validated #704 example demonstrating the skill's content authoring contract."""
import argparse
import copy
import json
import random
from pathlib import Path
from build_lesson import build

MAIN = '''class Solution:
    def search(self, nums, target):
        left, right = 0, len(nums) - 1
        while left <= right:
            mid = (left + right) // 2
            if nums[mid] < target:
                left = mid + 1
            elif nums[mid] > target:
                right = mid - 1
            else:
                return mid
        return -1'''
TRANSFER = '''class Solution:
    def searchInsert(self, nums, target):
        left, right = 0, len(nums)
        while left < right:
            mid = (left + right) // 2
            if nums[mid] < target:
                left = mid + 1
            else:
                right = mid
        return left'''
STARTER = 'class Solution:\n    def search(self, nums, target):\n        pass'
TRANSFER_STARTER = 'class Solution:\n    def searchInsert(self, nums, target):\n        pass'

def question(prompt, options, answer, explanations):
    return {'prompt':prompt,'choices':[{'text':s,'correct':i==answer,'feedback':explanations[i]} for i,s in enumerate(options)]}

def trace(nums, target, lower=False):
    left,right=0,len(nums) if lower else len(nums)-1
    frames=[]
    def frame(caption,operation,line,mid=None,answer=None,q=None):
        indices=list(range(len(nums)))
        active=[mid] if mid is not None else []
        discarded=[i for i in indices if i<left or (i>=right if lower else i>right)]
        state={'left':left,'right':right,'区间':'[left, right)' if lower else '[left, right]','target':target}
        pointers={'left':left,'right':right}
        if mid is not None:state.update({'mid':mid,'nums[mid]':nums[mid]});pointers['mid']=mid
        if answer is not None:state['返回值']=answer
        row={'caption':caption,'operation':operation,'line':line,'state':state,'view':{'type':'array','values':list(nums),'pointers':pointers,'active':active,'discarded':discarded}}
        if q:row['question']=q
        frames.append(row)
    while left<right if lower else left<=right:
        mid=(left+right)//2;value=nums[mid]
        if lower:
            q=question(f'当前 mid={mid}，nums[mid]={value}，target={target}。应如何缩小边界？',['left = mid + 1','right = mid','直接返回 mid'],0 if value<target else 1,[f'{value} 小于目标，mid 及左侧都无法成为第一个不小于目标的位置。' if value<target else f'{value} 已不小于目标，答案可能还在更左边，不能排除 mid。',f'{value} 已不小于目标，要继续压缩右侧边界。' if value>=target else '当前值小于目标，右边仍可能出现第一个合格位置。','命中数值也不代表已经证明了最左边界。'])
        else:
            correct=0 if value<target else 1 if value>target else 2
            q=question(f'当前 nums[mid]={value}，target={target}。哪一种结论有充分证据？',['排除 mid 及其左半','排除 mid 及其右半','当前 mid 就是答案'],correct,[f'有序且 {value} < {target}，mid 及左边全部小于目标。' if value<target else '当前值并不小于目标，不能证明 mid 及左边都不是答案。',f'有序且 {value} > {target}，mid 及右边全部大于目标。' if value>target else '当前值并不大于目标，不能证明右边全部不可能。',f'{value} = {target}，精确查找可以返回当前索引。' if value==target else f'当前 {value} 与 {target} 不相等，还不能返回这个索引。'])
        frame('橙色位置是当前 mid；先读目标与中点值，再决定如何排除。','读取中点，判断可以证明的排除方向',6,mid,q=q)
        if value<target:
            left=mid+1;frame('已排除 mid 及其左侧；剩余候选仍满足当前区间契约。','left = mid + 1',7,mid)
        elif lower:
            right=mid;frame('右边界移动到 mid，最左合格位置仍可能恰好是 mid。','right = mid',9,mid)
        elif value>target:
            right=mid-1;frame('已排除 mid 及其右侧，保留所有尚可能命中的位置。','right = mid - 1',9,mid)
        else:
            frame('命中：当前 mid 的值等于目标，返回它的索引。','返回当前索引',11,mid,mid)
            return frames,mid
    answer=left if lower else -1
    frame('左右边界重合，得到第一个合格位置；等于数组长度表示插在尾部。' if lower else 'left 已越过 right，候选集合为空；目标不存在。','返回左边界' if lower else '返回未命中值 -1',10 if lower else 12,answer=answer)
    return frames,answer

def case(cid,name,purpose,nums,target,lower=False):
    frames,answer=trace(nums,target,lower)
    return {'id':cid,'name':name,'purpose':purpose,'input':{'nums':nums,'target':target},'expected':answer,'frames':frames}

def make_lesson():
    normal=case('normal','正常：两轮命中','从第一次比较读出可以整段淘汰的证据',[2,5,8,12,16,21,27,31,38],27)
    counter=case('counter','反例：两个候选','若更新为 left=mid，这个输入可能停在同一位置',[2,5],5)
    missing=case('missing','未命中：目标在两个值之间','区间最终为空，而不是挑最接近的数字作为答案',[2,5,8,12],7)
    edge=case('edge','边界：只有一个候选','left==right 时仍需比较，所以闭区间循环不能写成 left<right',[8],8)
    stages=[
      {'title':'概念诊断','goal':'精确查找的对象是候选索引；判断依赖有序性，而不是背移动口诀。','case':'normal','notes':['当前目标为 27。灰色区域表示已经用证据排除的索引。','输入样例说明题意；下面的问题要求说明为何能够排除一整段。'],'questions':[question('二分能删除一大片候选，真正依赖什么？',['当前比较与候选顺序能证明整段不可能','mid 恰好处在数组几何中心','每轮随便丢弃一半也总能命中'],0,['正确。有序性把一次比较扩展成整段排除证据。','取中点控制缩减规模，但删除哪边仍需要比较证据。','缺少排除证明，会直接删除真实答案。'])]},
      {'title':'反例与瓶颈','goal':'用两个候选看出“排除边界”和“严格缩小”必须同时满足。','case':'counter','notes':['数组 [2,5]，目标 5。第一轮 mid=0。若使用 left=mid，left 仍是 0，下一轮还会看到同一个中点。','正确操作必须排除已经证明不可能的 mid：将 left 移到其后方。'],'questions':[question('把本轮 left 更新为 mid，最直接的问题是什么？',['目标不存在了','候选规模可能不变，循环无法推进','时间复杂度一定变成 O(n²)'],1,['目标仍在数组里，问题在于更新没有真正缩小区间。','正确。两个候选时，中点取整可能仍等于 left。','这个反例揭露的是可能停滞，不能从小样例断言平方复杂度。'])]},
      {'title':'心智模型','goal':'把区间契约、可排除证据、终止条件和答案位置放到同一个模型中。','case':'edge','notes':['闭区间 [left,right] 的两个端点都属于候选集合。','当 left==right 时还有一个候选；当 left>right 时，候选集合才为空。','每次继续迭代都严格缩小区间。总共 O(log n) 次比较，只保留常数个索引。'],'questions':[question('left==right 时，当前候选集合是什么？',['已经为空','只剩一个位置，仍需比较','只能说明已经命中'],1,['闭区间包含两端，重合时还剩一个元素。','正确。必须比较这个唯一候选，才能命中或排除。','是否命中还取决于元素值与 target 的关系。'])]},
      {'title':'真实运行轨迹','goal':'亲自推进每个状态，解释高亮代码行怎样改变候选集合。','case':'normal','notes':['先回答当前帧的问题，再推进到边界更新后的状态。你也可以自由前后查看。','切换未命中与单元素案例，核对终止条件是否仍成立。'],'questions':[]},
      {'title':'手填槽位','goal':'把区间契约和排除证据翻译为自己的关键表达式。','notes':[],'questions':[]},
      {'title':'独立重写与迁移','goal':'离开已有骨架，从接口重写，并把精确命中改成边界定位。','notes':[],'questions':[]}
    ]
    slot_specs=[('right','初始右端点','闭区间必须落在最后一个有效索引。',['len(nums) - 1']),('loop','仍有候选','什么时候闭区间尚未为空？',['left <= right']),('mid','中点索引','用当前两个端点确定一个有效中点。',['(left + right) // 2','left + (right - left) // 2']),('smaller','小于目标的证据','比较当前候选的值，而不是比较索引。',['nums[mid] < target']),('left','排除左侧','已经证明 mid 也不可能命中。',['mid + 1']),('larger','大于目标的证据','哪一个比较结果支持排除右侧？',['nums[mid] > target']),('rightUpdate','排除右侧','已经证明 mid 及右侧均不能命中。',['mid - 1']),('hit','精确命中返回','题目要求返回命中元素的位置。',['mid']),('absent','未命中返回','使用题目规定的失败返回语义。',['-1'])]
    return {
      'meta':{'id':704,'title':'二分查找','slug':'binary-search','difficulty':'Easy','tags':['候选排除','闭区间契约','边界证明'],'source':'https://leetcode.com/problems/binary-search/','language':'Python'},
      'problem':{'summary':'在升序且元素互不相同的整数数组中查找 target。存在时返回索引，否则返回 -1；要求 O(log n) 时间。','signature':STARTER,'constraints':['数组有至少一个元素，元素按升序排列且互不相同。','返回的是索引，未命中返回 -1。','算法的时间复杂度应为 O(log n)。'],'examples':[{'input':'nums = [-1,0,3,5,9,12], target = 9','output':'4','purpose':'命中时返回位置 4，而不是数值 9。'},{'input':'nums = [-1,0,3,5,9,12], target = 2','output':'-1','purpose':'精确查找不会返回邻近值或插入位置。'}]},
      'model':{'headline':'一次比较，证明整段候选都不可能。','state':'候选索引闭区间 [left,right]，以及当前中点 mid。','contract':'若目标存在，它始终位于尚未排除的闭区间内。','operation':'读取 nums[mid]，按比较结果删除已证明不可能的整段。','invariant':'被删除的每个索引都无法命中 target；其余候选被完整保留。','boundary':'left==right 仍有一个候选；left>right 才为空。','answer':'值相等时返回 mid；候选为空时返回 -1。','complexity':{'time':'O(log n)','space':'O(1)'}},
      'ladder':[{'title':'线性候选','detail':'逐个比较能理解正确性，但无法满足对数级比较次数。','problem':'直接遍历数组'},{'title':'整段排除','detail':'用有序性将一次比较扩展到一整段索引。','problem':'#704 二分查找','current':True},{'title':'第一个合格位置','detail':'命中仍继续压缩边界；重新定义循环与答案位置。','problem':'#35 搜索插入位置'},{'title':'单调答案空间','detail':'候选可以变成速度或容量，用可行性谓词代替读取数组。','problem':'#875 爱吃香蕉的珂珂'}],
      'cases':[normal,counter,missing,edge],'stages':stages,
      'code':{'starter':STARTER,'skeleton':'class Solution:\n    def search(self, nums, target):\n        left, right = 0, {{right}}\n        while {{loop}}:\n            mid = {{mid}}\n            if {{smaller}}:\n                left = {{left}}\n            elif {{larger}}:\n                right = {{rightUpdate}}\n            else:\n                return {{hit}}\n        return {{absent}}','slots':[{'id':i,'label':label,'hint':hint,'accepted':accepted} for i,label,hint,accepted in slot_specs],'reference':MAIN,'checklist':['初始两个边界符合闭区间定义。','单元素输入依然进入一次比较。','继续迭代时必然严格减少候选个数。','精确命中返回索引，候选耗尽返回 -1。','已用正常、两个候选、未命中和单元素四类输入推演。']},
      'transfer':{'title':'迁移 #35：搜索插入位置','source':'https://leetcode.com/problems/search-insert-position/','summary':'仍是升序无重复数组，但目标不存在时需要返回保持有序的插入位置。将任务统一成“第一个不小于 target 的位置”。','preserved':['有序候选上的整段排除。','中点比较提供缩小范围的证据。'],'changed':['从精确命中改为定位边界。','采用半开区间 [left,right)，初始 right 可以等于 n。','相等时继续缩小右侧；终止后返回 left。'],'newProof':'小于 left 的位置全小于目标；从 right 起的位置全部不小于目标。两端重合时，唯一分界位置就是插入位置。','starter':TRANSFER_STARTER,'reference':TRANSFER,'checklist':['明确使用闭区间还是半开区间，并让循环与更新一致。','相等时仍保留最左边界的可能性。','能够返回 0 和 len(nums) 这两个合法插入位置。','不存在时返回插入位置而不是 -1。'],'questions':[question('nums[mid]==target 时，为什么这里仍然可以压缩右边界？',['问题已经变成边界位置，仍需统一证明分界','因为当前值一定不是目标','因为相等时总要删除整个左半'],0,['正确。保留 mid 可能是最左合格位置，并继续缩小边界。','相等的值当然是目标，但这不是当前模型的完整终止证明。','删除左侧会失去更左的合格位置。'])],'cases':[case('insert','迁移：插入中间','区间最后收敛到第一个不小于 2 的位置',[1,3,5,6],2,True),case('tail','迁移：插入末尾','合法答案可以等于数组长度，[left,right) 允许右端越界',[1,3,5,6],7,True)]}
    }

def verify_algorithms():
    main_ns={};transfer_ns={};exec(MAIN,main_ns);exec(TRANSFER,transfer_ns)
    main=main_ns['Solution']().search;lower=transfer_ns['Solution']().searchInsert;rng=random.Random(704)
    count=0
    for _ in range(250):
        nums=sorted(rng.sample(range(-50,51),rng.randint(1,35)))
        for target in (rng.randint(-60,60),nums[0],nums[-1]):
            expected=nums.index(target) if target in nums else -1
            lower_expected=next((i for i,n in enumerate(nums) if n>=target),len(nums))
            frames,value=trace(nums,target);lf,lv=trace(nums,target,True)
            assert value==main(nums,target)==expected
            assert lv==lower(nums,target)==lower_expected
            assert frames[-1]['state']['返回值']==value and lf[-1]['state']['返回值']==lv
            for row in frames[:-1]:
                s=row['state']
                if target in nums and row['line']==6:assert s['left']<=expected<=s['right']
            count+=2
    return count

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output-dir',required=True,type=Path);parser.add_argument('--home');args=parser.parse_args()
    count=verify_algorithms();lesson=make_lesson();args.output_dir.mkdir(parents=True,exist_ok=True)
    (args.output_dir/'lesson.json').write_text(json.dumps(lesson,ensure_ascii=False,indent=2),encoding='utf-8')
    output=build(lesson,args.output_dir/'leetcode_704_learning.html',args.home)
    print(json.dumps({'referenceAndTraceComparisons':count,'mainCases':len(lesson['cases']),'transferCases':len(lesson['transfer']['cases']),'html':str(output)},ensure_ascii=False,indent=2))
