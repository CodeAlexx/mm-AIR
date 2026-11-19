#!/usr/bin/env python3
"""Independent stdio checks of the Movie Maker MCP server. CPU only: the render worker runs in its
test-fixture mode (an ffmpeg test clip stands in for H3), in a temporary output folder.

    python3 mcp/tests/protocol_test.py [--bin build/release/bin]
"""
import argparse
import json
import os
from pathlib import Path
import selectors
import socket
import subprocess
import tempfile
import time


class Client:
    def __init__(self, server, root, extra=(), socket_input=False):
        argv = [str(server), '--output-root', str(root), '--scratch', str(root / 'scratch'), *extra]
        if socket_input:
            # Claude Code hands a stdio server a socket as stdin.
            parent, child = socket.socketpair()
            try:
                self.p = subprocess.Popen(argv, stdin=child, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                          text=True, bufsize=1)
                self.p.stdin = parent.makefile('w', encoding='utf-8', buffering=1)
            finally:
                parent.close()
                child.close()
        else:
            self.p = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                      text=True, bufsize=1)
        self.id = 0

    def raw(self, line):
        self.p.stdin.write(line + '\n')
        self.p.stdin.flush()
        return self.read()

    def read(self):
        with selectors.DefaultSelector() as select:
            select.register(self.p.stdout, selectors.EVENT_READ)
            assert select.select(60), f'no response; process={self.p.poll()}'
        line = self.p.stdout.readline()
        assert line, (self.p.poll(), self.p.stderr.read())
        return json.loads(line)

    def send(self, method, params=None, notification=False):
        self.id += 1
        msg = dict(jsonrpc='2.0', method=method)
        if not notification:
            msg['id'] = self.id
        if params is not None:
            msg['params'] = params
        self.p.stdin.write(json.dumps(msg) + '\n')
        self.p.stdin.flush()
        if notification:
            return None
        reply = self.read()
        assert reply['jsonrpc'] == '2.0' and reply['id'] == self.id, reply
        return reply

    def initialize(self):
        result = self.send('initialize', dict(protocolVersion='2025-06-18', capabilities={},
                                              clientInfo=dict(name='test', version='1')))['result']
        assert result['protocolVersion'] == '2025-06-18' and 'tools' in result['capabilities'], result
        self.send('notifications/initialized', {}, True)
        return result

    def call(self, name, arguments=None, error=False):
        reply = self.send('tools/call', dict(name=name, arguments=arguments or {}))
        assert 'result' in reply, reply
        result = reply['result']
        assert result['isError'] == error, (name, arguments, result)
        data = result['structuredContent']
        assert json.loads(result['content'][0]['text']) == data
        return data

    def close(self):
        self.p.stdin.close()
        self.p.wait(timeout=30)
        assert self.p.returncode == 0, self.p.stderr.read()
        assert self.p.stdout.read() == '', 'unexpected stdout outside the protocol'
        assert self.p.stderr.read() == '', 'unexpected diagnostics'


def wait_status(client, job, done, seconds=120):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        status = client.call('movie_status', dict(job=job))
        if done(status):
            return status
        time.sleep(0.25)
    raise AssertionError(f'job did not finish: {status}')


def shot(id_, title, **extra):
    body = dict(id=id_, title=title, duration_seconds=1.0, width=256, height=256, seed=7,
                shot_description=f'{title}: a red ball rolls across a wooden table, soft daylight.')
    body.update(extra)
    return body


POLICY = dict(conditioner_projection='convrot_i8', transformer_projection='row_scaled_i8', attention='dense_i8',
              profile='donor_7')


