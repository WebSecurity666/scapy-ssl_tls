# -*- coding: utf-8 -*-

from __future__ import print_function
import os


basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
try:
    # This import works from the project directory
    from scapy_ssl_tls.ssl_tls import *
except ImportError:
    # If you installed this package via pip, you just need to execute this
    from scapy.layers.ssl_tls import *

host = ("localhost", 8443)
cipher = TLSCipherSuite.RSA_WITH_AES_128_CBC_SHA

with open(os.path.join(basedir, "tests/integration/keys/cert.der"), "rb") as f:
    cert = f.read()
certificates = TLSCertificate(data=cert)

with TLSSocket(client=False) as tls_socket:
    tls_socket.tls_ctx.server_ctx.load_rsa_keys_from_file(os.path.join(basedir, "tests/integration/keys/key.pem"))

    try:
        tls_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        tls_socket.bind(host)
        tls_socket.listen(1)
        client_socket, _ = tls_socket.accept()
    except socket.error as se:
        print("Failed to bind server: %s" % (host,), file=sys.stderr)
    else:
        try:
            r = client_socket.recvall()
            version = r[TLSClientHello].version
            server_hello = TLSRecord(version=version) / TLSHandshakes(handshakes=[TLSHandshake() / TLSServerHello(version=version, cipher_suite=cipher),
                                                                                  TLSHandshake() / TLSCertificateList() /
                                                                                                   TLS10Certificate(certificates=certificates),
                                                                                  TLSHandshake(type=TLSHandshakeType.SERVER_HELLO_DONE)])
            r = client_socket.do_round_trip(server_hello)
            r.show()

            client_socket.do_round_trip(TLSRecord(version=version) / TLSChangeCipherSpec(), recv=False)
            r = client_socket.do_round_trip(TLSHandshakes(handshakes=[TLSHandshake() / TLSFinished(data=client_socket.tls_ctx.get_verify_data())]))

            r.show()
            client_socket.do_round_trip(TLSPlaintext(data="It works!\n"), recv=False)
            client_socket.do_round_trip(TLSAlert(), recv=False)
        except TLSProtocolError as tpe:
            print("Got TLS error: %s" % tpe, file=sys.stderr)
            tpe.response.show()
        finally:
            print(client_socket.tls_ctx)
