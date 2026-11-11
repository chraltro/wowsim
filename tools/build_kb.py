#!/usr/bin/env python3
"""Build the knowledge bank page: docs/kb/*.md -> dist/kb/index.html (one self-contained file).

The pages use a small part of Markdown: headings, paragraphs, bullet lists, tables, **bold**, `code` and [links](url).
That is all this converts. Standard library only.
"""
import html, json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KB = os.path.join(ROOT, 'docs', 'kb')
ORDER = ['group', 'leveling', 'shaman', 'paladin', 'classes', 'systems', 'gold', 'raids', 'open-questions', 'sources', 'changelog']
SHORT = {'group': 'The group', 'leveling': 'Leveling and dungeons', 'shaman': 'Shaman', 'paladin': 'Paladin alt', 'classes': 'Other classes',
         'systems': 'Systems', 'gold': 'Gold making', 'raids': 'Raids', 'open-questions': 'Open questions', 'sources': 'Sources', 'changelog': 'Changes'}


def slug(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')


def inline(text, page):
    out, pos = [], 0
    token = re.compile(r'\[([^\]]+)\]\(([^)\s]+)\)|\*\*(.+?)\*\*|`([^`]+)`')
    for m in token.finditer(text):
        out.append(html.escape(text[pos:m.start()].replace('\\>', '>').replace('\\<', '<'), quote=False))
        if m.group(1) is not None:
            label, url = m.group(1), m.group(2)
            local = re.match(r'^([a-z-]+)\.md(#.*)?$', url)
            if local:
                out.append('<a href="#%s">%s</a>' % (local.group(1), inline(label, page)))
            else:
                out.append('<a href="%s" target="_blank" rel="noopener">%s</a>' % (html.escape(url), inline(label, page)))
        elif m.group(3) is not None:
            out.append('<strong>%s</strong>' % inline(m.group(3), page))
        else:
            out.append('<code>%s</code>' % html.escape(m.group(4), quote=False))
        pos = m.end()
    out.append(html.escape(text[pos:].replace('\\>', '>').replace('\\<', '<'), quote=False))
    return ''.join(out)


def cells(line):
    return [c.strip() for c in re.split(r'(?<!\\)\|', line.strip().strip('|'))]


def convert(md, page):
    """Markdown of one page -> (title, lead, html, [(id, heading)])."""
    lines = md.replace('\r', '').split('\n')
    title, out, heads, i, lead = page, [], [], 0, None
    while i < len(lines):
        l = lines[i]
        if not l.strip():
            i += 1; continue
        if l.startswith('# '):
            title = l[2:].strip(); i += 1; continue
        m = re.match(r'^(#{2,4}) (.+)$', l)
        if m:
            level, text = len(m.group(1)), m.group(2).strip()
            hid = page + '-' + slug(text)
            if level == 2: heads.append((hid, text))
            out.append('<h%d id="%s">%s</h%d>' % (level + 1, hid, inline(text, page), level + 1)); i += 1; continue
        if l.lstrip().startswith('|') and i + 1 < len(lines) and re.match(r'^\s*\|[\s:|-]+\|\s*$', lines[i + 1]):
            head = cells(l); i += 2; rows = []
            while i < len(lines) and lines[i].lstrip().startswith('|'):
                rows.append(cells(lines[i])); i += 1
            out.append('<div class="tw"><table><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>' % (
                ''.join('<th>%s</th>' % inline(c, page) for c in head),
                ''.join('<tr>%s</tr>' % ''.join('<td>%s</td>' % inline(c, page) for c in r) for r in rows)))
            continue
        if re.match(r'^\s*- ', l):
            items = []
            while i < len(lines):
                if re.match(r'^\s*- ', lines[i]):
                    items.append(re.sub(r'^\s*- ', '', lines[i])); i += 1
                elif lines[i].strip() and lines[i].startswith('  ') and items:
                    items[-1] += ' ' + lines[i].strip(); i += 1
                elif not lines[i].strip() and i + 1 < len(lines) and re.match(r'^\s*- ', lines[i + 1]):
                    i += 1
                else:
                    break
            out.append('<ul>%s</ul>' % ''.join('<li>%s</li>' % inline(x, page) for x in items)); continue
        para = [l.strip()]; i += 1
        while i < len(lines) and lines[i].strip() and not re.match(r'^(#{1,4} |\s*- |\s*\|)', lines[i]):
            para.append(lines[i].strip()); i += 1
        text = ' '.join(para)
        if lead is None and not out:
            lead = text; continue
        out.append('<p>%s</p>' % inline(text, page))
    return title, lead, '\n'.join(out), heads


PAGE = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>WoW Forever knowledge bank</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@500;600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono&display=swap" rel="stylesheet">
<style>
:root{--bg:#0c1318;--panel:#121b21;--panel-2:#17232a;--line:#26353e;--line-2:#33454f;--text:#e7e9e3;--muted:#8e9ea3;--gold:#d9b46c;--mark:#3a3118;--ease:cubic-bezier(.2,.75,.2,1);color-scheme:dark}
*{box-sizing:border-box}
html{scroll-behavior:smooth;scroll-padding-top:76px}
html,body{margin:0;background:var(--bg);color:var(--text);font-family:'IBM Plex Sans',-apple-system,'Segoe UI',Roboto,sans-serif;font-size:15.5px;line-height:1.6;-webkit-font-smoothing:antialiased}
body{background:radial-gradient(1200px 600px at 50% -220px,#16232b 0%,var(--bg) 70%) fixed,var(--bg);min-height:100vh}
a{color:var(--gold);text-underline-offset:3px;text-decoration-thickness:1px}
.top{position:sticky;top:0;z-index:5;background:rgba(12,19,24,.86);backdrop-filter:saturate(1.4) blur(14px);-webkit-backdrop-filter:saturate(1.4) blur(14px);border-bottom:1px solid var(--line)}
.top .in{max-width:1180px;margin:0 auto;padding:12px 20px;display:flex;gap:16px;align-items:center}
.brand{font-family:'Cinzel',Georgia,serif;font-weight:600;letter-spacing:.03em;font-size:16px;color:var(--text);text-decoration:none;white-space:nowrap}
.brand span{color:var(--muted);font-family:'IBM Plex Sans',sans-serif;font-weight:400;letter-spacing:0;font-size:13px;margin-left:8px}
.find{margin-left:auto;position:relative;flex:0 1 300px}
.find input{width:100%;background:var(--panel);border:1px solid var(--line);border-radius:999px;color:var(--text);font:inherit;font-size:14px;padding:8px 14px;outline:none;transition:border-color .2s var(--ease),background .2s}
.find input:focus{border-color:var(--gold);background:var(--panel-2)}
.find input::placeholder{color:var(--muted)}
.wrap{max-width:1180px;margin:0 auto;padding:28px 20px 96px;display:grid;grid-template-columns:220px minmax(0,1fr);gap:40px}
nav.side{position:sticky;top:76px;align-self:start;display:grid;gap:2px;max-height:calc(100vh - 96px);overflow:auto;padding-right:4px}
nav.side a{display:block;color:var(--muted);text-decoration:none;font-size:14px;padding:7px 12px;border-radius:10px;border-left:2px solid transparent;transition:color .2s var(--ease),background .2s var(--ease),border-color .2s var(--ease)}
nav.side a:hover{color:var(--text);background:var(--panel)}
nav.side a.on{color:var(--text);background:var(--panel);border-left-color:var(--gold)}
nav.side a:focus-visible,.find input:focus-visible{outline:2px solid var(--gold);outline-offset:2px}
main{min-width:0;display:grid;grid-template-columns:minmax(0,1fr);gap:56px}
header.hero{display:grid;grid-template-columns:minmax(0,1fr);gap:10px}
h1{font-family:'Cinzel',Georgia,serif;font-weight:600;font-size:clamp(26px,4.4vw,36px);letter-spacing:.02em;margin:0;line-height:1.2}
.hero p{margin:0;color:var(--muted);max-width:70ch}
.stamp{display:inline-flex;gap:8px;align-items:center;font-size:13px;color:var(--muted);border:1px solid var(--line);border-radius:16px;padding:5px 12px;justify-self:start;max-width:100%}
.stamp b{color:var(--text);font-weight:500}
.dot{width:7px;height:7px;border-radius:50%;background:#6fbf8b;flex:none}
section.page{display:grid;grid-template-columns:minmax(0,1fr);gap:14px;min-width:0}
section.page>h2{font-family:'Cinzel',Georgia,serif;font-weight:600;font-size:24px;letter-spacing:.03em;margin:0;padding-bottom:10px;border-bottom:1px solid var(--line)}
.lead{color:var(--muted);margin:0}
h3{font-size:17px;font-weight:600;margin:18px 0 0;color:var(--text)}
h4{font-size:15px;font-weight:600;margin:10px 0 0;color:var(--text)}
p{margin:0;max-width:78ch}
ul{margin:0;padding-left:20px;display:grid;gap:8px;max-width:78ch}
li::marker{color:var(--line-2)}
strong{font-weight:600;color:#f3f1e8}
code{font-family:'IBM Plex Mono',ui-monospace,Menlo,monospace;font-size:.88em;background:var(--panel-2);border:1px solid var(--line);border-radius:6px;padding:1px 6px}
.tw{overflow-x:auto;border:1px solid var(--line);border-radius:14px;background:var(--panel);-webkit-overflow-scrolling:touch}
table{border-collapse:collapse;width:100%;font-size:14px}
th,td{text-align:left;padding:9px 14px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-weight:600;color:var(--muted);font-size:12.5px;letter-spacing:.04em;text-transform:uppercase;white-space:nowrap;background:var(--panel-2)}
tr:last-child td{border-bottom:0}
td:first-child{white-space:nowrap}
mark{background:var(--mark);color:#f6e3b0;border-radius:3px;padding:0 1px}
.hide{display:none!important}
.none{color:var(--muted);padding:24px 0}
footer{font-size:13px;color:var(--muted);border-top:1px solid var(--line);padding-top:18px}
@media (max-width:860px){
  .wrap{grid-template-columns:minmax(0,1fr);gap:20px;padding-top:16px}
  nav.side{position:sticky;top:57px;z-index:4;display:flex;gap:6px;overflow-x:auto;max-height:none;margin:0 -20px;padding:10px 20px;background:rgba(12,19,24,.9);backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);border-bottom:1px solid var(--line);scrollbar-width:none}
  nav.side::-webkit-scrollbar{display:none}
  nav.side a{white-space:nowrap;border:1px solid var(--line);border-left-width:1px;border-radius:999px;padding:6px 12px}
  nav.side a.on{border-color:var(--gold)}
  html{scroll-padding-top:118px}
  .brand span{display:none}
  td:first-child{white-space:normal}
  table{min-width:540px}
}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}*{transition:none!important}}
</style>
</head>
<body>
<div class="top"><div class="in">
  <a class="brand" href="#">WoW Forever<span>knowledge bank</span></a>
  <label class="find"><input id="q" type="search" placeholder="Find in the notes" autocomplete="off" aria-label="Find in the notes"></label>
</div></div>
<div class="wrap">
  <nav class="side" id="nav" aria-label="Pages">/*NAV*/</nav>
  <main id="main">
    <header class="hero">
      <h1>Knowledge bank</h1>
      <p>/*INTRO*/</p>
      <span class="stamp"><span class="dot"></span><span>Checked against Blizzard's notes <b>/*CHECKED*/</b></span></span>
    </header>
    /*BODY*/
    <div class="none hide" id="none">Nothing in the notes matches that.</div>
    <footer>Kept in <a href="https://github.com/chraltro/wowsim/tree/main/docs/kb">docs/kb</a> of the repo and rebuilt on every change. Not affiliated with Blizzard Entertainment.</footer>
  </main>
</div>
<script>
(function(){
  var nav = document.getElementById('nav'), links = [].slice.call(nav.querySelectorAll('a')), pages = [].slice.call(document.querySelectorAll('section.page'));
  // highlight the page being read
  var byId = {}; links.forEach(function(a){ byId[a.getAttribute('href').slice(1)] = a; });
  function setOn(id){ links.forEach(function(a){ a.classList.toggle('on', a === byId[id]); }); var a = byId[id]; if(a && nav.scrollWidth > nav.clientWidth) nav.scrollTo({left: a.offsetLeft - 20, behavior: 'smooth'}); }
  if('IntersectionObserver' in window){
    var seen = {};
    var io = new IntersectionObserver(function(es){
      es.forEach(function(e){ seen[e.target.id] = e.isIntersecting; });
      for(var i = 0; i < pages.length; i++) if(seen[pages[i].id]){ setOn(pages[i].id); break; }
    }, {rootMargin: '-90px 0px -55% 0px'});
    pages.forEach(function(p){ io.observe(p); });
  }
  // find: hide blocks without the words, mark the ones with them
  var q = document.getElementById('q'), none = document.getElementById('none');
  var blocks = [].slice.call(document.querySelectorAll('section.page > *:not(h2)'));
  var orig = new Map();
  function esc(s){ return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }
  function unmark(el){ if(orig.has(el)){ el.innerHTML = orig.get(el); orig.delete(el); } }
  function mark(el, re){
    orig.set(el, el.innerHTML);
    var w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT), nodes = [], n;
    while((n = w.nextNode())) nodes.push(n);
    nodes.forEach(function(t){
      if(!re.test(t.nodeValue)) return; re.lastIndex = 0;
      var span = document.createElement('span');
      span.innerHTML = t.nodeValue.replace(/[&<>]/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;'}[c]; }).replace(re, '<mark>$&</mark>');
      t.parentNode.replaceChild(span, t);
    });
  }
  var timer;
  function run(){
    var words = q.value.trim().toLowerCase().split(/\s+/).filter(Boolean);
    blocks.forEach(unmark);
    var any = false;
    pages.forEach(function(p){
      var shown = 0;
      [].slice.call(p.children).forEach(function(el){
        if(el.tagName === 'H2') return;
        var hit = !words.length || words.every(function(w){ return el.textContent.toLowerCase().indexOf(w) >= 0; });
        el.classList.toggle('hide', !hit);
        if(hit){ shown++; if(words.length && !/^H[34]$/.test(el.tagName)) mark(el, new RegExp(words.map(esc).join('|'), 'gi')); }
      });
      // a heading with nothing under it says nothing
      if(words.length) [].slice.call(p.querySelectorAll('h3,h4')).forEach(function(h){ var nx = h.nextElementSibling; while(nx && nx.classList.contains('hide') && !/^H[234]$/.test(nx.tagName)) nx = nx.nextElementSibling; if(!nx || /^H[234]$/.test(nx.tagName)) { if(!h.classList.contains('hide')) shown--; h.classList.add('hide'); } });
      p.classList.toggle('hide', shown <= 0);
      if(byId[p.id]) byId[p.id].classList.toggle('hide', shown <= 0);
      if(shown > 0) any = true;
    });
    none.classList.toggle('hide', any);
  }
  q.addEventListener('input', function(){ clearTimeout(timer); timer = setTimeout(run, 90); });
  document.addEventListener('keydown', function(e){ if(e.key === '/' && document.activeElement !== q){ e.preventDefault(); q.focus(); } if(e.key === 'Escape' && document.activeElement === q){ q.value = ''; run(); q.blur(); } });
})();
</script>
</body>
</html>
'''


def main():
    readme = open(os.path.join(KB, 'README.md'), encoding='utf-8').read()
    m = re.search(r'Last checked against Blizzard\'s notes: (.+)', readme)
    checked = m.group(1).strip().rstrip('.') if m else 'date unknown'
    intro = next((l.strip() for l in readme.split('\n')[1:] if l.strip() and not l.startswith('#')), '')
    nav, body = [], []
    for name in ORDER:
        path = os.path.join(KB, name + '.md')
        if not os.path.exists(path): continue
        title, lead, content, _ = convert(open(path, encoding='utf-8').read(), name)
        nav.append('<a href="#%s">%s</a>' % (name, html.escape(SHORT.get(name, title))))
        body.append('<section class="page" id="%s"><h2>%s</h2>%s\n%s</section>' % (
            name, html.escape(title), '<p class="lead">%s</p>' % inline(lead, name) if lead else '', content))
    page = PAGE.replace('/*NAV*/', ''.join(nav)).replace('/*INTRO*/', inline(intro, 'README')).replace('/*CHECKED*/', html.escape(checked)).replace('/*BODY*/', '\n'.join(body))
    out = os.path.join(ROOT, 'local', 'kb')   # never dist/: the notes are not published
    os.makedirs(out, exist_ok=True)
    open(os.path.join(out, 'index.html'), 'w', encoding='utf-8').write(page)
    print('kb/index.html', len(page.encode()), 'bytes,', len(nav), 'pages')


if __name__ == '__main__':
    main()
