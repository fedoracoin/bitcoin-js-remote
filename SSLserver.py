#!/usr/bin/python
import socket, os, time, shutil, signal
from SocketServer import BaseServer, ThreadingMixIn
import ssl

import posixpath
import BaseHTTPServer
import urllib, urllib2
import cgi

BITCOIN = "http://192.168.42.3:7332"

class SecureHTTPServer(ThreadingMixIn, BaseHTTPServer.HTTPServer):
	def __init__(self, server_address, HandlerClass):
		BaseServer.__init__(self, server_address, HandlerClass)
		fpem = 'server.pem'
		fcert = 'server.cert'

		self.daemon_threads = True
		self.protocol_version = 'HTTP/1.1'

		self.socket = ssl.wrap_socket(socket.socket(self.address_family, self.socket_type),
				keyfile=fpem, certfile=fcert, server_side=True, ssl_version=ssl.PROTOCOL_SSLv3)

		self.server_bind()
		self.server_activate()

class SecureHTTPRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
	def address_string(self):
		return self.client_address[0]

	def do_POST(self):
		length = int(self.headers.getheader('content-length'))

		query = self.rfile.read(length)

		req = urllib2.Request(BITCOIN, query, self.headers)

		print "PRE"
		try:
			response = urllib2.urlopen(req)
		except urllib2.URLError, e:
			response = e
		finally:
			try:
				data = response.read()
				self.send_response(response.code)
				self.send_header("Content-Length", len(data))
				self.send_header("Last-Modified", time.time())
				self.end_headers()
				if data:
					self.request.send(data)
			except:
				self.send_error(404, "File not found")

		print " -- POST"


	def do_GET(self):
		f = self.send_head()
		if f:
			self.copyfile(f, self.wfile)
			f.close()

	def do_HEAD(self):
		f = self.send_head()

	def translate_path(self, path):
		# abandon query parameters
		path = path.split('?',1)[0]
		path = path.split('#',1)[0]
		path = posixpath.normpath(urllib.unquote(path))
		words = path.split('/')
		words = filter(None, words)
		path = os.getcwd()
		for word in words:
			drive, word = os.path.splitdrive(word)
			head, word = os.path.split(word)
			if word in (os.curdir, os.pardir): continue
			path = os.path.join(path, word)
		return path

	def copyfile(self, source, outputfile):
		shutil.copyfileobj(source, outputfile)

	def send_head(self):
		path = self.translate_path(self.path)
		f = None
		if os.path.isdir(path):
			if not self.path.endswith('/'):
				# redirect browser - doing basically what apache does
				self.send_response(301)
				self.send_header("Location", self.path + "/")
				self.end_headers()
				return None
			for index in "index.html", "index.htm":
				index = os.path.join(path, index)
				if os.path.exists(index):
					path = index
					break

		try:
			# Always read in binary mode. Opening files in text mode may cause
			# newline translations, making the actual size of the content
			# transmitted *less* than the content-length!
			f = open(path, 'rb')
		except IOError:
			self.send_error(404, "File not found")
			return None
		self.send_response(200)
		fs = os.fstat(f.fileno())
		self.send_header("Content-Length", str(fs[6]))
		self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
		self.end_headers()
		return f

def run(HandlerClass = SecureHTTPRequestHandler,
		 ServerClass = SecureHTTPServer):
	server_address = ('', 8888) 
	httpd = ServerClass(server_address, HandlerClass)
	sa = httpd.socket.getsockname()
	print "Serving HTTPS on", sa[0], "port", sa[1], "..."
	httpd.serve_forever()

def exit_handler(signum, frame):
	print "Exit"
	os._exit(0)

if __name__ == '__main__':
	signal.signal(signal.SIGINT, exit_handler)
	run()