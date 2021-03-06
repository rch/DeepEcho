# -*- coding: utf-8 -*-

"""Functions to run the DeepEcho Benchmark on a Kubernetes cluster."""

import argparse
import importlib
import json
import logging
import os
import re
import sys
from io import StringIO

import boto3
import tabulate
import yaml
from dask.distributed import Client
from kubernetes.client import Configuration
from kubernetes.client.api import core_v1_api
from kubernetes.config import load_kube_config

RUN_TEMPLATE = """
/bin/bash <<'EOF'

{}

EOF
"""

CONFIG_TEMPLATE = """
cat > config.json << JSON
{}
JSON
"""

WORKER_COMM = '/usr/local/bin/dask-worker --nthreads {} --memory-limit 0 --death-timeout 0'


def _import_function(config):
    function = config['function']
    function = function.split('.')
    function_name = function[-1]
    package = '.'.join(function[:-1])
    module = importlib.import_module(package)

    return getattr(module, function_name)


def _logging_setup(verbosity=1):
    log_level = (3 - verbosity) * 10
    fmt = '%(asctime)s - %(process)d - %(levelname)s - %(name)s - %(module)s - %(message)s'
    logging.basicConfig(level=log_level, format=fmt)
    logging.getLogger("botocore").setLevel(logging.ERROR)
    logging.getLogger("urllib3").setLevel(logging.CRITICAL)


def _get_extra_setup(setup_dict):
    extra_packages = []

    script = setup_dict.get('script')
    if script:
        extra_packages.append('exec {}'.format(script))

    apt_packages = setup_dict.get('apt_packages')
    if apt_packages:
        extra_packages.append('apt get install {}'.format(' '.join(apt_packages)))

    pip_packages = setup_dict.get('pip_packages')
    if pip_packages:
        extra_packages.append('pip install {}'.format(' '.join(pip_packages)))

    git_repository = setup_dict.get('git_repository')
    if git_repository:
        url = git_repository.get('url')
        reference = git_repository.get('reference', 'master')
        install = git_repository.get('install')

        git_clone = 'git clone {} repo && cd repo'.format(url)
        git_checkout = 'git checkout {}'.format(reference)
        extra_packages.append('\n '.join([git_clone, git_checkout, install]))

    if len(extra_packages) > 1:
        return '\n '.join(extra_packages)

    return extra_packages[0]


def _generate_cluster_spec(config, master=False):
    extra_setup = ''
    dask_cluster = config['dask_cluster']
    metadata = {}
    image = dask_cluster.get('image', 'daskdev/dask:latest')

    setup = dask_cluster.get('setup')
    if setup:
        extra_setup = _get_extra_setup(setup)

    if master:
        metadata['generateName'] = '{}-'.format(re.sub(r'[\W_]', '-', image))

        config_command = CONFIG_TEMPLATE.format(json.dumps(config))
        run_command = 'python3 -u -m deepecho.benchmark.kubernetes config.json'
        extra_setup = '\n'.join([extra_setup, config_command, run_command])
        resources = dask_cluster.get('master_resources', {})

    else:
        run_command = WORKER_COMM.format(dask_cluster.get('threads', 1))
        extra_setup = '\n'.join([extra_setup, run_command])
        resources = dask_cluster.get('worker_resources', {})

    run_commands = RUN_TEMPLATE.format(extra_setup)

    spec = {
        'metadata': metadata,
        'spec': {
            'restartPolicy': 'Never',
            'containers': [{
                'args': ['-c', run_commands],
                'command': ['tini', '-g', '--', '/bin/sh'],
                'image': image,
                'name': 'dask-worker',
                'resources': {'requests': resources, 'limits': resources}
            }]
        }
    }

    return spec


def _dataframe_to_csv_str(dataframe):
    with StringIO() as sio:
        dataframe.to_csv(sio)
        return sio.getvalue()


def _upload_to_s3(bucket, path, results, aws_key=None, aws_secret=None):
    client = boto3.client('s3', aws_access_key_id=aws_key, aws_secret_access_key=aws_secret)
    client.put_object(Bucket=bucket, Key=path, Body=_dataframe_to_csv_str(results))


