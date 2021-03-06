import os
import json
import errno

from node import Node
from subprocess import call
from werkzeug import secure_filename
from flask import Flask, render_template, request, jsonify, send_file, redirect
import io

app = Flask(__name__)
controller = None
ip = None
port = None


class REST:

    def __init__(self, ctrl, host, p):
        global controller, ip, port
        controller = ctrl
        ip = host
        port = p


    @app.route('/')
    def home_page():
        return render_template(
            'upload.html',
            rest_host=ip,
            rest_port=port,
            entries=controller.get_ledger_entries(),
            strategies=controller.get_strategies(),
            upload_status="",
            curr_strategy=controller.get_current_strategy()
        )


    @app.route('/storage', methods=['POST'])
    def upload_file():
        if 'file' in request.files:
            success = controller.store(
                secure_filename(request.files['file'].filename),
                request.files['file'].stream.read()
            )
            if success:
                response = jsonify({"msg": 'File uploaded successfully.'})
                response.status_code = 200
                return render_template(
                    'upload.html', rest_host=ip,
                    rest_port=port,
                    entries=controller.get_ledger_entries(),
                    strategies=controller.get_strategies(),
                    upload_status="{} successfully uploaded".format(
                        request.files['file'].filename
                    ),
                    curr_strategy=controller.get_current_strategy()
                )
            else:
                response = jsonify({"msg": "File couldn't be written to nodes."})
                response.status_code = 500
                return render_template(
                    'upload.html',
                    rest_host=ip,
                    rest_port=port,
                    entries=controller.get_ledger_entries(),
                    strategies=controller.get_strategies(),
                    upload_status="Failed",
                    curr_strategy=controller.get_current_strategy()
                )
        return jsonify({"msg": "File not present in request"})


    @app.route('/storage/', methods=['GET'])
    def download_file():
        if 'file_name' in request.args:
            file = controller.retrieve(
                secure_filename(request.args.get('file_name'))
            )
            if file:
                mem = io.BytesIO()
                mem.write(file["result"].decode('hex'))
                mem.seek(0)
                return send_file(
                    mem,
                    attachment_filename=request.args.get('file_name'),
                    as_attachment=True
                )
            else:
                response = jsonify({"msg": "File couldn't be found."})
                response.status_code = 500
                return response
        return jsonify({"msg": "File name not present in request"})


    @app.route('/log/', methods=['GET'])
    def get_log():
        return send_file(
            open("log.txt", "rb"),
            attachment_filename="log.txt",
            as_attachment=True
        )


    @app.route('/clearlog/', methods=['GET'])
    def clear_log():
        print("clear file")
        f = open('log.txt', 'w')
        f.write("")
        f.close()
        return render_template(
            'upload.html',
            rest_host=ip,
            rest_port=port,
            entries=controller.get_ledger_entries(),
            strategies=controller.get_strategies(), upload_status="",
            curr_strategy=controller.get_current_strategy()
        )


    @app.route('/strategy', methods=['GET'])
    def set_strategy():
        if 'strategy_name' in request.args:
            # TODO: change ledger
            controller.set_strategy(request.args.get('strategy_name'), request.args.get('attname'))
            return home_page()


    def start(self):
        app.run(debug=True, host=ip, port=port)
