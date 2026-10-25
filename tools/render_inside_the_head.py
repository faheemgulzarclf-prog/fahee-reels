import subprocess, sys, wave, json, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
# "Inside Gary's head" sketch reel (25 Oct): a control room inside the head where emotions drive the trade.
# Gary: FOMO hits BUY, Greed pulls the lot lever, Fear drags the stop, account blown while Discipline sleeps locked up.
# Tariq: Discipline drives, Greed is locked up, FOMO gets blocked, Fear calms down. Premium motion template (render_gambler_vs_trader_5_pro.py).
# usage: python3 render_inside_the_head.py vo.wav times.json vo_lines.txt fontdir/ out.mp4 posts_dir [snap t1,t2]
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

def V(a, l): r = math.radians(a); return l * math.sin(r), l * math.cos(r)

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


# ---------------- emotion characters ----------------
ECOL = {'fomo': RED, 'greed': GOLD, 'fear': (128, 158, 196), 'disc': INK}
ENAME = {'fomo': 'FOMO', 'greed': 'GREED', 'fear': 'FEAR', 'disc': 'DISCIPLINE'}
EPOSE = {'idle': (-35, -15, 35, 15), 'up': (-155, -175, 155, 175), 'press': (-25, -5, 25, 5), 'pull': (-35, -15, 75, 150),
         'reach': (-60, -100, 60, 100), 'block': (-95, -95, 35, 15), 'hold': (-35, -15, 50, 150), 'head': (-130, 115, 130, -115)}
ETOP = {'fomo': -205, 'greed': -192, 'fear': -214, 'disc': -198}

def S(k, phrase): return A(k, TXT[k].index(phrase) / len(TXT[k]))

