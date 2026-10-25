import subprocess, sys, wave, json, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
# "Ollie the Overtrader vs Tariq" sketch reel (25 Oct), premium motion template (render_gambler_vs_trader_5_pro.py), Ollie on the left panel:
# 12 trades before lunch vs waiting for one setup, fees eat the small wins, 60 trades / 50 screen hours vs 3 trades, -2% burned out vs +4%.
# usage: python3 render_ollie_overtrader.py vo.wav times.json vo_lines.txt fontdir/ out.mp4 posts_dir [snap t1,t2]
sys.path.insert(0, sys.argv[6] if len(sys.argv) > 6 else '.')
import cinematic_audio as ca

VO, TIMES, LINES, FD, OUT = sys.argv[1:6]
W, H, FPS, SR, SS = 1080, 1920, 30, 44100, 2
SEG = json.load(open(TIMES)); TXT = [l.strip() for l in open(LINES) if l.strip()]; WORDS = [l.split() for l in TXT]
TT = [a for a, b in SEG]
with wave.open(VO) as w:
    vsr = w.getframerate(); vo = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(float) / 32768
DUR = len(vo) / vsr + 1.2

PAPER = (247, 245, 238); INK = (24, 24, 26); WHITE = (255, 255, 255); GOLD = (214, 168, 79); GOLD_D = (170, 122, 34)
RED = (214, 58, 66); GREY = (150, 150, 150); BLUE = (52, 98, 190); BLUE_D = (30, 60, 130)
LOGO = Image.open('/mnt/project-files/Insta/Logo.png').convert('RGBA')
LOGO = LOGO.resize((int(LOGO.width * 40 / LOGO.height), 40), Image.LANCZOS)

_fc = {}
def F(w, s):
    s = max(8, int(s))
    if (w, s) not in _fc: _fc[(w, s)] = ImageFont.truetype(f'{FD}montserrat-latin-{w}-normal.woff', s)
    return _fc[(w, s)]
def clamp(t): return max(0, min(1, t))
def ease(t): t = clamp(t); return 1 - (1 - t) ** 3
def back(t): t = clamp(t); c = 1.7; return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2
def lerp(a, b, p): return a + (b - a) * p
def A(k, f): return SEG[k][0] + f * (SEG[k][1] - SEG[k][0])
def scene(t): return max([0] + [i for i in range(len(TT)) if t >= TT[i] - .12])


# two-part lines: Gary's sentence(s) first, Tariq's second
SPLIT = {}
for k, n in ((2, 1), (4, 1), (6, 1), (8, 1)):
    s = TXT[k]; i = 0
    for _ in range(n): i = s.index('. ', i) + 1
    SPLIT[k] = (0, i / len(s))
def G(k, f): a, b = SPLIT[k]; return A(k, lerp(a, b, f))
def T(k, f): a, b = SPLIT[k]; return A(k, lerp(b, 1, f))

# paper with grain + soft vignette
rng0 = np.random.default_rng(7)
pap = np.array(PAPER, float)[None, None, :] + rng0.normal(0, 2.6, (H, W, 1))
yy, xx = np.mgrid[0:H, 0:W]; vig = 1 - .06 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
PAPER_IMG = Image.fromarray(np.clip(pap * vig[..., None], 0, 255).astype(np.uint8), 'RGB').convert('RGBA')

BOIL = 0
class Pen:
    def __init__(s, w, h, ox, oy):
        s.img = Image.new('RGBA', (w * SS, h * SS), (0, 0, 0, 0)); s.d = ImageDraw.Draw(s.img); s.ox, s.oy, s.n = ox, oy, 0
    def P(s, x, y): return ((x - s.ox) * SS, (y - s.oy) * SS)
    def stroke(s, pts, col=INK, w=5, prog=1.0, amp=1.0, a=1.0):
        s.n += 1
        if prog <= 0 or a <= 0: return
        pts = np.array(pts, float)
        seg = np.r_[0, np.cumsum(np.hypot(*np.diff(pts, axis=0).T))]
        if seg[-1] < 1: return
        n = max(6, int(seg[-1] / 9) + 1); L = np.linspace(0, seg[-1], n)
        p = np.c_[np.interp(L, seg, pts[:, 0]), np.interp(L, seg, pts[:, 1])]
        r = np.random.default_rng((BOIL * 7919 + s.n * 104729) % 2 ** 32)
        k = np.ones(5) / 5
        def nz(sc): return np.c_[np.convolve(r.normal(0, 1, n), k, 'same'), np.convolve(r.normal(0, 1, n), k, 'same')] * amp * sc
        m = max(2, int(math.ceil(n * clamp(prog))))
        c1 = col + (int(255 * a),); c2 = col + (int(140 * a),)
        q = p + nz(2.2); pp = [s.P(*v) for v in q[:m]]
        s.d.line(pp, fill=c1, width=max(1, int(w * SS)), joint='curve')
        rr = w * SS / 2
        for v in (pp[0], pp[-1]): s.d.ellipse([v[0] - rr, v[1] - rr, v[0] + rr, v[1] + rr], fill=c1)
        q = p + nz(2.6); s.d.line([s.P(*v) for v in q[:m]], fill=c2, width=max(1, int(w * .45 * SS)), joint='curve')
    def ell(s, cx, cy, rx, ry, a0=-100, sweep=375, **kw):
        an = np.radians(np.linspace(a0, a0 + sweep, 40))
        s.stroke(np.c_[cx + rx * np.cos(an), cy + ry * np.sin(an)], **kw)
    def circ(s, cx, cy, r, **kw): s.ell(cx, cy, r, r, **kw)
    def arc(s, cx, cy, r, a0, a1, **kw):
        an = np.radians(np.linspace(a0, a1, 24)); s.stroke(np.c_[cx + r * np.cos(an), cy + r * np.sin(an)], **kw)
    def rect(s, x0, y0, x1, y1, prog=1.0, **kw):
        o = 5; sides = [[(x0 - o, y0), (x1 + o, y0)], [(x1, y0 - o), (x1, y1 + o)], [(x1 + o, y1), (x0 - o, y1)], [(x0, y1 + o), (x0, y0 - o)]]
        for i, sd in enumerate(sides): s.stroke(sd, prog=clamp(prog * 4 - i), **kw)
    def dash(s, x0, x1, y, col=INK, w=2.5, a=1.0, prog=1.0):
        xe = lerp(x0, x1, clamp(prog)); x = x0
        while x < xe: s.stroke([(x, y), (min(x + 14, xe), y)], col=col, w=w, amp=.25, a=a); x += 24
    def fill(s, pts, col, a=.3):
        s.d.polygon([s.P(*v) for v in pts], fill=col + (int(255 * a),))
    def hatch(s, x0, y0, x1, y1, col=INK, gap=11, prog=1.0, w=2.2, a=.8):
        c = x0 + y0; cs = np.arange(x0 + y0 + gap / 2, x1 + y1, gap); m = int(len(cs) * clamp(prog))
        for c in cs[:m]:   # line x + y = c clipped to the box
            xa, xb = max(x0, c - y1), min(x1, c - y0)
            if xb > xa: s.stroke([(xa, c - xa), (xb, c - xb)], col=col, w=w, amp=.6, a=a)
    def text(s, x, y, txt, size, col=INK, wt=900, a=1.0, rot=0, sc=1.0):
        if a <= 0 or sc <= .03: return
        f = F(wt, size * SS * sc)
        if not rot:
            s.d.text(s.P(x, y), txt, font=f, fill=col + (int(255 * a),), anchor='mm'); return
        tw = int(s.d.textlength(txt, font=f)) + 40; th = int(f.size * 1.6)
        im = Image.new('RGBA', (tw, th), (0, 0, 0, 0)); ImageDraw.Draw(im).text((tw / 2, th / 2), txt, font=f, fill=col + (int(255 * a),), anchor='mm')
        im = im.rotate(rot, resample=Image.BICUBIC, expand=True); px, py = s.P(x, y)
        s.img.alpha_composite(im, (int(px - im.width / 2), int(py - im.height / 2)))
    def stamp(s, x, y, txt, size, col, at, t, rot=-9):
        p = clamp((t - at) / .12)
        if p <= 0: return
        sc = 1.6 - .6 * back((t - at) / .28)
        f = F(900, size * sc); tw = ImageDraw.Draw(Image.new('L', (1, 1))).textlength(txt, font=f)
        hw, hh = tw / 2 + 16, size * sc * .62
        an = math.radians(-rot); co, si = math.cos(an), math.sin(an)
        cs = [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh), (-hw, -hh)]
        s.fill([(x + u * co - v * si, y + u * si + v * co) for u, v in cs[:4]], WHITE, .94 * p)
        s.text(x, y, txt, size, col, rot=rot, sc=sc, a=p)
        s.stroke([(x + u * co - v * si, y + u * si + v * co) for u, v in cs], col=col, w=5, a=p)

