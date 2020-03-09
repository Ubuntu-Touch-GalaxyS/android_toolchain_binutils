#!/usr/bin/env python3
#
# Copyright (C) 2017 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""Builds binutils."""
import argparse
import logging
import multiprocessing
import os
from pathlib import Path
import shutil
import site
import subprocess


THIS_DIR = os.path.realpath(os.path.dirname(__file__))
site.addsitedir(os.path.join(THIS_DIR, '../../ndk'))

# pylint: disable=import-error,wrong-import-position
import ndk.abis
from ndk.hosts import Host
import ndk.paths
import ndk.timer
# pylint: enable=import-error,wrong-import-position


def logger():
    """Returns the module level logger."""
    return logging.getLogger(__name__)


def makedirs(path):
    """os.makedirs with logging."""
    logger().info('makedirs %s', path)
    os.makedirs(path)


def rmtree(path):
    """shutil.rmtree with logging."""
    logger().info('rmtree %s', path)
    shutil.rmtree(path)


def chdir(path):
    """os.chdir with logging."""
    logger().info('chdir %s', path)
    os.chdir(path)


def install_file(src, dst):
    """shutil.copy2 with logging."""
    logger().info('copy %s %s', src, dst)
    shutil.copy2(src, dst)


def check_call(cmd, *args, **kwargs):
    """subprocess.check_call with logging."""
    logger().info('check_call %s', subprocess.list2cmdline(cmd))
    subprocess.check_call(cmd, *args, **kwargs)


def configure(arch, host: Host, install_dir, src_dir):
    """Configures binutils."""
    configure_host = {
        Host.Darwin: 'x86_64-apple-darwin',
        Host.Linux: 'x86_64-linux-gnu',
        Host.Windows64: 'x86_64-w64-mingw32',
    }[host]

    sysroot = ndk.paths.sysroot_path(ndk.abis.arch_to_toolchain(arch))
    configure_args = [
        os.path.join(src_dir, 'configure'),
        '--target={}'.format(ndk.abis.arch_to_triple(arch)),
        '--host={}'.format(configure_host),
        '--enable-initfini-array',
        '--enable-plugins',
        '--enable-threads',
        '--disable-nls',
        '--with-sysroot={}'.format(sysroot),
        '--prefix={}'.format(install_dir),
    ]

    if arch == 'arm64':
        configure_args.append('--enable-fix-cortex-a53-835769')
        configure_args.append('--enable-gold')
    else:
        # Gold for aarch64 currently emits broken debug info.
        # https://issuetracker.google.com/70838247
        configure_args.append('--enable-gold=default')

    env = {}

    if host == Host.Darwin:
        toolchain = ndk.paths.android_path(
            'prebuilts/gcc/darwin-x86/host/i686-apple-darwin-4.2.1')
        toolchain_prefix = 'i686-apple-darwin10'
        env['MACOSX_DEPLOYMENT_TARGET'] = '10.9'
    elif host == Host.Linux:
        toolchain = ndk.paths.android_path(
            'prebuilts/gcc/linux-x86/host/x86_64-linux-glibc2.15-4.8')
        toolchain_prefix = 'x86_64-linux'
    elif host.is_windows:
        toolchain = ndk.paths.android_path(
            'prebuilts/gcc/linux-x86/host/x86_64-w64-mingw32-4.8')
        toolchain_prefix = 'x86_64-w64-mingw32'
    else:
        raise NotImplementedError

    cc = os.path.join(toolchain, 'bin', '{}-gcc'.format(toolchain_prefix))
    cxx = os.path.join(toolchain, 'bin', '{}-g++'.format(toolchain_prefix))

    # Our darwin prebuilts are gcc *only*. No binutils.
    if host == Host.Darwin:
        ar = 'ar'
        strip = 'strip'
    else:
        ar = os.path.join(toolchain, 'bin', '{}-ar'.format(toolchain_prefix))
        strip = os.path.join(
            toolchain, 'bin', '{}-strip'.format(toolchain_prefix))

    env['AR'] = ar
    env['CC'] = cc
    env['CXX'] = cxx
    env['STRIP'] = strip
    env['CFLAGS'] = '-O2 -m64'
    env['CXXFLAGS'] = '-O2 -m64'
    env['LDFLAGS'] = '-O2 -m64'

    env_args = ['env'] + ['='.join([k, v]) for k, v in env.items()]
    check_call(env_args + configure_args)


def build(jobs):
    """Builds binutils."""
    check_call(['make', '-j', str(jobs)])