def emo(pen, kind, x, fy, t, pose='idle', mood='calm', s=1.3, shake=0.0, tag=True, a=1.0, pp=None):
    x += shake * math.sin(t * 55) * s; fy += 3 * s * math.sin(t * 3.1 + len(kind))
    if kind == 'fomo': x += 1.5 * math.sin(t * 31)
    col = ECOL[kind]
    def P(dx, dy): return (x + dx * s, fy + dy * s)
    for sx in (-1, 1): pen.stroke([P(sx * 16, -40), P(sx * 20, 0), P(sx * 34, 0)], w=5 * s, a=a)
    if kind == 'fomo':
        cy, rx, ry = -112, 56, 70; pts = []
        for q in np.linspace(0, 6.283, 60):
            r = 1 + (.34 * max(0, math.cos(6 * (q + math.pi / 2))) if math.sin(q) < -.45 else 0)
            pts.append(P(rx * r * math.cos(q), cy + ry * r * math.sin(q)))
    elif kind == 'greed':
        cy, rx, ry = -100, 70, 62; pts = [P(rx * math.cos(q), cy + ry * math.sin(q)) for q in np.linspace(0, 6.283, 40)]
    elif kind == 'fear':
        cy, rx, ry = -126, 42, 86; pts = [P(rx * math.cos(q) * (1 + .06 * math.sin(5 * q + t * 9)), cy + ry * math.sin(q)) for q in np.linspace(0, 6.283, 40)]
    else:
        cy, rx, ry = -118, 50, 78; pts = [P(-50, -196), P(50, -196), P(50, -40), P(-50, -40)]
    pen.fill(pts, col, a); pen.stroke(pts + [pts[0]], w=5 * s, a=a)
    if kind == 'greed':
        cr = [P(-30, -150), P(-30, -178), P(-15, -162), P(0, -184), P(15, -162), P(30, -178), P(30, -150)]
        pen.fill(cr, GOLD_D, a); pen.stroke(cr + [cr[0]], w=4 * s, a=a)
    if kind == 'disc':
        tie = [P(0, -150), P(-9, -130), P(0, -84), P(9, -130)]; pen.fill(tie, GOLD, a)
    # arms
    la, lf, ra, rf = (pp or EPOSE[pose])
    if kind == 'greed' and pose == 'up' and mood == 'angry':   # banging on the glass
        b = 25 * math.sin(t * 14); la, lf, ra, rf = la + b, lf + b, ra - b, rf - b
    hands = []
    for sx, a1, a2 in ((-1, la, lf), (1, ra, rf)):
        s0 = P(sx * (rx - 6), cy + 12); d1 = V(a1, 46 * s); e = (s0[0] + d1[0], s0[1] + d1[1]); d2 = V(a2, 42 * s); hd = (e[0] + d2[0], e[1] + d2[1])
        pen.stroke([s0, e, hd], w=5 * s, a=a); hands.append(hd)
        pen.fill([(hd[0] + 9 * s * math.cos(q), hd[1] + 9 * s * math.sin(q)) for q in np.linspace(0, 6.28, 12)], WHITE, a); pen.circ(*hd, 9 * s, w=3.5 * s, a=a)
    if pose == 'hold':   # clipboard with the plan
        hx, hy = hands[1]; cb = [(hx - 30 * s, hy - 46 * s), (hx + 22 * s, hy - 46 * s), (hx + 22 * s, hy + 18 * s), (hx - 30 * s, hy + 18 * s)]
        pen.fill(cb, WHITE, a); pen.stroke(cb + [cb[0]], w=3.5 * s, a=a)
        for j in range(3): pen.stroke([(hx - 22 * s, hy - (32 - 14 * j) * s), (hx + 12 * s, hy - (32 - 14 * j) * s)], w=2.5 * s, amp=.3, a=a)
    # face
    ey = {'fomo': -135, 'greed': -112, 'fear': -150, 'disc': -160}[kind]; er = 15 if kind != 'fomo' else 17
    for sx in (-1, 1):
        ex, eyy = P(sx * 20, ey)
        if mood == 'sleep':
            pen.arc(ex, eyy + 2 * s, 9 * s, 20, 160, col=WHITE if kind == 'disc' else INK, w=3.5 * s, a=a); continue
        pen.fill([(ex + er * s * math.cos(q), eyy + er * s * math.sin(q)) for q in np.linspace(0, 6.28, 16)], WHITE, a)
        pen.circ(ex, eyy, er * s, w=3 * s, a=a)
        if kind == 'greed': pen.text(ex, eyy + 1 * s, '$', 20 * s, GOLD_D, a=a)
        else:
            look = {'fear': -5, 'fomo': 0}.get(kind, 0)
            pen.circ(ex + look * s, eyy + 1 * s, (3 if kind == 'fomo' else 5) * s, w=(4 if kind == 'fomo' else 6) * s, a=a, amp=.2)
        if kind == 'disc': pen.circ(ex, eyy, 20 * s, col=WHITE, w=3 * s, a=a, amp=.4)
    if kind == 'disc' and mood != 'sleep': pen.stroke([P(-2, ey), P(2, ey)], col=WHITE, w=3 * s, a=a)
    lc = WHITE if kind == 'disc' else INK
    if mood in ('scared', 'angry', 'frown') or kind == 'fear':
        for sx in (-1, 1):
            up = mood in ('scared',) or kind == 'fear'
            pen.stroke([P(sx * 32, ey - 20 - (0 if up else -6)), P(sx * 10, ey - 24 - (8 if up else -8))], col=lc, w=4 * s, a=a)
    my = ey + 40
    if mood == 'grin':
        mp = [P(-20, my - 4), P(20, my - 4)] + [P(20 * math.cos(q), my - 4 + 15 * math.sin(q)) for q in np.radians(np.linspace(0, 180, 12))]
        pen.fill(mp, WHITE, a); pen.stroke(mp + [mp[0]], w=3.5 * s, a=a)
    elif mood in ('smile', 'calm'): pen.arc(*P(0, my - 16), (16 if mood == 'smile' else 12) * s, 30, 150, col=lc, w=4 * s, a=a)
    elif mood == 'scared': pen.ell(*P(0, my), 8 * s, 11 * s, col=lc, w=4 * s, a=a)
    elif mood in ('frown',): pen.arc(*P(0, my + 12), 13 * s, 210, 330, col=lc, w=4 * s, a=a)
    elif mood == 'angry': pen.stroke([P(-14, my + 2), P(-5, my - 3), P(5, my + 2), P(14, my - 3)], col=lc, w=4 * s, a=a)
    elif mood == 'sleep':
        pen.stroke([P(-8, my), P(8, my)], col=lc, w=3.5 * s, a=a)
        for j in range(2):
            ph = (t * .6 + j * .5) % 1; zx, zy = P(40 + 30 * ph, -170 - 60 * ph)
            pen.text(zx, zy, 'z', (22 + 10 * j) * s, GREY, a=a * (1 - ph))
    if (mood == 'scared' or (kind == 'fear' and shake > 0)):
        for i, dx in enumerate((48, -50)):
            ph = (t * 1.4 + i * .5) % 1; yd = fy + (ey - 10 + 30 * ph) * s; xd = x + dx * s
            pen.stroke([(xd, yd - 10 * s), (xd - 5 * s, yd + 2 * s), (xd, yd + 7 * s), (xd + 5 * s, yd + 2 * s), (xd, yd - 10 * s)], col=(70, 140, 210), w=3 * s, a=a * (1 - ph))
    if tag:
        nm = ENAME[kind]; f = F(900, 17 * SS * s); tw = pen.d.textlength(nm, font=f) / SS
        tx, ty = P(0, ETOP[kind] - 26)
        pen.fill([(tx - tw / 2 - 12 * s, ty - 15 * s), (tx + tw / 2 + 12 * s, ty - 15 * s), (tx + tw / 2 + 12 * s, ty + 15 * s), (tx - tw / 2 - 12 * s, ty + 15 * s)], col if kind != 'greed' else GOLD_D, a)
        pen.text(tx, ty, nm, 17 * s, WHITE, a=a)

# ---------------- room pieces ----------------
RX0, RX1, RY0, RY1 = 110, 970, 440, 1290        # room card
SY0, SY1 = 524, 700; MX0, MX1 = 150, 790        # monitor
DESK = 1066; FYC = 1112                          # desk top, character feet (legs hidden behind the desk)
BUYX, LEVX = 300, 780

