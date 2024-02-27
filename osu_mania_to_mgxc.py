from osupyparser import OsuFile
import sys
from osupyparser.osu.objects import TimingPoint, HitObject
import re
import uuid
from typing import List, Dict, Tuple
KEY_CNT_TO_KEY_WIDTH_MAPPING = {
    1: {0: (0, 16)},
    2: {0: (0, 8), 1: (8, 8)},
    3: {0: (0, 4), 1: (4, 8), 2: (12, 4)},
    4: {0: (0, 4), 1: (4, 4), 2: (8, 4), 3: (12, 4)},
    5: {0: (0, 3), 1: (3, 3), 2: (6, 4), 3: (10, 3), 4: (13, 3)},
    6: {0: (0, 3), 1: (3, 2), 2: (5, 3), 3: (8, 3), 4: (11, 2), 5: (13, 3)},
    7: {0: (0, 2), 1: (2, 2), 2: (4, 2), 3: (6, 4), 4: (10, 2), 5: (12, 2), 6: (14, 2)},
    8: {0: (0, 2), 1: (2, 2), 2: (4, 2), 3: (6, 2), 4: (8, 2), 5: (10, 2), 6: (12, 2), 7: (14, 2)},
}


def pLine(*args):
    print(*args, sep='\t', file=mgxcFile)


def pErr(*args):
    print(*args, file=sys.stderr)


LV_REGEX = re.compile(r'.*\[(\d\d?)\].*')


def getLevel(version):
    m = LV_REGEX.match(version)
    if m:
        return m[1]
    return '1'


BEAT_TICK_LEN = 480


def printTimePoints(timePoints: List[TimingPoint]):
    bpms = set(tp.bpm for tp in timePoints if tp.bpm is not None)

    if len(bpms) > 1:
        raise ValueError('cannot support changing of BPM')

    timePoints.sort(key=lambda tp: tp.offset)

    tp1 = timePoints[0]

    beatCount = 0.0
    sectionCount = 0.0
    for i, tp in enumerate(timePoints):
        if i != len(timePoints) - 1:
            nextTp = timePoints[i+1]
        else:
            nextTp = None

        if i != 0:
            lastTp = timePoints[i-1]
        else:
            lastTp = None

        beatTick = round(beatCount * BEAT_TICK_LEN)

        if lastTp is None or lastTp.time_signature != tp.time_signature:
            if abs(sectionCount - round(sectionCount)) > 0.001:
                pErr('WARNING: changing beat signature not at the begining of section')
            else:
                pLine('BEAT', round(sectionCount), tp.time_signature, '4')
        if lastTp is None or lastTp.velocity != tp.velocity:
            pLine('TIL', '0', beatTick, tp.velocity)

        if nextTp is None:
            continue

        durationMs = nextTp.offset - tp.offset
        beatCount += durationMs / tp1.beat_length
        sectionCount += durationMs / tp1.beat_length / tp.time_signature
    pLine('BPM', '0', tp1.bpm)


def printNotes(timePoint1st: TimingPoint,
               hitObjects: List[HitObject],
               keyCount: int):

    keyWidthMapping = KEY_CNT_TO_KEY_WIDTH_MAPPING[keyCount]

    def timeToTick(time): return max(0,
                                     round((time - timePoint1st.offset) /
                                           timePoint1st.beat_length * BEAT_TICK_LEN))
    for o in hitObjects:
        osuKeyPos = o.pos.x * keyCount // 512
        chuKey = keyWidthMapping[osuKeyPos]
        tick = timeToTick(o.start_time)
        if o.type & 1:
            pLine('t', 'N', 'N', 'N', tick,
                  chuKey[0], chuKey[1], 8, 0, 0)
        else:
            pLine('h', 'BG', 'N', 'N', tick,
                  chuKey[0], chuKey[1], 8, 0, 0)
            pLine('.h', 'EN', 'N', 'N', timeToTick(int(o.additions.normal)),
                  chuKey[0], chuKey[1], 8, 0, 0)


def osuManiaToMgxc(osuFilename):
    data = OsuFile(osuFilename).parse_file()
    keyCount = int(data.cs)
    tp1 = data.timing_points[0]

    pLine('MGCF0')
    pLine('VERSION', '2')
    pLine('BEGIN', 'META')
    pLine('TITLE', data.title_unicode)
    pLine('ARTIST', data.artist_unicode)
    pLine('DESIGNER', data.creator)
    pLine('DIFFICULTY', '3')
    pLine('PLAYLEVEL', getLevel(data.version))
    pLine('WEATTRIBUTE', '')
    pLine('CHARTCONST', getLevel(data.version))
    pLine('SONGID', str(uuid.uuid4()))
    pLine('BGM', data.audio_filename)
    pLine('BGMOFFSET', -tp1.offset / 1000)
    pLine('BGMPREVIEW', '0.00000', '15.00000')
    pLine('JACKET', '')
    pLine('BG', data.background_file)
    pLine('BGSCENE', '')
    pLine('BGSYNC', '1')
    pLine('FIELDCOL', '0')
    pLine('FIELDBG', '')
    pLine('FIELDSCENE', '')
    pLine('MAINTIL', '0')
    pLine('MAINBPM', tp1.bpm)
    pLine('TUTORIAL', '0')
    pLine('SOFFSET', '1')
    pLine('USECLICK', '1')
    pLine('EXLONG', '0')
    pLine('BGMWAITEND', '0')
    pLine('AUTHOR_LIST', '')
    pLine('AUTHOR_SITES', '')
    pLine('DLURL', '')
    pLine('COPYRIGHT', '')
    pLine('LICENSE', '', '')
    pLine('BEGIN', 'HEADER')
    printTimePoints(data.timing_points)
    pLine('BEGIN', 'NOTES')
    printNotes(tp1, data.hit_objects, keyCount)


mgxcFile = sys.stdout

if __name__ == '__main__':
    if len(sys.argv) < 3:
        raise ValueError(
            f'require 3 parameters but got {len(sys.argv) - 1} only')
    osuFilename = sys.argv[1]
    mgxcFilename = sys.argv[2]
    # osuFilename = '.\_icerain6k.osu'
    with open(mgxcFilename, 'w', newline='') as f:
        mgxcFile = f
        osuManiaToMgxc(osuFilename)

a = [
    TimingPoint(
        offset=169.0, beat_length=451.127819548872,
        time_signature=4, sample_set_id=2, custom_sample_index=0,
        sample_volume=5, timing_change=True, kiai_time_active=False,
        velocity=1, bpm=133),
    TimingPoint(offset=61523.0, beat_length=-133.333333333333, time_signature=2,
                sample_set_id=2, custom_sample_index=0, sample_volume=5, timing_change=False,
                kiai_time_active=False, velocity=0.7500000000000019, bpm=None),
    TimingPoint(offset=63328.0, beat_length=-100.0, time_signature=4, sample_set_id=2, custom_sample_index=0, sample_volume=5, timing_change=False, kiai_time_active=False,
                velocity=1.0, bpm=None)]