def install_winpthreads(is_windows32, install_dir):
    """Installs the winpthreads runtime to the Windows bin directory."""
    lib_name = 'libwinpthread-1.dll'
    mingw_dir = ndk.paths.android_path(
        'prebuilts/gcc/linux-x86/host/x86_64-w64-mingw32-4.8',
        'x86_64-w64-mingw32')
    # Yes, this indeed may be found in bin/ because the executables are the
    # 64-bit version by default.
    pthread_dir = 'lib32' if is_windows32 else 'bin'
    lib_path = os.path.join(mingw_dir, pthread_dir, lib_name)

    lib_install = os.path.join(install_dir, 'bin', lib_name)
    install_file(lib_path, lib_install)


def install(jobs, arch, host, install_dir):
    """Installs binutils."""
    check_call(['make', 'install-strip', '-j', str(jobs)])

    if host.is_windows:
        arch_install_dir = os.path.join(
            install_dir, ndk.abis.arch_to_triple(arch))
        install_winpthreads(host == 'win', install_dir)
        install_winpthreads(host == 'win', arch_install_dir)


def dist(dist_dir, base_dir, package_name):
    """Packages binutils for distribution."""
    has_pbzip2 = shutil.which('pbzip2') is not None
    if has_pbzip2:
        compress_arg = '--use-compress-prog=pbzip2'
    else:
        compress_arg = '-j'

    package_path = os.path.join(dist_dir, package_name + '.tar.bz2')
    cmd = [
        'tar', compress_arg, '-cf', package_path, '-C', base_dir, package_name,
    ]
    subprocess.check_call(cmd)


def copy_logs_to_dist_dir(build_dir: Path, base_log_dir: Path) -> None:
    """Preserves any relevant log files from the build directory."""
    log_file = 'config.log'
    log_dir = base_log_dir / 'autoconf'
    for root, _, files in os.walk(build_dir):
        root_path = Path(root)
        if log_file not in files:
            continue
        rel_path = Path(root).relative_to(build_dir)
        dest_dir = log_dir / rel_path
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(root_path / log_file), str(dest_dir / log_file))


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser()

    def host_from_arg(arg: str) -> Host:
        return {
            'darwin': Host.Darwin,
            'linux': Host.Linux,
            'win64': Host.Windows64,
        }[arg]

    parser.add_argument(
        '--arch', choices=ndk.abis.ALL_ARCHITECTURES, required=True)
    parser.add_argument(
        '--host', choices=Host, type=host_from_arg, required=True)

    parser.add_argument(
        '--clean', action='store_true',
        help='Clean the out directory before building.')
    parser.add_argument(
        '-j', '--jobs', type=int, default=multiprocessing.cpu_count(),
        help='Number of jobs to use when building.')

    return parser.parse_args()


def main():
    """Program entry point."""
    args = parse_args()
    logging.basicConfig(level=logging.INFO)

    total_timer = ndk.timer.Timer()
    total_timer.start()

    out_dir = ndk.paths.get_out_dir()
    dist_dir = ndk.paths.get_dist_dir(out_dir)
    artifact_host = {
        Host.Darwin: 'darwin',
        Host.Linux: 'linux',
        Host.Windows64: 'win64',
    }[args.host]
    base_build_dir = os.path.join(out_dir, 'binutils', artifact_host,
                                  args.arch)
    build_dir = os.path.join(base_build_dir, 'build')
    package_name = 'binutils-{}-{}'.format(args.arch, artifact_host)
    install_dir = os.path.join(base_build_dir, 'install', package_name)
    binutils_path = os.path.join(THIS_DIR, 'binutils-2.27')

    did_clean = False
    clean_timer = ndk.timer.Timer()
    if args.clean and os.path.exists(build_dir):
        did_clean = True
        with clean_timer:
            rmtree(build_dir)

    if not os.path.exists(build_dir):
        makedirs(build_dir)

    orig_dir = os.getcwd()
    chdir(build_dir)
    try:
        configure_timer = ndk.timer.Timer()
        with configure_timer:
            configure(args.arch, args.host, install_dir, binutils_path)

        build_timer = ndk.timer.Timer()
        with build_timer:
            build(args.jobs)

        install_timer = ndk.timer.Timer()
        with install_timer:
            install(args.jobs, args.arch, args.host, install_dir)
    finally:
        copy_logs_to_dist_dir(Path(build_dir), Path(dist_dir) / 'logs')
        chdir(orig_dir)

    package_timer = ndk.timer.Timer()
    with package_timer:
        dist(dist_dir, os.path.dirname(install_dir), package_name)

    total_timer.finish()

    if did_clean:
        print('Clean: {}'.format(clean_timer.duration))
    print('Configure: {}'.format(configure_timer.duration))
    print('Build: {}'.format(build_timer.duration))
    print('Install: {}'.format(install_timer.duration))
    print('Package: {}'.format(package_timer.duration))
    print('Total: {}'.format(total_timer.duration))


if __name__ == '__main__':
    main()
