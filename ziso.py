# -*- coding: utf-8 -*-
#!/usr/bin/env python3

# Copyright (c) 2011 by Virtuous Flame
# Based BOOSTER 1.01 ZSO Compressor
#
# GNU General Public Licence (GPL)
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 59 Temple
# Place, Suite 330, Boston, MA  02111-1307  USA
#
# pylint: disable=wrong-import-position
# pylint: disable=logging-fstring-interpolation

"""PS2 ISO to ZSO converter."""

import os
import re
import sys

import argparse
from pathlib import Path
from struct import pack, unpack
from multiprocessing import Pool
from os.path import abspath, basename, join, dirname

import lz4.block

WORK_DIR = dirname(__file__)

PARSER = argparse.ArgumentParser(
    description='Script to compresso PS2 ISO to ZSO or ZSO to ISO.'
)
PARSER.add_argument(
    '-c',
    dest='compress_level',
    type=int,
    default=9,
    help='Level: 1-9 compress ISO to ZSO, use any non-zero number it has no effect 0 decompress ZSO to ISO'
)
PARSER.add_argument(
    '-m',
    action='store_true',
    default=True,
    help='Use multiprocessing acceleration for compressing'
)
PARSER.add_argument(
    '-t',
    dest='compress_percentage',
    type=int,
    default=100,
    help='Percent Compression Threshold (1-100)'
)
PARSER.add_argument(
    '-ap',
    dest='align_padding',
    type=int,
    default=6,
    help='Align Padding alignment 0=small/slow 6=fast/large'
)
PARSER.add_argument(
    '-p',
    dest='padding_byte',
    type=int,
    default=br'X',
    help='Pad Padding byte'
)
PARSER.add_argument(
    '-a',
    '--all',
    dest='all',
    action='store_true',
    default=False,
    help='All files in current dir'
)

PARSER.add_argument(
    '-f',
    '--file',
    dest='input_file',
    type=Path,
    help='Input ISO/ZSO file'
)

PARSER.add_argument(
    '-d',
    '--dir',
    dest='isos_dir',
    type=Path,
    help='A diretory with multiple ISO/ZSO files'
)

ARGS = PARSER.parse_args()

CISO_MAGIC = 0x4F53495A
DEFAULT_ALIGN = ARGS.align_padding
COMPRESS_THREHOLD = ARGS.compress_percentage
DEFAULT_PADDING = ARGS.padding_byte

MULTPROCESS_STATE = ARGS.m
MP_NR = 1024 * 16

# def hexdump(data):
#     for i in data:
#         print("0x%02X" % ((ord(i)))),
#     print()


def lz4_compress(plain, level=9):
    return lz4.block.compress(plain, store_size=False)


def lz4_compress_mp(i):
    return lz4.block.compress(i[0], store_size=False)


def lz4_decompress(compressed):
    # hexdump(compressed)
    usize = 2048
    max_size = 4177920
    while True:
        try:
            decompressed = lz4.block.decompress(
                compressed, uncompressed_size=usize)
            break
        except lz4.block.LZ4BlockError:
            usize *= 2
            if usize > max_size:
                print('Error: data too large or corrupt')
                break
    return decompressed


def open_input_output(fname_in, fname_out):
    try:
        fin = open(fname_in, "rb")
    except IOError:
        print("Can't open %s" % (fname_in))
        sys.exit(-1)

    try:
        fout = open(fname_out, "wb")
    except IOError:
        print("Can't create %s" % (fname_out))
        sys.exit(-1)
    return fin, fout


def seek_and_read(fin, offset, size):
    fin.seek(offset)
    return fin.read(size)


def read_zso_header(fin):
    """ZSO header has 0x18 bytes"""
    return unpack('IIQIbbxx', seek_and_read(fin, 0, 0x18))


def generate_zso_header(magic, header_size, total_bytes, block_size, ver, align):
    #    assert(len(data) == 0x18)
    return pack('IIQIbbxx', magic, header_size, total_bytes, block_size, ver, align)


def show_zso_info(fname_in, fname_out, total_bytes, block_size, total_block, align):
    print("Decompress '%s' to '%s'" % (fname_in, fname_out))
    print("Total File Size %ld bytes" % (total_bytes))
    print("block size      %d  bytes" % (block_size))
    print("total blocks    %d  blocks" % (total_block))
    print("index align     %d" % (align))


