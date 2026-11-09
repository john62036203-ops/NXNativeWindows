#!/usr/bin/env python3
# slim-app: our slim build's app (host, launcher, rewritten modules) built again from this tree (switch2 + upstream's fixes since 2026-11-07, its shader chain kept at the slim
# build's), packed with the shader libraries of OoT-slim.ipa as they are: no shader is translated or compiled again (minutes, not hours).
# Writes OoT-slim-up.ipa (romfs.id of the old dump, like OoT-slim.ipa) and OoT-slim-up-clean.ipa (romfs.id of the clean dump, C:\OOT-A12\RomFS.img, like OoT-slim-clean.ipa).
# Usage: python win\slim_app.py
import os, shutil, struct, subprocess, sys, time, zipfile, zlib
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding='utf-8', errors='replace')
    except Exception: pass
from pathlib import Path

WIN = Path(__file__).resolve().parent
REPO = WIN.parent
GAME = '0400486024DEC000'
SRC_IPA = Path(r'C:\Games\OoT\OoT-slim-x.ipa')
OUT = Path(r'C:\Games\OoT\OoT-slim-x3o.ipa')
OUT_CLEAN = Path(r'C:\Games\OoT\OoT-slim-x3o-clean.ipa')
EXEFS = Path(r'C:\Games\OoT\build\extract\v131072\ExeFS')
OLD_ROMFS = EXEFS.parent / 'RomFS.img'           # the old dump, unpacked by the builds: OoT-slim.ipa's romfs.id
CLEAN_ROMFS = Path(r'C:\OOT-A12\RomFS.img')
ICON = EXEFS.parent / 'icon.jpg'
WORK = Path(r'C:\Games\OoT\slimx3o_work')
MAIN_WIN = Path(r'D:\nxw\win')
BUNDLE = 'org.nxnativewindows.0400486024dec000'   # OoT-slim.ipa's: the same data folder on the phone (RomFS.img, saves)
ID_NAME = 'Payload/DmIOS.app/romfs.id'


def t(msg): print(f'[{time.strftime("%H:%M:%S")}] {msg}', flush=True)
def die(msg): t(f'FAIL: {msg}'); sys.exit(1)


def set_romfs_id(src, dst, img):
    """Copy src to dst with romfs.id naming img (same length stored entry: patched in place, CRC fixed in both headers)."""
    sys.path.insert(0, str(REPO / 'dm/tools'))
    from romfs_image import identity
    with zipfile.ZipFile(src) as z:
        info = z.getinfo(ID_NAME); old = z.read(ID_NAME).decode('utf-8'); start_dir = z.start_dir
    parts = dict(p.split('=', 1) for p in old.split()[1:] if '=' in p)
    new = (identity(str(img), parts.get('title', ''), parts.get('version', ''), parts.get('build', '')) + '\n').encode('utf-8')
    t(f'romfs.id for {dst.name}: {new.decode().strip()}')
    if info.compress_type != zipfile.ZIP_STORED or len(new) != info.file_size: die(f'romfs.id stored={info.compress_type == 0}, {info.file_size} bytes vs {len(new)}')
    part = dst.with_name(dst.name + '.part')
    shutil.copyfile(src, part)
    crc = zlib.crc32(new) & 0xffffffff
    with open(part, 'r+b') as f:
        f.seek(info.header_offset); h = f.read(30)
        if h[:4] != b'PK\x03\x04': die('local header not found')
        nl, el = struct.unpack('<HH', h[26:30])
        f.seek(info.header_offset + 14); f.write(struct.pack('<I', crc))
        f.seek(info.header_offset + 30 + nl + el); f.write(new)
        f.seek(start_dir); done = False
        while True:
            e = f.read(46)
            if len(e) < 46 or e[:4] != b'PK\x01\x02': break
            nl, el, cl = struct.unpack('<HHH', e[28:34]); nm = f.read(nl)
            if nm.decode('utf-8', 'replace') == ID_NAME: f.seek(-(nl + 46) + 16, 1); f.write(struct.pack('<I', crc)); done = True; break
            f.seek(el + cl, 1)
        if not done: die('central directory entry not found')
    with zipfile.ZipFile(part) as z:
        if z.read(ID_NAME) != new: die('verify')
    if dst.exists(): dst.unlink()
    part.replace(dst)