def run_dask_function(config):
    """Start a Dask Cluster using dask-kubernetes and run a function.

    Talks to kubernetes to create `n` amount of new `pods` with a dask worker inside of each
    forming a `dask` cluster. Then, a function specified from `config` is being imported and
    run with the given arguments. The tasks created by this `function` are being run on the
    `dask` cluster for distributed computation.

    The config dict must contain the following sections:
        * run
        * dask_cluster
        * output

    Args:
        config (dict):
            Config dictionary.
    """
    output_conf = config.get('output')
    if output_conf:
        path = output_conf.get('path')
        if not path:
            raise ValueError('An output path must be provided when providing `output`.')

    cluster_spec = _generate_cluster_spec(config, master=False)

    # Importing here to avoid an aiohttp error if not used.
    from dask_kubernetes import KubeCluster   # pylint: disable=C0415

    cluster = KubeCluster.from_dict(cluster_spec)

    workers = config['dask_cluster'].get('workers')

    if not workers:
        cluster.adapt()
    elif isinstance(workers, int):
        cluster.scale(workers)
    else:
        cluster.adapt(**workers)

    client = Client(cluster)
    client.get_versions(check=True)
    client.register_worker_callbacks(_logging_setup)

    try:
        run = _import_function(config['run'])
        kwargs = config['run']['args']
        results = run(**kwargs)

    finally:
        client.close()
        cluster.close()

    if output_conf:
        bucket = output_conf.get('bucket')

        try:
            if bucket:
                aws_key = output_conf.get('key')
                aws_secret = output_conf.get('secret_key')
                _upload_to_s3(bucket, path, results, aws_key, aws_secret)
            else:
                dirname = os.path.dirname(path)
                if dirname:
                    os.makedirs(dirname, exist_ok=True)

                results.to_csv(path)

        except Exception:   # pylint: disable=W0703
            print('Error storing results. Falling back to console dump.')
            print(_dataframe_to_csv_str(results))

        return None

    return results


def run_on_kubernetes(config, namespace='default'):
    """Run dask function inside a pod using the given config.

     Create a pod, using the local kubernetes configuration that starts a Dask Cluster
     using dask-kubernetes and runs a function specified within the `config` dictionary.

    Args:
        config (dict):
            Config dictionary.
        namespace (str):
            Kubernetes namespace were the pod will be created.
    """
    # read local config
    load_kube_config()
    Configuration.set_default(Configuration())

    # create client and create pod on default namespace
    core_v1 = core_v1_api.CoreV1Api()
    spec = _generate_cluster_spec(config, master=True)
    core_v1.create_namespaced_pod(body=spec, namespace=namespace)
    print('Pod created.')


def _get_parser():
    parser = argparse.ArgumentParser(description='Run on Kubernetes Command Line Interface')

    parser.add_argument('config', help='Path to the JSON config file.')
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help='Be verbose. Use -vv for increased verbosity.')
    parser.add_argument('--create-pod', action='store_true',
                        help='Create a master pod and run the given `config` from there.')
    parser.add_argument('-n', '--namespace', default='default',
                        help='Namespace were the pod will be created.')

    return parser


def _monkey_patch_dask_kubernetes():
    """Monkey-patch dask_kubernetes to avoid hitting a bug.

    The patch consists in replacing the `_cleanup_resources` function
    with a dummy alternative that does nothing.

    See: https://github.com/dask/dask-kubernetes/issues/170
    """
    import dask_kubernetes.core    # pylint: disable=C0415

    def _cleanup_resources(namespace, labels):
        del namespace, labels

    dask_kubernetes.core._cleanup_resources = _cleanup_resources    # pylint: disable=W0212


def main():
    """Command Line Interface to run DeepEcho Benchmark on a Kubernetes cluster."""
    # Parse args
    parser = _get_parser()
    if len(sys.argv) < 2:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    _logging_setup(args.verbose)

    with open(args.config) as config_file:
        if args.config.endswith('yaml') or args.config.endswith('yml'):
            config = yaml.safe_load(config_file)
        else:
            config = json.load(config_file)

    if args.create_pod:
        run_on_kubernetes(config, args.namespace)
    else:
        _monkey_patch_dask_kubernetes()

        results = run_dask_function(config)
        if results is not None:
            print(tabulate.tabulate(
                results,
                tablefmt='github',
                headers=results.columns
            ))


if __name__ == '__main__':
    main()
