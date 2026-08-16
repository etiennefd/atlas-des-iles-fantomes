#!/usr/bin/env python3
"""
Import stories from the CTENIQ blog into src/content/stories/fr/.

Reads the WordPress REST API rather than scraping the rendered page, so the
prose arrives verbatim — no model in the loop, nothing paraphrased. The posts
turn out to be structurally uniform: images, an optional centred caption, one
<ul> that is exactly the `notice` block, `//` scene breaks, then prose.

    python3 scripts/import_posts.py --slug ile-de-hy-brasil --dry-run
    python3 scripts/import_posts.py --all
    python3 scripts/import_posts.py --all --images     # also download plates

Nothing is overwritten unless --force is given.
"""
import argparse, html as htmllib, json, os, re, sys, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
OUT = os.path.join(ROOT, "src", "content", "stories", "fr")
IMGDIR = os.path.join(ROOT, "public", "iles")
API = "https://etiennefd.com/cteniq/wp-json/wp/v2/posts"
# Wikimedia asks for a descriptive agent rather than a browser string.
UA = "atlas-des-iles-fantomes/1.0 (import of author's own posts; contact via etiennefd.com)"
POST_URL = "https://etiennefd.com/cteniq/{slug}/"

# blog slug -> island ids. Three posts cover more than one island; the file is
# named for the first, which is what the map already assumes.
ISLANDS = {
    "antillia": ["antillia"],
    "bacalao": ["bacalao"],
    "crocker-land-et-bradley-land": ["crocker-land", "bradley-land"],
    "frisland": ["frisland"],
    "groclant": ["groclant"],
    "ile-aux-vaches": ["ile-aux-vaches"],
    "ile-buss": ["buss"],
    "ile-de-californie": ["californie"],
    "ile-de-dougherty": ["dougherty"],
    "ile-de-hy-brasil": ["hy-brasil"],
    "ile-de-saint-brendan": ["saint-brendan"],
    "ile-des-demons": ["ile-des-demons"],
    "ile-elizabeth": ["elizabeth"],
    "ile-emerald": ["emerald"],
    "ile-jacquet": ["jacquet"],
    "ile-juan-de-lisboa": ["juan-de-lisboa", "dos-romeiros"],
    "ile-maria-de-lajara": ["maria-de-lajara"],
    "ile-saint-mathieu": ["saint-mathieu"],
    "iles-aurora": ["aurora"],
    "kianida": ["kianida"],
    "la-coree": ["coree"],
    "la-terre-de-davis": ["terre-de-davis"],
    "les-recifs": ["ernest-legouve", "maria-theresa"],
    "lile-de-bermeja": ["bermeja"],
    "los-jardines": ["los-jardines"],
    "mayda": ["mayda"],
    "tuanaki": ["tuanaki"],
    "zanara": ["zanara"],
}


def fetch(slug):
    url = f"{API}?slug={slug}&_fields=id,slug,date,title,content"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.load(r)
    if not d:
        raise SystemExit(f"post not found: {slug}")
    return d[0]


# --- HTML -> markdown, for the small subset of tags these posts actually use --
def inline(frag):
    """Inline HTML to markdown. Order matters: links before tag-stripping."""
    s = frag
    s = re.sub(r"<br\s*/?>", " ", s, flags=re.I)
    s = re.sub(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
               lambda m: f"[{inline(m.group(2))}]({m.group(1)})", s, flags=re.S | re.I)
    s = re.sub(r"<(strong|b)\b[^>]*>(.*?)</\1>", r"**\2**", s, flags=re.S | re.I)
    s = re.sub(r"<(em|i)\b[^>]*>(.*?)</\1>", r"*\2*", s, flags=re.S | re.I)
    s = re.sub(r"<[^>]+>", "", s)               # spans, font sizing, leftovers
    s = htmllib.unescape(s)
    s = s.replace(" ", " ")                 # nbsp -> narrow space is lost anyway
    s = re.sub(r"\*\s+\*", " ", s)          # adjacent <em> runs: *a* *b* -> *a b*
    s = re.sub(r"[ \t]+", " ", s)
    return s.strip()


def is_sep(text):
    return re.fullmatch(r"/{2,}", text.replace(" ", "")) is not None


def parse(post):
    h = post["content"]["rendered"]
    blocks = re.findall(r"<(p|ul)\b[^>]*>(.*?)</\1>", h, re.S | re.I)

    images, notice, body = [], [], []
    pending_caption_for = None

    for tag, inner in blocks:
        if tag.lower() == "ul":
            for li in re.findall(r"<li\b[^>]*>(.*?)</li>", inner, re.S | re.I):
                t = inline(li)
                if not t:
                    continue
                m = re.match(r"^(.{1,60}?)\s*:\s*(.+)$", t, re.S)
                if m:
                    notice.append({"label": m.group(1).strip(), "body": m.group(2).strip()})
                else:
                    notice.append({"label": "", "body": t})
            continue

        srcs = re.findall(r'<img\b[^>]*?src="([^"]+)"', inner)
        if srcs:
            for s in srcs:
                images.append({"remote": s, "alt": "", "caption": ""})
            pending_caption_for = len(images) - 1
            continue

        text = inline(inner)
        if not text:
            continue
        if is_sep(text):
            body.append("***")
            pending_caption_for = None
            continue
        # a centred/italic paragraph straight after images is the plate caption
        if pending_caption_for is not None and not body:
            centred = "text-align: center" in tag or "text-align:center" in inner
            italic = inner.strip().startswith("<em") or "<em" in inner[:40]
            if centred or italic:
                m = re.fullmatch(r"\*(.+)\*", text, re.S)
                if m:
                    text = m.group(1).strip()
                images[pending_caption_for]["caption"] = text
                pending_caption_for = None
                continue
        pending_caption_for = None
        # A literal asterisk used as a footnote marker, immediately followed by
        # italic text, converts to "**…*" — which markdown reads as bold-open
        # and renders wrong. Escape the marker so it stays a marker. (kianida.)
        if text.startswith("*") and text.count("*") % 2:
            text = "\\" + text
        body.append(text)

    return images, notice, body


