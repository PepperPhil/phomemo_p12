#!/usr/bin/python3
# SPDX-License-Identifier: MIT

import os
from flask import Flask
from .printer import PrinterConnection

printer = PrinterConnection()


def create_app():
    app = Flask(__name__)
    app.config['MAX_CONTENT_LENGTH'] = 4 * 1024 * 1024  # 4MB upload limit
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'uploads')
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    from . import routes
    app.register_blueprint(routes.bp)

    return app


def main():
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
