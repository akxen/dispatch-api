"""Views used to run jobs"""

import os
import zlib
import json
from collections import OrderedDict

import redis
from rq import Queue
from rq.job import Job
from rq.exceptions import NoSuchJobError

from django.http import JsonResponse
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, ParseError, PermissionDenied


class JSONSerializer:
    @staticmethod
    def dumps(*args, **kwargs):
        return json.dumps(*args, **kwargs).encode('utf-8')

    @staticmethod
    def loads(s, *args, **kwargs):
        return json.loads(s.decode('utf-8'), *args, **kwargs)


class ZlibSerializer:
    @staticmethod
    def dumps(*args, **kwargs):
        return zlib.compress(json.dumps(*args, **kwargs).encode('utf-8'))

    @staticmethod
    def loads(s, *args, **kwargs):
        return json.loads(zlib.decompress(s).decode('utf-8'), *args, **kwargs)


serializer = ZlibSerializer


def get_db_connection():
    """Get connection to Redis database"""

    pool = redis.ConnectionPool(
        host=os.getenv('REDIS_HOST'),
        port=int(os.getenv('REDIS_PORT')),
        db=int(os.getenv('REDIS_DB')))

    conn = redis.Redis(connection_pool=pool)

    return conn


def get_job(job_id):
    conn = get_db_connection()
    try:
        return Job.fetch(
            job_id,
            connection=conn,
            serializer=serializer,
        )
    except NoSuchJobError:
        raise NotFound(detail="Job not found.")


def check_high_level_keys(data):

    keys = ['case_id', 'casefile', 'options', 'patches']

    for i in data.keys():
        if i not in keys:
            raise ParseError(detail=f"Invalid key: '{i}'")

    if ('casefile' not in data.keys()) and ('case_id' not in data.keys()):
        raise ParseError(detail="Must specify either 'casefile' or 'case_id'")

    if ('casefile' in data.keys()) and ('case_id' in data.keys()):
        raise ParseError(detail="Must specify either 'casefile' or 'case_id'")

    if ('casefile' in data.keys()) and ('patches' in data.keys()):
        raise ParseError(detail="Cannot specify both 'casefile' and 'patches'")


def check_options_keys(data):

    keys = ['run_mode', 'algorithm', 'solution_format',
            'return_casefile', 'solution_elements', 'label']

    options = data.get('options', {})

    for i in options.keys():
        if i not in keys:
            raise ParseError(detail=f"Invalid options key: '{i}'")

    if options.get('run_mode') not in [None, 'target', 'pricing']:
        raise ParseError(detail=f"Invalid 'run_mode': {options.get('run_mode')}")

    if options.get('algorithm') not in [None, 'default']:
        raise ParseError(detail=f"Invalid 'algorithm' option: {options.get('algorithm')}")

    if options.get('solution_format') not in [None, 'standard', 'validation']:
        raise ParseError(
            detail=f"Invalid 'solution_format' option: {options.get('solution_format')}")

    if options.get('return_casefile') not in [None, True, False]:
        raise ParseError(
            detail=f"Invalid 'return_casefile' option: {options.get('return_casefile')}")

    if (options.get('solution_elements') is not None) and (not isinstance(options.get('solution_elements'), list)):
        raise ParseError(
            detail=f"'solution_elements' must be an array: {options.get('solution_elements')}")

    if (options.get('label') is not None) and (not isinstance(options.get('label'), str)):
        raise ParseError(detail=f"'label' must be a string: {options.get('label')}")


def check_permissions(request, meta):
    """Check if requestor can access the job"""

    # Extract job creator
    created_by = meta.get('created_by')

    # Only job creator can access results
    has_permission = (created_by is not None) and (created_by == request.user.email)
    if not has_permission:
        raise PermissionDenied(detail="Permission denied.")