# ---------------- characters ----------------
POSES = {  # shoulder->elbow, elbow->hand angles per arm, hip->knee, knee->foot per leg (deg, 0 = down, +90 = right)
    'stand': (-12, -6, 12, 6), 'hips': (-40, 50, 40, -50), 'point': (-12, -6, 150, 165), 'allin': (-155, -170, 155, 170),
    'angry': (-100, -175, 100, 175), 'head': (-130, 115, 130, -115), 'shrug': (-70, -140, 70, 140),
    'think': (-12, -6, 25, -146), 'thumb': (-12, -6, 140, 175), 'run': (40, 110, -40, -100), 'walk': (-12, -6, 12, 6)}


def build_tl():
    g = [(0, 'point', 'grin'), (TT[1] - .12, 'stand', 'grin'), (G(2, 0), 'point', 'grin'), (TT[3] - .12, 'hips', 'grin'), (G(4, 0), 'thumb', 'grin'),
         (G(4, .6), 'shrug', 'frown'), (TT[5] - .12, 'stand', 'frown'), (G(6, .3), 'head', 'scared'), (TT[7] - .12, 'stand', 'frown'),
         (G(8, 0), 'head', 'cry'), (TT[9] - .12, 'stand', 'frown'), (TT[10] - .12, 'shrug', 'grin')]
    tr = [(0, 'stand', 'calm'), (A(0, .55), 'think', 'calm'), (TT[1] - .12, 'stand', 'calm'), (T(2, 0), 'think', 'calm'), (T(2, .6), 'hips', 'smile'),
          (TT[3] - .12, 'hips', 'calm'), (T(4, 0), 'thumb', 'smile'), (TT[5] - .12, 'stand', 'calm'), (T(6, 0), 'hips', 'smile'),
          (TT[7] - .12, 'stand', 'calm'), (T(8, 0), 'thumb', 'smile'), (TT[9] - .12, 'stand', 'calm'), (TT[10] - .12, 'thumb', 'smile')]
    return g, tr

TL = None

def pose_at(tl, t):
    i = max([0] + [j for j in range(len(tl)) if t >= tl[j][0]])
    cur = POSES[tl[i][1]]; prev = POSES[tl[i - 1][1]] if i else cur
    p = ease((t - tl[i][0]) / .22)
    return [lerp(a, b, p) for a, b in zip(prev, cur)], tl[i][1], tl[i][2]

def V(a, l): r = math.radians(a); return l * math.sin(r), l * math.cos(r)

def person(pen, kind, cx, fy, t, prog=1.0, shake=0):
    tl = TL[0] if kind == 'g' else TL[1]
    ang, pname, mood = pose_at(tl, t)
    cyc = 0
    if pname in ('run', 'walk'): cyc = math.sin(t * (17 if pname == 'run' else 9))
    fy = fy + 3 * math.sin(t * 3.1 + (0 if kind == 'g' else 1.7)) - (abs(cyc) * 10 if pname == 'run' else 0)
    cx += shake
    col = BLUE if kind == 'g' else GOLD
    def pg(a, b): return clamp((prog - a) / (b - a))
    hx, hy, r = cx, fy - 372, 42
    # legs
    legs = [(-7, -4, 7, 4)]
    if pname == 'run': lt, ls, rt, rs = 38 * cyc, 38 * cyc - 45, -38 * cyc, -38 * cyc - 45
    elif pname == 'walk': lt, ls, rt, rs = 22 * cyc, 22 * cyc - 12, -22 * cyc, -22 * cyc - 12
    else: lt, ls, rt, rs = -7, -4, 7, 4
    for sx, a1, a2, fd in ((-18, lt, ls, -1), (18, rt, rs, 1)):
        h0 = (cx + sx * .6, fy - 172); d1 = V(a1, 88); k1 = (h0[0] + d1[0], h0[1] + d1[1]); d2 = V(a2, 86); f1 = (k1[0] + d2[0], k1[1] + d2[1])
        if pname in ('run', 'walk'): fd = 1
        pen.stroke([h0, k1, f1, (f1[0] + 24 * fd, f1[1] + 2)], w=6, prog=pg(.55, .85))
    # torso
    tor = [(cx - 36, fy - 322), (cx - 30, fy - 172), (cx + 30, fy - 172), (cx + 36, fy - 322)]
    if prog > .3: pen.fill(tor, col if kind == 'g' else (235, 232, 222), .55 if kind == 'g' else 1)
    pen.stroke(tor + [(cx - 36, fy - 322)], w=6, prog=pg(.2, .5))
    if kind == 'g':
        pen.hatch(cx - 30, fy - 318, cx + 30, fy - 176, col=BLUE_D, gap=13, prog=pg(.45, .7), a=.6)
        pen.text(cx, fy - 255, '24/7', 30, WHITE, a=pg(.6, .8))
    else:
        tie = [(cx, fy - 322), (cx - 10, fy - 300), (cx, fy - 220), (cx + 10, fy - 300)]
        if prog > .5: pen.fill(tie, GOLD, 1)
        pen.stroke(tie + [(cx, fy - 322)], w=3.5, prog=pg(.5, .7))
        pen.stroke([(cx - 30, fy - 322), (cx - 8, fy - 270)], w=3.5, prog=pg(.5, .7))
        pen.stroke([(cx + 30, fy - 322), (cx + 8, fy - 270)], w=3.5, prog=pg(.5, .7))
    # arms
    la, lf, ra, rf = ang
    if pname == 'walk': la, lf, ra, rf = la + 25 * cyc, lf + 30 * cyc, ra - 25 * cyc, rf - 30 * cyc
    for sx, a1, a2 in ((-34, la, lf), (34, ra, rf)):
        s0 = (cx + sx, fy - 316); d1 = V(a1, 80); e = (s0[0] + d1[0], s0[1] + d1[1]); d2 = V(a2, 74); hnd = (e[0] + d2[0], e[1] + d2[1])
        pen.stroke([s0, e, hnd], w=6, prog=pg(.45, .75))
        if prog > .7: pen.fill([(hnd[0] + 10 * math.cos(q), hnd[1] + 10 * math.sin(q)) for q in np.linspace(0, 6.28, 12)], WHITE, 1)
        pen.circ(*hnd, 10, w=4, prog=pg(.7, .8))
        if pname == 'thumb' and sx > 0: pen.stroke([(hnd[0] - 2, hnd[1] - 8), (hnd[0] - 4, hnd[1] - 26)], w=5, prog=pg(.75, .85))
    # head
    if prog > .05: pen.fill([(hx + r * math.cos(q), hy + r * math.sin(q)) for q in np.linspace(0, 6.28, 30)], (252, 250, 245), 1)
    pen.circ(hx, hy, r, w=6, prog=pg(0, .25))
    if kind == 'g':   # Ollie: spiky hair + headset
        for j in range(6):
            a0 = math.radians(-160 + j * 28); bx, by = hx + r * math.cos(a0), hy + r * math.sin(a0)
            pen.stroke([(bx, by), (bx + 26 * math.cos(a0 - .3), by + 26 * math.sin(a0 - .3))], w=4.5, prog=pg(.2, .35))
        pen.arc(hx, hy - 2, r + 8, 190, 350, col=BLUE, w=6, prog=pg(.3, .45))
        pen.stroke([(hx - r - 6, hy + 4), (hx - r + 6, hy + 30), (hx - 12, hy + 34)], col=BLUE, w=4, prog=pg(.35, .5))
    else:             # neat hair + glasses
        hair = [(hx + r * math.cos(q), hy + r * math.sin(q)) for q in np.radians(np.linspace(-185, 5, 20))] + [(hx + 30, hy - 26), (hx - 6, hy - 22), (hx - 36, hy - 12)]
        if prog > .3: pen.fill(hair, INK, .92)
        pen.stroke([(hx - 14, hy - 40), (hx - 10, hy - 24)], col=(120, 120, 120), w=3, prog=pg(.3, .4))
    # face
    fp = pg(.8, 1)
    ex = 15; ey = hy - 2
    if mood in ('scared', 'angry'):
        for sx in (-1, 1):
            pen.fill([(hx + sx * ex + 9 * math.cos(q), ey + 9 * math.sin(q)) for q in np.linspace(0, 6.28, 12)], WHITE, fp)
            pen.circ(hx + sx * ex, ey, 9, w=3, prog=fp); pen.circ(hx + sx * ex, ey + 1, 2.5, w=4, prog=fp, amp=.2)
    else:
        for sx in (-1, 1):
            if mood == 'grin': pen.arc(hx + sx * ex, ey + 2, 6, 200, 340, w=4, prog=fp, amp=.3)
            else: pen.circ(hx + sx * ex, ey, 3, w=5, prog=fp, amp=.2)
    if kind == 't':
        for sx in (-1, 1): pen.circ(hx + sx * ex, ey, 12, w=3, prog=fp, amp=.5)
        pen.stroke([(hx - 3, ey - 2), (hx + 3, ey - 2)], w=3, prog=fp)
    br = {'angry': ((-26, -22, -6, -12), (26, -22, 6, -12)), 'scared': ((-26, -14, -7, -24), (26, -14, 7, -24)),
          'cry': ((-26, -14, -7, -24), (26, -14, 7, -24)), 'frown': ((-24, -18, -8, -14), (24, -18, 8, -14))}.get(mood)
    if br:
        for x0, y0, x1, y1 in br: pen.stroke([(hx + x0, ey + y0 - 4), (hx + x1, ey + y1 - 4)], w=4.5, prog=fp)
    my = hy + 20
    if mood in ('grin',):
        mp = [(hx - 18, my - 2), (hx + 18, my - 2)] + [(hx + 18 * math.cos(q), my - 2 + 14 * math.sin(q)) for q in np.radians(np.linspace(0, 180, 12))]
        pen.fill(mp, WHITE, fp); pen.stroke(mp, w=4, prog=fp)
    elif mood in ('smile', 'calm'): pen.arc(hx, my - 14, 16 if mood == 'smile' else 12, 30, 150, w=4, prog=fp)
    elif mood in ('frown', 'cry'): pen.arc(hx, my + 12, 13, 210, 330, w=4, prog=fp)
    elif mood == 'scared': pen.ell(hx, my + 2, 8, 10, w=4, prog=fp)
    elif mood == 'angry': pen.stroke([(hx - 14, my + 4), (hx - 5, my - 1), (hx + 5, my + 4), (hx + 14, my - 1)], w=4, prog=fp)
    if mood in ('scared', 'angry') and prog >= 1:
        for i, (dx, dy) in enumerate(((50, -24), (-52, -12))):
            ph = (t * 1.4 + i * .5) % 1; yd = hy + dy + 30 * ph
            pen.stroke([(hx + dx, yd - 10), (hx + dx - 5, yd + 2), (hx + dx, yd + 7), (hx + dx + 5, yd + 2), (hx + dx, yd - 10)], col=(70, 140, 210), w=3, a=1 - ph)
    if mood == 'cry' and prog >= 1:
        for sx in (-1, 1):
            for j in range(2):
                ph = (t * 1.6 + j * .5 + (sx > 0) * .25) % 1
                pen.circ(hx + sx * (ex + 4), ey + 12 + 50 * ph, 4, col=(70, 140, 210), w=4, a=1 - ph, amp=.3)

