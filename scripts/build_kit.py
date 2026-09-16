#!/usr/bin/env python3
"""Build the creator kit twice from one source of copy:
   kit/index.html               the web page (teamhuman.org/kit)
   kit/TeamHuman-Creator-Kit.pdf the same thing as a two-page PDF (via headless Chrome)
Edit the COPY below, run `python3 scripts/build_kit.py`, commit both outputs."""
import pathlib, subprocess, shutil, tempfile, os

ROOT = pathlib.Path(__file__).resolve().parent.parent
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
FILL = lambda t: f'<span class="fill">[{t}]</span>'

# ----------------------------------------------------------------- copy ----
HERO_H1 = 'It’s <em>easy</em> to participate in Team Human.'
HERO_LEDE = 'Join creators with 300M+ subscribers calling for a global slowdown until it’s safe.'

PLAN = f'''
  <ol class="first">
    <li>Make a video about AI and share your concerns. Best way to help.</li>
    <li>Or add a 30 to 60 second segment to a video.</li>
    <li>Or make a dedicated Short.</li>
  </ol>
  <p class="after-list">Include #TeamHuman in the title or description so we can find your video.</p>

  <h2>What to say</h2>
  <ul>
    <li>Your concerns with AI, the ones your audience will relate to. Everyone has their own reasons for joining.</li>
    <li>Link your reason to the solution: a global slowdown until it’s safe, through international agreements.</li>
    <li>Send viewers to <b>teamhuman.org</b> to add their name. Every signature will be hand-delivered to lawmakers in DC and Brussels.</li>
  </ul>

  <h2>Release your video on October 3, 10 or 17.</h2>
  <p>Any day through October 31 works.</p>

  <h2>An example, about 45 seconds</h2>
  <p class="q">AI is moving faster than our ability to control it. I make videos about {FILL('your topic')}, and the thing that actually gets me is {FILL('your reason')}. The heads of all four leading AI companies are now publicly calling for a slowdown, and more than 1,300 of their own employees signed an open letter asking government to make that possible, because no one can stop alone. We’re asking for one thing: no smarter-than-human AI until scientists agree it can be built safely, and the public agrees to go ahead. Governments won’t act until they see how much the public cares. Go to teamhuman.org and add your name. AI should serve humanity, not replace it.</p>
'''

QUESTIONS = '''
  <h2>Questions</h2>
  <p><b>Sam Obenchain</b> · <a href="mailto:sam@teamhuman.org">sam@teamhuman.org</a> · WhatsApp +1 931 639 7903 · Discord niceclimbers</p>
'''

LINES_H1 = 'Lines you can lift.'
LINES_LEDE = 'Pick one per slot, fill the blanks, end on the ask.'
LINES = f'''
  <h2>1. Open</h2>
  <ul>
    <li>“AI is moving faster than our ability to control it.”</li>
    <li>“AI could be the best thing that ever happens to humanity. It could also be the last.”</li>
    <li>“A handful of companies are racing to build the most powerful technology in history with no oversight and, by their own admission, without fully understanding what they’re building.”</li>
    <li>Quick pause. I make videos about {FILL('your topic')}. I never expected to make one about this.</li>
  </ul>

  <h2>2. Your reason</h2>
  <ul>
    <li>I joined Team Human because {FILL('your reason')}.</li>
    <li>Or go rapid-fire, two or three of these: “How much of the internet has to be fake?” “How many creators have to be buried under AI slop?” “How many artists have to compete with copies of themselves?” “How many scams and deepfakes?” “How many elections undermined?” “How many kids grow up shaped by algorithms no parent chose?” “How close to surveillance dystopias, AI-designed pandemics, killer robots, human extinction?”</li>
    <li>…then land it: “This situation is insane. And we all know it.”</li>
  </ul>

  <h2>3. Who agrees</h2>
  <ul>
    <li>“The heads of all four leading AI companies are now publicly calling for a slowdown.”</li>
    <li>“More than 1,300 of their own employees signed an open letter asking government to make that possible, because no one can stop alone.”</li>
    <li>“The people who agree on nothing agree on this. Scientists and generals. Left and right. Bishops and rock stars.”</li>
    <li>“Hundreds of Nobel Prize winners, AI experts and heads of state have signed the Superintelligence Statement.”</li>
    <li>“68% of voters back a pause on advanced AI and a ban on superintelligence.”</li>
    <li>“Creators with over 300 million subscribers have signed on.” Mark Rober. Kurzgesagt. {FILL('a creator your audience knows')}.</li>
  </ul>

  <h2>4. The fix</h2>
  <ul>
    <li>Team Human is asking for one thing: “slow down AI.”</li>
    <li>“No smarter-than-human AI until scientists agree it can be built safely, and the public agrees to go ahead.”</li>
    <li>“The root cause is the global AI arms race. It punishes anyone who slows down. That’s what governments are for.”</li>
    <li>“We limited nuclear weapons. We saved the ozone layer. We eradicated smallpox. Every time it took cooperation between countries, and ordinary people who refused to be quiet. It’s time to do it again.”</li>
  </ul>

  <h2>5. The ask</h2>
  <ul>
    <li>“Governments won’t act without seeing how much the public cares. With Team Human, we’re going to show them.”</li>
    <li>“Go to teamhuman.org and add your name. It takes ten seconds.”</li>
    <li>“In November, every signature gets hand-delivered to hundreds of lawmakers in Washington and Brussels.”</li>
    <li>“Join the movement to keep humans in control of AI.”</li>
    <li>“AI should serve humanity, not replace it.”</li>
  </ul>
'''