def yaml_str(s):
    """Quote for YAML. These strings carry colons, quotes and apostrophes."""
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def block(s, indent="      "):
    """Folded block scalar — keeps long markdown readable in frontmatter."""
    if len(s) <= 72 and "\n" not in s:
        return yaml_str(s)
    out = [">-"]
    for line in wrap(s, 74):
        out.append(indent + line)
    return "\n".join(out)


def wrap(s, width):
    words, line, lines = s.split(), "", []
    for w in words:
        if line and len(line) + 1 + len(w) > width:
            lines.append(line); line = w
        else:
            line = f"{line} {w}".strip()
    if line:
        lines.append(line)
    return lines or [""]


def render(post, images, notice, body):
    slug = post["slug"]
    ids = ISLANDS[slug]
    title = inline(post["title"]["rendered"])
    date = post["date"][:10]

    fm = ["---"]
    fm.append(f"title: {yaml_str(title)}")
    fm.append(f"islands: [{', '.join(ids)}]")
    fm.append(f"date: {date}")
    fm.append(f"source: {POST_URL.format(slug=slug)}")
    if images:
        fm.append("images:")
        for im in images:
            fm.append(f"  - src: {im['local']}")
            fm.append(f"    alt: {yaml_str(im['alt'])}")
            if im["caption"]:
                fm.append("    caption: " + block(im["caption"]))
    if notice:
        fm.append("notice:")
        for n in notice:
            fm.append(f"  - label: {yaml_str(n['label'])}")
            fm.append("    body: " + block(n["body"]))
    fm.append("---")
    return "\n".join(fm) + "\n\n" + "\n\n".join(body) + "\n"


def candidates(url):
    """URLs to try, in order. Filenames carry accents, so the path is encoded.
    Wikimedia rejects arbitrary thumbnail widths (HTTP 400, 'use thumbnail
    sizes listed'), so fall back through standard widths and then the
    original file."""
    parts = urllib.parse.urlsplit(url)
    # `safe` keeps % so an already-encoded path (Wikimedia writes %2C for a
    # comma) isn't encoded twice into %252C, which 404s. Accented characters
    # still get encoded, which is what the blog's own filenames need.
    path = urllib.parse.quote(parts.path, safe="/%:@!$&'()*+,;=~")
    build = lambda p: urllib.parse.urlunsplit(
        (parts.scheme, parts.netloc, p, parts.query, parts.fragment))
    out = [build(path)]
    if "upload.wikimedia.org" in parts.netloc:
        for w in (1280, 1024, 800):
            out.append(build(re.sub(r"/\d{3,5}px-", f"/{w}px-", path)))
        # /commons/thumb/a/ab/File.jpg/800px-File.jpg -> /commons/a/ab/File.jpg
        m = re.match(r"(.*)/thumb(/./../[^/]+)/[^/]+$", path)
        if m:
            out.append(build(m.group(1) + m.group(2)))
    seen, uniq = set(), []
    for u in out:
        if u not in seen:
            seen.add(u); uniq.append(u)
    return uniq


def download(url, dest):
    """Never fatal — one unreachable plate must not abort 28 imports."""
    for u in candidates(url):
        try:
            req = urllib.request.Request(u, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
            if data:
                open(dest, "wb").write(data)
                return True
        except Exception:
            continue
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--images", action="store_true", help="download the plates")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    slugs = list(ISLANDS) if a.all else ([a.slug] if a.slug else [])
    if not slugs:
        raise SystemExit("give --slug or --all")

    failed = []
    os.makedirs(OUT, exist_ok=True)
    if a.images and not a.dry_run:
        os.makedirs(IMGDIR, exist_ok=True)

    for slug in slugs:
        post = fetch(slug)
        images, notice, body = parse(post)
        ids = ISLANDS[slug]

        for i, im in enumerate(images, 1):
            ext = os.path.splitext(im["remote"])[1].split("?")[0] or ".png"
            name = f"{ids[0]}-{i}{ext}" if len(images) > 1 else f"{ids[0]}{ext}"
            im["local"] = f"/iles/{name}"
            if a.images and not a.dry_run:
                dest = os.path.join(IMGDIR, name)
                if a.force or not os.path.exists(dest):
                    ok = download(im["remote"], dest)
                    if not ok:
                        failed.append((slug, im["remote"]))

        md = render(post, images, notice, body)
        path = os.path.join(OUT, f"{ids[0]}.md")
        words = sum(len(b.split()) for b in body if b != "***")
        status = "would write" if a.dry_run else "wrote"
        if os.path.exists(path) and not a.force and not a.dry_run:
            status = "SKIP (exists, use --force)"
        else:
            if not a.dry_run:
                open(path, "w", encoding="utf-8").write(md)
        print(f"{status:<26} {os.path.relpath(path, ROOT):<42} "
              f"{words:>5} words  {len(notice)} notice  {len(images)} img  "
              f"{body.count('***')} breaks")


    if failed:
        print(f"\n{len(failed)} image(s) could not be downloaded:")
        for s_, u in failed:
            print(f"   {s_}\n      {u}")


if __name__ == "__main__":
    main()
