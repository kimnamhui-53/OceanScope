# -*- coding: utf-8 -*-
"""
작업 큐 — 렌더 요청을 한 건씩 순서대로 처리한다.

matplotlib 은 스레드 안전하지 않고 소용돌이 탐지는 CPU 를 오래 쓰므로
워커 스레드 하나로 직렬 처리한다. 진행 상황은 Job.step / Job.progress 로
프론트가 폴링해 가져간다.

작업 정보는 메모리에만 둔다. 서버를 끄면 사라진다.
"""
import queue
import threading
import time
import traceback
import uuid

_jobs = {}
_lock = threading.Lock()
_queue = queue.Queue()
_worker = None

# 오래된 작업 정리 기준 (초)
JOB_TTL = 60 * 60


class Job:
    def __init__(self, spec):
        self.id = uuid.uuid4().hex[:12]
        self.spec = spec
        self.state = 'queued'        # queued | running | done | error
        self.step = '대기 중'
        self.progress = 0.0          # 0.0 ~ 1.0
        self.results = []
        self.error = None
        self.created = time.time()

    def report(self, step, progress):
        self.step = step
        self.progress = progress

    def to_dict(self):
        return {
            'job_id': self.id,
            'state': self.state,
            'step': self.step,
            'progress': round(self.progress, 3),
            'error': self.error,
            'results': self.results,
        }


def submit(spec, handler):
    """작업을 큐에 넣고 Job 을 돌려준다. handler(job) 가 워커에서 실행된다."""
    _ensure_worker()
    job = Job(spec)
    with _lock:
        _jobs[job.id] = job
        _sweep()
    _queue.put((job, handler))
    return job


def get(job_id):
    with _lock:
        return _jobs.get(job_id)


def pending():
    """대기 중인 작업 수 (내 앞에 몇 건 있는지 안내용)."""
    return _queue.qsize()


def _sweep():
    """오래 끝난 작업을 정리한다. 호출자가 _lock 을 잡고 있어야 한다."""
    cutoff = time.time() - JOB_TTL
    for jid in [j for j, o in _jobs.items()
                if o.state in ('done', 'error') and o.created < cutoff]:
        _jobs.pop(jid, None)


def _run():
    while True:
        job, handler = _queue.get()
        job.state = 'running'
        try:
            job.results = handler(job) or []
            job.state = 'done'
            job.report('완료', 1.0)
        except Exception as e:                      # noqa: BLE001 — 사용자에게 그대로 전달
            job.state = 'error'
            job.error = str(e) or e.__class__.__name__
            job.report('실패', 1.0)
            traceback.print_exc()
        finally:
            # 자격증명은 작업이 끝나는 즉시 메모리에서 지운다
            job.spec.pop('username', None)
            job.spec.pop('password', None)
            _queue.task_done()


def _ensure_worker():
    global _worker
    if _worker is None or not _worker.is_alive():
        _worker = threading.Thread(target=_run, name='render-worker', daemon=True)
        _worker.start()