def axes(pen, x0, x1, a=1.0):
    for i in range(1, 4): pen.stroke([(x0 + 14, SY0 + i * (SY1 - SY0) / 4), (x1 - 14, SY0 + i * (SY1 - SY0) / 4)], col=(210, 210, 210), w=1.6, amp=.4, a=a)

def chart_pts(x0, x1, vals):
    xs = np.linspace(x0 + 24, x1 - 24, len(vals)); return [(x, SY1 - 20 - v * (SY1 - SY0 - 50)) for x, v in zip(xs, vals)]

def vy(v): return SY1 - 20 - v * (SY1 - SY0 - 50)

def monitor(pen):
    pen.fill([(MX0, SY0 - 14), (MX1, SY0 - 14), (MX1, SY1 + 14), (MX0, SY1 + 14)], WHITE, 1)
    pen.rect(MX0, SY0 - 14, MX1, SY1 + 14, w=5)
    mx = (MX0 + MX1) / 2; pen.stroke([(mx - 20, SY1 + 14), (mx - 26, DESK)], w=5); pen.stroke([(mx + 20, SY1 + 14), (mx + 26, DESK)], w=5)

def glassbox(pen, x0, y0, x1, y1, a=1.0):
    pen.fill([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], (226, 236, 242), .55 * a)
    pen.rect(x0, y0, x1, y1, w=4.5, a=a)
    for j in range(2): pen.stroke([(x0 + 18 + 26 * j, y0 + 60), (x0 + 50 + 26 * j, y0 + 22)], col=WHITE, w=5, a=.9 * a, amp=.3)
    cx = (x0 + x1) / 2; pen.arc(cx, y0 - 6, 12, 180, 360, w=4, a=a)
    pen.fill([(cx - 17, y0 - 8), (cx + 17, y0 - 8), (cx + 17, y0 + 16), (cx - 17, y0 + 16)], GOLD_D, a); pen.rect(cx - 17, y0 - 8, cx + 17, y0 + 16, w=3.5, a=a)
    pen.text(cx, y1 + 20, 'LOCKED', 17, INK, a=a)

def desk(pen, t, room, press_at, lot):
    top = [(100, DESK), (980, DESK), (1000, 1200), (80, 1200)]
    pen.fill(top, (236, 232, 222), 1); pen.stroke(top + [top[0]], w=5); pen.stroke([(100, DESK + 12), (980, DESK + 12)], w=3, amp=.4)
    for j, kx in enumerate((470, 530, 590)):
        pen.circ(kx, 1132, 13, w=4); pen.stroke([(kx, 1132), (kx + 9 * math.cos(j + t * .3), 1132 - 9 * math.sin(j + 2))], w=3)
    pen.rect(440, 1166, 620, 1182, w=3)
    # big BUY button
    pd = 10 * max(0, 1 - abs(t - press_at - .08) / .15) if press_at else 0
    dome = [(BUYX + 54 * math.cos(q), DESK + pd - 34 * math.sin(q)) for q in np.radians(np.linspace(0, 180, 20))]
    pen.fill(dome, RED, 1); pen.stroke(dome + [dome[0]], w=5)
    pen.fill([(BUYX - 66, DESK), (BUYX + 66, DESK), (BUYX + 66, DESK + 14), (BUYX - 66, DESK + 14)], INK, 1)
    pen.text(BUYX, 1128, 'BUY', 34, RED)
    # lot-size lever with its gauge
    ang = lerp(-50, 40, clamp(lot / 5)); r = math.radians(ang)
    hx, hy = LEVX + 150 * math.sin(r), DESK - 150 * math.cos(r)
    pen.arc(LEVX, DESK, 120, 215, 325, col=GREY, w=3, amp=.3)
    for j in range(6):
        q = math.radians(lerp(-50, 40, j / 5) - 90); pen.stroke([(LEVX + 112 * math.cos(q), DESK + 112 * math.sin(q)), (LEVX + 128 * math.cos(q), DESK + 128 * math.sin(q))], col=RED if j == 5 else GREY, w=3, amp=.2)
    pen.stroke([(LEVX, DESK), (hx, hy)], w=8); pen.fill([(hx + 20 * math.cos(q), hy + 20 * math.sin(q)) for q in np.linspace(0, 6.28, 16)], RED, 1); pen.circ(hx, hy, 20, w=4)
    pen.fill([(LEVX - 30, DESK - 8), (LEVX + 30, DESK - 8), (LEVX + 30, DESK + 6), (LEVX - 30, DESK + 6)], INK, 1)
    pen.text(LEVX, 1128, f'LOT {lot:.1f}', 30, RED if lot > 2 else INK)