# ---------------- layout ----------------
PX = [(120, 528), (552, 960)]; PY0, PY1 = 440, 1290; FY = 1268
SY0, SY1 = 506, 770

def screen_box(pen, x0, x1, prog=1.0):
    pen.fill([(x0, SY0), (x1, SY0), (x1, SY1), (x0, SY1)], WHITE, .9)
    pen.rect(x0, SY0, x1, SY1, w=5, prog=prog)
    mx = (x0 + x1) / 2
    pen.stroke([(mx, SY1), (mx, SY1 + 22)], w=5, prog=prog); pen.stroke([(mx - 34, SY1 + 24), (mx + 34, SY1 + 24)], w=5, prog=prog)

def axes(pen, x0, x1, a=1.0):
    for i in range(1, 4): pen.stroke([(x0 + 14, SY0 + i * (SY1 - SY0) / 4), (x1 - 14, SY0 + i * (SY1 - SY0) / 4)], col=(205, 205, 205), w=1.6, amp=.4, a=a)

def chart_pts(x0, x1, vals):
    xs = np.linspace(x0 + 22, x1 - 22, len(vals)); return [(x, SY1 - 18 - v * (SY1 - SY0 - 36)) for x, v in zip(xs, vals)]

def countv(pen, x, y, a, b, p, col, size=30):
    v = lerp(a, b, ease(p)); pen.text(x, y, ('-' if v < -.5 else '') + f'${abs(v):,.0f}', size, col)


def keyed(keys, t):
    if t <= keys[0][0]: return keys[0][1]
    for (a, va), (b, vb) in zip(keys, keys[1:]):
        if t < b: return lerp(va, vb, ease((t - a) / max(.01, b - a)))
    return keys[-1][1]

def meter(pen, ci, cx, t):   # TILT emotion meter at the outer edge of each panel
    lv = keyed(MKEYS[ci], t); mx = cx - 180 if ci == 0 else cx + 156; y0, y1 = 870, 1130
    sh = 4 * math.sin(t * 60) if lv > .85 else 0; mx += sh
    pen.text(mx + 12, y0 - 22, 'TILT', 20, INK)
    col = tuple(int(lerp(a, b, clamp((lv - .3) / .5))) for a, b in zip(GOLD, RED))
    fh = (y1 - y0 - 8) * lv
    pen.fill([(mx + 4, y1 - 4 - fh), (mx + 20, y1 - 4 - fh), (mx + 20, y1 - 4), (mx + 4, y1 - 4)], col, 1)
    pen.rect(mx, y0, mx + 24, y1, w=3.5)
    for i in range(1, 4): pen.stroke([(mx, y0 + i * (y1 - y0) / 4), (mx + 8, y0 + i * (y1 - y0) / 4)], w=2.5, amp=.3)
    if ci == 0 and lv > .97:
        pen.stamp(mx + 40, y0 + 30, 'MAX', 30, RED, MAXT, t, rot=-14)

def candle(pen, x, top, bot, up, prog=1.0, w=30):
    if prog <= 0: return
    bot = lerp(top, bot, ease(prog))
    pen.stroke([(x, top - 12), (x, bot + 10)], w=3, amp=.4)
    pen.fill([(x - w / 2, top), (x + w / 2, top), (x + w / 2, bot), (x - w / 2, bot)], GOLD if up else INK, 1)
    pen.rect(x - w / 2, top, x + w / 2, bot, w=3.5)

