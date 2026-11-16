# The Legend of Zelda: Ocarina of Time, Switch 2 edition (0400486024DEC000): the rewriter's patches of this game's own builds. dm/tools/patch_nso.py loads every profile's
# patches.py and applies those of a module's NSO build ID; CUTS, OBS and FRAME_STEP as described there ("Registered patches").
from nso_asm import ADRP, B

# Frame step (update v131072, main e0f3ccfa…): the game runs at 60 fps on the Switch 2, one game tick (1/60 s) per frame, and never changes its present interval: the frame-rate
# tick of its sead framework (vtable +0x128, main+0x4dbd60) returns at once because the framework's frame-rate mode ((fw+0x24f) & 3) is 1, so the interval controller
# embedded at fw+0x270 (main+0x3b4ef60, the same design as Breath of the Wild's) never runs. On a Mac that holds about 39 fps the game therefore plays in slow motion.
# The logic does follow the interval when one is set: with the controller forced to interval 2 / 30 fps, Link's run from the bed to the door took 23 presented frames instead
# of 59 (DM_NVN_REGLUM per-frame luminance, 2026-11-06, M1 Ultra), two ticks a frame, as Breath of the Wild's VFR does. So the host's frame step goes in at the controller:
#   · main+0x4dbd6c / +0x4dbd7c (the tick): with a target fps the mode check is skipped and the interval controller runs (never the VRR frame-rate controller, +0x232 / +0x231);
#   · main+0x3b4ef90 / +0x3b4ef9c (the controller's paused flag +0x60 and "no frame time yet", fw+0x140 < 1): skipped with a target, so the controller reaches its output every frame;
#   · main+0x3b4f054 (the controller's output: w21 = the interval it chose, stored at ctrl+0x48, fps = 60 / w21 at +0x58, then setFrameRate main+0x4dc0f0 → the swapchain's
#     setPresentInterval main+0xf49970 → nvnWindowSetPresentInterval, and setWaitVsyncInterval main+0x346c5c4, fps at fw+0xfc): w21 = the host's step in whole vsyncs
#     (state +0x20) once the host has decided one; until then the controller's own choice (its first frames measure the CPU and GPU time of the previous frame).
# State page target fps 0 (DM_FPS_TARGET=0): every stub runs the original instructions, the game keeps its fixed 60 fps interval 1 as shipped. x16 / x17 are free at all
# five sites (neither function uses them); the controller's sites keep the flags (adrp / ldr / cbz / mov do not set them: +0x3b4ef9c's b.lt reads cmp x8,#1 from before).
def frame_step(ctx):
    here, emit, fs_site, fs_put, FS_STATE_OFF = ctx.here, ctx.emit, ctx.site, ctx.put, ctx.state
    # the frame-rate tick (vtable +0x128): mode check and controller choice
    fs_site(0x4dbd6c, '60010054'); fs_site(0x4dbd7c, 'a1000054')
    start = here(); emit(ADRP(16, here(), FS_STATE_OFF))
    for w in (0xb9400210,   # ldr w16,[x16]          target fps
              0x34000090,   # cbz w16,orig (+4)
              0xaa0003e1,   # mov x1,x0
              0x9109c000):  # add x0,x0,#0x270       the interval controller
        emit(w)
    emit(B(here(), 0x3b4ef60))                                      # run it (the tail call at main+0x4dbd94)
    emit(0x54000160)                                                # orig: b.eq +11 → the ret at main+0x4dbd98 (below)
    emit(B(here(), 0x4dbd70))                                       # mode != 1: the original choice
    for _ in range(9): emit(0xd503201f)
    emit(B(here(), 0x4dbd98))                                       # the ret
    fs_put(0x4dbd6c, [B(0x4dbd6c, start)], 'frame-rate tick: with a target fps the frame-rate mode check is skipped and the interval controller runs')
    # the interval controller: paused flag and "no frame time yet"
    fs_site(0x3b4ef90, '28070037'); fs_site(0x3b4ef9c, 'cb060054')
    start = here(); emit(ADRP(16, here(), FS_STATE_OFF))
    for w in (0xb9400210,   # ldr w16,[x16]
              0x35000050):  # cbnz w16,on (+2)
        emit(w)
    emit(0x37000048)                                                # orig: tbnz w8,#0,paused (+2)
    emit(B(here(), 0x3b4ef94))                                      # on / not paused: continue
    emit(B(here(), 0x3b4f074))                                      # paused: the original target
    fs_put(0x3b4ef90, [B(0x3b4ef90, start)], 'interval controller: its paused flag (+0x60) is ignored with a target fps')
    start = here(); emit(ADRP(16, here(), FS_STATE_OFF))
    for w in (0xb9400210,   # ldr w16,[x16]
              0x35000050):  # cbnz w16,on (+2)
        emit(w)
    emit(0x5400004b)                                                # orig: b.lt skip (+2)   (flags: cmp x8,#1 at main+0x3b4ef98)
    emit(B(here(), 0x3b4efa0))                                      # on / a frame time exists: continue
    emit(B(here(), 0x3b4f074))                                      # skip: the original target
    fs_put(0x3b4ef9c, [B(0x3b4ef9c, start)], 'interval controller: runs before the first frame time too with a target fps')
    # the controller's output: the host's step
    fs_site(0x3b4f054, '88078052')
    start = here(); emit(ADRP(16, here(), FS_STATE_OFF))
    for w in (0xb9400211,   # ldr w17,[x16]          target fps (0 = off)
              0x340000f1,   # cbz w17,orig (+7)
              0xb9402211,   # ldr w17,[x16,#0x20]    step in vsyncs
              0x340000b1,   # cbz w17,orig (+5)      not decided yet: the controller's own interval
              0x2a1103f5,   # mov w21,w17
              0xf9401a11,   # ldr x17,[x16,#0x30]
              0x8b354231,   # add x17,x17,w21,uxtw
              0xf9001a11,   # str x17,[x16,#0x30]    vsyncs stepped
              0x52800788):  # orig: mov w8,#0x3c
        emit(w)
    emit(B(here(), 0x3b4f058))
    fs_put(0x3b4f054, [B(0x3b4f054, start)], "interval controller output: the host's step in whole vsyncs (state page target fps; 0 = the controller's own)")

