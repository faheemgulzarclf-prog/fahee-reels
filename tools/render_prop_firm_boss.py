import subprocess, sys, wave, json, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
# "Gary meets the Prop Firm Boss" sketch reel (25 Oct): office scene, the Boss checks 3 rules on a review board (daily loss, lot size,
# news), Gary fails every rule -> FAILED stamp; Tariq walks in, every rule green -> PAID. Premium motion template (render_gambler_vs_trader_5_pro.py).
# usage: python3 render_prop_firm_boss.py vo.wav times.json vo_lines.txt fontdir/ out.mp4 posts_dir [snap t1,t2]
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
RED = (214, 58, 66); GREY = (150, 150, 150)
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
    g = [(0, 'hips', 'grin'), (A(0, .55), 'point', 'grin'), (TT[1] - .12, 'stand', 'grin'), (G(2, 0), 'thumb', 'grin'),
         (TT[3] - .12, 'stand', 'frown'), (G(4, 0), 'think', 'scared'), (TT[5] - .12, 'stand', 'frown'), (KEY - .1, 'head', 'scared'),
         (TT[7] - .12, 'stand', 'frown'), (G(8, 0), 'head', 'cry'), (TT[9] - .12, 'head', 'cry'), (TT[10] - .12, 'shrug', 'grin')]
    tr = [(0, 'stand', 'calm'), (A(0, .55), 'think', 'calm'), (TT[1] - .12, 'stand', 'calm'), (T(2, 0), 'point', 'calm'), (T(2, .6), 'hips', 'smile'),
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
    col = RED if kind == 'g' else GOLD
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
        pen.hatch(cx - 30, fy - 318, cx + 30, fy - 176, col=(150, 30, 36), gap=13, prog=pg(.45, .7), a=.6)
        pen.text(cx, fy - 255, '$', 46, WHITE, a=pg(.6, .8))
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
    if kind == 'g':   # red cap + messy hair
        pen.stroke([(hx - 44, hy - 4), (hx - 54, hy - 22), (hx - 40, hy - 18), (hx - 48, hy - 36), (hx - 34, hy - 30)], w=4, prog=pg(.2, .35))
        cap = [(hx + r * math.cos(q), hy - 6 + r * 1.02 * math.sin(q)) for q in np.radians(np.linspace(-178, -2, 20))]
        if prog > .3: pen.fill(cap, RED, 1)
        pen.stroke(cap + [cap[0]], w=5, prog=pg(.25, .4))
        pen.stroke([(hx + 30, hy - 10), (hx + 78, hy - 4)], w=7, prog=pg(.35, .45))
        for dx, dy in ((-10, 30), (-2, 34), (8, 31), (14, 27), (-16, 25)): pen.circ(hx + dx, hy + dy, 1.4, w=2.5, prog=pg(.85, 1), amp=.2)
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

def countv(pen, x, y, a, b, p, col, size=30):
    v = lerp(a, b, ease(p)); pen.text(x, y, ('-' if v < -.5 else '') + f'${abs(v):,.0f}', size, col)


def keyed(keys, t):
    if t <= keys[0][0]: return keys[0][1]
    for (a, va), (b, vb) in zip(keys, keys[1:]):
        if t < b: return lerp(va, vb, ease((t - a) / max(.01, b - a)))
    return keys[-1][1]

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

def logo(img):
    d = ImageDraw.Draw(img); d.rounded_rectangle([120, 262, 120 + LOGO.width + 28, 262 + 58], 29, fill=INK)
    img.alpha_composite(LOGO, (134, 271))



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


def S(k, phrase): return A(k, TXT[k].index(phrase) / len(TXT[k]))

def build_tl():
    nx = S(7, 'Next')
    g = [(0, 'walk', 'grin'), (CEND + 1.0, 'hips', 'grin'), (A(2, .3), 'shrug', 'frown'), (TT[3] - .12, 'stand', 'frown'),
         (A(4, .4), 'head', 'scared'), (TT[5] - .12, 'stand', 'scared'), (A(6, .5), 'head', 'scared'), (TT[7] - .12, 'head', 'cry'), (nx, 'walk', 'cry')]
    tr = [(0, 'walk', 'calm'), (TT[8] + 1.0, 'stand', 'calm'), (S(8, 'Payout'), 'thumb', 'smile'), (TT[9] - .12, 'stand', 'calm'), (TT[10] - .12, 'thumb', 'smile')]
    return g, tr

# ---------------- office ----------------
RX0, RX1, RY0, RY1 = 110, 970, 440, 1290
BX0, BX1, BY0, BY1 = 140, 940, 466, 830        # review board
BOSSX = 320; CANDX = 770; FYC = 1268

def board(pen, t, k):
    pen.fill([(BX0, BY0), (BX1, BY0), (BX1, BY1), (BX0, BY1)], WHITE, 1); pen.rect(BX0, BY0, BX1, BY1, w=5)
    tar = t > TT[8] - .1
    if k >= 10:   # the verdicts side by side
        for j, (nm, word, c) in enumerate((('GARY', 'FAILED', RED), ('TARIQ', 'PAID', GOLD_D))):
            x = 340 + 400 * j; at = TT[10] - .12 + j * .3
            pen.text(x, BY0 + 90, nm, 40, INK, a=clamp((t - at) / .2))
            pen.stamp(x, BY0 + 220, word, 76, c, at + .1, t, rot=-8 if j == 0 else 6)
        pen.stroke([(540, BY0 + 40), (540, BY1 - 40)], col=(210, 210, 210), w=3, amp=.3)
        return
    pen.d.text(pen.P(BX0 + 30, BY0 + 40), 'CHALLENGE REVIEW', font=F(900, 26 * SS), fill=GREY + (255,), anchor='lm')
    nm, c = ('TARIQ', GOLD) if tar else ('GARY', RED)
    q = back((t - (TT[8] - .1 if tar else CEND + .3)) / .3)
    if q > .05:
        f = F(900, 30 * SS); tw = pen.d.textlength(nm, font=f) / SS
        pen.fill([(BX1 - 40 - tw - 30, BY0 + 18), (BX1 - 40, BY0 + 18), (BX1 - 40, BY0 + 62), (BX1 - 40 - tw - 30, BY0 + 62)], c, 1)
        pen.text(BX1 - 55 - tw / 2, BY0 + 40, nm, 30 * q, WHITE if not tar else INK)
    for x, h in ((BX0 + 30, 'RULE'), (560, 'RESULT'), (730, 'LIMIT')):
        pen.d.text(pen.P(x, BY0 + 100), h, font=F(800, 18 * SS), fill=(170, 170, 170, 255), anchor='lm' if h == 'RULE' else 'mm')
    pen.stroke([(BX0 + 24, BY0 + 118), (BX1 - 24, BY0 + 118)], col=(215, 215, 215), w=2, amp=.3)
    for j, (rule, gv, tv, lim) in enumerate(RULES):
        y = BY0 + 168 + j * 72
        if tar:
            r_at, v_at, m_at = TT[8] - .1, S(8, 'Every') + j * .22, S(8, 'Every') + j * .22 + .08
        else:
            r_at, v_at, m_at = TT[2 * j + 1] - .12, G_VAL[j], G_X[j]
        a = clamp((t - r_at) / .2)
        if a <= 0: continue
        pen.d.text(pen.P(BX0 + 30 + 30 * (1 - ease((t - r_at) / .3)), y), rule, font=F(900, 26 * SS), fill=INK + (int(255 * a),), anchor='lm')
        pen.text(730, y, lim, 22, GREY, a=a)
        va = clamp((t - v_at) / .15)
        if va > 0: pen.text(560, y, tv if tar else gv, 30, (GOLD_D if tar else RED), a=va, sc=1 + .4 * (1 - back((t - v_at) / .3)))
        mp = back((t - m_at) / .25); mx = 870
        if mp > .05:
            if tar: pen.stroke([(mx - 18 * mp, y), (mx - 5 * mp, y + 14 * mp), (mx + 20 * mp, y - 16 * mp)], col=GOLD_D, w=8)
            else:
                pen.stroke([(mx - 18 * mp, y - 18 * mp), (mx + 18 * mp, y + 18 * mp)], col=RED, w=8); pen.stroke([(mx + 18 * mp, y - 18 * mp), (mx - 18 * mp, y + 18 * mp)], col=RED, w=8)
    if not tar: pen.stamp(540, BY0 + 260, 'FAILED', 120, RED, FAILT, t, rot=-8)
    else:
        pen.stamp(540, BY0 + 250, 'PAID', 120, GOLD_D, PAIDT, t, rot=6)
        if t > PAIDT: sparkles(pen, 540, BY0 + 250, t - PAIDT - .1, big=1.8)

def boss(pen, t):
    cx = BOSSX; smile = t > PAIDT
    # torso + arms behind the desk
    tor = [(cx - 92, 1080), (cx - 72, 960), (cx + 72, 960), (cx + 92, 1080)]
    pen.fill(tor, (66, 66, 72), 1); pen.stroke(tor + [tor[0]], w=6)
    pen.fill([(cx - 26, 960), (cx + 26, 960), (cx, 1010)], WHITE, 1); pen.stroke([(cx - 26, 960), (cx, 1010), (cx + 26, 960)], w=4)
    tie = [(cx, 972), (cx - 9, 990), (cx, 1050), (cx + 9, 990)]; pen.fill(tie, RED, 1); pen.stroke(tie + [tie[0]], w=3)
    pen.stroke([(cx - 72, 972), (cx - 120, 1030), (cx - 70, 1062)], w=7)
    pen.circ(cx - 70, 1062, 11, w=4)
    # stamp arm: raises before each slam, comes down on it
    hy = 1052
    for at in SLAMS:
        if at - .45 < t < at: hy = lerp(1052, 900, ease((t - at + .45) / .3))
        if at <= t < at + .08: hy = lerp(900, 1052, (t - at) / .08)
    hx = cx + 120; sh = (cx + 72, 972); el = (cx + 128, (sh[1] + hy) / 2 + 10)
    pen.stroke([sh, el, (hx, hy)], w=7)
    pen.fill([(hx - 10, hy - 52), (hx + 10, hy - 52), (hx + 10, hy - 14), (hx - 10, hy - 14)], (120, 84, 60), 1); pen.rect(hx - 10, hy - 52, hx + 10, hy - 14, w=3)
    pen.fill([(hx - 30, hy - 14), (hx + 30, hy - 14), (hx + 30, hy + 4), (hx - 30, hy + 4)], INK, 1)
    pen.circ(hx, hy - 34, 12, w=4)
    # head: bald, side hair, square glasses, moustache
    hx0, hy0, r = cx, 880, 60
    pen.fill([(hx0 + r * math.cos(q), hy0 + r * 1.05 * math.sin(q)) for q in np.linspace(0, 6.28, 30)], (252, 250, 245), 1)
    pen.ell(hx0, hy0, r, r * 1.05, w=6)
    for sx in (-1, 1):
        pen.stroke([(hx0 + sx * 58, hy0 - 20), (hx0 + sx * 66, hy0 - 4), (hx0 + sx * 58, hy0 + 12)], w=4)
        pen.rect(hx0 + sx * 22 - 16, hy0 - 16, hx0 + sx * 22 + 16, hy0 + 6, w=3.5)
        pen.circ(hx0 + sx * 22, hy0 - 5, 3, w=6, amp=.2)
        pen.stroke([(hx0 + sx * 36, hy0 - 30 + (0 if smile else -6)), (hx0 + sx * 8, hy0 - 24 + (0 if smile else 6))], w=5)
    pen.stroke([(hx0 - 6, hy0 - 5), (hx0 + 6, hy0 - 5)], w=3)
    mo = [(hx0 - 30, hy0 + 30), (hx0 - 12, hy0 + 18), (hx0, hy0 + 22), (hx0 + 12, hy0 + 18), (hx0 + 30, hy0 + 30), (hx0, hy0 + 30)]
    pen.fill(mo, INK, 1)
    if smile: pen.arc(hx0, hy0 + 26, 16, 30, 150, w=4)
    else: pen.stroke([(hx0 - 12, hy0 + 42), (hx0 + 12, hy0 + 42)], w=4)
    # desk in front
    dk = [(130, 1070), (530, 1070), (545, 1272), (118, 1272)]
    pen.fill(dk, (222, 196, 160), 1); pen.stroke(dk + [dk[0]], w=6); pen.stroke([(130, 1086), (530, 1086)], w=3, amp=.4)
    pen.fill([(240, 1150), (420, 1150), (420, 1200), (240, 1200)], INK, 1); pen.text(330, 1175, 'THE BOSS', 24, GOLD)
    bk = [(150, 1048), (230, 1040), (236, 1068), (156, 1072)]; pen.fill(bk, RED, 1); pen.stroke(bk + [bk[0]], w=4)
    pen.text(193, 1057, 'RULES', 14, WHITE, rot=4)
    pen.fill([(cx + 80, 1062), (cx + 170, 1058), (cx + 172, 1072), (cx + 82, 1074)], WHITE, 1); pen.stroke([(cx + 80, 1062), (cx + 170, 1058), (cx + 172, 1072), (cx + 82, 1074), (cx + 80, 1062)], w=3)

def office(t, k):
    pen = Pen(W, RY1 - RY0 + 120, 0, RY0 - 60)
    if k != 9:
        board(pen, t, k); boss(pen, t)
        gx = keyed([(0, 1180), (CEND - .2, 1180), (CEND + 1.0, CANDX), (NEXTT, CANDX), (NEXTT + 1.3, 1260)], t)
        if t < NEXTT + 1.3: person(pen, 'g', gx, FYC, t)
        if t > TT[8] - .3: person(pen, 't', keyed([(TT[8] - .3, 1240), (TT[8] + 1.0, CANDX)], t), FYC, t)
    return pen.img.reduce(SS)

# ---------------- overlays ----------------
HEADS = {1: [('RULE 1: ', GOLD_D), ('DAILY LOSS', INK)], 2: [('RULE 1: ', GOLD_D), ('DAILY LOSS', INK)], 3: [('RULE 2: ', GOLD_D), ('LOT SIZE', INK)],
         4: [('RULE 2: ', GOLD_D), ('LOT SIZE', INK)], 5: [('RULE 3: ', GOLD_D), ('NO NEWS TRADING', INK)], 6: [('RULE 3: ', GOLD_D), ('NO NEWS TRADING', INK)],
         7: [('CHALLENGE ', RED), ('FAILED', RED)], 8: [("TARIQ'S ", GOLD_D), ('REVIEW', INK)], 9: [],
         10: [('WHO WOULD THE BOSS ', INK), ('PAY?', GOLD_D)]}

def headline(img, t, k):
    if k == 0:
        if t < CEND: return
        parts = [('GARY ', RED), ('MEETS ', INK), ('THE BOSS', INK)]; a0 = CEND
    else:
        parts = HEADS[k]; a0 = TT[k] - .12
        if k in (2, 4, 6): a0 = TT[k - 1] - .12
    if not parts: return
    d = ImageDraw.Draw(img); y = 388; size = 60
    while sum(d.textlength(p, font=F(900, size)) for p, c in parts) > 820: size -= 2
    f = F(900, size); words = [(w + ' ', c) for p, c in parts for w in p.split()]
    tw = d.textlength(''.join(w for w, c in words).rstrip(), font=f); x = W / 2 - tw / 2
    lay = Image.new('RGBA', (W, 120), (0, 0, 0, 0)); dl = ImageDraw.Draw(lay)
    for i, (w, c) in enumerate(words):
        q = ease((t - a0 - i * .06) / .28)
        if q > 0: dl.text((x, 60 + 34 * (1 - q)), w, font=f, fill=c + (int(255 * q),), anchor='lm')
        x += d.textlength(w, font=f)
    img.alpha_composite(lay, (0, y - 60))

def quote(img, t):
    k = scene(t)
    if k != 9: return 0
    a0 = TT[9] - .12; p = ease((t - a0) / .3)
    pen = Pen(W, 900, 0, 420)
    pen.fill([(110, 520), (970, 520), (970, 1240), (110, 1240)], WHITE, .97 * p)
    pen.rect(110, 520, 970, 1240, w=6, prog=ease((t - a0) / .5))
    lines = [('THE BOSS', INK, 100), ("DOESN'T CHECK", INK, 74), ('YOUR ENTRY.', INK, 84), ('HE CHECKS', GOLD_D, 90), ('YOUR RULES.', GOLD_D, 96)]
    ys = [630, 745, 840, 1000, 1110]; rel = [0, .1, .22, .58, .75]
    for (s, c, z), y, r in zip(lines, ys, rel):
        at = A(9, r); pen.text(540, y, s, z, c, sc=back((t - at) / .3), a=clamp((t - at) / .1))
    pen.stroke([(330, 1175), (750, 1169)], col=GOLD, w=10, prog=ease((t - A(9, .85)) / .4))
    img.alpha_composite(pen.img.reduce(SS), (0, 420)); return p

def endcard(img, t):
    a0 = SEG[10][1] - .25
    if t < a0: return False
    q = ease((t - a0) / .35); y0 = int(1300 + 200 * (1 - q))
    band = Image.new('RGBA', (840, 170), INK + (255,)); d = ImageDraw.Draw(band)
    parts = [('FAILED', RED), ('  or  ', WHITE), ('PAID', GOLD), ('?', WHITE)]; f = F(900, 76)
    tw = sum(d.textlength(p, font=f) for p, c in parts); x = 420 - tw / 2
    for p, c in parts: d.text((x, 70), p, font=f, fill=c, anchor='lm'); x += d.textlength(p, font=f)
    d.text((420, 140), 'SEND THIS TO YOUR PROP FIRM FRIEND', font=F(800, 22), fill=(170, 170, 174), anchor='mm')
    m = Image.new('L', band.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, 839, 169], 26, fill=255); band.putalpha(m)
    img.alpha_composite(band, (120, y0)); return True

