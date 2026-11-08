#!/usr/bin/env python3
# A12 app-only rebuild (a12-ios branch): cheemu21's A12 IPA keeps its shader libraries (compiled on a Mac, Apple metal 32023.922);
# only the app (the host, the launcher, the rewritten modules) is built again from this tree, which differs from tag a12 in:
#   - DM_NDVE defaults to the game's network (the MetalFX route froze the title movie on an iPhone 16 Pro Max: decoder held 12 pictures, 0 fps)
#   - win/ (the Windows toolchain) taken from john62036203-ops/NXNativeWindows switch2
# Usage: python win\a12_app.py [A12.ipa] [out.ipa]
import os, shutil, subprocess, sys, time, zipfile
from pathlib import Path

WIN = Path(__file__).resolve().parent
REPO = WIN.parent
GAME = '0400486024DEC000'
SRC_IPA = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r'C:\OOT\OcarinaOfTime-A12.ipa')
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(r'C:\OOT\OoT-A12-fix.ipa')
EXEFS = Path(r'C:\Games\OoT\build\extract\v131072\ExeFS')
ICON = EXEFS.parent / 'icon.jpg'
ROMFS = Path(r'C:\Users\john6\Documents\新增資料夾\RomFS (1).img')   # the new dump's image: its size and index go into romfs.id
WORK = Path(r'C:\OOT\a12work')
MAIN_WIN = Path(r'D:\nxw\win')   # the main checkout: toolchain.json (absolute paths), the iPhoneOS SDK, zstd


def t(msg): print(f'[{time.strftime("%H:%M:%S")}] {msg}', flush=True)
def die(msg): t(f'FAIL: {msg}'); sys.exit(1)


def main():
    t(f'tree {REPO}'); t(f'A12 IPA {SRC_IPA}'); t(f'output {OUT}')
    for p in (SRC_IPA, EXEFS / 'main', ROMFS):
        if not p.exists(): die(f'missing {p}')
    free = shutil.disk_usage(OUT.parent).free / 2**30
    t(f'free space on {OUT.drive}: {free:.1f} GB')
    if free < 9: die('need about 9 GB free (shader image 3.5 GB + new IPA 3.5 GB)')
    if not (WIN / 'toolchain.json').exists() and (MAIN_WIN / 'toolchain.json').exists():
        shutil.copy2(MAIN_WIN / 'toolchain.json', WIN / 'toolchain.json'); t('toolchain.json copied from D:\\nxw\\win')

    env = dict(os.environ)
    env['PYTHONPATH'] = os.pathsep.join([str(WIN / 'pyshim')] + [p for p in env.get('PYTHONPATH', '').split(os.pathsep) if p])
    env['PYTHONUTF8'] = '1'
    env['DM_GAME'] = GAME

    # 1) the A12 IPA: its shader image and the two tables its shader build wrote (c1_full.tsv, cb_extent.tsv)
    msl = WORK / 'msl'; msl.mkdir(parents=True, exist_ok=True)
    gd = REPO / 'dm/games' / GAME
    with zipfile.ZipFile(SRC_IPA) as z:
        names = z.namelist()
        imgs = [n for n in names if n.startswith('Payload/DmIOS.app/msl/') and n.endswith('.img')]
        if len(imgs) != 1: die(f'expected one shader image in the IPA, found {imgs}')
        img = imgs[0]; dst = msl / Path(img).name
        info = z.getinfo(img)
        if not (dst.exists() and dst.stat().st_size == info.file_size):
            t(f'extracting {img} ({info.file_size / 2**30:.2f} GB)')
            with z.open(img) as s, open(dst, 'wb') as d: shutil.copyfileobj(s, d, 16 << 20)
        else: t(f'{dst.name} already extracted')
        for f in ('c1_full.tsv', 'cb_extent.tsv'):
            n = f'Payload/DmIOS.app/dm/{f}'
            if n in names: (gd / f).write_bytes(z.read(n)); t(f'{f} from the A12 IPA')
            else: t(f'[warn] {f} not in the A12 IPA')
        for f in ('shader_map.tsv', 'pso_manifest.tsv'):
            n = f'Payload/DmIOS.app/dm/{f}'
            if n in names and z.read(n) != (gd / f).read_bytes(): t(f'[warn] {f} in the A12 IPA differs from this tree\'s; using the IPA\'s'); (gd / f).write_bytes(z.read(n))
    chain = Path(img).stem
    hdr = (REPO / 'dm/gfx/nvn/dmsh_chain.h').read_text(encoding='utf-8')
    if f'"{chain[2:]}"' not in hdr: die(f'the IPA\'s shader image {chain} is not this tree\'s chain ({hdr.strip().splitlines()[-1]})')
    t(f'shader chain {chain} matches dmsh_chain.h')

    # 2) the code modules rewritten with this tree's patches (A12's patches.py)
    patched = WORK / 'patched_v131072'
    if patched.exists(): shutil.rmtree(patched)
    patched.mkdir(parents=True)
    for m in ('main', 'subsdk0', 'sdk'):
        t(f'rewrite {m} (patch_nso.py)')
        log = WORK / f'rewrite_{m}.log'
        with open(log, 'w', encoding='utf-8') as lf:
            r = subprocess.run([sys.executable, str(REPO / 'dm/tools/patch_nso.py'), str(EXEFS / m), str(patched), m], env=env, stdout=lf, stderr=subprocess.STDOUT)
        if r.returncode: print(log.read_text(encoding='utf-8', errors='replace')[-3000:]); die(f'patch_nso.py {m} exit {r.returncode}')

    # 3) the app, packed with the A12 shader image; no game files in the IPA (Documents/RomFS.img stays as it is on the phone)
    benv = dict(env, GAME=GAME, W=str(WORK), PATCHED=str(patched), ROMFS=str(ROMFS), MSL_IOS=str(msl), DM_COPY_ROMFS='NO', DM_SHOW_FPS='1',
                DM_DISPLAY_NAME='Ocarina of Time', DM_APP_VERSION='1.0', DM_BUNDLE_ID='org.nxnative.0400486024dec000', DM_ICON=str(ICON),
                NXW_ENTITLEMENTS='1', NXW_TRUST_MSL='1', DM_PSO_GPUS='none', AOC='')
    benv.pop('NXW_BUNDLE_PREFIX', None)
    tmp = OUT.with_name(OUT.stem + '.partial.ipa')
    if tmp.exists(): tmp.unlink()
    t('app build (win/build_app.py)')
    r = subprocess.run([sys.executable, str(WIN / 'build_app.py'), str(tmp)], env=benv)
    if r.returncode: die(f'build_app.py exit {r.returncode}')
    if OUT.exists(): OUT.unlink()
    tmp.replace(OUT)
    t(f'done: {OUT} ({OUT.stat().st_size / 2**30:.2f} GB)')


if __name__ == '__main__':
    main()
