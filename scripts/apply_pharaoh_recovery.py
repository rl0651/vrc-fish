from pathlib import Path

p = Path('engine/fish_engine.cpp')
s = p.read_text(encoding='utf-8')


def replace_once(old: str, new: str, label: str) -> None:
    global s
    count = s.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected exactly 1 match, found {count}')
    s = s.replace(old, new, 1)

replace_once(
'''\tint cachedFishTplIdx{};\n\tbool hasCachedFishTpl{};\n\tint recordFrame{};''',
'''\tint cachedFishTplIdx{};\n\tbool hasCachedFishTpl{};\n\tint fastDetectFrames{};\n\tint stableFishFrames{};\n\tint pendingFishY{};\n\tbool hasPendingFish{};\n\tint recordFrame{};''',
'LoopState recovery fields')

replace_once(
'''\tloop.hasLastGoodPos = false;\n\tloop.consecutiveMiss = 0;\n\n\tif (config.ml_mode == 1) {''',
'''\tloop.hasLastGoodPos = false;\n\tloop.consecutiveMiss = 0;\n\tloop.fastDetectFrames = 0;\n\tloop.stableFishFrames = 0;\n\tloop.pendingFishY = 0;\n\tloop.hasPendingFish = false;\n\n\tif (config.ml_mode == 1) {''',
'round reset')

old_detect = r'''\tif (!loop.hasCachedFishTpl) {
\t\tint bestIdx = 0;
\t\tok = detectFishAndSliderFull(
\t\t\tgray,
\t\t\tmatchRoi,
\t\t\truntime_.templates(),
\t\t\tconfig,
\t\t\tloop.cachedTrackScale,
\t\t\tloop.cachedTrackAngle,
\t\t\t&det,
\t\t\t&bestIdx);
\t\tif (ok) {
\t\t\tloop.cachedFishTplIdx = bestIdx;
\t\t\tloop.hasCachedFishTpl = true;
\t\t}
\t\tdidFullDetect = true;
\t} else {
\t\tok = detectFishAndSliderFast(
\t\t\tgray,
\t\t\tmatchRoi,
\t\t\truntime_.templates(),
\t\t\tconfig,
\t\t\tloop.cachedTrackScale,
\t\t\tloop.cachedTrackAngle,
\t\t\tloop.cachedFishTplIdx,
\t\t\t&det);
\t\tif (!ok) {
\t\t\tint bestIdx = 0;
\t\t\tok = detectFishAndSliderFull(
\t\t\t\tgray,
\t\t\t\tmatchRoi,
\t\t\t\truntime_.templates(),
\t\t\t\tconfig,
\t\t\t\tloop.cachedTrackScale,
\t\t\t\tloop.cachedTrackAngle,
\t\t\t\t&det,
\t\t\t\t&bestIdx);
\t\t\tif (ok) {
\t\t\t\tloop.cachedFishTplIdx = bestIdx;
\t\t\t}
\t\t\tdidFullDetect = true;
\t\t}
\t}
'''.replace('\\t', '\t')