def decompress_zso(fname_in, fname_out, level):
    fin, fout = open_input_output(fname_in, fname_out)
    magic, header_size, total_bytes, block_size, ver, align = read_zso_header(
        fin)

    if magic != CISO_MAGIC or block_size == 0 or total_bytes == 0:
        print("ziso file format error")
        return -1

    total_block = total_bytes // block_size
    index_buf = []

    for _ in range(total_block + 1):
        index_buf.append(unpack('I', fin.read(4))[0])

    show_zso_info(fname_in, fname_out, total_bytes,
                  block_size, total_block, align)

    block = 0
    percent_period = total_block/100
    percent_cnt = 0

    while block < total_block:
        percent_cnt += 1
        if percent_cnt >= percent_period and percent_period != 0:
            percent_cnt = 0
            print("decompress %d%%\r" %
                  (block / percent_period), file=sys.stderr, end='\r'),

        index = index_buf[block]
        plain = index & 0x80000000
        index &= 0x7fffffff
        read_pos = index << (align)

        if plain:
            read_size = block_size
        else:
            index2 = index_buf[block+1] & 0x7fffffff
            # Have to read more bytes if align was set
            if align:
                read_size = (index2-index+1) << (align)
            else:
                read_size = (index2-index) << (align)

        zso_data = seek_and_read(fin, read_pos, read_size)

        if plain:
            dec_data = zso_data
        else:
            try:
                dec_data = lz4_decompress(zso_data)
            except Exception as error_lz4:
                print("%d block: 0x%08X %d %s" % (block, read_pos, read_size, error_lz4))
                sys.exit(-1)

        fout.write(dec_data)
        block += 1

    fin.close()
    fout.close()
    print("ziso decompress completed")


def show_comp_info(fname_in, fname_out, total_bytes, block_size, align, level):
    print("Compress '%s' to '%s'" % (fname_in, fname_out))
    print("Total File Size %ld bytes" % (total_bytes))
    print("block size      %d  bytes" % (block_size))
    print("index align     %d" % (1 << align))
    print("compress level  %d" % (level))
    if MULTPROCESS_STATE:
        print("multiprocessing %s" % (MULTPROCESS_STATE))


def set_align(fout, write_pos, align):
    if write_pos % (1 << align):
        align_len = (1 << align) - write_pos % (1 << align)
        fout.write(DEFAULT_PADDING * align_len)
        write_pos += align_len

    return write_pos


def compress_zso(input_file, output_file, level_of_compression):
    """Method to compress ISO to ZSO."""
    fin, fout = open_input_output(input_file, output_file)
    fin.seek(0, os.SEEK_END)
    total_bytes = fin.tell()
    fin.seek(0)

    magic, header_size, block_size, ver, align = CISO_MAGIC, 0x18, 0x800, 1, DEFAULT_ALIGN

    # We have to use alignment on any ZSO files which > 2GB, for MSB bit of index as the plain indicator
    # If we don't then the index can be larger than 2GB, which its plain indicator was improperly set
    if total_bytes >= 2 ** 31 and align == 0:
        align = 1

    header = generate_zso_header(
        magic, header_size, total_bytes, block_size, ver, align)
    fout.write(header)

    total_block = total_bytes // block_size
    index_buf = [0 for i in range(total_block + 1)]

    fout.write(b"\x00\x00\x00\x00" * len(index_buf))
    show_comp_info(input_file, output_file, total_bytes,
                   block_size, align, level_of_compression)

    write_pos = fout.tell()
    percent_period = total_block/100
    percent_cnt = 0

    if MULTPROCESS_STATE:
        with Pool() as process_pool:

            block = 0
            while block < total_block:
                if MULTPROCESS_STATE:
                    percent_cnt += min(total_block - block, MP_NR)
                else:
                    percent_cnt += 1

                if percent_cnt >= percent_period and percent_period != 0:
                    percent_cnt = 0

                    if block == 0:
                        print("compress %3d%% avarage rate %3d%%\r" % (
                            block / percent_period, 0), file=sys.stderr, end='\r'),
                    else:
                        print("compress %3d%% avarage rate %3d%%\r" % (
                            block / percent_period, 100*write_pos/(block*0x800)), file=sys.stderr, end='\r'),

                if MULTPROCESS_STATE:
                    iso_data = [(fin.read(block_size), level_of_compression)
                                for i in range(min(total_block - block, MP_NR))]
                    zso_data_all = process_pool.map_async(
                        lz4_compress_mp, iso_data).get(9999999)

                    for i in range(len(zso_data_all)):
                        write_pos = set_align(fout, write_pos, align)
                        index_buf[block] = write_pos >> align
                        zso_data = zso_data_all[i]

                        if 100 * len(zso_data) / len(iso_data[i][0]) >= min(COMPRESS_THREHOLD, 100):
                            zso_data = iso_data[i][0]
                            index_buf[block] |= 0x80000000  # Mark as plain
                        elif index_buf[block] & 0x80000000:
                            print(
                                "Align error, you have to increase align by 1 or OPL won't be able to read offset above 2 ** 31 bytes")
                            sys.exit(1)

                        fout.write(zso_data)
                        write_pos += len(zso_data)
                        block += 1
                else:
                    iso_data = fin.read(block_size)

                    try:
                        zso_data = lz4_compress(iso_data, level_of_compression)
                    except Exception as e:
                        print("%d block: %s" % (block, e))
                        sys.exit(-1)

                    write_pos = set_align(fout, write_pos, align)
                    index_buf[block] = write_pos >> align

                    if 100 * len(zso_data) / len(iso_data) >= COMPRESS_THREHOLD:
                        zso_data = iso_data
                        index_buf[block] |= 0x80000000  # Mark as plain
                    elif index_buf[block] & 0x80000000:
                        print(
                            "Align error, you have to increase align by 1 or CFW won't be able to read offset above 2 ** 31 bytes")
                        sys.exit(1)

                    fout.write(zso_data)
                    write_pos += len(zso_data)
                    block += 1

            # Last position (total size)
            index_buf[block] = write_pos >> align

            # Update index block
            fout.seek(len(header))
            for i in index_buf:
                idx = pack('I', i)
        #        assert(len(idx) == 4)
                fout.write(idx)

            print("ziso compress completed , total size = %8d bytes , rate %d%%" %
                  (write_pos, (write_pos*100/total_bytes)))

            fin.close()
            fout.close()


