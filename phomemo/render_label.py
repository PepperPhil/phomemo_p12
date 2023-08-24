#!/usr/bin/python3
# SPDX-License-Identifier: MIT
# -*- coding: utf-8 -*-

import sys
import argparse
import math
import cairo
import PIL.Image

def convert_to_pbm(img, outstrm):
    width, height = img.size

    ASCII_BITS = ['0', '1']

    # Convert image data to a list of ASCII bits.
    data = [ASCII_BITS[bool(val)] for val in img.getdata()]
    # Convert that to 2D list (list of character lists)
    data = [data[offset: offset+width] for offset in range(0, width*height, width)]

    outstrm.write('P1\n')
    outstrm.write(f'{width} {height}\n')
    for row in data:
        outstrm.write(' '.join(row) + '\n')


def cairo_context_init(surface_w, surface_h, fname, fsize, fweight: NORMAL):
    imagesize = (surface_w, surface_h)

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, *imagesize)

    cr = cairo.Context(surface)
    cr.set_antialias( cairo.Antialias.NONE )
    cr.set_source_rgb(0.0, 0.0, 0.0)
    cr.rectangle(0, 0, surface_w, surface_h)
    cr.fill()

    # setup font
    cr.set_source_rgb(1, 1, 1)
    cr.select_font_face(fname, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_+fweight)
    cr.set_font_size(fsize)

    return cr

def render_text(cr, text):
    t_ext = cr.text_extents(text)
    #print(t_ext, file=sys.stderr)
    #print(-int(t_ext.y_bearing-1), file=sys.stderr)
    cr.move_to(int(t_ext.x_bearing+1), -int(t_ext.y_bearing-1))
    cr.show_text(text)
    cr.stroke()

    #src = PIL.Image.frombytes('RGBA', (surface_w, surface_h), cr.get_target().get_data().tobytes(), 'raw')
    #rot.save("surface.png")
    #mono = src.convert("1")
    #return mono

def crop_rendered_text(cr, text):
    t_ext = cr.text_extents(text)
    surface_w = cr.get_target().get_width()
    surface_h = cr.get_target().get_height()
    x_offset = math.ceil(t_ext.x_bearing)
    x_width = x_offset + math.ceil(t_ext.x_advance)
    y_height = surface_h
    #print((x_offset, 0, x_width, y_height), file=sys.stderr)

    src = PIL.Image.frombytes('RGBA', (surface_w, surface_h), cr.get_target().get_data().tobytes(), 'raw')
    #rot.save("surface.png")
    mono = src.convert("1")

    return mono.crop((x_offset, 0, x_width, y_height))

def calc_y_offset(cr, text, fname, fsize):
    t_ext = cr.text_extents(text)

    return int((cr.get_target().get_height() - math.ceil(t_ext.height)) / 2)

def main():
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('--font', default="", help='Select font for text rendering')
    parser.add_argument('--font-size', type=int, default=0, help='Set Font size. Use [WIDTH - MARGIN] value as default.')
    parser.add_argument('--font-weight', default="NORMAL", help='Set Font weight. Default = NORMAL; Others like BOLD, ...')
    parser.add_argument('--width', type=int, default=96, help='The number of dots in the hardware tape width direction. default=96')
    parser.add_argument('--margin', type=int, default=8, help='Set width of unprintable region. default=8')
    parser.add_argument('--offset', type=int, default=0, help='Set rendering position offset')
    parser.add_argument('text')

    args = parser.parse_args()

    surface_w = 32767
    surface_h = args.width - args.margin

    font_size = args.font_size

    if args.font_size == 0:
        font_size = surface_h

    cr = cairo_context_init(surface_w, surface_h, args.font, font_size, args.font_weight)

    render_text(cr, args.text)
    cropped = crop_rendered_text(cr, args.text)
    y_offset = calc_y_offset(cr, args.text, args.font, font_size)

    y_offset -= args.offset

    resized = PIL.Image.new('1', cropped.size, 0)
    resized.paste(cropped, (0, y_offset))
    rot = resized.rotate(270, expand=True)

    convert_to_pbm(rot, sys.stdout)


if __name__ == '__main__':
    main()
