"""Extract Kochouran KAG text using source control flow and Win32 font advances.

Opens .ks/.tjs text and optional verified frame-dimension JSON only. Does not
render media, capture windows, launch a game, send input, or read process memory.
"""
import argparse
import collections
import copy
import ctypes as C
from ctypes import wintypes as W
import hashlib
import json
from pathlib import Path
import re

from _lib.kochouran_extract import write_json, sha256
from _lib.kochouran_kag import lex


class Advances:
    """GDI metrics only; no bitmap, drawing, screen DC, or image API."""
    def __init__(self):
        self.g = C.WinDLL('gdi32', use_last_error=True)
        self.g.CreateCompatibleDC.argtypes = [W.HDC]
        self.g.CreateCompatibleDC.restype = W.HDC
        self.g.CreateFontW.argtypes = [C.c_int]*5 + [W.DWORD]*8 + [W.LPCWSTR]
        self.g.CreateFontW.restype = W.HFONT
        self.g.SelectObject.argtypes = [W.HDC, W.HGDIOBJ]
        self.g.SelectObject.restype = W.HGDIOBJ
        class SIZE(C.Structure):
            _fields_ = [('cx',C.c_long),('cy',C.c_long)]
        self.SIZE=SIZE
        self.g.GetTextExtentPoint32W.argtypes = [W.HDC,W.LPCWSTR,C.c_int,C.POINTER(SIZE)]
        self.g.GetTextFaceW.argtypes = [W.HDC, C.c_int, W.LPWSTR]
        self.g.DeleteObject.argtypes = [W.HGDIOBJ]
        self.g.DeleteDC.argtypes = [W.HDC]
        self.dc = self.g.CreateCompatibleDC(None)
        assert self.dc
        self.fonts, self.widths, self.resolved = {}, {}, {}

    def width(self, ch, size, face, bold):
        fk = (size, face, bold)
        key = fk + (ch,)
        if key not in self.widths:
            if fk not in self.fonts:
                # MessageLayer sets font.height=-size, bold=true.
                # Kirikiri 2 measures a nonbold font, then adds floor(height/50)+1 for bold.
                self.fonts[fk] = self.g.CreateFontW(-size, 0, 0, 0, 400,
                                                   0, 0, 0, 128, 0, 0, 4, 0, face)
                assert self.fonts[fk]
            self.g.SelectObject(self.dc, self.fonts[fk])
            name = C.create_unicode_buffer(256)
            assert self.g.GetTextFaceW(self.dc, len(name), name)
            self.resolved[str(fk)] = name.value
            metric=self.SIZE()
            assert self.g.GetTextExtentPoint32W(self.dc,ch,1,C.byref(metric)), ch
            self.widths[key] = metric.cx + (int(metric.cy/50)+1 if bold else 0)
        return self.widths[key]

    def close(self):
        self.g.DeleteDC(self.dc)
        for h in self.fonts.values():
            self.g.DeleteObject(h)