def note(pen, x0, x1, y, title, sub, col, at, t, icon='!'):   # phone notification card sliding in
    p = back((t - at) / .3)
    if p <= .03: return
    y = y - 60 * (1 - p); a = clamp((t - at) / .15)
    pen.fill([(x0, y), (x1, y), (x1, y + 92), (x0, y + 92)], WHITE, a)
    pen.rect(x0, y, x1, y + 92, w=3.5, a=a)
    pen.fill([(x0 + 12, y + 20), (x0 + 64, y + 20), (x0 + 64, y + 72), (x0 + 12, y + 72)], col, a)
    if icon == 'check': pen.stroke([(x0 + 24, y + 46), (x0 + 34, y + 58), (x0 + 54, y + 32)], col=WHITE, w=6, a=a)
    else: pen.text(x0 + 38, y + 46, icon, 34, WHITE, a=a)
    pen.d.text(pen.P(x0 + 78, y + 32), title, font=F(900, 21 * SS), fill=col + (int(255 * a),), anchor='lm')
    pen.d.text(pen.P(x0 + 78, y + 64), sub, font=F(700, 18 * SS), fill=(90, 90, 90, int(255 * a)), anchor='lm')


def phone_icon(pen, x, y, s, col, a=1.0):
    pen.fill([(x - 26 * s, y - 46 * s), (x + 26 * s, y - 46 * s), (x + 26 * s, y + 46 * s), (x - 26 * s, y + 46 * s)], col, a)
    pen.rect(x - 26 * s, y - 46 * s, x + 26 * s, y + 46 * s, w=4, a=a)
    pen.circ(x, y + 36 * s, 4 * s, col=WHITE, w=3, a=a)

def watch_icon(pen, x, y, s, col, a=1.0):
    pen.fill([(x - 14 * s, y - 54 * s), (x + 14 * s, y - 54 * s), (x + 14 * s, y + 54 * s), (x - 14 * s, y + 54 * s)], INK, a)
    pen.fill([(x + 30 * s * math.cos(q), y + 30 * s * math.sin(q)) for q in np.linspace(0, 6.28, 24)], col, a)
    pen.circ(x, y, 30 * s, w=4, a=a); pen.stroke([(x, y), (x, y - 18 * s), ], w=3, a=a); pen.stroke([(x, y), (x + 12 * s, y)], w=3, a=a)

def jar(pen, x, y0, y1, lv, label, col, a=1.0):
    pen.fill([(x - 50, y1 - (y1 - y0) * lv), (x + 50, y1 - (y1 - y0) * lv), (x + 50, y1), (x - 50, y1)], col, .9 * a)
    pen.stroke([(x - 56, y0 - 6), (x - 50, y1), (x + 50, y1), (x + 56, y0 - 6)], w=5, a=a)
    pen.text(x, y1 + 26, label, 18, INK, wt=800, a=a)

def laptop(pen, x, y, close, a=1.0):
    pen.stroke([(x - 90, y), (x + 90, y)], w=6, a=a)
    ang = math.radians(lerp(100, 8, ease(close)))
    pen.stroke([(x - 80, y - 4), (x - 80 + 160 * math.cos(math.radians(0)), y - 4)], w=3, a=a)
    top = [(x - 80, y - 6), (x + 80, y - 6), (x + 80 - 0, y - 6 - 120 * math.sin(ang)), (x - 80, y - 6 - 120 * math.sin(ang))]
    pen.fill(top, (230, 230, 232), a); pen.stroke(top + [top[0]], w=4.5, a=a)

def logrow(pen, sx0, sx1, y, label, amt, col, at, t, icon):   # trade-log row sliding in
    q = back((t - at) / .3)
    if q <= .03: return
    xo = 90 * (1 - q); a = clamp((t - at) / .12)
    pen.fill([(sx0 + 14 + xo, y - 24), (sx1 - 14 + xo, y - 24), (sx1 - 14 + xo, y + 24), (sx0 + 14 + xo, y + 24)], (246, 244, 238), a)
    pen.fill([(sx0 + 24 + xo, y - 14), (sx0 + 52 + xo, y - 14), (sx0 + 52 + xo, y + 14), (sx0 + 24 + xo, y + 14)], col, a)
    if icon == 'check': pen.stroke([(sx0 + 30 + xo, y), (sx0 + 36 + xo, y + 7), (sx0 + 47 + xo, y - 7)], col=WHITE, w=3.5, amp=.2, a=a)
    else:
        pen.stroke([(sx0 + 31 + xo, y - 7), (sx0 + 45 + xo, y + 7)], col=WHITE, w=3.5, amp=.2, a=a)
        pen.stroke([(sx0 + 45 + xo, y - 7), (sx0 + 31 + xo, y + 7)], col=WHITE, w=3.5, amp=.2, a=a)
    pen.d.text(pen.P(sx0 + 64 + xo, y), label, font=F(900, 22 * SS), fill=INK + (int(255 * a),), anchor='lm')
    pen.d.text(pen.P(sx1 - 24 + xo, y), amt, font=F(900, 22 * SS), fill=col + (int(255 * a),), anchor='rm')

def cracks(pen, x, y, sx0, sx1, p, a=.75):   # glass cracks spreading from the impact point
    if p <= 0: return
    r = np.random.default_rng(11)
    for j in range(7):
        an = j / 7 * 6.28 + r.uniform(-.3, .3); L = r.uniform(90, 190); pts = [(x, y)]
        for st in range(4):
            an += r.uniform(-.45, .45); px, py = pts[-1]
            pts.append((min(sx1 - 6, max(sx0 + 6, px + L / 4 * math.cos(an))), min(SY1 - 6, max(SY0 + 6, py + L / 4 * math.sin(an)))))
        pen.stroke(pts, col=INK, w=2.6, amp=.3, prog=ease(p), a=a)
    pen.circ(x, y, 10, col=INK, w=2.5, prog=ease(p), a=a)

def sparkles(pen, x, y, r_, big=1.0):   # four-point gold glints that pop in one by one
    for j, (dx, dy, sz) in enumerate(((-120, -40, 18), (115, -55, 14), (-95, 45, 12), (130, 35, 16))):
        q = r_ - j * .12
        if q <= 0: continue
        s_ = sz * big * (back(q / .25)) * (.75 + .25 * math.sin(q * 6 + j)); cx_, cy_ = x + dx * big, y + dy * big
        pen.fill([(cx_, cy_ - s_), (cx_ + s_ * .28, cy_ - s_ * .28), (cx_ + s_, cy_), (cx_ + s_ * .28, cy_ + s_ * .28),
                  (cx_, cy_ + s_), (cx_ - s_ * .28, cy_ + s_ * .28), (cx_ - s_, cy_), (cx_ - s_ * .28, cy_ - s_ * .28)], GOLD, 1)