FONTS = '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400..900;1,9..144,400..900&family=Inter:wght@400;500;600;700&display=%s" rel="stylesheet">'

SHARED_CSS = '''
  :root{--parchment:#f6efe3;--cream:#fbf6ec;--charcoal:#201c17;--terracotta:#9c3a26;--terracotta-dark:#83301f;--walnut:#5e4630;--slate:#5b7d8f;--line:rgba(94,70,48,.18)}
  *{box-sizing:border-box}
  h1{font-family:'Fraunces',Georgia,serif;font-weight:700;line-height:1.08;letter-spacing:-.01em;margin:0 0 8px}
  h1 em{font-style:italic;color:var(--terracotta)}
  .lede{font-family:'Fraunces',Georgia,serif;font-style:italic;color:var(--walnut);margin:0}
  h2{font-family:'Fraunces',Georgia,serif;font-weight:700;line-height:1.2;margin:22px 0 6px}
  ol,ul{margin:0;padding-left:22px}
  li{margin:0 0 5px}
  li::marker{color:var(--terracotta);font-weight:700}
  .after-list{margin:8px 0 0}
  .fill{background:rgba(91,125,143,.13);border-bottom:1.5px solid var(--slate);color:#2f4a57;padding:0 3px;border-radius:3px}
  .q{font-family:'Fraunces',Georgia,serif;color:#2b2520;padding:12px 16px;border-left:3px solid var(--terracotta);background:var(--cream);border-radius:0 8px 8px 0;margin:4px 0 0}
  a{color:var(--terracotta)}
'''

# ------------------------------------------------------------ web page ----
WEB = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Creator Kit | #TeamHuman</title>
<meta name="description" content="Everything a creator needs to take part in Team Human: the ask, what to say, lines lifted from the site, and the dates.">
<meta name="robots" content="noindex">
<link rel="icon" href="../brand/handprint.png">
{FONTS % 'swap'}
<style>
{SHARED_CSS}
  html{{scroll-behavior:smooth}}
  body{{margin:0;font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif;background:var(--parchment);color:var(--charcoal);line-height:1.6;-webkit-font-smoothing:antialiased;min-height:100vh;display:flex;flex-direction:column;font-size:1.02rem}}
  ::selection{{background:var(--terracotta);color:var(--cream)}}
  :focus-visible{{outline:2px solid var(--terracotta);outline-offset:2px}}
  nav{{background:rgba(246,239,227,.92);border-bottom:1px solid var(--line)}}
  .nav-inner{{display:flex;align-items:center;justify-content:space-between;height:66px;max-width:1140px;margin:0 auto;padding:0 24px}}
  .lockup img{{height:34px;width:auto;display:block}}
  nav a.back{{color:var(--charcoal);text-decoration:none;font-size:.92rem;font-weight:500}}
  nav a.back:hover{{color:var(--terracotta)}}
  main{{flex:1;padding:52px 0 80px}}
  .wrap{{max-width:720px;margin:0 auto;padding:0 24px;width:100%}}
  .kicker{{font-size:.78rem;font-weight:700;letter-spacing:.26em;text-transform:uppercase;color:var(--terracotta);margin-bottom:14px}}
  h1{{font-size:clamp(2rem,4.6vw,2.9rem)}}
  .lede{{font-size:1.15rem}}
  ol.first{{margin-top:22px}}
  .pdf{{display:inline-block;margin:14px 0 0;color:var(--walnut);font-size:.88rem;text-decoration:underline;text-underline-offset:3px}}
  .pdf:hover{{color:var(--terracotta)}}
  h2{{font-size:1.35rem}}
  .q{{font-size:1.08rem;line-height:1.55}}
  .lines{{margin-top:64px;padding-top:40px;border-top:1px solid var(--line)}}
  .lines h1{{font-size:clamp(1.7rem,3.6vw,2.3rem)}}
  .lines h2{{font-size:1.2rem;margin-top:26px}}
  .lines li{{margin-bottom:6px}}
  .questions{{margin-top:56px;padding-top:28px;border-top:1px solid var(--line)}}
  .questions h2{{margin-top:0}}
  footer{{border-top:1px solid var(--line);padding:26px 0}}
  .foot-inner{{max-width:1140px;margin:0 auto;padding:0 24px;display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap;font-size:.84rem;color:var(--walnut)}}
  .foot-inner a{{color:var(--walnut);text-decoration:none}}
  .foot-inner a:hover{{color:var(--terracotta)}}
  @media (max-width:480px){{ body{{font-size:.98rem}} }}