class JobCreate(APIView):

    def post(self, request, format=None):
        """Create a new job"""

        # TODO: Lookup which queue job should be appended to
        user_queue = 'public'

        # Validate inputs
        check_high_level_keys(data=request.data)
        check_options_keys(data=request.data)

        # Get Redis connection and queue
        conn = get_db_connection()
        queue = Queue(
            user_queue,
            connection=conn,
            failure_ttl=7200,
            serializer=serializer,
        )

        # Metadata for job
        meta = {
            'created_by': request.user.email,
            'label': request.data.get('options', {}).get('label')
        }

        # Create job and add to queue
        job = Job.create(
            func='nemde.core.model.execution.run_model',
            args=[request.data],
            connection=conn,
            meta=meta,
            result_ttl=7200,
            failure_ttl=7200,
            serializer=serializer,
        )

        result = queue.enqueue_job(job)

        # Keys to return to user when job is submitted
        keys = ['created_at', 'enqueued_at', 'timeout', 'status']
        filtered = [(k, v) for k, v in result.to_dict().items() if k in keys]

        # Add job ID to results
        job_id_list = [('job_id', result.get_id())]
        label_list = [('label', meta.get('label'))]
        output = OrderedDict(job_id_list + filtered + label_list)

        return Response(output)


class JobResults(APIView):

    def get(self, request, job_id, format=None):
        """Get job results"""

        # Get job instance and check if caller can access results
        job = get_job(job_id=job_id)
        check_permissions(request=request, meta=job.meta)

        base = [
            ('job_id', job_id),
            ('status', job.get_status()),
            ('created_at', job.created_at),
            ('enqueued_at', job.enqueued_at),
            ('started_at', job.started_at),
            ('ended_at', job.ended_at),
            ('timeout', job.timeout),
            ('label', job.meta['label']),
            ('exc_info', job.exc_info),
            ('results', job.result),
        ]

        output = OrderedDict(base)

        # Handle exceptions
        if output.get('exc_info') is not None:
            output['exc_info'] = 'Error processing job'

            # TODO: send exc_info to database for analysis

        return Response(output)


class JobSize(APIView):

    def get(self, request, job_id, format=None):

        conn = get_db_connection()
        redis_id = f'rq:job:{job_id}'
        job = conn.hgetall(redis_id)

        print(job)

        return Response({"message": "Working."})


class JobStatus(APIView):

    def get(self, request, job_id, format=None):
        """Get job results"""

        # Get job instance and check if caller can access results
        job = get_job(job_id=job_id)
        check_permissions(request=request, meta=job.meta)

        base = [
            ('job_id', job_id),
            ('status', job.get_status()),
            ('created_at', job.created_at),
            ('enqueued_at', job.enqueued_at),
            ('started_at', job.started_at),
            ('ended_at', job.ended_at),
            ('timeout', job.timeout),
            ('label', job.meta['label']),
        ]

        return Response(OrderedDict(base))


class JobStatusList(APIView):

    def get(self, request, format=None):
        """Get status for a given job"""

        conn = get_db_connection()

        # Keys to retain
        keys = ['status', 'created_at', 'enqueued_at', 'started_at',
                'ended_at', 'timeout']

        # Container for output
        out = []
        for k in conn.scan_iter():
            if k.startswith(b'rq:job:'):
                # Extract job ID
                job_id = k.decode('utf-8').replace('rq:job:', '')

                # If meta data is missing delete job - cleaning up queue
                # This can happen if job cancelled while worker running
                meta_bytes = conn.hget(k, b'meta')
                if meta_bytes is None:
                    job = Job.fetch(
                        job_id,
                        connection=conn,
                        serializer=serializer,
                    )
                    job.cancel()
                    job.delete()
                    continue

                # Check caller has permission to access results
                meta_str = zlib.decompress(meta_bytes).decode('utf-8')
                meta = json.loads(meta_str)

                try:
                    check_permissions(request=request, meta=meta)
                except PermissionDenied:
                    continue

                # Extract data
                j = {k.decode('utf-8'): v.decode('utf-8')
                     for k, v in conn.hscan_iter(k) if k.decode('utf-8') in keys}

                # Order job to make display format nicer
                j_list = [(k, j[k]) for k in keys]

                # Combine job details with job ID and label
                job_info = [('job_id', job_id)] + j_list + [('label', meta.get('label'))]

                out.append(OrderedDict(job_info))

        # Sort values
        out_sorted = sorted(out, key=lambda x: x['created_at'], reverse=True)
        return Response(out_sorted)


class JobDelete(APIView):

    def get(self, request, job_id, format=None):
        """Get job results"""

        try:
            job = get_job(job_id=job_id)

            # Check permissions
            check_permissions(request=request, meta=job.meta)

            # Delete jobs
            job.cancel()
            job.delete()
            return Response({'message': 'Deleted job.'})

        except NoSuchJobError:
            raise NotFound(detail='Job not found.')