def load_sector_table(sector_table_fn, total_block, default_level=9):
    """
    In future we will support NC
    """
    sectors = [default_level for i in range(total_block)]

    with open(sector_table_fn) as f:
        for line in f:
            line = line.strip()
            a = line.split(":")

            if len(a) < 2:
                raise ValueError("Invalid line founded: %s" % (line))

            if -1 == a[0].find("-"):
                try:
                    sector, level = int(a[0]), int(a[1])
                except ValueError:
                    raise ValueError("Invalid line founded: %s" % (line))
                if level < 1 or level > 9:
                    raise ValueError("Invalid line founded: %s" % (line))
                sectors[sector] = level
            else:
                b = a[0].split("-")
                try:
                    start, end, level = int(b[0]), int(b[1]), int(a[1])
                except ValueError:
                    raise ValueError("Invalid line founded: %s" % (line))
                i = start
                while i < end:
                    sectors[i] = level
                    i += 1

    return sectors


def make_output_path(current_dir, iso_file_name):
    """Create a .zso path with .iso path."""
    return abspath(
        join(
            current_dir,
            re.sub(r"(?i)\.iso", ".zso", iso_file_name)
        )
    )


def main():
    """Main method."""
    print("-" * 50)
    print(f"VERSÃO: {__version__:>17}")
    print(f"ziso-python: {__author__:>23}")
    print("Binary Windows/Linux: luizoti")
    print("-" * 50)
    print()

    level = ARGS.compress_level

    if ARGS.input_file:
        current_dir = ARGS.isos_dir
        input_file_path = ARGS.input_file
        output_file_path = make_output_path(current_dir, basename(input_file_path))
        compress_zso(input_file_path, output_file_path, level)
        return

    if ARGS.isos_dir:
        current_dir = ARGS.isos_dir
        files = [x for x in os.listdir(current_dir) if re.search(r"(?i)\.iso", x, re.I)]
        print()
        print("\n".join(files))
        print()

        for file_iso in files:
            input_file_path = abspath(join(current_dir, file_iso))
            output_file_path = make_output_path(current_dir, file_iso)
            compress_zso(input_file_path, output_file_path, level)
        return

if __name__ == "__main__":
    try:
        __version__ = "0.1"
        __author__ = "Virtuous Flame | luizoti"
        print("-" * 50)
        print(f"VERSÃO: {__version__:>17}")
        print(f"ziso-python: {__author__:>23}")
        print("Binary Windows/Linux: luizoti")
        print("-" * 50)
        print()
        main()
    except KeyboardInterrupt:
        sys.exit(0)
