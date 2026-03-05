#!/usr/bin/python3
# SPDX-License-Identifier: MIT

import io
import os
import uuid
import base64

from flask import Blueprint, render_template, request, jsonify, current_app, send_file
import PIL.Image

from . import printer

bp = Blueprint('main', __name__, static_folder='static', template_folder='templates')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'gif', 'webp'}


def _allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _image_to_png_bytes(image):
    """Convert a PIL Image to PNG bytes."""
    buf = io.BytesIO()
    # Convert 1-bit to grayscale for PNG compatibility
    image.convert('L').save(buf, format='PNG')
    buf.seek(0)
    return buf


def _image_to_base64_png(image):
    """Convert a PIL Image to base64-encoded PNG string."""
    buf = _image_to_png_bytes(image)
    return base64.b64encode(buf.read()).decode('ascii')


@bp.route('/')
def index():
    return render_template('index.html')


@bp.route('/api/config', methods=['GET'])
def get_config():
    return jsonify({
        'port': printer.port_path,
        'dots': printer.dots
    })


@bp.route('/api/config', methods=['POST'])
def set_config():
    data = request.get_json()
    if not data or 'port' not in data:
        return jsonify({'status': 'error', 'message': 'Missing port parameter'}), 400

    port = data['port'].strip()
    dots = int(data.get('dots', 96))

    if not port:
        return jsonify({'status': 'error', 'message': 'Port cannot be empty'}), 400

    printer.configure(port, dots)
    return jsonify({'status': 'ok', 'port': port, 'dots': dots})


@bp.route('/api/fonts', methods=['GET'])
def list_fonts():
    fonts = printer.list_fonts()
    return jsonify({'fonts': fonts})


@bp.route('/api/preview', methods=['POST'])
def preview():
    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({'status': 'error', 'message': 'Missing text parameter'}), 400

    text = data['text']
    if not text.strip():
        return jsonify({'status': 'error', 'message': 'Text cannot be empty'}), 400

    try:
        image = printer.render_text_to_image(
            text=text,
            font=data.get('font', ''),
            font_size=int(data.get('fontSize', 0)),
            font_weight=data.get('fontWeight', 'NORMAL'),
            font_slant=data.get('fontSlant', 'NORMAL'),
            margin=int(data.get('margin', 8)),
            offset=int(data.get('offset', 0))
        )
        preview_b64 = _image_to_base64_png(image)
        return jsonify({'status': 'ok', 'preview': preview_b64})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@bp.route('/api/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file uploaded'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No file selected'}), 400

    if not _allowed_file(file.filename):
        return jsonify({'status': 'error',
                        'message': f'File type not allowed. Accepted: {", ".join(ALLOWED_EXTENSIONS)}'}), 400

    try:
        file_id = str(uuid.uuid4())
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{file_id}.{ext}"
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Generate preview of the converted image
        with open(filepath, 'rb') as f:
            image_bytes = f.read()
        converted = printer.prepare_uploaded_image(image_bytes)
        preview_b64 = _image_to_base64_png(converted)

        return jsonify({
            'status': 'ok',
            'fileId': file_id,
            'filename': filename,
            'preview': preview_b64
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@bp.route('/api/print', methods=['POST'])
def print_label():
    if not printer.port_path:
        return jsonify({'status': 'error', 'message': 'Printer not configured. Set port first.'}), 400

    data = request.get_json()
    if not data or 'type' not in data:
        return jsonify({'status': 'error', 'message': 'Missing label type'}), 400

    try:
        label_type = data['type']

        if label_type == 'text':
            text = data.get('text', '').strip()
            if not text:
                return jsonify({'status': 'error', 'message': 'Text cannot be empty'}), 400
            image = printer.render_text_to_image(
                text=text,
                font=data.get('font', ''),
                font_size=int(data.get('fontSize', 0)),
                font_weight=data.get('fontWeight', 'NORMAL'),
                font_slant=data.get('fontSlant', 'NORMAL')
            )
        elif label_type == 'image':
            filename = data.get('filename', '')
            if not filename:
                return jsonify({'status': 'error', 'message': 'Missing filename'}), 400
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            if not os.path.exists(filepath):
                return jsonify({'status': 'error', 'message': 'Uploaded file not found'}), 404
            with open(filepath, 'rb') as f:
                image = printer.prepare_uploaded_image(f.read())
        else:
            return jsonify({'status': 'error', 'message': f'Unknown label type: {label_type}'}), 400

        printer.print_label(image)
        return jsonify({'status': 'ok'})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 503


@bp.route('/api/print-all', methods=['POST'])
def print_all():
    if not printer.port_path:
        return jsonify({'status': 'error', 'message': 'Printer not configured. Set port first.'}), 400

    data = request.get_json()
    if not data or 'labels' not in data:
        return jsonify({'status': 'error', 'message': 'Missing labels array'}), 400

    results = []
    for i, label in enumerate(data['labels']):
        try:
            label_type = label.get('type', '')

            if label_type == 'text':
                text = label.get('text', '').strip()
                if not text:
                    results.append({'index': i, 'status': 'error', 'message': 'Empty text'})
                    continue
                image = printer.render_text_to_image(
                    text=text,
                    font=label.get('font', ''),
                    font_size=int(label.get('fontSize', 0)),
                    font_weight=label.get('fontWeight', 'NORMAL'),
                    font_slant=label.get('fontSlant', 'NORMAL')
                )
            elif label_type == 'image':
                filename = label.get('filename', '')
                filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                if not os.path.exists(filepath):
                    results.append({'index': i, 'status': 'error', 'message': 'File not found'})
                    continue
                with open(filepath, 'rb') as f:
                    image = printer.prepare_uploaded_image(f.read())
            else:
                results.append({'index': i, 'status': 'error', 'message': f'Unknown type: {label_type}'})
                continue

            printer.print_label(image)
            results.append({'index': i, 'status': 'ok'})

        except Exception as e:
            results.append({'index': i, 'status': 'error', 'message': str(e)})

    return jsonify({'status': 'ok', 'results': results})
