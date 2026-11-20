#!/bin/sh
# Persistent macOS launchd entrypoint for the 19/11/2026 morning capture.
set -eu
project_root="/Users/thylnh.iu/Documents/Neo-LiquidityGuard"
cd "$project_root"

symbols="ACB,BID,BSR,CTG,FPT,GAS,GVR,HDB,HPG,LPB,MBB,MCH,MSN,MWG,SAB,SHB,SSB,SSI,STB,TCB,TCX,VCB,VHM,VIB,VIC,VJC,VNM,VPB,VPL,VRE,VIX,POW,KDH,VND,GEX,NVL,MSB,NKG,DXG,TPB,VCI,VSC,CII,PNJ,TCH,PVT,KHG,DBC,PVD,DIG,HCM,KOS,EIB,PDR,HSG,DPM,HDC,HHV,CTS,VCG,HAG,HDG,GMD,GEL,TIG,SHS,CEO,PVS,MBS,VC3,DST,NRC,IDC,MST,NVB,TNG,VTZ,BVS,HUT,VGS,AMV,SRA,APS,VFS,DXP,PVC,PPT,IDJ,SVN,HDA,PV2,NAG,DVM,CTP,MBG,TTH,THT,MSR,ACM,BGE,AMS,POM,DRI,OIL,HNG,DDG,PHP,ACV,AAS,TCD,TVN,CLI,DDV,TAR,VCP,TV1,LCM,BIG,VEA,HNM,VGT,ABB,VGI,PCB,SBS,EME,SCL,PVX,PVL,LMH"

set +e
env PYTHONPATH=src "$project_root/.venv/bin/python" -m ssi_api.session_capture \
  --window morning \
  --symbols "$symbols" \
  --report outputs/qa/ssi_capture_morning_20261119_130symbols.json
status=$?
# Reconcile every quote appended after the mid-session QA refresh, then rebuild
# the observed-scope replay report. Both commands are idempotent.
env PYTHONPATH=src "$project_root/.venv/bin/python" -m data.pipeline data/raw/ws/2026-11-19.jsonl \
  --price-multiplier 1 --quantity-multiplier 1 \
  --unit-evidence-ref SSI_CUSTOMER_SUPPORT_EMAIL_QUOTE_UNITS_FULL_BOOK_2026-11-19 \
  --complete-book-verified --allowed-phase LO --replace-existing
env PYTHONPATH=src "$project_root/.venv/bin/python" -m data.replay
# launchctl submit jobs are keep-alive by default. Remove this dated job after
# the bounded collector returns so it cannot restart after 11:30.
launchctl remove com.liquidityguard.ssi.morning130.20261119 >/dev/null 2>&1 || true
exit "$status"
