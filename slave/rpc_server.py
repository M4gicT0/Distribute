#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
#
# Distributed under terms of the MIT license.

"""
RPC Server used to receive instructions from the lead node
"""

import json
import kodo
import logging
import threading

from node import Node
from lead import LeadNode

from os import walk
from random import shuffle
from werkzeug.serving import run_simple
from werkzeug.wrappers import Request, Response
from jsonrpc import JSONRPCResponseManager, dispatcher


controller = None
ip = None
port = None
mac = None
folder = "upload/"

def success():
    return {"code": 200, "msg": "Success"}


def failure():
    return {"code": 401, "msg": "Failure"}

class Server(threading.Thread):

    def __init__(self, this_controller, this_mac, this_ip, this_port):
        threading.Thread.__init__(self)
        global ip, port, controller, mac, success, failure
        ip = this_ip
        port = this_port
        mac = this_mac
        controller = this_controller
        logging.basicConfig()


    def run(self):
        run_simple(ip, port, self.application)


    @dispatcher.add_method
    def write_file(**kwargs):
        with open(folder+kwargs["name"], "w") as file:
            if controller.write_file(kwargs["name"],
                                     kwargs["content"].decode('hex')):
                return success()
        return failure()


    #REQ: name, content, ttl, nodes, kodo_content
    @dispatcher.add_method
    def write_files_kodo_repeat(**kwargs):
        filename = kwargs["name"]
        nodes = json.loads(kwargs["nodes"])
        loses = kwargs["loses"]
        coded = kwargs["coded"]
        index = kwargs["index"]
        content = kwargs["content"]
        kodo_packets = []

        if not coded:
            print("not coded")
            symbol_size = 4096
            print(content)
            print(type(content))
            symbols = len(content.decode('hex')) / symbol_size
            field = kodo.field.binary8
            factory_encoder = kodo.RLNCEncoderFactory(field, symbols, symbol_size)
            encoder = factory_encoder.build()
            encoder.set_const_symbols(content)
            encoder.set_systematic_off()
            encoded_packets = []
            packets_count = symbols + loses
            # print("After packets_count")
            for i in range(packets_count):
                encoded_packets.append(encoder.write_payload())
            print("Encoder end")
            kodo_packets = encoded_packets
            print(len(kodo_packets))
            #kodo_packets = encypt_with_kodo(content) TODO: FIX THIS YOU HAVE TO ENCODE HERE
            #kodo_packets = list([content,content,content,content]) # TODO: DELETE THIS IT IS ONLY USED FOR TESTING
        else:
            for cod in json.loads(content):
                kodo_packets.append(cod["pack"])
            print("is coded")
        kodo_filename = "{}.kodo.{}".format(filename,index)
        if not kodo_packets:
            print("done")
            return success()
        with open(folder+kodo_filename, "w") as file:
            file.write(kodo_packets.pop())
            controller.register_location(kwargs["name"], mac)
        new_nodes = []
        for node in nodes:
            new_nodes.append(Node(node['mac'], node['ip'], node['port'], node['units']))
        shuffle(new_nodes)
        for node in new_nodes:
            if node.mac == mac:
                continue
            print("sending to node: {} on {}".format(node.mac, node.ip))
            if len(kodo_packets) == 0:
                return  success()
            thread = threading.Thread(target=node.write_kodo_repeat,args=(filename,
                                                                 kodo_packets, loses, kwargs["nodes"], True, int(index)+1))
            thread.start()
            #node.write_kodo_repeat(filename, kodo_packets, loses, kwargs["nodes"], True, index+1)
            break
        return success()


    def encypt_with_kodo(self, file_bytes):
        return list([file_bytes,file_bytes,file_bytes,file_bytes,file_bytes])


    @dispatcher.add_method
    def write_file_repeat(**kwargs):
        print('you reached the write_file_repeat function')
        with open(folder+kwargs["name"], "w") as file:
            print("write file")
            file.write(kwargs["content"].decode('hex'))
        replications = kwargs["ttl"] - 1
        payload = controller.make_payload("register_location",{"file_name":kwargs["name"],"location":mac,"size":len(kwargs["content"].decode('hex'))})
        controller.leadNode.call(payload)
        print("replication {} -> {}".format(kwargs["ttl"],replications))
        if replications == 0:
            return success()
        else:
            nodes = json.loads(kwargs["nodes"])
            i = 0
            for node in nodes:
                if node['mac'] == mac:
                    nodes.pop(i)
                i = i+1
            for node in nodes:
                print(node)
                if node['mac'] == mac:
                    continue
                else:
                    print("send to other node")
                    new_node = Node(node['mac'],node['ip'],node['port'],node['units'])
                    new_node.write_repeat(kwargs["name"],kwargs["content"],replications,json.dumps(nodes))
                    break;
            print("no more nodes")
            return success()
        return failure()


    @dispatcher.add_method
    def read_file(**kwargs):
        filename = kwargs["name"]
        print("Read File {}".format(filename))
        if ".kodo." not in filename: #IF WE DON*T REQUEST A ENCODED FILE JUST RETURN IT
            print("read file {}".format(filename))
            with open(folder+filename, "rb") as file:
                return file.read().encode('hex') # TODO: Serialize before return
        else: #IF WE DO REQUEST A ENCODED FILE ALL MUST BE RETURNED
            f = []
            files = []
            for (dirpath, dirnames, filenames) in walk(os.getcwd()):
                f.extend(filenames)
            print(f)
            for path_filename in f:
                if filename in path_filename:
                    print(path_filename)
                    with open(folder+path_filename, "rb") as file:
                        files.append(file.read().encode('hex'))
            return files
        return failure()


    @dispatcher.add_method
    def read_kodo_files(**kwargs):
        filename = kwargs["name"]
        nodes = kwargs["nodes"]
        packs = []
        for node in nodes:
            print("retriving files: {}".format(filename))
            response = node.read("{}.kodo".format(filename))
            packs.extend(response["result"])
            #response = decypt_with_kodo(packs) TODO: uncomment and make code decryption here
            return {"result": file_bytes[0]} # TODO: delete this as it is used for testing only
            if response is None:
                continue
            # Will keep trying while there are locations to try on
            if response:
                return response.encode('hex')
        return failure()
        return success()


    def decypt_with_kodo(self, file_bytes):
        print(file_bytes[0])
        return {"result":file_bytes[0]}
        #return NONE if it can't be decoded with the amount of packets


    @dispatcher.add_method
    def delete_file(**kwargs):
        if controller.delete(kwargs["name"]):
            return success()
        else:
            return failure()


    @dispatcher.add_method
    def add_neighbour(**kwargs):
        if controller.add_neighbour(
            kwargs["mac"], kwargs["ip"], kwargs["port"], kwargs["units"]
        ):
            return success()
        else:
            return failure()


    @Request.application
    def application(self, request):
        response = JSONRPCResponseManager.handle(request.data, dispatcher)
        return Response(response.json, mimetype='application/json')



