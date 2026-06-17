# -*- coding: utf-8 -*-
"""Live rebuild: fetch gitlink journals (Day1-5), emit index.html. Stdlib only (runs on Linux CI)."""
import json, re, urllib.request
from datetime import datetime, timezone, timedelta

OWNER_REPO = "zhipu_course/AI-study-buddy-camp"
BASE = "https://gitlink.org.cn"
SRC = f"{BASE}/{OWNER_REPO}/issues/1"
NDAYS = 5
UA = "Mozilla/5.0 (compatible; daka-refresh)"

def api(path):
    req = urllib.request.Request(BASE + path, headers={"User-Agent": UA, "Accept": "application/json",
                                                        "Referer": f"{BASE}/{OWNER_REPO}/issues/1"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.load(r)

def clean_text(s):
    if not s:
        return ''
    s = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', s)
    s = re.sub(r'^[ \t]*#{1,6}[ \t]*', '', s, flags=re.M)
    s = re.sub(r'^[ \t]*>[ \t]?', '', s, flags=re.M)
    s = s.replace('**', '').replace('__', '').replace('`', '')
    s = re.sub(r'(?<![\*\w])\*(?!\*)', '', s)
    s = re.sub(r'[ \t]+', ' ', s)
    s = re.sub(r'\n{3,}', '\n\n', s)
    return s.strip()

def parts_of(notes):
    parts, pos = [], 0
    for m in re.finditer(r'!\[[^\]]*\]\(([^)]*)\)', notes):
        ct = clean_text(notes[pos:m.start()])
        if ct:
            parts.append({'t': 't', 'v': ct})
        u = m.group(1)
        full = (BASE + u) if u.startswith('/') else u
        parts.append({'t': 'i', 'v': full})
        pos = m.end()
    tail = clean_text(notes[pos:])
    if tail:
        parts.append({'t': 't', 'v': tail})
    return parts

rows, seq, nimg = [], 0, 0
for idx in range(1, NDAYS + 1):
    try:
        data = api(f"/api/v1/{OWNER_REPO}/issues/{idx}/journals?page=1&limit=200")
    except Exception as e:
        print(f"WARN day{idx}: {e}")
        continue
    for j in data.get('journals', []):
        if not j.get('notes'):
            continue
        u = j.get('user') or {}
        seq += 1
        parts = parts_of(j['notes'])
        nimg += sum(1 for p in parts if p['t'] == 'i')
        rows.append({'seq': seq, 'day': idx,
                     'name': u.get('name') or u.get('login'),
                     'login': u.get('login'),
                     'time': j.get('created_at'),
                     'parts': parts,
                     'txt': ' '.join(p['v'] for p in parts if p['t'] == 't')})

DATA_JSON = json.dumps(rows, ensure_ascii=False)
STAMP = (datetime.now(timezone.utc) + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M')

TEMPLATE = r"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI 打卡汇总 · 实时</title>
<style>
:root{--bg:#f5f6f8;--panel:#fff;--ink:#1f2430;--body:#33384a;--muted:#8a91a0;--line:#e7e9ee;--hover:#fafbfc;--off:#f1f3f5;
--d1:#2563eb;--d2:#16a34a;--d3:#d97706;--d4:#6b7280;--d5:#ea580c;}
html[data-theme=dark]{--bg:#0f1115;--panel:#171a21;--ink:#e8eaf0;--body:#cdd2dd;--muted:#878f9e;--line:#262b35;--hover:#1b1f28;--off:#222734;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",Segoe UI,Roboto,sans-serif;-webkit-font-smoothing:antialiased;line-height:1.6;transition:background .2s,color .2s}
.wrap{max-width:1060px;margin:0 auto;padding:28px 20px 64px}
.top{display:flex;align-items:flex-start;justify-content:space-between;gap:16px}
header h1{font-size:24px;font-weight:600;margin:0 0 6px}
header .meta{color:var(--muted);font-size:13px;margin:0}
header .meta a{color:var(--muted)}
.theme{flex:none;border:1px solid var(--line);background:var(--panel);color:var(--ink);font:inherit;font-size:13px;padding:8px 14px;border-radius:999px;cursor:pointer}
.tabs{display:flex;gap:6px;margin:22px 0 18px;border-bottom:1px solid var(--line)}
.tabs button{border:0;background:none;font:inherit;font-size:15px;color:var(--muted);padding:10px 16px;cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-1px;font-weight:500}
.tabs button.active{color:var(--ink);border-bottom-color:var(--ink)}
.view{display:none}.view.active{display:block}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:18px}
.stat{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px 18px}
.stat .k{color:var(--muted);font-size:12px;margin:0 0 6px}.stat .v{font-size:26px;font-weight:600;margin:0}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:18px 20px;margin-bottom:18px}
.panel h2{font-size:14px;font-weight:600;color:var(--muted);margin:0 0 14px}
.bars{display:flex;flex-direction:column;gap:10px}
.barrow{display:grid;grid-template-columns:54px 1fr 46px;align-items:center;gap:10px;font-size:13px}
.barrow .lab{color:var(--muted)}
.track{display:block;height:14px;background:var(--bg);border-radius:8px;overflow:hidden}
.fill{display:block;height:100%;border-radius:8px;transition:width .6s cubic-bezier(.2,.8,.2,1)}
.matrix{width:100%;border-collapse:separate;border-spacing:0;font-size:14px}
.matrix th,.matrix td{padding:10px 8px;text-align:center;border-bottom:1px solid var(--line)}
.matrix th{position:sticky;top:0;background:var(--panel);color:var(--muted);font-weight:600;font-size:12px;cursor:pointer}
.matrix th.l,.matrix td.l{text-align:left}
.matrix tr.person{cursor:pointer}.matrix tr.person:hover td{background:var(--hover)}
.matrix .id{color:var(--muted);font-size:12px}
.dot{display:inline-flex;align-items:center;justify-content:center;width:26px;height:26px;border-radius:8px;font-weight:700}
.dot.on{color:#fff}.dot.off{color:var(--muted);background:var(--off)}
.pbar{display:flex;align-items:center;gap:8px}
.pbar .pt{display:block;flex:1;height:10px;background:var(--bg);border-radius:6px;overflow:hidden;min-width:60px}
.pbar .pf{display:block;height:100%;background:#22c55e;border-radius:6px}
.pbar .pn{font-variant-numeric:tabular-nums;font-weight:600;font-size:13px;min-width:34px;text-align:right}
.controls{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:16px}
.controls input,.controls select{font:inherit;font-size:14px;padding:9px 12px;border:1px solid var(--line);border-radius:10px;background:var(--panel);color:var(--ink);outline:none}
.controls input{flex:1;min-width:200px}
.chips{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:14px}
.chip{font-size:13px;padding:7px 13px;border-radius:999px;border:1px solid var(--line);background:var(--panel);cursor:pointer;color:var(--muted);font-weight:500}
.chip.active{color:#fff;border-color:transparent}
.count{color:var(--muted);font-size:13px;margin:0 0 12px}
.clist{display:flex;flex-direction:column;gap:12px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;overflow:hidden}
.card .chead{display:flex;align-items:center;gap:10px;padding:12px 16px;border-bottom:1px solid var(--line)}
.badge{font-size:12px;font-weight:600;padding:3px 10px;border-radius:999px;color:#fff;white-space:nowrap}
.card .who{font-weight:600}.card .uid{color:var(--muted);font-size:12px}.card .when{margin-left:auto;color:var(--muted);font-size:12px}
.card .body{padding:13px 16px}
.ptext{white-space:pre-wrap;font-size:14.5px;color:var(--body)}
.ptext+.shot,.shot+.ptext,.shot+.shot{margin-top:10px}
.shot{display:block;max-width:100%;height:auto;border:1px solid var(--line);border-radius:10px;background:var(--off);min-height:30px}
.empty{color:var(--muted);text-align:center;padding:40px 0;font-size:14px}
.foot{color:var(--muted);font-size:12px;margin-top:24px;text-align:center}
@media(max-width:640px){.stats{grid-template-columns:1fr}.matrix .id{display:none}}
</style>
</head>
<body>
<div class="wrap">
  <div class="top">
    <header>
      <h1>AI Study Buddy Camp · 打卡汇总</h1>
      <p class="meta">数据来源 <a href="__SRC__" target="_blank" rel="noopener">gitlink.org.cn</a> · 最后更新 <b>__STAMP__</b>（每 30 分钟自动刷新）· <span id="mPeople"></span> 人 · <span id="mTotal"></span> 条 · __NIMG__ 图</p>
    </header>
    <button class="theme" id="themeBtn">🌙 深色</button>
  </div>
  <nav class="tabs"><button data-tab="progress" class="active">进度总览</button><button data-tab="comments">评论明细</button></nav>
  <section id="progress" class="view active">
    <div class="stats">
      <div class="stat"><p class="k">参与人数</p><p class="v" id="sPeople">–</p></div>
      <div class="stat"><p class="k">总打卡数</p><p class="v" id="sTotal">–</p></div>
      <div class="stat"><p class="k">人均完成</p><p class="v" id="sAvg">–</p></div>
    </div>
    <div class="panel"><h2>每日打卡人数</h2><div class="bars" id="dayBars"></div></div>
    <div class="panel"><h2>每人进度（点姓名查看 ta 的评论）</h2>
      <table class="matrix"><thead><tr>
        <th class="l" data-sort="rank">#</th><th class="l" data-sort="name">名称</th>
        <th data-sort="d1">D1</th><th data-sort="d2">D2</th><th data-sort="d3">D3</th><th data-sort="d4">D4</th><th data-sort="d5">D5</th>
        <th data-sort="count">完成进度 ▾</th></tr></thead><tbody id="matrixBody"></tbody></table>
    </div>
  </section>
  <section id="comments" class="view">
    <div class="controls">
      <input id="q" type="search" placeholder="搜索名称 / ID / 评论内容…">
      <select id="sort"><option value="seq">默认顺序</option><option value="time_desc">时间（新→旧）</option><option value="time_asc">时间（旧→新）</option><option value="name">按名称</option><option value="day">按任务</option></select>
    </div>
    <div class="chips" id="dayChips"></div><p class="count" id="cCount"></p><div class="clist" id="cList"></div>
  </section>
  <p class="foot">本页由 GitHub Actions 定时从 gitlink 重新抓取并自动部署 · 最后更新 __STAMP__</p>
</div>
<script>
const DATA = __DATA__;
const DI={1:{label:'Day 1',hex:'#2563eb'},2:{label:'Day 2',hex:'#16a34a'},3:{label:'Day 3',hex:'#d97706'},4:{label:'Day 4',hex:'#6b7280'},5:{label:'Day 5',hex:'#ea580c'}};
const TOTAL=DATA.length;
const people={};DATA.forEach(c=>{(people[c.login]=people[c.login]||{name:c.name,login:c.login,days:new Set()}).days.add(c.day);});
let prog=Object.values(people).map(p=>({name:p.name,login:p.login,days:p.days,count:p.days.size}));
prog.sort((a,b)=>b.count-a.count||a.name.localeCompare(b.name,'zh'));prog.forEach((p,i)=>p.rank=i+1);
const perDay={};for(let d=1;d<=5;d++)perDay[d]=prog.filter(p=>p.days.has(d)).length;
const NP=prog.length,avg=prog.reduce((s,p)=>s+p.count,0)/(NP||1);
mPeople.textContent=NP;mTotal.textContent=TOTAL;sPeople.textContent=NP;sTotal.textContent=TOTAL;sAvg.textContent=avg.toFixed(1)+' / 5';
const maxd=Math.max(...Object.values(perDay),1);
dayBars.innerHTML=[1,2,3,4,5].map(d=>{const n=perDay[d],w=Math.round(n/maxd*100);return `<div class="barrow"><span class="lab">${DI[d].label}</span><span class="track"><span class="fill" style="width:${w}%;background:${DI[d].hex}"></span></span><span class="lab" style="text-align:right">${n} 人</span></div>`;}).join('');
let mSort='count',mDir=-1;
function esc(s){return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function renderMatrix(){const arr=[...prog].sort((a,b)=>{let x,y;if(mSort==='name')return mDir*a.name.localeCompare(b.name,'zh');if(mSort==='rank'){x=a.rank;y=b.rank;}else if(mSort[0]==='d'){const d=+mSort[1];x=a.days.has(d)?1:0;y=b.days.has(d)?1:0;}else{x=a.count;y=b.count;}return mDir*(x-y);});
matrixBody.innerHTML=arr.map(p=>{const cells=[1,2,3,4,5].map(d=>p.days.has(d)?`<td><span class="dot on" style="background:${DI[d].hex}">✓</span></td>`:`<td><span class="dot off">·</span></td>`).join('');const w=Math.round(p.count/5*100);return `<tr class="person" data-login="${esc(p.login)}"><td class="l">${p.rank}</td><td class="l"><b>${esc(p.name)}</b> <span class="id">${esc(p.login)}</span></td>${cells}<td><div class="pbar"><span class="pt"><span class="pf" style="width:${w}%"></span></span><span class="pn">${p.count}/5</span></div></td></tr>`;}).join('');
document.querySelectorAll('tr.person').forEach(tr=>tr.onclick=()=>{const lg=tr.dataset.login;q.value=lg;state.q=lg;state.day=0;syncChips();renderList();switchTab('comments');});}
document.querySelectorAll('.matrix th[data-sort]').forEach(th=>th.onclick=()=>{const k=th.dataset.sort;if(mSort===k)mDir*=-1;else{mSort=k;mDir=(k==='name'||k==='rank')?1:-1;}renderMatrix();});
const state={q:'',day:0,sort:'seq'};
const chips=[{d:0,t:'全部'}].concat([1,2,3,4,5].map(d=>({d,t:DI[d].label+' ('+perDay[d]+')'})));
dayChips.innerHTML=chips.map(c=>`<span class="chip${c.d===0?' active':''}" data-day="${c.d}">${c.t}</span>`).join('');
function syncChips(){document.querySelectorAll('.chip').forEach(ch=>{const d=+ch.dataset.day,on=d===state.day;ch.classList.toggle('active',on);ch.style.background=on?(d?DI[d].hex:'var(--ink)'):'';ch.style.color=on?'#fff':'';});}
document.querySelectorAll('.chip').forEach(ch=>ch.onclick=()=>{state.day=+ch.dataset.day;syncChips();renderList();});
q.oninput=e=>{state.q=e.target.value.trim();renderList();};
document.getElementById('sort').onchange=e=>{state.sort=e.target.value;renderList();};
function bodyHtml(parts){return parts.map(p=>p.t==='i'?`<img class="shot" loading="lazy" src="${p.v}" alt="截图" referrerpolicy="no-referrer">`:`<div class="ptext">${esc(p.v)}</div>`).join('');}
function renderList(){let arr=DATA.filter(c=>{if(state.day&&c.day!==state.day)return false;if(state.q){const x=state.q.toLowerCase();if(!((c.name||'').toLowerCase().includes(x)||(c.login||'').toLowerCase().includes(x)||(c.txt||'').toLowerCase().includes(x)))return false;}return true;});
const s=state.sort;arr=[...arr].sort((a,b)=>s==='time_desc'?(b.time||'').localeCompare(a.time||''):s==='time_asc'?(a.time||'').localeCompare(b.time||''):s==='name'?a.name.localeCompare(b.name,'zh'):s==='day'?a.day-b.day||a.seq-b.seq:a.seq-b.seq);
cCount.textContent=`显示 ${arr.length} / ${TOTAL} 条`;
cList.innerHTML=arr.length?arr.map(c=>`<div class="card"><div class="chead"><span class="badge" style="background:${DI[c.day].hex}">${DI[c.day].label}</span><span class="who">${esc(c.name)}</span><span class="uid">${esc(c.login)}</span><span class="when">${esc(c.time||'')}</span></div><div class="body">${bodyHtml(c.parts)}</div></div>`).join(''):'<div class="empty">没有匹配的评论</div>';}
function switchTab(n){document.querySelectorAll('.tabs button').forEach(b=>b.classList.toggle('active',b.dataset.tab===n));document.querySelectorAll('.view').forEach(v=>v.classList.toggle('active',v.id===n));window.scrollTo({top:0,behavior:'smooth'});}
document.querySelectorAll('.tabs button').forEach(b=>b.onclick=()=>switchTab(b.dataset.tab));
const root=document.documentElement,tb=document.getElementById('themeBtn');
function applyTheme(t){if(t==='dark'){root.setAttribute('data-theme','dark');tb.textContent='☀ 浅色';}else{root.removeAttribute('data-theme');tb.textContent='🌙 深色';}}
applyTheme(localStorage.getItem('theme')||(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'));
tb.onclick=()=>{const t=root.getAttribute('data-theme')==='dark'?'light':'dark';localStorage.setItem('theme',t);applyTheme(t);};
renderMatrix();syncChips();renderList();
</script>
</body>
</html>"""

html = (TEMPLATE.replace('__DATA__', DATA_JSON).replace('__SRC__', SRC)
        .replace('__STAMP__', STAMP).replace('__NIMG__', str(nimg)))
open('index.html', 'w', encoding='utf-8').write(html)
print(f"built index.html | comments={len(rows)} images={nimg} stamp={STAMP} bytes={len(html)}")
