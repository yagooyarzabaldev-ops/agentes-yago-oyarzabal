"""Meaningful local checks for track identity, sample-zero edits and gentle ducking."""
from pathlib import Path
from contextlib import redirect_stderr
import importlib.util
import io
import json
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave

try:
    import numpy as np
except ImportError:
    np=None

ROOT=Path(__file__).resolve().parents[1]
SCRIPT_DIR=ROOT/'scripts/musica_opciones'


@unittest.skipIf(np is None,'NumPy is required for local audio tests')
class MusicTrackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0,str(SCRIPT_DIR))
        try:
            spec=importlib.util.spec_from_file_location('tested_music_track',SCRIPT_DIR/'usar_track.py')
            cls.module=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.module)
        finally:
            sys.path.pop(0)

    def test_ducking_has_bounded_speech_reduction_and_recovers_in_pauses(self):
        rate=self.module.SR
        t=np.arange(6*rate)/rate
        music=np.column_stack((.15*np.sin(2*np.pi*331*t),.12*np.sin(2*np.pi*517*t)))
        voice_signal=.25*np.sin(2*np.pi*173*t)*(((t>=.5)&(t<2))|((t>=3.5)&(t<5)))
        voice=np.column_stack((voice_signal,voice_signal))
        original=voice.copy()
        ducked,summary,envelope=self.module.sidechain(voice,music,-28,2,8,6,20,280)
        self.assertTrue(np.array_equal(voice,original),'The sidechain must not edit its voice source')
        self.assertGreater(summary['speech_reduction_percentiles_db']['p50'],3)
        self.assertLessEqual(summary['measured_maximum_db'],6.01)
        self.assertGreater(summary['pauses_at_least150ms'][1]['recovered_db'],4)
        # Independent RMS measurement of stable speech and the end of a real pause.
        active=slice(round(1.4*rate),round(1.8*rate));pause=slice(round(3.1*rate),round(3.4*rate))
        speech_ratio=np.sqrt(np.mean(ducked[active]**2)/np.mean(music[active]**2))
        pause_ratio=np.sqrt(np.mean(ducked[pause]**2)/np.mean(music[pause]**2))
        self.assertLess(speech_ratio,.71)
        self.assertGreater(pause_ratio,.96)
        self.assertGreater(np.min(np.diff(envelope['seconds'])),0)

    @unittest.skipUnless(shutil.which('ffmpeg'),'Local FFmpeg unavailable')
    def test_excerpt_keeps_decoded_sample_zero_and_exact_prefix(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'source.wav';excerpt=Path(folder)/'excerpt.wav'
            # Distinct nonperiodic stereo input catches seek offsets, looping and retiming.
            rng=np.random.default_rng(1703)
            values=rng.integers(-9000,9000,(48000,2),dtype=np.int16)
            values[0]=[12345,-23456]
            with wave.open(str(source),'wb') as stream:
                stream.setnchannels(2);stream.setsampwidth(2);stream.setframerate(48000)
                stream.writeframes(values.astype('<i2').tobytes())
            result=self.module.extract_prefix(source,excerpt,24000)
            expected=values[:24000].astype(float)/32768
            np.testing.assert_array_equal(result,expected)
            self.assertEqual(len(result),24000)

    def test_short_source_rejected_before_creating_outputs(self):
        with tempfile.TemporaryDirectory() as folder:
            output=Path(folder)/'must-not-exist';work=Path(folder)/'also-must-not-exist'
            def metadata(path,kind='audio'):
                return {'track.wav':2,'voice.wav':3,'video.mp4':3}[Path(path).name]
            args=['--track','track.wav','--voice','voice.wav','--video','video.mp4',
                  '--output-dir',str(output),'--work-dir',str(work),'--rights-note','Test fixtures']
            messages=io.StringIO()
            with patch.object(self.module,'duration',side_effect=metadata),redirect_stderr(messages):
                with self.assertRaises(SystemExit) as error:self.module.main(args)
            self.assertEqual(error.exception.code,2)
            self.assertIn('Track is shorter than the video',messages.getvalue())
            self.assertFalse(output.exists());self.assertFalse(work.exists())

    def test_default_profile_requires_mode_and_exact_hash(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);asset=root/'private.mp3';asset.write_bytes(b'owned source fixture')
            profile=root/'profile.json'
            profile.write_text(json.dumps({'music':{'mode':'user_track','asset_path':'private.mp3',
                                                    'source_sha256':self.module.sha(asset)}}),encoding='utf-8')
            selected,metadata=self.module.resolve_track(None,profile,root)
            self.assertEqual(selected,asset);self.assertEqual(metadata['selection'],'profile_default')
            asset.write_bytes(b'changed source')
            with self.assertRaisesRegex(ValueError,'SHA256'):self.module.resolve_track(None,profile,root)
            profile.write_text('{"music":{"mode":"synthesis"}}',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'not user_track'):self.module.resolve_track(None,profile,root)
            selected,metadata=self.module.resolve_track(asset,profile,root)
            self.assertEqual(selected,asset);self.assertEqual(metadata['selection'],'explicit_cli_override')


if __name__=='__main__':unittest.main()
