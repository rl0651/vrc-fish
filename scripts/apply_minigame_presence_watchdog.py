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
'''\tint pendingFishY{};\n\tbool hasPendingFish{};\n\tint recordFrame{};''',
'''\tint pendingFishY{};\n\tbool hasPendingFish{};\n\tint minigamePresenceTick{};\n\tint minigamePresenceMisses{};\n\tint recordFrame{};''',
'presence watchdog fields')

replace_once(
'''\tloop.pendingFishY = 0;\n\tloop.hasPendingFish = false;\n\n\tif (config.ml_mode == 1) {''',
'''\tloop.pendingFishY = 0;\n\tloop.hasPendingFish = false;\n\tloop.minigamePresenceTick = 0;\n\tloop.minigamePresenceMisses = 0;\n\n\tif (config.ml_mode == 1) {''',
'presence watchdog reset')

anchor = '''\tconst cv::Rect matchRoi = loop.fixedTrackRoi;\n\tFishSliderResult det{};'''
watchdog = '''\t// Independent minigame-presence watchdog. Fish/slider templates can produce\n\t// plausible false positives after the round has already ended, which would\n\t// otherwise keep ControlMinigame alive forever. Periodically verify that the\n\t// full minigame track itself still exists near the locked ROI.\n\tloop.minigamePresenceTick++;\n\tif (loop.minigamePresenceTick >= 24) {\n\t\tloop.minigamePresenceTick = 0;\n\n\t\tdouble presenceScale = 1.0;\n\t\tdouble presenceAngle = 0.0;\n\t\tTplMatch presence = matchBestRoiTrackBarAutoScale(\n\t\t\tgray,\n\t\t\truntime_.templates().minigameBarFull,\n\t\t\tsearchRoi,\n\t\t\tconfig,\n\t\t\tcv::TM_CCOEFF_NORMED,\n\t\t\t&presenceScale,\n\t\t\t&presenceAngle);\n\n\t\tbool presenceOk = presence.score >= config.minigame_threshold;\n\t\tif (presenceOk) {\n\t\t\t// Reject a high-scoring match that is nowhere near the ROI we originally\n\t\t\t// locked. This reduces the chance of background scenery passing the check.\n\t\t\tconst int presenceCY = presence.rect.y + presence.rect.height / 2;\n\t\t\tconst int lockedCY = loop.fixedTrackRoi.y + loop.fixedTrackRoi.height / 2;\n\t\t\tconst int yTolerance = std::max(100, loop.fixedTrackRoi.height / 2);\n\t\t\tpresenceOk = std::abs(presenceCY - lockedCY) <= yTolerance;\n\t\t}\n\n\t\tif (presenceOk) {\n\t\t\tif (loop.minigamePresenceMisses > 0 && (config.vr_debug || runtime_.hasVrLogFile())) {\n\t\t\t\tstd::ostringstream oss;\n\t\t\t\toss << "[presence] minigame recovered score=" << presence.score;\n\t\t\t\twriteVrLogLine(oss.str(), config.vr_debug);\n\t\t\t}\n\t\t\tloop.minigamePresenceMisses = 0;\n\t\t} else {\n\t\t\tloop.minigamePresenceMisses++;\n\t\t\tif (config.vr_debug || runtime_.hasVrLogFile()) {\n\t\t\t\tstd::ostringstream oss;\n\t\t\t\toss << "[presence] minigame MISS " << loop.minigamePresenceMisses\n\t\t\t\t\t<< "/2 score=" << presence.score;\n\t\t\t\twriteVrLogLine(oss.str(), config.vr_debug);\n\t\t\t}\n\n\t\t\tif (loop.minigamePresenceMisses >= 2) {\n\t\t\t\tif (loop.holding) {\n\t\t\t\t\truntime_.mouseLeftUp();\n\t\t\t\t\tloop.holding = false;\n\t\t\t\t}\n\t\t\t\tif (config.vr_debug || runtime_.hasVrLogFile()) {\n\t\t\t\t\twriteVrLogLine("[presence] minigame absent -> reset/recast", config.vr_debug);\n\t\t\t\t}\n\t\t\t\tsaveDebugFrame(frame, "presence_watchdog_end", searchRoi, presence.rect);\n\t\t\t\tswitchState(loop, VrFishState::PostMinigame);\n\t\t\t\tsleepControlInterval();\n\t\t\t\treturn;\n\t\t\t}\n\t\t}\n\t}\n\n\t// Last-resort failsafe. A normal fishing round should never spend four\n\t// minutes continuously in ControlMinigame. This protects against any future\n\t// detector failure mode without affecting normal or difficult fish.\n\tif (nowMs() - loop.stateStart > 240000ULL) {\n\t\tif (loop.holding) {\n\t\t\truntime_.mouseLeftUp();\n\t\t\tloop.holding = false;\n\t\t}\n\t\tif (config.vr_debug || runtime_.hasVrLogFile()) {\n\t\t\twriteVrLogLine("[presence] 240s control timeout -> reset/recast", config.vr_debug);\n\t\t}\n\t\tswitchState(loop, VrFishState::PostMinigame);\n\t\tsleepControlInterval();\n\t\treturn;\n\t}\n\n\tconst cv::Rect matchRoi = loop.fixedTrackRoi;\n\tFishSliderResult det{};'''
replace_once(anchor, watchdog, 'presence watchdog insertion')

p.write_text(s, encoding='utf-8')
print('Applied minigame presence watchdog successfully.')
