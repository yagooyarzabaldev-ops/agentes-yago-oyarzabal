"""Independently review generated music comparisons without claiming listening.

Usage: python scripts/musica_opciones/revisar.py --comparison-dir runtime/new-mixes
  --music-dir runtime/new-score --voice path/to/voice.wav --video path/to/video.mp4
  --output-dir runtime/new-qa

Checks complete decodes, metadata, post-encoding loudness, copied video packets,
input and output hashes, score events, durations and distinct waveforms.
Returns nonzero for technical findings. Does not prove subjective musical quality.
"""
from pathlib import Path
import argparse
import collections
import itertools
import math
import numpy as np

from _audio import child, duration, ffmpeg, measure, new_directory, probe, read, sha, strict_decode, video_hash, write


def pcm(path):
    return np.frombuffer(ffmpeg('-v', 'error', '-i', path, '-vn', '-ac', '1', '-ar', '16000',
                               '-f', 'f32le', '-').stdout, dtype='<f4')


def inspect(path, logs):
    fingerprint = sha(path)
    strict_decode(path, logs / (path.stem + '-decode.log'))
    audio = pcm(path)
    loudness = measure(path, log=logs / (path.stem + '-loudness.log'))
    if sha(path) != fingerprint:
        raise RuntimeError(f'File changed during QA: {path}')
    return {'file': path.name, 'sha256': fingerprint, 'bytes': path.stat().st_size,
            'decoded_audio_seconds': len(audio) / 16000, 'probe': probe(path),
            'lufs': float(loudness['input_i']), 'true_peak_dbtp': float(loudness['input_tp']),
            'strict_decode_passed': True}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for name in ('comparison-dir', 'music-dir', 'voice', 'video', 'output-dir'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args(argv)
    comparison = read(args.comparison_dir / 'comparacion-y-procedencia.json')
    provenance = read(args.music_dir / 'procedencia.json')
    output = new_directory(args.output_dir)
    logs = output / 'logs'
    logs.mkdir()
    issues, results, signals = [], {}, {}
    picture_hash, video_digest, voice_digest = video_hash(args.video), sha(args.video), sha(args.voice)
    expected_seconds = duration(args.video, 'video')
    method = comparison['comparison_method']
    if video_digest != comparison['source_video_sha256_before'] or video_digest != comparison['source_video_sha256_after']:
        issues.append('Video source hash changed or does not match comparison.')
    if voice_digest != comparison['voice_sha256']:
        issues.append('Voice source hash changed or does not match comparison.')
    if abs(expected_seconds - comparison['duration_seconds']) > .01:
        issues.append('Video duration differs from comparison metadata.')
    if duration(args.voice) > expected_seconds + 1 / 48000:
        issues.append('Complete narration does not fit the video.')
    for option in comparison['options']:
        key = option['id']
        row = {'files': {}}
        paths = {kind: child(args.comparison_dir, name) for kind, name in option['files'].items()}
        for kind, path in paths.items():
            row['files'][kind] = inspect(path, logs)
            check = row['files'][kind]
            if check['sha256'] != option['sha256'][kind]:
                issues.append(f'{key}/{kind}: hash differs from comparison manifest.')
            if check['true_peak_dbtp'] >= 0:
                issues.append(f'{key}/{kind}: true peak reaches 0 dBTP.')
        row['picture_bitstream_identical'] = video_hash(paths['reel']) == picture_hash
        if not row['picture_bitstream_identical']:
            issues.append(f'{key}: copied video stream differs.')
        for kind in ('reel', 'mix_wav'):
            if abs(row['files'][kind]['decoded_audio_seconds'] - expected_seconds) > .06:
                issues.append(f'{key}/{kind}: full mix duration differs.')
        audition_seconds = expected_seconds + method['solo_duration_seconds'] + method['gap_seconds']
        if abs(row['files']['audition']['decoded_audio_seconds'] - audition_seconds) > .025:
            issues.append(f'{key}: audition duration differs from solo/gap/full-voice layout.')
        row['audition_sections'] = {
            'solo': measure(paths['audition'], start=0, seconds=method['solo_duration_seconds'],
                            log=logs / (key + '-audition-solo.log')),
            'voice_mix': measure(paths['audition'], start=method['solo_duration_seconds'] + method['gap_seconds'],
                                 log=logs / (key + '-audition-voice.log'))}
        decoded_audition = pcm(paths['audition'])
        # Exclude encoder ringing at either edge of the intentional silent gap.
        margin = min(.05, method['gap_seconds'] / 4)
        gap_start = round((method['solo_duration_seconds'] + margin) * 16000)
        gap_end = round((method['solo_duration_seconds'] + method['gap_seconds'] - margin) * 16000)
        gap = decoded_audition[gap_start:gap_end]
        row['audition_gap_interior_peak_dbfs'] = 20 * math.log10(max(float(np.max(np.abs(gap))), 1e-15))
        if row['audition_gap_interior_peak_dbfs'] > -40:
            issues.append(f'{key}: intended comparison gap is not silent.')
        if not -15.1 <= row['files']['reel']['lufs'] <= -13.6 or row['files']['reel']['true_peak_dbtp'] > -2:
            issues.append(f'{key}: encoded reel loudness or peak outside comparison target.')
        score = next(o for o in provenance['options'] if o['id'] == key)
        source = child(args.music_dir, score['file'])
        events_file = child(args.music_dir, key + '/eventos.json')
        events = read(events_file)
        counts = dict(collections.Counter(event['instrument'] for event in events))
        notes = [e['note_midi'] for e in events if e['note_midi'] is not None]
        row['composition'] = {'bpm': score['bpm'], 'arrangement': score['arrangement'],
            'event_count': len(events), 'instrument_counts': counts, 'events_sha256': sha(events_file),
            'minimum_pitched_midi': min(notes),
            'no_bass_events_in_authored_score': not any('bass' in e['instrument'].lower() for e in events)}
        if sha(source) != score['sha256'] or sha(source) != option['source_sha256'] or counts != score['instrument_counts']:
            issues.append(f'{key}: source music or score provenance mismatch.')
        if len(events) != score['events']:
            issues.append(f'{key}: score event count mismatch.')
        signals[key] = pcm(paths['instrumental_wav'])
        results[key] = row
        print(f'{key}: technical review completed', flush=True)
    spreads = {}
    for kind in ('instrumental_wav', 'instrumental_mp3', 'mix_wav', 'reel'):
        values = {key: row['files'][kind]['lufs'] for key, row in results.items()}
        spread = max(values.values()) - min(values.values())
        spreads[kind] = {'lufs': values, 'spread_lu': spread}
        if spread > .5:
            issues.append(f'{kind}: inter-option loudness spread exceeds 0.5 LU.')
    pairs = []
    for first, second in itertools.combinations(results, 2):
        n = min(len(signals[first]), len(signals[second]))
        x, y = signals[first][:n].astype(float), signals[second][:n].astype(float)
        x /= math.sqrt(float(np.mean(x*x)))
        y /= math.sqrt(float(np.mean(y*y)))
        pairs.append({'pair': [first, second], 'normalized_correlation': float(np.corrcoef(x,y)[0,1]),
                      'rms_normalized_difference': float(np.sqrt(np.mean((x-y)**2))),
                      'event_files_differ': results[first]['composition']['events_sha256'] != results[second]['composition']['events_sha256']})
    baseline = child(args.comparison_dir, comparison['baseline_audio'])
    baseline_check = inspect(baseline, logs)
    if sha(baseline) != comparison['baseline_audio_sha256']:
        issues.append('Reference audio hash differs from comparison manifest.')
    if sha(args.video) != video_digest or sha(args.voice) != voice_digest:
        issues.append('A source changed during QA.')
    report = {'status': 'technical_findings_require_review' if issues else 'technical_checks_passed_no_perceptual_listening',
        'options': results, 'loudness_comparison': spreads, 'signal_distinctness': pairs,
        'baseline_audio': baseline_check, 'source_video_sha256': video_digest, 'voice_sha256': voice_digest,
        'findings': issues, 'perceptual_listening': False,
        'limitations': ['Signal differences and score events do not certify musical quality or novelty.',
                       'No audible-click, voice naturalness, comfort or subjective no-bass claim.',
                       'Source voice is reused without edits; perceptual synchronization still needs review.']}
    write(output / 'calidad.json', report)
    print(report['status'], flush=True)
    return 1 if issues else 0


if __name__ == '__main__':
    raise SystemExit(main())
