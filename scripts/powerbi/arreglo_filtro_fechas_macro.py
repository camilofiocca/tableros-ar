"""Arreglo del filtro de fechas del Tablero Macro AR (23/11/2026).

Uso: python3 -I arreglo_filtro_fechas_macro.py <Medidas.tmdl origen> <Medidas.tmdl destino>

Reescribe las medidas de "ultimo dato" del modelo para que lean el dato vigente a la fecha de
fin de la ventana elegida (medida [Fin del período]) e ignoren el inicio de la ventana y el boton
de Rango. Ademas hay que agregar a mano la columna 'Año-Mes' en series y la relacion muchos a
muchos series['Año-Mes'] -> Calendario['Año-Mes'] (ver docs/arreglo-filtro-fechas.md).
"""
import re, sys, json

SRC, DST = sys.argv[1], sys.argv[2]
EXCL = {'Tooltip serie','Salario real total (base 100)','Salario real privado registrado (base 100)',
        'Salario real público (base 100)','Valor provincia','Título del mapa','Total país (mapa)',
        'Provincia líder','Mapa de Argentina'}
RM = 'REMOVEFILTERS ( Calendario ), REMOVEFILTERS ( Rangos )'

def split_args(inner):
    args=[];depth=0;cur='';q=False
    for ch in inner:
        if ch=='"': q=not q
        if not q:
            if ch=='(' : depth+=1
            elif ch==')': depth-=1
            elif ch==',' and depth==0:
                args.append(cur);cur='';continue
        cur+=ch
    args.append(cur);return args

def rewrite_calls(body):
    out=[];i=0;changed=False;needfin=False
    tok='CALCULATE ('
    while True:
        k=body.find(tok,i)
        if k<0: out.append(body[i:]);break
        j=k+len(tok);depth=1;q=False
        while depth:
            c=body[j]
            if c=='"': q=not q
            if not q:
                if c=='(': depth+=1
                elif c==')': depth-=1
            j+=1
        call=body[k:j];inner=call[len(tok):-1]
        args=[a.strip() for a in split_args(inner)]
        new=call
        a0=args[0]
        m1=re.fullmatch(r'MAX \( (series|series_diarias)\[fecha\] \)',a0)
        m2=re.fullmatch(r'SUM \( (series|series_diarias)\[\w+\] \)',a0)
        hascal=any('Calendario' in a for a in args)
        if m1 and not hascal:
            T=m1.group(1)
            add=', '+RM
            if not any(re.search(rf'{T}\[fecha\] <=',a) for a in args):
                add+=f', {T}[fecha] <= fin';needfin=True
            new=call[:-1].rstrip()+add+' )'
        elif m2 and not hascal:
            T=m2.group(1)
            if any(re.fullmatch(rf'{T}\[fecha\] = \w+',a) for a in args):
                new=call[:-1].rstrip()+', '+RM+' )'
        if new!=call: changed=True
        out.append(body[i:k]);out.append(new);i=j
    return ''.join(out),changed,needfin

lines=open(SRC,encoding='utf-8').read().split('\n')
# build blocks
starts=[i for i,l in enumerate(lines) if l.startswith('\tmeasure ')]
ends=starts[1:]+[next(i for i,l in enumerate(lines) if l.startswith('\tcolumn ') and i>starts[-1])]
res=lines[:starts[0]]
report=[]
for s,e in zip(starts,ends):
    blk=lines[s:e]
    name=blk[0].split(' = ')[0].replace('\tmeasure ','').strip() if ' = ' in blk[0] else blk[0].replace('\tmeasure ','').rstrip('= ').strip()
    name=name.strip("'")
    # split off property lines (start with 2 tabs + known props) : properties are lines with exactly two tabs followed by word + ':'
    pi=len(blk)
    for t in range(1,len(blk)):
        if re.match(r'^\t\t(formatString|displayFolder|lineageTag|dataCategory|description|isHidden|annotation)\b',blk[t]) :
            pi=t;break
    expr='\n'.join(blk[:pi]);props=blk[pi:]
    if name in EXCL:
        res+=blk;continue
    # manual tweaks
    if name in ('Diario último','Diario hace 7 días','Diario hace 30 días'):
        expr=expr.replace('VAR f = MAX ( series_diarias[fecha] )','VAR f = CALCULATE ( MAX ( series_diarias[fecha] ), series_diarias[fecha] <= fin )')
        expr=re.sub(r'REMOVEFILTERS \( Calendario \)(?!, REMOVEFILTERS \( Rangos \))', RM, expr)
    new,ch,needfin=rewrite_calls(expr)
    # rewrite manual calls (Diario f) again to add removefilters: they have no Calendario => handled in rewrite_calls
    new=re.sub(r'REMOVEFILTERS \( Calendario \)(?!, REMOVEFILTERS \( Rangos \))', RM, new) if name=='Carry en USD 12 meses' else new
    if name in ('Riesgo país último (pb)','Etiqueta Riesgo país'):
        new=new.replace('ALL ( Calendario )',RM)
        new=new.replace(f'series_diarias[id_indicador] = "riesgo_pais", {RM} )',f'series_diarias[id_indicador] = "riesgo_pais", {RM}, series_diarias[fecha] <= fin )',1)
        needfin=True;ch=True
    if name=='Carry en USD último mes':
        new=new.replace('series[fecha] = f )',f'series[fecha] = f, {RM} )');ch=True
    if '<= fin' in new and 'VAR fin' not in new: needfin=True
    if needfin:
        k=new.find('VAR ')
        if k<0: report.append(('NOVAR',name))
        else:
            new=new[:k]+'VAR fin = [Fin del período]'+('\n'+re.match(r'[\t ]*',new[new.rfind('\n',0,k)+1:]).group(0) if '\n' in new[:k] or new[:k].endswith('\t') else ' ')+new[k:]
    if ch or needfin:
        report.append(('CAMBIADA',name))
    res+=new.split('\n')+props
# find the first measure position: add Fin del período measure before first measure
fin_meas=[
"\tmeasure 'Fin del período' = CALCULATE ( MAX ( Calendario[Fecha] ), REMOVEFILTERS ( Rangos[Rango] ) )",
"\t\tformatString: dd/mm/yyyy",
"\t\tdisplayFolder: Fechas",
"\t\tlineageTag: 3f0f5a9e-62c1-4d5b-9a3e-7b1d9c2e4a10",
"",
]
final=res[:starts[0]]+fin_meas+res[starts[0]:]+lines[ends[-1]:]
open(DST,'w',encoding='utf-8',newline='\r\n').write('\n'.join(final))
json.dump(report,open(DST+'.report.json','w'),ensure_ascii=False,indent=0)
print(len([r for r in report if r[0]=='CAMBIADA']),'cambiadas;',[r for r in report if r[0]!='CAMBIADA'])
