import argparse
import os
import sys
import tempfile


from .blend2gltf import ConverterBlend2Gltf
from .gltf2bam import ConverterGltf2Bam
from .common import Settings


def convert(settings, srcdir, src, dst):
    blend2gltf = ConverterBlend2Gltf(settings)
    gltf2bam = ConverterGltf2Bam(settings)

    for src_element in src:
        if not os.path.exists(src_element):
            print('Source ({}) does not exist'.format(src_element))
            sys.exit(1)

        if len(src) > 1 and not os.path.isfile(src_element):
            print('Source ({}) is not a file'.format(src_element))
            sys.exit(1)

        if len(src) == 1 and not (os.path.isfile(src_element) or os.path.isdir(src_element)):
            print('Source ({}) must be a file or a directory'.format(src))
            sys.exit(1)

    src_is_dir = os.path.isdir(src[0])
    dst_is_dir = not os.path.splitext(dst)[1]

    files_to_convert = []
    if src_is_dir:
        srcdir = src[0]
        for root, _, files in os.walk(srcdir):
            files_to_convert += [
                os.path.join(root, i)
                for i in files
                if i.endswith('.blend')
            ]
    else:
        files_to_convert = [os.path.abspath(i) for i in src]

    is_batch = len(files_to_convert) > 1

    if is_batch and not dst_is_dir:
        print('Destination must be a directory if the source is a directory or multiple files')

    if is_batch:
        # Batch conversion
        blend2gltf.convert_batch(srcdir, dst, files_to_convert)
        tmpfiles = [i.replace(srcdir, dst).replace('.blend', '.gltf') for i in files_to_convert]
        gltf2bam.convert_batch(dst, dst, tmpfiles)
        _ = [os.remove(i) for i in tmpfiles]
    else:
        # Single file conversion
        srcfile = files_to_convert[0]
        if dst_is_dir:
            # Destination is a directory, add a filename
            dst = os.path.join(dst, os.path.basename(srcfile.replace('blend', 'bam')))

        tmpfile = tempfile.NamedTemporaryFile(delete=False)
        tmpfile.close()
        try:
            blend2gltf.convert_single(srcfile, tmpfile.name)
            gltf2bam.convert_single(tmpfile.name, dst)
        finally:
            os.remove(tmpfile.name)

def main():
    parser = argparse.ArgumentParser(
        description='CLI tool to convert Blender blend files to Panda3D BAM files'
    )

    parser.add_argument('src', nargs='+', type=str, help='source path')
    parser.add_argument('dst', type=str, help='destination path')

    parser.add_argument(
        '-m', '--material-mode',
        choices=[
            'legacy',
            'pbr',
        ],
        default='legacy',
        help='control how materials are exported'
    )

    parser.add_argument(
        '--physics-engine',
        choices=[
            'builtin',
            'bullet',
        ],
        default='builtin',
        help='the physics engine to build collision solids for'
    )

    parser.add_argument(
        '--srcdir',
        default=None,
        help='a common source directory to use when specifying multiple source files'
    )

    parser.add_argument(
        '--blender-dir',
        default='',
        help='directory that contains the blender binary'
    )

    args = parser.parse_args()

    src = [os.path.abspath(i) for i in args.src]
    srcdir = args.srcdir if args.srcdir is not None else os.path.commonpath(src)
    dst = os.path.abspath(args.dst) + os.sep

    settings = Settings(
        material_mode=args.material_mode,
        physics_engine=args.physics_engine,
        blender_dir=args.blender_dir
    )

    convert(settings, srcdir, src, dst)