class Message:
    def __init__(self):
        self.width, self.height = 740, 160
        self.frame = ''
        self.capacity_verified = True
        self.ml, self.mt, self.mr, self.mb = 260, 20, 60, 30
        self.default_size, self.default_face, self.default_bold = 24, 'ＭＳ Ｐ明朝', True
        self.default_line, self.default_spacing, self.default_pitch = 0, 8, 0
        self.default_auto = True
        self.reset()

    def reset(self, automatic=False):
        if not automatic:
            self.indent = 0
            self.size, self.face, self.bold = self.default_size, self.default_face, self.default_bold
            self.spacing, self.pitch = self.default_spacing, self.default_pitch
            self.reserve, self.auto = self.default_line, self.default_auto
        self.x, self.y = self.ml + (self.indent if automatic else 0), self.mt
        self.last = ''
        self.line_size = max(self.size, self.reserve)
        self.pending_size = self.size
        self.size_changed = False
        self.segments, self.atoms = [], []
        self.name = ''
        self.segment_name = ''
        self.links = []
        self.fresh = False
        self.last_wait = ''

    def signature(self):
        return (self.width,self.height,self.frame,self.capacity_verified,self.ml,self.mt,self.mr,self.mb,
                self.default_size,self.default_face,self.default_bold,self.default_line,
                self.default_spacing,self.default_pitch,self.default_auto,
                self.x,self.y,self.last,self.indent,self.size,self.face,self.bold,
                self.spacing,self.pitch,self.reserve,self.auto,self.line_size,
                self.pending_size,self.size_changed,self.name,self.segment_name,
                tuple((tuple(x['atoms']),x['name']) for x in self.segments),
                tuple(self.atoms),tuple(self.links),self.fresh,self.last_wait)

    def reline(self):
        # MessageLayer: baseline+originY+topOffset+lineSize >= height-marginB.
        # baseline+topOffset = lineSpacing+lineSize exactly.
        if self.capacity_verified and self.y + self.spacing + 2*self.line_size >= self.height-self.mb:
            return self.auto
        self.decide_size()
        self.y += self.line_size + self.spacing
        self.x = self.ml + self.indent
        self.line_size = max(self.reserve, self.size)
        return False

    def decide_size(self):
        if self.size_changed:
            self.size = self.pending_size
            self.size_changed = False

    def change_size(self):
        self.decide_size()
        self.line_size = max(self.line_size,self.size)

    def add_atom(self, atom):
        # (file, token, start, end, kind); merge adjacent glyphs from same token.
        if self.atoms and atom[4] == 'text':
            prev = self.atoms[-1]
            if prev[0:2] == atom[0:2] and prev[4] == 'text' and prev[3] == atom[2]:
                self.atoms[-1] = prev[:3] + (atom[3], 'text')
                return
        self.atoms.append(atom)
        self.fresh = True


class State:
    def __init__(self):
        self.messages = [[Message() for _ in range(2)] for _ in range(2)]
        self.current = (0,0)

    @property
    def cur(self):
        p,n = self.current
        return self.messages[p][n]

    def signature(self):
        return (self.current, tuple(m.signature() for page in self.messages for m in page))

    def target(self, attrs):
        page = 1 if attrs.get('page') == 'back' else 0
        layer = attrs.get('layer')
        if layer is None and 'page' not in attrs:
            return self.current
        num = self.current[1] if layer in (None,'message') else int(layer[7:] or '0')
        return page,num