def main():
    here = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser()
    parser.add_argument('--bin', default=str(here / 'build/release/bin'))
    args = parser.parse_args()
    server = Path(args.bin) / 'mm-air-movie-mcp'
    worker = Path(args.bin) / 'mm-air-movie-render'
    assert server.is_file() and worker.is_file(), 'build both programs first (mcp/build.sh)'
    checks = 0
    with tempfile.TemporaryDirectory(prefix='mm-air-movie-mcp-') as tmp:
        root = Path(tmp)
        library = root / 'movies'

        # protocol framing
        c = Client(server, root, ['--test-fixture', '--allow-render', '--render-bin', str(worker)])
        early = c.send('tools/list')
        assert early['error']['code'] == -32002, early
        assert c.raw('{not json')['error']['code'] == -32700
        assert c.raw('[1,2]')['error']['code'] == -32600
        info = c.initialize()
        assert 'movie_render' in info['instructions']
        assert c.send('ping')['result'] == {}
        assert c.send('no/such')['error']['code'] == -32601
        tools = {t['name']: t for t in c.send('tools/list')['result']['tools']}
        assert set(tools) == {'movie_list', 'movie_inspect', 'movie_create', 'movie_update_project', 'movie_update_shot',
                              'movie_add_shot', 'movie_delete_shot', 'movie_render', 'movie_status', 'movie_logs',
                              'movie_stop', 'movie_assemble'}, sorted(tools)
        for t in tools.values():
            assert t['inputSchema']['type'] == 'object' and len(t['description']) < 200
        checks += 1

        # library and create
        assert c.call('movie_list')['projects'] == []
        c.call('movie_unknown', error=True)
        c.call('movie_list', dict(extra=1), error=True)
        project = dict(schema='serenity.h3.movie.v1', title='Ball', shots=[shot(1, 'One'), shot(2, 'Two')])
        bad = json.loads(json.dumps(project)); bad['shots'][0]['durations'] = 2
        assert 'durations' in c.call('movie_create', dict(name='ball', project_json=bad), error=True)['message']
        dup = json.loads(json.dumps(project)); dup['shots'][1]['id'] = 1
        assert 'Two shots' in c.call('movie_create', dict(name='ball', project_json=dup), error=True)['message']
        big = json.loads(json.dumps(project)); big['shots'][0]['width'] = 1
        c.call('movie_create', dict(name='ball', project_json=big), error=True)
        c.call('movie_create', dict(name='../escape', project_json=project), error=True)
        created = c.call('movie_create', dict(name='ball', project_json=project))
        assert created['path'] == str(library / 'ball.serenitymovie.json') and created['shots'] == 2
        c.call('movie_create', dict(name='ball', project_json=project), error=True)  # no overwrite
        c.call('movie_create', dict(name='empty', title='Empty one', make_current=True))
        listing = c.call('movie_list')
        assert {p['name'] for p in listing['projects']} == {'ball', 'empty'}
        assert [p['current'] for p in listing['projects'] if p['name'] == 'empty'] == [True]
        assert (library / 'current-project.txt').read_text().strip() == str(library / 'empty.serenitymovie.json')
        c.call('movie_inspect', dict(project='/etc/passwd'), error=True)
        c.call('movie_inspect', dict(project='nothere'), error=True)
        checks += 1

        # edits: a fresh read and one atomic write each, in the window's own file format
        c.call('movie_update_shot', dict(project='ball', shot=1, fields=dict(title='Opening', seed=11)))
        c.call('movie_update_shot', dict(project='ball', shot=1, fields=dict(colour='red')), error=True)
        c.call('movie_update_shot', dict(project='ball', shot=1, fields=dict(first_frame='/no/such.png')), error=True)
        c.call('movie_update_shot', dict(project='ball', shot=1, fields=dict(width='wide')), error=True)
        c.call('movie_update_shot', dict(project='ball', shot=9, fields=dict(title='x')), error=True)
        added = c.call('movie_add_shot', dict(project='ball', fields=dict(title='Extra', shot_description='Extra shot.',
                                                                          duration_seconds=1.0, width=256, height=256)))
        extra_id = added['shot']['id']
        assert extra_id == 3, added
        c.call('movie_delete_shot', dict(project='ball', shot=extra_id))
        c.call('movie_update_project', dict(project='ball', director_brief='Short test film.'))
        on_disk = json.loads((library / 'ball.serenitymovie.json').read_text())
        assert on_disk['schema'] == 'serenity.h3.movie.v1' and on_disk['director_brief'] == 'Short test film.'
        assert [s['id'] for s in on_disk['shots']] == [1, 2] and on_disk['shots'][0]['title'] == 'Opening'
        assert not list(library.glob('*.tmp')), list(library.glob('*'))
        inspected = c.call('movie_inspect', dict(project='ball'))
        assert inspected['shots'][0]['state'] == 'unrendered' and 'Opening' not in inspected['shots'][0]['prompt']
        assert inspected['shots'][0]['frames'] == 24 and inspected['shots'][0]['problem'] == ''
        checks += 1

        # render: the policy is never chosen for the caller
        c.call('movie_render', dict(project='ball'), error=True)
        c.call('movie_render', dict(project='ball', conditioner_projection='convrot_i8',
                                    transformer_projection='row_scaled_i8', attention='dense_i8'), error=True)
        c.call('movie_render', dict(project='ball', **POLICY, evaluations=7), error=True)
        c.call('movie_render', dict(project='ball', **POLICY, shots=[5]), error=True)
        started = c.call('movie_render', dict(project='ball', **POLICY))
        assert started['shots'] == [1, 2], started
        busy = c.call('movie_render', dict(project='ball', **POLICY), error=True)
        assert 'already running' in busy['message'] or 'Every shot' in busy['message'], busy
        status = wait_status(c, started['job'], lambda s: s['state'] not in ('waiting', 'running'))
        assert status['state'] == 'done', status
        assert [s['state'] for s in status['shots']] == ['done', 'done'], status
        logs = c.call('movie_logs', dict(job=started['job']))
        assert 'movie-render: started' in logs['log'], logs
        inspected = c.call('movie_inspect', dict(project='ball'))
        for s in inspected['shots']:
            assert s['state'] == 'rendered' and s['selected_take'] == 0, s
            assert Path(s['takes'][0]['output']).is_file() and s['takes'][0]['output'].startswith(str(library / 'takes'))
            assert Path(s['takes'][0]['output'] + '.json').is_file()  # the parameters sidecar, as the window writes
        on_disk = json.loads((library / 'ball.serenitymovie.json').read_text())
        assert on_disk['shots'][0]['status'] == 'Ready' and on_disk['shots'][0]['take_states'] == ['done']
        assert on_disk['shots'][0]['output_path'] == on_disk['shots'][0]['take_output_paths'][0]
        assert 'Every shot' in c.call('movie_render', dict(project='ball', **POLICY), error=True)['message']
        c.call('movie_stop', dict(job=started['job']), error=True)  # finished jobs cannot be stopped
        checks += 1

        # continuation of a rendered shot, rendered alone with an explicit schedule
        cont = c.call('movie_add_shot', dict(project='ball', continue_from_shot=2))['shot']
        assert cont['continue_from'].endswith('.airh3ctx') and cont['state'] == 'unrendered', cont
        second = c.call('movie_render', dict(project='ball', conditioner_projection='convrot_i8',
                                             transformer_projection='row_scaled_i8', attention='dense_i8',
                                             evaluations=7, schedule='simple', sampler='res_multistep',
                                             shots=[cont['id']]))
        status = wait_status(c, second['job'], lambda s: s['state'] not in ('waiting', 'running'))
        assert status['state'] == 'done', status
        checks += 1

        # assemble the selected takes
        out = c.call('movie_assemble', dict(project='ball'))
        assert Path(out['output']).is_file() and out['shots'] == 3, out
        seconds = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                                                 '-of', 'csv=p=0', out['output']], text=True))
        assert 2.8 < seconds < 3.3, seconds
        c.call('movie_assemble', dict(project='ball', output=out['output']), error=True)  # no overwrite
        c.call('movie_assemble', dict(project='empty'), error=True)
        checks += 1
        c.close()

        # stop now: a worker that never finishes, ended through its process group
        slow = root / 'slow-worker.sh'
        slow.write_text('#!/bin/sh\nsleep 300\n')
        slow.chmod(0o755)
        c = Client(server, root, ['--test-fixture', '--allow-render', '--render-bin', str(slow)])
        c.initialize()
        c.call('movie_update_shot', dict(project='empty', shot=1, fields=dict(
            shot_description='A slow pan over a quiet lake.', width=256, height=256, duration_seconds=1.0)))
        job = c.call('movie_render', dict(project='empty', **POLICY))['job']
        time.sleep(0.5)
        assert c.call('movie_status', dict(job=job))['state'] == 'waiting'
        c.call('movie_update_shot', dict(project='empty', shot=1, fields=dict(title='x')), error=True)  # in the job
        c.call('movie_delete_shot', dict(project='empty', shot=1), error=True)
        c.call('movie_stop', dict(job=job, mode='later'), error=True)
        stopped = c.call('movie_stop', dict(job=job))
        assert stopped['state'] == 'stopped', stopped
        pid = (root / 'movies/.mcp-jobs' / job / 'worker/pid').read_text().strip()
        assert subprocess.run(['kill', '-0', '--', pid], stderr=subprocess.DEVNULL).returncode != 0, 'worker group still alive'
        assert c.call('movie_status')['state'] == 'stopped'
        c.close()

        # rendering is off unless the server owner allows it
        c = Client(server, root, ['--test-fixture'])
        assert 'off' in c.initialize()['instructions']
        assert '--allow-render' in c.call('movie_render', dict(project='ball', **POLICY), error=True)['message']
        c.close()
        checks += 1

        # socket stdin
        c = Client(server, root, [], socket_input=True)
        c.initialize()
        assert len(c.send('tools/list')['result']['tools']) == 12
        assert {p['name'] for p in c.call('movie_list')['projects']} == {'ball', 'empty'}
        c.close()
        checks += 1
    print(f'movie MCP protocol test: {checks} groups passed')


if __name__ == '__main__':
    main()
