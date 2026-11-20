"""Scoped Streamlit shell derived from the supplied design tokens."""
from pathlib import Path

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Nunito+Sans:wght@600;700;800;900&display=swap');
html,body,[class*="css"] {font-family:Inter,sans-serif;}
.stApp {background:linear-gradient(120deg,#EBDEF2,#F5EBF3);color:#30243C;}
[data-testid="stHeader"]{background:transparent;height:0;}
[data-testid="stToolbar"]{display:none;}
.stMainBlockContainer{max-width:1420px;padding:18px 20px 25px;margin:22px auto;background:radial-gradient(ellipse at 75% 0%,#755a7a60,transparent 60%),linear-gradient(120deg,#3E2F4F,#594361);border:1px solid #BDAFD1;border-radius:34px;box-shadow:0 22px 44px #3e2f4f44;min-height:970px;}
.stMainBlockContainer > div > [data-testid="stVerticalBlock"]{gap:10px;}
.stMainBlockContainer h1,.stMainBlockContainer h2,.stMainBlockContainer h3{font-family:'Nunito Sans',sans-serif;}
.lg-brand{font:900 20px 'Nunito Sans',sans-serif;color:white;display:flex;align-items:center;white-space:nowrap;}
.lg-greeting{color:#fff;font-size:11px;text-align:right;line-height:1.5;padding-top:5px;}
.lg-greeting small{color:#E6D9EA;font-size:10px;}
.lg-section-title{font:800 19px 'Nunito Sans',sans-serif;color:#30243C;margin-bottom:6px;}
.lg-eyebrow{font-size:10px;text-transform:uppercase;letter-spacing:1.5px;color:#7e638f;font-weight:800;}
.lg-subtle{font-size:11px;color:#776883;line-height:1.5;}
.lg-pill{display:inline-block;background:#DCCFF0;color:#3E2F4F;padding:4px 9px;border-radius:999px;font-size:10px;font-weight:700;}
.lg-pill.demo{background:#F3C9DD;color:#5c305d;}
.lg-kpi{min-height:103px;padding:12px 10px;border-radius:23px;background:linear-gradient(145deg,#faf7fc,#dccff0);box-shadow:0 7px 18px #24192f22;border:1px solid #ffffff90;}
.lg-kpi.k1{background:linear-gradient(140deg,#faf7fc,#f3c9dd);}.lg-kpi.k2{background:linear-gradient(140deg,#faf7fc,#f2e6d7);}
.lg-kpi.k3{background:linear-gradient(140deg,#faf7fc,#f3c9dd);}.lg-kpi.k4{background:linear-gradient(140deg,#faf7fc,#dccff0);}
.lg-kpi.k5{background:linear-gradient(140deg,#faf7fc,#e3efde);}.lg-kpi.k6{background:linear-gradient(140deg,#faf7fc,#bdafd1);}
.lg-kpi-label{font-size:11px;font-weight:700;display:flex;align-items:center;gap:4px;white-space:nowrap;}
.lg-kpi-value{font:900 25px 'Nunito Sans',sans-serif;line-height:1.45;letter-spacing:-.8px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.lg-kpi small{font-size:9px;color:#6e547d;}.lg-kpi svg{color:#9563C4;width:19px;height:19px;}
.lg-hero{min-height:250px;border-radius:26px;border:1px solid #ffffff50;display:grid;grid-template-columns:minmax(0,1fr) minmax(280px,.85fr);align-items:center;gap:28px;overflow:hidden;background:radial-gradient(ellipse at 60% 80%,#DCCFF0 0%,transparent 46%),linear-gradient(120deg,#715578,#BDAFD1);padding:26px 28px;color:white;box-shadow:0 12px 28px #24192f2a;}
.lg-hero-copy{position:relative;z-index:2;min-width:0;}.lg-hero h1{font:900 33px 'Nunito Sans',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;margin:8px 0 10px;color:white;line-height:1.05;}.lg-hero p{font-size:13px;line-height:1.6;margin:0;color:#fff4ff;}
.lg-progress{position:static;width:auto;min-width:0;padding:15px;border:1px solid #ffffff80;border-radius:24px;background:#f7eaf4c9;color:#30243C;backdrop-filter:blur(6px);}
.lg-progress strong{font-size:12px;}.lg-progress-track{height:10px;border-radius:10px;background:#3e2f4f18;margin:10px 0;overflow:hidden;}.lg-progress-track span{height:100%;display:block;background:linear-gradient(90deg,#D7B38C,#bb8396);border-radius:10px;}
.lg-step{display:flex;gap:8px;font-size:10px;align-items:center;padding:9px 0;border-bottom:1px solid #3e2f4f0a;}.lg-step i{width:18px;height:18px;border-radius:50%;background:#a8ddb5;color:#3e2f4f;display:flex;align-items:center;justify-content:center;font-style:normal;}.lg-step.pending i{background:#dccff0;}
.lg-hero-badge{margin-top:18px;}.lg-hero .lg-pill{background:#fff8;color:#30243C;}
.lg-chart-title{font:800 14px 'Nunito Sans',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#30243C;display:flex;align-items:center;gap:7px;}.lg-chart-title svg{width:18px;height:18px;color:#9563C4;}
.lg-empty{min-height:150px;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;color:#756383;font-size:12px;padding:12px;}.lg-empty strong{font-size:13px;margin-bottom:8px;}
.lg-health{font-size:10px;display:flex;justify-content:space-between;gap:6px;padding:5px 0;border-bottom:1px solid #3e2f4f0a;}.lg-health b{max-width:65%;text-align:right;overflow-wrap:anywhere;}
.lg-footer{font-size:10px;color:#e6d9ea;text-align:center;padding-top:10px;}
.lg-mode-banner{font-size:11px;color:#fff;background:#dccff01f;border:1px solid #dccff033;border-radius:12px;padding:6px 10px;}
.lg-compare-hero{min-height:150px;margin:4px 0 10px;padding:24px 28px;border-radius:26px;color:white;background:radial-gradient(circle at 82% 35%,#f3c9dd88 0,transparent 28%),linear-gradient(115deg,#6E547D,#A77EC0 64%,#D7B38C);box-shadow:0 12px 28px #30243c20}.lg-compare-hero h1{margin:4px 0 5px;font:900 34px 'Nunito Sans',sans-serif;letter-spacing:-1px}.lg-compare-hero p{margin:0 0 14px;font-size:12px}.lg-compare-hero small{font-size:9px;font-weight:800;letter-spacing:1.5px;color:#F2E6D7}.lg-compare-hero span{display:inline-block;margin-right:6px;padding:5px 9px;border-radius:999px;background:#fff9;color:#3E2F4F;font-size:9px;font-weight:800}
[class*="st-key-lg_card"],[class*="st-key-lg_chart"],.st-key-lg_trade,.st-key-lg_settings,.st-key-lg_filters{background:linear-gradient(140deg,#FAF7FC,#fcf1ee);border:1px solid #ffffff99;border-radius:24px;padding:14px;box-shadow:0 6px 16px #24192f18;}
.st-key-lg_trade{background:linear-gradient(115deg,#F2E6D7,#DCCFF0,#F3C9DD);padding:9px 14px;}
.st-key-lg_header [data-testid="stHorizontalBlock"]{align-items:center;}
.st-key-lg_header .stButton button{background:transparent;border:0;color:white;font-size:11px;padding:7px 5px;min-height:32px;white-space:nowrap;}
.st-key-lg_header .stButton button[kind="primary"]{background:#F2E6D7;color:#30243C;border-radius:999px;}
.stMainBlockContainer .stButton button,.stMainBlockContainer .stDownloadButton button{font-family:Inter,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;font-size:12px;border-radius:14px;}
[class*="st-key-lg_card"] .stButton button{background:linear-gradient(115deg,#faf7fc,#e6d5f0);border:1px solid #dccff0;color:#3e2f4f;border-radius:999px;}
.stMainBlockContainer .stButton button[kind="primary"]{background:#9563c4;border-color:#9563c4;color:white;}
.stMainBlockContainer label,.stMainBlockContainer [data-testid="stMarkdownContainer"]{font-family:Inter,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;}
.stMainBlockContainer [data-testid="stWidgetLabel"] p{font-size:11px;}
.stMainBlockContainer [data-baseweb="select"] > div,.stMainBlockContainer [data-baseweb="input"]{border-radius:12px;background:#FAF7FC;color:#30243C;}
.stMainBlockContainer .stSegmentedControl button{font-size:10px;}
.st-key-lg_trade [data-testid="stMetricValue"]{font-size:17px;font-weight:800;}.st-key-lg_trade [data-testid="stMetricLabel"]{font-size:10px;}
.st-key-lg_mode .stSegmentedControl{margin-top:0;}.stMainBlockContainer [data-testid="stExpander"]{border:1px solid #dccff030;border-radius:12px;background:#FAF7FC;}
.stMainBlockContainer [data-testid="stPopover"] > button{min-height:20px;height:20px;padding:0;border:0;background:transparent;font-size:12px;}
.stMainBlockContainer [data-testid="stPopover"] > button > svg{display:none;}
.st-key-lg_header .stButton button[kind="primary"]{background:#F2E6D7;border-color:#F2E6D7;color:#30243C;}
.stMainBlockContainer{font-family:Inter,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;height:auto!important;}
.stMainBlockContainer [data-testid="stPopoverButton"]{min-height:20px;height:20px;padding:0 3px;border:0;background:transparent;font-size:12px;}
.stMainBlockContainer [data-testid="stPopoverButton"] [data-testid="stIconMaterial"]{display:none;}
.st-key-lg_filters [data-testid="stExpander"]{border:0;}
.lg-nav-text{color:#fff;font-size:13px;}
.stMainBlockContainer [data-testid="stVerticalBlock"]{gap:10px;}
.stMainBlockContainer [data-testid="stHorizontalBlock"]>[data-testid="stColumn"]{min-width:0;}
.st-key-lg_mobile_nav{display:none;}
@media(max-width:1100px){.stMainBlockContainer{margin:8px auto;padding:14px;border-radius:24px;}.lg-brand{font-size:16px;}.lg-kpi-value{font-size:21px;}.lg-hero h1{font-size:28px;}.lg-hero{grid-template-columns:minmax(0,1fr) minmax(250px,.9fr);gap:16px;}}
@media(min-width:761px) and (max-width:1100px){
 .stMainBlockContainer [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"] > .st-key-lg_card_quick){display:block;}
 .stMainBlockContainer [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"] > .st-key-lg_card_quick) > [data-testid="stColumn"]{width:100%;flex:1 1 100%;}
}
@media(max-width:760px){.stMainBlockContainer{margin:0;padding:12px;border-radius:0;}.lg-greeting{display:none;}.lg-hero{min-height:0;grid-template-columns:1fr;padding:20px;}.lg-progress{width:auto;padding:10px;}.lg-step{display:inline-flex;width:48%;padding:5px 0;}.lg-hero h1{font-size:30px;}.lg-kpi{min-height:90px;}.lg-kpi-value{font-size:24px;}.lg-brand{font-size:20px;}}
@media(max-width:760px){.st-key-lg_header [data-testid="stColumn"]:nth-child(n+2){display:none;}.st-key-lg_mobile_nav{display:block;}.st-key-lg_kpis [data-testid="stHorizontalBlock"]{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;}.st-key-lg_kpis [data-testid="stColumn"]{width:100%;min-width:0;}.lg-progress .lg-step{font-size:10px;}.lg-hero p{font-size:12px;}}
@media(max-width:760px){
 .stMainBlockContainer [data-testid="stHorizontalBlock"]{display:block;}
 .stMainBlockContainer [data-testid="stColumn"]{width:100%!important;flex:1 1 100%!important;min-width:0!important;}
 .st-key-lg_kpis [data-testid="stHorizontalBlock"]{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));}
 [class*="st-key-lg_chart"] [data-testid="stHorizontalBlock"]{display:flex;flex-direction:row;}
 [class*="st-key-lg_chart"] [data-testid="stColumn"]:first-child{flex:8!important;}
 [class*="st-key-lg_chart"] [data-testid="stColumn"]:last-child{flex:1!important;}
}
"""

EXECUTION_CSS = r"""
/* Execution Lab locked layout. Every rule is scoped to the dedicated shell. */
.stApp:has(.st-key-lg_exec_shell){background:linear-gradient(135deg,#FCF9FF,#F2EAF7);}
.stApp:has(.st-key-lg_exec_shell) [data-testid="stHeader"]{display:none;}
.stMainBlockContainer:has(.st-key-lg_exec_shell){max-width:none;width:100%;padding:0;margin:0;background:transparent;border:0;border-radius:0;box-shadow:none;min-height:100vh;overflow:visible;}
.stMainBlockContainer:has(.st-key-lg_exec_shell) > div{padding:0!important;}
.st-key-lg_exec_shell{width:100%;min-height:100vh;}
.st-key-lg_exec_shell > div > [data-testid="stVerticalBlock"]{gap:0!important;}
.st-key-lg_exec_shell > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]{gap:0!important;align-items:stretch;}
.st-key-lg_exec_shell > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child{flex:0 0 228px!important;width:228px!important;min-width:228px!important;background:linear-gradient(180deg,#3E2F4F,#5C4368);}
.st-key-lg_exec_shell > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child{flex:1 1 auto!important;width:calc(100% - 228px)!important;min-width:0!important;}
.st-key-lg_exec_sidebar{position:sticky;top:0;min-height:100vh;padding:25px 18px;color:white;overflow:hidden;background:linear-gradient(180deg,#3E2F4F,#5C4368);box-shadow:8px 0 25px #30243c18;}
.lg-exec-brand{display:flex;align-items:center;gap:8px;margin-bottom:32px;color:white;}
.lg-exec-brand img{width:46px;height:46px;object-fit:contain;filter:drop-shadow(0 5px 8px #24192f66);}
.lg-exec-brand strong{display:block;font:900 18px 'Nunito Sans',sans-serif;letter-spacing:-.5px;}
.lg-exec-brand span{display:block;margin-top:2px;font-size:8.5px;line-height:1.35;color:#E8DDF0;}
.st-key-lg_exec_sidebar .stButton button{min-height:48px;margin:3px 0;padding:0 15px;background:transparent;border:0;border-radius:18px;color:#F7F0FA;justify-content:flex-start;font-size:13px;font-weight:650;}
.st-key-lg_exec_sidebar .stButton button:hover{background:#ffffff12;color:white;}
.st-key-lg_exec_sidebar .stButton button[kind="primary"]{background:linear-gradient(135deg,#F3EAF8,#DCCFF0);border:1px solid #ffffff80;color:#30243C;box-shadow:0 8px 20px #24192f4a;}
.lg-exec-clouds{position:absolute;left:0;right:0;bottom:30px;height:90px;opacity:.18;}
.lg-exec-clouds i{position:absolute;width:120px;height:45px;border-radius:999px;background:#F2E6D7;}
.lg-exec-clouds i:nth-child(1){left:-45px;bottom:10px}.lg-exec-clouds i:nth-child(2){left:65px;bottom:-12px}.lg-exec-clouds i:nth-child(3){right:-65px;bottom:35px}
.st-key-lg_exec_topbar{height:66px;padding:11px 14px;background:#FFFDFE;border-bottom:1px solid rgba(62,47,79,.09);box-shadow:0 3px 14px #30243c0c;position:sticky;top:0;z-index:30;}
.st-key-lg_exec_topbar [data-testid="stHorizontalBlock"]{align-items:center;gap:9px;}
.st-key-lg_exec_topbar .stSegmentedControl{background:#F4EDF7;border-radius:999px;padding:3px;}
.st-key-lg_exec_topbar .stSegmentedControl button{min-height:34px;border-radius:999px;font-size:10px;font-weight:800;}
.st-key-lg_exec_topbar .stSegmentedControl button[aria-pressed="true"]{background:#9563C4;color:white;}
.st-key-lg_exec_topbar [data-baseweb="select"]>div,.st-key-lg_exec_topbar [data-baseweb="input"]{min-height:40px;background:#FAF7FC;border:1px solid #E8DEED;border-radius:13px;}
.lg-exec-date{height:40px;display:flex;align-items:center;padding:0 11px;background:#FAF7FC;border:1px solid #E8DEED;border-radius:13px;font-size:11px;font-weight:700;white-space:nowrap;}
.lg-exec-greeting{height:40px;display:flex;flex-direction:column;justify-content:center;color:#30243C;line-height:1.25;white-space:nowrap}.lg-exec-greeting b{font-size:12px}.lg-exec-greeting span{font-size:9px;color:#7D6C88;}
.st-key-lg_exec_topbar .stButton button{height:40px;min-height:40px;border:1px solid #E8DEED;background:#FAF7FC;color:#3E2F4F;border-radius:13px;}
.lg-execution-lab{height:0;}
.st-key-lg_exec_shell .stFragment{padding:7px 12px 26px 14px;}
.st-key-lg_exec_shell .stFragment > div > [data-testid="stVerticalBlock"]{gap:9px;}
.st-key-lg_exec_shell .stFragment > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]{gap:14px;align-items:flex-start;}
.st-key-lg_exec_shell .stFragment > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child{flex:1 1 986px!important;min-width:0!important;}
.st-key-lg_exec_shell .stFragment > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child{flex:0 0 min(29.4%,415px)!important;min-width:300px!important;}
.lg-exec-hero{height:174px;position:relative;overflow:hidden;border-radius:26px;padding:25px 28px;color:white;background:radial-gradient(circle at 82% 80%,#EADBF1 0,transparent 27%),linear-gradient(115deg,#715A80,#A986BE 58%,#BDAFD1);box-shadow:0 12px 30px #30243c20;border:1px solid #ffffff80;}
.lg-exec-hero-copy{position:relative;z-index:3;width:66%;}.lg-exec-hero h1{margin:0 0 5px;color:white;font:900 42px/1.02 'Nunito Sans',sans-serif;letter-spacing:-1.5px;}.lg-exec-hero p{margin:0;color:#FFF8FF;font-size:13px;line-height:1.45;}.lg-exec-hero p b{font-size:14px;}.lg-exec-hero img{position:absolute;right:3%;bottom:-8px;width:41%;height:188px;object-fit:contain;object-position:center bottom;z-index:2;filter:drop-shadow(0 10px 13px #3e2f4f40);}.lg-exec-tags{display:flex;gap:6px;margin-top:13px}.lg-exec-tags span{padding:5px 8px;border-radius:999px;background:#fff8;border:1px solid #fff8;color:#3E2F4F;font-size:9px;font-weight:800;backdrop-filter:blur(4px);white-space:nowrap}.lg-exec-hero-copy>small{display:block;margin-top:8px;font-size:9px;color:#FAF2FC;}.lg-exec-hero .cloud{position:absolute;border-radius:999px;background:#FFF8;filter:blur(.2px)}.lg-exec-hero .c1{width:110px;height:34px;right:3%;top:18px}.lg-exec-hero .c2{width:75px;height:25px;right:40%;bottom:8px}
.st-key-lg_exec_controls{min-height:62px;margin-top:9px;padding:9px 12px;background:linear-gradient(105deg,#FFFDFE,#FCF4FB);border:1px solid var(--lg-border);border-radius:20px;box-shadow:0 7px 20px #30243c13;}
.st-key-lg_exec_controls [data-testid="stHorizontalBlock"]{align-items:center;gap:8px}.lg-exec-control-title{font-size:14px;color:#3E2F4F;padding-left:4px;white-space:nowrap}.st-key-lg_exec_controls [data-baseweb="select"]>div,.st-key-lg_exec_controls [data-baseweb="input"]{min-height:42px;background:white;border-radius:13px;border-color:#E6D8EC}.st-key-lg_exec_controls .stSegmentedControl{background:#EFE6F3;border-radius:13px;padding:3px}.st-key-lg_exec_controls .stSegmentedControl button{min-height:36px;border-radius:10px;font-size:11px;font-weight:800}.st-key-lg_exec_controls .stSegmentedControl button[aria-pressed="true"]{background:#9563C4;color:white}.st-key-lg_exec_controls .stButton button{height:42px;min-height:42px;border-radius:13px;background:linear-gradient(135deg,#A26BD0,#8753B3);border:0;color:white;font-weight:800;}
.lg-exec-results{min-height:68px;margin-top:9px;display:grid;grid-template-columns:1.25fr repeat(5,1fr);align-items:stretch;background:#FEF9FE;border:1px solid var(--lg-border);border-radius:20px;box-shadow:0 7px 20px #30243c12;overflow:hidden}.lg-exec-results header{padding:12px 14px;display:flex;flex-direction:column;justify-content:center;color:#3E2F4F;font-size:13px;background:#F4EAF7}.lg-exec-results header small{font-size:8px;color:#897893;margin-top:4px}.lg-exec-results>div{display:flex;flex-direction:column;justify-content:center;padding:8px 10px;border-left:1px solid #3e2f4f12}.lg-exec-results span{font-size:9px;color:#766781;white-space:nowrap}.lg-exec-results b{margin-top:4px;font:800 18px 'Nunito Sans',sans-serif;font-variant-numeric:tabular-nums;white-space:nowrap}.lg-exec-results>div:last-child b{color:#4E9A64}
.lg-exec-insight{min-height:84px;margin-top:9px;display:grid;grid-template-columns:48px 1fr 210px;align-items:center;gap:12px;padding:13px 16px;border:1px solid #F3C9DD;border-radius:22px;background:linear-gradient(115deg,#FFF2F7,#F8E9F0 62%,#F2E6D7);box-shadow:0 8px 20px #30243c10}.lg-exec-insight.warning{background:linear-gradient(115deg,#FFF0F3,#F7E1E7,#F2E6D7)}.lg-exec-insight.blocked{background:linear-gradient(115deg,#FFF0F0,#F6E6E8,#F2E6D7)}.lg-exec-insight .bulb{width:43px;height:43px;border-radius:50%;display:grid;place-items:center;background:#FFF7D7;color:#9563C4;font-size:21px;box-shadow:0 5px 12px #30243c15}.lg-exec-insight p{margin:0;font-size:11.5px;line-height:1.45;color:#493856}.lg-exec-insight aside{display:flex;flex-direction:column;gap:4px}.lg-exec-insight aside span{font-size:9.5px;font-weight:700;color:#4C7657;background:#ffffff9c;border-radius:999px;padding:4px 7px;white-space:nowrap}
.st-key-lg_exec_shell [class*="st-key-lg_chart_exec_"]{height:174px;margin-top:9px;padding:10px 12px 5px;background:#FFF9FA;border:1px solid var(--lg-border);border-radius:23px;box-shadow:0 8px 22px #30243c13;overflow:hidden}.st-key-lg_exec_shell .st-key-lg_chart_exec_spread,.st-key-lg_exec_shell .st-key-lg_chart_exec_obi{height:151px}.st-key-lg_exec_shell [class*="st-key-lg_chart_exec_"] [data-testid="stPlotlyChart"]{height:128px}.st-key-lg_exec_shell .st-key-lg_chart_exec_spread [data-testid="stPlotlyChart"],.st-key-lg_exec_shell .st-key-lg_chart_exec_obi [data-testid="stPlotlyChart"]{height:108px}.st-key-lg_exec_shell [class*="st-key-lg_chart_exec_"] iframe{height:100%!important}.st-key-lg_exec_shell [class*="st-key-lg_chart_exec_"] [data-testid="stHorizontalBlock"]{min-height:21px}.st-key-lg_exec_shell .lg-chart-title{font-size:12px}.st-key-lg_exec_shell .lg-empty{min-height:112px;font-size:10px}
.st-key-lg_exec_shell [data-testid="stExpander"]{margin-top:9px;background:#FFF9FA;border:1px solid var(--lg-border);border-radius:20px;box-shadow:0 8px 20px #30243c10}.st-key-lg_exec_shell [data-testid="stExpander"] summary{min-height:62px;font-weight:800;color:#3E2F4F}.st-key-lg_exec_shell [data-testid="stExpander"] p{font-size:11px;line-height:1.5}
.st-key-lg_exec_watchlist,.st-key-lg_exec_session,.st-key-lg_exec_trust{padding:14px 15px;background:linear-gradient(145deg,#FFFDFE,#FFF5F7);border:1px solid var(--lg-border);border-radius:23px;box-shadow:0 9px 25px #30243c14;overflow:hidden}.st-key-lg_exec_watchlist{min-height:285px}.st-key-lg_exec_session{min-height:225px;margin-top:10px}.st-key-lg_exec_trust{min-height:160px;margin-top:10px}.lg-exec-rail-title{font:800 16px 'Nunito Sans',sans-serif;color:#30243C}.lg-exec-rail-title em{float:right;padding:3px 7px;border-radius:999px;background:#E4F2E4;color:#4E805A;font:800 8px Inter,sans-serif;text-transform:uppercase}.st-key-lg_exec_watchlist .stCaptionContainer,.st-key-lg_exec_session .stCaptionContainer{font-size:9px;color:#84758D}.st-key-lg_exec_watchlist [data-testid="stHorizontalBlock"]{align-items:center;gap:5px}.st-key-lg_exec_watchlist .stButton button{min-height:34px;border:0;background:#F1E7F5;border-radius:12px;color:#3E2F4F;font-size:11px;font-weight:800}.st-key-lg_exec_watchlist [data-testid="stHorizontalBlock"]:first-child .stButton button{background:transparent;font-size:9px;color:#9563C4}.lg-exec-watch-price{font-size:11px;font-variant-numeric:tabular-nums}.lg-exec-watch-state{display:block;font-size:8px;font-weight:800;color:#4E805A}.lg-exec-watch-state+small{display:block;font-size:7px;color:#8A7A91;white-space:nowrap}.lg-exec-row{display:flex;align-items:center;justify-content:space-between;min-height:31px;border-bottom:1px solid #3e2f4f10;font-size:10px}.lg-exec-row span{color:#786981}.lg-exec-row b{font-size:10px;text-align:right;font-variant-numeric:tabular-nums}.lg-exec-check{margin:5px 0;padding:5px 7px;border-radius:9px;font-size:9px;font-weight:700}.lg-exec-check.pass{background:#E8F4E9;color:#477653}.lg-exec-check.fail{background:#FDE9EE;color:#A64E66}.st-key-lg_exec_trust .stButton button{min-height:31px;margin-top:4px;background:#F0E6F4;border:0;border-radius:11px;color:#3E2F4F;font-size:9px;font-weight:800}
@media(max-width:1439px){.st-key-lg_exec_shell > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child{flex-basis:190px!important;width:190px!important;min-width:190px!important}.st-key-lg_exec_shell .stFragment > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child{min-width:280px!important}.lg-exec-brand span{display:none}.lg-exec-tags span{font-size:8px}.lg-exec-results b{font-size:15px}}
@media(max-width:1099px){.st-key-lg_exec_shell .stFragment > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type{display:block}.st-key-lg_exec_shell .stFragment > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]{width:100%!important;min-width:0!important}.st-key-lg_exec_watchlist{margin-top:12px}.lg-exec-hero-copy{width:70%}.lg-exec-hero img{width:36%}.lg-exec-results{grid-template-columns:1fr repeat(3,1fr)}}
@media(max-width:760px){.st-key-lg_exec_shell > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]{display:block}.st-key-lg_exec_shell > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child{display:none}.st-key-lg_exec_shell > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child{width:100%!important}.st-key-lg_exec_topbar{height:auto;position:relative}.st-key-lg_exec_topbar [data-testid="stHorizontalBlock"]{display:grid!important;grid-template-columns:1fr 1fr}.lg-exec-hero{height:255px}.lg-exec-hero-copy{width:100%}.lg-exec-hero h1{font-size:34px}.lg-exec-hero img{opacity:.32;width:65%;height:175px}.lg-exec-tags{flex-wrap:wrap}.lg-exec-results{grid-template-columns:repeat(2,1fr)}.lg-exec-results header{grid-column:1/-1}.lg-exec-insight{grid-template-columns:40px 1fr}.lg-exec-insight aside{grid-column:1/-1}.st-key-lg_exec_shell [data-testid="stHorizontalBlock"]{display:block}.st-key-lg_exec_shell [data-testid="stColumn"]{width:100%!important;min-width:0!important}.st-key-lg_exec_shell [class*="st-key-lg_chart_exec_"]{height:210px}}
/* Pixel-alignment refinements after the 1672×941 browser render. */
@media(min-width:1100px){
 .lg-exec-hero h1{font-size:39px;line-height:1;margin-bottom:3px}.lg-exec-hero p{font-size:12.5px;line-height:1.35}.lg-exec-hero p b{font-size:13.5px}.lg-exec-tags{margin-top:8px}.lg-exec-tags span{padding:4px 8px}.lg-exec-hero-copy>small{margin-top:4px;font-size:8.5px}
 .lg-exec-results{height:70px;min-height:0;margin-top:0}.lg-exec-results header{padding:8px 14px}.lg-exec-results header small{margin-top:2px}.lg-exec-results>div{padding:5px 10px}.lg-exec-results b{margin-top:2px}
 .lg-exec-insight{height:88px;min-height:0;margin-top:0;padding:10px 16px;overflow:hidden}.lg-exec-insight p{font-size:11px;line-height:1.4}.lg-exec-insight aside{gap:3px}.lg-exec-insight aside span{font-size:9px;padding:3px 7px}
 .st-key-lg_exec_shell [class*="st-key-lg_chart_exec_"]{margin-top:0}
 .st-key-lg_exec_shell .st-key-lg_chart_exec_depth,.st-key-lg_exec_shell .st-key-lg_chart_exec_sweep,.st-key-lg_exec_shell .st-key-lg_chart_exec_coverage{height:174px!important;min-height:174px!important;max-height:174px!important;box-sizing:border-box!important}
 .st-key-lg_exec_shell .st-key-lg_chart_exec_spread,.st-key-lg_exec_shell .st-key-lg_chart_exec_obi{height:152px!important;min-height:152px!important;max-height:152px!important;box-sizing:border-box!important}
 .st-key-lg_exec_shell [data-testid="stExpander"]{margin-top:0}
 .st-key-lg_exec_watchlist{height:285px;min-height:0}.st-key-lg_exec_session{height:225px;min-height:0;margin-top:0}.st-key-lg_exec_trust{height:180px;min-height:0;margin-top:0}
 .st-key-lg_exec_watchlist [data-testid="stHorizontalBlock"]{gap:4px}.st-key-lg_exec_watchlist .stButton button{min-height:31px}
 .lg-exec-check{margin:2px 0;padding:3px 7px;border-radius:8px;font-size:8.5px}.st-key-lg_exec_trust .stButton button{min-height:27px;margin-top:2px}
}
"""


def inject(st, density="Thoải mái"):
    root = Path(__file__).resolve().parents[2]
    legacy_tokens = root / "docs/ui_reference/design_tokens.css"
    tokens = legacy_tokens.read_text() if legacy_tokens.exists() else ""
    execution_tokens = (root / "docs/ui_reference/design_tokens_execution_lab.css").read_text()
    st.markdown(f"<style>{tokens}\n{execution_tokens}\n{CSS}\n{EXECUTION_CSS}</style>", unsafe_allow_html=True)
    if density == "Gọn":
        st.markdown("<style>.stMainBlockContainer [data-testid='stVerticalBlock']{gap:6px}.lg-kpi{padding:8px;min-height:88px}</style>",unsafe_allow_html=True)
