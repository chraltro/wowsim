def parse_values(s):
    """Parse MySQL VALUES (...),(...) string into list of tuples (strings/None/numbers)."""
    out=[];i=0;n=len(s)
    while i<n:
        if s[i]!='(':
            i+=1; continue
        i+=1; row=[]; 
        while True:
            while s[i]==' ': i+=1
            if s[i]=="'":
                j=i+1; buf=[]
                while True:
                    c=s[j]
                    if c=='\\': buf.append(s[j+1]); j+=2; continue
                    if c=="'":
                        if j+1<n and s[j+1]=="'": buf.append("'"); j+=2; continue
                        break
                    buf.append(c); j+=1
                row.append(''.join(buf)); i=j+1
            else:
                j=i
                while s[j] not in ',)': j+=1
                tok=s[i:j].strip()
                if tok=='NULL': row.append(None)
                else:
                    try: row.append(int(tok))
                    except ValueError: row.append(float(tok))
                i=j
            if s[i]==',': i+=1; continue
            if s[i]==')': i+=1; break
        out.append(tuple(row))
    return out