# The fork's dynamic-resolution ceiling (upstream PR #1497; state +0x10) shares the build's FRAME_STEP entry with the frame step (state +0, +0x20, +0x30)
def render_scale(ctx):
    site = 0x31d3f48
    ctx.site(site, '805e0ebd')  # str s0,[x20,#0xe5c]
    start = ctx.here()
    ctx.emit(0xadbf7ffe)  # stp q30,q31,[sp,#-32]!
    ctx.emit(0xa9bf47f0)  # stp x16,x17,[sp,#-16]!
    ctx.emit(ADRP(16, ctx.here(), ctx.state))
    for word in (
        0xd53b4211,  # mrs x17,nzcv: the original store leaves flags intact
        0xbd40121e,  # ldr s30,[x16,#0x10]: host scale ceiling
        0x1e2023c8,  # fcmp s30,#0
        0x540000ed,  # b.le original: an unset state keeps the game
        0x1e2e101f,  # fmov s31,#1
        0x1e3f23c0,  # fcmp s30,s31
        0x5400008a,  # b.ge original: 1.0 keeps the original bits
        0x1e3e581f,  # fmin s31,s0,s30: the game can still choose a lower scale
        0xbd0e5e9f,  # str s31,[x20,#0xe5c]: leave s0 as the original store did
        0x14000002,  # b restore
        0xbd0e5e80,  # original: str s0,[x20,#0xe5c]
        0xd51b4211,  # restore: msr nzcv,x17
        0xa8c147f0,  # ldp x16,x17,[sp],#16
        0xacc17ffe,  # ldp q30,q31,[sp],#32
    ):
        ctx.emit(word)
    ctx.emit(B(ctx.here(), site + 4))
    ctx.put(site, [B(site, start)], 'dynamic resolution capped by the host render scale (1.0 = original)')
    ctx.render_scale = 1