def coldopen(img, t):   # black open: the review is coming
    if t > CEND + .45: return
    lay = Image.new('RGBA', (W, H), INK + (255,)); d = ImageDraw.Draw(lay, 'RGBA')
    d.text((540, 587), 'YOUR CHALLENGE IS UNDER REVIEW', font=F(800, 30), fill=(170, 170, 174), anchor='mm')
    pul = 1 + .3 * (1 - back(t / .35))
    d.text((540, 790), '3 RULES', font=F(900, int(200 * pul)), fill=WHITE, anchor='mm')
    lw = 520 * ease((t - .2) / .6); d.rectangle([540 - lw / 2, 920, 540 + lw / 2, 928], fill=GOLD)
    pk = A(0, .3)
    if t < pk: words = [('EVERY', WHITE), ('PROP', WHITE), ('FIRM', WHITE)]; w0 = .05
    else: words = [('HAS', WHITE), ('A', WHITE), ('BOSS.', RED)]; w0 = pk
    f2 = F(900, 66); tw = sum(d.textlength(w + ' ', font=f2) for w, c in words) - d.textlength(' ', font=f2); x = 540 - tw / 2
    for i, (w, c) in enumerate(words):
        q = ease((t - w0 - i * .09) / .25)
        if q > 0: d.text((x, 1060 + 30 * (1 - q)), w, font=f2, fill=c + (int(255 * q),), anchor='lm')
        x += d.textlength(w + ' ', font=f2)
    sp = ease((t - CEND) / .45)
    if sp <= 0: img.alpha_composite(lay); return
    off = int(sp * H / 2 + 4)
    if off >= H // 2: return
    img.alpha_composite(lay.crop((0, off, W, H // 2)), (0, 0))
    img.alpha_composite(lay.crop((0, H // 2, W, H - off)), (0, H // 2 + off))

def hit_list():
    return [(.05, 1.0), (A(0, .3), .8), (CEND, 1.0)] + [(TT[k] - .12, .9) for k in (1, 3, 5)] + [(x, 1.0) for x in G_X] + \
        [(FAILT, 1.2), (TT[8] - .12, 1.0), (PAIDT, 1.0), (TT[9] - .12, 1.0), (A(9, .58), .9), (TT[10] - .12, 1.0), (TT[10] + .2, .8)]

def frame(t):
    global BOIL
    BOIL = int(t * 8); k = scene(t)
    img = PAPER_IMG.copy(); lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    if k != 9: lay.alpha_composite(SHADOW)
    im = office(t, k)
    gl = t - FAILT
    if 0 <= gl < .25:
        r_, g_, b_, a_ = im.split(); o = int(9 * (1 - gl / .25)) + 2
        im = Image.merge('RGBA', (r_.transform(im.size, Image.AFFINE, (1, 0, -o, 0, 1, 0)), g_, b_.transform(im.size, Image.AFFINE, (1, 0, o, 0, 1, 0)), a_))
    sh = 0
    for at, s in HITS:
        if 0 < t - at < .3 and s >= 1: sh = int(7 * s * math.sin((t - at) * 70) * (1 - (t - at) / .3))
    lay.alpha_composite(im, (sh, RY0 - 60))
    r = t - (TT[k] - .12); z = 1.01 + .006 * math.sin(t * .7) + .04 * max(0, 1 - r / .22)
    fx, fy = 540, 865
    if k in (2, 4, 6): fx, fy = 620, 700; z += .05 * ease((t - TT[k]) / 1.2)
    for at in (FAILT, PAIDT):
        q = ease((t - at + .1) / .25) * (1 - ease((t - at - 1.2) / .4))
        if q > 0: z += .05 * q; fy = lerp(fy, 680, q)
    zw, zh = int(W * z), int(H * z); big = lay.resize((zw, zh), Image.BILINEAR)
    cx = int(fx * z - fx); cy = int(fy * z - fy); lay = big.crop((cx, cy, cx + W, cy + H))
    img.alpha_composite(lay)
    if 0 <= t - FAILT < .6: img.alpha_composite(_vig(RED_VIG, 1 - (t - FAILT) / .6))
    quote(img, t); headline(img, t, k)
    if not endcard(img, t): captions(img, t, k)
    coldopen(img, t); logo(img)
    return img.convert('RGB')

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
    b = 60 / 118
    for j in range(int((DUR - .5) / b)):
        at = .3 + j * b
        add(dry, ca.kick(.25, .8), at, .3 if j % 2 == 0 else .16); add(dry, ca.tick(.04), at + b / 2, .1)
        if j % 4 == 2: add(dry, ca.clap(.3), at, .12, 120)
    prog = [(45, 52, 57, 60), (41, 48, 53, 57), (43, 50, 55, 59), (40, 47, 52, 55)]
    for i, at in enumerate(np.arange(.3, DUR - 1, 4.0)): add(fx, ca.pad(prog[i % 4], 4.4), at, .24, 400)
    whoosh, ping, cash = sfx('whoosh'), sfx('ping'), sfx('cash')
    add(fx, ca.sub_boom(3.0, 38), 0, .4); add(fx, whoosh, CEND, .5)
    for j in range(5): add(dry, ca.tick(.05), CEND + j * .22, .5)   # footsteps in
    for j in range(5): add(dry, ca.tick(.05), NEXTT + j * .22, .4)  # and out
    for j in range(5): add(dry, ca.tick(.05), TT[8] - .2 + j * .22, .4)
    for x in G_VAL: add(fx, ping, x, .3)
    for x in G_X: add(fx, sfx('alarm'), x, .3)
    add(fx, ca.riser(1.4, 250, 4500), FAILT - 1.4, .25, 200); add(fx, sfx('glitch'), FAILT, .5)
    for j in range(3): add(fx, ping, S(8, 'Every') + j * .22 + .08, .35)
    add(fx, cash, PAIDT, .5); add(fx, sfx('shimmer'), PAIDT + .1, .45); add(fx, sfx('shimmer'), TT[10] + .3, .35)
    for at, s in HITS: hit(at, s)
    bed = ca.reverb(dry + fx, 2.0, .22); bed /= np.max(np.abs(bed)) + 1e-9
    tt_ = np.arange(N) / SR; gate = 1 - .92 * ((tt_ > FAILT - .45) & (tt_ < FAILT - .05))
    bed *= gate[:, None]
    v = np.interp(np.arange(N) / SR, np.arange(len(vo)) / vsr, vo, right=0)
    e = np.convolve(np.abs(v), np.ones(int(.2 * SR)) / int(.2 * SR), 'same')
    duck = 1 - .55 * np.clip(e / (e.max() * .25), 0, 1)
    voice = np.stack([v, v], 1) / (np.max(np.abs(v)) + 1e-9)
    m = np.tanh((bed * duck[:, None] * .45 + voice * 1.0) * 1.2) * .9
    with wave.open('boss_audio.wav', 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((m * 32767).astype(np.int16).tobytes())

RULES = [('DAILY LOSS', '-6%', '-0.8%', 'MAX 5%'), ('LOT SIZE', '10 LOTS', '0.5 LOTS', 'MAX 3'), ('NEWS TRADES', '2', '0', 'ALLOWED 0')]
CEND = S(0, 'Today')
G_VAL = [A(2, .25), A(4, .3), A(6, .2)]
G_X = [S(2, 'The limit') + .5, A(4, .75), S(6, 'Twice')]
FAILT = TT[7] - .05; NEXTT = S(7, 'Next'); PAIDT = S(8, 'Payout')
SLAMS = G_X + [FAILT, PAIDT]
TL = build_tl(); HITS = hit_list()
SHADOW = Image.new('RGBA', (W, H), (0, 0, 0, 0))
SHADOW.paste((40, 30, 20, 60), (RX0 + 10, RY0 + 18, RX1 + 10, RY1 + 18)); SHADOW = SHADOW.filter(ImageFilter.GaussianBlur(16))
SHADOW.paste((251, 250, 246, 255), (RX0, RY0, RX1, RY1))
_r = np.hypot((xx - W / 2) / (W / 2), (yy - H / 2) / (H / 2))
RED_VIG = Image.fromarray(np.dstack([np.full((H, W), c, np.uint8) for c in RED] + [np.clip((_r - .55) * 260, 0, 120).astype(np.uint8)]), 'RGBA')

if __name__ == '__main__':
    if len(sys.argv) > 7:
        for tt in sys.argv[7].split(','): frame(float(tt)).save(f'snap_{tt}.png')
        sys.exit()
    audio()
    p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                          '-i', 'boss_audio.wav', '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '17',
                          '-preset', 'medium', '-c:a', 'aac', '-b:a', '192k', '-ar', '44100', '-shortest', '-movflags', '+faststart', OUT], stdin=subprocess.PIPE)
    for i in range(int(DUR * FPS)): p.stdin.write(frame(i / FPS).tobytes())
    p.stdin.close(); p.wait()
