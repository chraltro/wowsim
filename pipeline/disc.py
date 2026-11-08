import json,sys,re,html
d=json.load(open(sys.argv[1]))
mx=int(sys.argv[2]) if len(sys.argv)>2 else 1500
print('TITLE:',d.get('title'),'| posts:',d.get('posts_count'),'| created:',d.get('created_at'))
for p in d['post_stream']['posts']:
    c=re.sub(r'<(p|li|h[1-6]|br|blockquote)[^>]*>','\n',p['cooked'])
    txt=re.sub(r'\n\s*\n+','\n',html.unescape(re.sub(r'<[^>]+>','',c))).strip()
    staff = 'STAFF' if (p.get('staff') or p.get('moderator') or p.get('admin')) else ''
    print(f"=== #{p['post_number']} {p['username']} {p['created_at'][:16]} likes={p.get('like_count','?')} {staff}")
    print(txt[:mx])