def bubble(pen, x, y, txt, col, at, t, until, tail):
    q = back((t - at) / .25); out = ease((t - until) / .2)
    if q < .05 or out >= 1: return
    a = clamp((t - at) / .1) * (1 - out); f = F(900, 30 * SS); tw = pen.d.textlength(txt, font=f) / SS
    w2, h2 = (tw / 2 + 24) * q, 34 * q
    pen.fill([(x - w2, y - h2), (x + w2, y - h2), (x + w2, y + h2), (x - w2, y + h2)], WHITE, a)
    pen.fill([(tail - 12, y + h2 - 2), (tail + 12, y + h2 - 2), (tail, y + h2 + 26 * q)], WHITE, a)
    pen.rect(x - w2, y - h2, x + w2, y + h2, w=4, a=a)
    pen.stroke([(tail - 12, y + h2), (tail, y + h2 + 26 * q), (tail + 12, y + h2)], w=4, a=a)
    pen.text(x, y, txt, 30, col, a=a, sc=q)

def beacon(pen, t, on):
    x, y = 470, RY0 + 6
    if on:
        for j in range(2):
            q = t * 5 + j * math.pi; pts = [(x, y + 20)] + [(x + 700 * math.cos(q + d), y + 20 + 380 * abs(math.sin(q + d))) for d in (-.18, .18)]
            pen.fill(pts, RED, .14)
    dome = [(x + 30 * math.cos(q), y + 30 * math.sin(q)) for q in np.radians(np.linspace(0, 180, 16))]
    pen.fill(dome, RED if on and (t * 4) % 1 < .5 else (200, 120, 124), 1); pen.stroke(dome + [dome[0]], w=4)

# ---------------- timeline ----------------
def gary_room(pen, t, k):
    beacon(pen, t, t > G_BLOWN)
    # monitor: setup -> buy -> drop -> blown
    monitor(pen); axes(pen, MX0, MX1)
    vals = [.3, .34, .31, .42, .48, .58, .64, .56, .46, .38, .3, .2, .1, .02]
    pk = keyed([(A(1, 0), 0), (G_BUY, .46), (G_DROP, .5), (G_MOVE, .72), (TT[4], .8), (G_BLOWN, 1.0)], t)
    pts = chart_pts(MX0, MX1, vals); pen.stroke(pts, col=RED if t > G_DROP else INK, w=6, prog=pk)
    if t > G_BUY:
        ex, ey_ = pts[6]; pen.circ(ex, ey_, 12, col=RED, w=5)
        pen.stamp(ex + 4, ey_ - 46, 'BUY', 34, RED, G_BUY, t, rot=-8)
        sl = vy(.45) if t < G_MOVE else lerp(vy(.45), vy(.06), ease((t - G_MOVE) / .6))
        pen.dash(MX0 + 18, MX1 - 18, sl, col=RED, a=.85); pen.text(MX0 + 40, sl - 16, 'SL', 18, RED)
        if t > G_MOVE + .2: pen.text(MX1 - 110, sl - 18, 'SL MOVED', 20, RED, a=clamp((t - G_MOVE - .2) / .2))
    bal = 100000 if t < G_DROP else lerp(100000, 94000, ease((t - G_DROP) / 1.5)) if t < TT[4] else lerp(94000, 88000, ease((t - TT[4]) / (G_BLOWN - TT[4])))
    pen.text(MX0 + 110, SY0 + 10, f'${bal:,.0f}', 26, RED if bal < 100000 else INK)
    if t > G_FIVE: pen.text(MX1 - 90, SY0 + 10, '5 LOTS', 24, RED, a=clamp((t - G_FIVE) / .2))
    if t > G_BLOWN:
        cracks(pen, 470, 612, MX0, MX1, (t - G_BLOWN) / .25)
        pen.stamp(470, 612, 'ACCOUNT BLOWN', 40, RED, G_BLOWN + .05, t, rot=-6)
    glassbox(pen, 818, 530, 958, 722)
    emo(pen, 'disc', 888, 714, t, 'idle', 'sleep', s=.5, tag=False)
    pen.text(888, 512, 'DISCIPLINE', 15, INK)
    blown = t > G_BLOWN
    # FOMO
    fx = keyed([(0, 225), (G_FOMO, 225), (G_FOMO + .35, BUYX)], t)
    fp, fm = ('idle', 'grin') if t < G_FOMO else ('up', 'grin') if t < G_BUY else ('press', 'grin') if t < G_DROP else ('idle', 'scared')
    if blown: fp, fm = 'head', 'scared'
    emo(pen, 'fomo', fx, FYC - 14 * abs(math.sin(math.pi * clamp((t - G_FOMO) / .35))), t, fp, fm)
    # GREED
    gx = keyed([(0, 520), (G_GREED, 520), (G_GREED + .35, 675)], t)
    gp, gm = ('idle', 'grin') if t < G_GREED else ('pull', 'grin') if t < G_RICH else ('up', 'grin') if t < G_DROP else ('idle', 'frown')
    if blown: gp, gm = 'head', 'scared'
    emo(pen, 'greed', gx, FYC - 14 * abs(math.sin(math.pi * clamp((t - G_GREED) / .35))), t, gp, gm)
    # FEAR
    rx_ = keyed([(0, 905), (G_FEAR, 905), (G_FEAR + .45, 495)], t)
    rp, rm = ('idle', 'calm') if t < G_DROP else ('idle', 'scared') if t < G_MOVE else ('pull', 'scared')
    if blown: rp, rm = 'head', 'scared'
    emo(pen, 'fear', rx_, FYC - 14 * abs(math.sin(math.pi * clamp((t - G_FEAR) / .35))), t, rp, rm, shake=3 if t > G_DROP else 0)
    lot = 0.5 if t < G_FIVE else lerp(.5, 5, ease((t - G_FIVE) / .45))
    desk(pen, t, 'g', G_BUY, lot)
    bubble(pen, 300, 758, 'BUY NOW!', RED, G_BUY - .05, t, TT[2] - .2, BUYX)
    bubble(pen, 640, 758, "LET'S GET RICH!", GOLD_D, G_RICH - .05, t, TT[3] - .2, 660)
    bubble(pen, 470, 758, "IT'LL COME BACK!", (78, 110, 160), G_MOVE + .1, t, TT[4] - .1, 500)