def main():
    t(f'tree {REPO}'); t(f'shaders from {SRC_IPA}'); t(f'output {OUT} and {OUT_CLEAN}')
    for p in (SRC_IPA, EXEFS / 'main', OLD_ROMFS):
        if not p.exists(): die(f'missing {p}')
    free = shutil.disk_usage(OUT.parent).free / 2**30
    t(f'free space on {OUT.drive}: {free:.1f} GB')
    if free < 20: die('need about 20 GB free (shader image 7.9 GB + two IPAs of 4.5 GB)')
    if not (WIN / 'toolchain.json').exists() and (MAIN_WIN / 'toolchain.json').exists():
        shutil.copy2(MAIN_WIN / 'toolchain.json', WIN / 'toolchain.json'); t('toolchain.json copied from D:\\nxw\\win')

    env = dict(os.environ)
    env['PYTHONPATH'] = os.pathsep.join([str(WIN / 'pyshim')] + [p for p in env.get('PYTHONPATH', '').split(os.pathsep) if p])
    env['PYTHONUTF8'] = '1'
    env['DM_GAME'] = GAME

    # 1) OoT-slim.ipa: its shader image and the tables its shader build wrote
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
        for f in ('c1_full.tsv', 'cb_extent.tsv', 'shader_map.tsv', 'pso_manifest.tsv', 'shader_pairs.tsv', 'pso_pairs.tsv'):
            n = f'Payload/DmIOS.app/dm/{f}'
            if n in names: (gd / f).write_bytes(z.read(n)); t(f'{f} from OoT-slim.ipa')
            else: t(f'[warn] {f} not in OoT-slim.ipa')
    # The pipelines met in play on the phone (its Documents/pso_user.tsv, copied into the tree as pso_user_seed.tsv) join the shipped prewarm list: a fresh install prepares them at the start
    # instead of compiling each at its first draw (1-3 s stalls a batch). Same rows (S / R / C / M), duplicates dropped
    seed = gd / 'pso_user_seed.tsv'; man = gd / 'pso_manifest.tsv'
    if seed.exists() and man.exists():
        have = set(l.rstrip('\n') for l in man.read_text(encoding='utf-8').splitlines() if l and not l.startswith('#'))
        add = [l.rstrip('\n') for l in seed.read_text(encoding='utf-8').splitlines() if l and not l.startswith('#') and l.rstrip('\n') not in have]
        add = list(dict.fromkeys(add))
        if add:
            with open(man, 'a', encoding='utf-8', newline='\n') as f: f.write('\n'.join(add) + '\n')
        t(f'pso_manifest.tsv: {len(add)} rows added from pso_user_seed.tsv ({len(have)} were there)')
    chain = Path(img).stem
    hdr = (REPO / 'dm/gfx/nvn/dmsh_chain.h').read_text(encoding='utf-8')
    if f'"{chain[2:]}"' not in hdr: die(f'the IPA\'s shader image {chain} is not this tree\'s chain ({hdr.strip().splitlines()[-1]})')
    t(f'shader chain {chain} matches dmsh_chain.h')

    # 2) the code modules rewritten with this tree's patches
    patched = WORK / 'patched_v131072'
    if patched.exists(): shutil.rmtree(patched)
    patched.mkdir(parents=True)
    for m in ('main', 'subsdk0', 'sdk'):
        t(f'rewrite {m} (patch_nso.py)')
        log = WORK / f'rewrite_{m}.log'
        with open(log, 'w', encoding='utf-8') as lf:
            r = subprocess.run([sys.executable, str(REPO / 'dm/tools/patch_nso.py'), str(EXEFS / m), str(patched), m], env=env, stdout=lf, stderr=subprocess.STDOUT)
        if r.returncode: print(log.read_text(encoding='utf-8', errors='replace')[-3000:]); die(f'patch_nso.py {m} exit {r.returncode}')

    # 3) the app with OoT-slim.ipa's shader image; no game files in the IPA
    benv = dict(env, GAME=GAME, W=str(WORK), PATCHED=str(patched), ROMFS=str(OLD_ROMFS), MSL_IOS=str(msl), DM_COPY_ROMFS='NO', DM_SHOW_FPS='1',
                DM_DISPLAY_NAME='The Legend of Zelda: Ocarina of Time', DM_APP_VERSION='1.0', DM_BUNDLE_ID=BUNDLE, DM_ICON=str(ICON),
                NXW_ENTITLEMENTS='1', NXW_TRUST_MSL='1', DM_PSO_GPUS='none', AOC='')
    benv.pop('NXW_BUNDLE_PREFIX', None); benv.pop('NXW_ROMFS_ID_IMAGE', None)
    tmp = OUT.with_name(OUT.stem + '.partial.ipa')
    if tmp.exists(): tmp.unlink()
    t('app build (win/build_app.py)')
    r = subprocess.run([sys.executable, str(WIN / 'build_app.py'), str(tmp)], env=benv)
    if r.returncode: die(f'build_app.py exit {r.returncode}')
    if OUT.exists(): OUT.unlink()
    tmp.replace(OUT)
    t(f'done: {OUT} ({OUT.stat().st_size / 2**30:.2f} GB), romfs.id of the old dump')

    # 4) the same app naming the clean dump's RomFS.img
    if CLEAN_ROMFS.exists():
        set_romfs_id(OUT, OUT_CLEAN, CLEAN_ROMFS)
        t(f'done: {OUT_CLEAN}, romfs.id of {CLEAN_ROMFS}')
    else: t(f'[warn] {CLEAN_ROMFS} not found: no clean-dump variant')
    t('ALL DONE')


if __name__ == '__main__':
    main()
