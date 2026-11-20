#!/bin/sh
# Persistent Terminal entrypoint: VN30 + two non-overlapping 100-symbol batches.
set -eu
project_root="/Users/thylnh.iu/Documents/Neo-LiquidityGuard"
cd "$project_root"

base_symbols="ACB,BID,BSR,CTG,FPT,GAS,GVR,HDB,HPG,LPB,MBB,MCH,MSN,MWG,SAB,SHB,SSB,SSI,STB,TCB,TCX,VCB,VHM,VIB,VIC,VJC,VNM,VPB,VPL,VRE,VIX,POW,KDH,VND,GEX,NVL,MSB,NKG,DXG,TPB,VCI,VSC,CII,PNJ,TCH,PVT,KHG,DBC,PVD,DIG,HCM,KOS,EIB,PDR,HSG,DPM,HDC,HHV,CTS,VCG,HAG,HDG,GMD,GEL,TIG,SHS,CEO,PVS,MBS,VC3,DST,NRC,IDC,MST,NVB,TNG,VTZ,BVS,HUT,VGS,AMV,SRA,APS,VFS,DXP,PVC,PPT,IDJ,SVN,HDA,PV2,NAG,DVM,CTP,MBG,TTH,THT,MSR,ACM,BGE,AMS,POM,DRI,OIL,HNG,DDG,PHP,ACV,AAS,TCD,TVN,CLI,DDV,TAR,VCP,TV1,LCM,BIG,VEA,HNM,VGT,ABB,VGI,PCB,SBS,EME,SCL,PVX,PVL,LMH"
extra_symbols="PLX,MZG,NAB,TTF,VCK,ORS,DXS,OCB,DCM,BAF,IJC,HQC,AAA,ANV,SBT,NT2,CRC,GEE,ELC,PVP,NLG,SZC,VAB,PAN,HHS,VTP,CTI,DGW,VPI,PC1,FCN,KBC,TCM,EVF,PLC,LAS,NTP,DL1,EVS,PIA,MAC,LIG,DTD,VC7,VIG,PSD,API,CET,OCH,C69,PCH,KSF,NDN,SJE,TDT,NBC,VHE,CST,ADC,BCC,LDP,BKC,PVB,PSI,L18,ICG,VC2,VNH,VNE,F88,VKC,HBC,QTP,DVN,SAS,ATA,AAV,VST,DFF,LLM,CEN,CT3,VIW,V68,DGT,KVC,HKB,PVE,C4G,CAD,CQN,PXI,FTM,SDA,ABW,PXL,CAT,AGP,AAH,PXS"
symbols="$base_symbols,$extra_symbols"

set +e
env PYTHONPATH=src "$project_root/.venv/bin/python" -m ssi_api.session_capture \
  --window morning \
  --skip-symbol-rest \
  --symbols "$symbols" \
  --report outputs/qa/ssi_capture_morning_20261119_230symbols.json
status=$?
env PYTHONPATH=src "$project_root/.venv/bin/python" -m data.pipeline data/raw/ws/2026-11-19.jsonl \
  --price-multiplier 1 --quantity-multiplier 1 \
  --unit-evidence-ref SSI_CUSTOMER_SUPPORT_EMAIL_QUOTE_UNITS_FULL_BOOK_2026-11-19 \
  --complete-book-verified --allowed-phase LO --replace-existing
env PYTHONPATH=src "$project_root/.venv/bin/python" -m data.replay
exit "$status"