def panel(ci, t, k, hits):
    x0, x1 = PX[ci]; pen = Pen(x1 - x0 + 40, PY1 - PY0 + 40, x0 - 20, PY0 - 20); cx = (x0 + x1) / 2
    sx0, sx1 = x0 + 20, x1 - 20; scx = (sx0 + sx1) / 2; scy = (SY0 + SY1) / 2
    col = BLUE if ci == 0 else GOLD
    intro = ease((t - CEND + .05) / .7)
    pen.rect(x0, PY0, x1, PY1, w=4, prog=intro, col=(60, 60, 64))
    shake = 0
    for at, s in hits:
        if ci == 0 and 0 < t - at < .3: shake = int(9 * s * math.sin((t - at) * 70) * (1 - (t - at) / .3))
    screen_box(pen, sx0 + shake, sx1 + shake, intro)
    is_g = ci == 0
    if k == 0:   # trade counters
        pen.text(scx, SY0 + 60, 'TRADES TODAY', 22, GREY, wt=800)
        n = trades_open(t) if is_g else 0
        pen.text(scx, SY0 + 160, f'{n}', 110, BLUE if is_g else INK)
    elif k == 2:
        if is_g:
            n = min(12, int(12 * clamp((t - G(2, .05)) / (G(2, .85) - G(2, .05))) + 1))
            for j in range(12):   # trade tickets filling up
                if j >= n: break
                x = sx0 + 40 + (j % 4) * 80; y = SY0 + 50 + (j // 4) * 62
                win = j % 3 != 1
                pen.fill([(x, y), (x + 62, y), (x + 62, y + 44), (x, y + 44)], (236, 242, 252) if win else (252, 236, 236), 1)
                pen.rect(x, y, x + 62, y + 44, w=3); pen.text(x + 31, y + 22, ('+' if win else '-') + str(3 + (j * 7) % 9), 20, GOLD_D if win else RED)
            pen.text(scx, SY1 - 30, f'{n} TRADES BEFORE LUNCH', 20, BLUE)
        else:
            axes(pen, sx0, sx1)
            pen.stroke(chart_pts(sx0, sx1, [.4, .44, .41, .46, .43, .45]), col=INK, w=5, prog=clamp((t - T(2, 0)) / .6))
            q = ease((t - T(2, .2)) / .4)
            if q > 0:
                pen.fill([(scx + 40, SY0 + 40), (sx1 - 20, SY0 + 40), (sx1 - 20, SY0 + 110), (scx + 40, SY0 + 110)], GOLD, .25 * q)
                pen.text((scx + sx1) / 2 + 10, SY0 + 75, 'SETUP?', 20, GOLD_D, a=q)
            pen.stamp(scx - 20, scy + 60, 'WAIT', 46, GOLD_D, T(2, .45), t, rot=-7)
    elif k == 4:   # fees eat the small wins
        if is_g:
            p1 = ease((t - G(4, .05)) / .4); p2 = ease((t - G(4, .45)) / .4)
            pen.text(sx0 + 70, SY0 + 70, 'PROFIT', 20, GREY); pen.text(sx0 + 70, SY0 + 150, 'FEES', 20, GREY)
            pen.fill([(sx0 + 120, SY0 + 52), (sx0 + 120 + 200 * p1, SY0 + 52), (sx0 + 120 + 200 * p1, SY0 + 88), (sx0 + 120, SY0 + 88)], GOLD, 1)
            pen.fill([(sx0 + 120, SY0 + 132), (sx0 + 120 + 167 * p2, SY0 + 132), (sx0 + 120 + 167 * p2, SY0 + 168), (sx0 + 120, SY0 + 168)], RED, 1)
            if p1 > .9: pen.text(sx0 + 120 + 200 + 4 - 40, SY0 + 70, '+$30', 22, INK)
            if p2 > .9: pen.text(sx0 + 120 + 167 - 36, SY0 + 150, '-$25', 22, WHITE)
            pen.text(scx, SY1 - 36, 'NET: +$5', 30, BLUE, a=clamp((t - G(4, .8)) / .2), sc=1 + .4 * (1 - back((t - G(4, .8)) / .3)))
        else:
            pen.text(scx, scy - 50, '$0', 96, GREY, a=clamp((t - T(4, 0)) / .2))
            note(pen, sx0 + 12, sx1 - 12, SY1 - 112, 'NO SETUP TODAY', 'No trade is a position', GOLD_D, T(4, .35), t, icon='check')
    elif k == 6:   # the weekly count
        if is_g:
            n = int(lerp(12, 60, ease((t - G(6, 0)) / (G(6, .45) - G(6, 0)))))
            pen.text(sx0 + 80, SY0 + 46, 'TRADES', 20, GREY); pen.text(sx0 + 80, SY0 + 100, f'{n}', 64, BLUE)
            h = ease((t - G(6, .45)) / (KEY - G(6, .45)))
            pen.text(sx1 - 90, SY0 + 46, 'SCREEN', 20, GREY)
            pen.rect(sx1 - 120, SY0 + 70, sx1 - 60, SY1 - 20, w=3.5)
            pen.fill([(sx1 - 114, SY1 - 26 - (SY1 - SY0 - 102) * h), (sx1 - 66, SY1 - 26 - (SY1 - SY0 - 102) * h), (sx1 - 66, SY1 - 26), (sx1 - 114, SY1 - 26)], RED if h > .7 else BLUE, 1)
            pen.text(sx1 - 160, SY1 - 26 - (SY1 - SY0 - 102) * h, f'{int(50 * h)}H', 28, RED if h > .7 else BLUE)
            pen.stamp(sx0 + 100, SY1 - 50, 'BURNOUT', 34, RED, KEY, t, rot=-7)
        else:
            pen.text(scx, SY0 + 46, 'TRADES', 20, GREY); pen.text(scx, SY0 + 110, '3', 80, INK, a=clamp((t - T(6, 0)) / .2))
            for j in range(3):
                q = clamp((t - T(6, .25) - j * .18) / .15)
                if q > 0: x = scx - 70 + j * 70; pen.stroke([(x - 14, SY1 - 70), (x - 2, SY1 - 56), (x + 18, SY1 - 84)], col=GOLD_D, w=7, a=q)
    elif k == 8:
        if is_g:
            pen.text(scx, scy - 50, '-2%', 100, RED, a=clamp((t - G(8, 0)) / .2), sc=1 + .4 * (1 - back((t - G(8, 0)) / .3)))
            note(pen, sx0 + 12, sx1 - 12, SY1 - 112, 'EXHAUSTED', 'Fees + tired entries', RED, G(8, .35), t)
        else:
            gp = ease((t - T(8, 0)) / .5)
            if gp > 0: pen.fill([(scx + 120 * math.cos(q), scy - 50 + 70 * math.sin(q)) for q in np.linspace(0, 6.28, 30)], GOLD, .16 * gp)
            pen.text(scx, scy - 50, '+4%', 100, GOLD_D, a=clamp((t - T(8, 0)) / .2), sc=1 + .4 * (1 - back((t - T(8, 0)) / .3)))
            sparkles(pen, scx, scy - 50, t - T(8, .15))
            note(pen, sx0 + 12, sx1 - 12, SY1 - 112, 'FRESH', 'Ready for next week', GOLD_D, T(8, .45), t, icon='check')
    elif k == 10:
        a0 = TT[10] - .12 + (0 if is_g else .25)
        if not is_g: sparkles(pen, scx, scy + 6, t - a0 - .2, big=1.3)
        pen.text(scx, scy + 6, 'BURNED OUT' if is_g else 'SHARP', 48 if is_g else 66, RED if is_g else GOLD_D, sc=1 + .5 * (1 - back((t - a0) / .3)), a=clamp((t - a0) / .1))
        if not is_g and t > a0:
            r = np.random.default_rng(3)
            for j in range(26):
                ph = ((t - a0) * .5 + r.random()) % 1; xx = sx0 + r.random() * (sx1 - sx0); yy = SY0 - 40 + ph * 900
                pen.stroke([(xx, yy), (xx + 10, yy + 6)], col=GOLD if j % 2 else INK, w=5, amp=.3, a=1 - ph)
    if k <= 8 or k == 10: meter(pen, ci, cx, t)
    person(pen, 'g' if is_g else 't', cx, FY, t, intro, shake)
    # name tag: name big, role small
    nm, role = ('OLLIE', 'THE OVERTRADER') if is_g else ('TARIQ', 'THE TRADER')
    sp = back((t - (A(0, .45) if is_g else A(0, .6))) / .3)
    if sp > .03:
        f = F(900, 30 * SS * sp); tw = max(pen.d.textlength(nm, font=f) / SS, 110 * sp)
        px, py = cx, PY0 + 40
        pen.fill([(px - tw / 2 - 22, py - 30 * sp), (px + tw / 2 + 22, py - 30 * sp), (px + tw / 2 + 22, py + 30 * sp), (px - tw / 2 - 22, py + 30 * sp)], col, 1)
        pen.text(px, py - 6 * sp, nm, 30, WHITE if is_g else INK, sc=sp)
        pen.text(px, py + 18 * sp, role, 13, WHITE if is_g else INK, wt=800, sc=sp)
    return pen

def active(ci, t, k):
    if k in (2, 4, 6, 8):
        mid = A(k, SPLIT[k][1]) - .08; g_on = t < mid
        return 1.0 if (g_on == (ci == 0)) else .45
    return 1.0

HEAD = {1: ('MONDAY', 'MORNING'), 2: ('MONDAY', 'MORNING'), 3: ('', 'EVERY SMALL WIN'), 4: ('', 'EVERY SMALL WIN'),
        5: ('FRIDAY', 'THE COUNT'), 6: ('FRIDAY', 'THE COUNT'), 7: ('', 'THE RESULT'), 8: ('', 'THE RESULT')}

def headline(img, t, k):
    d = ImageDraw.Draw(img); y = 388
    if k == 0:
        parts = [('MEET ', INK), ('OLLIE,', BLUE), (' THE 24/7 TRADER', INK)]; a0 = CEND
    elif k == 10:
        if t < A(10, .3): parts = [('BURNED OUT ', RED), ('VS ', INK), ('SHARP', GOLD_D)]; a0 = TT[10] - .12
        else: parts = [('WHICH ONE ARE YOU?', INK)]; a0 = A(10, .3)
    elif HEAD.get(k):
        r, s = HEAD[k]; parts = ([(r + ': ', GOLD_D)] if r else []) + [(s, INK)]
        a0 = TT[k] - .12 if k not in (2, 4, 6, 8) else TT[k - 1] - .12
    else: return
    size = 60
    while sum(d.textlength(p, font=F(900, size)) for p, c in parts) > 820: size -= 2
    if k == 0 and t < CEND: return
    f = F(900, size); words = [(w + ' ', c) for p, c in parts for w in p.split()]
    tw = d.textlength(''.join(w for w, c in words).rstrip(), font=f); x = W / 2 - tw / 2
    lay = Image.new('RGBA', (W, 120), (0, 0, 0, 0)); dl = ImageDraw.Draw(lay)
    for i, (w, c) in enumerate(words):
        q = ease((t - a0 - i * .06) / .28)
        if q > 0: dl.text((x, 60 + 34 * (1 - q)), w, font=f, fill=c + (int(255 * q),), anchor='lm')
        x += d.textlength(w, font=f)
    img.alpha_composite(lay, (0, y - 60))

def banner(img, t, k):
    if k not in (1, 3, 5, 7): return
    a0, a1 = TT[k] - .12, TT[k + 1] - .2
    if t < a0 or t > a1 + .3: return
    rn, top = HEAD[k]; ch = (1, 3, 5, 7).index(k) + 1
    band = Image.new('RGBA', (W, 300), INK + (255,)); d = ImageDraw.Draw(band, 'RGBA')
    d.text((140, 46), f'0{ch} / 04', font=F(800, 24), fill=(120, 120, 124), anchor='lm')
    if rn: d.text((540, 92), rn, font=F(900, 50), fill=GOLD, anchor='mm')
    sz = 104
    while d.textlength(top, font=F(900, sz)) > 800: sz -= 4
    q = ease((t - a0 - .12) / .35)
    d.text((540, 190 + 30 * (1 - q)), top, font=F(900, sz), fill=WHITE + (int(255 * q),), anchor='mm')
    lw = 360 * ease((t - a0 - .3) / .4); d.rectangle([540 - lw / 2, 252, 540 + lw / 2, 260], fill=GOLD)
    x = int(-W * (1 - ease((t - a0) / .3)) + W * ease((t - a1) / .25))
    if not -W < x < W: return
    full = Image.new('RGBA', (W, 300), (0, 0, 0, 0)); full.paste(band, (x, 0))
    sh = Image.new('RGBA', (W, 340), (0, 0, 0, 0)); sh.paste((0, 0, 0, 70), (max(0, x), 30, min(W, x + W), 330))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)), (0, 715 - 20))
    img.alpha_composite(full, (0, 715))



