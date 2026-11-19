import asyncio
import json
import os
import unittest
from unittest.mock import patch

os.environ.setdefault('DATABASE_URL', 'postgresql+asyncpg://sab:test@localhost/sab')

import httpx
from fastapi import HTTPException
from pydantic import SecretStr

from backend.core.config import Settings, settings
from backend.services.qwen import _arguments, generate_garment


def schema(negative_prompt=True):
    names = ['input_image', 'prompt', 'seed', 'randomize_seed', 'guidance_scale', 'steps']
    if negative_prompt:
        names.append('negative_prompt')
    parameters = [
        {'parameter_name': name, 'parameter_has_default': name not in ('input_image', 'prompt'),
         'parameter_default': 'blurry' if name == 'negative_prompt' else None}
        for name in names
    ]
    for i in range(6):
        parameters.extend([
            {'parameter_name': f'param_{i * 2}', 'label': f'LoRA {i + 1}',
             'parameter_has_default': True, 'parameter_default': 'some-adapter'},
            {'parameter_name': f'param_{i * 2 + 1}', 'label': 'Strength',
             'parameter_has_default': True, 'parameter_default': 0.75},
        ])
    return {'named_endpoints': {'/infer': {'parameters': parameters}}}


class QwenTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.config = patch.multiple(settings, hf_token=SecretStr('test-secret'),
                                     hf_space_url='https://test.hf.space',
                                     hf_api_name='infer', hf_timeout_seconds=1.0)
        self.config.start()
        self.addCleanup(self.config.stop)
        self.requests = []
        self.stream = 'event: heartbeat\ndata: null\n\nevent: complete\ndata: [{"path":"/tmp/output.png","url":"https://untrusted.test/image"},42]\n\n'

    def handler(self, request):
        self.requests.append(request)
        self.assertEqual(request.url.host, 'test.hf.space')
        self.assertEqual(request.headers['Authorization'], 'Bearer test-secret')
        path = request.url.path
        if path.endswith('/info'):
            return httpx.Response(200, json=schema())
        if path.endswith('/upload'):
            self.assertIn(b'input.jpg', request.content)
            self.assertIn(b'photo-bytes', request.content)
            return httpx.Response(200, json=['/tmp/input.jpg'])
        if path.endswith('/call/infer'):
            args = json.loads(request.content)['data']
            self.assertEqual(args[0], {'path': '/tmp/input.jpg', 'meta': {'_type': 'gradio.FileData'}})
            self.assertIn('jacket', args[1])
            self.assertIn('Preserve the zipper', args[1])
            self.assertEqual(args[2:7], [0, True, 1.0, 4, 'blurry'])
            self.assertEqual(args[7:], ['None', 0.75] * 6)
            return httpx.Response(200, json={'event_id': 'job-123'})
        if path.endswith('/job-123'):
            return httpx.Response(200, text=self.stream, headers={'content-type': 'text/event-stream'})
        if '/file=' in path:
            return httpx.Response(200, content=b'generated-image')
        self.fail(f'Unexpected request: {request.url}')

    async def generate(self, handler=None):
        client_class = httpx.AsyncClient
        transport = httpx.MockTransport(handler or self.handler)
        with patch('backend.services.qwen.httpx.AsyncClient',
                   side_effect=lambda **kwargs: client_class(transport=transport, **kwargs)):
            return await generate_garment(b'photo-bytes', 'jacket', 'Preserve the zipper')

    async def test_upload_queue_and_download(self):
        self.assertEqual(await self.generate(), b'generated-image')
        self.assertEqual(len(self.requests), 5)

    async def test_missing_token_skips_network(self):
        settings.hf_token = SecretStr('')
        with self.assertRaises(HTTPException) as caught:
            await self.generate()
        self.assertEqual(caught.exception.status_code, 503)
        self.assertEqual(self.requests, [])

    async def test_access_and_availability_errors_do_not_expose_body(self):
        for status in (401, 403, 429, 500, 503):
            with self.subTest(status=status):
                with self.assertRaises(HTTPException) as caught:
                    await self.generate(lambda _: httpx.Response(status, text='test-secret'))
                self.assertIn(caught.exception.status_code, (502, 503))
                self.assertNotIn('test-secret', caught.exception.detail)

    async def test_queue_quota_and_generation_failure(self):
        for message, status in [('GPU quota exceeded', 503), ('internal test-secret', 502)]:
            self.stream = 'event: error\ndata: ' + json.dumps(message) + '\n\n'
            with self.assertRaises(HTTPException) as caught:
                await self.generate()
            self.assertEqual(caught.exception.status_code, status)
            self.assertNotIn('test-secret', caught.exception.detail)

    async def test_incomplete_queue(self):
        self.stream = 'event: heartbeat\ndata: null\n\n'
        with self.assertRaises(HTTPException) as caught:
            await self.generate()
        self.assertEqual(caught.exception.status_code, 502)

    async def test_malformed_response(self):
        for body in ('not json', '{}', '{"named_endpoints": {}}'):
            with self.subTest(body=body):
                with self.assertRaises(HTTPException) as caught:
                    await self.generate(lambda _: httpx.Response(200, text=body))
                self.assertEqual(caught.exception.status_code, 502)

    async def test_invalid_output(self):
        for output in ('[]', '[null]', '[{"url":"https://untrusted.test/image"}]'):
            self.stream = f'event: complete\ndata: {output}\n\n'
            with self.assertRaises(HTTPException) as caught:
                await self.generate()
            self.assertEqual(caught.exception.status_code, 502)

    async def test_network_failure(self):
        def handler(request):
            raise httpx.ConnectError('DNS failed', request=request)
        with self.assertRaises(HTTPException) as caught:
            await self.generate(handler)
        self.assertEqual(caught.exception.status_code, 502)

    async def test_wall_clock_timeout(self):
        async def handler(request):
            await asyncio.sleep(0.1)
            return self.handler(request)
        settings.hf_timeout_seconds = 0.01
        with self.assertRaises(HTTPException) as caught:
            await self.generate(handler)
        self.assertEqual(caught.exception.status_code, 504)

    async def test_output_limit(self):
        with patch('backend.services.qwen.MAX_OUTPUT_BYTES', 2):
            with self.assertRaises(HTTPException) as caught:
                await self.generate()
        self.assertEqual(caught.exception.status_code, 502)

    def test_older_schema_without_negative_prompt(self):
        args = _arguments(schema(negative_prompt=False), 'path', 'prompt')
        self.assertEqual(len(args), 18)
        self.assertEqual(args[6:], ['None', 0.75] * 6)

    def test_unknown_required_input_rejected(self):
        info = schema()
        info['named_endpoints']['/infer']['parameters'].append({'parameter_name': 'new_required'})
        with self.assertRaises(ValueError):
            _arguments(info, 'path', 'prompt')

    def test_config_masks_token(self):
        config = Settings(_env_file=None, database_url='test', hf_token='test-secret')
        self.assertNotIn('test-secret', repr(config))
        self.assertTrue(config.ai_configured)
        config.hf_token = SecretStr('replace_me')
        self.assertFalse(config.ai_configured)
