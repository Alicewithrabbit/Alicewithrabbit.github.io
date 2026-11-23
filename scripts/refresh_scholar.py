"""Refresh the static Google Scholar citation panel from Chong Wu's public profile."""

from datetime import date
from argparse import ArgumentParser
from html import unescape
from pathlib import Path
import re
from urllib.request import Request, urlopen

PAGE = Path(__file__).resolve().parents[1] / "index.html"
PROFILE = "https://scholar.google.com/citations?user=WLKRwxYAAAAJ&hl=en"


def citation_data(page):
    if not re.search(r'id="gsc_prf_in"[^>]*>\s*Chong Wu\s*<', page, re.I):
        raise ValueError("Google Scholar did not return Chong Wu's profile.")
    table = re.search(r'<table id="gsc_rsb_st".*?</table>', page, re.S)
    if not table or not re.search(r'>All</th>', table[0]):
        raise ValueError("Google Scholar's all-time metrics are unavailable.")
    total = re.search(r'>Citations</a></td>\s*<td class="gsc_rsb_std">([0-9,]+)</td>', table[0])
    years = re.findall(r'<span class="gsc_g_t"[^>]*>([0-9]{4})</span>', page)
    values = re.findall(r'<span class="gsc_g_al">([0-9,]+)</span>', page)
    if not total or not years or len(years) != len(values) or years != sorted(set(years)):
        raise ValueError("Google Scholar's citation totals or year labels are incomplete.")
    return int(total[1].replace(",", "")), [(y, int(v.replace(",", ""))) for y, v in zip(years, values)]


def update_panel(markup, total, annual, today):
    peak = max(v for _, v in annual) or 1
    label = ", ".join(f"{y}: {v}" for y, v in annual)
    bars = "\n".join(
        f'            <i style="--bar:{100 * v / peak:.1f}%" title="{y}: {v} citations"></i>'
        for y, v in annual
    )
    start = markup.index('          <span class="metric">')
    end = markup.index('        </a>', start)
    panel = f'''          <span class="metric"><strong data-citation-total>{total:,}</strong> citations</span>
          <span class="trend" role="img" aria-label="Annual citations, {label}">
{bars}
          </span>
          <span class="chart-years"><span>{annual[0][0]}</span><span>{annual[-1][0]}</span></span>
          <span class="as-of">Checked <time datetime="{today.isoformat()}">{today.day} {today:%b %Y}</time></span>
'''
    return markup[:start] + panel + markup[end:]


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("page", nargs="?", type=Path, default=PAGE)
    target = parser.parse_args().page
    with urlopen(Request(PROFILE, headers={"User-Agent": "Mozilla/5.0"}), timeout=20) as response:
        profile = response.read().decode(response.headers.get_content_charset() or "utf-8", errors="replace")
    total, annual = citation_data(unescape(profile))
    page = update_panel(target.read_text(), total, annual, date.today())
    temp = target.with_suffix(".html.tmp")
    temp.write_text(page)
    temp.replace(target)
    print(f"Google Scholar: {total:,} citations, {annual[0][0]}–{annual[-1][0]}.")
