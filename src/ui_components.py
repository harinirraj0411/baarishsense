"""Presentation layer: CSS theme and reusable HTML components for Streamlit."""
from __future__ import annotations

import html

import streamlit as st

from . import config

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600&family=Sora:wght@300;400;600&display=swap');
:root{
  --bg:#060A12; --panel:rgba(13,22,40,.62); --panel-solid:#0B1424; --line:rgba(131,160,200,.16);
  --line-strong:rgba(45,212,191,.45); --text:#E8EEF7; --muted:#8393AB; --teal:#2DD4BF; --cyan:#38BDF8; --amber:#F2B04C;
}
html, body, .stApp,
.stApp p, .stApp h1, .stApp h2, .stApp h3, .stApp h4,
.stApp label, .stApp button, .stApp input, .stApp textarea,
.stApp li, .stApp td, .stApp th {
  font-family:'IBM Plex Sans','Segoe UI',system-ui,sans-serif;
}
span[data-testid="stIconMaterial"],
[data-testid="stSidebarCollapsedControl"] span,
[data-testid="stExpandSidebarButton"] span,
[data-testid="stSidebarCollapseButton"] span,
.material-symbols-rounded,
.material-icons {
  font-family:"Material Symbols Rounded","Material Symbols Outlined","Material Icons" !important;
}
.stApp{
  background:
    radial-gradient(1200px 520px at 78% -10%, rgba(45,212,191,.08), transparent 60%),
    linear-gradient(rgba(131,160,200,.035) 1px, transparent 1px) 0 0/48px 48px,
    linear-gradient(90deg, rgba(131,160,200,.035) 1px, transparent 1px) 0 0/48px 48px,
    var(--bg);
}

#MainMenu,
footer,




header[data-testid="stHeader"] {
    background: transparent !important;
}

[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarCollapsedControl"] {
    visibility: visible !important;
    display: flex !important;
    opacity: 1 !important;
    pointer-events: auto !important;
}


/* header */
.vn-header{display:flex; justify-content:space-between; align-items:flex-end; gap:1rem; flex-wrap:wrap;
  padding:0 0 1.1rem; border-bottom:1px solid var(--line); margin-bottom:1.2rem;}
.vn-brand{font-family:'Sora',sans-serif; font-weight:600; font-size:2rem; letter-spacing:.28em; line-height:1; color:var(--text);}
.vn-tag{margin-top:.55rem; font-size:.78rem; letter-spacing:.2em; color:var(--teal); font-weight:500;}
.vn-meta{margin-top:.3rem; font-size:.7rem; letter-spacing:.16em; color:var(--muted);}
.vn-status{display:inline-flex; align-items:center; gap:.55rem; padding:.4rem .8rem; border:1px solid var(--line);
  border-radius:999px; font-size:.7rem; letter-spacing:.16em; color:var(--text); background:var(--panel);}
.vn-dot{width:8px; height:8px; border-radius:50%; background:var(--teal); box-shadow:0 0 0 0 rgba(45,212,191,.6); animation:vnpulse 2.4s infinite;}
@keyframes vnpulse{0%{box-shadow:0 0 0 0 rgba(45,212,191,.55)}70%{box-shadow:0 0 0 8px rgba(45,212,191,0)}100%{box-shadow:0 0 0 0 rgba(45,212,191,0)}}

/* section titles */
.vn-section{margin:1.8rem 0 .7rem;}
.vn-section h3{margin:0; font-size:.82rem; font-weight:600; letter-spacing:.2em; color:var(--text); text-transform:uppercase;}
.vn-section p{margin:.3rem 0 0; font-size:.86rem; color:var(--muted); max-width:78ch;}
.vn-section:before{content:""; display:block; width:28px; height:2px; background:var(--teal); margin-bottom:.6rem;}

/* KPI */
.vn-kpis{display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr)); gap:.8rem; margin:.4rem 0 .4rem;}
.vn-kpi{background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:.95rem 1.05rem;
  backdrop-filter:blur(10px); box-shadow:0 8px 24px rgba(0,0,0,.28); transition:border-color .2s, transform .2s;}
.vn-kpi:hover{border-color:var(--line-strong); transform:translateY(-2px);}
.vn-kpi .l{font-size:.68rem; letter-spacing:.16em; color:var(--muted); text-transform:uppercase;}
.vn-kpi .v{font-family:'Sora',sans-serif; font-weight:400; font-size:1.7rem; margin-top:.35rem; color:var(--text); line-height:1.15; overflow-wrap:anywhere;}
.vn-kpi .u{font-size:.8rem; color:var(--muted); margin-left:.25rem; font-family:'IBM Plex Sans',sans-serif;}
.vn-kpi .s{font-size:.78rem; color:var(--muted); margin-top:.3rem;}
.vn-kpi.hot .v{color:var(--amber);}