def tariq_room(pen, t, k):
    beacon(pen, t, False)
    monitor(pen); axes(pen, MX0, MX1)
    t0 = TT[5] + .3
    vals = [.4, .46, .38, .5, .42, .47, .4, .45]
    pen.stroke(chart_pts(MX0, MX1 - 190, vals), col=INK, w=5, prog=clamp((t - t0) / (T_DISC - t0)))
    for j, it in enumerate(('TREND', 'LEVEL', 'R:R 1:3')):   # the plan checklist: nothing ticks
        at = T_DISC + .15 + j * .22; q = clamp((t - at) / .15)
        if q <= 0 or t > TT[7] - .1: continue
        y = SY0 + 40 + j * 52; pen.text(MX1 - 110, y, it, 20, INK, a=q)
        pen.stroke([(MX1 - 40, y - 10), (MX1 - 22, y + 10)], col=RED, w=5, a=q); pen.stroke([(MX1 - 22, y - 10), (MX1 - 40, y + 10)], col=RED, w=5, a=q)
    if t < TT[7] - .1: pen.stamp(MX0 + 220, SY0 + 120, 'NO TRADE', 40, GOLD_D, T_NOT, t, rot=-7)
    if t > TT[7] - .12:
        pen.text(MX0 + 110, SY0 + 10, '$99,000' if t > T_LOSS + .3 else '$100,000', 26, INK)
        logrow(pen, MX0, MX0 + 360, SY0 + 90, 'SMALL LOSS', '-1%', GREY, T_LOSS, t, 'x')
        q = ease((t - T_SAYS) / .5)
        if q > 0:
            pen.text(MX1 - 140, SY0 + 90, 'RISK', 22, GOLD_D, a=q)
            pen.fill([(MX1 - 200, SY0 + 120), (MX1 - 200 + 150 * .2 * q, SY0 + 120), (MX1 - 200 + 150 * .2 * q, SY0 + 140), (MX1 - 200, SY0 + 140)], GOLD, 1)
            pen.rect(MX1 - 200, SY0 + 120, MX1 - 50, SY0 + 140, w=3, a=q); pen.text(MX1 - 125, SY0 + 170, '1%', 30, GOLD_D, a=q)
    glassbox(pen, 818, 530, 958, 722)
    emo(pen, 'greed', 888, 714, t, 'up', 'angry', s=.5, tag=False)
    pen.text(888, 512, 'GREED', 15, INK)
    # FOMO tries, gets blocked
    fx = keyed([(0, 230), (T_FOMO, 230), (T_FOMO + .4, BUYX + 30), (T_HANDS, BUYX + 30), (T_HANDS + .4, 205)], t)
    fp, fm = ('idle', 'grin') if t < T_FOMO else ('reach', 'grin') if t < T_HANDS else ('idle', 'frown')
    emo(pen, 'fomo', fx, FYC, t, fp, fm)
    dp, dm = ('idle', 'calm') if t < T_DISC else ('hold', 'calm') if t < T_HANDS else ('block', 'calm') if t < TT[7] - .1 else ('idle', 'calm') if t < T_FINE else ('up', 'smile')
    emo(pen, 'disc', 560, FYC, t, dp, dm)
    if t > T_FEAR - .1:
        rx_ = keyed([(T_FEAR - .1, 1060), (T_FEAR + .45, 800)], t)
        emo(pen, 'fear', rx_, FYC, t, 'idle', 'smile' if t > T_FINE else 'scared', shake=0 if t > T_FINE else 3)
    desk(pen, t, 't', None, .5)
    bubble(pen, 560, 758, 'NOT OUR SETUP.', INK, T_NOT - .05, t, TT[7] - .2, 560)
    bubble(pen, 600, 758, "1% RISK. WE'RE FINE.", GOLD_D, T_SAYS + .1, t, TT[8] - .2, 580)

