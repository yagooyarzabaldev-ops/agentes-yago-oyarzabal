"""Build comparable music previews using the same complete voice and copied video.

Usage: python scripts/musica_opciones/comparar.py --music-dir runtime/new-score
  --voice path/to/voice.wav --video path/to/video.mp4 --output-dir runtime/new-mixes

Requires a componer.py provenance manifest. All options use the same normalization
and ducking. Preview: solo excerpt + gap + complete voice mix. Source files are
hashed and preserved. This local CLI does not publish, call APIs or install tools.
Use --sample-start and --sample-duration when the defaults exceed a short piece.
"""
from pathlib import Path
import argparse
import math

from _audio import child, duration, ffmpeg, measure, new_directory, normalize, read, sha, video_hash, write


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--music-dir', type=Path, required=True)
    parser.add_argument('--voice', type=Path, required=True)
    parser.add_argument('--video', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True, help='New or empty output directory.')
    parser.add_argument('--sample-start', type=float, default=8)
    parser.add_argument('--sample-duration', type=float, default=8)
    parser.add_argument('--gap', type=float, default=.3)
    args = parser.parse_args(argv)
    if not all(math.isfinite(v) for v in (args.sample_start, args.sample_duration, args.gap)):
        parser.error('Sample timings must be finite')
    if args.sample_start < 0 or args.sample_duration <= 0 or args.gap <= 0:
        parser.error('Sample start must be nonnegative, and duration/gap positive')
    provenance = read(args.music_dir / 'procedencia.json')
    options = provenance['options']
    if not options or len({o['id'] for o in options}) != len(options):
        parser.error('Expected at least one option and unique IDs')
    video_seconds, voice_seconds = duration(args.video, 'video'), duration(args.voice)
    duration(args.video, 'audio')  # The reference MP3 requires existing video audio.
    if voice_seconds > video_seconds + 1 / 48000:
        parser.error('Video is shorter than the voice; narration would be truncated')
    before = {'video': sha(args.video), 'voice': sha(args.voice)}
    picture_hash = video_hash(args.video)
    for option in options:
        source = child(args.music_dir, option['file'])
        if sha(source) != option['sha256']:
            parser.error(f'Music hash differs from provenance: {option["id"]}')
        seconds = duration(source)
        if seconds + 1 / 48000 < video_seconds or seconds < args.sample_start + args.sample_duration:
            parser.error(f'Music too short for video or solo excerpt: {option["id"]}')
    output = new_directory(args.output_dir)
    logs = output / 'logs'
    logs.mkdir()
    manifest = {
        'schema_version': 1, 'source_video': str(args.video.resolve()), 'voice': str(args.voice.resolve()),
        'music_dir': str(args.music_dir.resolve()), 'source_video_sha256_before': before['video'],
        'voice_sha256': before['voice'], 'source_video_stream_hash': picture_hash,
        'duration_seconds': video_seconds, 'voice_duration_seconds': voice_seconds,
        'comparison_method': {'instrumental_lufs_target': -16.5, 'mix_lufs_target': -14.4,
            'mix_peak_ceiling_dbtp': -2.5, 'music_gain_before_ducking': .11,
            'ducking': {'threshold': .045, 'ratio': 5, 'attack_ms': 10, 'release_ms': 180},
            'solo_start_seconds': args.sample_start, 'solo_duration_seconds': args.sample_duration,
            'gap_seconds': args.gap, 'mix_duration_seconds': video_seconds},
        'perceptual_listening': False, 'options': []}
    for option in options:
        source = child(args.music_dir, option['file'])
        prefix = source.stem
        music = output / (prefix + '_instrumental.wav')
        music_metrics = normalize(source, music, -16.5, -3, logs)
        music_mp3 = output / (prefix + '_instrumental.mp3')
        ffmpeg('-v', 'error', '-n', '-i', music, '-c:a', 'libmp3lame', '-b:a', '256k', music_mp3)
        raw = output / (prefix + '_mezcla_cruda.wav')
        # Pad each input to the picture duration; never cut the supplied narration.
        graph = (f'[0:a]apad,atrim=duration={video_seconds},asplit=2[v][sc];'
                 f'[1:a]apad,atrim=duration={video_seconds},volume=0.11[m];'
                 '[m][sc]sidechaincompress=threshold=0.045:ratio=5:attack=10:release=180[duck];'
                 '[v][duck]amix=inputs=2:normalize=0:duration=first[a]')
        ffmpeg('-v', 'error', '-n', '-i', args.voice, '-i', music, '-filter_complex', graph,
               '-map', '[a]', '-ar', '48000', '-ac', '2', '-c:a', 'pcm_s24le', raw)
        master = output / (prefix + '_con_voz.wav')
        mix_metrics = normalize(raw, master, -14.4, -2.5, logs)
        reel = output / (prefix + '_reel.mp4')
        ffmpeg('-v', 'error', '-n', '-i', args.video, '-i', master, '-map', '0:v:0', '-map', '1:a:0',
               '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-t', video_seconds, '-movflags', '+faststart', reel)
        audition = output / (prefix + '_comparacion.mp3')
        fade_out = min(.3, args.sample_duration / 3)
        graph = (f'[0:a]atrim=start={args.sample_start}:duration={args.sample_duration},asetpts=PTS-STARTPTS,'
                 f'afade=t=in:d={min(.03, args.sample_duration / 4)},'
                 f'afade=t=out:st={args.sample_duration-fade_out}:d={fade_out}[solo];'
                 f'anullsrc=r=48000:cl=stereo,atrim=duration={args.gap}[gap];'
                 '[1:a]asetpts=PTS-STARTPTS[voice];[solo][gap][voice]concat=n=3:v=0:a=1[a]')
        ffmpeg('-v', 'error', '-n', '-i', music, '-i', master, '-filter_complex', graph,
               '-map', '[a]', '-ar', '48000', '-c:a', 'libmp3lame', '-b:a', '256k', audition)
        files = {'instrumental_wav': music, 'instrumental_mp3': music_mp3,
                 'mix_wav': master, 'reel': reel, 'audition': audition}
        manifest['options'].append({'id': option['id'], 'bpm': option['bpm'],
            'source_wav': option['file'], 'source_sha256': sha(source),
            'files': {key: path.name for key, path in files.items()},
            'sha256': {key: sha(path) for key, path in files.items()},
            'music_metrics': music_metrics, 'mix_metrics': mix_metrics,
            'encoded_reel_metrics': measure(reel)})
        print(f'{option["id"]}: comparison artifacts created', flush=True)
    # Existing mixed audio is a reference with a different layout than auditions.
    baseline = output / '00_base_audio.mp3'
    ffmpeg('-v', 'error', '-n', '-i', args.video, '-vn', '-c:a', 'libmp3lame', '-b:a', '256k', baseline)
    manifest['baseline_audio'] = baseline.name
    manifest['baseline_audio_sha256'] = sha(baseline)
    manifest['source_video_sha256_after'] = sha(args.video)
    if before != {'video': sha(args.video), 'voice': sha(args.voice)}:
        raise RuntimeError('A source changed during comparison')
    write(output / 'comparacion-y-procedencia.json', manifest)
    print('Complete. Run revisar.py for independent technical checks; listening remains pending.')


if __name__ == '__main__':
    main()