# Wide view (DM_WIDE_VIEW, a launcher setting): the game sizes its output from fixed constants, so a screen wider than 16:9 shows bars. These stubs take the widths from the state page,
# written at each start from the screen's shape (loader.c), so the view widens and nothing stretches, and 0 there (16:9, or the setting off) runs the game's own constant. Sites from
# nxnative PR 1460 by vladbondarenko97, which cut them at build time; v131072 only (this FRAME_STEP key). Ported from HookLink (dsi-hub/nxnative hooklink 67189cd3, d4e2c93a).
# Each stub writes only the register the constant loads
wide_sites = [(0x1202ee0, 0xD2814008, 0x100, 8, 'graphics setup output width'), (0x31f39f4, 0xD2814008, 0x100, 8, 'docked render width'),
              (0x31f3a00, 0xD280F008, 0x104, 8, 'handheld render width'), (0xecbc80, 0x52A8A409, 0x108, 9, 'output width as a float')]
def wide_view(ctx):
    here, emit, fs_site, fs_put, FS_STATE_OFF = ctx.here, ctx.emit, ctx.site, ctx.put, ctx.state
    for site, orig, off, rd, what in wide_sites:
        fs_site(site, orig.to_bytes(4, 'little').hex())
        start = here(); emit(ADRP(rd, here(), FS_STATE_OFF))
        emit(0xB9400000 | (off // 4) << 10 | rd << 5 | rd)      # ldr w<rd>,[x<rd>,#off]
        emit(0x35000040 | rd)                                   # cbnz w<rd>,the branch back
        emit(orig); emit(B(here(), site + 4))
        fs_put(site, [B(site, start)], f'wide view: {what} from the state page (0: the game\'s own)')
    # The output resolution table (main+0x3f58540, read here by the display mode, a leaf ending in ret: x9..x11 are free): each entry's width from its height and the screen's ratio
    site = 0x112c604
    fs_site(site, '287968f8')   # ldr x8,[x9,x8,lsl #3]: width in the low word, height in the high one
    start = here(); emit(0xF8687928); emit(ADRP(9, here(), FS_STATE_OFF))
    for w in (0xB9410D2A, 0x340000EA, 0xD360FD0B, 0x9B0B7D4A, 0x9142014A, 0xD354FD4A, 0xD37CED4A, 0xB3407D48): emit(w)   # ratio (16.16); if 0 skip; height * ratio, to a multiple of 16; width
    emit(B(here(), site + 4))
    fs_put(site, [B(site, start)], 'wide view: output resolution table width from its height')
    # The 3D view: the render targets follow the wider size, but the game's cameras keep a 16:9 aspect, so the picture was stretched. sead::PerspectiveProjection::doUpdateMatrix (main+0x3485cc0, a
    # leaf: vtable main+0x4bf8c70 slot 11; near +0x98, far +0x9c, tan of the half angle +0xac, aspect +0xb0) gives a 16:9 projection (within 0.01) the picture's ratio (state +0x110, float; 0 = off)
    # and stores it, so what reads the aspect back agrees with the matrix: the vertical angle stays and the sides show more. Every 16:9 projection takes it: sead's default near 1 / far 10000
    # (main+0xea5480) is the shape the game's own cameras keep, and leaving it at 16:9 left the picture stretched on the phone. Views of another ratio (cube maps, shadow maps) stay as they are.
    # The state page counts the matrices built (+0x120) and widened (+0x124) and keeps the last other ratio seen (+0x128), for the log (hle_nvn.c). x9, x16, s2..s4 and the flags are free at the entry
    site = 0x3485cc0
    fs_site(site, '0084552d')   # ldp s0,s1,[x0,#0xac]
    start = here(); emit(0x2D558400); emit(ADRP(16, here(), FS_STATE_OFF))
    for w in (0xB9412209, 0x11000529, 0xB9012209,                                                   # +0x120 += 1
              0xBD411202, 0x1E202048, 0x54000240,                                                   # ldr s2,[x16,#0x110]; fcmp s2,#0; b.eq back
              0x5291C729, 0x72A7FC69, 0x1E270123, 0x1E233823, 0x1E20C063, 0x529AE149, 0x72A78469, 0x1E270124, 0x1E242060, 0x540000EA,   # |aspect - 16/9| >= 0.01: b.ge other
              0x1E204041, 0xBD00B001,                                                               # fmov s1,s2; str s1,[x0,#0xb0]
              0xB9412609, 0x11000529, 0xB9012609, 0x14000002,                                       # +0x124 += 1; b back
              0xBD012A01):                                                                          # other: str s1,[x16,#0x128]
        emit(w)
    emit(B(here(), site + 4))
    fs_put(site, [B(site, start)], 'wide view: a 16:9 camera takes the picture\'s ratio (the sides show more, nothing stretched)')
    # The game's code holds copies of that matrix code (getProjectionMatrix main+0x23b910 checks the vtable slot and builds it in place), so the stub above was never reached: the phone's log
    # counted 0 projections in 1,200 frames. The ratio is changed where the game sets it instead: each store of a perspective projection's aspect (+0xb0, with its changed flag +8) whose value is
    # 16:9 (within 2 ulps of 1920/1080) stores the picture's ratio when wide view is on. Viewport ratios of the camera list (main+0x3b50988, +0x3b50b50, +0x28e72a4), sead's set (main+0xea4b20, the
    # aspect in s8) and constructor (main+0x3485c64, s3), and the game's cameras' own parameter (+0x140: main+0x4c533c, +0x2e1bb6c, +0x2e1c7d0). x16 and x17 are dead at each site (a call or a
    # write follows) and the test is cbnz, as two sites carry live flags. Each site counts its passes at state +0x130 + 4 * index and the widened ones at +0x124, for the log (hle_nvn.c)
    for k, (site, orig, n) in enumerate(((0x3485c64, 0xBD00B003, 3), (0xEA4B20, 0x2D15A260, 8), (0x4C533C, 0xBD00B280, 0), (0x653BD4, 0xBD00B100, 0), (0x6545F4, 0xBD00B340, 0),
                                         (0x28E72A4, 0xBD00B100, 0), (0x2DD7164, 0xBD00B2C0, 0), (0x2E1BB6C, 0xBD00B2E0, 0), (0x2E1C7D0, 0xBD00B2A0, 0), (0x3B50988, 0xBD00B000, 0),
                                         (0x3B50B50, 0xBD00B300, 0))):
        fs_site(site, orig.to_bytes(4, 'little').hex())
        c = (0x130 + 4 * k) // 4
        start = here(); emit(ADRP(16, here(), FS_STATE_OFF))
        if site in (0x4C533C, 0x2E1BB6C, 0x2E1C7D0):
            # The game's cameras' own aspect parameter (+0x140, copied from +0xc8): the phone's log showed main+0x4c533c storing it every frame and never 16:9, so whatever it holds is
            # scaled by the picture's ratio over 16:9 (state +0x114, float; 0 = off) and the value it came with is kept at +0x128 for the log. s1 is written or a call follows at each site
            for w in (0xB9400211 | c << 10, 0x11000631, 0xB9000211 | c << 10, 0xBD012A00,      # this site's passes += 1; +0x128 = the aspect as the game set it
                      0xB9411611, 0x34000011 | 6 << 5, 0x1E270221, 0x1E210800,                  # w17 = the scale, 0: store as is; s1 = scale; s0 *= s1
                      0xB9412611, 0x11000631, 0xB9012611, orig):                                 # widened += 1; the game's store
                emit(w)
            emit(B(here(), site + 4))
            fs_put(site, [B(site, start)], f'wide view: the game camera\'s aspect parameter is scaled by the picture\'s ratio over 16:9 (site {k})')
            continue
        for w in (0xB9400211 | c << 10, 0x11000631, 0xB9000211 | c << 10,                    # this site's passes += 1
                  0x1E260011 | n << 5, 0x52800010 | 0x8E37 << 5, 0x72A00010 | 0x3FE3 << 5,      # w17 = the aspect's bits; w16 = 16:9's bits - 2
                  0x4B100231, 0x53027E31, 0x35000011 | 8 << 5):                                  # (w17 - w16) >> 2 != 0: not 16:9, store as is
            emit(w)
        emit(ADRP(16, here(), FS_STATE_OFF))
        for w in (0xB9411211, 0x34000011 | 5 << 5, 0x1E270220 | n,                              # ratio (+0x110), 0: store as is; s<n> = ratio
                  0xB9412611, 0x11000631, 0xB9012611, orig):                                     # widened += 1; the game's store
            emit(w)
        emit(B(here(), site + 4))
        fs_put(site, [B(site, start)], f'wide view: a 16:9 camera aspect set here takes the picture\'s ratio (site {k})')


def frame_step_and_scale(ctx):
    frame_step(ctx)
    render_scale(ctx)
    wide_view(ctx)


FRAME_STEP = {'e0f3ccfaf50065ae4ea01eb5aeb13b1a': frame_step_and_scale}

# Movie pictures (HookLink df4b1f60, its movie cut only: that commit's frame-ratio and frame-time-floor parts are for HookLink's newer frame step, which this fork does not have).
# The movies are AV1 at 60 pictures a second (Event/Movie/*.webm, no sound track: the opening's Dm_Kokiri_0000 is 9,254 pictures, 154.2 s). The player's update
# (main+0x3b5ca60, v131072) adds the time object's step (+0x18 x 60, the frame ratio) to a remainder and advances that many picture times, at most the player's limit (+0x20):
# main+0x3b5cb20. Its queue (main+0x3b61ea0) pops that many decoded pictures and shows the last, so the player can skip. The limit is 1 + (the creation argument >= 2)
# (main+0x3b5d068 / +0x3b5d084), and the game passes 1 (main+0x3b5c55c): one picture a calc at most, right at 60 calcs a second and nowhere else. At this fork's 2-vsync
# interval the game steps two ticks a frame (frame_step above), so a movie played at half speed and fell behind its sound. The cut makes the limit 2, the player's own value
# for an argument of 2 or more (its buffers follow it, +0x50), so a movie keeps its time down to 30 fps. Not run on this fork: carried over from HookLink unchanged.
#   main+0x3b5cec0, 828 bytes: cinc w8,w28,ge -> add w8,w28,#1 at +0x1c4 (w28 = 1; the flags of cmp w27,#2 are not read again)
movie = 'movie pictures: up to 2 a calc'
MATCH_CUTS = {'main': [
    {'name': movie, 'size': 828, 'fingerprints': ['f61ad468b6b4e1d574fe8678f5a12dfc60e1aab71be7375142a4b48b0d73ce19'],
     'cuts': [(452, '88b79c1a', '88070011', movie + ' (as v131072 main+0x3b5d084)')]},
]}

# How general each patch is and could be (dm/tools/docs_patches.py "Binding", listed in docs/agents/game-patches.md)
BINDING = [
    {'what': 'wide view: output and render widths and the 3D camera ratio from the state page', 'now': 'build', 'goal': 'game', 'purpose': 'rendering',
     'why': "the game's own size constants and sead's projection, at fixed addresses of v131072 (HookLink's port of nxnative PR 1460)"},
    {'what': 'frame step in whole vsyncs', 'now': 'build', 'goal': 'game', 'purpose': 'frame rate',
     'why': "the framework's interval controller and frame-rate tick",
     'blocked': 'frame-step stubs have no function-matched form yet'},
    {'what': 'dynamic-resolution ceiling', 'now': 'build', 'goal': 'game', 'purpose': 'rendering',
     'why': "the game's final scale store follows its dynamic and fixed-mode choices",
     'blocked': 'the store and its role are verified for this main build only',
     'checked': 'v131072 main E0F3CCFAF50065AE4EA01EB5AEB13B1A, original store and surrounding code, 2026-11-06'},
    {'what': movie, 'now': 'game', 'goal': 'game', 'purpose': 'frame rate',
     'why': "the game's own movie player takes one picture a calc at most; function-matched (MATCH_CUTS) on any build that keeps the player's constructor",
     'checked': 'v131072 main: one function with this fingerprint; the limit, its two readers, the update that clamps to it and the queue that skips read by disassembly (2026-11-09, HookLink); '
                'the opening movie timed on an iPhone before the cut (9,254 pictures in 262 s for 154 s)'},
]
