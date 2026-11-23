#!/usr/bin/env python3
"""Derive Panther X2 B1 DTB by isolating network devices only."""
from __future__ import annotations
import re, sys
from pathlib import Path

def block_span(text: str, marker: str) -> tuple[int,int]:
 hits=[m.start() for m in re.finditer(re.escape(marker),text)]
 if len(hits)!=1: raise RuntimeError(f"expected exactly one marker {marker!r}, found {len(hits)}")
 pos=hits[0]; start=text.rfind("\n",0,pos)+1; brace=text.find("{",pos)
 if brace<0: raise RuntimeError(f"opening brace missing: {marker!r}")
 depth=0; state="normal"; i=brace
 while i<len(text):
  ch=text[i]; nxt=text[i+1] if i+1<len(text) else ""
  if state=="line":
   if ch=="\n": state="normal"
   i+=1
  elif state=="block":
   if ch=="*" and nxt=="/": state="normal"; i+=2
   else: i+=1
  elif state=="string":
   if ch=="\\": i+=2
   elif ch=='"': state="normal"; i+=1
   else: i+=1
  elif ch=="/" and nxt=="/": state="line"; i+=2
  elif ch=="/" and nxt=="*": state="block"; i+=2
  elif ch=='"': state="string"; i+=1
  elif ch=="{": depth+=1; i+=1
  elif ch=="}":
   depth-=1; i+=1
   if depth==0:
    end=i
    while end<len(text) and text[end] in " \t\r\n": end+=1
    if end<len(text) and text[end]==";": end+=1
    else: raise RuntimeError(f"block terminator missing: {marker!r}")
    return start,end
  else: i+=1
 raise RuntimeError(f"unclosed block: {marker!r}")

def remove_block(text,marker):
 a,b=block_span(text,marker); return text[:a]+text[b:]

def direct_status_span(block):
 brace=block.find("{")
 if brace<0: raise RuntimeError("node opening brace missing")
 depth=0; state="normal"; i=0; line_start=0
 while i<len(block):
  if i==brace:
   depth=1; i+=1; line_start=i; continue
  ch=block[i]; nxt=block[i+1] if i+1<len(block) else ""
  if state=="line":
   if ch=="\n": state="normal"; line_start=i+1
   i+=1
  elif state=="block":
   if ch=="*" and nxt=="/": state="normal"; i+=2
   else: i+=1
  elif state=="string":
   if ch=="\\": i+=2
   elif ch=='"': state="normal"; i+=1
   else: i+=1
  elif ch=="/" and nxt=="/": state="line"; i+=2
  elif ch=="/" and nxt=="*": state="block"; i+=2
  elif ch=='"': state="string"; i+=1
  elif ch=="{": depth+=1; i+=1
  elif ch=="}":
   depth-=1
   if depth==0: return None
   i+=1
  elif ch=="\n":
   line_start=i+1; i+=1
  else:
   if depth==1 and block[line_start:i].strip()=="":
    line_end=block.find("\n",i)
    if line_end<0: line_end=len(block)
    line=block[line_start:line_end]
    match=re.match(r'^([ \t]*)status\s*=\s*"([^"]+)"\s*;[ \t]*$',line)
    if match: return (line_start,line_end,match.group(1),match.group(2))
   i+=1
 return None

def get_direct_status(text,marker):
 a,b=block_span(text,marker); found=direct_status_span(text[a:b])
 return found[3] if found else None

def set_status(text,marker,status):
 a,b=block_span(text,marker); block=text[a:b]
 found=direct_status_span(block)
 if found:
  line_start,line_end,indent,_=found
  block=block[:line_start]+f'{indent}status = "{status}";'+block[line_end:]
 else:
  brace=block.find("{")
  block=block[:brace+1]+f'\n\tstatus = "{status}";'+block[brace+1:]
 return text[:a]+block+text[b:]

def remove_property(text,marker,name):
 a,b=block_span(text,marker); block=text[a:b]
 block,n=re.subn(rf"(?m)^[ \t]*{re.escape(name)}\s*=.*;[ \t]*\n","",block)
 if n!=1: raise RuntimeError(f"expected one {name!r} in {marker!r}, found {n}")
 return text[:a]+block+text[b:]

def main():
 if len(sys.argv)!=2: raise SystemExit("usage: prepare-clean-dtb.py <rk3566-panther-x2.dts>")
 path=Path(sys.argv[1]); original=path.read_text()
 if 'model = "Panther X2";' not in original or '"panther,x2"' not in original: raise SystemExit("refusing non-Panther-X2 DTS")
 text=original
 for marker in ("sdio_pwrseq: sdio-pwrseq","sdio-pwrseq {","wireless-wlan {","\tbt {","bluetooth {","led_wifi: led-wifi","led_wifi_enable_h: led-wifi-enable-h"):
  text=remove_block(text,marker)
 text=remove_property(text,"&sdmmc1 {","mmc-pwrseq")
 for marker in ("&gmac1 {","&mdio1 {","rgmii_phy1: ethernet-phy@0","&sdmmc1 {"):
  text=set_status(text,marker,"disabled")
 residue=re.compile(r"\b(?:wifi|wireless|bluetooth|bt_enable_h|bt_host_wake_l|bt_wake_l|sdio_pwrseq|wifi_enable_h|wifi_host_wake_irq|led_wifi)\b",re.I)
 if residue.search(text): raise SystemExit("Wi-Fi/BT residue remains in derived DTS")
 a,b=block_span(text,"aliases {"); aliases=text[a:b]
 for alias in ("ethernet0","mmc0","mmc1","mmc2"):
  if not re.search(rf"(?m)^\s*{alias}\s*=",aliases): raise SystemExit(f"original alias lost: {alias}")
 for marker in ("&gmac1 {","&mdio1 {","rgmii_phy1: ethernet-phy@0","&sdmmc1 {"):
  actual=get_direct_status(text,marker)
  if actual!="disabled": raise SystemExit(f"node direct status not disabled: {marker} (actual={actual!r})")
 for marker in ("&sdhci {","&sdmmc0 {","&uart1 {","&uart2 {","&usb_host0_xhci {","&usb_host0_ohci {","&usb_host0_ehci {","&usb2phy0 {","&usb2phy0_host {","&usb2phy0_otg {"):
  a,b=block_span(text,marker)
  if re.search(r'status\s*=\s*"disabled"',text[a:b]): raise SystemExit(f"non-network node disabled: {marker}")
 path.write_text(text)
 print(f"Prepared B1 network-isolated DTB source: {path}")
 print("Disabled: GMAC1, MDIO1, RTL8211F node, Wi-Fi SDIO host")
 print("Removed: Wi-Fi/BT nodes, GPIO/power sequence and Wi-Fi LED")
 print("Retained: eMMC, TF/SD, USB, UART1/2, aliases, Ethernet LED and shared resources")

if __name__=="__main__": main()