/* location banner */
.vn-loc{background:var(--panel); border:1px solid var(--line); border-left:3px solid var(--teal); border-radius:10px;
  padding:1rem 1.3rem; margin:.2rem 0 1rem;}
.vn-loc .n{font-family:'Sora',sans-serif; font-size:1.6rem; letter-spacing:.12em; text-transform:uppercase;}
.vn-loc .st{color:var(--muted); font-size:.9rem; margin-top:.15rem;}
.vn-loc .m{margin-top:.7rem; font-size:.85rem; color:var(--text);}
.vn-loc .m span{color:var(--muted);}

/* chips */
.vn-chips{display:flex; flex-wrap:wrap; gap:.4rem; margin:.2rem 0 1rem;}
.vn-chip{font-size:.72rem; padding:.22rem .65rem; border-radius:999px; border:1px solid var(--line-strong);
  color:var(--teal); background:rgba(45,212,191,.07); letter-spacing:.04em;}
.vn-chip.idle{border-color:var(--line); color:var(--muted); background:transparent;}

/* summary / explain / states */
.vn-summary{background:linear-gradient(180deg,rgba(45,212,191,.07),rgba(13,22,40,.6)); border:1px solid var(--line);
  border-radius:10px; padding:1.1rem 1.3rem; margin-top:1.4rem;}
.vn-summary h4{margin:0 0 .6rem; font-size:.76rem; letter-spacing:.2em; font-weight:600; color:var(--teal); text-transform:uppercase;}
.vn-summary p{margin:.35rem 0; font-size:.92rem; line-height:1.6; color:var(--text); max-width:90ch;}
.vn-explain{background:var(--panel); border:1px solid rgba(242,176,76,.35); border-radius:10px; padding:1.1rem 1.3rem;}
.vn-explain .t{font-size:.76rem; letter-spacing:.2em; color:var(--amber); font-weight:600; text-transform:uppercase; margin-bottom:.8rem;}
.vn-explain dl{display:grid; grid-template-columns:max-content 1fr; gap:.45rem 1.4rem; margin:0;}
.vn-explain dt{color:var(--muted); font-size:.82rem;} .vn-explain dd{margin:0; font-size:.95rem;}
.vn-explain .r{margin-top:.9rem; padding-top:.8rem; border-top:1px solid var(--line); font-size:.9rem; color:var(--text); line-height:1.55;}
.vn-state{border:1px dashed var(--line-strong); border-radius:12px; padding:2rem 1.6rem; background:var(--panel); text-align:left; max-width:760px; margin:1.5rem 0;}
.vn-state h4{margin:0 0 .6rem; letter-spacing:.2em; font-size:.9rem; color:var(--text);}
.vn-state p, .vn-state li{color:var(--muted); font-size:.92rem; line-height:1.6;}
.vn-state code{color:var(--teal); background:rgba(45,212,191,.08); padding:.1rem .4rem; border-radius:4px;}
.vn-note{font-size:.78rem; color:var(--muted); margin:.3rem 0 .8rem;}
.vn-grid{display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:.6rem .9rem;}
.vn-grid .c{background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:.7rem .9rem;}
.vn-grid .c .k{font-size:.68rem; letter-spacing:.14em; color:var(--muted); text-transform:uppercase;}
.vn-grid .c .v{font-size:.95rem; margin-top:.2rem; overflow-wrap:anywhere;}
.vn-grid .c .v.warn{color:var(--amber);}
.vn-footer{margin-top:3rem; padding-top:1rem; border-top:1px solid var(--line); font-size:.72rem; letter-spacing:.14em; color:var(--muted); text-align:center;}