def driver_cards(pen, t):
    for ci, (x0, x1) in enumerate(((120, 528), (552, 960))):
        cx = (x0 + x1) / 2; at = TT[8] - .12 + ci * .3; q = ease((t - at) / .4)
        if q <= 0: continue
        pen.fill([(x0, RY0), (x1, RY0), (x1, RY1), (x0, RY1)], (251, 250, 246), 1); pen.rect(x0, RY0, x1, RY1, w=4, prog=q, col=(60, 60, 64))
        hd = [(cx + 170 * math.cos(q_), 760 + 190 * math.sin(q_)) for q_ in np.linspace(0, 6.283, 50)]
        pen.stroke(hd, w=6, prog=q)
        kind = 'greed' if ci == 0 else 'disc'
        emo(pen, kind, cx, 950, t, 'reach', 'grin' if ci == 0 else 'smile', s=1.05, tag=False, a=q)
        pen.circ(cx, 885, 62, w=8, a=q); pen.stroke([(cx - 62, 885), (cx + 62, 885)], w=6, a=q); pen.stroke([(cx, 885), (cx, 947)], w=6, a=q)
        nm, c = ('GARY', RED) if ci == 0 else ('TARIQ', GOLD_D)
        pen.text(cx, 1060, nm + "'S DRIVER", 26, GREY, a=q)
        pen.text(cx, 1140, 'GREED' if ci == 0 else 'DISCIPLINE', 58 if ci == 0 else 44, RED if ci == 0 else GOLD_D, a=clamp((t - at - .3) / .2), sc=1 + .4 * (1 - back((t - at - .3) / .3)))

def lineup(pen, t):
    for j, (kind, x) in enumerate((('fomo', 210), ('greed', 420), ('fear', 640), ('disc', 860))):
        at = TT[9] - .12 + j * .12; q = back((t - at) / .3)
        if q < .05: continue
        pose, mood = ('up', 'smile') if kind == 'disc' else ('idle', 'grin' if kind != 'fear' else 'scared')
        emo(pen, kind, x, 1230 - 40 * (1 - q), t, pose, mood, s=1.25)
    pen.text(540, 640, '?', 260, GOLD_D, a=clamp((t - TT[9]) / .3), sc=1 + .3 * (1 - back((t - TT[9]) / .4)))

def room(t, k):
    pen = Pen(W, RY1 - RY0 + 120, 0, RY0 - 60)
    if k <= 4 or (k == 5 and t < TT[5] + .2): gary_room(pen, t, k)
    elif k <= 7: tariq_room(pen, t, k)
    elif k == 8: driver_cards(pen, t)
    else: lineup(pen, t)
    return pen.img.reduce(SS)

# ---------------- overlays ----------------
HEADS = {1: [('FOMO: ', RED), ('BUY NOW!', INK)], 2: [('GREED: ', GOLD_D), ('5 LOTS', INK)], 3: [('FEAR: ', (78, 110, 160)), ('MOVE THE STOP', INK)],
         4: [('ACCOUNT ', RED), ('BLOWN', RED)], 5: [('INSIDE ', INK), ("TARIQ'S HEAD", GOLD_D)], 6: [('DISCIPLINE: ', GOLD_D), ('NOT OUR SETUP', INK)],
         7: [('DISCIPLINE: ', GOLD_D), ('1% RISK', INK)], 8: [('SAME EMOTIONS. ', INK), ('DIFFERENT DRIVER.', GOLD_D)],
         9: [("WHO'S DRIVING ", INK), ('YOUR TRADES?', GOLD_D)]}

def headline(img, t, k):
    if k == 0:
        if t < CEND: return
        parts = [('INSIDE ', INK), ("GARY'S HEAD", RED)]; a0 = CEND
    else: parts = HEADS[k]; a0 = TT[k] - .12
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

def banner(img, t, k):   # ink band wipe into Tariq's head
    a0, a1 = TT[5] - .12, TT[6] - .3
    if not (a0 <= t <= a1 + .3): return
    band = Image.new('RGBA', (W, 300), INK + (255,)); d = ImageDraw.Draw(band, 'RGBA')
    d.text((540, 92), 'NOW LOOK INSIDE', font=F(900, 44), fill=GOLD, anchor='mm')
    q = ease((t - a0 - .12) / .35)
    d.text((540, 190 + 30 * (1 - q)), "TARIQ'S HEAD", font=F(900, 104), fill=WHITE + (int(255 * q),), anchor='mm')
    lw = 360 * ease((t - a0 - .3) / .4); d.rectangle([540 - lw / 2, 252, 540 + lw / 2, 260], fill=GOLD)
    x = int(-W * (1 - ease((t - a0) / .3)) + W * ease((t - a1) / .25))
    if not -W < x < W: return
    full = Image.new('RGBA', (W, 300), (0, 0, 0, 0)); full.paste(band, (x, 0))
    sh = Image.new('RGBA', (W, 340), (0, 0, 0, 0)); sh.paste((0, 0, 0, 70), (max(0, x), 30, min(W, x + W), 330))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)), (0, 695)); img.alpha_composite(full, (0, 715))