def quote(img, t):
    k = scene(t)
    if k != 9: return 0
    a0 = TT[9] - .12; p = ease((t - a0) / .3)
    pen = Pen(W, 900, 0, 420)
    pen.fill([(110, 520), (970, 520), (970, 1240), (110, 1240)], WHITE, .97 * p)
    pen.rect(110, 520, 970, 1240, w=6, prog=ease((t - a0) / .5))
    lines = [('MORE TRADES', INK, 92), ("DON'T MEAN", INK, 76), ('MORE MONEY.', INK, 88), ('BETTER', GOLD_D, 116), ('TRADES DO.', GOLD_D, 100)]
    ys = [630, 740, 840, 1000, 1110]; rel = [0, .15, .3, .65, .78]
    for (s, c, z), y, r in zip(lines, ys, rel):
        at = A(9, r); pen.text(540, y, s, z, c, sc=back((t - at) / .3), a=clamp((t - at) / .1))
    pen.stroke([(330, 1175), (750, 1169)], col=GOLD, w=10, prog=ease((t - A(9, .9)) / .4))
    img.alpha_composite(pen.img.reduce(SS), (0, 420)); return p

def captions(img, t, k):   # word-by-word, 3 words at a time, active word on a gold block
    if k >= len(SEG): return
    a, b = SEG[k]
    if not (a - .05 <= t <= b + .25): return
    ws = WORDS[k]; wt = np.cumsum([0] + [len(w) + 2 for w in ws]); wt = a + (b - a) * wt / wt[-1]
    i = int(np.clip(np.searchsorted(wt, t, 'right') - 1, 0, len(ws) - 1))
    c0 = i // 3 * 3; chunk = ws[c0:c0 + 3]
    d = ImageDraw.Draw(img); f = F(900, 56); gap = 18
    widths = [d.textlength(w, font=f) for w in chunk]; tot = sum(widths) + gap * (len(chunk) - 1)
    if tot > 840: f = F(900, int(56 * 840 / tot)); widths = [d.textlength(w, font=f) for w in chunk]; tot = sum(widths) + gap * (len(chunk) - 1)
    x = 540 - tot / 2; y = 1340
    for j, (w_, wd) in enumerate(zip(chunk, widths)):
        if c0 + j == i:
            pp = back((t - wt[i]) / .15)
            d.rounded_rectangle([x - 10, y - 4 - 6 * pp, x + wd + 10, y + f.size + 14], 10, fill=GOLD)
        d.text((x, y), w_, font=f, fill=INK if c0 + j <= i else (150, 150, 150)); x += wd + gap

def endcard(img, t):
    a0 = SEG[10][1] - .25
    if t < a0: return False
    q = ease((t - a0) / .35); y0 = int(1300 + 200 * (1 - q))
    band = Image.new('RGBA', (840, 170), INK + (255,)); d = ImageDraw.Draw(band)
    parts = [('O', BLUE), ('  or  ', WHITE), ('T', GOLD), (' ?', WHITE)]; f = F(900, 92)
    tw = sum(d.textlength(p, font=f) for p, c in parts); x = 420 - tw / 2
    for p, c in parts: d.text((x, 72), p, font=f, fill=c, anchor='lm'); x += d.textlength(p, font=f)
    d.text((420, 140), 'NEXT: GARY MEETS THE PROP FIRM BOSS', font=F(800, 22), fill=(170, 170, 174), anchor='mm')
    m = Image.new('L', band.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, 839, 169], 26, fill=255); band.putalpha(m)
    img.alpha_composite(band, (120, y0)); return True