class Extractor:
    def __init__(self, root, evidence, frame_geometry=None):
        self.root, self.evidence = root, evidence
        self.frame_geometry_path = frame_geometry
        self.frame_geometry = (json.loads(frame_geometry.read_text(encoding='utf-8'))['frames']
                               if frame_geometry else {})
        self.files = {p.name:list(lex(p)) for p in sorted((root/'scenario').glob('*.ks'))}
        self.labels = {fn:{t['value'].split('|')[0]:i for i,t in enumerate(ts)
                          if t['kind']=='label'} for fn,ts in self.files.items()}
        self.story = ['chapter1.ks']
        for route, count in [('yushima',13),('katsuragi',13),('ichijou',13),
                             ('toujou',13),('kikyou',8),('shujinnkou',8)]:
            self.story += [f'{route}{i:02}.ks' for i in range(1,count+1)]
        self.story += ['furo.ks','cokking1.ks','cokking2.ks','senka.ks']
        assert len(self.story) == 73, len(self.story)
        self.fonts = Advances()
        src = (root/'system'/'MessageLayer.tjs').read_text(encoding='utf-8')
        self.leading, self.following, self.weak = [self.read_tjs_string(src,n)
                                                  for n in ['wwLeading','wwFollowing','wwFollowingWeak']]
        self.following += self.weak
        self.pages, self.choice_rows = {}, {}
        self.covered = set()
        self.auto_events, self.anomalies = {}, {}
        self.stats = collections.Counter()
        self.visited = set()
        self.context = ()

    @staticmethod
    def read_tjs_string(src, name):
        val = re.search(r'var '+name+r'\s*=\s*((?:"(?:[^"\\]|\\.)*"\s*)+);',src)[1]
        return ''.join(json.loads(m) for m in re.findall(r'"(?:[^"\\]|\\.)*"',val))

    def atom_value(self, atom):
        fn,ti,a,b,kind = atom
        return self.files[fn][ti]['value'][a:b]

    def format_atoms(self, atoms, name=''):
        out = ''
        prefix = name
        for atom in atoms:
            value = self.atom_value(atom)
            if atom[4]=='name':
                prefix = value[1:-1]
            else:
                if value:
                    out += prefix + value
                    prefix = ''
        return out

    def finish_segment(self, m, reason, source):
        if m.atoms:
            # A name-only wait does not generate an empty body row.
            if any(a[4]=='text' and self.atom_value(a).strip() for a in m.atoms):
                m.segments.append(dict(atoms=list(m.atoms),name=m.segment_name,
                                       reason=reason,source=source))
            m.atoms = []
        m.segment_name = m.name
        m.last_wait = reason

    def finish_page(self, m, reason, source):
        self.finish_segment(m, reason, source)
        if m.segments and m.fresh:
            # Cloned/backed-up pages have the same source identity and are stored once.
            key = tuple(tuple(s['atoms']) for s in m.segments)
            segs = [dict(text=self.format_atoms(s['atoms'],s['name']),
                         atoms=s['atoms'],reason=s['reason'],source=s['source'],name=s['name'])
                    for s in m.segments]
            all_atoms = [a for s in m.segments for a in s['atoms']]
            merged = self.format_atoms(all_atoms,m.segments[0]['name'])
            context = tuple((fn, self.files[fn][pc-1]['line']) for fn,pc in self.context)
            contexts = set(self.pages.get(key,{}).get('contexts',[])) | {context}
            self.pages[key] = dict(segments=segs,merged_text=merged,contexts=sorted(contexts),
                                  close=reason,close_source=source,frame=m.frame,
                                  capacity_verified=m.capacity_verified,
                                  geometry=dict(width=m.width,height=m.height,
                                                margins=[m.ml,m.mt,m.mr,m.mb],
                                                size=m.size,line_size=m.line_size,
                                                default_line=m.default_line,spacing=m.spacing))
        m.segments,m.atoms = [],[]
        m.name,m.segment_name = '',''
        m.fresh = False

    def automatic(self, m, fn, ti, offset, mode):
        source = [fn,self.files[fn][ti]['line'],offset]
        event = (fn,ti,offset,mode)
        if event not in self.auto_events:
            self.auto_events[event] = dict(source=source,kind=mode,x=m.x,y=m.y,
                                            width=m.width,height=m.height,
                                            margins=[m.ml,m.mt,m.mr,m.mb],size=m.size,
                                            face=m.face,line_size=m.line_size,
                                            spacing=m.spacing,previous_wait=m.last_wait)
        self.finish_page(m,'automatic_'+mode,source)
        m.change_size()
        m.reset(automatic=True)

    def glyph(self, m, ch, fn, ti, offset, kind='text', add=True):
        edge = m.width-m.mr-2*m.pending_size
        if m.capacity_verified and m.x >= edge and m.auto:
            break_ok = ((not m.last or m.last not in self.leading) and ch not in self.following
                        or m.last and m.last in self.weak and ch in self.weak)
            if break_ok or m.x > m.width:
                if m.reline():
                    self.automatic(m,fn,ti,offset,'text')
        if m.size_changed:
            m.change_size()
        advance = self.fonts.width(ch,m.size,m.face,m.bold)
        m.x += advance + m.pitch
        m.last = ch
        if add:
            m.add_atom((fn,ti,offset,offset+1,kind))
        self.covered.add((fn,ti,offset))

    def text(self, m, fn, ti):
        t = self.files[fn][ti]
        value = t['value']
        is_name = (re.fullmatch(r'≪[^≫]+≫',value) is not None
                   and ti+1<len(self.files[fn])
                   and self.files[fn][ti+1].get('tag')=='r')
        if m.links and m.links[-1][3] == 'open':
            # Links are literal text choices. Preserve source command occurrences.
            key = (fn,ti)
            self.choice_rows[key] = dict(text=value,source=[fn,t['line'],t['col']],token=ti)
            for i,ch in enumerate(value):
                self.glyph(m,ch,fn,ti,i,add=False)
            return
        if is_name:
            old_pages = len(self.auto_events)
            for i,ch in enumerate(value):
                self.glyph(m,ch,fn,ti,i,kind='name',add=False)
            assert len(self.auto_events)==old_pages, ('name split by automatic page',fn,t['line'])
            m.add_atom((fn,ti,0,len(value),'name'))
            m.name = value[1:-1]
        else:
            for i,ch in enumerate(value):
                self.glyph(m,ch,fn,ti,i)

    def destination(self, fn, attrs):
        dest = attrs.get('storage',fn).strip('"')
        if dest in ('first.ks','title.ks'):
            return None
        if dest not in self.files:
            self.anomalies[(fn,str(attrs))] = dict(type='missing_storage',source=fn,attrs=attrs)
            return None
        target = attrs.get('target','').lstrip('*')
        if not target:
            return dest,0
        if target not in self.labels[dest]:
            self.anomalies[(fn,str(attrs))] = dict(type='missing_label',source=fn,attrs=attrs)
            return None
        return dest,self.labels[dest][target]

    def run(self):
        pending = [('chapter1.ks',0,(),State())]
        while pending:
            fn,pc,stack,state = pending.pop()
            while pc < len(self.files[fn]):
                node = (fn,pc,stack,state.signature())
                if node in self.visited:
                    break
                self.visited.add(node)
                self.stats['executed_tokens']+=1
                self.context = stack
                t = self.files[fn][pc]
                source = [fn,t['line'],t['col']]
                if t['kind']=='text':
                    self.text(state.cur,fn,pc)
                elif t['kind']=='tag':
                    tag,attrs = t['tag'],t['attrs']
                    m = state.cur
                    if tag in ('er','cm','ct'):
                        targets = [m] if tag=='er' else [x for page in state.messages for x in page]
                        for obj in targets:
                            self.finish_page(obj,tag,source)
                            obj.reset()
                        if tag=='ct': state.current=(0,0)
                    elif tag=='position':
                        p,n = state.target(attrs)
                        obj = state.messages[p][n]
                        self.finish_page(obj,'position',source)
                        if 'frame' in attrs:obj.frame=attrs['frame']
                        for key,field in [('width','width'),('height','height'),
                                          ('marginl','ml'),('margint','mt'),('marginr','mr'),('marginb','mb')]:
                            if key in attrs: setattr(obj,field,int(attrs[key]))
                        # clearLayer loads a frame and replaces the numeric position size.
                        obj.capacity_verified = not obj.frame or obj.frame in self.frame_geometry
                        if obj.frame in self.frame_geometry:
                            obj.width = self.frame_geometry[obj.frame]['width']
                            obj.height = self.frame_geometry[obj.frame]['height']
                        obj.reset()
                        for key in ('marint','maringt'):
                            if key in attrs:
                                self.anomalies[(fn,pc,key)]=dict(type='ignored_source_attribute',source=source,
                                                                 attribute=key,value=attrs[key])
                    elif tag=='current':
                        state.current=state.target(attrs)
                    elif tag=='backlay':
                        layer=attrs.get('layer')
                        if layer is None:
                            state.messages[1]=copy.deepcopy(state.messages[0])
                            for obj in state.messages[1]:obj.fresh=False
                        elif layer.startswith('m'):
                            n=int(layer[7:]);state.messages[1][n]=copy.deepcopy(state.messages[0][n])
                            state.messages[1][n].fresh=False
                    elif tag in ('trans','wipe'):
                        # Default base transition includes children; exchange=false copies back -> fore.
                        layer=attrs.get('layer','base')
                        if attrs.get('children','true')!='false':
                            selected=range(2) if layer=='base' else ([int(layer[7:])] if layer.startswith('m') else [])
                            for n in selected:
                                old=state.messages[0][n]
                                new=copy.deepcopy(state.messages[1][n])
                                same=(old.atoms==new.atoms and old.segments==new.segments)
                                if same:new.fresh=new.fresh or old.fresh
                                elif old.fresh:self.finish_page(old,'transition',source)
                                state.messages[0][n]=new
                    elif tag in ('p','ps','l','pr','waitclick'):
                        self.finish_segment(m,tag,source)
                        if tag=='pr' and m.reline():
                            self.automatic(m,fn,pc,0,'r_after_p')
                    elif tag in ('r','his'):
                        if m.reline():
                            self.automatic(m,fn,pc,0,'r')
                    elif tag=='indent':
                        m.indent=m.x-m.ml
                    elif tag=='endindent':
                        m.indent=0
                    elif tag in ('font','resetfont'):
                        if tag=='resetfont':
                            m.pending_size=m.default_size;m.face=m.default_face;m.bold=m.default_bold
                        else:
                            if 'size' in attrs: m.pending_size=m.default_size if attrs['size']=='default' else int(attrs['size'])
                            if 'face' in attrs: m.face=m.default_face if attrs['face']=='default' else attrs['face']
                            if 'bold' in attrs: m.bold=attrs['bold'] in ('true','1')
                        m.size_changed=True
                    elif tag=='deffont':
                        if 'size' in attrs:m.default_size=int(attrs['size'])
                        if 'face' in attrs:m.default_face=attrs['face']
                    elif tag=='defstyle':
                        if 'linesize' in attrs:m.default_line=int(attrs['linesize'])
                    elif tag in ('style','resetstyle'):
                        m.reserve=m.default_line;m.spacing=m.default_spacing;m.pitch=m.default_pitch
                        m.line_size=max(m.reserve,m.size)
                    elif tag=='link':
                        dest=self.destination(fn,attrs)
                        if dest:m.links.append((dest[0],dest[1],pc,'open'))
                    elif tag=='endlink':
                        if m.links:
                            dest=m.links[-1];m.links[-1]=dest[:3]+('closed',)
                    elif tag=='s':
                        self.finish_segment(m,'s',source)
                        for dest in reversed(m.links):
                            pending.append((dest[0],dest[1],stack,copy.deepcopy(state)))
                        break
                    elif tag=='jump':
                        dest=self.destination(fn,attrs)
                        if not dest:break
                        fn,pc=dest
                        continue
                    elif tag=='call':
                        dest=self.destination(fn,attrs)
                        if dest and dest[0] in self.story:
                            stack=stack+((fn,pc+1),)
                            fn,pc=dest
                            continue
                    elif tag in ('return','recall_end','gotostart'):
                        if tag=='recall_end':
                            # Replay-only return adds no unique text and does not change normal play.
                            pass
                        elif not stack:
                            break
                        else:
                            fn,pc=stack[-1];stack=stack[:-1]
                            continue
                    elif tag=='if':
                        # Explore both source branches; merge identical states at the join.
                        depth=0;other=None;end=None
                        for j in range(pc+1,len(self.files[fn])):
                            tj=self.files[fn][j].get('tag')
                            if tj=='if':depth+=1
                            elif tj=='endif':
                                if depth==0:end=j;break
                                depth-=1
                            elif tj=='else' and depth==0:other=j
                        assert end is not None,(fn,source)
                        pending.append((fn,(other+1 if other is not None else end+1),stack,copy.deepcopy(state)))
                    elif tag=='else':
                        depth=0
                        for j in range(pc+1,len(self.files[fn])):
                            tj=self.files[fn][j].get('tag')
                            if tj=='if':depth+=1
                            elif tj=='endif':
                                if depth==0:pc=j;break
                                depth-=1
                    elif tag in ('emb','graph','locate','hch','ch','input'):
                        raise ValueError(('unhandled text-affecting tag',fn,source,tag,attrs))
                pc+=1
            # Record any final fresh body even if a broken original jump prevents continuation.
            for page in state.messages:
                for m in page:self.finish_page(m,'path_end',[fn,pc,0])
        self.fonts.close()
        self.write()

    def write(self):
        expected={(fn,i,j) for fn in self.story for i,t in enumerate(self.files[fn])
                  if t['kind']=='text' for j in range(len(t['value']))}
        missing=expected-self.covered
        extra=self.covered-expected
        # Pages from the same source may be reached under multiple caller configurations.
        # Keep all candidates in evidence and require no conflicting physical segmentation.
        pages=sorted(self.pages.values(),key=lambda p:self.atom_order(p['segments'][0]['atoms'][0]))
        pages, alternatives = self.resolve_layout_variants(pages)
        lines,rows,layout=[],[],[]
        emitted_segments = {}
        page_variants=collections.defaultdict(set)
        items=[]
        for page in pages:
            atoms=[a for s in page['segments'] for a in s['atoms']]
            for atom in atoms:
                page_variants[(atom[0],atom[1],atom[2],atom[3])].add(tuple(tuple(s['atoms']) for s in page['segments']))
            items.append((self.atom_order(atoms[0]),'page',page))
        for (fn,ti),choice in self.choice_rows.items():
            items.append((self.atom_order((fn,ti,0,0,'text')),'choice',choice))
        for variant in alternatives:
            atoms=[a for s in variant['page']['segments'] for a in s['atoms']]
            last=atoms[-1]
            items.append((self.atom_order((last[0],last[1],last[3],last[3],'text')),'alternative',variant))
        for _,kind,obj in sorted(items,key=lambda a:a[0]):
            if kind=='choice':
                lines.append(obj['text'])
                rows.append(dict(line=len(lines),kind='choice',**obj))
            elif kind=='alternative':
                page=obj['page']
                atoms=[a for s in page['segments'] for a in s['atoms']]
                segment_lines=[line for key in obj['canonical'] for line in emitted_segments[key]]
                value=page['merged_text']
                assert ''.join(lines[line-1] for line in segment_lines)==value
                lines.append(value)
                layout.append(dict(segments=segment_lines,merged=len(lines),merged_text=value,
                                   source='caller-dependent actual page',kind='caller_layout_variant',
                                   contexts=page['contexts'],geometry=page['geometry']))
                rows.append(dict(line=len(lines),kind='merged',text=value,atoms=atoms,
                                 derivation='caller_layout_variant',contexts=page['contexts']))
                obj['output_line']=len(lines)
                obj['canonical_segment_lines']=segment_lines
            else:
                segment_lines=[]
                for seg in obj['segments']:
                    if not seg['text'].strip():continue
                    lines.append(seg['text']);segment_lines.append(len(lines))
                    rows.append(dict(line=len(lines),kind='segment',**seg))
                emitted_segments[self.page_key(obj)]=segment_lines
                if len(segment_lines)>1:
                    lines.append(obj['merged_text'])
                    atoms=[a for s in obj['segments'] for a in s['atoms']]
                    source='; '.join(f'{a[0]}:{self.files[a[0]][a[1]]["line"]}' for a in atoms)
                    layout.append(dict(segments=segment_lines,merged=len(lines),merged_text=obj['merged_text'],source=source))
                    rows.append(dict(line=len(lines),kind='merged',text=obj['merged_text'],atoms=atoms))
        conflicts={str(k):len(v) for k,v in page_variants.items() if len(v)>1}
        source_rows=collections.Counter()
        for row in rows:
            if row['kind']=='segment':
                for fn in set(a[0] for a in row['atoms']):source_rows[fn]+=1
            elif row['kind']=='choice':source_rows[row['source'][0]]+=1
        missing_tokens=collections.defaultdict(list)
        for fn,ti,j in sorted(missing):missing_tokens[(fn,ti)].append(j)
        missing_records=[dict(file=fn,line=self.files[fn][ti]['line'],value=self.files[fn][ti]['value'],
                              offsets=offsets) for (fn,ti),offsets in missing_tokens.items()]
        summary=dict(story_files=len(self.story),source_text_tokens=sum(t['kind']=='text' for fn in self.story for t in self.files[fn]),
                     source_text_chars=len(expected),covered_text_chars=len(expected & self.covered),
                     missing_records=missing_records,unexpected_text_chars=len(extra),
                     rows=len(lines),segment_rows=sum(r['kind']=='segment' for r in rows),
                     choice_rows=len(self.choice_rows),multi_segment_pages=len(layout)-len(alternatives),
                     caller_variant_rows=len(alternatives),
                     physical_pages=len(pages),automatic_events=len(self.auto_events),
                     framed_pages_with_unverified_capacity=sum(not p['capacity_verified'] for p in pages),
                     capacity_policy=('Frame dimensions from verified PNG IHDR metadata; KAG wrap/clear handlers and GDI advances determine automatic page splits.'
                                      if self.frame_geometry else 'Frame-free geometry only; framed capacity boundaries remain unverified.'),
                     frame_geometry_sha256=sha256(self.frame_geometry_path) if self.frame_geometry_path else None,
                     conflicts=conflicts,source_rows=dict(source_rows),
                     names=sorted({self.atom_value(a)[1:-1] for p in pages for s in p['segments'] for a in s['atoms'] if a[4]=='name'}),
                     resolved_fonts=self.fonts.resolved,statistics=dict(self.stats),
                     input_sha256={str(p.relative_to(self.root)):sha256(p) for p in sorted(self.root.rglob('*')) if p.is_file() and p.suffix in ('.ks','.tjs')},
                     extractor_sha256=sha256(__file__),lexer_sha256=sha256((Path(__file__).parent / '_lib' / 'kochouran_kag.py')))
        self.evidence.mkdir(parents=True,exist_ok=True)
        write_json(self.evidence/'coverage.json',summary)
        write_json(self.evidence/'source_rows.json',rows)
        write_json(self.evidence/'layout_map.json',dict(pages=layout))
        write_json(self.evidence/'automatic_pages.json',list(self.auto_events.values()))
        write_json(self.evidence/'source_anomalies.json',list(self.anomalies.values()))
        write_json(self.evidence/'caller_layout_variants.json',alternatives)
        if missing_records or conflicts or extra:
            print(json.dumps(dict(missing_record_count=len(missing_records),missing_sample=missing_records[:4],
                                  conflicts=list(conflicts.items())[:5],unexpected_text_chars=len(extra),rows=len(lines)),ensure_ascii=False))
            raise ValueError('Coverage or layout conflicts require investigation; final text was not written.')
        self.output.parent.mkdir(parents=True,exist_ok=True)
        self.output.write_text('\n'.join(lines)+'\n',encoding='utf-8-sig',newline='\n')
        print(json.dumps({k:summary[k] for k in ['story_files','source_text_chars','rows','segment_rows','choice_rows','multi_segment_pages','physical_pages','automatic_events','resolved_fonts']},ensure_ascii=False))

    def atom_order(self,a):
        return self.story.index(a[0]),a[1],a[2]

    @staticmethod
    def page_key(page):
        return tuple(tuple(tuple(a) for a in s['atoms']) for s in page['segments'])

    def resolve_layout_variants(self, pages):
        """Keep source once, plus a proven alternate whole page for caller variants.

        Overlapping pages must form complete alternatives with identical source
        characters. No boundary is synthesized: retained boundaries come from a
        caller's actual KAG state. A coarser actual page is emitted as a derived
        full-page row after the finer variant's segments.
        """
        parents=list(range(len(pages)))
        def find(i):
            while parents[i]!=i:
                parents[i]=parents[parents[i]];i=parents[i]
            return i
        chars=[];owners={}
        for i,page in enumerate(pages):
            positions={(a[0],a[1],j) for s in page['segments'] for a in s['atoms'] for j in range(a[2],a[3])}
            chars.append(positions)
            for position in positions:
                if position in owners:parents[find(i)]=find(owners[position])
                else:owners[position]=i
        groups=collections.defaultdict(list)
        for i in range(len(pages)):groups[find(i)].append(i)
        keep=[];alternatives=[]
        for group in groups.values():
            if len(group)==1:
                keep.append(pages[group[0]]);continue
            universe=set().union(*(chars[i] for i in group))
            selected=[];consumed=set()
            for i in sorted(group,key=lambda j:len(chars[j])):
                if not chars[i]&consumed:
                    selected.append(i);consumed.update(chars[i])
            assert consumed==universe, ('incompatible caller layouts',group)
            selected.sort(key=lambda i:self.atom_order(pages[i]['segments'][0]['atoms'][0]))
            keep.extend(pages[i] for i in selected)
            for i in group:
                if i in selected:continue
                subset=[j for j in selected if chars[j] <= chars[i]]
                assert set().union(*(chars[j] for j in subset))==chars[i]
                assert len(pages[i]['segments'])==1, 'Complex caller variants need explicit handling'
                # Each retained variant must have actual common-script call contexts.
                assert pages[i]['contexts'] and all(pages[j]['contexts'] for j in subset)
                alternatives.append(dict(page=pages[i],canonical=[self.page_key(pages[j]) for j in subset],
                                         source_characters=len(chars[i]),
                                         canonical_geometry=[pages[j]['geometry'] for j in subset],
                                         canonical_contexts=[pages[j]['contexts'] for j in subset]))
        keep.sort(key=lambda page:self.atom_order(page['segments'][0]['atoms'][0]))
        return keep,alternatives


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--evidence',type=Path,required=True)
    p.add_argument('--frame-geometry',type=Path)
    a=p.parse_args()
    e=Extractor(a.root,a.evidence,a.frame_geometry)
    e.output=a.output
    e.run()