def endcard(img, t):
    a0 = SEG[9][1] - .25
    if t < a0: return False
    q = ease((t - a0) / .35); y0 = int(1300 + 200 * (1 - q))
    band = Image.new('RGBA', (840, 170), INK + (255,)); d = ImageDraw.Draw(band)
    parts = [("WHO'S ", WHITE), ('DRIVING', GOLD), ('?', WHITE)]; f = F(900, 76)
    tw = sum(d.textlength(p, font=f) for p, c in parts); x = 420 - tw / 2
    for p, c in parts: d.text((x, 70), p, font=f, fill=c, anchor='lm'); x += d.textlength(p, font=f)
    d.text((420, 140), 'SEND THIS TO THE FRIEND RUN BY GREED', font=F(800, 22), fill=(170, 170, 174), anchor='mm')
    m = Image.new('L', band.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, 839, 169], 26, fill=255); band.putalpha(m)
    img.alpha_composite(band, (120, y0)); return True

def head_mask(r):
    m = Image.new('L', (W, H), 0); d = ImageDraw.Draw(m); cx, cy = 540, 860
    d.ellipse([cx - r, cy - r * 1.12, cx + r, cy + r * 1.12], fill=255); return m

def coldopen(img, t):   # black open: a head outline, then we zoom through it into the control room
    if t > CEND + .6: return
    lay = Image.new('RGBA', (W, H), INK + (255,)); d = ImageDraw.Draw(lay, 'RGBA')
    r = 230 * (1 + 7 * ease((t - CEND) / .6) ** 2)
    m = head_mask(r) if t > CEND else None
    cx, cy = 540, 860; dr = r * (1 + .02 * (1 - ease(t / .5)))
    d.ellipse([cx - dr, cy - dr * 1.12, cx + dr, cy + dr * 1.12], outline=WHITE, width=8)
    if t < CEND:
        d.rectangle([cx - 70, cy + dr * 1.08, cx + 70, cy + dr * 1.08 + 120], fill=INK); d.line([(cx - 70, cy + dr * 1.06), (cx - 80, 1300)], fill=WHITE, width=8)
        d.line([(cx + 70, cy + dr * 1.06), (cx + 80, 1300)], fill=WHITE, width=8)
        pq = 1 + .08 * math.sin(t * 6); d.text((cx, cy), '?', font=F(900, int(230 * pq)), fill=GOLD, anchor='mm')
    words = [('WHO', WHITE), ('IS', WHITE), ('DRIVING', GOLD), ('YOUR', WHITE), ('TRADES?', WHITE)]
    fr = [.0, .06, .2, .36, .44]; f2 = F(900, 56)
    tw = sum(d.textlength(w + ' ', font=f2) for w, c in words) - d.textlength(' ', font=f2); x = 540 - tw / 2
    for (w, c), fq in zip(words, fr):
        q = ease((t - A(0, fq) - .05) / .25)
        if q > 0 and t < CEND + .1: d.text((x, 470 + 30 * (1 - q)), w, font=f2, fill=c + (int(255 * q),), anchor='lm')
        x += d.textlength(w + ' ', font=f2)
    if m is not None: lay.putalpha(Image.eval(m, lambda v: 255 - v))
    img.alpha_composite(lay)

def hit_list():
    return [(.05, 1.0), (CEND, 1.0), (G_BUY, 1.0), (G_FIVE, .9), (G_DROP, .8), (G_MOVE, .9), (G_BLOWN, 1.2), (TT[5] - .12, 1.0),
            (T_NOT, .8), (T_HANDS, .9), (T_LOSS, .5), (T_FINE, .6), (TT[8] - .12, 1.0), (TT[9] - .12, 1.0)]

