# -*- coding: utf-8 -*-
"""Live rebuild with PERMANENT local images + designed front-end.
Fetch gitlink journals (Day1-5) -> download+resize screenshots into images/<uuid>.jpg
(only new) -> emit index.html. Stdlib + Pillow (Linux CI)."""
import json, re, os, io, urllib.request
from PIL import Image

OWNER_REPO = "zhipu_course/AI-study-buddy-camp"
BASE = "https://gitlink.org.cn"
SRC = f"{BASE}/{OWNER_REPO}/issues/1"
NDAYS = 5
UA = "Mozilla/5.0 (compatible; daka-refresh)"
IMGDIR = "images"
AVDIR = "avatars"
os.makedirs(IMGDIR, exist_ok=True)
os.makedirs(AVDIR, exist_ok=True)

def api(path):
    req = urllib.request.Request(BASE + path, headers={"User-Agent": UA, "Accept": "application/json",
                                                       "Referer": f"{BASE}/{OWNER_REPO}/issues/1"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.load(r)

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": f"{BASE}/{OWNER_REPO}/issues/1"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()

def local_image(url):
    uuid = re.sub(r'[^A-Za-z0-9_-]', '_', url.rstrip('/').split('/')[-1]) or 'img'
    rel = f"{IMGDIR}/{uuid}.jpg"
    if os.path.exists(rel):
        return rel
    try:
        data = fetch(url)
        im = Image.open(io.BytesIO(data))
        if im.mode in ('RGBA', 'LA', 'P'):
            im = im.convert('RGBA')
            bg = Image.new('RGB', im.size, (255, 255, 255))
            bg.paste(im, mask=im.split()[-1]); im = bg
        else:
            im = im.convert('RGB')
        w, h = im.size
        if w > 1000:
            im = im.resize((1000, round(h * 1000 / w)))
        im.save(rel, 'JPEG', quality=72, optimize=True)
        return rel
    except Exception as e:
        print(f"WARN image {url}: {e}")
        return url

def local_avatar(login, url):
    safe = re.sub(r'[^A-Za-z0-9_-]', '_', login or 'u')
    rel = f"{AVDIR}/{safe}.jpg"
    if os.path.exists(rel):
        return rel
    if not url:
        return ''
    try:
        im = Image.open(io.BytesIO(fetch(url)))
        if im.mode in ('RGBA', 'LA', 'P'):
            im = im.convert('RGBA'); bg = Image.new('RGB', im.size, (255, 255, 255))
            bg.paste(im, mask=im.split()[-1]); im = bg
        else:
            im = im.convert('RGB')
        im = im.resize((96, 96))
        im.save(rel, 'JPEG', quality=82, optimize=True)
        return rel
    except Exception as e:
        print(f"WARN avatar {login}: {e}")
        return url

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
        parts.append({'t': 'i', 'v': local_image(full)})
        pos = m.end()
    tail = clean_text(notes[pos:])
    if tail:
        parts.append({'t': 't', 'v': tail})
    return parts

rows, seq, nimg, latest, av_map = [], 0, 0, '', {}
for idx in range(1, NDAYS + 1):
    try:
        data = api(f"/api/v1/{OWNER_REPO}/issues/{idx}/journals?page=1&limit=200")
    except Exception as e:
        print(f"WARN day{idx}: {e}"); continue
    for j in data.get('journals', []):
        if not j.get('notes'):
            continue
        u = j.get('user') or {}
        lg = u.get('login')
        if lg not in av_map:
            av_map[lg] = local_avatar(lg, u.get('image_url'))
        seq += 1
        parts = parts_of(j['notes'])
        nimg += sum(1 for p in parts if p['t'] == 'i')
        t = j.get('created_at') or ''
        latest = max(latest, t)
        rows.append({'seq': seq, 'day': idx, 'name': u.get('name') or u.get('login'),
                     'login': u.get('login'), 'time': t, 'parts': parts,
                     'txt': ' '.join(p['v'] for p in parts if p['t'] == 't')})

DATA_JSON = json.dumps(rows, ensure_ascii=False)
AV_JSON = json.dumps(av_map, ensure_ascii=False)
LATEST = latest or '—'

TEMPLATE = r"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>打卡汇总 · AI Study Buddy Camp</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2032%2032'%3E%3Crect%20width='32'%20height='32'%20rx='7'%20fill='%235b6bd6'/%3E%3Crect%20x='8'%20y='16'%20width='4'%20height='8'%20rx='1'%20fill='white'/%3E%3Crect%20x='14'%20y='11'%20width='4'%20height='13'%20rx='1'%20fill='white'/%3E%3Crect%20x='20'%20y='7'%20width='4'%20height='17'%20rx='1'%20fill='white'/%3E%3C/svg%3E">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root{
  --paper:#f6f6f3; --card:#fffffe; --ink:#17181c; --body:#3c3e46; --muted:#7c7f88; --faint:#b9bcc4;
  --line:#e7e7e2; --line2:#dededa; --accent:#5b6bd6; --accent-soft:#eef0fb;
  --d1:#2f9e8f; --d2:#3b82c4; --d3:#5b6bd6; --d4:#8a5cc8; --d5:#c2557e;
  --fdisp:'Space Grotesk',system-ui,sans-serif;
  --fmono:ui-monospace,'SF Mono','JetBrains Mono',Menlo,Consolas,monospace;
  --fsans:system-ui,-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;
}
html[data-theme=dark]{
  --paper:#0e0f13; --card:#16181e; --ink:#eceef3; --body:#c4c7d0; --muted:#878b96; --faint:#4a4e58;
  --line:#23252d; --line2:#2c2f38; --accent:#8b97f0; --accent-soft:#1b1e2c;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--fsans);line-height:1.65;
  -webkit-font-smoothing:antialiased;transition:background .25s,color .25s}
.wrap{max-width:980px;margin:0 auto;padding:40px 24px 80px}
.eyebrow{font-family:var(--fmono);font-size:11px;letter-spacing:.18em;text-transform:uppercase;color:var(--muted)}
a{color:var(--accent)}
:focus-visible{outline:2px solid var(--accent);outline-offset:3px;border-radius:3px}

/* header */
.head{display:flex;justify-content:space-between;align-items:flex-start;gap:20px;margin-bottom:8px}
h1{font-family:var(--fdisp);font-weight:600;font-size:38px;line-height:1.05;margin:10px 0 0;letter-spacing:-.01em}
.sub{color:var(--muted);font-size:13px;margin:12px 0 0;font-family:var(--fmono);letter-spacing:.01em}
.sub a{color:var(--muted);text-decoration:underline;text-underline-offset:2px}
.toggle{flex:none;font-family:var(--fmono);font-size:12px;letter-spacing:.08em;color:var(--ink);background:none;
  border:1px solid var(--line2);border-radius:999px;padding:8px 14px;cursor:pointer;transition:.15s}
.toggle:hover{border-color:var(--muted)}

/* tabs */
.tabs{display:flex;gap:28px;margin:34px 0 28px;border-bottom:1px solid var(--line)}
.tabs button{appearance:none;border:0;background:none;font-family:var(--fdisp);font-size:15px;font-weight:500;
  color:var(--faint);padding:0 0 12px;margin-bottom:-1px;cursor:pointer;border-bottom:2px solid transparent;transition:.15s}
.tabs button:hover{color:var(--body)}
.tabs button.active{color:var(--ink);border-bottom-color:var(--accent)}
.view{display:none}.view.active{display:block;animation:rise .4s ease}
@keyframes rise{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}

/* thesis */
.thesis{font-size:19px;line-height:1.6;color:var(--body);max-width:46ch;margin:4px 0 30px}
.thesis b{color:var(--ink);font-weight:500}

/* stage funnel — signature */
.sec-h{display:flex;align-items:baseline;gap:12px;margin:0 0 18px}
.sec-h .zh{font-family:var(--fdisp);font-weight:500;font-size:15px;color:var(--ink)}
.funnel{padding:22px 4px 4px;border-top:1px solid var(--line)}
.bars{display:grid;grid-template-columns:repeat(5,1fr);gap:14px}
.bcol{height:178px;display:flex;flex-direction:column;justify-content:flex-end;align-items:center;gap:11px}
.stage-n{font-family:var(--fdisp);font-weight:600;font-size:30px;line-height:1;font-variant-numeric:tabular-nums}
.bar{width:100%;max-width:54px;border-radius:6px 6px 2px 2px;min-height:4px;transition:height .85s cubic-bezier(.2,.85,.25,1)}
.baseline{height:1px;background:var(--line2);margin:0 0 14px}
.labels{display:grid;grid-template-columns:repeat(5,1fr);gap:14px;text-align:center}
.lcol .code{font-family:var(--fmono);font-size:12px;font-weight:500;letter-spacing:.06em}
.lcol .name{font-size:12px;color:var(--muted);margin-top:3px}
.funnel-cap{display:flex;justify-content:space-between;font-family:var(--fmono);font-size:11px;
  color:var(--faint);letter-spacing:.04em;margin:14px 2px 0}

/* metrics */
.metrics{display:grid;grid-template-columns:repeat(4,1fr);margin:36px 0 8px}
.m{padding:4px 18px;border-left:1px solid var(--line)}
.m:first-child{padding-left:0;border-left:0}
.m-k{font-family:var(--fmono);font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
.m-v{font-family:var(--fdisp);font-weight:600;font-size:34px;line-height:1.1;margin-top:6px;font-variant-numeric:tabular-nums}
.m-zh{font-size:12px;color:var(--muted);margin-top:1px}

/* roster */
.roster{width:100%;border-collapse:collapse;font-size:14px;margin-top:4px}
.roster th{font-family:var(--fmono);font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);
  font-weight:400;text-align:center;padding:10px 6px;border-bottom:1px solid var(--line2);cursor:pointer;user-select:none}
.roster th.l{text-align:left}
.roster td{padding:11px 6px;border-bottom:1px solid var(--line);text-align:center;vertical-align:middle}
.roster tr:hover td{background:var(--card)}
.rk{font-family:var(--fmono);font-size:12px;color:var(--faint)}
.who{display:flex;align-items:center;gap:9px}
.who .nm{font-weight:500;color:var(--ink)}
.who .id{font-family:var(--fmono);font-size:11px;color:var(--muted)}
.av{width:24px;height:24px;border-radius:50%;object-fit:cover;border:1px solid var(--line2);background:var(--off);flex:none}
.avlg{width:30px;height:30px}
.wall{display:flex;flex-wrap:wrap;gap:8px;margin:2px 0 32px}
.wav{width:40px;height:40px;border-radius:50%;object-fit:cover;border:1px solid var(--line2);background:var(--off);cursor:pointer;transition:transform .13s,box-shadow .13s}
.wav:hover{transform:translateY(-3px) scale(1.07);box-shadow:0 6px 16px -6px rgba(0,0,0,.32)}
.wav-x{display:inline-flex;align-items:center;justify-content:center;font-family:var(--fdisp);font-weight:600;font-size:16px;color:var(--muted)}
.cell{display:inline-flex;width:20px;height:20px;border-radius:6px;border:1px solid var(--line2)}
.cell.on{border:0}
.score{font-family:var(--fmono);font-size:13px;color:var(--body);white-space:nowrap}
.score b{font-family:var(--fdisp);font-weight:600;color:var(--ink);font-size:15px}
.person{cursor:pointer}

/* comments */
.controls{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:14px}
.controls input,.controls select{font:inherit;font-size:14px;padding:10px 13px;border:1px solid var(--line2);
  border-radius:10px;background:var(--card);color:var(--ink);outline:none}
.controls input{flex:1;min-width:200px}
.controls input::placeholder{color:var(--faint)}
.chips{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px}
.chip{font-family:var(--fmono);font-size:12px;letter-spacing:.03em;padding:6px 12px;border-radius:8px;
  border:1px solid var(--line2);background:none;color:var(--muted);cursor:pointer;transition:.13s}
.chip:hover{border-color:var(--muted);color:var(--body)}
.chip.active{color:#fff;border-color:transparent}
.count{font-family:var(--fmono);font-size:12px;color:var(--muted);margin:0 0 14px;letter-spacing:.03em}
.clist{display:flex;flex-direction:column;gap:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;overflow:hidden;transition:border-color .15s,transform .15s,box-shadow .15s}
.card:hover{border-color:var(--line2);transform:translateY(-1px);box-shadow:0 6px 22px -14px rgba(0,0,0,.25)}
.chead{display:flex;align-items:center;gap:11px;padding:13px 16px 12px}
.tag{font-family:var(--fmono);font-size:11px;font-weight:500;letter-spacing:.05em;color:#fff;padding:3px 8px;border-radius:6px}
.chead .nm{font-weight:500}
.chead .id{font-family:var(--fmono);font-size:11px;color:var(--muted)}
.chead .tm{margin-left:auto;font-family:var(--fmono);font-size:11px;color:var(--faint)}
.cbody{padding:0 16px 15px}
.ptext{white-space:pre-wrap;font-size:14.5px;color:var(--body);line-height:1.7}
.ptext+.shot,.shot+.ptext,.shot+.shot{margin-top:11px}
.shot{display:block;max-width:100%;height:auto;border:1px solid var(--line);border-radius:9px;background:var(--paper);min-height:30px}
.empty{color:var(--muted);text-align:center;padding:48px 0;font-family:var(--fmono);font-size:13px}
.foot{margin-top:40px;padding-top:18px;border-top:1px solid var(--line);font-family:var(--fmono);
  font-size:11px;color:var(--faint);letter-spacing:.03em;text-align:center;line-height:1.8}
@media(max-width:680px){
  h1{font-size:30px}.wrap{padding:28px 18px 60px}
  .metrics{grid-template-columns:repeat(2,1fr);gap:18px 0}
  .m:nth-child(3){padding-left:0;border-left:0}
  .stage-name{display:none}.roster .id{display:none}
}
@media(prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
</style>
</head>
<body>
<div class="wrap">
  <div class="head">
    <div>
      <div class="eyebrow">AI Study Buddy Camp · 2026</div>
      <h1>打卡汇总</h1>
      <p class="sub">更新于 __LATEST__ · 每 30 分钟自动同步 · 源 <a href="__SRC__" target="_blank" rel="noopener">gitlink</a></p>
    </div>
    <button class="toggle" id="themeBtn">DARK</button>
  </div>

  <nav class="tabs"><button data-tab="overview" class="active">进度总览</button><button data-tab="feed">评论明细</button></nav>

  <section id="overview" class="view active">
    <p class="thesis"><b id="heroN">–</b> 位同学，正穿过这场 Vibe Coding 学习营的 <b>五个阶段</b>。下面是这支小队的行进轨迹。</p>

    <div class="sec-h"><span class="eyebrow">Members</span><span class="zh">参与同学 · <span id="wallN">–</span> 人 · 点头像看 ta 的评论</span></div>
    <div class="wall" id="wall"></div>

    <div class="sec-h"><span class="eyebrow">Stage funnel</span><span class="zh">阶段漏斗 · 每个阶段的打卡人数</span></div>
    <div class="funnel" id="funnel"></div>
    <div class="funnel-cap"><span>入营</span><span>结营 →</span></div>

    <div class="metrics" id="metrics"></div>

    <div class="sec-h" style="margin-top:44px"><span class="eyebrow">Roster</span><span class="zh">每人进度 · 点姓名看 ta 的评论</span></div>
    <table class="roster"><thead><tr>
      <th class="l" data-sort="rank">#</th><th class="l" data-sort="name">同学</th>
      <th data-sort="d1">D1</th><th data-sort="d2">D2</th><th data-sort="d3">D3</th><th data-sort="d4">D4</th><th data-sort="d5">D5</th>
      <th data-sort="count">完成 ↓</th></tr></thead><tbody id="roster"></tbody></table>
  </section>

  <section id="feed" class="view">
    <div class="controls">
      <input id="q" type="search" placeholder="搜索同学 / ID / 评论内容…">
      <select id="sort"><option value="seq">默认顺序</option><option value="time_desc">时间 · 新→旧</option><option value="time_asc">时间 · 旧→新</option><option value="name">按姓名</option><option value="day">按阶段</option></select>
    </div>
    <div class="chips" id="chips"></div><p class="count" id="cCount"></p><div class="clist" id="cList"></div>
  </section>

  <p class="foot">页面与 __NIMG__ 张截图均永久托管于 GitHub · GitHub Actions 每 30 分钟自动从 gitlink 重新抓取部署<br>数据更新至 __LATEST__</p>
</div>

<script>
const DATA = __DATA__;
const AV = __AV__;
const DI={
 1:{c:'D1',n:'案例体验',hex:'#2f9e8f'},2:{c:'D2',n:'动手准备',hex:'#3b82c4'},3:{c:'D3',n:'学会对话',hex:'#5b6bd6'},
 4:{c:'D4',n:'第一个作品',hex:'#8a5cc8'},5:{c:'D5',n:'作品展示',hex:'#c2557e'}};
const TOTAL=DATA.length;
const people={};DATA.forEach(c=>{(people[c.login]=people[c.login]||{name:c.name,login:c.login,days:new Set()}).days.add(c.day);});
let prog=Object.values(people).map(p=>({name:p.name,login:p.login,days:p.days,count:p.days.size}));
prog.sort((a,b)=>b.count-a.count||a.name.localeCompare(b.name,'zh'));prog.forEach((p,i)=>p.rank=i+1);
const perDay={};for(let d=1;d<=5;d++)perDay[d]=prog.filter(p=>p.days.has(d)).length;
const NP=prog.length, UNIT=prog.reduce((s,p)=>s+p.count,0), AVG=(UNIT/(NP||1));
const esc=s=>(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
const av=(lg,big)=>{const s=AV[lg];return s?`<img class="av${big?' avlg':''}" src="${s}" alt="" loading="lazy">`:'';};

document.getElementById('heroN').textContent=NP;

// funnel
const MAXD=Math.max(...Object.values(perDay),1);
const bars=[1,2,3,4,5].map(d=>{const n=perDay[d];const px=n?Math.max(8,Math.round(n/MAXD*150)):4;
  return `<div class="bcol"><div class="stage-n" style="color:${n?DI[d].hex:'var(--faint)'}">${n}</div><div class="bar" style="height:${px}px;background:${n?DI[d].hex:'var(--line2)'}"></div></div>`;}).join('');
const labels=[1,2,3,4,5].map(d=>`<div class="lcol"><div class="code" style="color:${DI[d].hex}">${DI[d].c}</div><div class="name">${DI[d].n}</div></div>`).join('');
document.getElementById('funnel').innerHTML=`<div class="bars">${bars}</div><div class="baseline"></div><div class="labels">${labels}</div>`;

// member avatar wall
document.getElementById('wallN').textContent=NP;
document.getElementById('wall').innerHTML=prog.map(p=>{const s=AV[p.login];const ttl=`${esc(p.name)} · ${p.count}/5`;
  return s?`<img class="wav" src="${s}" title="${ttl}" data-login="${esc(p.login)}" alt="${esc(p.name)}" loading="lazy">`:`<span class="wav wav-x" title="${ttl}" data-login="${esc(p.login)}">${esc((p.name||'?').slice(0,1))}</span>`;}).join('');
document.querySelectorAll('.wav[data-login]').forEach(el=>el.onclick=()=>{const lg=el.dataset.login;q.value=lg;state.q=lg;state.day=0;syncChips();renderList();switchTab('feed');});

// metrics
const M=[['Members','参与人数',NP],['Comments','总评论数',TOTAL],['Check-ins','打卡人次',UNIT],['Avg / 5','人均完成',AVG.toFixed(1)]];
document.getElementById('metrics').innerHTML=M.map(m=>`<div class="m"><div class="m-k">${m[0]}</div><div class="m-v">${m[2]}</div><div class="m-zh">${m[1]}</div></div>`).join('');

// roster
let mSort='count',mDir=-1;
function renderRoster(){
  const arr=[...prog].sort((a,b)=>{let x,y;if(mSort==='name')return mDir*a.name.localeCompare(b.name,'zh');
    if(mSort==='rank'){x=a.rank;y=b.rank;}else if(mSort[0]==='d'){const d=+mSort[1];x=a.days.has(d)?1:0;y=b.days.has(d)?1:0;}else{x=a.count;y=b.count;}return mDir*(x-y);});
  document.getElementById('roster').innerHTML=arr.map(p=>{
    const cells=[1,2,3,4,5].map(d=>p.days.has(d)?`<td><span class="cell on" style="background:${DI[d].hex}"></span></td>`:`<td><span class="cell"></span></td>`).join('');
    return `<tr class="person" data-login="${esc(p.login)}"><td class="l rk">${String(p.rank).padStart(2,'0')}</td>
      <td class="l"><div class="who">${av(p.login)}<span class="nm">${esc(p.name)}</span><span class="id">${esc(p.login)}</span></div></td>${cells}
      <td><span class="score"><b>${p.count}</b>/5</span></td></tr>`;}).join('');
  document.querySelectorAll('.person').forEach(tr=>tr.onclick=()=>{const lg=tr.dataset.login;q.value=lg;state.q=lg;state.day=0;syncChips();renderList();switchTab('feed');});
}
document.querySelectorAll('.roster th[data-sort]').forEach(th=>th.onclick=()=>{const k=th.dataset.sort;if(mSort===k)mDir*=-1;else{mSort=k;mDir=(k==='name'||k==='rank')?1:-1;}renderRoster();});

// feed
const state={q:'',day:0,sort:'seq'};
const chips=[{d:0,t:'全部'}].concat([1,2,3,4,5].map(d=>({d,t:DI[d].c+' · '+perDay[d]})));
document.getElementById('chips').innerHTML=chips.map(c=>`<span class="chip${c.d===0?' active':''}" data-day="${c.d}">${c.t}</span>`).join('');
function syncChips(){document.querySelectorAll('.chip').forEach(ch=>{const d=+ch.dataset.day,on=d===state.day;ch.classList.toggle('active',on);ch.style.background=on?(d?DI[d].hex:'var(--ink)'):'';ch.style.color=on?'#fff':'';});}
document.querySelectorAll('.chip').forEach(ch=>ch.onclick=()=>{state.day=+ch.dataset.day;if(!state.day){state.q='';q.value='';}syncChips();renderList();});
q.oninput=e=>{state.q=e.target.value.trim();renderList();};
document.getElementById('sort').onchange=e=>{state.sort=e.target.value;renderList();};
function bodyHtml(parts){return parts.map(p=>p.t==='i'?`<img class="shot" loading="lazy" src="${p.v}" alt="截图" referrerpolicy="no-referrer">`:`<div class="ptext">${esc(p.v)}</div>`).join('');}
function renderList(){let arr=DATA.filter(c=>{if(state.day&&c.day!==state.day)return false;if(state.q){const x=state.q.toLowerCase();if(!((c.name||'').toLowerCase().includes(x)||(c.login||'').toLowerCase().includes(x)||(c.txt||'').toLowerCase().includes(x)))return false;}return true;});
  const s=state.sort;arr=[...arr].sort((a,b)=>s==='time_desc'?(b.time||'').localeCompare(a.time||''):s==='time_asc'?(a.time||'').localeCompare(b.time||''):s==='name'?a.name.localeCompare(b.name,'zh'):s==='day'?a.day-b.day||a.seq-b.seq:a.seq-b.seq);
  document.getElementById('cCount').textContent=`${arr.length} / ${TOTAL} 条`;
  document.getElementById('cList').innerHTML=arr.length?arr.map(c=>`<div class="card"><div class="chead"><span class="tag" style="background:${DI[c.day].hex}">${DI[c.day].c}</span>${av(c.login,1)}<span class="nm">${esc(c.name)}</span><span class="id">${esc(c.login)}</span><span class="tm">${esc(c.time||'')}</span></div><div class="cbody">${bodyHtml(c.parts)}</div></div>`).join(''):'<div class="empty">没有匹配的评论</div>';}

function switchTab(n){document.querySelectorAll('.tabs button').forEach(b=>b.classList.toggle('active',b.dataset.tab===n));document.querySelectorAll('.view').forEach(v=>v.classList.toggle('active',v.id===n));window.scrollTo({top:0,behavior:'smooth'});}
document.querySelectorAll('.tabs button').forEach(b=>b.onclick=()=>switchTab(b.dataset.tab));
const root=document.documentElement,tb=document.getElementById('themeBtn');
function applyTheme(t){if(t==='dark'){root.setAttribute('data-theme','dark');tb.textContent='LIGHT';}else{root.removeAttribute('data-theme');tb.textContent='DARK';}}
applyTheme(localStorage.getItem('theme')||(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'));
tb.onclick=()=>{const t=root.getAttribute('data-theme')==='dark'?'light':'dark';localStorage.setItem('theme',t);applyTheme(t);};
renderRoster();syncChips();renderList();
</script>
</body>
</html>"""

html = (TEMPLATE.replace('__SRC__', SRC).replace('__LATEST__', LATEST).replace('__NIMG__', str(nimg))
        .replace('__AV__', AV_JSON).replace('__DATA__', DATA_JSON))
open('index.html', 'w', encoding='utf-8').write(html)
print(f"built | comments={len(rows)} images={nimg} latest={LATEST} bytes={len(html)}")