def coldopen(img, t):   # black open on the starting balance, splits open on 'two very different plans'
    if t > CEND + .45: return
    lay = Image.new('RGBA', (W, H), INK + (255,)); d = ImageDraw.Draw(lay, 'RGBA')
    d.text((540, 587), 'TRADES TODAY', font=F(800, 32), fill=(170, 170, 174), anchor='mm')
    n = trades_open(t); pul = 1 + .06 * (1 - ease((t - n_at(n)) / .12))
    d.text((540, 800), f'{n}', font=F(900, int(260 * pul)), fill=WHITE, anchor='mm')
    pk = A(0, .22)
    lw = 520 * ease((t - .2) / .6); d.rectangle([540 - lw / 2, 948, 540 + lw / 2, 956], fill=GOLD)
    if t < pk: words = [('MEET', WHITE), ('OLLIE.', BLUE)]; w0 = .05
    else: words = [('NOT', WHITE), ('A', WHITE), ('GAMBLER.', WHITE)]; w0 = pk
    f2 = F(900, 66); tw = sum(d.textlength(w + ' ', font=f2) for w, c in words) - d.textlength(' ', font=f2); x = 540 - tw / 2
    for i, (w, c) in enumerate(words):
        q = ease((t - w0 - i * .09) / .25)
        if q > 0: d.text((x, 1080 + 30 * (1 - q)), w, font=f2, fill=c + (int(255 * q),), anchor='lm')
        x += d.textlength(w + ' ', font=f2)
    sp = ease((t - CEND) / .45)
    if sp <= 0: img.alpha_composite(lay); return
    off = int(sp * H / 2 + 4)
    if off >= H // 2: return
    top = lay.crop((0, off, W, H // 2)); img.alpha_composite(top, (0, 0))
    img.alpha_composite(lay.crop((0, H // 2, W, H - off)), (0, H // 2 + off))

def n_at(n): return CEND * (n / 47) ** 1.6   # trade counter: slow, then frantic
def trades_open(t): return int(47 * clamp(t / CEND) ** (1 / 1.6))

def logo(img):
    d = ImageDraw.Draw(img); d.rounded_rectangle([120, 262, 120 + LOGO.width + 28, 262 + 58], 29, fill=INK)
    img.alpha_composite(LOGO, (134, 271))



def hit_list():
    return [(.05, 1.0), (A(0, .22), .8), (A(0, .5), 1.0), (TT[1] - .12, .9), (G(2, .5), .7), (T(2, .45), .6),
            (TT[3] - .12, 1.0), (G(4, .8), .8), (T(4, .35), .5), (TT[5] - .12, 1.0), (G(6, .45), .8), (KEY, 1.2),
            (T(6, .25), .5), (TT[7] - .12, 1.0), (G(8, 0), 1.1), (G(8, .35), .8), (T(8, 0), .6), (T(8, .45), .6),
            (TT[9] - .12, 1.0), (A(9, .5), .9), (A(9, .7), 1.1), (TT[10] - .12, 1.0), (TT[10] + .13, .7), (A(10, .3), .8)]

def frame(t):
    global BOIL
    BOIL = int(t * 8); k = scene(t); hits = HITS
    img = PAPER_IMG.copy(); lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    if t > CEND - .1: lay.alpha_composite(SHADOW)
    for ci in (0, 1):
        pen = panel(ci, t, k, hits); im = pen.img.reduce(SS)
        if ci == 0 and k >= 6 and t > KEY + .1:   # Gary's world drains of colour after the wipeout
            dp = .55 * ease((t - KEY - .1) / .6); g = im.convert('LA').convert('RGBA'); g.putalpha(im.split()[3])
            im = Image.blend(im, g, dp)
        gl = t - KEY
        if ci == 0 and 0 <= gl < .28:   # slippage glitch: RGB split + sliced offsets
            r_, g_, b_, a_ = im.split(); o = int(10 * (1 - gl / .28)) + 2
            im = Image.merge('RGBA', (r_.transform(im.size, Image.AFFINE, (1, 0, -o, 0, 1, 0)), g_, b_.transform(im.size, Image.AFFINE, (1, 0, o, 0, 1, 0)), a_))
            rr = np.random.default_rng(int(gl * 40))
            for _ in range(3):
                y0 = int(rr.uniform(60, 360)); hh = int(rr.uniform(10, 30)); dx = int(rr.uniform(-22, 22))
                sl = im.crop((0, y0, im.width, y0 + hh)); im.paste((0, 0, 0, 0), (0, y0, im.width, y0 + hh)); im.alpha_composite(sl, (max(0, dx), y0))
        a = active(ci, t, k)
        if k in (1, 3, 5, 7): a = min(a, .5)
        if a < 1:   # focus pull: the side not talking softens and recedes
            im = im.filter(ImageFilter.GaussianBlur(1.8 * (1 - a) / .55))
            ov = Image.new('RGBA', (im.width, im.height), PAPER + (int(255 * (1 - a) * .7),)); ov.putalpha(im.split()[3].point(lambda v: int(v * (1 - a) * .7)))
            im = im.copy(); im.alpha_composite(ov)
        lay.alpha_composite(im, (PX[ci][0] - 20, PY0 - 20))
    # camera: slow drift + punch-in on each new line toward the speaker + a hard push into the slippage
    r = t - (TT[k] - .12); z = 1.008 + .006 * math.sin(t * .7) + .05 * max(0, 1 - r / .22)
    fx, fy = 540, 865
    if k in (2, 4, 6, 8): z += .02 * ease((t - TT[k]) / 1.5); fx = 324 if active(0, t, k) == 1 else 756
    sp = ease((t - (KEY - .2)) / .3) * (1 - ease((t - (T(6, 0) - .35)) / .35))
    if sp > 0: z += .07 * sp; fx = lerp(fx, 324, sp); fy = lerp(fy, 880, sp)
    zw, zh = int(W * z), int(H * z); big = lay.resize((zw, zh), Image.BILINEAR)
    cx = int(fx * z - fx); cy = int(fy * z - fy); lay = big.crop((cx, cy, cx + W, cy + H))
    img.alpha_composite(lay)
    for at, s in hits:   # danger pulse on Gary's big hits instead of white flashes
        if s >= 1.1 and 0 <= t - at < .5: img.alpha_composite(_vig(RED_VIG, 1 - (t - at) / .5))
    banner(img, t, k); quote(img, t)
    headline(img, t, k)
    if not endcard(img, t): captions(img, t, k)
    coldopen(img, t); logo(img)
    return img.convert('RGB')

def _vig(v, q):
    o = v.copy(); o.putalpha(v.split()[3].point(lambda a: int(a * q))); return o

# crisp synthesized SFX (freesound previews return 403 from this container, so these are made here)
def _t(l): return np.arange(int(l * SR)) / SR
def sfx(name):
    if name == 'whoosh':
        t = _t(.45); n = np.random.default_rng(5).normal(0, 1, len(t)); env = np.sin(np.pi * t / t[-1]) ** 2
        return ca.bp(n, 300, 3500) * env * 1.6
    if name == 'ping':   # phone notification: two soft bell tones
        out = np.zeros(int(.6 * SR))
        for at, f in ((0, 1318.5), (.11, 1760)):
            t = _t(.45); tone = (np.sin(2 * np.pi * f * t) + .3 * np.sin(4 * np.pi * f * t)) * np.exp(-t * 9)
            i = int(at * SR); out[i:i + len(t)] += tone
        return out * .8
    if name == 'cash':   # ka-ching: drawer clack + bright bell
        t = _t(.9); clack = ca.hp(np.random.default_rng(2).normal(0, 1, len(t)), 1500) * np.exp(-t * 60)
        bell = sum(np.sin(2 * np.pi * f * t) * g for f, g in ((2093, 1), (3136, .6), (4186, .35), (5274, .2))) * np.exp(-t * 4)
        out = clack * .8; i = int(.09 * SR); out[i:] += bell[:len(out) - i] * .7
        return out
    if name == 'coin':   # a few metallic clinks
        out = np.zeros(int(.8 * SR)); r = np.random.default_rng(9)
        for j in range(5):
            t = _t(.25); f = r.uniform(3200, 5200)
            c = (np.sin(2 * np.pi * f * t) + .5 * np.sin(2 * np.pi * f * 1.48 * t)) * np.exp(-t * 28)
            i = int(j * .11 * SR + r.uniform(0, .03) * SR); out[i:i + len(t)] += c * (1 - j * .12)
        return out * .7
    if name == 'glitch':   # bit-crushed stutter
        t = _t(.32); n = np.random.default_rng(4).normal(0, 1, len(t)); sq = np.sign(np.sin(2 * np.pi * 140 * t))
        g = (np.floor(t * 28) % 2 == 0).astype(float); x = (ca.bp(n, 800, 6000) * .7 + sq * .4) * g * np.exp(-t * 4)
        return np.round(x * 6) / 6
    if name == 'crack':    # glass crack: sharp transients + glassy ring
        t = _t(1.0); r = np.random.default_rng(6); out = np.zeros(len(t))
        for j in range(6):
            i = int((j * .025 + r.uniform(0, .015)) * SR); b = ca.hp(r.normal(0, 1, int(.05 * SR)), 2500) * np.exp(-np.arange(int(.05 * SR)) / SR * 90)
            out[i:i + len(b)] += b * (1 - j * .1)
        ring = sum(np.sin(2 * np.pi * f * t) * np.exp(-t * d) for f, d in ((2900, 9), (4300, 12), (6100, 15))) * .25
        return out + ring
    if name == 'shimmer':  # clean rising chime
        out = np.zeros(int(1.4 * SR))
        for j, f in enumerate((1046.5, 1318.5, 1568, 2093)):
            t = _t(1.0); c = (np.sin(2 * np.pi * f * t) + .25 * np.sin(4 * np.pi * f * t)) * np.exp(-t * 3.5); i = int(j * .07 * SR); out[i:i + len(t)] += c * .5
        return out
    if name == 'heart':
        t = _t(.5); th = lambda f, d: np.sin(2 * np.pi * f * t * (1 - t)) * np.exp(-t * d)
        out = np.zeros(int(.5 * SR)); a = th(55, 18); i = int(.16 * SR); out += a; out[i:] += a[:len(out) - i] * .7
        return out
    if name == 'alarm':   # breaking-news double beep
        out = np.zeros(int(.7 * SR))
        for at in (0, .22):
            t = _t(.16); b = np.sign(np.sin(2 * np.pi * 880 * t)) * .5 * np.exp(-t * 6); i = int(at * SR); out[i:i + len(t)] += ca.lp(b, 4000)
        return out
    return None

def audio():
    N = int(DUR * SR); dry = np.zeros((N, 2)); fx = np.zeros((N, 2))
    def add(buf, sig, at, g=1.0, width=0):
        if sig is None: return
        i = int(at * SR)
        if i >= N or i < 0: return
        if sig.ndim == 1: sig = np.stack([sig, sig], 1)
        sig = sig[:N - i] * g; rr = np.roll(sig, width, axis=0) if width else sig
        buf[i:i + len(sig), 0] += sig[:, 0]; buf[i:i + len(sig), 1] += rr[:, 1]
    def hit(at, big=1.0):
        add(dry, ca.kick(.5, 1.0 + .3 * big), at, .5 + .3 * big); add(fx, ca.impact(1.2), at, .15 + .2 * big, 240)
        if big >= 1: add(dry, ca.sub_boom(2.0, 46), at, .6)
    b = 60 / 126
    for j in range(int((DUR - .5) / b)):
        at = .3 + j * b
        add(dry, ca.kick(.25, .8), at, .32 if j % 2 == 0 else .18); add(dry, ca.tick(.04), at + b / 2, .12)
        if j % 4 == 2: add(dry, ca.clap(.3), at, .12, 120)
    prog = [(45, 52, 57, 60), (41, 48, 53, 57), (43, 50, 55, 59), (40, 47, 52, 55)]
    for i, at in enumerate(np.arange(.3, DUR - 1, 4.0)): add(fx, ca.pad(prog[i % 4], 4.4), at, .24, 400)
    whoosh, cash, ping, coins = sfx('whoosh'), sfx('cash'), sfx('ping'), sfx('coin')
    for at in (TT[1], TT[3], TT[5], TT[7], TT[9], TT[10]):
        add(fx, ca.reverse_swell(.3), at - .42, .18, 300); add(fx, whoosh, at - .25, .35)
    add(fx, ca.sub_boom(3.0, 38), 0, .4); add(fx, whoosh, CEND, .5)
    for n in range(1, 48): add(dry, ca.tick(.03), n_at(n), .35)   # every new trade clicks
    for j in range(12): add(dry, ca.tick(.03), lerp(G(2, .05), G(2, .85), j / 12), .45)
    add(fx, coins, G(4, .1), .3); add(fx, sfx('glitch'), G(4, .5), .25); add(fx, ping, T(4, .35), .4)
    for j in range(5): add(dry, sfx('heart'), G(6, .45) - .4 + j * .5, .8)
    add(fx, ca.riser(1.2, 250, 4500), KEY - 1.2, .22, 200)
    add(fx, sfx('alarm'), KEY, .45); add(fx, sfx('glitch'), KEY, .5)
    add(fx, ping, G(8, .35), .45); add(fx, sfx('shimmer'), T(8, 0) + .05, .45); add(fx, sfx('shimmer'), TT[10] + .13, .4)
    for at, s in HITS: hit(at, s)
    bed = ca.reverb(dry + fx, 2.0, .22); bed /= np.max(np.abs(bed)) + 1e-9
    tt_ = np.arange(N) / SR; gate = 1 - .92 * ((tt_ > KEY - .45) & (tt_ < KEY - .05))   # a beat of silence before the wipeout
    bed *= gate[:, None]
    v = np.interp(np.arange(N) / SR, np.arange(len(vo)) / vsr, vo, right=0)
    e = np.convolve(np.abs(v), np.ones(int(.2 * SR)) / int(.2 * SR), 'same')
    duck = 1 - .55 * np.clip(e / (e.max() * .25), 0, 1)
    voice = np.stack([v, v], 1) / (np.max(np.abs(v)) + 1e-9)
    m = np.tanh((bed * duck[:, None] * .45 + voice * 1.0) * 1.2) * .9
    with wave.open('ollie_audio.wav', 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((m * 32767).astype(np.int16).tobytes())

KEY = G(6, .85); CEND = A(0, .5); TL = build_tl(); HITS = hit_list(); MAXT = KEY
SHADOW = Image.new('RGBA', (W, H), (0, 0, 0, 0))
for x0, x1 in PX: SHADOW.paste((40, 30, 20, 60), (x0 + 10, PY0 + 18, x1 + 10, PY1 + 18))
SHADOW = SHADOW.filter(ImageFilter.GaussianBlur(16))
for x0, x1 in PX: SHADOW.paste((251, 250, 246, 255), (x0, PY0, x1, PY1))   # lifted card under each panel
_r = np.hypot((xx - W / 2) / (W / 2), (yy - H / 2) / (H / 2))
RED_VIG = Image.fromarray(np.dstack([np.full((H, W), c, np.uint8) for c in RED] + [np.clip((_r - .55) * 260, 0, 120).astype(np.uint8)]), 'RGBA')
MKEYS = ([(0, .4), (G(2, 0), .55), (G(4, .6), .65), (G(6, 0), .8), (KEY - .1, .9), (KEY, 1.0)],
         [(0, .15), (A(0, .6), .2), (T(2, .3), .08), (T(4, .3), .05), (T(6, .3), .08)])

if __name__ == '__main__':
    if len(sys.argv) > 7:
        for tt in sys.argv[7].split(','): frame(float(tt)).save(f'snap_{tt}.png')
        sys.exit()
    audio()
    p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                          '-i', 'ollie_audio.wav', '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '17',
                          '-preset', 'medium', '-c:a', 'aac', '-b:a', '192k', '-ar', '44100', '-shortest', '-movflags', '+faststart', OUT], stdin=subprocess.PIPE)
    for i in range(int(DUR * FPS)): p.stdin.write(frame(i / FPS).tobytes())
    p.stdin.close(); p.wait()