def frame(t):
    global BOIL
    BOIL = int(t * 8); k = scene(t)
    img = PAPER_IMG.copy(); lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    if k <= 7:
        lay.alpha_composite(SHADOW)
    im = room(t, k)
    if k == 4 and t > G_BLOWN + .1:   # the room drains of colour, the alarm keeps its red
        g = im.convert('LA').convert('RGBA'); g.putalpha(im.split()[3]); im = Image.blend(im, g, .35 * ease((t - G_BLOWN - .1) / .6))
    gl = t - G_BLOWN
    if 0 <= gl < .28:
        r_, g_, b_, a_ = im.split(); o = int(10 * (1 - gl / .28)) + 2
        im = Image.merge('RGBA', (r_.transform(im.size, Image.AFFINE, (1, 0, -o, 0, 1, 0)), g_, b_.transform(im.size, Image.AFFINE, (1, 0, o, 0, 1, 0)), a_))
    sh = 0
    for at, s in HITS:
        if 0 < t - at < .3 and k <= 4: sh = int(8 * s * math.sin((t - at) * 70) * (1 - (t - at) / .3))
    lay.alpha_composite(im, (sh, RY0 - 60))
    # camera: slow drift, punch-in toward whoever is acting
    r = t - (TT[k] - .12); z = 1.01 + .006 * math.sin(t * .7) + .04 * max(0, 1 - r / .22)
    fx, fy = 540, 865
    focus = {1: BUYX, 2: 660, 3: 500, 6: 460, 7: 700}.get(k)
    if focus: fx = lerp(540, focus, .6); z += .05 * ease((t - TT[k]) / 1.2)
    if k == 4: z += .06 * ease((t - G_BLOWN + .2) / .3); fy = 760
    zw, zh = int(W * z), int(H * z); big = lay.resize((zw, zh), Image.BILINEAR)
    cx = int(fx * z - fx); cy = int(fy * z - fy); lay = big.crop((cx, cy, cx + W, cy + H))
    img.alpha_composite(lay)
    if k == 4 and t > G_BLOWN: img.alpha_composite(_vig(RED_VIG, .35 + .3 * math.sin((t - G_BLOWN) * 10)))
    banner(img, t, k); headline(img, t, k)
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
    b = 60 / 124
    for j in range(int((DUR - .5) / b)):
        at = .3 + j * b
        if TT[5] - .4 < at < TT[5] + .2: continue
        add(dry, ca.kick(.25, .8), at, .32 if j % 2 == 0 else .18); add(dry, ca.tick(.04), at + b / 2, .12)
        if j % 4 == 2: add(dry, ca.clap(.3), at, .12, 120)
    prog = [(45, 52, 57, 60), (41, 48, 53, 57), (43, 50, 55, 59), (40, 47, 52, 55)]
    for i, at in enumerate(np.arange(.3, DUR - 1, 4.0)): add(fx, ca.pad(prog[i % 4], 4.4), at, .24, 400)
    whoosh, ping, coins = sfx('whoosh'), sfx('ping'), sfx('coin')
    add(fx, ca.sub_boom(3.0, 38), 0, .4); add(fx, ca.reverse_swell(.6), CEND - .5, .3, 300); add(fx, whoosh, CEND, .6)
    for at in (TT[5], TT[8], TT[9]): add(fx, whoosh, at - .25, .4)
    add(fx, coins, G_BUY + .05, .35)
    for j in range(6): add(dry, ca.tick(.05), G_FIVE + j * .08, .5 + j * .05)   # lever ratchet
    for j in range(4): add(dry, sfx('heart'), G_DROP + j * .62, .9)
    add(fx, whoosh, G_MOVE, .5); add(fx, ca.riser(1.4, 250, 4500), G_BLOWN - 1.4, .25, 200)
    for j in range(4): add(fx, sfx('alarm'), G_BLOWN + j * .6, .45)
    add(fx, sfx('glitch'), G_BLOWN, .5); add(fx, sfx('crack'), G_BLOWN + .05, .6)
    add(fx, ping, T_NOT, .4); add(fx, sfx('shimmer'), T_FINE, .45); add(fx, sfx('shimmer'), TT[9] + .1, .4)
    for at, s in HITS: hit(at, s)
    bed = ca.reverb(dry + fx, 2.0, .22); bed /= np.max(np.abs(bed)) + 1e-9
    tt_ = np.arange(N) / SR; gate = 1 - .92 * ((tt_ > G_BLOWN - .45) & (tt_ < G_BLOWN - .05))   # a beat of silence before it blows
    bed *= gate[:, None]
    v = np.interp(np.arange(N) / SR, np.arange(len(vo)) / vsr, vo, right=0)
    e = np.convolve(np.abs(v), np.ones(int(.2 * SR)) / int(.2 * SR), 'same')
    duck = 1 - .55 * np.clip(e / (e.max() * .25), 0, 1)
    voice = np.stack([v, v], 1) / (np.max(np.abs(v)) + 1e-9)
    m = np.tanh((bed * duck[:, None] * .45 + voice * 1.0) * 1.2) * .9
    with wave.open('head_audio.wav', 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((m * 32767).astype(np.int16).tobytes())

CEND = S(0, "Let's look")
G_FOMO, G_BUY = S(1, 'FOMO grabs'), S(1, 'Buy now'); G_GREED, G_FIVE, G_RICH = S(2, 'Greed'), S(2, 'Five lots'), S(2, "Let's get")
G_DROP, G_FEAR, G_MOVE, G_BLOWN = S(3, 'Price drops'), S(3, 'Fear'), S(3, 'Move the'), S(4, 'Account')
T_FOMO, T_DISC, T_NOT, T_HANDS = S(6, 'FOMO reaches'), S(6, 'Discipline checks'), S(6, 'Not our'), S(6, 'Hands off')
T_LOSS, T_FEAR, T_SAYS, T_FINE = S(7, 'Then a'), S(7, 'Fear shows'), S(7, 'Discipline says'), S(7, "We're fine")
HITS = hit_list()
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
                          '-i', 'head_audio.wav', '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '17',
                          '-preset', 'medium', '-c:a', 'aac', '-b:a', '192k', '-ar', '44100', '-shortest', '-movflags', '+faststart', OUT], stdin=subprocess.PIPE)
    for i in range(int(DUR * FPS)): p.stdin.write(frame(i / FPS).tobytes())
    p.stdin.close(); p.wait()
