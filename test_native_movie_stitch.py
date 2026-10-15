"""Exercise native Movie export with apostrophes, spaces, two colors and audio."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
for name in ('binary','ffmpeg-bin','output','report'):
    parser.add_argument('--'+name, required=True, type=Path)
args = parser.parse_args()
ff = args.ffmpeg_bin
suffix = '.exe' if os.name == 'nt' else ''
encoder = str(ff/('ffmpeg'+suffix))
env = os.environ.copy()
env['PATH'] = str(ff)+os.pathsep+env.get('PATH','')
with tempfile.TemporaryDirectory(prefix="MM-Air's movie ") as work:
    clips = []
    for i,color in enumerate(('red','blue')):
        clip = Path(work)/f'take {i}.mp4'
        subprocess.run([encoder,'-v','error','-nostdin','-f','lavfi','-i',
                        f'color=c={color}:s=320x240:r=24:d=3','-f','lavfi','-i',
                        f'sine=frequency={440+i*440}:sample_rate=48000:duration=3',
                        '-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-shortest',str(clip)],
                       check=True,timeout=60)
        clips.append(str(clip))
    p = subprocess.run([str(args.binary.resolve()),*clips,str(args.output.resolve()),work],
                       env=env,capture_output=True,text=True,timeout=180)
    print(p.stdout,p.stderr)
    assert p.returncode == 0,p.returncode
p = subprocess.run([str(ff/('ffprobe'+suffix)),'-v','error','-show_streams',
                    '-show_format','-of','json',str(args.output)],capture_output=True,text=True,check=True)
d = json.loads(p.stdout)
v = next(s for s in d['streams'] if s['codec_type']=='video')
a = next(s for s in d['streams'] if s['codec_type']=='audio')
assert (v['width'],v['height'],v['nb_frames'],v['r_frame_rate'])==(1344,768,'48','24/1'),v
assert abs(float(v['start_time'])) < 0.001,v
assert a['sample_rate']=='48000' and a['channels']==2,a
assert abs(float(d['format']['duration'])-2)<0.06,d['format']
colors = []
for t in ('0.5','1.5'):
    p = subprocess.run([encoder,'-v','error','-ss',t,'-i',str(args.output),'-frames:v','1',
                        '-vf','crop=2:2:672:384','-pix_fmt','rgb24','-f','rawvideo','-'],
                       capture_output=True,check=True)
    colors.append(list(p.stdout[:3]))
assert colors[0][0]>200 and colors[0][2]<30 and colors[1][2]>200 and colors[1][0]<30,colors
r = dict(status='passed',platform=os.name,dimensions=[1344,768],frames=48,fps=24,
         duration_seconds=float(d['format']['duration']),audio_sample_rate=48000,audio_channels=2,
         center_pixels_at_0_5_and_1_5_seconds=colors,
         path_regression='scratch directory contains spaces and apostrophe',
         source_duration_seconds=3,planned_duration_per_shot_seconds=1,
         unfinished_shot_excluded=True,
         synthetic_fixture=True,h3_inference=False)
args.report.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
print(json.dumps(r))