new_detect = r'''\tif (!loop.hasCachedFishTpl) {
\t\tint bestIdx = 0;
\t\tok = detectFishAndSliderFull(
\t\t\tgray,
\t\t\tmatchRoi,
\t\t\truntime_.templates(),
\t\t\tconfig,
\t\t\tloop.cachedTrackScale,
\t\t\tloop.cachedTrackAngle,
\t\t\t&det,
\t\t\t&bestIdx);
\t\tif (ok) {
\t\t\tloop.cachedFishTplIdx = bestIdx;
\t\t\tloop.hasCachedFishTpl = true;
\t\t\tloop.fastDetectFrames = 0;
\t\t}
\t\tdidFullDetect = true;
\t} else {
\t\tok = detectFishAndSliderFast(
\t\t\tgray,
\t\t\tmatchRoi,
\t\t\truntime_.templates(),
\t\t\tconfig,
\t\t\tloop.cachedTrackScale,
\t\t\tloop.cachedTrackAngle,
\t\t\tloop.cachedFishTplIdx,
\t\t\t&det);
\t\tif (ok) {
\t\t\tloop.fastDetectFrames++;
\t\t}
\t\tif (!ok) {
\t\t\tint bestIdx = 0;
\t\t\tok = detectFishAndSliderFull(
\t\t\t\tgray,
\t\t\t\tmatchRoi,
\t\t\t\truntime_.templates(),
\t\t\t\tconfig,
\t\t\t\tloop.cachedTrackScale,
\t\t\t\tloop.cachedTrackAngle,
\t\t\t\t&det,
\t\t\t\t&bestIdx);
\t\t\tif (ok) {
\t\t\t\tloop.cachedFishTplIdx = bestIdx;
\t\t\t\tloop.hasCachedFishTpl = true;
\t\t\t\tloop.fastDetectFrames = 0;
\t\t\t}
\t\t\tdidFullDetect = true;
\t\t}
\t}

\t// Recovery watchdog: the cached fast detector can latch onto a static false
\t// match. Recheck quickly if fishY is frozen while outside the slider. Also do
\t// a sparse full verification to recover from slower template drift without
\t// adding meaningful overhead during difficult fish.
\tif (ok && !didFullDetect) {
\t\tif (loop.hasPrevFish && std::abs(det.fishY - loop.prevFishY) <= 2) {
\t\t\tloop.stableFishFrames++;
\t\t} else {
\t\t\tloop.stableFishFrames = 0;
\t\t}

\t\tint outsideDistance = 0;
\t\tif (det.fishY < det.sliderTop) {
\t\t\toutsideDistance = det.sliderTop - det.fishY;
\t\t} else if (det.fishY > det.sliderBottom) {
\t\t\toutsideDistance = det.fishY - det.sliderBottom;
\t\t}
\t\tconst int suspiciousOutside = std::max(30, det.sliderHeight / 2);
\t\tconst bool staleSuspicious = loop.stableFishFrames >= 6 && outsideDistance > suspiciousOutside;
\t\tconst bool periodicVerify = loop.fastDetectFrames >= 180;

\t\tif (staleSuspicious || periodicVerify) {
\t\t\tFishSliderResult fullDet{};
\t\t\tint bestIdx = 0;
\t\t\tconst bool fullOk = detectFishAndSliderFull(
\t\t\t\tgray,
\t\t\t\tmatchRoi,
\t\t\t\truntime_.templates(),
\t\t\t\tconfig,
\t\t\t\tloop.cachedTrackScale,
\t\t\t\tloop.cachedTrackAngle,
\t\t\t\t&fullDet,
\t\t\t\t&bestIdx);
\t\t\tdidFullDetect = true;

\t\t\tif (fullOk) {
\t\t\t\tconst int oldFishY = det.fishY;
\t\t\t\tdet = fullDet;
\t\t\t\tloop.cachedFishTplIdx = bestIdx;
\t\t\t\tloop.hasCachedFishTpl = true;
\t\t\t\tloop.fastDetectFrames = 0;
\t\t\t\tloop.stableFishFrames = 0;
\t\t\t\tif ((staleSuspicious || std::abs(det.fishY - oldFishY) > 20) &&
\t\t\t\t\t(config.vr_debug || runtime_.hasVrLogFile())) {
\t\t\t\t\tstd::ostringstream oss;
\t\t\t\t\toss << "[recover] full fish verify oldY=" << oldFishY
\t\t\t\t\t\t<< " newY=" << det.fishY
\t\t\t\t\t\t<< " tpl=" << bestIdx
\t\t\t\t\t\t<< (staleSuspicious ? " stale" : " periodic");
\t\t\t\t\twriteVrLogLine(oss.str(), config.vr_debug);
\t\t\t\t}
\t\t\t} else {
\t\t\t\t// Force an all-template search again on the following frame instead of
\t\t\t\t// staying permanently committed to a suspicious cached template.
\t\t\t\tloop.hasCachedFishTpl = false;
\t\t\t\tloop.fastDetectFrames = 0;
\t\t\t\tloop.stableFishFrames = 0;
\t\t\t}
\t\t}
\t}
'''.replace('\\t', '\t')
replace_once(old_detect, new_detect, 'detector recovery block')

old_jump = r'''\tif (loop.hasPrevFish) {
\t\tconst int fishJump = std::abs(det.fishY - loop.prevFishY);
\t\tif (fishJump > config.fish_jump_threshold) {
\t\t\tdet.fishY = loop.prevFishY;
\t\t}
\t}
'''.replace('\\t', '\t')

new_jump = r'''\tif (loop.hasPrevFish) {
\t\tconst int fishJump = std::abs(det.fishY - loop.prevFishY);
\t\tif (fishJump > config.fish_jump_threshold) {
\t\t\t// Difficult fish can legitimately teleport farther than the old one-frame
\t\t\t// jump guard allowed. Hold only the first suspicious frame, force a FULL
\t\t\t// search, then accept a consistent second observation.
\t\t\tint tolerance = config.fish_jump_threshold / 2;
\t\t\tif (tolerance < 20) tolerance = 20;
\t\t\tconst bool confirmsPending = didFullDetect && loop.hasPendingFish &&
\t\t\t\tstd::abs(det.fishY - loop.pendingFishY) <= tolerance;

\t\t\tif (confirmsPending) {
\t\t\t\tif (config.vr_debug || runtime_.hasVrLogFile()) {
\t\t\t\t\tstd::ostringstream oss;
\t\t\t\t\toss << "[recover] confirmed fish jump oldY=" << loop.prevFishY
\t\t\t\t\t\t<< " newY=" << det.fishY
\t\t\t\t\t\t<< " jump=" << fishJump;
\t\t\t\t\twriteVrLogLine(oss.str(), config.vr_debug);
\t\t\t\t}
\t\t\t\tloop.hasPendingFish = false;
\t\t\t\t// Accept the teleport but reset motion history so it is not interpreted
\t\t\t\t// as an enormous velocity/acceleration spike by the controller.
\t\t\t\tloop.hasPrevFish = false;
\t\t\t\tloop.smoothFishVel = 0.0;
\t\t\t\tloop.prevSmoothFishVel = 0.0;
\t\t\t\tloop.smoothFishAccel = 0.0;
\t\t\t\tloop.hasPrevDeviation = false;
\t\t\t} else {
\t\t\t\tloop.pendingFishY = det.fishY;
\t\t\t\tloop.hasPendingFish = true;
\t\t\t\tloop.hasCachedFishTpl = false;
\t\t\t\tdet.fishY = loop.prevFishY;
\t\t\t}
\t\t} else {
\t\t\tloop.hasPendingFish = false;
\t\t}
\t} else {
\t\tloop.hasPendingFish = false;
\t}
'''.replace('\\t', '\t')
replace_once(old_jump, new_jump, 'large-jump confirmation block')

p.write_text(s, encoding='utf-8')
print('Applied Pharaoh recovery source changes successfully.')