/* widgets */
div[data-baseweb="select"] > div, .stDateInput > div > div, .stNumberInput input{background:rgba(11,20,36,.85)!important; border-color:var(--line)!important;}
div[data-baseweb="select"] > div:hover{border-color:var(--line-strong)!important;}
.stButton>button, .stDownloadButton>button{border:1px solid var(--line-strong); background:rgba(45,212,191,.07); color:var(--text); border-radius:8px; transition:background .2s;}
.stButton>button:hover, .stDownloadButton>button:hover{background:rgba(45,212,191,.18); border-color:var(--teal); color:var(--text);}
[data-testid="stDataFrame"]{border:1px solid var(--line); border-radius:10px; overflow:hidden;}
:focus-visible{outline:2px solid var(--teal)!important; outline-offset:2px;}
@media (prefers-reduced-motion: reduce){ .vn-dot{animation:none} .vn-kpi{transition:none} }
@media (max-width:900px){ .vn-brand{font-size:1.5rem; letter-spacing:.2em} }
</style>
"""


def esc(x) -> str:
    return html.escape(str(x))


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def render_header() -> None:
    st.markdown(
        f"""<div class="vn-header"><div>
        <div class="vn-brand">{esc(config.APP_NAME)}</div>
        <div class="vn-tag">{esc(config.APP_TAGLINE)}</div>
        <div class="vn-meta">{esc(config.APP_META)}</div></div>
        <div class="vn-status" role="status"><span class="vn-dot"></span>ANALYTICS ONLINE</div></div>""",
        unsafe_allow_html=True)


def render_footer() -> None:
    st.markdown(f'<div class="vn-footer">{esc(config.FOOTER_TEXT)}</div>', unsafe_allow_html=True)


def section_title(title: str, subtitle: str = "") -> None:
    sub = f"<p>{esc(subtitle)}</p>" if subtitle else ""
    st.markdown(f'<div class="vn-section"><h3>{esc(title)}</h3>{sub}</div>', unsafe_allow_html=True)


def kpi_row(items: list[dict]) -> None:
    """items: {label, value, unit?, sub?, hot?}"""
    cards = []
    for it in items:
        unit = f'<span class="u">{esc(it["unit"])}</span>' if it.get("unit") else ""
        sub = f'<div class="s">{esc(it["sub"])}</div>' if it.get("sub") else ""
        cls = "vn-kpi hot" if it.get("hot") else "vn-kpi"
        cards.append(f'<div class="{cls}"><div class="l">{esc(it["label"])}</div><div class="v">{esc(it["value"])}{unit}</div>{sub}</div>')
    st.markdown(f'<div class="vn-kpis">{"".join(cards)}</div>', unsafe_allow_html=True)


def location_banner(name: str, state: str | None, period: str, extra: str = "") -> None:
    st_html = f'<div class="st">{esc(state)}</div>' if state else ""
    ex = f'<div class="m"><span>{esc(extra)}</span></div>' if extra else ""
    st.markdown(f'<div class="vn-loc"><div class="n">{esc(name)}</div>{st_html}'
                f'<div class="m">Rainfall Analysis<br><span>Selected Period: {esc(period)}</span></div>{ex}</div>',
                unsafe_allow_html=True)


def filter_chips(active: list[str]) -> None:
    chips = "".join(f'<span class="vn-chip">{esc(a)}</span>' for a in active) if active \
        else '<span class="vn-chip idle">No refinements - full dataset period</span>'
    st.markdown(f'<div class="vn-chips" aria-label="Active filters">{chips}</div>', unsafe_allow_html=True)


def summary_box(lines: list[str], title: str = "ANALYTICAL SUMMARY") -> None:
    paras = "".join(f"<p>{esc(l)}</p>" for l in lines)
    st.markdown(f'<div class="vn-summary"><h4>{esc(title)}</h4>{paras}</div>', unsafe_allow_html=True)


def explain_card(info: dict, title: str = "HIGH-RAINFALL OBSERVATION") -> None:
    rows = [("Date / region", info.get("where", "")), ("Rainfall", info["rainfall"]), ("Selected threshold", info["threshold"]),
            ("Difference", info["difference"]), ("Relative level", info["relative"]), ("Position", info["percentile"])]
    dl = "".join(f"<dt>{esc(k)}</dt><dd>{esc(v)}</dd>" for k, v in rows if v)
    st.markdown(f'<div class="vn-explain"><div class="t">{esc(title)}</div><dl>{dl}</dl>'
                f'<div class="r"><b>Reason</b><br>{esc(info["reason"])}</div></div>', unsafe_allow_html=True)


def state_card(title: str, body_html: str) -> None:
    st.markdown(f'<div class="vn-state"><h4>{esc(title)}</h4>{body_html}</div>', unsafe_allow_html=True)


def empty_state() -> None:
    state_card("NO OBSERVATIONS FOUND", "<p>Try expanding the selected date range<br>or changing the location.</p>")


def note(text: str) -> None:
    st.markdown(f'<div class="vn-note">{esc(text)}</div>', unsafe_allow_html=True)


def info_grid(items: list[tuple[str, str, bool]]) -> None:
    """items: (key, value, warn)"""
    cells = "".join(f'<div class="c"><div class="k">{esc(k)}</div><div class="v{" warn" if w else ""}">{esc(v)}</div></div>'
                    for k, v, w in items)
    st.markdown(f'<div class="vn-grid">{cells}</div>', unsafe_allow_html=True)
