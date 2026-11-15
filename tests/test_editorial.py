import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from marketing.agents import Agents, BRIEF, EDITORIAL_STAGES, SHOTS, Workflow, validate, validate_script, duration_instructions
from marketing.config import AppError, Config
from marketing.media import render, verify_video
from marketing.store import Store, digest
from marketing.style import check_shots, load_style

ROOT = Path(__file__).resolve().parents[1]


def shot_plan():
    return {'summary': 'Cambio de sistema, ejemplo de prueba', 'shots': [
        {'start': i * 2, 'end': (i + 1) * 2, 'visual_id': f'system-{i}',
         'idea': f'Paso {i}', 'visual': f'Módulo de trabajo {i}',
         'layout': 'split' if i % 2 else 'full', 'palette': ['amber', 'violet', 'emerald'][i % 3],
         'motion': ['assembly', 'truck', 'particles', 'kinetic-type'][i % 4],
         'animation': 'El módulo se separa y conecta con la siguiente tarea',
         'transition': ['cut', 'fold', 'match', 'trace'][i % 4], 'aside_reason': ''}
        for i in range(30)]}


class EditorialAgents:
    def __init__(self):
        self.calls, self.contexts = [], []
        self.fail = None

    def run(self, role, context, schema):
        self.calls.append(role)
        self.contexts.append(copy.deepcopy(context))
        if self.fail == role:
            raise AppError('Interrupción de prueba')
        if role == '01-trend-hunter':
            return {'mode': 'evergreen', 'formats': [
                {'hook': 'Problema real', 'rationale': 'Contexto', 'original_sound': 'Original',
                 'visual_approach': 'Módulos'} for _ in range(5)]}
        if role == '02-guionista':
            return {'title': 'Cambiar cómo trabajamos', 'hook': '¿Dónde se traba?',
                    'segments': [{'spoken': '¿Dónde se traba?' if i == 0 else 'Probamos este cambio.',
                                  'screen': 'El sistema', 'seconds': 3} for i in range(20)],
                    'alternative_hooks': ['Uno', 'Dos', 'Tres'], 'claims_to_verify': [],
                    **({'duration_reason': ''} if 'duration_reason' in schema['properties'] else {})}
        if schema is SHOTS:
            return shot_plan()
        if role == '06-thumbnail-copy':
            return {'youtube_title': 'Cambiar el sistema', 'youtube_description': 'Un ejemplo',
                    'instagram_caption': 'Un ejemplo', 'hashtags': ['#IA'], 'first_comment': '¿Cómo lo hacés?',
                    'covers': ['El sistema', 'Menos pasos', 'Probar primero'], 'image_prompt': 'Módulos ámbar'}
        return {'summary': 'Brief concreto', 'items': ['Entrega para el siguiente especialista']}


class EditorialTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.config = Config(ROOT, env={})
        self.config.runtime = Path(temp.name)
        self.store = Store(self.config.runtime)
        self.agents = EditorialAgents()
        self.workflow = Workflow(self.config, self.store, self.agents)

    def approved(self):
        job = self.store.create('Cambiar el sistema con IA')
        job = self.workflow.draft(job['id'])
        return self.workflow.approve(job['id'], digest(job['script'])[:16])

    def test_default_runs_manager_and_specialists_without_roulette(self):
        job = self.approved()
        result = self.workflow.produce(job['id'])
        self.assertEqual(result['video_format'], 'editorial')
        self.assertEqual(self.agents.calls, ['00-orquestador', '01-trend-hunter', '02-guionista'] +
                         [role for role, _ in EDITORIAL_STAGES])
        self.assertTrue(all(c['style']['id'] == 'infinite-process-editorial-v2' for c in self.agents.contexts))
        self.assertTrue(all(c['style']['format']['duration_seconds'] == [60, 75] for c in self.agents.contexts))
        self.assertIsNone(result['video'])
        self.assertEqual(result['plan_review']['export_review'], 'pending')
        handoff = json.loads((self.store.artifact_dir(result) / 'handoff-produccion.json').read_text(encoding='utf-8'))
        self.assertEqual(handoff['status'], 'plan_ready_render_pending')
        self.assertEqual(handoff['style_sha256'], result['style']['sha256'])

    def test_failed_stage_resumes_without_repeating_completed_agents(self):
        job = self.approved()
        self.agents.fail = '10-musica'
        with self.assertRaises(AppError):
            self.workflow.produce(job['id'])
        self.assertEqual(self.store.get(job['id'])['state'], 'approved')
        self.agents.fail = None
        self.workflow.produce(job['id'])
        self.assertEqual(self.agents.calls.count('09-montaje'), 1)
        self.assertEqual(self.agents.calls.count('10-musica'), 2)

    def test_profile_is_pinned_and_tampering_rejected(self):
        job = self.approved()
        with patch('marketing.style.load_style', side_effect=AssertionError('No recargar perfil')):
            self.workflow.produce(job['id'])
        job = self.store.get(job['id'])
        job['style']['profile']['music']['bass_line'] = True
        self.store.save(job)
        with self.assertRaisesRegex(AppError, 'perfil de estilo'):
            self.workflow.produce(job['id'])

    def test_resume_rechecks_a_modified_plan(self):
        job = self.workflow.produce(self.approved()['id'])
        job['agents']['04-director-visual']['shots'][1]['start'] = 1
        self.store.save(job)
        with self.assertRaises(AppError):
            self.workflow.produce(job['id'])

    def test_editorial_cannot_accidentally_render_old_roulette(self):
        job = self.approved()
        with self.assertRaisesRegex(AppError, 'histórica'):
            render(self.config, self.store, job['id'])

    def test_approved_duration_is_accepted_and_out_of_range_rejected(self):
        info = {'width': 1080, 'height': 1920, 'video_codec': 'h264', 'audio_codec': 'aac',
                'seconds': 67.1, 'fps': 30, 'bytes': 45294969}
        with patch('marketing.media.video_info', return_value=info):
            self.assertEqual(verify_video('fixture.mp4')['seconds'], 67.1)
            for duration in (20, 30, 75, 120, 180):
                info['seconds'] = duration
                self.assertEqual(verify_video('fixture.mp4')['seconds'], duration)
            for duration in (19, 180.1):
                info['seconds'] = duration
                with self.assertRaises(AppError):
                    verify_video('fixture.mp4')

    def test_provider_receives_editorial_policy_and_style(self):
        class Http:
            def json(inner, method, url, **kwargs):
                inner.data = kwargs['data']
                return {'status': 'completed', 'output': [{'type': 'message', 'content': [
                    {'type': 'output_text', 'text': '{"summary":"Brief","items":[]}'}]}]}
        http = Http()
        Agents(Config(ROOT, env={'OPENAI_API_KEY': 'test-placeholder'}), http).run('00-orquestador', {}, BRIEF)
        data = json.loads(http.data['input'])
        self.assertFalse(data['style']['music']['bass_line'])
        self.assertIn('60 a 75', http.data['instructions'])
        self.assertIn('duration_reason', http.data['instructions'])
        self.assertNotIn('El cierre dice:', http.data['instructions'])

    def test_bad_plans_are_blocked_before_motion_and_mix(self):
        mutations = {
            'always_camera': lambda s: [x.update(layout='split') for x in s],
            'repeated_images': lambda s: [x.update(visual_id=f'image-{i % 3}') for i, x in enumerate(s)],
            'single_palette': lambda s: [x.update(palette='violet') for x in s],
            'single_motion': lambda s: [x.update(motion='push') for x in s],
            'single_transition': lambda s: [x.update(transition='cut') for x in s],
            'gap': lambda s: s[4].update(start=8.5),
            'short_timeline': lambda s: s.pop(),
            'unmotivated_bw': lambda s: s[1].update(layout='split_bw'),
        }
        for reason, mutate in mutations.items():
            with self.subTest(reason=reason):
                plan = shot_plan()
                mutate(plan['shots'])
                with patch.object(self.agents, 'run', wraps=self.agents.run) as run:
                    original = self.agents.run
                    run.side_effect = lambda role, context, schema: plan if schema is SHOTS else EditorialAgents.run(self.agents, role, context, schema)
                    job = self.approved()
                    before = len(self.agents.calls)
                    with self.assertRaises(AppError):
                        self.workflow.produce(job['id'])
                    self.assertNotIn('13-motion', self.agents.calls[before:])
                    self.assertEqual(self.store.get(job['id'])['state'], 'approved')

    def test_example_plan_meets_style_contract(self):
        validate(shot_plan(), SHOTS)
        report = check_shots(shot_plan(), 60, load_style(ROOT))
        self.assertEqual(report['camera_fraction'], 0.5)
        self.assertEqual(report['unique_visual_fraction'], 1)

    def timed_script(self, seconds, reason=''):
        count = 12 if seconds <= 75 else 30
        segment_seconds, remainder = divmod(seconds - 2, count - 1)
        durations = [2] + [segment_seconds + (1 if i < remainder else 0) for i in range(count - 1)]
        return {'title': 'Duración por contenido', 'hook': 'Mirá este proceso.',
                'segments': [{'spoken': 'Mirá este proceso.', 'screen': 'Un paso concreto', 'seconds': value} for value in durations],
                'alternative_hooks': ['Uno', 'Dos', 'Tres'], 'claims_to_verify': [], 'duration_reason': reason}

    def test_base_duration_needs_no_exception_reason(self):
        for seconds in (60, 67, 75):
            with self.subTest(seconds=seconds):
                validate_script(self.timed_script(seconds), style=load_style(ROOT))

    def test_adjustments_require_a_reason_and_stay_within_allowed_range(self):
        for seconds in (20, 35, 45, 76, 90, 120, 180):
            with self.subTest(seconds=seconds):
                with self.assertRaisesRegex(AppError, 'justificar'):
                    validate_script(self.timed_script(seconds, '  '), style=load_style(ROOT))
                validate_script(self.timed_script(seconds, 'La cantidad de pasos del ejemplo define esta duración.'), style=load_style(ROOT))
        for seconds in (19, 181):
            with self.subTest(seconds=seconds), self.assertRaises(AppError):
                validate_script(self.timed_script(seconds, 'Un motivo no habilita cualquier duración.'), style=load_style(ROOT))

    def test_short_and_long_content_reach_production_with_recorded_duration(self):
        original_run = self.agents.run
        for seconds, reason in [(30, 'Una sola corrección de configuración y su resultado.'),
                                (120, 'Demostrar tres pasos completos de integración con su comprobación.')]:
            with self.subTest(seconds=seconds):
                def run(role, context, schema):
                    if role == '02-guionista':
                        return self.timed_script(seconds, reason)
                    if schema is SHOTS:
                        plan = shot_plan()
                        plan['shots'] = [dict(copy.deepcopy(plan['shots'][i % 30]),
                                             start=i * 2, end=(i + 1) * 2, visual_id=f'visual-{i}')
                                         for i in range(seconds // 2)]
                        return plan
                    return original_run(role, context, schema)
                with patch.object(self.agents, 'run', side_effect=run):
                    job = self.workflow.produce(self.approved()['id'])
                exported = self.store.artifact_dir(job)
                handoff = json.loads((exported / 'handoff-produccion.json').read_text(encoding='utf-8'))
                self.assertEqual(handoff['duration_seconds'], seconds)
                self.assertEqual(handoff['duration_reason'], reason)
                self.assertEqual(job['agents']['04-director-visual']['shots'][-1]['end'], seconds)
                self.assertIn(reason, (exported / 'produccion.md').read_text(encoding='utf-8'))

    def test_existing_v1_work_keeps_its_duration_contract(self):
        style = load_style(ROOT)
        style.update(id='infinite-process-editorial-v1', version=1)
        style['format']['duration_seconds'] = [60, 90]
        style.pop('duration_policy')
        script = self.timed_script(85)
        script.pop('duration_reason')
        job = self.store.create('Trabajo iniciado con el perfil anterior')
        job['style'] = {'profile': style, 'sha256': digest(style)}
        self.store.save(job)
        original_run = self.agents.run
        def run(role, context, schema):
            if role == '02-guionista':
                self.assertNotIn('duration_reason', schema['properties'])
                self.assertIn('60 a 90', duration_instructions(context['style']))
                return script
            return original_run(role, context, schema)
        with patch.object(self.agents, 'run', side_effect=run):
            drafted = self.workflow.draft(job['id'])
        self.assertEqual(drafted['style']['sha256'], digest(style))
        self.assertEqual(sum(s['seconds'] for s in drafted['script']['segments']), 85)


if __name__ == '__main__':
    unittest.main()