</style>
</head>
<body>
<nav>
  <div class="nav-inner">
    <a class="lockup" href="../" aria-label="Team Human home"><img src="../brand/wordmark.png" alt="Team Human"></a>
    <a class="back" href="../invite/">← Creator invite</a>
  </div>
</nav>

<main>
  <div class="wrap">
    <div class="kicker">Creator Kit · October 2026</div>
    <h1>{HERO_H1}</h1>
    <p class="lede">{HERO_LEDE}</p>
    <a class="pdf" href="TeamHuman-Creator-Kit.pdf">Download as PDF ↓</a>
{PLAN}
    <div class="lines" id="lines">
      <h1>{LINES_H1}</h1>
      <p class="lede">{LINES_LEDE}</p>
{LINES}
    </div>
    <div class="questions">
{QUESTIONS}
    </div>
  </div>
</main>

<footer>
  <div class="foot-inner">
    <span>© 2026 TeamHuman. We are the pressure.</span>
    <a href="../">teamhuman.org</a>
  </div>
</footer>
</body>
</html>
'''

# ---------------------------------------------------------------- print ----
def print_html(base):
    hdr = f'<header><img src="file://{base}/brand/wordmark.png" alt="TeamHuman"><span class="kick">Creator Kit · October 2026</span></header>'
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><title>TeamHuman Creator Kit</title>
{FONTS % 'block'}
<style>
{SHARED_CSS}
  @page{{size:Letter;margin:0}}
  html,body{{margin:0;padding:0;background:var(--parchment);color:var(--charcoal);font-family:'Inter',-apple-system,sans-serif;font-size:11.2pt;line-height:1.5;-webkit-print-color-adjust:exact;print-color-adjust:exact}}
  .page{{width:8.5in;height:11in;padding:.6in .8in .95in;position:relative;page-break-after:always;overflow:hidden;display:flex;flex-direction:column}}
  .page:last-child{{page-break-after:auto}}
  header{{display:flex;align-items:center;justify-content:space-between;margin-bottom:22px}}
  header img{{height:20px}}
  header .kick{{font-size:8.5pt;letter-spacing:.2em;text-transform:uppercase;color:var(--walnut);font-weight:600}}
  h1{{font-size:27pt}}
  .lede{{font-size:12.5pt;margin-bottom:22px}}
  h2{{font-size:14pt}}
  .q{{font-size:10.6pt;line-height:1.45;padding:10px 14px}}
  .bottom{{margin-top:auto}}
  .slot header{{margin-bottom:12px}}
  .slot h1{{font-size:21pt;margin-bottom:2px}}
  .slot .lede{{margin-bottom:0;font-size:11pt}}
  .slot h2{{margin:9px 0 4px;font-size:12.5pt}}
  .slot li{{margin-bottom:1px;font-size:9.9pt;line-height:1.35}}
  a{{color:inherit;text-decoration:none}}
  footer{{position:absolute;left:.8in;right:.8in;bottom:.4in;font-size:8.5pt;color:var(--walnut);display:flex;justify-content:space-between}}
</style></head><body>
<section class="page">
  {hdr}
  <h1>{HERO_H1}</h1>
  <p class="lede">{HERO_LEDE}</p>
{PLAN}
  <div class="bottom">
{QUESTIONS}
  </div>
  <footer><span>teamhuman.org/kit</span><span>1 / 2</span></footer>
</section>
<section class="page slot">
  {hdr}
  <h1>{LINES_H1}</h1>
  <p class="lede">{LINES_LEDE}</p>
{LINES}
  <footer><span>teamhuman.org/kit</span><span>2 / 2</span></footer>
</section>
</body></html>
'''

if __name__ == "__main__":
    (ROOT / "kit").mkdir(exist_ok=True)
    (ROOT / "kit" / "index.html").write_text(WEB)
    tmp = pathlib.Path(tempfile.mkdtemp())
    src = tmp / "kit-print.html"; src.write_text(print_html(ROOT))
    out = ROOT / "kit" / "TeamHuman-Creator-Kit.pdf"
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--virtual-time-budget=20000",
                    f"--print-to-pdf={out}", f"file://{src}"], check=True, capture_output=True)
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"wrote kit/index.html ({len(WEB)//1024} KB) and {out.name} ({out.stat().st_size//1024} KB)")
